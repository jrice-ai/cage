#!/usr/bin/env python3
"""How many supervisor overrides and rule-defender proposals the simulator actually executed.

CC4 actions have durations (Restore 5, Remove 3, Analyse 2, DeployDecoy 2) and an action handed to
an agent that is mid-action is dropped (SimulationController: actions_in_progress is set only when
empty). The step record's "action" is cyborg.get_last_action, the action executed that step, so a
proposal at step t of an action with duration d is confirmed by an executed action of the same
type on the same host by the same agent at step t + d - 1 (exactly; held arms match at that step and nowhere else, and the window of 0 .. d + 1 used
before 2026-10-12 also caught the agent's own later actions on the same host). Everything else was dropped.

usage: python3 tools_dropped.py DIR [DIR ...] [--episodes N]
Reports, per arm: overrides by type (proposed, executed, share), defender proposals by kind
(proposed, executed, share), and the agents' busy share of agent-steps implied by executed
multi-tick actions.
"""
import glob, json, os, sys
from collections import Counter

DUR = {"Restore": 5, "Remove": 3, "Analyse": 2, "DeployDecoy": 2, "Sleep": 1, "Monitor": 1,
       "BlockTrafficZone": 1, "AllowTrafficZone": 1}
KIND = {"alerts": "Restore", "strict": "Restore", "truth": "Restore", "remove": "Remove",
        "triage": "Analyse", "decoy": "DeployDecoy"}


def _acts(r):
    return r.get("action") or r.get("actions") or {}      # oracle.py names it "action", capture_hmarl.py "actions"


def executed_at(steps, i, agent, typ, host):
    d = DUR.get(typ, 1)
    k = d - 1                                   # an accepted directive completes at exactly t + d - 1
    if i + k >= len(steps):
        return None
    a = _acts(steps[i + k]).get(agent, "")
    if a.startswith(f"[{typ} {host}") or (host == "" and a.startswith(f"[{typ}")):
        return k
    return None


def analyse(d, max_eps):
    prop = Counter(); ok = Counter(); busy = 0; agent_steps = 0; n = 0
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))[:max_eps]:
        rows = [json.loads(l) for l in open(f) if l.strip()]
        steps = [r for r in rows if r.get("record") == "step"]
        if not steps or rows[-1].get("record") != "footer":
            continue
        n += 1
        for i, r in enumerate(steps):
            for agent, a in _acts(r).items():
                agent_steps += 1
                typ = a.strip("[]").split(" ")[0]
                busy += max(0, DUR.get(typ, 1) - 1)
            for agent, frm, to in r.get("overrides", []):
                typ, _, host = to.partition(":")
                prop[("override", typ)] += 1
                if executed_at(steps, i, agent, typ, host) is not None:
                    ok[("override", typ)] += 1
            for agent, why, host in r.get("defender", []):
                if why not in KIND:
                    continue
                typ = KIND[why]
                prop[("defender", why)] += 1
                if executed_at(steps, i, agent, typ, host) is not None:
                    ok[("defender", why)] += 1
    if not n:
        print(f"{os.path.basename(d)}: no complete episodes"); return
    print(f"{os.path.basename(d)}: {n} episodes; busy share of agent-steps (ticks inside executed multi-tick actions) {busy / agent_steps:.3f}")
    for key in sorted(prop):
        p, e = prop[key], ok[key]
        print(f"  {key[0]:8} {key[1]:12} proposed {p / n:7.1f}/ep  executed {e / n:7.1f}/ep  share {e / p:.3f}")


def main():
    argv = sys.argv[1:]; max_eps = 10 ** 9
    if "--episodes" in argv:
        i = argv.index("--episodes"); max_eps = int(argv[i + 1]); del argv[i:i + 2]
    if not argv:
        sys.exit(__doc__)
    for d in argv:
        analyse(d if os.path.isdir(d) else os.path.join("data", "traces", d), max_eps)


if __name__ == "__main__":
    main()
