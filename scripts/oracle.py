"""Programmatic oracle arms. Perfect-information overrides on KEEP.

Rules:
  none  KEEP unmodified, control
  O1    Restore any compromised host in the agent's subnets
  O2    Override only when KEEP's choice is wrong given ground truth
  O2e   As O2, but 'compromised' is the latched observable-evidence set (hosts named by a
        substantive raw obs since their last Restore/Remove), not ground truth
  O2er  As O2e, most-recently-observed host first
  O2ew  As O2er, flags expire 30 steps after the last observation naming the host
  O2s   As O2er, but a host is flagged only by a Files entry with Density >= 0.9 (Analyse-confirmed)
  O11   Constrain: when a compromised host exists, force Restore/Remove but take the host from
        the argmax of KEEP's own action distribution over those two verbs
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
from CybORG.Simulator.Actions import Restore, Remove, Monitor, Sleep, Analyse
from submission import Submission
from wrapper.globals import MY_SUBNETS, MAX_HOSTS, MAX_ACTIONS, NODE_ACTIONS
from oracle_rules import (make_oracle, note_impacts, owned_hosts, compromised_by_agent, subnet_of,
                          EPISODE_LENGTH, BLUE, RED, OWNER, EXPENSIVE, HARNESS_SHA, MACHINE,
                          _IMPACT_SEEN, _HOSTS_CACHE)


def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0):
    """Wrap action_translator so overrides slot in before execution."""
    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap)
    original = env.action_translator
    def patched(agent_name, a_id):
        return intercept(agent_name, original(agent_name, a_id))
    env.action_translator = patched


def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent", min_gap=0, workers=0):
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
    stats["dact"] = []      # rule defender's per-step reasons; emptied into each step record
    decoys = {}
    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap)
    if rule == "O11":
        stats["probs"] = {}
        for _n, _ag in agents.items():
            def _wrap(obs, *a, _orig=_ag.get_action, _ag=_ag, _n=_n):
                state, is_blocked = obs
                if is_blocked:
                    stats["probs"][_n] = None
                else:
                    with torch.no_grad():
                        stats["probs"][_n] = _ag.actor(*state).probs.detach().flatten()
                return _orig(obs, *a)
            _ag.get_action = _wrap

    wrapped_obs, _ = env.reset()
    for a in agents.values():
        if hasattr(a, "reset"):
            a.reset()

    path = Path(out_dir) / f"ep_{ep:05d}.jsonl"
    total = 0.0
    t0 = time.time()

    with open(path, "w") as f:
        f.write(json.dumps({
            "record": "header", "harness_sha": HARNESS_SHA, "machine": MACHINE, "weights": os.environ.get("KEEP_WEIGHTS", "shipped"), "red_agent": _rc.__name__, "episode": ep, "seed": seed,
            "rule": rule, "budget": budget, "min_gap": min_gap, "workers": workers, "cyborg_version": CYBORG_VERSION,
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
                "overrides": stats.pop("ovr", []),
                "defender": stats.get("dact") or [],
            }) + "\n")
            stats["dact"] = []

            if term.get("blue_agent_0") or trunc.get("blue_agent_0"):
                break

        f.write(json.dumps({
            "record": "footer", "episode": ep, "steps": step + 1,
            "total_reward": total, "overrides": stats["override"], "translator_calls": stats["calls"],
            "agreements": stats["agree"],
            "deferred": stats.get("deferred", 0),
            "analyses": stats.get("exec_Analyse", 0), "restores": stats.get("exec_Restore", 0),
            "removes": stats.get("exec_Remove", 0), "sleeps": stats.get("exec_Sleep", 0),
            "flags_new": stats.get("flags_new", 0),
            "latch_tp": stats.get("tp", 0), "latch_fp": stats.get("fp", 0),
            "latch_fn": stats.get("fn", 0), "latch_own": stats.get("own", 0),
            "defender_restores": stats.get("d_restore", 0), "defender_analyses": stats.get("d_analyse", 0),
            "defender_decoys": stats.get("d_decoy", 0), "defender_sleeps": stats.get("d_sleep", 0),
            "defender_flags_new": stats.get("d_flags_new", 0), "defender_alerts": stats.get("d_alerts", 0),
            "defender_removes": stats.get("d_remove", 0), "defender_blocks": stats.get("d_block", 0), "defender_allows": stats.get("d_allow", 0),
            "defender_tp": stats.get("d_tp", 0), "defender_fp": stats.get("d_fp", 0), "defender_fn": stats.get("d_fn", 0),
            "wall_seconds": round(time.time() - t0, 2),
        }) + "\n")

    return total, stats["override"], stats["agree"], time.time() - t0


def main():
    p = argparse.ArgumentParser("Oracle arms")
    p.add_argument("--min-gap", type=int, default=0, help="per-agent minimum steps between overrides")
    p.add_argument("--rule", default="O1",
                   choices=["none", "O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9r", "O9s", "O2e", "O2er", "O2ew", "O2s", "O11", "O10", "O12", "O13",
                            "R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "RT",
                            "R1+O1", "R2+O1", "R2+O10", "R3+O1", "R4+O1", "R4+O10", "R4+O13", "R4+O2s", "R4d+O1", "RT+O1"],
                   help="a supervisor rule on KEEP, or a rule defender (R1 to R4, RT), optionally with a supervisor rule on top (R4+O1)")
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
        delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red, a.min_gap, a.workers)
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
