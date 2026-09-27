#!/usr/bin/env python3
"""Share of the distance to the ground-truth ceiling that a supervised arm closes, with a paired
bootstrap interval. Pure Python.

usage: python3 tools_ceiling.py CEILING_DIR CONTROL_DIR ARM_DIR [ARM_DIR ...] [--n 10000]

gap    = mean(ceiling) - mean(control)     (RT under the same adversary, minus the policy alone)
delta  = mean(arm) - mean(control)         (the supervisor's gain)
closed = delta / gap

Unlike the fraction of excess loss (tools_fraction_ci.py), the ceiling is a score the same
environment pays a policy with perfect eyes, so the share stays meaningful for policies whose
stock control is not a ceiling of their own. All directories must share episode file names.
The bootstrap resamples seeds with replacement, keeping a seed's three footers together.
"""
import glob, json, os, random, sys


def footers(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        last = None
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    last = line
        if last:
            try:
                rec = json.loads(last)
            except json.JSONDecodeError:
                continue
            if rec.get("record") == "footer":
                out[os.path.basename(f)] = rec["total_reward"]
    return out


def mean(xs):
    return sum(xs) / len(xs)


def main():
    argv = sys.argv[1:]
    n = 10000
    if "--n" in argv:
        i = argv.index("--n"); n = int(argv[i + 1]); del argv[i:i + 2]
    if len(argv) < 3:
        sys.exit(__doc__)
    ceil, ctl, arms = argv[0], argv[1], argv[2:]
    R, C = footers(ceil), footers(ctl)
    rng = random.Random(0)
    for arm in arms:
        A = footers(arm)
        eps = sorted(set(R) & set(C) & set(A))
        if not eps:
            print(f"{os.path.basename(arm)}: no shared episodes"); continue
        r = [R[e] for e in eps]; c = [C[e] for e in eps]; a = [A[e] for e in eps]
        m = len(eps)
        gap = mean(r) - mean(c); delta = mean(a) - mean(c)
        if gap <= 0:        # the policy alone is already at or above the ceiling
            print(f"{os.path.basename(arm):30} n {m:3}  ceiling {mean(r):8.1f}  control {mean(c):8.1f}  gap {gap:7.1f}  delta {delta:+7.1f}  closed n/a (no gap)")
            continue
        cb = []
        for _ in range(n):
            idx = [rng.randrange(m) for _ in range(m)]
            rm = sum(r[i] for i in idx) / m; cm = sum(c[i] for i in idx) / m; am = sum(a[i] for i in idx) / m
            g = rm - cm
            if g > 0:
                cb.append((am - cm) / g)
        cb.sort()
        lo, hi = cb[int(0.025 * len(cb))], cb[int(0.975 * len(cb)) - 1]
        print(f"{os.path.basename(arm):30} n {m:3}  ceiling {mean(r):8.1f}  control {mean(c):8.1f}  gap {gap:7.1f}  "
              f"delta {delta:+7.1f}  closed {delta / gap:.3f}  95% CI [{lo:.3f}, {hi:.3f}]")


if __name__ == "__main__":
    main()
