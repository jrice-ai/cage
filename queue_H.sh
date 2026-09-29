#!/bin/bash
# Queue H, 2026-09-29: a person's eyes and hands, and the displays that could feed them. All arms
# 100 episodes under Wrecker, gap 32, the directive held, unless named otherwise.
#   2a  The eyes surface: O1 through a detector with recall R and false-alarm share F (O1n), ten
#       points and the surface's zero; O2f held, and O1n at the latch's own measured R and F, which
#       tests whether a real detector sits where its R and F put it. Three points on H-MARL.
#   2b  A person's hands: O1 with the click held (--queue first) and a delay, a wrong-host rate or a
#       skip rate (O1h); a typical and a tired profile on both defenders; the typical person on a
#       detector at R 0.75, F 0.05.
#   2c  The trial's condition: the loss thermostat with the click held, with and without the
#       typical person; its matched timer (gap 64) held; H-MARL's thermostat held.
#   2d  R2's triage as a supervisor (O16t) at gaps 32 and 8, under the stock red, and on H-MARL.
#   2e  The policy's own suspicion, surveyed (O17 at --engage 1e9: KEEP alone, the signal logged).
#   2f  O1 on one agent at a time, and on the two agents O1 acts for most.
# 44 arms, two lanes, about two and a half hours. An arm with fewer than 100 footers is cleared
# through the container (no sudo) and run again once. Exit lines in data/ft_runs.log.
#   nohup ./queue_H.sh > /dev/null 2>&1 &     launch
#   ./queue_H.sh read                          read, after "queue_H done" appears in data/ft_runs.log
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
W=FSRedAgentWrecker; S=FiniteStateRedAgent; B="--budget 99999"
nfoot() { local n=0 f; for f in data/traces/$1/ep_*.jsonl; do [ -f "$f" ] && tail -n 1 "$f" | grep -q '"footer"' && n=$((n+1)); done; echo $n; }
arm() {    # arm IMAGE WORKDIR SCRIPT RULE RED OUT [flags]
  local img=$1 wd=$2 py=$3 rule=$4 red=$5 out=$6; shift 6
  [ -n "$out" ] || return
  [ "$(nfoot $out)" -ge 100 ] && { echo "$out skipped, exists $(date)" >> data/ft_runs.log; return; }
  for try in 1 2; do
    [ -d data/traces/$out ] && bin/run $img bash -c "rm -rf /work/data/traces/$out"
    bin/run $img bash -c "cd $wd && python3 -u /work/scripts/$py --rule $rule $* --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
    echo "$out exit $? try $try $(date)" >> data/ft_runs.log
    [ "$(nfoot $out)" -ge 100 ] && return
  done
  echo "$out INCOMPLETE after two tries $(date)" >> data/ft_runs.log
}
keep() { arm cage-keep:dev /opt/cage/cage-4-submission oracle.py "$@"; }
hm() { arm cage-hmarl:dev /work/repos/Hierarchical-MARL/h-marl-3policy capture_hmarl.py "$@"; }
latch_rf() {   # the O2f latch's recall and false-alarm share per free agent-tick, from an arm's footers
  python3 - "$1" <<'EOF'
import glob, json, sys
tp = fp = fn = own = 0
for f in glob.glob(f"data/traces/{sys.argv[1]}/ep_*.jsonl"):
    r = json.loads(open(f).read().strip().splitlines()[-1])
    if r.get("record") == "footer":
        tp += r["latch_tp"]; fp += r["latch_fp"]; fn += r["latch_fn"]; own += r["latch_own"]
print(f"{tp / (tp + fn):.3f} {min(0.95, fp / max(1, own - tp - fn)):.4f}")
EOF
}
top2() {       # the two agents O1 acts for most, from wo_O1_g32_wb's step records
  python3 - <<'EOF'
import collections, glob, json
c = collections.Counter()
for f in glob.glob("data/traces/wo_O1_g32_wb/ep_*.jsonl"):
    for l in open(f):
        r = json.loads(l)
        if r.get("record") == "step":
            for o in r.get("overrides", []): c[o[0]] += 1
print(",".join(sorted(a[-1] for a, _ in c.most_common(2))))
EOF
}
Q="--min-gap 32 $B --queue first"; TYP="--delay 2 --wrong 0.1 --skip 0.2"; TIRED="--delay 4 --wrong 0.25 --skip 0.4"
lane1() {
  keep O1 $W wo_O1n_r100_f000_g32_wb --min-gap 32 $B --recall 1 --false-alarm 0
  for spec in "0.75 0 r075_f000" "0.5 0 r050_f000" "0.25 0 r025_f000" "1 0.02 r100_f002" "1 0.05 r100_f005" \
              "1 0.1 r100_f010" "1 0.2 r100_f020" "0.75 0.05 r075_f005" "0.5 0.05 r050_f005" "0.5 0.1 r050_f010"; do
    set -- $spec; keep O1 $W wo_O1n_$3_g32_wb --min-gap 32 $B --recall $1 --false-alarm $2
  done
  keep O2f $W wo_O2f_g32_wb --min-gap 32 $B
  rf=$(latch_rf wo_O2f_g32_wb); echo "latch recall and false-alarm share from wo_O2f_g32_wb: $rf $(date)" >> data/ft_runs.log
  [ -n "$rf" ] && { set -- $rf; keep O1 $W wo_O1n_latch_g32_wb --min-gap 32 $B --recall $1 --false-alarm $2; }
  for i in 0 1 2 3 4; do keep O1 $W wo_O1_a${i}_g32_wb --min-gap 32 $B --agents $i; done
  pair=$(top2); echo "top two agents by O1 overrides: $pair $(date)" >> data/ft_runs.log
  [ -n "$pair" ] && keep O1 $W wo_O1_a${pair//,/}_g32_wb --min-gap 32 $B --agents $pair
  keep O16t $W wo_O16t_g32_wb --min-gap 32 $B
  keep O16t $W wo_O16t_g8_wb --min-gap 8 $B
  keep O16t $S so_O16t_g32_wb --min-gap 32 $B
}
lane2() {
  keep O1 $W wo_O1h_typ_g32_wb $Q $TYP
  keep O1 $W wo_O1h_tired_g32_wb $Q $TIRED
  for d in 2 4 8; do keep O1 $W wo_O1h_d${d}_g32_wb $Q --delay $d; done
  for spec in "0.1 w10" "0.25 w25" "0.5 w50" ; do set -- $spec; keep O1 $W wo_O1h_$2_g32_wb $Q --wrong $1; done
  for spec in "0.25 s25" "0.5 s50"; do set -- $spec; keep O1 $W wo_O1h_$2_g32_wb $Q --skip $1; done
  keep O1 $W wo_O1h_typ_r075_f005_g32_wb $Q $TYP --recall 0.75 --false-alarm 0.05
  keep O15r $W wo_O15r_e24_g32_qf_wb --engage 24 $Q
  keep O15r $W wo_O15r_e24_g32_typ_wb --engage 24 $Q $TYP
  keep O1 $W wo_O1_g64_qf_wb --min-gap 64 $B --queue first
  keep O17 $W svy_wo_O17_wb --engage 1e9 --min-gap 32 $B
  hm O1 $W hm_wo_O1h_typ_g32_wb $Q $TYP
  hm O1 $W hm_wo_O1h_tired_g32_wb $Q $TIRED
  for spec in "0.5 0 r050_f000" "1 0.05 r100_f005" "0.5 0.05 r050_f005"; do
    set -- $spec; hm O1 $W hm_wo_O1n_$3_g32_wb --min-gap 32 $B --recall $1 --false-alarm $2
  done
  hm O15r $W hm_wo_O15r_e10_g32_qf_wb --engage 10 $Q
  hm O16t $W hm_wo_O16t_g32_wb --min-gap 32 $B
}

# ------------------------------------------------------------------------------------ read
foot() {   # footer means per arm, for the bookkeeping tools_gate.py does not print
  python3 - "$@" <<'EOF'
import glob, json, sys
KEYS = ("overrides", "deferred", "queued", "queue_fired", "queue_stale", "h_skip", "h_wrong", "analyses", "restores", "exec_clean", "agreements")
for d in sys.argv[1:]:
    rows = []
    for f in sorted(glob.glob(f"data/traces/{d}/ep_*.jsonl")):
        r = json.loads(open(f).read().strip().splitlines()[-1])
        if r.get("record") == "footer": rows.append(r)
    if not rows: print(f"{d}: no footers"); continue
    m = lambda k: sum(r.get(k, 0) for r in rows) / len(rows)
    line = f"{d:34} n {len(rows):3} mean {m('total_reward'):7.1f}  " + "  ".join(f"{k} {m(k):.1f}" for k in KEYS if m(k))
    if m("restores"): line += f"  clean share of restores {m('exec_clean') / m('restores'):.2f}"
    print(line)
EOF
}
rates() {  # where an arm's eyes sit: realized recall and false-alarm share per free agent-tick
  python3 - "$@" <<'EOF'
import glob, json, sys
print(f"{'arm':34} {'eyes':6} {'recall':>7} {'false':>7} {'restores':>9} {'clean share':>12}")
for d in sys.argv[1:]:
    t = {}; n = 0
    for f in glob.glob(f"data/traces/{d}/ep_*.jsonl"):
        r = json.loads(open(f).read().strip().splitlines()[-1])
        if r.get("record") != "footer": continue
        n += 1
        for k, v in r.items():
            if isinstance(v, (int, float)): t[k] = t.get(k, 0) + v
    if not n: print(f"{d:34} no footers"); continue
    g = lambda k: t.get(k, 0)
    if g("eyes_clean"): src, tp, fp, fn, clean = "model", g("eyes_tp"), g("eyes_fp"), g("eyes_fn"), g("eyes_clean")
    elif g("sup_own"): src, tp, fp, fn, clean = "R2", g("sup_tp"), g("sup_fp"), g("sup_fn"), g("sup_own") - g("sup_tp") - g("sup_fn")
    elif g("latch_own"): src, tp, fp, fn, clean = "latch", g("latch_tp"), g("latch_fp"), g("latch_fn"), g("latch_own") - g("latch_tp") - g("latch_fn")
    else: print(f"{d:34} no eyes recorded"); continue
    rs = g("restores") / n
    print(f"{d:34} {src:6} {tp / max(1, tp + fn):7.3f} {fp / max(1, clean):7.4f} {rs:9.1f} {g('exec_clean') / max(1, g('restores')):12.2f}")
EOF
}
svy17() {  # the policy's own suspicion against the truth, from the survey's step records
  python3 - <<'EOF'
import glob, json
rows = []
for f in sorted(glob.glob("data/traces/svy_wo_O17_wb/ep_*.jsonl")):
    for l in open(f):
        r = json.loads(l)
        if r.get("record") == "step" and "signal" in r:
            rows += list(r["signal"].values())
if not rows: print("no signal records"); raise SystemExit
n = len(rows); wc = [x for x in rows if x[4] > 0]
print(f"free agent-ticks {n}; with a compromised owned host {len(wc)} ({len(wc) / n:.2f})")
print(f"the top suspect is compromised, when some host is: {sum(x[1] for x in wc) / len(wc):.3f}")
print(f"some compromised host outscores every clean one: {sum(1 for x in wc if x[2] > x[3]) / len(wc):.3f}")
tops = sorted(x[0] for x in rows); q = lambda p: tops[min(n - 1, int(p * n))]
print("top score at quantile   engaged share   precision   recall")
for p in (0.5, 0.75, 0.9, 0.95, 0.99):
    th = q(p); eng = [x for x in rows if x[0] >= th]
    prec = sum(x[1] for x in eng) / len(eng)
    rec = sum(1 for x in wc if x[0] >= th and x[1]) / len(wc)
    print(f"{p:4.2f}  {th:10.4f}   {len(eng) / n:13.3f}   {prec:9.3f}   {rec:6.3f}")
EOF
}
G() { python3 tools_gate.py "$@"; }
P() { python3 tools_paired.py "$@" 2>&1 | grep -v '^warning' | tail -n +2; }
read_all() {
  EYES="wo_O1n_r100_f000_g32_wb wo_O1n_r075_f000_g32_wb wo_O1n_r050_f000_g32_wb wo_O1n_r025_f000_g32_wb wo_O1n_r100_f002_g32_wb wo_O1n_r100_f005_g32_wb wo_O1n_r100_f010_g32_wb wo_O1n_r100_f020_g32_wb wo_O1n_r075_f005_g32_wb wo_O1n_r050_f005_g32_wb wo_O1n_r050_f010_g32_wb"
  HANDS="wo_O1h_typ_g32_wb wo_O1h_tired_g32_wb wo_O1h_d2_g32_wb wo_O1h_d4_g32_wb wo_O1h_d8_g32_wb wo_O1h_w10_g32_wb wo_O1h_w25_g32_wb wo_O1h_w50_g32_wb wo_O1h_s25_g32_wb wo_O1h_s50_g32_wb wo_O1h_typ_r075_f005_g32_wb"
  PAIR=$(ls -d data/traces/wo_O1_a??_g32_wb 2>/dev/null | head -n 1 | xargs -r basename)
  AG="wo_O1_a0_g32_wb wo_O1_a1_g32_wb wo_O1_a2_g32_wb wo_O1_a3_g32_wb wo_O1_a4_g32_wb $PAIR"
  HMA="hm_wo_O1h_typ_g32_wb hm_wo_O1h_tired_g32_wb hm_wo_O1n_r050_f000_g32_wb hm_wo_O1n_r100_f005_g32_wb hm_wo_O1n_r050_f005_g32_wb hm_wo_O15r_e10_g32_qf_wb hm_wo_O16t_g32_wb"
  echo "== exits and log lines since the launch"; sed -n '/queue_H start/,$p' data/ft_runs.log | grep -v 'exit 0 try 1\|skipped'
  echo "== completeness"
  for d in $EYES wo_O2f_g32_wb wo_O1n_latch_g32_wb $HANDS wo_O15r_e24_g32_qf_wb wo_O15r_e24_g32_typ_wb wo_O1_g64_qf_wb svy_wo_O17_wb $AG wo_O16t_g32_wb wo_O16t_g8_wb so_O16t_g32_wb $HMA; do
    n=$(nfoot $d); [ "$n" -lt 100 ] && echo "$d: $n"; done; echo "(end of list)"

  echo; echo "==== 2a. the eyes surface: O1 through a detector (KEEP, Wrecker)"
  G --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_wb $EYES wo_O2f_g32_wb wo_O1n_latch_g32_wb
  rates $EYES wo_O2f_g32_wb wo_O1n_latch_g32_wb wo_O16_g32_wb wo_O16t_g32_wb
  echo "-- the latch against the model at its own recall and false-alarm share, paired"; P data/traces/wo_O2f_g32_wb data/traces/wo_O1n_latch_g32_wb
  echo "-- the random pick against O1's first-listed host, paired"; P data/traces/wo_O1_g32_wb data/traces/wo_O1n_r100_f000_g32_wb
  echo "-- H-MARL"; G --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g32_wb hm_wo_O1n_r050_f000_g32_wb hm_wo_O1n_r100_f005_g32_wb hm_wo_O1n_r050_f005_g32_wb
  rates hm_wo_O1n_r050_f000_g32_wb hm_wo_O1n_r100_f005_g32_wb hm_wo_O1n_r050_f005_g32_wb

  echo; echo "==== 2b. a person's hands on the held click (reference: the held click, no noise)"
  G --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_qf_wb $HANDS
  P data/traces/wo_O1_g32_qf_wb $(for d in $HANDS; do echo data/traces/$d; done)
  foot wo_O1_g32_qf_wb $HANDS
  echo "-- H-MARL"; G --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g32_qf_wb hm_wo_O1h_typ_g32_wb hm_wo_O1h_tired_g32_wb
  P data/traces/hm_wo_O1_g32_qf_wb data/traces/hm_wo_O1h_typ_g32_wb data/traces/hm_wo_O1h_tired_g32_wb
  foot hm_wo_O1h_typ_g32_wb hm_wo_O1h_tired_g32_wb

  echo; echo "==== 2c. the thermostat with the click held (reference: the gap-64 timer, held click)"
  G --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g64_qf_wb wo_O1_g64_wb wo_O15r_e24_g32_wb wo_O15r_e24_g32_qf_wb wo_O15r_e24_g32_typ_wb wo_O1h_typ_g32_wb
  echo "-- thermostat held click against the timer held click, and against the thermostat without it"
  P data/traces/wo_O1_g64_qf_wb data/traces/wo_O15r_e24_g32_qf_wb; P data/traces/wo_O15r_e24_g32_wb data/traces/wo_O15r_e24_g32_qf_wb data/traces/wo_O15r_e24_g32_typ_wb
  foot wo_O15r_e24_g32_qf_wb wo_O15r_e24_g32_typ_wb wo_O1_g64_qf_wb
  echo "-- H-MARL"; G --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g64_wb hm_wo_O15r_e10_g32_wb hm_wo_O15r_e10_g32_qf_wb
  P data/traces/hm_wo_O15r_e10_g32_wb data/traces/hm_wo_O15r_e10_g32_qf_wb

  echo; echo "==== 2d. R2's triage as a supervisor (O16t) against the as-is supervisor (O16) and the directed look (O10)"
  G --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_wb wo_O16_g32_wb wo_O16t_g32_wb wo_O16t_g8_wb wo_O10_g32_wb
  P data/traces/red_FSRedAgentWrecker data/traces/wo_O16t_g32_wb data/traces/wo_O16t_g8_wb; P data/traces/wo_O16_g32_wb data/traces/wo_O16t_g32_wb
  G --ceiling rd_RT_s_none_wb --control corpus_v1 --ref so_O1_g32_wb so_O16_g32_wb so_O16t_g32_wb
  P data/traces/corpus_v1 data/traces/so_O16t_g32_wb
  G --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g32_wb hm_wo_O16_g32_wb hm_wo_O16t_g32_wb
  P data/traces/hm_w_none data/traces/hm_wo_O16t_g32_wb
  foot wo_O16t_g32_wb wo_O16t_g8_wb so_O16t_g32_wb hm_wo_O16t_g32_wb

  echo; echo "==== 2e. the policy's own suspicion (KEEP alone, surveyed)"
  echo "-- the survey is the policy alone: expect +0.0 against the control"; P data/traces/red_FSRedAgentWrecker data/traces/svy_wo_O17_wb
  svy17

  echo; echo "==== 2f. O1 on one agent at a time, and on the top two"
  G --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_wb $AG
  python3 - $AG <<'EOF'
import glob, json, sys
def mean(d):
    v = [json.loads(open(f).read().strip().splitlines()[-1]).get("total_reward") for f in glob.glob(f"data/traces/{d}/ep_*.jsonl")]
    v = [x for x in v if x is not None]; return sum(v) / len(v)
c = mean("red_FSRedAgentWrecker"); allfive = mean("wo_O1_g32_wb") - c
singles = [mean(d) - c for d in sys.argv[1:6]]
print(f"sum of the five single-agent gains {sum(singles):+.1f} against all five together {allfive:+.1f}")
EOF
}
if [ "$1" = read ]; then read_all; exit 0; fi
echo "queue_H start $(date)" >> data/ft_runs.log
lane1 &
sleep 30
lane2 &
wait
echo "queue_H done $(date)" >> data/ft_runs.log
