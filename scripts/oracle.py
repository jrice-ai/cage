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
import wrapper.graph_wrapper as _gw
from wrapper.globals import MY_SUBNETS, MAX_HOSTS, MAX_ACTIONS, NODE_ACTIONS
from oracle_rules import (make_oracle, note_impacts, owned_hosts, compromised_by_agent, subnet_of,
                          EPISODE_LENGTH, BLUE, RED, OWNER, EXPENSIVE, HARNESS_SHA, MACHINE,
                          _IMPACT_SEEN, _HOSTS_CACHE)


def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False, engage=None, window=16, queue=None, noise=None, agents=None, noise_seed=0):
    """Wrap action_translator so overrides slot in before execution."""
    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue,
                            noise=noise, agents=agents, noise_seed=noise_seed)
    original = env.action_translator
    def patched(agent_name, a_id):
        base = original(agent_name, a_id)
        if "pol" in stats:   # --log-policy: the policy's own directive, before any rule
            stats["pol"][agent_name] = None if a_id is None else str(base)
        return intercept(agent_name, base)
    env.action_translator = patched


def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent", min_gap=0, workers=0, wait_busy=False, engage=None, window=16, queue=None, noise=None, only_agents=None, policy_seed=None, log_policy=False):
    seed = base_seed + ep
    pseed = seed if policy_seed is None else policy_seed + ep   # as capture.py: the policy stream can be redrawn on the same environment seed
    torch.manual_seed(pseed); np.random.seed(seed); random.seed(seed)

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
    if log_policy:
        stats["pol"] = {}
    stats["dact"] = []      # rule defender's per-step reasons; emptied into each step record
    decoys = {}
    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue,
                   noise=noise, agents=only_agents, noise_seed=seed)
    if rule in ("O11", "O17"):
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
            "record": "header", "harness_sha": HARNESS_SHA, "machine": MACHINE, "weights": os.environ.get("KEEP_WEIGHTS", "shipped"), "busy": getattr(_gw, "_KEEP_BUSY", "unpatched"), "log_policy": log_policy, "red_agent": _rc.__name__, "episode": ep, "seed": seed, "policy_seed": policy_seed,
            "rule": rule, "budget": budget, "min_gap": min_gap, "workers": workers, "wait_busy": wait_busy, "engage": engage, "window": window, "queue": queue, "noise": noise, "agents": only_agents, "cyborg_version": CYBORG_VERSION,
            "episode_length": EPISODE_LENGTH,
        }) + "\n")

        for step in range(EPISODE_LENGTH):
            st = cyborg.environment_controller.state
            phase = st.mission_phase
            n_comp = sum(len(v) for v in compromised_by_agent(cyborg).values())

            busy = [n for n in BLUE if cyborg.environment_controller.actions_in_progress.get(n) is not None]
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
            stats.setdefault("rew_hist", []).append(step_reward)   # O15r reads the trailing window

            f.write(json.dumps({
                "record": "step", "episode": ep, "step": step,
                "phase": int(phase), "action": executed,
                "red_action": red_acts,
                "step_reward": step_reward, "cumulative_reward": total,
                "n_compromised_owned": n_comp,
                "overrides": stats.pop("ovr", []),
                "defender": stats.get("dact") or [],
                **({"signal": stats.pop("sig")} if "sig" in stats else {}),
                **({"policy": stats["pol"], "busy": busy} if log_policy else {}),
            }) + "\n")
            if log_policy:
                stats["pol"] = {}
            stats["dact"] = []

            if term.get("blue_agent_0") or trunc.get("blue_agent_0"):
                break

        f.write(json.dumps({
            "record": "footer", "episode": ep, "steps": step + 1,
            "total_reward": total, "overrides": stats["override"], "translator_calls": stats["calls"],
            "agreements": stats["agree"],
            "deferred": stats.get("deferred", 0),
            "busy_skips": stats.get("busy", 0),
            "engaged": stats.get("engaged", 0), "engaged_hit": stats.get("engaged_hit", 0),
            "quiet_comp": stats.get("quiet_comp", 0), "signal_sum": stats.get("signal_sum", 0.0),
            "signal_ticks": stats.get("signal_ticks", 0), "alerts": stats.get("alerts", 0),
            "queued": stats.get("queued", 0), "queue_fired": stats.get("queue_fired", 0),
            "queue_stale": stats.get("queue_stale", 0), "queue_wait": stats.get("queue_wait", 0),
            "o16_confirmed": stats.get("o16_confirmed", 0), "o15h_clean": stats.get("o15h_clean", 0),
            "exec_clean": stats.get("exec_clean", 0), "h_skip": stats.get("h_skip", 0), "h_wrong": stats.get("h_wrong", 0),
            "eyes_tp": stats.get("eyes_tp", 0), "eyes_fp": stats.get("eyes_fp", 0), "eyes_fn": stats.get("eyes_fn", 0), "eyes_clean": stats.get("eyes_clean", 0),
            "sup_tp": stats.get("sup_tp", 0), "sup_fp": stats.get("sup_fp", 0), "sup_fn": stats.get("sup_fn", 0), "sup_own": stats.get("sup_own", 0),
            "o17_clean": stats.get("o17_clean", 0),
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


def _rule_arg(s):
    from oracle_rules import KNOWN_RULES, DEFENDERS
    d, _, r = s.partition("+")
    if s in KNOWN_RULES or (d in DEFENDERS and (r == "" or r in KNOWN_RULES)):
        return s
    raise argparse.ArgumentTypeError(f"unknown rule {s}")


def main():
    p = argparse.ArgumentParser("Oracle arms")
    p.add_argument("--min-gap", type=int, default=0, help="per-agent minimum steps between overrides")
    p.add_argument("--wait-busy", action="store_true", help="a directive to a busy agent waits for its next free tick instead of being dropped by the simulator; rule defenders sleep while busy")
    p.add_argument("--engage", type=float, default=None, help="O15 threshold: O15r loss over the window, O15a alerts over the window, O15c compromised owned hosts")
    p.add_argument("--window", type=int, default=16, help="O15r and O15a trailing window in simulator steps")
    p.add_argument("--queue", choices=["first", "last"], default=None, help="with --wait-busy: decide on a busy tick and hold the directive for the free tick (first: keep the first decision; last: replace it each busy tick)")
    p.add_argument("--recall", type=float, default=None, help="O1 through a detector: probability a compromise is ever shown (drawn per compromise)")
    p.add_argument("--false-alarm", type=float, default=None, help="O1 through a detector: stationary share of clean owned hosts flagged")
    p.add_argument("--delay", type=int, default=None, help="with --queue first: steps from a person's decision to the click landing")
    p.add_argument("--wrong", type=float, default=None, help="with --queue first: probability the click lands on another owned host")
    p.add_argument("--skip", type=float, default=None, help="with --queue first: probability a person lets a prompt pass")
    p.add_argument("--agents", default=None, help="supervise only these agents, e.g. 0,4")
    p.add_argument("--rule", default="O1", type=_rule_arg,
                   help="a supervisor rule on KEEP, or a rule defender (R1 to R4, RT), optionally with a supervisor rule on top (R4+O1)")
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--base-seed", type=int, default=0)
    p.add_argument("--policy-seed", type=int, default=None, help="torch seed base for the policy; default ties it to the environment seed")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--budget", type=int, default=77,
                   help="Max overrides per episode for O5")
    p.add_argument("--red", default="FiniteStateRedAgent")
    p.add_argument("--log-policy", action="store_true", help="record each agent's directive before any rule, and the agents busy when each step began")
    p.add_argument("--out", default="/work/data/traces/oracle")
    a = p.parse_args()
    noise = {k: v for k, v in (("recall", a.recall), ("false", a.false_alarm), ("delay", a.delay),
                               ("wrong", a.wrong), ("skip", a.skip)) if v is not None} or None
    agents = [int(x) for x in a.agents.split(",")] if a.agents else None

    os.makedirs(a.out, exist_ok=True)
    print(f"Rule {a.rule}, {a.episodes} episodes, {a.workers} workers")

    res = Parallel(n_jobs=a.workers, prefer="processes")(
        delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red, a.min_gap, a.workers, a.wait_busy, a.engage, a.window, a.queue, noise, agents, a.policy_seed, a.log_policy)
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
