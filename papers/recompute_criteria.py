#!/usr/bin/env python3
"""Recovery criteria on the step before completion. The record holds executed actions, and an action
appears at the step it completes, so an action recorded at step t is scored against the true state and
the latched evidence set of the record at t-1, the last state before it took effect (the step record stores post-step state; capture.py line 171 then 201).
  truth : the host held a red session in the previous step's truth.red_hosts
  latch : the host was in the agent's latched evidence set built from observations through t-1
Also the O1 rule's target at each KEEP Restore step (first compromised owned host, previous-step truth).
usage: python3 recompute_criteria.py DIR [--episodes N]"""
import glob, json, os, sys
from collections import Counter

argv = sys.argv[1:]; max_eps = 10**9
if "--episodes" in argv:
    i = argv.index("--episodes"); max_eps = int(argv[i+1]); del argv[i:i+2]
d = argv[0] if os.path.isdir(argv[0]) else os.path.join("data", "traces", argv[0])
META = {"success", "message", "action"}
OWNER = {sn: f"blue_agent_{int(a)}" for a, sns in json.load(open(os.path.expanduser("~/cage/scripts/cc4_subnets.json"))).items() for sn in sns}
def owner(h):
    for sn, ag in OWNER.items():
        if h.startswith(sn): return ag
    return None

c = Counter(); n = 0; red_share = []; red_owned = []; nhosts = nowned = None; rule_t = rule_l = 0
for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))[:max_eps]:
    rows = [json.loads(l) for l in open(f) if l.strip()]
    if rows[-1].get("record") != "footer": continue
    hdr = rows[0]; n += 1
    if nhosts is None and isinstance(hdr.get("hosts"), list): nhosts = len(hdr["hosts"]); nowned = sum(1 for h in hdr["hosts"] if owner(h))
    order = {h: i for i, h in enumerate(hdr.get("hosts") or [])}
    flagged = {}; prev_red = set()
    for r in rows:
        if r.get("record") != "step": continue
        decision_flagged = {a: set(v) for a, v in flagged.items()}       # evidence through t-1
        red_now = set((r.get("truth") or {}).get("red_hosts") or [])
        if nhosts: red_share.append(len(red_now) / nhosts)
        if nowned: red_owned.append(sum(1 for h in red_now if owner(h)) / nowned)
        for agent, a in (r.get("action") or {}).items():
            parts = a.strip("[]").split()
            if len(parts) < 2 or parts[0] not in ("Restore", "Remove"): continue
            typ, host = parts[0], parts[1].rstrip("]")
            c[(typ, "n")] += 1
            c[(typ, "truth")] += host in prev_red
            c[(typ, "latch")] += host in decision_flagged.get(agent, set())
            if typ == "Restore":
                comp = sorted((h for h in prev_red if owner(h) == agent), key=lambda h: order.get(h, 10**9))
                if comp:
                    rule_t += 1; rule_l += comp[0] in decision_flagged.get(agent, set())
            flagged.get(agent, set()).discard(host)                       # executed recovery clears the latch
        for agent, o in (r.get("obs") or {}).items():                     # this step's observation, seen before t+1
            if isinstance(o, dict):
                flagged.setdefault(agent, set()).update(h for h, v in o.items() if h not in META and isinstance(v, dict))
        prev_red = red_now
print(f"{os.path.basename(d)}: {n} episodes" + (f", {nhosts} hosts" if nhosts else "") + ", basis is the state of step t-1, the step before the action completed")
if red_share: print(f"  hosts with a red session per step, mean share {sum(red_share)/len(red_share):.3f} (chance for a random target)")
if red_owned: print(f"  owned hosts with a red session per step, mean share {sum(red_owned)/len(red_owned):.3f} over {nowned} owned hosts (chance for a Restore target)")
for typ in ("Restore", "Remove"):
    k = c[(typ, "n")]
    if k: print(f"  {typ:8} n {k:6}  per episode {k/n:6.1f}  truth {100*c[(typ,'truth')]/k:6.2f}%  latch {100*c[(typ,'latch')]/k:6.2f}%")
print(f"  O1 target at KEEP Restore steps: {rule_t} targets, on latch {100*rule_l/max(rule_t,1):.2f}%")
