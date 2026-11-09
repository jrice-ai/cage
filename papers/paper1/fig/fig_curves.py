#!/usr/bin/env python3
"""Figure and table of the busy-check pilot. KEEP trained from scratch with its busy check as shipped (arm F) and
with it removed (arm N) on paired training seeds, every hundredth checkpoint scored on the paired episodes at the
stock adversary, N both its own way and with the check on, and arm F continued past the paired range. Reads the
traces under $CAGE/data/traces/kbf_<arm>_s<seed>_u<update>_<busy>, pairs episodes by file name, and writes
fig/curves.pdf, curves.png, curves.json, fig/tab_pilot.tex (the paired range) and fig/tab_cont.tex (the continuation). Prints every number the ledger carries.

  per seed and checkpoint   F, N scored its own way (check off), N scored with the check on, the Restores per
                            episode N sends to busy agents when scored its own way, and the paired difference
                            F minus N (check on) with a seeded 10,000-draw bootstrap 95% interval and wins of 100
  per checkpoint            means over seeds, the seeds in which F leads, the smallest and largest lead
  continuation              F at every scored checkpoint past the paired range, with the paired difference to the
                            released policy (corpus_v1), four sampling draws (tied, 9000, 9001, 9002) where all four
                            are scored, the fixed-layout, seeded control S and the read-all control R where scored,
                            each with its four draws where scored. Panel (b) is drawn on an axis of episodes consumed
                            by the learner, five per update for F and S and twenty-five for R.
Version 5 (t23): endpoint paired differences of the controls against the check-on arm.
"""
import glob, json, os, random, re, statistics as st
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

CAGE = os.environ.get("CAGE", os.path.expanduser("~/cage"))
T = lambda a: os.path.join(CAGE, "data", "traces", a)
OUT = os.path.dirname(os.path.abspath(__file__))
BLUE, ORANGE, INK, QUIET, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#d9d8d3"
PAIRED_MAX = 400
WORDS = {100: "oneh", 200: "twoh", 300: "threeh", 400: "fourh", 800: "eighth", 1200: "twelveh", 1600: "sixteenh", 2000: "twentyh"}


def footers(arm):
    out = {}
    for f in sorted(glob.glob(os.path.join(T(arm), "ep_*.jsonl"))):
        lines = [l for l in open(f) if l.strip()]
        if not lines: continue
        try: r = json.loads(lines[-1])
        except json.JSONDecodeError: continue
        if r.get("record") == "footer": out[os.path.basename(f)] = r["total_reward"]
    return out


def restores_at_busy(arm):
    """Mean over episodes of policy Restores sent to a busy agent (traces captured with --log-policy)."""
    per = []
    for f in sorted(glob.glob(os.path.join(T(arm), "ep_*.jsonl"))):
        n, ok = 0, False
        for line in open(f):
            r = json.loads(line)
            if r.get("record") == "step" and "policy" in r:
                busy = set(r["busy"])
                n += sum(1 for a, act in r["policy"].items() if a in busy and act is not None and act.startswith("Restore"))
            elif r.get("record") == "footer": ok = True
        if ok: per.append(n)
    return st.mean(per) if per else float("nan")


def paired(A, C):
    eps = sorted(set(A) & set(C))
    if len(eps) < 100: return None
    d = [A[e] - C[e] for e in eps]; m = st.mean(d)
    rng = random.Random(0); boots = sorted(st.mean(rng.choices(d, k=len(d))) for _ in range(10000))
    return {"delta": m, "lo": boots[250], "hi": boots[9749], "wins": sum(1 for x in d if x > 0), "n": len(d)}


def arm_mean(arm):
    F = footers(arm); return (st.mean(F.values()), len(F)) if len(F) >= 100 else (None, len(F))


