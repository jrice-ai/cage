# SUPERSEDED 2026-10-11 by recompute_criteria.py: this script scores against the same-step truth, which capture.py writes after the step ran. Kept for the record.
#!/usr/bin/env python3
"""Eviction precision against ground truth: of every executed Restore and Remove, how many landed on a
host that held a red session at that step. usage: python3 recompute_precision.py DIR [--episodes N]"""
import glob, json, os, sys
from collections import Counter

argv = sys.argv[1:]; max_eps = 10**9
if "--episodes" in argv:
    i = argv.index("--episodes"); max_eps = int(argv[i+1]); del argv[i:i+2]
d = argv[0] if os.path.isdir(argv[0]) else os.path.join("data", "traces", argv[0])

hit = Counter(); miss = Counter(); red_share = []; n = 0; nhosts = None
for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))[:max_eps]:
    rows = [json.loads(l) for l in open(f) if l.strip()]
    if rows[-1].get("record") != "footer": continue
    hdr = rows[0]
    if nhosts is None and isinstance(hdr.get("hosts"), list): nhosts = len(hdr["hosts"])
    n += 1
    for r in rows:
        if r.get("record") != "step": continue
        truth = r.get("truth") or {}
        red = set(truth.get("red_hosts") or [])
        if nhosts: red_share.append(len(red) / nhosts)
        acts = r.get("action") or r.get("actions") or {}
        for agent, a in acts.items():
            parts = a.strip("[]").split()
            if len(parts) < 2 or parts[0] not in ("Restore", "Remove"): continue
            typ, host = parts[0], parts[1].rstrip("]")
            (hit if host in red else miss)[typ] += 1
print(f"{os.path.basename(d)}: {n} episodes" + (f", {nhosts} hosts" if nhosts else ""))
if red_share: print(f"  hosts with a red session per step, mean share {sum(red_share)/len(red_share):.3f} (chance for a random target)")
for typ in ("Restore", "Remove"):
    h, m = hit[typ], miss[typ]
    print(f"  {typ:8} on compromised {h:6}  on clean {m:6}  total {h+m:6}  precision {100*h/max(h+m,1):6.2f}%   per episode {(h+m)/n:6.1f}")
