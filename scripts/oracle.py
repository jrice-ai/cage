"""Programmatic oracle arms. Perfect-information overrides on KEEP.

Rules:
  none  KEEP unmodified, control
  O1    Restore any compromised host in the agent's subnets
  O2    Override only when KEEP's choice is wrong given ground truth
  O2e   As O2, but 'compromised' is the latched observable-evidence set (hosts named by a
        substantive raw obs since their last Restore/Remove), not ground truth
  O2er  As O2e, most-recently-observed host first
  O2ew  As O2er, flags expire 30 steps after the last observation naming the host
  O3    Remove instead of Restore
  O4    Restore only in zones expensive in the current phase

Usage:
  python3 /work/scripts/oracle.py --rule O1 --episodes 100 --workers 12 \
      --out /work/data/traces/oracle_O1
"""
import argparse, json, os, random, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/opt/cage/cage-4-submission")

import numpy as np
import torch
from joblib import Parallel, delayed

from CybORG import CybORG, CYBORG_VERSION
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Simulator.Actions import Restore, Remove, Monitor, Sleep
from submission import Submission
from wrapper.globals import MY_SUBNETS

# --- provenance (added 2026-09-15) ---
import os as _os, platform as _platform, subprocess as _subprocess

def _harness_sha():
    sha = _os.environ.get("HARNESS_SHA")
    if sha:
        return sha
    try:
        here = _os.path.dirname(_os.path.abspath(__file__))
        return _subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here,
                                        stderr=_subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"

HARNESS_SHA = _harness_sha()
MACHINE = _platform.node()
RED_AGENT_NAME = "FiniteStateRedAgent"   # overwritten where --red is resolved
# --- end provenance ---

EPISODE_LENGTH = 500
BLUE = [f"blue_agent_{i}" for i in range(5)]
RED = [f"red_agent_{i}" for i in range(6)]

OWNER = {}
for _aid, _sns in MY_SUBNETS.items():
    for _sn in _sns:
        OWNER[_sn] = f"blue_agent_{_aid}"

EXPENSIVE = {"restricted_zone_a_subnet", "restricted_zone_b_subnet"}



def subnet_of(hostname):
    for sn in OWNER:
        if hostname.startswith(sn):
            return sn
    return None


_HOSTS_CACHE = {}
_IMPACT_SEEN = {}


def note_impacts(cyborg, step):
    key = id(cyborg)
    d = _IMPACT_SEEN.setdefault(key, {})
    for a in [f'red_agent_{i}' for i in range(6)]:
        act = cyborg.get_last_action(a)
        if act is None:
            continue
        txt = str(act)
        if 'Impact' in txt or 'Degrade' in txt:
            parts = txt.strip('[]').split()
            if len(parts) > 1:
                d[parts[1]] = step
    return d


def owned_hosts(cyborg, agent_name):
    key = (id(cyborg), agent_name)
    if key not in _HOSTS_CACHE:
        st = cyborg.environment_controller.state
        _HOSTS_CACHE[key] = [
            h for h in st.hosts
            if "router" not in h and subnet_of(h)
            and OWNER.get(subnet_of(h)) == agent_name]
    return _HOSTS_CACHE[key]


def compromised_by_agent(cyborg):
    st = cyborg.environment_controller.state
    out = {}
    for hn, h in st.hosts.items():
        if any(a.startswith("red") and s for a, s in h.sessions.items()):
            sn = subnet_of(hn)
            if sn:
                out.setdefault(OWNER[sn], []).append((hn, sn))
    return out


SERVER_W = 2.0


def _zone_weight(cyborg, subnet):
    ph = int(cyborg.environment_controller.state.mission_phase)
    tbl = cyborg.environment_controller.team_reward_calculators[
        "Blue"]["BlueRewardMachine"].get_phase_rewards(ph)
    e = tbl.get(subnet, {})
    return -(e.get("LWF", 0) + e.get("ASF", 0) + e.get("RIA", 0))


def _host_score(cyborg, hostname, decoys):
    sn = subnet_of(hostname)
    w = _zone_weight(cyborg, sn) if sn else 0.0
    if "server" in hostname:
        w *= SERVER_W
    return w / (1.0 + decoys.get(hostname, 0))


