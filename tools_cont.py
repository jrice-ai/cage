#!/usr/bin/env python3
"""Continuations: does the training seed matter beyond the evaluation draw?

usage: python3 tools_cont.py CONTROL_DIR ARM_DIR [ARM_DIR ...]

Each ARM_DIR is one evaluation draw of one continuation. Arms are grouped by training seed
(the _s<seed>_ token in the name). For each arm the paired mean delta against the control is
computed over shared episodes. Then a one-way decomposition with training seed as the factor
and draws as replicates: between-seed sd of the seed means, within-seed sd of the draw means,
the between share of variance with the within contribution to the seed means removed, and a
permutation p value (10,000 shuffles of draw means across seeds, seed 0) for the observed
between-seed variance.
"""
import glob, json, os, random, re, sys
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

ctl = footers(sys.argv[1]); groups = {}
for d in sys.argv[2:]:
    A = footers(d); eps = sorted(set(A) & set(ctl))
    if len(eps) < len(ctl): print(f"warning: {os.path.basename(d)} shares {len(eps)} of {len(ctl)} episodes", file=sys.stderr)
    delta = mean(A[e] - ctl[e] for e in eps); wins = sum(1 for e in eps if A[e] > ctl[e])
    seed = re.search(r"_s(\d+)_", os.path.basename(d)).group(1)
    groups.setdefault(seed, []).append((os.path.basename(d), delta, wins, len(eps)))
seeds = sorted(groups)
for s in seeds:
    for name, delta, wins, n in groups[s]: print(f"seed {s}  {name:52} delta {delta:+8.1f}  wins {wins}/{n}")
    ds = [g[1] for g in groups[s]]
    print(f"seed {s}  mean of {len(ds)} draws {mean(ds):+8.1f}  sd across draws {variance(ds)**0.5 if len(ds) > 1 else float('nan'):6.1f}  signs {'same' if all(x > 0 for x in ds) or all(x < 0 for x in ds) else 'mixed'}")
means = [mean(g[1] for g in groups[s]) for s in seeds]
k = mean(len(groups[s]) for s in seeds)
within = mean(variance([g[1] for g in groups[s]]) for s in seeds)
between_naive = variance(means)
between = max(between_naive - within / k, 0.0)
share = between / (between + within) if (between + within) > 0 else float("nan")
print(f"between-seed sd of seed means {between_naive**0.5:.1f}  within-seed sd of draw means {within**0.5:.1f}  between share (within removed) {share:.3f}")
allv = [g[1] for s in seeds for g in groups[s]]; sizes = [len(groups[s]) for s in seeds]
random.seed(0); obs = between_naive; hits = 0; N = 10000
for _ in range(N):
    random.shuffle(allv); i = 0; ms = []
    for sz in sizes: ms.append(mean(allv[i:i + sz])); i += sz
    if variance(ms) >= obs - 1e-12: hits += 1
print(f"permutation p for the training seed mattering beyond the draw {hits / N:.3f}  ({N} shuffles, seed 0)")
