#!/usr/bin/env python3
"""H-MARL Expert through the oracle ladder.

The rules are the ones in scripts/oracle_rules.py (shared with oracle.py), installed on
the H-MARL 3-policy wrapper. That wrapper alternates a master phase (each agent's master
picks Investigate or Recover; no simulator step) and a sub-policy phase (env_step; one
simulator step). Rules intercept inside env_step, after the sub-policy's index becomes a
CybORG action and before the simulator moves, so overrides, agreements, translator_calls
and gap ticks count per simulator step exactly as they do for KEEP.

Rules: everything oracle_rules supports except O11 (needs KEEP's actor), plus
  O14   Mode authority. When ground truth says the agent's subnets hold a compromised
        host and the expert gate says Investigate, flip the gate to Recover before the
        master acts (mask, high_actionmask and return_agent set as an observed IoC
        would set them); the recover sub-policy picks the host. The verb-level
        authority (cf. O11) expressed in H-MARL's own hierarchy. Counted as an
        override, subject to --min-gap.

Seeding modes
  default   fresh CybORG(seed=base+ep) per episode, sampling reseeded per episode with
            (--policy-seed or base)+ep, episodes run in parallel. Arms pair seed by seed.
  --compat  mirrors h-marl-3policy/subpolicies/evaluation.py with build/hmarl-fixes.patch:
            seed once, load policies, one CybORG(seed=base) reset per episode, sequential.
            With --rule none this must reproduce their numbers to the digit
            (seed 0: -124.11 FiniteStateRedAgent, -863.86 FSRedAgentWrecker, 100 episodes).

Trace format: one ep_NNNNN.jsonl per episode, header / step / footer records. Step
records are per simulator step and carry each agent's executed mode and the expert
master's own choice. Footer keys match oracle.py's plus mode_overrides and
recover_agent_steps.

Usage (inside cage-hmarl:dev via bin/run; cwd must be h-marl-3policy or set H3P_DIR):
  python3 -u /work/scripts/capture_hmarl.py --compat --rule none --red FSRedAgentWrecker \
      --episodes 3 --out /work/data/traces/hm_compat_wrecker_3
  python3 -u /work/scripts/capture_hmarl.py --rule O1 --min-gap 32 --red FSRedAgentWrecker \
      --episodes 100 --workers 6 --out /work/data/traces/hm_wo_O1_g32
"""
import argparse, json, os, random, sys, time
from collections import Counter
from pathlib import Path


def _find_h3p():
    for c in (os.environ.get("H3P_DIR"), os.getcwd(),
              "/work/repos/Hierarchical-MARL/h-marl-3policy"):
        if c and os.path.exists(os.path.join(c, "subpolicies", "submission.py")):
            return os.path.abspath(c)
    sys.exit("capture_hmarl: h-marl-3policy not found; run from it or set H3P_DIR")