seeds = sorted({int(m.group(1)) for p in glob.glob(T("kbf_F_s*_u*_shipped")) for m in [re.search(r"kbf_F_s(\d+)_u", p)] if m})
updates = sorted({int(m.group(1)) for p in glob.glob(T("kbf_F_s*_u*_shipped")) for m in [re.search(r"_u(\d+)_shipped$", p)] if m})
pilot = {}      # (seed, u) -> dict
for s in seeds:
    for u in updates:
        F = footers(f"kbf_F_s{s}_u{u}_shipped")
        if len(F) < 100: continue
        row = {"F": st.mean(F.values())}
        Non = footers(f"kbf_N_s{s}_u{u}_shipped"); Nown = footers(f"kbf_N_s{s}_u{u}_none")
        if len(Non) >= 100 and len(Nown) >= 100:
            row.update({"Non": st.mean(Non.values()), "Nown": st.mean(Nown.values()),
                        "busy": restores_at_busy(f"kbf_N_s{s}_u{u}_none"), "pair": paired(F, Non)})
        pilot[(s, u)] = row
corpus = footers("corpus_v1")
# the released policy's reproduction interval, four sampling draws, t with 3 df (ledger keeprepro, keepreprolo, keepreprohi)
draws = [st.mean(footers(a).values()) for a in ("corpus_v1", "keep_null", "keep_null_9001", "keep_null_9002") if len(footers(a)) >= 100]
band = (st.mean(draws), st.mean(draws) - 3.182 * st.stdev(draws) / 2, st.mean(draws) + 3.182 * st.stdev(draws) / 2) if len(draws) == 4 else None
long = {}       # (seed, u) -> F mean and paired difference to corpus_v1, past the paired range
for (s, u), row in pilot.items():
    if u > PAIRED_MAX: long[(s, u)] = {"F": row["F"], "pair": paired(footers(f"kbf_F_s{s}_u{u}_shipped"), corpus)}
R = {}          # read-all control (25 episodes generated and read per update), (seed, u) -> dict with mean and paired difference to corpus_v1
for p in glob.glob(T("kbf_R_s*_u*_shipped")):
    m = re.search(r"kbf_R_s(\d+)_u(\d+)_shipped$", p)
    if m:
        Fp = footers(os.path.basename(p))
        if len(Fp) >= 100: R[(int(m.group(1)), int(m.group(2)))] = {"F": st.mean(Fp.values()), "pair": paired(Fp, corpus)}
def four_draws(arm):
    ds = [arm_mean(arm + sfx)[0] for sfx in ("", "_p9000", "_p9001", "_p9002")]
    if not all(x is not None for x in ds): return None
    m_, sd_ = st.mean(ds), st.stdev(ds)
    return {"draws": ds, "mean": m_, "lo": m_ - 3.182 * sd_ / 2, "hi": m_ + 3.182 * sd_ / 2, "sd": sd_,
            "gap": (band[0] if band else st.mean(corpus.values())) - m_}
draws = {}      # (seed, u) -> the four sampling draws of one F checkpoint (tied, 9000, 9001, 9002), mean and t interval (3 df)
for (s, u) in list(long):
    d = four_draws(f"kbf_F_s{s}_u{u}_shipped")
    if d: draws[(s, u)] = d
rdraws = {(s, u): d for (s, u) in R for d in [four_draws(f"kbf_R_s{s}_u{u}_shipped")] if d}
S, Spair = {}, {}   # S control (fixed layout, workers seeded) checkpoints, (seed, u) -> mean, and the paired difference to corpus_v1
for p in glob.glob(T("kbf_S_s*_u*_shipped")):
    m = re.search(r"kbf_S_s(\d+)_u(\d+)_shipped$", p); mean_, n = arm_mean(os.path.basename(p))
    if m and mean_ is not None:
        S[(int(m.group(1)), int(m.group(2)))] = mean_; Spair[(int(m.group(1)), int(m.group(2)))] = paired(footers(os.path.basename(p)), corpus)
sdraws = {(s, u): d for (s, u) in S for d in [four_draws(f"kbf_S_s{s}_u{u}_shipped")] if d}
EPU = {"F": 5, "S": 5, "R": 25}      # episodes the learner consumes per update, by arm
endpairs = {}   # the controls against the check-on arm at the endpoint, paired over the same 100 episodes on the tied draw
for s in sorted({s for (s, u) in long if u == 2000}):
    Fp = footers(f"kbf_F_s{s}_u2000_shipped")
    if (s, 2000) in S: endpairs[f"S_{s}"] = paired(footers(f"kbf_S_s{s}_u2000_shipped"), Fp)
    if (s, 400) in R: endpairs[f"R_{s}"] = paired(footers(f"kbf_R_s{s}_u400_shipped"), Fp)

