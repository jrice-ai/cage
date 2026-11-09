#!/usr/bin/env python3
"""Write fig/tab_busyreds.tex, the released KEEP policy with its busy check on and off at the stock adversary and nine
others, recomputed from the traces by tools_busy_charge.py (paired, 10,000-draw bootstrap over episodes, seed 0).
Its numbers are literal and check_numbers.py skips the file, as it does tab_arms.tex. Run from anywhere; CAGE names
the harness directory (default ~/cage). Prints the extremes the ledger rows relbusycostmin, relbusycostmax,
relbusychargesharemin, relbusychargesharemax and relbusyrestzero record. The tool prints check off minus check on,
the table prints cost (on minus off), charge and rest in that direction, so the rest is the cost less the charge."""
import os, re, subprocess
CAGE = os.environ.get("CAGE", os.path.expanduser("~/cage"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tab_busyreds.tex")
ROWS = [("", "stock"), ("_FSRedAgentWrecker", "Wrecker"), ("_FSRedAgentTargetARestricted", "TargetA restricted"),
        ("_FSRedAgentTargetAOperational", "TargetA operational"), ("_FSRedAgentTargetA", "TargetA"), ("_FSRedAgentTargetB", "TargetB"),
        ("_FSRedAgentTargetBRestricted", "TargetB restricted"), ("_FSRedAgentTargetBOperational", "TargetB operational"),
        ("_FSRedAgentCombined", "Combined"), ("_FSRedAgentFailureTracker", "FailureTracker")]
NUM = r"(-?[\d.]+)"
def read(suffix, prefix="keep_released_busy_"):
    a, b = prefix + "shipped" + suffix, prefix + "none" + suffix
    o = subprocess.run(f"python3 tools_busy_charge.py data/traces/{a} data/traces/{b}", shell=True, cwd=CAGE, capture_output=True, text=True)
    o = o.stdout + o.stderr
    on = re.search(re.escape(a) + r"\s+reward\s+" + NUM, o); off = re.search(re.escape(b) + r"\s+reward\s+" + NUM + r"\s+Restores passed\s+" + NUM + r"\s+of them to busy agents\s+" + NUM, o)
    d = re.search(r"reward difference\s+" + NUM + r"\s+ci95 \[" + NUM + ", " + NUM + r"\]", o)
    c = re.search(r"charge difference\s+" + NUM + r"\s+ci95 \[" + NUM + ", " + NUM + r"\]", o)
    r = re.search(r"\n\s+rest\s+" + NUM + r"\s+ci95 \[" + NUM + ", " + NUM + r"\]", o)
    if not (on and off and d and c and r): raise SystemExit(f"could not read {a} against {b}\n" + o[-400:])
    return [float(on.group(1)), float(off.group(1)), float(off.group(3))] + [float(x) for x in d.groups() + c.groups() + r.groups()]
def neg(v): return ("\\ensuremath{-}" + f"{-v:.2f}") if v < 0 else f"{abs(v):.2f}"   # abs keeps a negated zero from printing as -0.00
def iv(lo, hi): return f"[{neg(lo)}, {neg(hi)}]"
lines = [r"\setlength{\tabcolsep}{2.5pt}\begin{tabular}{L{0.16\linewidth}rrrlrrlr}", r"\toprule",
         r"Adversary & Check on & Check off & Cost & 95\% interval & Charge & Rest & 95\% interval & To busy \\", r"\midrule"]
ext = []
for suffix, name in ROWS:
    on, off, busy, d, dlo, dhi, c, clo, chi, r, rlo, rhi = read(suffix)
    lines.append(f"{name} & {neg(on)} & {neg(off)} & {-d:.2f} & {iv(-dhi, -dlo)} & {-c:.2f} & {neg(-r)} & {iv(-rhi, -rlo)} & {busy:.2f} \\\\")   # rest as cost less charge
    if suffix: ext.append((-d, c / d, rlo <= 0 <= rhi, name, -r, -rhi, -rlo))
on, off, busy, d, dlo, dhi, c, clo, chi, r, rlo, rhi = read("", "hm_released_busy_")   # the released H-MARL policy, mask off, stock
lines += [r"\midrule", f"H-MARL, stock & {neg(on)} & {neg(off)} & {-d:.2f} & {iv(-dhi, -dlo)} & {-c:.2f} & {neg(-r)} & {iv(-rhi, -rlo)} & {busy:.2f} \\\\"]
lines += [r"\bottomrule", r"\end{tabular}"]
open(OUT, "w").write("\n".join(lines) + "\n")
costs = sorted(ext); shares = sorted(x[1] for x in ext)
print(f"wrote {OUT}; nine adversaries, cost min {costs[0][0]:.2f} ({costs[0][3]}) max {costs[-1][0]:.2f} ({costs[-1][3]}), "
      f"charge share min {shares[0]:.3f} max {shares[-1]:.3f}, rest interval covers zero in {sum(x[2] for x in ext)} of 9")
for x in ext:
    if not x[2]: print(f"rest excludes zero: {x[3]} cost {x[0]:.2f} rest {x[4]:.2f} [{x[5]:.2f}, {x[6]:.2f}]")
