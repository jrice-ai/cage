#!/usr/bin/env python3
"""Fraction of excess loss recovered, with a paired bootstrap interval. Pure Python.

usage: python3 tools_fraction_ci.py STOCK_CONTROL_DIR ADVERSARY_CONTROL_DIR ARM_DIR [ARM_DIR ...] [--n 10000]

excess   = mean(control under adversary) - mean(control under stock red)   (negative: the extra loss)
delta    = mean(arm) - mean(control under adversary)                        (the supervisor's gain)
fraction = delta / -excess

All three directories must share episode file names (same environment seeds). The bootstrap
resamples seeds with replacement, keeping the three footers of a seed together.
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
    stock, ctl, arms = argv[0], argv[1], argv[2:]
    S, C = footers(stock), footers(ctl)
    rng = random.Random(0)
    for arm in arms:
        A = footers(arm)
        eps = sorted(set(S) & set(C) & set(A))
        if not eps:
            print(f"{os.path.basename(arm)}: no shared episodes"); continue
        s = [S[e] for e in eps]; c = [C[e] for e in eps]; a = [A[e] for e in eps]
        m = len(eps)
        excess = mean(c) - mean(s); delta = mean(a) - mean(c); frac = delta / -excess
        fb = []
        for _ in range(n):
            idx = [rng.randrange(m) for _ in range(m)]
            sm = sum(s[i] for i in idx) / m; cm = sum(c[i] for i in idx) / m; am = sum(a[i] for i in idx) / m
            ex = cm - sm
            if ex != 0:
                fb.append((am - cm) / -ex)
        fb.sort()
        lo, hi = fb[int(0.025 * len(fb))], fb[int(0.975 * len(fb)) - 1]
        print(f"{os.path.basename(arm):26} n {m:3}  excess {excess:8.1f}  delta {delta:+7.1f}  "
              f"fraction {frac:.3f}  95% CI [{lo:.3f}, {hi:.3f}]")


if __name__ == "__main__":
    main()