# ---------------------------------------------------------------- summary per checkpoint
summary = {}
for u in updates:
    rows = [pilot[(s, u)] for s in seeds if (s, u) in pilot and "Non" in pilot[(s, u)]]
    if len(rows) < 1 or u > PAIRED_MAX: continue
    deltas = [r["pair"]["delta"] for r in rows]
    sd = st.stdev(deltas) if len(deltas) > 1 else float("nan")     # across training seeds, the treatment's replication unit
    tq = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}.get(len(deltas), float("nan"))   # two-sided 95% t quantile for n seeds, n - 1 df
    summary[u] = {"seeds": len(rows), "F": st.mean(r["F"] for r in rows), "Nown": st.mean(r["Nown"] for r in rows),
                  "Non": st.mean(r["Non"] for r in rows), "busy": st.mean(r["busy"] for r in rows),
                  "delta": st.mean(deltas), "min": min(deltas), "max": max(deltas), "sd": sd,
                  "tlo": st.mean(deltas) - tq * sd / len(deltas) ** 0.5, "thi": st.mean(deltas) + tq * sd / len(deltas) ** 0.5,
                  "signp": min(1.0, 2 * 0.5 ** len(deltas)) if all(d > 0 for d in deltas) or all(d < 0 for d in deltas) else None,
                  "fleads": sum(1 for d in deltas if d > 0), "excl": sum(1 for r in rows if r["pair"]["lo"] > 0 or r["pair"]["hi"] < 0)}
out = {"seeds": seeds, "updates": updates, "pilot": {f"{s}_{u}": r for (s, u), r in pilot.items()}, "summary": summary,
       "long": {f"{s}_{u}": r for (s, u), r in long.items()}, "S": {f"{s}_{u}": v for (s, u), v in S.items()},
       "draws": {f"{s}_{u}": d for (s, u), d in draws.items()},
       "R": {f"{s}_{u}": r for (s, u), r in R.items()}, "rdraws": {f"{s}_{u}": d for (s, u), d in rdraws.items()},
       "sdraws": {f"{s}_{u}": d for (s, u), d in sdraws.items()}, "Spair": {f"{s}_{u}": p for (s, u), p in Spair.items()}, "episodes_per_update": EPU,
       "endpairs": endpairs,
       "corpus": st.mean(corpus.values()) if corpus else None, "band": band}
json.dump(out, open(os.path.join(OUT, "curves.json"), "w"), indent=1)

print(f"seeds {seeds}, checkpoints {updates}, corpus_v1 {out['corpus']:.2f}" + (f", reproduction {band[0]:.2f} [{band[1]:.2f}, {band[2]:.2f}]" if band else ""))
for u in updates:
    if u > PAIRED_MAX: continue
    for s in seeds:
        r = pilot.get((s, u))
        if not r: continue
        if "Non" in r:
            p = r["pair"]
            print(f"u{u} s{s}  F {r['F']:.2f}  Nown {r['Nown']:.2f}  Non {r['Non']:.2f}  busy {r['busy']:.1f}  "
                  f"F-Non {p['delta']:+.1f} [{p['lo']:.1f}, {p['hi']:.1f}] wins {p['wins']}/{p['n']}")
        else: print(f"u{u} s{s}  F {r['F']:.2f}  (N not scored)")
    if u in summary:
        m = summary[u]
        print(f"u{u} mean of {m['seeds']} seeds  F {m['F']:.1f}  Nown {m['Nown']:.1f}  Non {m['Non']:.1f}  busy {m['busy']:.1f}  "
              f"F-Non {m['delta']:+.1f} (min {m['min']:+.1f}, max {m['max']:+.1f})  F leads in {m['fleads']} of {m['seeds']}  "
              f"intervals excluding zero {m['excl']} of {m['seeds']}")
        print(f"u{u} across seeds  sd {m['sd']:.1f}  t interval [{m['tlo']:.1f}, {m['thi']:.1f}]  sign test p {m['signp'] if m['signp'] is None else f'{m['signp']:.3f}'}")
