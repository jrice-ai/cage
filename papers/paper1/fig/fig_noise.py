#!/usr/bin/env python3
"""Figure: what a score is made of. (a) sampling share of outcome variance at two adversaries, random effects with
bootstrap intervals; (b) the six H-MARL control draws against their centre; (c) three continuations of one training
run from three seeds, against the shipped weights. Writes fig/noise.pdf, noise.png, noise.json."""
import glob, json, os, random
from statistics import mean, variance, stdev
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

CAGE = os.environ.get("CAGE", os.path.expanduser("~/cage"))
T = lambda a: os.path.join(CAGE, "data", "traces", a)
OUT = os.path.dirname(os.path.abspath(__file__))
BLUE, ORANGE, INK, QUIET, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#d9d8d3"

def footers(arm):
    out = {}
    for f in sorted(glob.glob(os.path.join(T(arm), "ep_*.jsonl"))):
        r = json.loads([l for l in open(f) if l.strip()][-1])
        if r.get("record") == "footer": out[os.path.basename(f)] = r["total_reward"]
    return out

def decompose(arms, eps):
    k = len(arms)
    within = mean(variance([a[e] for a in arms]) for e in eps)
    vm = variance([mean(a[e] for a in arms) for e in eps])
    dif = max(vm - within / k, 0.0)
    return within / (within + dif)

def share(arm_names, nboot=4000):
    arms = [footers(a) for a in arm_names]; eps = sorted(set.intersection(*[set(a) for a in arms]))
    s = decompose(arms, eps); random.seed(0)
    boots = sorted(decompose(arms, [random.choice(eps) for _ in eps]) for _ in range(nboot))
    return s, boots[int(0.025 * nboot)], boots[int(0.975 * nboot)], len(eps)

stock = share(["corpus_v1", "keep_null", "keep_null_9001", "keep_null_9002"])
wreck = share(["red_FSRedAgentWrecker", "wrecker_null_9000", "wrecker_null_9001", "wrecker_null_9002", "wrecker_null_9003", "wrecker_null_9004"])
hmw = share(["hm_w_none", "hm_w_none_p9000", "hm_w_none_p9001", "hm_w_none_p9002", "hm_w_none_p9003", "hm_w_none_p9004"])
hms = share(["hm_s_none", "hm_s_none_p9000", "hm_s_none_p9001", "hm_s_none_p9002"])
hms6 = share(["hm_s_none", "hm_s_none_p9000", "hm_s_none_p9001", "hm_s_none_p9002", "hm_s_none_p9003", "hm_s_none_p9004"])
draws = {a: mean(footers(a).values()) for a in ["hm_w_none", "hm_w_none_p9000", "hm_w_none_p9001", "hm_w_none_p9002", "hm_w_none_p9003", "hm_w_none_p9004"]}
centre = mean(draws.values())
ctl = footers("red_FSRedAgentWreckerQ32")
conts = {}
for seed in ["s1000", "s1001", "s1002"]:
    A = footers(f"k_kft_WreckerQ32_{seed}_final_WreckerQ32_none"); eps = sorted(set(A) & set(ctl))
    d = [A[e] - ctl[e] for e in eps]; conts[seed] = (mean(d), sum(1 for x in d if x > 0), len(d))
out = {"stock": stock, "wrecker": wreck, "hmarl_wrecker": hmw, "hmarl_stock": hms, "hmarl_stock_six": hms6, "draws": draws, "centre": centre, "continuations": conts}
json.dump(out, open(os.path.join(OUT, "noise.json"), "w"), indent=1)
print(f"stock share {stock[0]:.3f} [{stock[1]:.3f}, {stock[2]:.3f}]  wrecker {wreck[0]:.3f} [{wreck[1]:.3f}, {wreck[2]:.3f}]  hmarl wrecker {hmw[0]:.3f} [{hmw[1]:.3f}, {hmw[2]:.3f}]  hmarl stock {hms[0]:.3f} [{hms[1]:.3f}, {hms[2]:.3f}]  hmarl stock six {hms6[0]:.3f} [{hms6[1]:.3f}, {hms6[2]:.3f}]")
print(f"H-MARL centre {centre:.2f}, control above centre by {draws['hm_w_none']-centre:.1f}")
print("continuations " + ", ".join(f"{k} {v[0]:+.1f} ({v[1]}/{v[2]})" for k, v in conts.items()))

