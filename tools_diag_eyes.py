#!/usr/bin/env python3
"""What the blue observation gives a rule defender to act on. Runs single episodes inside
cage-keep:dev and tabulates, per agent-step and host:
  passive  the host is named by a substantive observation entry (the O2e criterion)
  files    the max Files Density reported for the host this step (Analyse results)
  truth    the host holds a red session
so the precision of each candidate restore criterion can be read before a rule is written.

usage (inside the container, from /opt/cage/cage-4-submission):
  python3 /work/tools_diag_eyes.py --red FSRedAgentWrecker --rule none --seed 0
  python3 /work/tools_diag_eyes.py --red FSRedAgentWrecker --rule R1 --seed 0
"""
import argparse, importlib, random, sys
from collections import Counter, defaultdict
sys.path.insert(0, "/opt/cage/cage-4-submission"); sys.path.insert(0, "/work/scripts")
import numpy as np, torch
from CybORG import CybORG
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from submission import Submission
from oracle_rules import make_oracle, compromised_by_agent, owned_hosts, EPISODE_LENGTH, BLUE

META = {"success", "action", "message"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--red", default="FSRedAgentWrecker"); ap.add_argument("--rule", default="none")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    torch.manual_seed(a.seed); np.random.seed(a.seed); random.seed(a.seed)
    rc = getattr(importlib.import_module(f"CybORG.Agents.SimpleAgents.{a.red}"), a.red)
    sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, green_agent_class=EnterpriseGreenAgent,
                                     red_agent_class=rc, steps=EPISODE_LENGTH)
    cyborg = CybORG(sg, "sim", seed=a.seed); env = Submission.wrap(cyborg); agents = Submission.AGENTS
    stats = Counter(); stats["dact"] = []
    icp = make_oracle(cyborg, a.rule, stats, 99999, {}, 0)
    orig = env.action_translator
    env.action_translator = lambda n, i: icp(n, orig(n, i))
    obs, _ = env.reset()
    for ag in agents.values():
        if hasattr(ag, "reset"): ag.reset()

    named_comp = Counter()                                    # passive criterion, reset listing excluded
    reset_named = 0
    dens = defaultdict(Counter)                               # is_comp -> density bucket counts, on Analyse results
    repeat = defaultdict(lambda: [0, 0])                      # times named since last restore -> [events, compromised]
    seen = defaultdict(Counter)                               # agent -> host -> times named since last restore
    cover = Counter(); comp_steps = 0                         # compromised host-steps with >= k namings
    last_act = {}
    for step in range(EPISODE_LENGTH):
        comp = {c[0] for v in compromised_by_agent(cyborg).values() for c in v}
        for n in BLUE:
            o = cyborg.get_observation(n) or {}
            own = set(owned_hosts(cyborg, n))
            la = last_act.get(n)
            if isinstance(la, list):
                la = la[0] if la else None
            if la is not None and type(la).__name__ in ("Restore", "Remove"):
                seen[n].pop(getattr(la, "hostname", None), None)
            for h, v in o.items():
                if h in META or not isinstance(v, dict) or h not in own:
                    continue
                if step == 0:
                    reset_named += 1
                    continue
                is_c = h in comp
                named_comp[is_c] += 1
                seen[n][h] += 1; k = min(seen[n][h], 5)
                repeat[k][0] += 1; repeat[k][1] += is_c
                fl = v.get("Files") or []
                ds = [float(x.get("Density") or 0) for x in fl if isinstance(x, dict)]
                if la is not None and type(la).__name__ == "Analyse" and getattr(la, "hostname", None) == h:
                    mx = max(ds) if ds else -1
                    b = "none" if mx < 0 else ("0" if mx == 0 else ("<0.5" if mx < 0.5 else ("<0.9" if mx < 0.9 else ">=0.9")))
                    dens[is_c][b] += 1
            for h in own:
                if h in comp:
                    comp_steps += 1
                    k = seen[n].get(h, 0)
                    for j in (1, 2, 3, 4):
                        if k >= j:
                            cover[j] += 1
        actions = {n: agents[n].get_action(obs[n], env.action_space(n)) for n in BLUE}
        obs, rew, term, trunc, info = env.step(actions)
        for n in BLUE:
            last_act[n] = cyborg.get_last_action(n)
        stats["dact"] = []
        if term.get("blue_agent_0") or trunc.get("blue_agent_0"):
            break

    tot = sum(named_comp.values())
    print(f"{a.red} rule {a.rule} seed {a.seed}: {step + 1} steps; reset listing named {reset_named} hosts (excluded below)")
    print(f"  passive: {tot} host-namings after step 0, {named_comp[True]} on compromised hosts, precision {named_comp[True] / tot if tot else float('nan'):.3f}")
    for k in sorted(repeat):
        n_, c_ = repeat[k]
        print(f"    named {'>=' if k == 5 else ''}{k} time(s) since last restore: {n_:5} events, precision {c_ / n_ if n_ else float('nan'):.3f}")
    print(f"  coverage: of {comp_steps} compromised host-steps, named >=1: {cover[1] / comp_steps if comp_steps else 0:.3f}, "
          f">=2: {cover[2] / comp_steps if comp_steps else 0:.3f}, >=3: {cover[3] / comp_steps if comp_steps else 0:.3f}, >=4: {cover[4] / comp_steps if comp_steps else 0:.3f}")
    for is_c in (True, False):
        d = dens[is_c]; s = sum(d.values())
        print(f"  Analyse result on {'compromised' if is_c else 'clean'} host: {s} results; max Density none {d['none']} / 0 {d['0']} / <0.5 {d['<0.5']} / <0.9 {d['<0.9']} / >=0.9 {d['>=0.9']}")
    print(f"  defender counts: " + ", ".join(f"{k}={v}" for k, v in sorted(stats.items()) if k.startswith("d_")))


if __name__ == "__main__":
    main()
