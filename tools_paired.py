#!/usr/bin/env python3
"""Paired comparison of trace arms against a control, episode by episode.

usage: python3 tools_paired.py CONTROL_DIR ARM_DIR [ARM_DIR ...]

Pairs footers by episode file name (same environment seeds). Prints, per arm:
mean, mean delta over control, wins of N, exact two-sided sign test p (ties dropped),
and per-episode overrides / agreements / executed analyses and restores, plus
mode_overrides and recover_agent_steps when present (H-MARL arms).
"""
import glob, json, os, sys
from math import comb


def footers(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        last = None
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    last = line
        if last:
            out[os.path.basename(f)] = json.loads(last)
    return out


def sign_test(wins, losses):
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    p = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ctl_dir, arm_dirs = sys.argv[1], sys.argv[2:]
    C = footers(ctl_dir)
    if not C:
        sys.exit(f"no footers under {ctl_dir}")
    cm = mean([c["total_reward"] for c in C.values()])
    print(f"control {ctl_dir}: {len(C)} episodes, mean {cm:.2f}")
    hdr = f"{'arm':<28}{'n':>4}{'mean':>10}{'delta':>9}{'wins':>6}{'p':>9}{'ovr/ep':>8}{'agr/ep':>8}{'anl/ep':>8}{'rst/ep':>8}{'mode/ep':>9}{'recov/ep':>10}"
    print(hdr)
    for d in arm_dirs:
        A = footers(d)
        eps = sorted(set(A) & set(C))
        if not eps:
            print(f"{os.path.basename(d):<28}   no shared episodes")
            continue
        deltas = [A[e]["total_reward"] - C[e]["total_reward"] for e in eps]
        wins = sum(1 for x in deltas if x > 0)
        losses = sum(1 for x in deltas if x < 0)
        p = sign_test(wins, losses)
        g = lambda k: mean([A[e].get(k, 0) or 0 for e in eps])
        print(f"{os.path.basename(d):<28}{len(eps):>4}{mean([A[e]['total_reward'] for e in eps]):>10.2f}"
              f"{mean(deltas):>+9.1f}{wins:>4}/{len(eps):<3}{p:>7.3f}"
              f"{g('overrides'):>8.1f}{g('agreements'):>8.1f}{g('analyses'):>8.1f}{g('restores'):>8.1f}"
              f"{g('mode_overrides'):>9.1f}{g('recover_agent_steps'):>10.1f}")


if __name__ == "__main__":
    main()
