#!/bin/bash
# Queue G, 2026-09-28: the runs behind the pre-trial display decisions, all with the directive held.
#   The held click: O1 with --queue first and last on KEEP and H-MARL under Wrecker (the price of
#     staleness against the same rule that re-decides at the free tick).
#   The rate curve under held directives: O1 at gaps 4, 8, 16, 128 on KEEP (32, 64, 96 exist) and
#     16, 128 on H-MARL; burst against spread as O2 at gap 0 with budget 77 and O2 at gap 32.
#   The as-is ceiling: O16 (latch eyes, a look, a restore on a confirmed file) at the trial pace
#     (gap 32) on KEEP under Wrecker, stock, mass 16 and 32, and on H-MARL; and at gap 8 on KEEP.
#   The alert gate with as-is hands: O15h at threshold 1 on KEEP and H-MARL under Wrecker.
#   Two more rungs of the loss thermostat at mass 16 and 32; H-MARL's mode gate (O14) held.
# 25 arms, two lanes, about 75 minutes. Arms whose directory already holds 100 episodes are
# skipped. Exit lines in data/ft_runs.log.
#   ./queue_G.sh        launch (nohup it)
#   ./queue_G.sh read   read, after "queue_G done" appears in data/ft_runs.log
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
have() { [ -d data/traces/$1 ] && [ "$(ls data/traces/$1 2>/dev/null | wc -l)" -ge 100 ]; }
keep() {   # keep RULE RED OUT [flags]
  local rule=$1 red=$2 out=$3; shift 3
  have $out && { echo "$out skipped, exists $(date)" >> data/ft_runs.log; return; }
  $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $rule $* --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
  echo "$out exit $? $(date)" >> data/ft_runs.log
}
hm() {     # hm RULE RED OUT [flags]
  local rule=$1 red=$2 out=$3; shift 3
  have $out && { echo "$out skipped, exists $(date)" >> data/ft_runs.log; return; }
  $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule $rule $* --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
  echo "$out exit $? $(date)" >> data/ft_runs.log
}
W=FSRedAgentWrecker; S=FiniteStateRedAgent; B="--budget 99999"
lane1() {
  keep O1 $W wo_O1_g32_qf_wb --min-gap 32 $B --queue first
  keep O1 $W wo_O1_g32_ql_wb --min-gap 32 $B --queue last
  for g in 4 8 16 128; do keep O1 $W wo_O1_g${g}_wb --min-gap $g $B; done
  keep O2 $W wo_O2_g0_b77_wb --min-gap 0 --budget 77
  keep O2 $W wo_O2_g32_wb --min-gap 32 $B
  keep O16 $W wo_O16_g32_wb --min-gap 32 $B
  keep O16 $W wo_O16_g8_wb --min-gap 8 $B
  keep O16 $S so_O16_g32_wb --min-gap 32 $B
  keep O15h $W wo_O15h_e1_g32_wb --engage 1 --min-gap 32 $B
}
lane2() {
  hm O1 $W hm_wo_O1_g32_qf_wb --min-gap 32 $B --queue first
  hm O1 $W hm_wo_O1_g32_ql_wb --min-gap 32 $B --queue last
  for g in 16 128; do hm O1 $W hm_wo_O1_g${g}_wb --min-gap $g $B; done
  hm O16 $W hm_wo_O16_g32_wb --min-gap 32 $B
  hm O15h $W hm_wo_O15h_e1_g32_wb --engage 1 --min-gap 32 $B
  hm O14 $W hm_wo_O14_g32_wb --min-gap 32 $B
  for red in FSRedAgentWreckerQ16 FSRedAgentWreckerQ32; do keep O16 $red o16_g32_${red}_wb --min-gap 32 $B; done
  for e in 3 12; do keep O15r FSRedAgentWreckerQ16 o15r_e${e}_g32_FSRedAgentWreckerQ16_wb --engage $e --min-gap 32 $B; done
  for e in 6 22; do keep O15r FSRedAgentWreckerQ32 o15r_e${e}_g32_FSRedAgentWreckerQ32_wb --engage $e --min-gap 32 $B; done
}
foot() {   # per-arm footer means for the bookkeeping tools_gate.py does not print
  python3 - "$@" <<'EOF'
import glob, json, sys
for d in sys.argv[1:]:
    rows = []
    for f in sorted(glob.glob(f"data/traces/{d}/ep_*.jsonl")):
        last = None
        for l in open(f):
            if l.strip(): last = l
        if last:
            r = json.loads(last)
            if r.get("record") == "footer": rows.append(r)
    if not rows: print(f"{d}: no footers"); continue
    m = lambda k: sum(r.get(k, 0) for r in rows) / len(rows)
    keys = [k for k in ("overrides", "deferred", "queued", "queue_fired", "queue_stale", "analyses", "restores", "o16_confirmed", "o15h_clean", "engaged", "engaged_hit", "agreements") if any(k in r for r in rows)]
    line = f"{d:38} n {len(rows):3} mean {m('total_reward'):8.1f}  " + "  ".join(f"{k} {m(k):.1f}" for k in keys)
    if m("queue_fired"): line += f"  wait/fired {m('queue_wait') / m('queue_fired'):.1f} ticks  stale share {m('queue_stale') / m('queue_fired'):.3f}"
    print(line)
EOF
}
read_all() {
  echo "== exits"; awk '/Mon Sep 28 2[2-3]:|Tue Sep 29 0[0-9]:/' data/ft_runs.log | grep -v 'exit 0\|skipped'; awk '/Mon Sep 28 2[2-3]:|Tue Sep 29 0[0-9]:/' data/ft_runs.log | grep -c 'exit 0'
  echo "== completeness"
  for d in wo_O1_g32_qf_wb wo_O1_g32_ql_wb wo_O1_g4_wb wo_O1_g8_wb wo_O1_g16_wb wo_O1_g128_wb wo_O2_g0_b77_wb wo_O2_g32_wb wo_O16_g32_wb wo_O16_g8_wb so_O16_g32_wb wo_O15h_e1_g32_wb hm_wo_O1_g32_qf_wb hm_wo_O1_g32_ql_wb hm_wo_O1_g16_wb hm_wo_O1_g128_wb hm_wo_O16_g32_wb hm_wo_O15h_e1_g32_wb hm_wo_O14_g32_wb o16_g32_FSRedAgentWreckerQ16_wb o16_g32_FSRedAgentWreckerQ32_wb o15r_e3_g32_FSRedAgentWreckerQ16_wb o15r_e12_g32_FSRedAgentWreckerQ16_wb o15r_e6_g32_FSRedAgentWreckerQ32_wb o15r_e22_g32_FSRedAgentWreckerQ32_wb; do
    n=$(for f in data/traces/$d/ep_*.jsonl; do tail -n 1 "$f" | grep -c '"footer"'; done 2>/dev/null | awk '{s+=$1} END {print s+0}'); [ "$n" -lt 100 ] && echo "$d: $n"; done; echo "(end of list)"
  echo; echo "==== the held click: queue first and last against the re-deciding rule (KEEP, then H-MARL, Wrecker)"
  python3 tools_gate.py --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_wb wo_O1_g32_qf_wb wo_O1_g32_ql_wb
  python3 tools_paired.py data/traces/wo_O1_g32_wb data/traces/wo_O1_g32_qf_wb data/traces/wo_O1_g32_ql_wb | tail -n 2
  python3 tools_gate.py --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g32_wb hm_wo_O1_g32_qf_wb hm_wo_O1_g32_ql_wb
  python3 tools_paired.py data/traces/hm_wo_O1_g32_wb data/traces/hm_wo_O1_g32_qf_wb data/traces/hm_wo_O1_g32_ql_wb | tail -n 2
  foot wo_O1_g32_wb wo_O1_g32_qf_wb wo_O1_g32_ql_wb hm_wo_O1_g32_wb hm_wo_O1_g32_qf_wb hm_wo_O1_g32_ql_wb
  echo; echo "==== the rate curve under held directives (KEEP under Wrecker)"
  python3 tools_gate.py --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_wb wo_O1_g4_wb wo_O1_g8_wb wo_O1_g16_wb wo_O1_g64_wb wo_O1_g96_wb wo_O1_g128_wb wo_O2_g0_b77_wb wo_O2_g32_wb
  echo "-- burst against spread, same rule (O2), paired"; python3 tools_paired.py data/traces/wo_O2_g32_wb data/traces/wo_O2_g0_b77_wb | tail -n 1
  echo "-- H-MARL"; python3 tools_gate.py --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g32_wb hm_wo_O1_g16_wb hm_wo_O1_g64_wb hm_wo_O1_g128_wb
  echo; echo "==== the as-is ceiling (O16) against the control and O1 (KEEP Wrecker, stock, mass 16, mass 32; H-MARL Wrecker)"
  python3 tools_gate.py --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_wb wo_O16_g32_wb wo_O16_g8_wb wo_O10_g32_wb wo_O13_g32_wb
  python3 tools_paired.py data/traces/red_FSRedAgentWrecker data/traces/wo_O16_g32_wb data/traces/wo_O16_g8_wb | tail -n 2
  python3 tools_gate.py --ceiling rd_RT_s_none_wb --control corpus_v1 --ref so_O1_g32_wb so_O16_g32_wb o10_g32_wb
  python3 tools_paired.py data/traces/corpus_v1 data/traces/so_O16_g32_wb | tail -n 1
  for Q in Q16 Q32; do python3 tools_gate.py --ceiling rd_RT_Wrecker${Q}_none_wb --control red_FSRedAgentWrecker${Q} --ref o1_g32_FSRedAgentWrecker${Q}_wb o16_g32_FSRedAgentWrecker${Q}_wb o10_g32_FSRedAgentWrecker${Q}_wb | tail -n 2; done
  python3 tools_gate.py --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g32_wb hm_wo_O16_g32_wb hm_wo_O10_g32_wb
  python3 tools_paired.py data/traces/hm_w_none data/traces/hm_wo_O16_g32_wb | tail -n 1
  foot wo_O16_g32_wb wo_O16_g8_wb so_O16_g32_wb o16_g32_FSRedAgentWreckerQ16_wb o16_g32_FSRedAgentWreckerQ32_wb hm_wo_O16_g32_wb
  echo; echo "==== the alert gate with as-is hands (O15h) against O15a and the timer"
  python3 tools_gate.py --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g64_wb wo_O15h_e1_g32_wb wo_O15a_e1_g32_wb
  python3 tools_paired.py data/traces/wo_O15a_e1_g32_wb data/traces/wo_O15h_e1_g32_wb | tail -n 1
  python3 tools_gate.py --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g64_wb hm_wo_O15h_e1_g32_wb hm_wo_O15a_e1_g32_wb
  foot wo_O15h_e1_g32_wb hm_wo_O15h_e1_g32_wb
  echo; echo "==== the thermostat ladder at mass 16 and 32"
  python3 tools_gate.py --ceiling rd_RT_WreckerQ16_none_wb --control red_FSRedAgentWreckerQ16 --ref o1_g32_FSRedAgentWreckerQ16_wb o15r_e3_g32_FSRedAgentWreckerQ16_wb o15r_e6_g32_FSRedAgentWreckerQ16_wb o15r_e12_g32_FSRedAgentWreckerQ16_wb o1_g64_FSRedAgentWreckerQ16_wb | tail -n 4
  python3 tools_gate.py --ceiling rd_RT_WreckerQ32_none_wb --control red_FSRedAgentWreckerQ32 --ref o1_g32_FSRedAgentWreckerQ32_wb o15r_e6_g32_FSRedAgentWreckerQ32_wb o15r_e11_g32_FSRedAgentWreckerQ32_wb o15r_e22_g32_FSRedAgentWreckerQ32_wb o1_g64_FSRedAgentWreckerQ32_wb | tail -n 4
  echo; echo "==== H-MARL's mode gate, held"
  python3 tools_paired.py data/traces/hm_w_none data/traces/hm_wo_O14_g32_wb data/traces/hm_wo_O14_g32 | tail -n 2
  echo; echo "==== execution shares"
  python3 tools_dropped.py wo_O1_g32_qf_wb wo_O16_g32_wb hm_wo_O1_g32_qf_wb --episodes 20 2>&1 | grep -v defender
}
if [ "$1" = read ]; then read_all; exit 0; fi
lane1 &
sleep 30
lane2 &
wait
echo "queue_G done $(date)" >> data/ft_runs.log
