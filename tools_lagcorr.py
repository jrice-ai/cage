#!/usr/bin/env python3
"""Correlation between two redraws' outcomes on the episodes where they share a policy stream.
A redraw with policy seed P seeds episode i with P+i, so redraws P and P+d share a stream on their episodes i+d and i,
which run on different scenarios. Give one or more sets of redraws of one policy on the same environment seeds,
separated by --. usage: python3 tools_lagcorr.py ARM ARM ... [-- ARM ARM ...]"""
import glob, json, os, re, statistics, sys
def foot(a):
    out = {}
    for f in sorted(glob.glob(os.path.join("data", "traces", a, "ep_*.jsonl"))):
        rec = json.loads([l for l in open(f) if l.strip()][-1])
        if rec.get("record") == "footer": out[int(re.search(r"ep_(\d+)", f).group(1))] = rec["total_reward"]
    return out
def pseed(a):
    for f in sorted(glob.glob(os.path.join("data", "traces", a, "ep_*.jsonl"))):
        if int(re.search(r"ep_(\d+)", f).group(1)) == 0: return json.loads(open(f).readline()).get("policy_seed")
groups, cur = [], []
for t in sys.argv[1:]:
    if t == "--": groups.append(cur); cur = []
    else: cur.append(t)
groups.append(cur)
rs = []
for g in groups:
    F = {a: foot(a) for a in g}; P = {a: pseed(a) for a in g}
    for ai in g:
        for aj in g:
            if ai == aj or not isinstance(P[ai], int) or not isinstance(P[aj], int) or P[aj] - P[ai] not in (1, 2): continue
            d = P[aj] - P[ai]; ee = [e for e in sorted(F[aj]) if e + d in F[ai]]
            r = statistics.correlation([F[ai][e + d] for e in ee], [F[aj][e] for e in ee]); rs.append(r)
            print(f"{ai} ep e+{d} vs {aj} ep e: corr {r:+.3f} over {len(ee)} episodes")
print(f"pairs {len(rs)}  min {min(rs):+.3f}  max {max(rs):+.3f}")
