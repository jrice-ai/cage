#!/usr/bin/env python3
"""The null tests on KEEP's target selection (RESULTS.md "Five explanations tested"), recomputed.
usage: python3 recompute_nulltests.py   (run from ~/cage; arms corpus_v1, keep_null, oracle_O8)"""
import glob, json, os
from statistics import mean, pstdev

def load(arm):
    out = {}
    for f in sorted(glob.glob(os.path.join("data", "traces", arm, "ep_*.jsonl"))):
        rows = [json.loads(l) for l in open(f) if l.strip()]
        if rows[-1].get("record") != "footer": continue
        out[os.path.basename(f)] = rows
    return out

def corr(x, y):
    mx, my = mean(x), mean(y); sx, sy = pstdev(x), pstdev(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) * sx * sy)

keep = load("corpus_v1"); null = load("keep_null"); o8 = load("oracle_O8")
common_null = sorted(set(keep) & set(null)); common_o8 = sorted(set(keep) & set(o8))

# 1. step reward at Restore steps, and 30 steps before and after a Restore
at = []; before = []; after = []; allr = []
for ep, rows in keep.items():
    steps = [r for r in rows if r.get("record") == "step"]
    sr = [float(r.get("step_reward", 0.0)) for r in steps]; allr += sr
    for i, r in enumerate(steps):
        if any(a.startswith("[Restore") for a in (r.get("action") or {}).values()):
            at.append(sr[i]); before += sr[max(0, i - 30):i]; after += sr[i + 1:i + 31]
print(f"1 restore steps mean step reward {mean(at):.3f} against {mean(allr):.3f} overall; 30 steps before {mean(before):.3f}, 30 steps after {mean(after):.3f}")

# 2. regression to the mean: corr(delta, KEEP score) for the null arm and for O8
ks = {ep: keep[ep][-1]["total_reward"] for ep in keep}
d_null = [null[ep][-1]["total_reward"] - ks[ep] for ep in common_null]
d_o8 = [o8[ep][-1]["total_reward"] - ks[ep] for ep in common_o8]
print(f"2 corr(delta, KEEP score): null arm {corr(d_null, [ks[e] for e in common_null]):.3f} ({len(common_null)} ep), O8 {corr(d_o8, [ks[e] for e in common_o8]):.3f} ({len(common_o8)} ep)")

# 3. early red aggression in the first 100 steps against the O8 delta, raw and partial on KEEP score
AGG = ("Impact", "ExploitRemoteService", "PrivilegeEscalate", "DegradeServices")
def early(rows):
    n = 0
    for r in rows:
        if r.get("record") != "step" or r["step"] >= 100: continue
        for a in (r.get("red_action") or {}).values():
            if any(k in str(a) for k in AGG): n += 1
    return n
agg = [early(keep[ep]) for ep in common_o8]; k8 = [ks[e] for e in common_o8]
r_da, r_dk, r_ka = corr(d_o8, agg), corr(d_o8, k8), corr(k8, agg)
partial = (r_da - r_dk * r_ka) / ((1 - r_dk**2) ** 0.5 * (1 - r_ka**2) ** 0.5)
print(f"3 corr(delta, early aggression) {r_da:.3f} raw, {partial:.3f} partial on KEEP score")

# 4. overrides per episode against delta within O8
ov = [o8[ep][-1].get("overrides", 0) for ep in common_o8]
print(f"4 corr(overrides, delta) within O8 {corr(ov, d_o8):.3f}")