late = [u for u in summary if 200 <= u <= PAIRED_MAX]
if late:
    print(f"pairs from u200 on: {sum(summary[u]['seeds'] for u in late)}, F leads in {sum(summary[u]['fleads'] for u in late)}, "
          f"intervals excluding zero {sum(summary[u]['excl'] for u in late)}, "
          f"smallest lead {min(summary[u]['min'] for u in late):+.1f}, largest {max(summary[u]['max'] for u in late):+.1f}")
for (s, u), r in sorted(long.items()):
    p = r["pair"]
    print(f"long u{u} s{s}  F {r['F']:.2f}  F-corpus {p['delta']:+.1f} [{p['lo']:.1f}, {p['hi']:.1f}] wins {p['wins']}/{p['n']}" if p
          else f"long u{u} s{s}  F {r['F']:.2f}")
for (s, u), d in sorted(draws.items()):
    print(f"draws u{u} s{s}  four draws mean {d['mean']:.2f} [{d['lo']:.2f}, {d['hi']:.2f}] sd {d['sd']:.2f}  gap to the released reproduction mean {d['gap']:.1f}  draws " + ", ".join(f"{x:.2f}" for x in d["draws"]))
for (s, u), v in sorted(S.items()):
    p = Spair.get((s, u))
    print(f"S u{u} s{s}  {v:.2f}" + (f"  S-corpus {p['delta']:+.1f} [{p['lo']:.1f}, {p['hi']:.1f}] wins {p['wins']}/{p['n']}" if p else "")
          + (f"  S-F same seed {v - (long.get((s, u)) or pilot.get((s, u)))['F']:+.2f}" if (s, u) in long or (s, u) in pilot else ""))
for (s, u), d in sorted(sdraws.items()):
    print(f"S draws u{u} s{s}  four draws mean {d['mean']:.2f} [{d['lo']:.2f}, {d['hi']:.2f}] sd {d['sd']:.2f}  gap to the released reproduction mean {d['gap']:.1f}  draws " + ", ".join(f"{x:.2f}" for x in d["draws"]))
for (s, u), r in sorted(R.items()):
    p = r["pair"]
    print(f"R u{u} s{s}  {r['F']:.2f}  (the experience of F at {5 * u})" + (f"  R-corpus {p['delta']:+.1f} [{p['lo']:.1f}, {p['hi']:.1f}] wins {p['wins']}/{p['n']}" if p else ""))
for (s, u), d in sorted(rdraws.items()):
    print(f"R draws u{u} s{s}  four draws mean {d['mean']:.2f} [{d['lo']:.2f}, {d['hi']:.2f}] sd {d['sd']:.2f}  gap to the released reproduction mean {d['gap']:.1f}")
for k, p in sorted(endpairs.items()):
    if p: print(f"endpoint pair {k} minus F on the tied draw  {p['delta']:+.1f} [{p['lo']:.1f}, {p['hi']:.1f}] wins {p['wins']}/{p['n']}")

# ---------------------------------------------------------------- table
def num(x, d=2):
    if round(x, d) == 0: return f"{0:.{d}f}"          # no negative zero
    return ("$-$" + f"{abs(x):.{d}f}") if x < 0 else f"{x:.{d}f}"
L = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
     r"Updates & Seed & F & N, check off & N, check on & Restores at busy & F minus N, check on & Wins \\", r"\midrule"]
for u in updates:
    if u > PAIRED_MAX: continue
    for s in seeds:
        r = pilot.get((s, u))
        if not r or "Non" not in r: continue
        p = r["pair"]
        L.append(f"{u} & {s} & {num(r['F'])} & {num(r['Nown'])} & {num(r['Non'])} & {r['busy']:.1f} & "
                 f"{num(p['delta'], 1)} [{num(p['lo'], 0)}, {num(p['hi'], 0)}] & {p['wins']} \\\\")
    if u in summary:
        m = summary[u]
        L.append(f"{u} & mean & {num(m['F'], 1)} & {num(m['Nown'], 1)} & {num(m['Non'], 1)} & {m['busy']:.1f} & "
                 f"{num(m['delta'], 1)} (sd {m['sd']:.1f} across seeds) & F leads in {m['fleads']} of {m['seeds']} \\\\")
    L.append(r"\addlinespace")
