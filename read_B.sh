#!/bin/bash
# Read for queue B (wait-busy rerun). Run from ~/cage after "queue_B done" in data/ft_runs.log.
cd ~/cage || exit 1
echo "== exits and lane timing"; tail -n 21 data/ft_runs.log
echo "== execution shares with the flag (expect near 1.0)"
python3 tools_dropped.py wo_O1_g32_wb wo_O10_g32_wb rd_R2_w_O1_g32_wb rd_R4tn_w_O1_g32_wb rd_RT_w_none_wb --episodes 30
python3 tools_dropped.py hm_wo_O1_g32_wb --episodes 20
echo "== KEEP under Wrecker: waiting directives against the same rule dropped, and against the control"
python3 tools_paired.py data/traces/red_FSRedAgentWrecker data/traces/wo_O1_g32_wb data/traces/wo_O1_g32 data/traces/wo_O10_g32_wb data/traces/wo_O10_g32 data/traces/wo_O13_g32_wb data/traces/wo_O13_g32 | tail -n 6
python3 tools_paired.py data/traces/wo_O1_g32 data/traces/wo_O1_g32_wb | tail -n 1
python3 tools_paired.py data/traces/wo_O10_g32 data/traces/wo_O10_g32_wb | tail -n 1
echo "== KEEP under stock"
python3 tools_paired.py data/traces/corpus_v1 data/traces/o2_g32_wb data/traces/o2_g32 data/traces/o10_g32_wb data/traces/o10_g32 | tail -n 4
echo "== H-MARL under Wrecker"
python3 tools_paired.py data/traces/hm_w_none data/traces/hm_wo_O1_g32_wb data/traces/hm_wo_O1_g32 data/traces/hm_wo_O10_g32_wb data/traces/hm_wo_O10_g32 | tail -n 4
echo "== rule defenders, busy-aware, alone and under waiting O1"
for k in R2 RT R4tn R2d; do echo "$k w: $(tail -n 1 data/rd_${k}_w_none_wb.log)"; done
echo "R2 s: $(tail -n 1 data/rd_R2_s_none_wb.log)"
for k in R2 RT R4tn R2d; do python3 tools_paired.py data/traces/rd_${k}_w_none data/traces/rd_${k}_w_none_wb | tail -n 1; done
for k in R2 RT R4tn R2d; do python3 tools_paired.py data/traces/rd_${k}_w_none_wb data/traces/rd_${k}_w_O1_g32_wb | tail -n 1; done
python3 tools_paired.py data/traces/rd_R2_s_none_wb data/traces/rd_R2_s_O1_g32_wb | tail -n 1
echo "== ceiling shares with waiting directives"
python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/red_FSRedAgentWrecker data/traces/wo_O1_g32_wb data/traces/wo_O10_g32_wb data/traces/wo_O13_g32_wb
python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/hm_w_none data/traces/hm_wo_O1_g32_wb data/traces/hm_wo_O10_g32_wb
python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/rd_R2_w_none_wb data/traces/rd_R2_w_O1_g32_wb
python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/rd_R4tn_w_none_wb data/traces/rd_R4tn_w_O1_g32_wb
python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/rd_R2d_w_none_wb data/traces/rd_R2d_w_O1_g32_wb
python3 tools_ceiling.py data/traces/rd_RT_s_none data/traces/rd_R2_s_none_wb data/traces/rd_R2_s_O1_g32_wb
echo "== the directed look, executed looks only"
python3 tools_investigate.py data/traces/wo_O10_g32 data/traces/wo_O10_g32_wb data/traces/wo_O13_g32_wb data/traces/rd_R2_w_O10_g32 data/traces/hm_wo_O10_g32_wb
