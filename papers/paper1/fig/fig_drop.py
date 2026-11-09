#!/usr/bin/env python3
"""Figure: the silent drop. Reads the four O1 arms, the two controls and the held ceiling from $CAGE/data/traces,
computes everything it draws, writes fig/drop.pdf, fig/drop.png and fig/drop.json (the numbers behind each mark).
usage: python3 fig_drop.py"""
import glob, json, os, sys
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CAGE = os.environ.get("CAGE", os.path.expanduser("~/cage"))
T = lambda a: os.path.join(CAGE, "data", "traces", a)
OUT = os.path.dirname(os.path.abspath(__file__))
DUR = {"Restore": 5, "Remove": 3, "Analyse": 2, "DeployDecoy": 2}
HELD, FIRED, INK, QUIET, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#d9d8d3"

def rows(f):
    return [json.loads(l) for l in open(f) if l.strip()]

def footers(arm):
    out = {}
    for f in sorted(glob.glob(os.path.join(T(arm), "ep_*.jsonl"))):
        r = rows(f)[-1]
        if r.get("record") == "footer": out[os.path.basename(f)] = r["total_reward"]
    return out

def executed_at(steps, i, agent, typ, host):
    k = DUR.get(typ, 1) - 1                      # an accepted directive completes at exactly t + d - 1
    if i + k >= len(steps): return None
    a = (steps[i + k].get("action") or steps[i + k].get("actions") or {}).get(agent, "")
    return k if a.startswith(f"[{typ} {host}") else None

def drop_stats(arm):
    prop = ok = busy = agent_steps = 0
    for f in sorted(glob.glob(os.path.join(T(arm), "ep_*.jsonl"))):
        rs = rows(f); steps = [r for r in rs if r.get("record") == "step"]
        if not steps or rs[-1].get("record") != "footer": continue
        for i, r in enumerate(steps):
            for agent, a in (r.get("action") or r.get("actions") or {}).items():
                agent_steps += 1; busy += max(0, DUR.get(a.strip("[]").split(" ")[0], 1) - 1)
            for agent, frm, to in r.get("overrides", []):
                typ, _, host = to.partition(":"); prop += 1
                if executed_at(steps, i, agent, typ, host) is not None: ok += 1
    return {"busy": busy / agent_steps, "exec": ok / max(prop, 1), "proposed": prop, "executed": ok}

defenders = [("KEEP", "red_FSRedAgentWrecker", "wo_O1_g32", "wo_O1_g32_wb"),
             ("H-MARL", "hm_w_none", "hm_wo_O1_g32", "hm_wo_O1_g32_wb")]
ceiling = footers("rd_RT_w_none_wb")
data = {}
for name, ctl, fired, held in defenders:
    C, F, H = footers(ctl), footers(fired), footers(held)
    eps = sorted(set(C) & set(F) & set(H) & set(ceiling))
    gap = sum(ceiling[e] - C[e] for e in eps) / len(eps)
    dF = sum(F[e] - C[e] for e in eps) / len(eps); dH = sum(H[e] - C[e] for e in eps) / len(eps)
    paired = [H[e] - F[e] for e in eps]
    data[name] = {"n": len(eps), "fired": drop_stats(fired), "held": drop_stats(held),
                  "gain_fired": dF, "gain_held": dH, "share_fired": dF / gap, "share_held": dH / gap, "gap": gap,
                  "paired_mean": sum(paired) / len(paired), "paired_wins": sum(1 for x in paired if x > 0), "paired": paired}
    print(f"{name}: busy {data[name]['fired']['busy']:.3f}/{data[name]['held']['busy']:.3f}  exec {data[name]['fired']['exec']:.3f}/{data[name]['held']['exec']:.3f}  "
          f"share {dF/gap:.3f} -> {dH/gap:.3f}  paired +{data[name]['paired_mean']:.1f} ({data[name]['paired_wins']}/{len(eps)})")
json.dump({k: {kk: vv for kk, vv in v.items() if kk != "paired"} for k, v in data.items()}, open(os.path.join(OUT, "drop.json"), "w"), indent=1)

