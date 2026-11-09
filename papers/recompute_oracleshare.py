#!/usr/bin/env python3
"""Of an oracle arm's executed Restores, the share that were the rule's own directives (an override at
t-4 for the same agent and host, the step an accepted Restore completes) against the policy's own
Restores passed through on steps where the rule had no target.
usage: python3 recompute_oracleshare.py ARM"""
import glob, json, os, sys
d = sys.argv[1] if os.path.isdir(sys.argv[1]) else os.path.join("data", "traces", sys.argv[1])
rule = own = 0; n = 0
for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
    rows = [json.loads(l) for l in open(f) if l.strip()]
    if rows[-1].get("record") != "footer": continue
    steps = [r for r in rows if r.get("record") == "step"]; n += 1
    for i, r in enumerate(steps):
        for agent, a in (r.get("action") or {}).items():
            parts = a.strip("[]").split()
            if len(parts) < 2 or parts[0] != "Restore": continue
            host = parts[1].rstrip("]")
            issued = i >= 4 and any(ag == agent and to == f"Restore:{host}" for ag, frm, to in steps[i - 4].get("overrides", []))
            if issued: rule += 1
            else: own += 1
tot = rule + own
print(f"{os.path.basename(d)}: {n} episodes, executed Restores {tot} ({tot/n:.1f} per episode)")
print(f"  rule share {rule/tot:.3f} ({rule})  pass-through share {own/tot:.3f} ({own})")
