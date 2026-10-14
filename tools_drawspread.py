#!/usr/bin/env python3
"""Whether a set of policy redraws spreads as its sampling share says it should.

Give one or more sets of redraws of one policy on the same environment seeds, separated by --. For each set the script
recomputes the one-way random-effects sampling share from the footers by the method of moments (episode as the factor,
draws as replicates), and compares the sd of the draw means with sqrt(MSW / n), the sd that independent draws with
that within-episode variance would give. The probability is the chi-square probability, with k - 1 degrees of freedom,
of draw means at least this close together.

usage  python3 tools_drawspread.py ARM ARM ... [-- ARM ARM ...]
"""
import glob, json, math, os, sys


def footers(a):
    d = a if os.path.isdir(a) else os.path.join("data", "traces", a)
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        last = None
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    last = line
        try:
            rec = json.loads(last) if last else None
        except ValueError:
            rec = None
        if rec and rec.get("record") == "footer":
            out[os.path.basename(f)] = float(rec["total_reward"])
    return out


def chi2_cdf(x, dof):
    a, t = dof / 2.0, x / 2.0
    if t <= 0:
        return 0.0
    term = 1.0 / math.gamma(a + 1)
    s, n = term, 0
    while term > 1e-15 * s:
        n += 1
        term *= t / (a + n)
        s += term
    return math.exp(-t + a * math.log(t)) * s


def spread(arms):
    F = [footers(a) for a in arms]
    missing = [a for a, f in zip(arms, F) if not f]
    if missing:
        print(f"{arms[0]} set, missing {' '.join(missing)}")
        return
    eps = sorted(set.intersection(*[set(f) for f in F]))
    k, n = len(F), len(eps)
    Y = [[f[e] for f in F] for e in eps]
    em = [sum(r) / k for r in Y]
    gm = sum(em) / n
    msw = sum((y - m) ** 2 for r, m in zip(Y, em) for y in r) / (n * (k - 1))
    msb = k * sum((m - gm) ** 2 for m in em) / (n - 1)
    share = msw / (msw + max(0.0, (msb - msw) / k))
    dm = [sum(f[e] for e in eps) / n for f in F]
    mu = sum(dm) / k
    var_dm = sum((x - mu) ** 2 for x in dm) / (k - 1)
    p = chi2_cdf((k - 1) * var_dm / (msw / n), k - 1)
    print(f"{arms[0]} set, {k} draws of {n} episodes, draw means {', '.join(f'{x:.2f}' for x in dm)}, sd of the draw means "
          f"{var_dm ** 0.5:.2f} against {(msw / n) ** 0.5:.2f} expected for independent draws (probability this close "
          f"or closer {p:.3f}), sampling share {share:.6f}")


def main():
    groups, cur = [], []
    for t in sys.argv[1:]:
        if t == "--":
            groups.append(cur)
            cur = []
        else:
            cur.append(t)
    groups.append(cur)
    groups = [g for g in groups if g]
    if not groups or any(len(g) < 2 for g in groups):
        sys.exit(__doc__)
    for g in groups:
        spread(g)


if __name__ == "__main__":
    main()