plt.rcParams.update({"font.size": 8, "font.family": "sans-serif", "axes.edgecolor": GRID, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.4), gridspec_kw={"width_ratios": [1.0, 1.35, 1.0], "wspace": 0.6})
names = [d[0] for d in defenders]; x = range(len(names)); w = 0.34

# (a) share of directives that executed, fired against held, with the busy share as a quiet label
a = ax[0]
for i, n in enumerate(names):
    fe, he = 100 * data[n]["fired"]["exec"], 100 * data[n]["held"]["exec"]
    a.bar(i - w/2, fe, w, color=FIRED, linewidth=0)
    a.bar(i + w/2, he, w, color=HELD, linewidth=0)
    a.text(i - w/2, fe + 2, f"{fe:.0f}%", ha="center", va="bottom", fontsize=6, color=INK)
    a.text(i + w/2, he + 2, f"{he:.0f}%", ha="center", va="bottom", fontsize=6, color=INK)
a.set_xticks(list(x)); a.set_xticklabels(names); a.set_ylim(0, 132); a.set_yticks([0, 50, 100])
a.set_ylabel("interventions executed, %"); a.set_title("(a) execution", fontsize=8, loc="left", color=INK)
a.bar(0, 0, color=FIRED, label="fired"); a.bar(0, 0, color=HELD, label="held"); a.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2, handlelength=0.8, columnspacing=1.0)

# (b) paired per-episode gain from holding, one strip per defender
b = ax[1]
import random; random.seed(0)
for i, n in enumerate(names):
    ys = data[n]["paired"]; xs = [i + random.uniform(-0.22, 0.22) for _ in ys]
    b.scatter(xs, ys, s=6, color=HELD, alpha=0.45, linewidths=0)
    m = data[n]["paired_mean"]
    b.plot([i - 0.3, i + 0.3], [m, m], color=INK, linewidth=1.4)
lo = min(min(data[n]["paired"]) for n in names); hi = max(max(data[n]["paired"]) for n in names)
for i, n in enumerate(names):
    m = data[n]["paired_mean"]
    b.text(i, lo - 90, f"+{m:.0f}\n{data[n]['paired_wins']} of {data[n]['n']}", va="top", ha="center", fontsize=6.5, color=INK, linespacing=1.1)
b.set_ylim(lo - 620, hi + 120)
b.axhline(0, color=GRID, linewidth=0.8, zorder=0)
b.set_xticks(list(x)); b.set_xticklabels(names); b.set_xlim(-0.6, 2.0)
b.set_ylabel("gain from holding, points"); b.set_title("(b) the same rule, delivered held", fontsize=8, loc="left", color=INK)

# (c) share of the distance to the ceiling closed, fired against held
c = ax[2]
for i, n in enumerate(names):
    sf, sh = 100 * data[n]["share_fired"], 100 * data[n]["share_held"]
    c.plot([sf, sh], [i, i], color=GRID, linewidth=1.2, zorder=1)
    c.scatter([sf], [i], s=28, color=FIRED, zorder=2, linewidths=0); c.scatter([sh], [i], s=28, color=HELD, zorder=2, linewidths=0)
    c.text(sf, i - 0.22, f"{sf:.1f}%", ha="center", va="top", fontsize=7, color=INK)
    c.text(sh, i + 0.22, f"{sh:.1f}%", ha="center", va="bottom", fontsize=7, color=INK)
c.set_yticks(list(x)); c.set_yticklabels(names); c.set_ylim(-0.7, 1.7); c.set_xlim(0, 100); c.set_xticks([0, 50, 100])
c.set_xlabel("share of the distance\nto the RT reference closed, %"); c.set_title("(c) directability", fontsize=8, loc="left", color=INK)
c.invert_yaxis()

for p in (os.path.join(OUT, "drop.pdf"), os.path.join(OUT, "drop.png")):
    fig.savefig(p, dpi=200, bbox_inches="tight")
print("wrote drop.pdf, drop.png, drop.json")