def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None):
    """Wrap action_translator so overrides slot in before execution."""
    if decoys is None:
        decoys = {}
    original = env.action_translator

    flagged = {}   # O2e: agent_name -> hosts named by a substantive obs since last Restore/Remove
    META = {"success", "action", "message"}

    def patched(agent_name, a_id):
        stats["calls"] += 1
        act = original(agent_name, a_id)
        if rule == "none":
            return act

        if rule in ("O9r", "O9s"):
            name = type(act).__name__
            if name == "DeployDecoy":
                t = getattr(act, "hostname", None)
                if t:
                    decoys[t] = decoys.get(t, 0) + 1
                return act

            dirty = {c[0] for c in
                     compromised_by_agent(cyborg).get(agent_name, [])}
            pool = [h for h in owned_hosts(cyborg, agent_name)
                    if h not in dirty]
            if not pool:
                return act
            ranked = sorted(pool,
                            key=lambda h: -_host_score(cyborg, h, decoys))

            if rule == "O9s":
                if name != "Restore":
                    return act
                tgt = getattr(act, "hostname", None)
                cutoff = set(ranked[:max(1, len(ranked) // 3)])
                if tgt in cutoff:
                    stats["agree"] += 1
                    return act
                if stats["override"] >= budget:
                    stats["exhausted"] += 1
                    return act
                stats["override"] += 1
                decoys[ranked[0]] = 0
                return Restore(session=0, agent=agent_name,
                               hostname=ranked[0])

            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            if name == "Restore" and getattr(act, "hostname", None) == ranked[0]:
                stats["agree"] += 1
                return act
            stats["override"] += 1
            decoys[ranked[0]] = 0
            return Restore(session=0, agent=agent_name, hostname=ranked[0])

        comp = compromised_by_agent(cyborg).get(agent_name, [])

        if rule == "O8":
            if type(act).__name__ == "Restore":
                tgt = getattr(act, "hostname", None)
                dirty = {c[0] for c in comp}
                hist = _IMPACT_SEEN.get(id(cyborg), {})
                step_now = cyborg.environment_controller.step_count
                recent = tgt in hist and (step_now - hist[tgt]) <= 30
                if tgt not in dirty and not recent:
                    stats["override"] += 1
                    return Sleep()
                stats["agree"] += 1
            return act

        if rule == "O7":
            if type(act).__name__ in ("Restore", "Remove"):
                pool = owned_hosts(cyborg, agent_name)
                if pool:
                    stats["override"] += 1
                    return type(act)(session=0, agent=agent_name,
                                     hostname=random.choice(pool))
            return act

        if rule == "O6":
            if type(act).__name__ in ("Restore", "Remove"):
                tgt = getattr(act, "hostname", None)
                if tgt not in {c[0] for c in comp}:
                    stats["override"] += 1
                    return Sleep()
                stats["agree"] += 1
            return act
        if rule in ("O2e", "O2er", "O2ew"):
            obs = cyborg.get_observation(agent_name) or {}
            st = flagged.setdefault(agent_name, {"t": 0, "h": {}})   # h: host -> [first_seen, last_seen]
            st["t"] += 1
            t = st["t"]
            for h, v in obs.items():
                if h not in META and isinstance(v, dict):
                    if h in st["h"]:
                        st["h"][h][1] = t
                    else:
                        st["h"][h] = [t, t]
            own = set(owned_hosts(cyborg, agent_name))
            live = {h: fl for h, fl in st["h"].items() if h in own}
            if rule == "O2ew":
                live = {h: fl for h, fl in live.items() if t - fl[1] <= 30}
            if rule == "O2e":
                ecomp = sorted(live, key=lambda h: live[h][0])       # oldest flag first
            else:
                ecomp = sorted(live, key=lambda h: -live[h][1])      # most recently seen first
            _gt = {c[0] for c in comp}; _ev = set(ecomp)
            stats["tp"] = stats.get("tp", 0) + len(_gt & _ev)
            stats["fp"] = stats.get("fp", 0) + len(_ev - _gt)
            stats["fn"] = stats.get("fn", 0) + len(_gt - _ev)
            stats["own"] = stats.get("own", 0) + len(own)
            acting_on = getattr(act, "hostname", None)
            if type(act).__name__ in ("Restore", "Remove") and acting_on in ecomp:
                stats["agree"] += 1
                st["h"].pop(acting_on, None)
                return act
            if not ecomp:
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            stats["override"] += 1
            tgt = ecomp[0]
            st["h"].pop(tgt, None)
            return Restore(session=0, agent=agent_name, hostname=tgt)

        if rule == "O4":
            comp = [c for c in comp if c[1] in EXPENSIVE]
        if not comp:
            return act

        target = comp[0][0]
        dirty = {c[0] for c in comp}
        name = type(act).__name__

        if rule == "O1":
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=target)
        if rule == "O3":
            stats["override"] += 1
            return Remove(session=0, agent=agent_name, hostname=target)
        if rule == "O4":
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=target)
        if rule == "O5":
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            ph = int(cyborg.environment_controller.state.mission_phase)
            tbl = cyborg.environment_controller.team_reward_calculators[
                "Blue"]["BlueRewardMachine"].get_phase_rewards(ph)
            def _w(sn):
                e = tbl.get(sn, {})
                return -e.get("RIA", 0) + e.get("LWF", 0)
            ranked = sorted(comp, key=lambda c: -_w(c[1]))
            best, best_sn = ranked[0]
            if _w(best_sn) < 2:
                stats["skipped"] += 1
                return act
            name2 = type(act).__name__
            if name2 == "Restore" and getattr(act, "hostname", None) in dirty:
                stats["agree"] += 1
                return act
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=best)

        if rule == "O2":
            acting_on = getattr(act, "hostname", None)
            if name in ("Restore", "Remove") and acting_on in dirty:
                stats["agree"] += 1
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=target)
        return act

    env.action_translator = patched


