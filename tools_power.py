#!/usr/bin/env python3
"""Sample size for the human trial, from the per-episode paired deltas of existing arms. Pure Python.

usage:
  python3 tools_power.py CONTROL_DIR ARM_DIR [ARM_DIR ...] [--effects 50,100,200,300,450] [--ns 10,20,30,50,100]
  python3 tools_power.py --pair ARM_A ARM_B [--effects ...] [--ns ...]

Mode 1 (condition against the policy alone): for each arm, the paired deltas arm - control by
episode file name, their mean and sd, and then, holding that sd, the power of a paired t-test
and of the sign test at alpha 0.05 two-sided for each N in --ns and each effect in --effects,
plus the smallest effect detectable at 80 percent power at each N. Effects are in score
points per episode.

Mode 2 (condition A against condition B, both supervised, paired on seeds): the same for
the deltas A - B, which is the comparison a trial between two interfaces makes.

Power is estimated by resampling the observed deltas with replacement (5,000 draws per cell),
shifted so their mean equals the effect, so the spread and shape are the arms' own. The
noise here is the environment's and the policy's sampling; a human supervisor adds variance
of their own, so every N is a floor.
"""
import glob, json, math, os, random, sys


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


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


# ---- t distribution via the regularized incomplete beta (Numerical Recipes betacf) ----
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d; h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < EPS: break
    return h


def _betai(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_two_sided_p(t, df):
    x = df / (df + t * t)
    return _betai(df / 2.0, 0.5, x)


def sign_p(wins, losses):
    n = wins + losses
    if n == 0: return 1.0
    k = min(wins, losses)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def power(deltas, effect, n, draws, rng, alpha=0.05):
    shift = effect - mean(deltas)
    xs = [d + shift for d in deltas]
    rej_t = rej_s = 0
    for _ in range(draws):
        smp = [xs[rng.randrange(len(xs))] for _ in range(n)]
        m = mean(smp); s = sd(smp)
        if s > 0:
            t = m / (s / math.sqrt(n))
            if t_two_sided_p(abs(t), n - 1) < alpha: rej_t += 1
        w = sum(1 for v in smp if v > 0); l = sum(1 for v in smp if v < 0)
        if sign_p(w, l) < alpha: rej_s += 1
    return rej_t / draws, rej_s / draws


def mde(deltas, n, rng, target=0.8, draws=1500):
    lo, hi = 0.0, 4 * sd(deltas) + 1.0
    for _ in range(18):
        mid = (lo + hi) / 2
        if power(deltas, mid, n, draws, rng)[0] >= target: hi = mid
        else: lo = mid
    return hi


def report(label, deltas, effects, ns, rng):
    m, s = mean(deltas), sd(deltas)
    w = sum(1 for d in deltas if d > 0); l = sum(1 for d in deltas if d < 0)
    print(f"\n{label}: n {len(deltas)}, mean delta {m:+.1f}, sd {s:.1f}, wins {w}/{w + l}, sign p {sign_p(w, l):.3g}")
    print("  power (paired t / sign) at alpha 0.05 two-sided, sd held at the arm's own:")
    print("  effect  " + "  ".join(f"N={n:<9}" for n in ns))
    for e in effects:
        row = []
        for n in ns:
            pt, ps = power(deltas, e, n, 3000, rng)
            row.append(f"{pt:.2f} / {ps:.2f}")
        print(f"  {e:6.0f}  " + "  ".join(f"{r:<11}" for r in row))
    print("  smallest effect at 80% power (paired t): " + ", ".join(f"N={n}: {mde(deltas, n, rng):.0f}" for n in ns))


def main():
    argv = sys.argv[1:]
    effects = [50, 100, 200, 300, 450]; ns = [10, 20, 30, 50, 100]
    if "--effects" in argv:
        i = argv.index("--effects"); effects = [float(x) for x in argv[i + 1].split(",")]; del argv[i:i + 2]
    if "--ns" in argv:
        i = argv.index("--ns"); ns = [int(x) for x in argv[i + 1].split(",")]; del argv[i:i + 2]
    rng = random.Random(0)
    if argv and argv[0] == "--pair":
        if len(argv) != 3: sys.exit(__doc__)
        A, B = footers(argv[1]), footers(argv[2])
        eps = sorted(set(A) & set(B))
        if not eps: sys.exit("no shared episodes")
        report(f"{os.path.basename(argv[1])} - {os.path.basename(argv[2])}", [A[e] - B[e] for e in eps], effects, ns, rng)
        return
    if len(argv) < 2: sys.exit(__doc__)
    C = footers(argv[0])
    for arm in argv[1:]:
        A = footers(arm)
        eps = sorted(set(A) & set(C))
        if not eps:
            print(f"{os.path.basename(arm)}: no shared episodes"); continue
        report(f"{os.path.basename(arm)} - {os.path.basename(argv[0])}", [A[e] - C[e] for e in eps], effects, ns, rng)


if __name__ == "__main__":
    main()