if L[-1] == r"\addlinespace": L.pop()
L += [r"\bottomrule", r"\end{tabular}"]
open(os.path.join(OUT, "tab_pilot.tex"), "w").write("\n".join(L) + "\n")
# the continuation in a table of its own (tab_cont.tex), the difference against the released policy on the same episodes
C = [r"\begin{tabular}{llrlr}", r"\toprule", r"Updates & Arm & Mean & Minus the released policy & Wins \\", r"\midrule"]
def crow(u, label, r):
    p = r["pair"]
    return f"{u} & {label} & {num(r['F'])} & " + (f"{num(p['delta'], 1)} [{num(p['lo'], 0)}, {num(p['hi'], 0)}] & {p['wins']}" if p else "&") + r" \\"
def cdraw(u, label, d): return f"{u} & {label}, four draws & {num(d['mean'])} & $t$ interval [{num(d['lo'], 0)}, {num(d['hi'], 0)}] & " + r"\\"
for s in sorted({s for (s, u) in long}):
    for u in sorted(u for (ss, u) in long if ss == s):
        C.append(crow(u, f"F {s}", long[(s, u)]))
        if (s, u) in draws: C.append(cdraw(u, f"F {s}", draws[(s, u)]))
    C.append(r"\addlinespace")
for s in sorted({s for (s, u) in S}):
    for u in sorted(u for (ss, u) in S if ss == s):
        C.append(crow(u, f"S {s}", {"F": S[(s, u)], "pair": Spair.get((s, u))}))
        if (s, u) in sdraws: C.append(cdraw(u, f"S {s}", sdraws[(s, u)]))
    C.append(r"\addlinespace")
for s in sorted({s for (s, u) in R}):
    for u in sorted(u for (ss, u) in R if ss == s):
        C.append(crow(u, f"R {s}", R[(s, u)]))
        if (s, u) in rdraws: C.append(cdraw(u, f"R {s}", rdraws[(s, u)]))
    C.append(r"\addlinespace")
if C[-1] == r"\addlinespace": C.pop()
if not (long or S or R): C.append(r"\multicolumn{5}{l}{continuation pending} \\")
C += [r"\bottomrule", r"\end{tabular}"]
open(os.path.join(OUT, "tab_cont.tex"), "w").write("\n".join(C) + "\n")

# ---------------------------------------------------------------- figure
plt.rcParams.update({"font.size": 8, "font.family": "sans-serif", "axes.edgecolor": GRID, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.7), gridspec_kw={"width_ratios": [1.0, 1.15], "wspace": 0.35})
a = ax[0]
pu = [u for u in updates if u <= PAIRED_MAX]
for s in seeds:
    xs = [u for u in pu if (s, u) in pilot and "Non" in pilot[(s, u)]]
    a.plot(xs, [pilot[(s, u)]["F"] for u in xs], color=BLUE, linewidth=0.6, alpha=0.45)
    a.plot(xs, [pilot[(s, u)]["Non"] for u in xs], color=ORANGE, linewidth=0.6, alpha=0.45)
    a.plot(xs, [pilot[(s, u)]["Nown"] for u in xs], color=ORANGE, linewidth=0.6, alpha=0.45, linestyle=(0, (2, 1.5)))
su = [u for u in pu if u in summary]
a.plot(su, [summary[u]["F"] for u in su], color=BLUE, linewidth=1.8, marker="o", markersize=3.5, label="trained with the check")
a.plot(su, [summary[u]["Non"] for u in su], color=ORANGE, linewidth=1.8, marker="o", markersize=3.5, label="trained without, scored with it on")
a.plot(su, [summary[u]["Nown"] for u in su], color=ORANGE, linewidth=1.8, marker="o", markersize=3.5, linestyle=(0, (2, 1.5)), label="trained without, scored without")
ref = band[0] if band else out["corpus"]
if ref is not None:
    if band: a.axhspan(band[1], band[2], color=GRID, alpha=0.6, linewidth=0, zorder=0)
    a.axhline(ref, color=INK, linewidth=0.8, zorder=0)
    a.text(pu[0] if pu else 100, ref + 25, "released policy", fontsize=7, color=INK, va="bottom")