H3P = _find_h3p()
sys.path.insert(0, os.path.join(H3P, "subpolicies"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # oracle_rules.py

import numpy as np
import torch

from CybORG import CybORG, CYBORG_VERSION
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Simulator.Actions import Action

from oracle_rules import (make_oracle, note_impacts, compromised_by_agent,
                          EPISODE_LENGTH, BLUE, RED, HARNESS_SHA, MACHINE)

RULES = ["none", "O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9r", "O9s",
         "O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O10", "O12", "O13", "O14", "O15r", "O15a", "O15c"]

_SUB = None


def _submission():
    """Import submission.py once per process. It builds the fifteen Ray policies at
    import, which consumes the torch RNG, so --compat calls this after seeding and
    the per-episode path calls it before seeding."""
    global _SUB
    if _SUB is None:
        cwd = os.getcwd()
        os.chdir(H3P)                       # Ray_BlueAgent loads saved_policies/ relative to cwd
        try:
            import submission as _s
        finally:
            os.chdir(cwd)
        _SUB = _s.Submission
    return _SUB


def _red_class(name):
    import importlib
    return getattr(importlib.import_module(f"CybORG.Agents.SimpleAgents.{name}"), name)


def _make_env(seed, red_cls):
    sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent,
                                     green_agent_class=EnterpriseGreenAgent,
                                     red_agent_class=red_cls, steps=EPISODE_LENGTH)
    cyborg = CybORG(sg, "sim", seed=seed)
    return cyborg, _submission().wrap(cyborg)


def _install(env):
    """Wrap env_step once per wrapper. holder['intercept'] is replaced per episode so
    the rule's own state (latches, gap ticks, rotation memory) starts fresh."""
    holder = {"intercept": None, "space": {}}

    def acts(agent):
        if agent not in holder["space"]:
            holder["space"][agent] = env.get_action_space(agent)["actions"]
        return holder["space"][agent]

    def index_of(agent, act):
        hn = getattr(act, "hostname", None)
        for i, a in enumerate(acts(agent)):
            if type(a) is type(act) and getattr(a, "hostname", None) == hn:
                return i
        raise KeyError(f"{agent}: {type(act).__name__} {hn} is not in the fixed action space")

    orig = env.env_step

    def env_step(actions, messages=None, **kw):
        icp = holder["intercept"]
        out = {}
        for key, v in actions.items():             # key: blue_agent_i_investigate | _recover
            agent = key[:12]
            act = v if isinstance(v, Action) else acts(agent)[int(v)]
            res = icp(agent, act)
            out[key] = v if res is act else index_of(agent, res)
        return orig(out, messages, **kw)

    env.env_step = env_step

    # The wrapper's time-to-recover metric (COMPUTE_METRICS) keys a dictionary by
    # blue subnet and raises KeyError('contractor_network_subnet') when a red
    # agent's activity marks a contractor host as infected (Trident's TargetA*
    # family does). The metric is theirs, feeds no reward and nothing we record,
    # so the call is made tolerant on this instance; their code is untouched.
    if hasattr(env, "update_time_to_recover_metric"):
        _metric = env.update_time_to_recover_metric

        def _safe_metric(*a_, **k_):
            try:
                return _metric(*a_, **k_)
            except KeyError:
                return None
        env.update_time_to_recover_metric = _safe_metric
    return holder


def _o14(env, cyborg, obs, stats, min_gap, t, last):
    """Master-phase hook, applied to the master observations before the master acts.
    Under HITL the expert gate is the action mask ([1,0] Investigate, [0,1] Recover),
    set by observation_change together with return_agent. When ground truth says the
    agent's subnets hold a compromised host and the gate says Investigate, flip the
    gate to Recover exactly as an observed IoC would have: mask, high_actionmask and
    return_agent together, so the wrapper's state is indistinguishable from a genuine
    Recover choice and its HITL consistency check holds."""
    comp = compromised_by_agent(cyborg)
    for key, o in obs.items():
        agent = key[:12]
        if not comp.get(agent):
            continue
        if int(o["action_mask"][1]) == 1:
            stats["agree"] += 1
            continue
        if min_gap and t - last.get(agent, -10 ** 9) < min_gap:
            stats["deferred"] += 1
            continue
        last[agent] = t
        m = np.array([0, 1], dtype=np.int64)
        o["action_mask"] = m
        env.high_actionmask[agent] = m
        ra = getattr(env, "return_agent", None)
        if isinstance(ra, dict):
            ra[agent] = agent + "_recover"
        stats["override"] += 1
        stats["mode_overrides"] += 1
        stats.setdefault("ovr", []).append([agent, "mode:investigate", "mode:recover"])


def _run_episode(ep, seed, cyborg, env, holder, rule, stats, budget, min_gap, out_dir, hdr):
    agents = _submission().AGENTS
    holder["intercept"] = make_oracle(cyborg, "none" if rule == "O14" else rule,
                                      stats, budget, {}, min_gap, hdr.get("wait_busy", False), hdr.get("engage"), hdr.get("window", 16))
    holder["space"].clear()
    o14_last = {}
    expert = {}
    total = 0.0
    t = 0
    recover_steps = 0
    t0 = time.time()

    obs, _ = env.reset()
    path = Path(out_dir) / f"ep_{ep:05d}.jsonl"
    with open(path, "w") as f:
        f.write(json.dumps({
            "record": "header", "harness": "capture_hmarl", "defender": "H-MARL Expert",
            "harness_sha": HARNESS_SHA, "machine": MACHINE, "episode": ep, "seed": seed,
            "rule": rule, "budget": budget, "min_gap": min_gap,
            "cyborg_version": CYBORG_VERSION, "episode_length": EPISODE_LENGTH, **hdr,
        }) + "\n")

        # Mirrors evaluation.py: 2*EPISODE_LENGTH iterations alternating master and
        # sub-policy phases, done computed over the returned observation keys.
        for _ in range(2 * EPISODE_LENGTH):
            master_phase = any("master" in k for k in obs)
            if master_phase:
                expert = {k[:12]: ("recover" if int(o["action_mask"][1]) == 1 else "investigate")
                          for k, o in obs.items()}          # the expert gate, before any edit
                if rule == "O14":
                    _o14(env, cyborg, obs, stats, min_gap, t, o14_last)
            actions = {n: agents[n].get_action(obs[n], env.action_space(n[:12])) for n in obs}
            if master_phase:
                obs, rew, term, trunc, info = env.step(actions)
            else:
                mode = {k[:12]: k[13:] for k in actions}
                n_comp = sum(len(v) for v in compromised_by_agent(cyborg).values())
                phase = int(cyborg.environment_controller.state.mission_phase)
                n0 = len(stats.get("ovr", []))
                obs, rew, term, trunc, info = env.step(actions)

            done = {n: term.get(n, False) or trunc.get(n, False) for n in obs}
            if all(done.values()):
                break
            if master_phase:
                continue

            note_impacts(cyborg, t)
            r = float(np.mean([v for k, v in rew.items() if "master" not in k]))
            total += r
            stats.setdefault("rew_hist", []).append(r)     # O15r reads the trailing window
            recover_steps += sum(1 for m in mode.values() if m == "recover")
            executed = {n: str(cyborg.get_last_action(n)) for n in BLUE}
            red = {n: str(cyborg.get_last_action(n)) for n in RED}
            red = {k: v for k, v in red.items() if v not in ("None", "[Sleep]")}
            f.write(json.dumps({
                "record": "step", "step": t, "phase": phase, "n_compromised_owned": n_comp,
                "mode": mode, "expert_mode": expert, "actions": executed, "red_action": red,
                "reward": r, "cum_reward": total, "overrides": stats.get("ovr", [])[n0:],
                **({"signal": stats.pop("sig")} if "sig" in stats else {}),
            }) + "\n")
            t += 1

        foot = {
            "record": "footer", "episode": ep, "seed": seed, "total_reward": total,
            "env_steps": t,
            "overrides": stats["override"], "agreements": stats["agree"],
            "translator_calls": stats["calls"], "deferred": stats["deferred"], "busy_skips": stats.get("busy", 0),
            "exhausted": stats["exhausted"],
            "analyses": stats["exec_Analyse"], "restores": stats["exec_Restore"],
            "removes": stats["exec_Remove"], "sleeps": stats["exec_Sleep"],
            "flags_new": stats["flags_new"],
            "latch_tp": stats["tp"], "latch_fp": stats["fp"], "latch_fn": stats["fn"],
            "latch_own": stats["own"],
            "mode_overrides": stats["mode_overrides"], "recover_agent_steps": recover_steps,
            "wall_seconds": round(time.time() - t0, 2),
        }
        for k, v in stats.items():                 # latch_* and anything else the rules count
            if isinstance(v, (int, float)) and k not in foot and k not in (
                    "override", "agree", "calls") and not k.startswith("exec_"):
                foot[k] = v
        f.write(json.dumps(foot) + "\n")
    return foot


def capture_episode(ep, a):
    """Per-episode mode: one fresh CybORG, reseeded sampling, independent of scheduling."""
    _submission()                                   # load before seeding, so it never moves the RNG
    seed = a["base_seed"] + ep
    pseed = (a["base_seed"] if a["policy_seed"] is None else a["policy_seed"]) + ep
    torch.manual_seed(pseed); np.random.seed(pseed); random.seed(pseed)
    cyborg, env = _make_env(seed, _red_class(a["red"]))
    holder = _install(env)
    hdr = {"red_agent": a["red"], "seed_mode": "episode", "policy_seed": pseed,
           "workers": a["workers"], "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"]}
    foot = _run_episode(ep, seed, cyborg, env, holder, a["rule"], Counter(),
                        a["budget"], a["min_gap"], a["out"], hdr)
    print(f"episode {ep} seed {seed} total {foot['total_reward']:.2f} "
          f"overrides {foot['overrides']} wall {foot['wall_seconds']}s", flush=True)
    return foot


