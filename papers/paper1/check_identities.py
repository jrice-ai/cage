#!/usr/bin/env python3
"""Arithmetic identities every build must satisfy, checked on ledger.csv. Run by make check.
    python3 check_identities.py ledger.csv
Each split in the paper is cost = charge + rest (or difference = rest - charge where the charge is paid by the arm
that scores lower), so the three printed values of a split must agree within rounding. The H-MARL mask-off pair has
a rest of zero on every episode, the O1 arm's precision is the rule's own share of its Restores within a quarter of a
point, and the t interval over four draws uses the 3 df quantile. A known-answer test pins the interval arithmetic
and the across-seed quantile table of fig/fig_curves.py. Exit 1 on any failure."""
import csv, os, re, statistics as st, sys

L = sys.argv[1] if len(sys.argv) > 1 else "ledger.csv"
rows = {r["key"]: r["value"] for r in csv.DictReader(open(L, newline=""))}
checked, failed = 0, []


def v(k):
    return float(rows[k])


def tol(*keys):            # rounding tolerance from the coarsest printed value, two roundings
    return max(0.5 * 10 ** -(len(rows[k].split(".")[1]) if "." in rows[k] else 0) for k in keys) * 2.2


def check(name, ok, detail=""):
    global checked
    checked += 1
    if not ok: failed.append(f"{name} {detail}")


def identity(name, total, a, b, sign=1):   # total = a + sign * b
    if not all(k in rows for k in (total, a, b)): return
    got = v(a) + sign * v(b)
    check(name, abs(v(total) - got) <= tol(total, a, b), f"{total} {v(total)} against {a} {'+' if sign > 0 else '-'} {b} = {got:.3f}")


# 1. cost = charge + rest, for the released policies with their checks off
for p in ("relbusy", "hmrelbusy", "relbusywrecker"):
    identity(f"{p}: cost = charge + rest", f"{p}cost", f"{p}chargecost", f"{p}rest")
# 2. held minus fired = charge + rest, by defender and adversary
for p in ("keepheldvsfired", "hmarlheldvsfired", "sheldvsfired", "hmsheldvsfired", "burstvsspread"):
    identity(f"{p}: difference = charge + rest", p, p + "charge", p + "rest")
identity("decoy held: gap = charge + rest", "decoyheldgap", "decoyheldcharge", "decoyheldrest")
# 3. a rule arm against its control: difference = rest - charge (the rule's arm pays the charge)
for p in ("soonefired", "sooneheld", "hmsoonefired", "hmsooneheld", "sooneunboundedheld"):
    identity(f"{p}: difference = rest - charge", p, p + "rest", p + "charge", -1)
if all(k in rows for k in ("oonedelta", "oonerest", "oonecharge")):
    identity("O1 fired: difference = rest - charge", "oonedelta", "oonerest", "oonecharge", -1)
# 4. the H-MARL mask-off pair, a rest of zero on every episode and executed actions identical
for k, want in (("hmrelbusyrest", 0.0), ("hmrelbusyrestlo", 0.0), ("hmrelbusyresthi", 0.0)):
    if k in rows: check(f"{k} is zero", abs(v(k)) < 1e-9, rows[k])
if "hmrelbusysamesteps" in rows and "episodes" in rows: check("H-MARL mask off, executed actions identical on every episode", v("hmrelbusysamesteps") == v("episodes"), rows["hmrelbusysamesteps"])
if "hmrelbusycost" in rows and "hmrelbusychargecost" in rows: check("H-MARL mask off, cost is the charge", abs(v("hmrelbusycost") - v("hmrelbusychargecost")) <= tol("hmrelbusycost"))
# 5. the O1 mixture, rule share plus pass-through share is one, and the arm's precision is the rule's share within a quarter point
if all(k in rows for k in ("oonerulerestoreshare", "oonepassthrough")):
    check("O1 shares sum to one", abs(v("oonerulerestoreshare") + v("oonepassthrough") - 1) <= 0.0011, f"{rows['oonerulerestoreshare']} + {rows['oonepassthrough']}")
