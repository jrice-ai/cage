#!/usr/bin/env python3
"""Sampling against difficulty over arms that share environment seeds and differ only in policy seed.
One-way random-effects decomposition: episode is the factor, policy seeds are replicates.
usage: python3 recompute_variance.py DIR DIR [DIR ...] [--n 10000]"""
import glob, json, os, random, sys
from statistics import mean, variance

def footers(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        last = None
        for line in open(f):
            if line.strip(): last = line
        rec = json.loads(last)
        if rec.get("record") == "footer": out[os.path.basename(f)] = rec["total_reward"]
    return out

args = [a for a in sys.argv[1:] if not a.startswith("--")]
nboot = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 10000
arms = [footers(d) for d in args]
k = len(arms)
eps = sorted(set.intersection(*[set(a) for a in arms]))
print(f"{k} arms, {len(eps)} shared episodes")

def decompose(ep_list):
    within = mean(variance([a[e] for a in arms]) for e in ep_list)        # sampling variance, ddof 1 over seeds
    vmeans = variance([mean(a[e] for a in arms) for e in ep_list])        # variance of per-episode means, ddof 1
    difficulty = max(vmeans - within / k, 0.0)                            # remove the sampling share of the mean's variance
    return within, vmeans, difficulty, within / (within + difficulty)

w, vm, dif, share = decompose(eps)
print(f"within-episode sd across policy seeds (sampling)   {w**0.5:.2f}   (RESULTS.md 44.50)")
print(f"sd of per-episode means, naive                     {vm**0.5:.2f}   (RESULTS.md 36.39)")
print(f"difficulty sd, sampling share of the mean removed  {dif**0.5:.2f}")
print(f"naive share by sd                                  {w**0.5/(w**0.5+vm**0.5):.3f}")
print(f"naive share by variance                            {w/(w+vm):.3f}")
print(f"sampling share of variance, random effects         {share:.3f}")
random.seed(0)
boots = sorted(decompose([random.choice(eps) for _ in eps])[3] for _ in range(nboot))
print(f"95% bootstrap interval over episodes               [{boots[int(0.025*nboot)]:.3f}, {boots[int(0.975*nboot)]:.3f}]")

sds = sorted((variance([a[e] for a in arms]) ** 0.5, e) for e in eps)
q = lambda p: sds[int(p * (len(sds) - 1))][0]
print(f"per-episode sd quantiles  min {q(0):.1f}  p25 {q(0.25):.1f}  median {q(0.5):.1f}  p75 {q(0.75):.1f}  p90 {q(0.9):.1f}  max {q(1):.1f}")
print("largest five:", ", ".join(f"{e} {s:.0f}" for s, e in sds[-5:]))
top = {e for _, e in sds[-5:]}
w2, vm2, dif2, share2 = decompose([e for e in eps if e not in top])
print(f"random-effects share without the largest five      {share2:.3f}")