def capture_compat(a):
    """evaluation.py order: seed, load policies, one CybORG, reset per episode."""
    s = a["base_seed"]
    torch.manual_seed(s); np.random.seed(s); random.seed(s)
    _submission()
    cyborg, env = _make_env(s, _red_class(a["red"]))
    holder = _install(env)
    foots = []
    for ep in range(a["episodes"]):
        hdr = {"red_agent": a["red"], "seed_mode": "compat", "policy_seed": s, "workers": 0, "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"]}
        foots.append(_run_episode(ep, s, cyborg, env, holder, a["rule"], Counter(),
                                  a["budget"], a["min_gap"], a["out"], hdr))
        tot = [x["total_reward"] for x in foots]
        print(f"episode {ep} total {tot[-1]:.2f} running mean {np.mean(tot):.2f}", flush=True)
    return foots


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rule", default="none", choices=RULES)
    ap.add_argument("--red", default="FiniteStateRedAgent")
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--base-seed", type=int, default=0)
    ap.add_argument("--policy-seed", type=int, default=None,
                    help="per-episode mode: reseed sampling with this+ep while the environment keeps base+ep")
    ap.add_argument("--budget", type=int, default=77)
    ap.add_argument("--min-gap", type=int, default=0)
    ap.add_argument("--wait-busy", action="store_true", help="a directive to a busy agent waits for its next free tick")
    ap.add_argument("--engage", type=float, default=None, help="O15 threshold (see oracle_rules)")
    ap.add_argument("--window", type=int, default=16, help="O15r and O15a trailing window in simulator steps")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--compat", action="store_true", help="mirror evaluation.py seeding, sequential")
    ap.add_argument("--out", required=True)
    a = vars(ap.parse_args())
    os.makedirs(a["out"], exist_ok=True)
    print(f"capture_hmarl {HARNESS_SHA[:12]} on {MACHINE}  h3p={H3P}  rule={a['rule']} "
          f"red={a['red']} gap={a['min_gap']} budget={a['budget']} "
          f"mode={'compat' if a['compat'] else 'episode'}", flush=True)

    if a["compat"]:
        foots = capture_compat(a)
    elif a["workers"] > 1:
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=a["workers"],
                                 mp_context=mp.get_context("spawn")) as ex:
            foots = list(ex.map(capture_episode, range(a["episodes"]),
                                [a] * a["episodes"]))
    else:
        foots = [capture_episode(ep, a) for ep in range(a["episodes"])]

    tot = np.array([f["total_reward"] for f in foots])
    sd = tot.std(ddof=1) if len(tot) > 1 else 0.0
    print(f"{a['rule']} {a['red']} episodes {len(tot)} mean {tot.mean():.2f} stdev {sd:.2f} "
          f"overrides/ep {np.mean([f['overrides'] for f in foots]):.1f} "
          f"agreements/ep {np.mean([f['agreements'] for f in foots]):.1f} "
          f"recover_agent_steps/ep {np.mean([f['recover_agent_steps'] for f in foots]):.1f}")


if __name__ == "__main__":
    main()