if all(k in rows for k in ("oonerestoreprecision", "oonerulerestoreshare")):
    check("O1 precision within a quarter point of the rule's share", abs(v("oonerestoreprecision") - 100 * v("oonerulerestoreshare")) <= 0.25 + 0.06, f"{rows['oonerestoreprecision']} against {100 * v('oonerulerestoreshare'):.2f}")
# 6. t intervals over four draws, 3 df, and a known answer
Q = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}       # two-sided 95 percent t quantile keyed by the number of draws or seeds (n - 1 df)
xs = [1.0, 2.0, 3.0, 4.0]; m, s = st.mean(xs), st.stdev(xs); h = Q[4] * s / 2
check("known answer, four draws 1 2 3 4", abs(m - 2.5) < 1e-9 and abs(h - 2.0540) < 5e-4, f"half-width {h:.4f}")
if all(k in rows for k in ("keeprepro", "keepreprolo", "keepreprohi", "keepreprose")):
    hw = Q[4] * v("keepreprose")          # the standard error of a four-draw mean is sd / 2
    check("released KEEP interval is mean plus or minus 3.182 standard errors", abs(v("keepreprohi") - v("keeprepro") - hw) <= 0.03 and abs(v("keeprepro") - v("keepreprolo") - hw) <= 0.03, f"half-width {hw:.3f}")
for k in sorted(k for k in rows if re.fullmatch(r"long[fsr][a-d](fourh|eighth|twelveh|sixteenh|twentyh|oneh|twoh|threeh)?draws", k)):
    stem = k[:-5]                      # every four-draw estimate of the continuation, F, S and R, keyed by seed letter
    if all(x in rows for x in (k + "lo", k + "hi", stem + "drawsd")):
        hw = Q[4] * v(stem + "drawsd") / 2
        check(f"{k} interval is mean plus or minus 3.182 sd / 2", abs(v(k + "hi") - v(k) - hw) <= 0.03 and abs(v(k) - v(k + "lo") - hw) <= 0.03, f"half-width {hw:.3f}")
        if "keeprepro" in rows and stem + "gap" in rows: check(f"{stem}gap is keeprepro less the four-draw mean", abs(v(stem + "gap") - (v("keeprepro") - v(k))) <= 0.06)
        if stem + "above" in rows: check(f"{stem}above is minus {stem}gap", abs(v(stem + "above") + v(stem + "gap")) <= 0.06)
if "longdrawsmeanall" in rows:                        # the mean over the continued seeds of their four-draw means at 2,000 updates
    ks = sorted(k for k in rows if re.fullmatch(r"longf[a-d]draws", k))
    got = sum(v(k) for k in ks) / len(ks)
    check("longdrawsmeanall is the mean of the continued seeds' four-draw means", abs(v("longdrawsmeanall") - got) <= 0.06, f"{got:.3f} over {len(ks)} seeds")
for w in ("oneh", "twoh", "threeh", "fourh"):       # across four training seeds, 3 df, half-width 3.182 sd / 2
    k = f"pilotdelta{w}"
    if all(x in rows for x in (k, f"pilotdeltasd{w}", f"pilotdeltatlo{w}", f"pilotdeltathi{w}")):
        hw = Q[4] * v(f"pilotdeltasd{w}") / 2
        check(f"{k} across-seed interval is mean plus or minus 3.182 sd / 2", abs(v(f"pilotdeltathi{w}") - v(k) - hw) <= 0.16 and abs(v(k) - v(f"pilotdeltatlo{w}") - hw) <= 0.16, f"half-width {hw:.2f} against stored [{rows[f'pilotdeltatlo{w}']}, {rows[f'pilotdeltathi{w}']}]")
fc = os.path.join(os.path.dirname(os.path.abspath(L)), "fig", "fig_curves.py")
if os.path.exists(fc):
    src = open(fc).read()
    m_ = re.search(r"tq = \{([^}]*)\}", src)
    check("fig_curves.py across-seed quantile keyed by the number of seeds", bool(m_) and all(f"{n}: {q}" in m_.group(1) for n, q in Q.items()), m_.group(1) if m_ else "no tq table")
    check("fig_curves.py four-draw interval uses 3.182 sd / 2", "3.182 * sd_ / 2" in src)
for f in failed: print("FAIL", f)
print(f"identities: {checked} checked, {len(failed)} failed")
sys.exit(1 if failed else 0)