a.set_xticks(pu); a.set_xlabel("training updates"); a.set_ylabel("mean score, 100 paired episodes")
a.set_title("(a) with and without the check, four seeds", fontsize=8, loc="left", color=INK)
a.legend(frameon=False, fontsize=6.5, loc="lower right")
b = ax[1]       # panel (b) is on an axis of episodes consumed by the learner, so R's updates land at matched experience
X0, X1 = EPU["F"] * PAIRED_MAX, EPU["F"] * 2000
if ref is not None:
    if band: b.axhspan(band[1], band[2], color=GRID, alpha=0.6, linewidth=0, zorder=0)
    b.axhline(ref, color=INK, linewidth=0.8, zorder=0)
    b.text(X0, ref + 8, "released policy, reproduction interval" if band else "released policy", fontsize=7, color=INK, va="bottom")
def bar(x, d, color, alpha):          # a four-draw mean with its t interval, heavier than the single-draw markers
    b.plot([x, x], [d["lo"], d["hi"]], color=color, linewidth=2.5, alpha=alpha, solid_capstyle="butt", zorder=3)
    b.scatter([x], [d["mean"]], s=34, color=color, alpha=min(1.0, alpha + 0.4), linewidths=0, zorder=4)
lseeds = sorted({s for (s, u) in long})
for i, s in enumerate(lseeds):
    xs = [u for u in sorted({u for (ss, u) in long if ss == s})]
    xs = [PAIRED_MAX] + xs if (s, PAIRED_MAX) in pilot else xs
    b.plot([EPU["F"] * u for u in xs], [pilot[(s, u)]["F"] if u <= PAIRED_MAX else long[(s, u)]["F"] for u in xs], color=BLUE, linewidth=1.2,
           marker="o", markersize=3.0, alpha=0.9 - 0.2 * i, label=f"with the check, seed {s}")
    for (ss, u), d in draws.items():
        if ss == s: bar(EPU["F"] * u, d, BLUE, 0.5 - 0.1 * i)
sseeds = sorted({s for (s, u) in S})
for s in sseeds:
    xs = sorted(u for (ss, u) in S if ss == s)
    b.plot([EPU["S"] * u for u in xs], [S[(s, u)] for u in xs], color=QUIET, linewidth=1.2, marker="s", markersize=3.0, label=f"fixed layout, seeded (S), seed {s}")
    for (ss, u), d in sdraws.items():
        if ss == s: bar(EPU["S"] * u, d, QUIET, 0.5)
rseeds = sorted({s for (s, u) in R})
for i, s in enumerate(rseeds):
    xs = sorted(u for (ss, u) in R if ss == s)
    b.plot([EPU["R"] * u for u in xs], [R[(s, u)]["F"] for u in xs], color=ORANGE, linewidth=1.2, marker="^", markersize=3.5, alpha=0.9 - 0.3 * i,
           linestyle="-" if i == 0 else (0, (3, 1.5)), label=f"read all 25 (R), seed {s}")
    for (ss, u), d in rdraws.items():
        if ss == s: bar(EPU["R"] * u, d, ORANGE, 0.5 - 0.15 * i)
if not long and not S and not R:
    b.text(0.5, 0.5, "continuation pending", transform=b.transAxes, ha="center", va="center", fontsize=8, color=QUIET)
b.set_xticks([X0, 4000, 6000, 8000, X1]); b.set_xlim(X0 - 300, X1 + 300)
b.set_xlabel("episodes consumed by the learner")
b.set_title("(b) the check-on arm continued, with the two controls", fontsize=8, loc="left", color=INK)
if long or S or R: b.legend(frameon=False, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, handlelength=1.6, columnspacing=1.2)   # below the axes, clear of every curve
for p in ("curves.pdf", "curves.png"): fig.savefig(os.path.join(OUT, p), dpi=200, bbox_inches="tight")
print("wrote curves.pdf, curves.png, curves.json, tab_pilot.tex, tab_cont.tex")
