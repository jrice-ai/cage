#!/usr/bin/env python3
"""Appendix B: every arm the ledger cites, with n, mean and sd recomputed from its traces and its
defender, adversary, supervision and delivery parsed from the arm name. Writes fig/tab_arms.tex."""
import csv, glob, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
CAGE = os.environ.get("CAGE", os.path.expanduser("~/cage"))
ledger = os.path.join(HERE, "..", "ledger.csv")

def expand(t):
    m = re.search(r"\{([^}]*)\}", t)
    if not m: return [t]
    return [x for alt in m.group(1).split(",") for x in expand(t[:m.start()] + alt + t[m.end():])]
def is_arm_dir(d):
    return os.path.isdir(d) and bool(glob.glob(os.path.join(d, "ep_*.jsonl")) or os.path.exists(os.path.join(d, "scores.txt")))
cands = set()
for r in csv.DictReader(open(ledger, newline="")):
    for field in ("arm", "cmd"):                       # arms named directly, and arms a command reads
        for t in re.split(r"[\s;]+", r.get(field, "")):
            t = t.strip(",").split("/")[-1]
            parts = [t] if "{" in t else t.split(",")
            for q in parts:
                if re.fullmatch(r"[A-Za-z0-9_{},*]+", q) and len(q) > 3: cands.update(expand(q))
arms = set()
for c in cands:
    for d in glob.glob(os.path.join(CAGE, "data", "**", c), recursive=True):
        if is_arm_dir(d): arms.add(os.path.basename(d))
arms = sorted(arms)
def arm_dir(a):
    hits = [d for d in glob.glob(os.path.join(CAGE, "data", "**", a), recursive=True) if is_arm_dir(d)]
    return hits[0] if hits else None

def stats(d):
    sc = os.path.join(d, "scores.txt"); files = sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))
    if not files and os.path.exists(sc):
        kv = dict(l.split(":", 1) for l in open(sc) if ":" in l)
        return int(float(kv.get("episodes", kv.get("n", 100)))), float(kv["reward_mean"]), float(kv["reward_stdev"])
    xs = []
    for f in files:
        rec = json.loads([l for l in open(f) if l.strip()][-1])
        if rec.get("record") == "footer": xs.append(rec["total_reward"])
    if not xs: return 0, float("nan"), float("nan")
    m = sum(xs) / len(xs); sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5 if len(xs) > 1 else float("nan")
    return len(xs), m, sd

