#!/usr/bin/env python3
"""KEEP's network posture, read off the live action objects (the trace strings carry no
arguments for BlockTrafficZone / AllowTrafficZone). Runs N episodes of the shipped policy and
reports, per mission phase, the fraction of agent-steps each zone pair is held blocked, the
block/allow event counts, and where decoys go.

usage (inside cage-keep:dev, from /opt/cage/cage-4-submission):
  python3 /work/tools_diag_posture.py --red FSRedAgentWrecker --episodes 5
"""
import argparse, importlib, random, sys
from collections import Counter, defaultdict
sys.path.insert(0, "/opt/cage/cage-4-submission"); sys.path.insert(0, "/work/scripts")
import numpy as np, torch
from CybORG import CybORG
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from submission import Submission
from oracle_rules import EPISODE_LENGTH, BLUE


def zones(act):
    d = {k: v for k, v in vars(act).items() if isinstance(v, str)}
    f = d.get("from_subnet") or d.get("from_zone"); t = d.get("to_subnet") or d.get("to_zone")
    if f is None or t is None:
        vals = [v for k, v in d.items() if k not in ("agent",)]
        f, t = (vals + [None, None])[:2]
    return f, t, d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--red", default="FSRedAgentWrecker"); ap.add_argument("--episodes", type=int, default=5)
    a = ap.parse_args()
    rc = getattr(importlib.import_module(f"CybORG.Agents.SimpleAgents.{a.red}"), a.red)
    held = defaultdict(Counter)        # phase -> pair -> agent-steps blocked
    steps_in_phase = Counter()
    events = Counter()                 # (kind, pair) -> count
    decoy_role = Counter(); decoy_zone = Counter()
    shown = Counter()
    for ep in range(a.episodes):
        seed = ep
        torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
        sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, green_agent_class=EnterpriseGreenAgent,
                                         red_agent_class=rc, steps=EPISODE_LENGTH)
        cyborg = CybORG(sg, "sim", seed=seed); env = Submission.wrap(cyborg); agents = Submission.AGENTS
        obs, _ = env.reset()
        for ag in agents.values():
            if hasattr(ag, "reset"): ag.reset()
        blocked = set()
        for step in range(EPISODE_LENGTH):
            actions = {n: agents[n].get_action(obs[n], env.action_space(n)) for n in BLUE}
            obs, rew, term, trunc, info = env.step(actions)
            phase = int(cyborg.environment_controller.state.mission_phase)
            for n in BLUE:
                la = cyborg.get_last_action(n)
                if isinstance(la, list):
                    la = la[0] if la else None
                if la is None:
                    continue
                name = type(la).__name__
                if name in ("BlockTrafficZone", "AllowTrafficZone"):
                    f, t, d = zones(la)
                    if shown[name] < 2:
                        shown[name] += 1; print(f"  sample {name}: {d}")
                    pair = (f, t)
                    events[(name, pair)] += 1
                    if name == "BlockTrafficZone":
                        blocked.add(pair)
                    else:
                        blocked.discard(pair)
                elif name == "DeployDecoy":
                    h = getattr(la, "hostname", "") or ""
                    decoy_role["server" if "server" in h else "user"] += 1
                    decoy_zone[h.rsplit("_subnet", 1)[0] if "_subnet" in h else h] += 1
            steps_in_phase[phase] += 1
            for pair in blocked:
                held[phase][pair] += 1
            if term.get("blue_agent_0") or trunc.get("blue_agent_0"):
                break
    print(f"\n{a.red}, {a.episodes} episodes")
    for ph in sorted(steps_in_phase):
        n = steps_in_phase[ph]
        print(f"phase {ph}: {n} steps")
        for pair, c in held[ph].most_common(12):
            print(f"    blocked {c / n:5.2f} of steps  {pair[0]} -> {pair[1]}")
    print("block/allow events per episode:")
    for (kind, pair), c in sorted(events.items(), key=lambda kv: -kv[1])[:16]:
        print(f"    {c / a.episodes:6.1f}  {kind:17} {pair[0]} -> {pair[1]}")
    print("decoys per episode by role:", {k: round(v / a.episodes, 1) for k, v in decoy_role.items()})
    print("decoys per episode by zone:", {k: round(v / a.episodes, 1) for k, v in decoy_zone.most_common()})


if __name__ == "__main__":
    main()