def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent"):
    seed = base_seed + ep
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)

    import importlib
    _rm = importlib.import_module(f"CybORG.Agents.SimpleAgents.{red_agent}")
    _rc = getattr(_rm, red_agent)
    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=_rc,
        steps=EPISODE_LENGTH)
    cyborg = CybORG(sg, "sim", seed=seed)
    env = Submission.wrap(cyborg)
    agents = Submission.AGENTS

    stats = Counter()
    decoys = {}
    install_oracle(env, cyborg, rule, stats, budget, decoys)

    wrapped_obs, _ = env.reset()
    for a in agents.values():
        if hasattr(a, "reset"):
            a.reset()

    path = Path(out_dir) / f"ep_{ep:05d}.jsonl"
    total = 0.0
    t0 = time.time()

    with open(path, "w") as f:
        f.write(json.dumps({
            "record": "header", "harness_sha": HARNESS_SHA, "machine": MACHINE, "red_agent": _rc.__name__, "episode": ep, "seed": seed,
            "rule": rule, "budget": budget, "red_agent": red_agent, "cyborg_version": CYBORG_VERSION,
            "episode_length": EPISODE_LENGTH,
        }) + "\n")

        for step in range(EPISODE_LENGTH):
            st = cyborg.environment_controller.state
            phase = st.mission_phase
            n_comp = sum(len(v) for v in compromised_by_agent(cyborg).values())

            actions = {n: agents[n].get_action(wrapped_obs[n],
                                               env.action_space(n))
                       for n in BLUE}
            wrapped_obs, rew, term, trunc, info = env.step(actions)

            note_impacts(cyborg, step)
            executed = {n: str(cyborg.get_last_action(n)) for n in BLUE}
            red_acts = {n: str(cyborg.get_last_action(n)) for n in RED}
            red_acts = {k: v for k, v in red_acts.items()
                        if v not in ("None", "[Sleep]")}

            step_reward = float(rew["blue_agent_0"])
            total += step_reward

            f.write(json.dumps({
                "record": "step", "episode": ep, "step": step,
                "phase": int(phase), "action": executed,
                "red_action": red_acts,
                "step_reward": step_reward, "cumulative_reward": total,
                "n_compromised_owned": n_comp,
            }) + "\n")

            if term.get("blue_agent_0") or trunc.get("blue_agent_0"):
                break

        f.write(json.dumps({
            "record": "footer", "episode": ep, "steps": step + 1,
            "total_reward": total, "overrides": stats["override"], "translator_calls": stats["calls"],
            "agreements": stats["agree"],
            "latch_tp": stats.get("tp", 0), "latch_fp": stats.get("fp", 0),
            "latch_fn": stats.get("fn", 0), "latch_own": stats.get("own", 0),
            "wall_seconds": round(time.time() - t0, 2),
        }) + "\n")

    return total, stats["override"], stats["agree"], time.time() - t0


def main():
    p = argparse.ArgumentParser("Oracle arms")
    p.add_argument("--rule", default="O1",
                   choices=["none", "O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9r", "O9s", "O2e", "O2er", "O2ew"])
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--base-seed", type=int, default=0)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--budget", type=int, default=77,
                   help="Max overrides per episode for O5")
    p.add_argument("--red", default="FiniteStateRedAgent")
    p.add_argument("--out", default="/work/data/traces/oracle")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    print(f"Rule {a.rule}, {a.episodes} episodes, {a.workers} workers")

    res = Parallel(n_jobs=a.workers, prefer="processes")(
        delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red)
        for ep in range(a.episodes))

    tot = [r[0] for r in res]
    ov = [r[1] for r in res]
    ag = [r[2] for r in res]
    import statistics as st
    print(f"\nmean {st.mean(tot):.2f}  "
          f"stdev {st.stdev(tot) if len(tot) > 1 else 0:.2f}  "
          f"overrides/ep {st.mean(ov):.1f}  agreements/ep {st.mean(ag):.1f}")


if __name__ == "__main__":
    main()
