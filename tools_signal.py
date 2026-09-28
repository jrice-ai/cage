#!/usr/bin/env python3
"""Calibrate O15's engagement threshold from the per-step signal records of a survey arm. Pure Python.

usage: python3 tools_signal.py DIR [DIR ...] [--o1 N] [--grid a,b,c]

An O15 arm run with --engage 1e9 never engages, so it is the policy alone with the signal
recorded at every free agent-tick: the step record's "signal" maps agent -> [signal, compromised
owned hosts]. For each arm this prints the signal's quantiles over agent-ticks, split by whether
the agent had a compromised owned host (the ticks O1 would act on), and for a grid of thresholds
the share of those ticks at or above the threshold (recall: how often the gate is open when
there is something to do), the share of clean ticks at or above it (false engagement), and the
share of open-gate ticks that had something to do (precision, the signal as a timing cue).
With --o1 N (O1's overrides per episode at the same gap and adversary) the recall is projected
onto interventions per episode; the projection assumes the policy's own dynamics, which the
gate then changes, so the pilot at the chosen threshold is the number that counts.
The grid is the integers 1..max for an integer signal (O15a, O15c) and the deciles of the
comp>0 ticks otherwise (O15r), unless --grid is given.
"""
import glob, json, os, sys


def q(xs, p):
    if not xs:
        return float("nan")
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def analyse(d, o1, grid):
    hit, miss = [], []; n = 0; steps = 0
    rule = None
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        rows = [json.loads(l) for l in open(f) if l.strip()]
        if not rows or rows[-1].get("record") != "footer":
            continue
        n += 1
        if rule is None:
            rule = rows[0].get("rule"); eng = rows[0].get("engage"); win = rows[0].get("window")
        for r in rows:
            if r.get("record") != "step":
                continue
            steps += 1
            for agent, (sig, nc) in (r.get("signal") or {}).items():
                (hit if nc > 0 else miss).append(sig)
    if not n:
        print(f"{os.path.basename(d)}: no complete episodes"); return
    allv = hit + miss
    print(f"\n{os.path.basename(d)}: rule {rule} engage {eng} window {win}; {n} episodes, {steps} steps, "
          f"{len(allv)} free agent-ticks, {len(hit) / len(allv):.3f} with a compromised owned host")
    for lab, xs in (("all ticks", allv), ("comp>0  ", hit), ("comp==0 ", miss)):
        print(f"  {lab}: n {len(xs):6}  mean {sum(xs) / len(xs) if xs else float('nan'):7.2f}  "
              + "  ".join(f"p{int(p * 100):02d} {q(xs, p):6.1f}" for p in (0.1, 0.25, 0.5, 0.75, 0.9, 0.95)) + f"  max {max(xs) if xs else float('nan'):6.1f}")
    if grid is None:
        if all(float(x).is_integer() for x in allv) and max(allv) <= 12:     # a count (O15a, O15c)
            grid = list(range(1, int(max(allv)) + 1))
        else:
            grid = sorted({round(q(hit, p), 1) for p in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)})
    print("  threshold  recall(comp>0 open)  false(comp==0 open)  precision(open ticks with comp>0)" + ("  projected overrides/ep" if o1 else ""))
    for th in grid:
        oh = sum(1 for x in hit if x >= th); om = sum(1 for x in miss if x >= th)
        rec = oh / len(hit) if hit else float("nan"); fal = om / len(miss) if miss else float("nan")
        prec = oh / (oh + om) if oh + om else float("nan")
        line = f"  {th:9.1f}  {rec:19.3f}  {fal:19.3f}  {prec:34.3f}"
        if o1:
            line += f"  {rec * o1:22.1f}"
        print(line)


def main():
    argv = sys.argv[1:]; o1 = None; grid = None
    if "--o1" in argv:
        i = argv.index("--o1"); o1 = float(argv[i + 1]); del argv[i:i + 2]
    if "--grid" in argv:
        i = argv.index("--grid"); grid = [float(x) for x in argv[i + 1].split(",")]; del argv[i:i + 2]
    if not argv:
        sys.exit(__doc__)
    for d in argv:
        analyse(d if os.path.isdir(d) else os.path.join("data", "traces", d), o1, grid)


if __name__ == "__main__":
    main()