plt.rcParams.update({"font.size": 8, "font.family": "sans-serif", "axes.edgecolor": GRID, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.4), gridspec_kw={"width_ratios": [1.0, 1.2, 1.1], "wspace": 0.7})

a = ax[0]
for i, (lab, (s, lo, hi, n)) in enumerate([("stock red", stock), ("Wrecker", wreck)]):
    a.plot([100 * lo, 100 * hi], [i, i], color=GRID, linewidth=3, solid_capstyle="butt", zorder=1)
    a.scatter([100 * s], [i], s=30, color=BLUE, zorder=2, linewidths=0)
    a.text(100 * s, i - 0.25, f"{100 * s:.1f}%", ha="center", va="bottom", fontsize=7, color=INK)
a.set_yticks([0, 1]); a.set_yticklabels(["stock red", "Wrecker"]); a.set_ylim(-0.7, 1.7); a.invert_yaxis()
a.set_xlim(0, 106); a.set_xticks([0, 50, 100]); a.axvline(50, color=GRID, linewidth=0.8, zorder=0)
a.set_xlabel("sampling share of\noutcome variance, %"); a.set_title("(a) the policy's own draw", fontsize=8, loc="left", color=INK)

b = ax[1]
names = list(draws); vals = [draws[k] for k in names]
b.scatter(range(len(names)), vals, s=30, color=[ORANGE] + [BLUE] * 5, linewidths=0, zorder=2)
b.axhline(centre, color=INK, linewidth=1.0, zorder=1); b.text(-0.45, centre + 2, f"null center {centre:.0f}".replace("-", "\u2212"), va="bottom", ha="left", fontsize=7, color=INK)
b.text(0.3, draws["hm_w_none"], f"control {draws['hm_w_none']:.0f}".replace("-", "\u2212"), ha="left", va="center", fontsize=7, color=INK)
b.set_xticks(range(len(names))); b.set_xticklabels(["ctl", "s0", "s1", "s2", "s3", "s4"], fontsize=7); b.set_xlabel("H-MARL control, then five redraws")
b.set_xlim(-0.6, 5.6); b.set_ylim(min(vals) - 10, max(vals) + 14); b.set_ylabel("mean score, 100 episodes"); b.set_title("(b) six draws of one control", fontsize=8, loc="left", color=INK)

c = ax[2]
for i, (seed, (m, w, n)) in enumerate(conts.items()):
    c.bar(i, m, 0.55, color=BLUE if m > 0 else ORANGE, linewidth=0)
    c.text(i, m + (6 if m > 0 else -6), f"{m:+.0f}\n{w} of {n}".replace("-", "\u2212"), ha="center", va="bottom" if m > 0 else "top", fontsize=6.5, color=INK, linespacing=1.1)
c.axhline(0, color=GRID, linewidth=0.8, zorder=0)
c.set_xticks(range(3)); c.set_xticklabels(["1000", "1001", "1002"], fontsize=7); c.set_xlabel("training seed"); c.set_ylim(-185, 150); c.set_xlim(-0.8, 2.8)
c.set_ylabel("final minus shipped, points"); c.set_title("(c) one training run, three seeds", fontsize=8, loc="left", color=INK)

for p in ("noise.pdf", "noise.png"): fig.savefig(os.path.join(OUT, p), dpi=200, bbox_inches="tight")
print("wrote noise.pdf, noise.png, noise.json")
