#!/bin/bash
# Read for queue F (the engagement gate). Run from ~/cage after "queue_F done" in data/ft_runs.log.
cd ~/cage || exit 1
echo "== exits"; awk '/Sun Sep 27 1[5-9]:|Sun Sep 27 2[0-3]:/' data/ft_runs.log | grep -v 'exit 0' | grep -v skipped; awk '/Sun Sep 27 1[5-9]:|Sun Sep 27 2[0-3]:/' data/ft_runs.log | grep -c 'exit 0'
echo "== completeness"
for d in data/traces/*O15*_wb data/traces/*O1_g64_wb data/traces/*O1_g96_wb data/traces/so_O1_g32_wb data/traces/o1_g64_*_wb; do [ -d "$d" ] || continue; case $d in *pilot_*|*svy_*|*gate_*) continue;; esac; n=$(for f in $d/ep_*.jsonl; do tail -n 1 "$f" | grep -c '"footer"'; done 2>/dev/null | awk '{s+=$1} END {print s+0}'); [ "$n" -lt 100 ] && echo "$(basename $d): $n"; done; echo "(end of list)"
echo; echo "==== KEEP under Wrecker: the gate ladder against O1 at full cadence (g32) and the ceiling"
python3 tools_gate.py --ceiling rd_RT_w_none_wb --control red_FSRedAgentWrecker --ref wo_O1_g32_wb wo_O15r_e16_g32_wb wo_O15r_e24_g32_wb wo_O15r_e40_g32_wb wo_O15a_e1_g32_wb wo_O15a_e2_g32_wb wo_O15c_e2_g32_wb wo_O15c_e3_g32_wb wo_O1_g64_wb wo_O1_g96_wb
echo; echo "== signal-timed against cadence-timed at matched effort (paired, the trial's comparison)"
python3 tools_paired.py data/traces/wo_O1_g64_wb data/traces/wo_O15r_e24_g32_wb data/traces/wo_O15c_e2_g32_wb data/traces/wo_O15a_e2_g32_wb | tail -n 3
python3 tools_paired.py data/traces/wo_O1_g96_wb data/traces/wo_O15r_e40_g32_wb | tail -n 1
python3 tools_paired.py data/traces/wo_O1_g32_wb data/traces/wo_O15r_e16_g32_wb data/traces/wo_O15a_e1_g32_wb | tail -n 2
echo; echo "==== KEEP under stock"
python3 tools_gate.py --ceiling rd_RT_s_none_wb --control corpus_v1 --ref so_O1_g32_wb so_O15r_e3_g32_wb so_O15c_e2_g32_wb so_O1_g64_wb o2_g32_wb
python3 tools_paired.py data/traces/so_O1_g64_wb data/traces/so_O15r_e3_g32_wb data/traces/so_O15c_e2_g32_wb | tail -n 2
for Q in Q16 Q32; do
  echo; echo "==== KEEP under Wrecker$Q"
  python3 tools_gate.py --ceiling rd_RT_Wrecker${Q}_none_wb --control red_FSRedAgentWrecker${Q} --ref o1_g32_FSRedAgentWrecker${Q}_wb o15r_e*_g32_FSRedAgentWrecker${Q}_wb o15a_e1_g32_FSRedAgentWrecker${Q}_wb o15c_e2_g32_FSRedAgentWrecker${Q}_wb o1_g64_FSRedAgentWrecker${Q}_wb
  python3 tools_paired.py data/traces/o1_g64_FSRedAgentWrecker${Q}_wb data/traces/o15r_e*_g32_FSRedAgentWrecker${Q}_wb data/traces/o15c_e2_g32_FSRedAgentWrecker${Q}_wb | tail -n 2
done
echo; echo "==== H-MARL under Wrecker"
python3 tools_gate.py --ceiling rd_RT_w_none_wb --control hm_w_none --ref hm_wo_O1_g32_wb hm_wo_O15r_e10_g32_wb hm_wo_O15a_e1_g32_wb hm_wo_O15c_e2_g32_wb hm_wo_O1_g64_wb
python3 tools_paired.py data/traces/hm_wo_O1_g64_wb data/traces/hm_wo_O15r_e10_g32_wb data/traces/hm_wo_O15c_e2_g32_wb | tail -n 2
echo; echo "== execution shares (expect near 1.0)"
python3 tools_dropped.py wo_O15r_e24_g32_wb wo_O1_g64_wb hm_wo_O15r_e10_g32_wb --episodes 20 2>&1 | grep -v defender
echo; echo "== trial sizing: signal-timed against cadence-timed at matched effort, and the gate against the control"
python3 tools_power.py --pair data/traces/wo_O15r_e24_g32_wb data/traces/wo_O1_g64_wb --ns 20,30,50 --effects 50,100,150,200 2>/dev/null | grep -v '^  power\|^  effect\|^     '
python3 tools_power.py data/traces/red_FSRedAgentWrecker data/traces/wo_O15r_e24_g32_wb --ns 20,30,50 --effects 100,200,300 2>/dev/null | grep -v '^  power\|^  effect\|^     '