def parse(a):
    """defender, adversary, supervision, delivery from the arm name."""
    dfd, adv, sup, dlv = "KEEP", "stock", "none", ""
    if a.startswith("hm_") or a.startswith("hmarl"): dfd = "H-MARL Expert"
    if a.startswith("rd_"): dfd = "rule defender " + a.split("_")[1]
    if a.startswith("k_kft_"): dfd = "KEEP cont. " + re.search(r"_s(\d+)", a).group(1)
    if a == "arm_keep_greedy": dfd = "KEEP, argmax actions"
    if "_busy_none" in a: dfd = ("H-MARL Expert, busy mask off" if a.startswith("hm_") else "KEEP, busy check off")
    if a == "arm_sleep": dfd = "Sleep policy"
    if a == "arm_monitor": dfd = "Monitor every step"
    if a == "arm_analyse": dfd = "Sleep and Analyse alternating"
    if a.startswith("red_"):
        nm = a[4:]
        nm = nm[len("FSRedAgent"):] if nm.startswith("FSRedAgent") else nm
        adv = "stock" if nm == "FiniteStateRedAgent" else re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[A-Z])(?=[A-Z][a-z])", " ", nm)   # Target A Operational, Wrecker Q32
    if re.search(r"(^|_)wo?_|wrecker|Wrecker", a) and not a.startswith("red_"): adv = "Wrecker"
    if "WreckerQ32" in a and not a.startswith("red_"): adv = "Wrecker Q32"
    mm = re.search(r"_FSRedAgent([A-Za-z0-9]+?)(_wb|$)", a)
    if mm and not a.startswith("red_"):
        adv = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[A-Z])(?=[A-Z][a-z])", " ", mm.group(1)); adv = "stock" if adv == "Finite State Red Agent" else adv
    if re.search(r"_p9\d{3}$", a): sup_draw = "seed " + a[-4:]
    else: sup_draw = None
    m = re.search(r"(^|_)([Oo]\d+[a-z]?)(_|$)", a)
    if m: sup = "O" + m.group(2)[1:]
    if a == "latch_wrecker": sup = "O2e"
    if re.search(r"_g(\d+)", a): sup += ", gap " + re.search(r"_g(\d+)", a).group(1) if sup != "none" else ""
    if re.search(r"_b(\d+)", a): sup += ", budget " + re.search(r"_b(\d+)", a).group(1)
    if a.endswith("_wb"): dlv = "held"
    elif sup != "none": dlv = "fired"
    if "_qf" in a: dlv = "queue first"
    if "null" in a: sup = "seed " + (a[-4:] if a[-4:].isdigit() else "9000")
    if sup_draw: sup = sup_draw
    if a.startswith("hmarl_s"): sup = "none, authors' path seed " + a[-1]
    if a == "hmarl_metrics_s0": sup = "none, authors' metrics script, seed 0"
    if a == "hmarl_expert_output": sup = "none, unseeded"
    if a.startswith("keep_null"): sup = "seed " + (a.split("_")[-1] if a[-1].isdigit() else "9000")
    adv = adv.replace("Conv Only", "ConvOnly")
    return dfd, adv, sup, dlv

def tex(s): return s.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")
def texarm(s): return s.replace("_", r"\textunderscore\allowbreak{}").replace("FSRedAgent", r"FSRedAgent\allowbreak{}")
def mfmt(x): return (r"$-$" + f"{abs(x):.2f}") if x < 0 else f"{x:.2f}"      # let long arm names break at underscores
rows = []; short = []
for a in arms:
    n, m, sd = stats(arm_dir(a)); dfd, adv, sup, dlv = parse(a)
    if n != 100: short.append((a, n)); continue
    rows.append(f"\\texttt{{{texarm(a)}}} & {tex(dfd)} & {tex(adv)} & {tex(sup)} & {dlv} & {mfmt(m)} & {sd:.2f} \\\\")
spec = r"L{0.24\linewidth}L{0.15\linewidth}L{0.13\linewidth}L{0.14\linewidth}L{0.09\linewidth}rr"
head = r"Arm & Defender & Adversary & Supervision & Delivery & Mean & SD \\"
cap = (r"\caption{Arms cited in this paper, \episodes\ episodes each. Reference arms are KEEP's four sampling seeds and H-MARL's four seeds of the authors' evaluation path. "
       r"The null draws and redraws of \secref{sec:noise} are \texttt{keep\_null*}, \texttt{wrecker\_null*}, \texttt{hm\_s\_none\_p*} and \texttt{hm\_w\_none\_p*}, labeled by policy seed, and KEEP cont.\ $n$ is a continuation of the shipped checkpoint trained from seed $n$. "
       r"Arms named \texttt{red\_*} run KEEP against the named red agent through the harness.}\label{tab:arms}\\")
body = ("\n".join([r"\begingroup\scriptsize\setlength{\tabcolsep}{3pt}", r"\begin{longtable}{" + spec + "}", cap,
                   r"\toprule", head, r"\midrule", r"\endfirsthead",
                   r"\multicolumn{7}{l}{\footnotesize Table~\ref{tab:arms}, continued}\\", r"\toprule", head, r"\midrule", r"\endhead",
                   r"\bottomrule", r"\endfoot"] + rows + [r"\end{longtable}", r"\endgroup"]) + "\n")
open(os.path.join(HERE, "tab_arms.tex"), "w").write(body)
print(f"wrote tab_arms.tex, {len(arms)} arms")
print("arms", len(rows), "skipped, not 100 episodes:", short)
