"""Capture CAGE 4 episodes to JSONL with full per-step state.

Usage:
    python3 /work/scripts/capture.py --episodes 5 --base-seed 0 \
        --out /work/data/traces/pilot
"""
import argparse, json, os, random, sys, time
from pathlib import Path

sys.path.insert(0, "/opt/cage/cage-4-submission")

import numpy as np
import torch

from CybORG import CybORG, CYBORG_VERSION
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from submission import Submission

EPISODE_LENGTH = 500
BLUE = [f"blue_agent_{i}" for i in range(5)]


def jsonable(x):
    """Coerce CybORG objects into something json can write."""
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [jsonable(v) for v in x]
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def red_presence(state):
    """Tier 3 ground truth. Which hosts hold red sessions, and how many."""
    out = {}
    for hostname, host in state.hosts.items():
        red = {a: len(s) for a, s in host.sessions.items()
               if a.startswith("red") and s}
        if red:
            out[hostname] = red
    return out


def red_session_count(state):
    return {a: len(s) for a, s in state.sessions.items()
            if a.startswith("red")}


def capture_episode(ep, base_seed, out_dir, agents):
    seed = base_seed + ep
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=FiniteStateRedAgent,
        steps=EPISODE_LENGTH,
    )
    cyborg = CybORG(sg, "sim", seed=seed)
    env = Submission.wrap(cyborg)
    state = cyborg.environment_controller.state

    wrapped_obs, _ = env.reset()
    for a in agents.values():
        if hasattr(a, "reset"):
            a.reset()

    path = Path(out_dir) / f"ep_{ep:05d}.jsonl"
    total = 0.0
    t0 = time.time()

    with open(path, "w") as f:
        f.write(json.dumps({
            "record": "header",
            "episode": ep,
            "seed": seed,
            "cyborg_version": CYBORG_VERSION,
            "scenario": "Scenario4",
            "episode_length": EPISODE_LENGTH,
            "agent_name": Submission.NAME,
            "agent_team": Submission.TEAM,
            "deterministic": False,
            "blue_agents": BLUE,
            "hosts": sorted(state.hosts.keys()),
            "phase_rewards": jsonable(
                cyborg.environment_controller.team_reward_calculators
                ["Blue"]["BlueRewardMachine"].phase_rewards),
            "host_subnet": {h: str(s) for h, s
                            in state.hostname_subnet_map.items()},
        }) + "\n")

        for step in range(EPISODE_LENGTH):
            phase = state.mission_phase

            actions = {}
            for name in BLUE:
                actions[name] = agents[name].get_action(
                    wrapped_obs[name], env.action_space(name)
                )

            wrapped_obs, rew, term, trunc, info = env.step(actions)


            raw_obs = {n: jsonable(cyborg.get_observation(n)) for n in BLUE}
            executed = {n: str(cyborg.get_last_action(n)) for n in BLUE}
            step_reward = float(rew["blue_agent_0"])
            total += step_reward

            f.write(json.dumps({
                "record": "step",
                "episode": ep,
                "step": step,
                "phase": int(phase),
                "obs": raw_obs,
                "action_index": {n: jsonable(actions[n]) for n in BLUE},
                "action": executed,
                "reward": {n: float(v) for n, v in rew.items()},
                "step_reward": step_reward,
                "cumulative_reward": total,
                "truth": {
                    "red_hosts": red_presence(state),
                    "red_sessions": red_session_count(state),
                },
                "done": bool(term.get("blue_agent_0", False)
                             or trunc.get("blue_agent_0", False)),
            }) + "\n")

            if term.get("blue_agent_0") or trunc.get("blue_agent_0"):
                break

        f.write(json.dumps({
            "record": "footer",
            "episode": ep,
            "steps": step + 1,
            "total_reward": total,
            "wall_seconds": round(time.time() - t0, 2),
        }) + "\n")

    return total, step + 1, time.time() - t0


def main():
    p = argparse.ArgumentParser("CAGE 4 trace capture")
    p.add_argument("--episodes", type=int, default=5)
    p.add_argument("--base-seed", type=int, default=0)
    p.add_argument("--out", default="/work/data/traces/pilot")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    agents = Submission.AGENTS

    print(f"CybORG v{CYBORG_VERSION}, Scenario4")
    print(f"Agent: {Submission.NAME} / {Submission.TEAM}")
    print(f"Writing to {args.out}")

    totals = []
    for ep in range(args.episodes):
        r, steps, secs = capture_episode(ep, args.base_seed, args.out, agents)
        totals.append(r)
        print(f"  ep {ep:>4}  seed {args.base_seed + ep:>5}  "
              f"steps {steps:>4}  reward {r:>9.2f}  {secs:>6.1f}s")

    print(f"\nmean {sum(totals)/len(totals):.2f} over {len(totals)} episodes")


if __name__ == "__main__":
    main()
