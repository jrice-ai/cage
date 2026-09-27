#!/usr/bin/env python3
"""What the blue observation gives a rule defender to act on. Runs episodes inside
cage-keep:dev and tabulates, per agent-step and host:
  passive  the host is named by a substantive observation entry (the reset listing at step 0
           excluded), counted by how many times it has been named since the host's last
           Restore or Remove
  files    the max Files Density reported for the host this step (Analyse results)
  truth    the host holds a red session
so the precision of each candidate restore criterion, its coverage of compromised host-steps,
and the yield of a look can be read before a rule is written. Counts are summed over episodes
(seeds --seed .. --seed + --episodes - 1); one line per episode, then the aggregate.

usage (inside the container, from /opt/cage/cage-4-submission):
  python3 /work/tools_diag_eyes.py --red FSRedAgentWrecker --rule none --seed 0 --episodes 20
  python3 /work/tools_diag_eyes.py --red FSRedAgentWrecker --rule R1 --seed 0 --episodes 20
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


class Tally:
    def __init__(self):
        self.named_comp = Counter()                       # passive criterion, reset listing excluded
        self.reset_named = 0
        self.dens = defaultdict(Counter)                  # is_comp -> density bucket counts, on Analyse results
        self.repeat = defaultdict(lambda: [0, 0])         # times named since last restore -> [events, compromised]
        self.cover = Counter(); self.comp_steps = 0       # compromised host-steps with >= k namings
        self.dstats = Counter()                           # defender d_* counts
        self.episodes = 0; self.steps = 0

    def add(self, o):
        self.named_comp.update(o.named_comp); self.reset_named += o.reset_named
        for k, c in o.dens.items():
            self.dens[k].update(c)
        for k, v in o.repeat.items():
            self.repeat[k][0] += v[0]; self.repeat[k][1] += v[1]
        self.cover.update(o.cover); self.comp_steps += o.comp_steps
        self.dstats.update(o.dstats); self.episodes += o.episodes; self.steps += o.steps

    def report(self, head):
        tot = sum(self.named_comp.values())
        print(f"{head}: {self.episodes} episode(s), {self.steps} steps; reset listing named {self.reset_named} host(s) (excluded below)")
        print(f"  passive: {tot} host-namings after step 0, {self.named_comp[True]} on compromised hosts, precision {self.named_comp[True] / tot if tot else float('nan'):.3f}")
        for k in sorted(self.repeat):
            n_, c_ = self.repeat[k]
            print(f"    named {'>=' if k == 5 else ''}{k} time(s) since last restore: {n_:6} events, {c_:6} compromised, precision {c_ / n_ if n_ else float('nan'):.3f}")
        cs = self.comp_steps
        print(f"  coverage: of {cs} compromised host-steps, named >=1: {self.cover[1] / cs if cs else 0:.3f}, "
              f">=2: {self.cover[2] / cs if cs else 0:.3f}, >=3: {self.cover[3] / cs if cs else 0:.3f}, >=4: {self.cover[4] / cs if cs else 0:.3f}")
        for is_c in (True, False):
            d = self.dens[is_c]; s = sum(d.values())
            print(f"  Analyse result on {'compromised' if is_c else 'clean'} host: {s} results; max Density none {d['none']} / 0 {d['0']} / <0.5 {d['<0.5']} / <0.9 {d['<0.9']} / >=0.9 {d['>=0.9']}")
        if self.dstats:
            print("  defender counts: " + ", ".join(f"{k}={v}" for k, v in sorted(self.dstats.items())))


def run_episode(red, rule, seed):
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    rc = getattr(importlib.import_module(f"CybORG.Agents.SimpleAgents.{red}"), red)
    sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, green_agent_class=EnterpriseGreenAgent,
                                     red_agent_class=rc, steps=EPISODE_LENGTH)
    cyborg = CybORG(sg, "sim", seed=seed); env = Submission.wrap(cyborg); agents = Submission.AGENTS
    stats = Counter(); stats["dact"] = []
    icp = make_oracle(cyborg, rule, stats, 99999, {}, 0)
    orig = env.action_translator
    env.action_translator = lambda n, i: icp(n, orig(n, i))
    obs, _ = env.reset()
    for ag in agents.values():
        if hasattr(ag, "reset"): ag.reset()

    t = Tally(); t.episodes = 1
    seen = defaultdict(Counter)                               # agent -> host -> times named since last restore
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
                    t.reset_named += 1
                    continue
                is_c = h in comp
                t.named_comp[is_c] += 1
                seen[n][h] += 1; k = min(seen[n][h], 5)
                t.repeat[k][0] += 1; t.repeat[k][1] += is_c
                fl = v.get("Files") or []
                ds = [float(x.get("Density") or 0) for x in fl if isinstance(x, dict)]
                if la is not None and type(la).__name__ == "Analyse" and getattr(la, "hostname", None) == h:
                    mx = max(ds) if ds else -1
                    b = "none" if mx < 0 else ("0" if mx == 0 else ("<0.5" if mx < 0.5 else ("<0.9" if mx < 0.9 else ">=0.9")))
                    t.dens[is_c][b] += 1
            for h in own:
                if h in comp:
                    t.comp_steps += 1
                    k = seen[n].get(h, 0)
                    for j in (1, 2, 3, 4):
                        if k >= j:
                            t.cover[j] += 1
        actions = {n: agents[n].get_action(obs[n], env.action_space(n)) for n in BLUE}
        obs, rew, term, trunc, info = env.step(actions)
        for n in BLUE:
            last_act[n] = cyborg.get_last_action(n)
        stats["dact"] = []
        if term.get("blue_agent_0") or trunc.get("blue_agent_0"):
            break
    t.steps = step + 1
    for k, v in stats.items():
        if k.startswith("d_"):
            t.dstats[k] += v
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--red", default="FSRedAgentWrecker"); ap.add_argument("--rule", default="none")
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--episodes", type=int, default=1)
    a = ap.parse_args()
    total = Tally()
    for seed in range(a.seed, a.seed + a.episodes):
        t = run_episode(a.red, a.rule, seed)
        tot = sum(t.named_comp.values())
        print(f"episode seed {seed}: namings {tot}, precision {t.named_comp[True] / tot if tot else float('nan'):.3f}, "
              f"compromised host-steps {t.comp_steps}, confirmed files on compromised {t.dens[True]['>=0.9']}, on clean {t.dens[False]['>=0.9']}", flush=True)
        total.add(t)
    total.report(f"{a.red} rule {a.rule} seeds {a.seed}-{a.seed + a.episodes - 1}")


if __name__ == "__main__":
    main()
