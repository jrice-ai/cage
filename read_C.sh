#!/bin/bash
# Read for queue C. Run from ~/cage after "queue_C done" in data/ft_runs.log.
cd ~/cage || exit 1
echo "== exits"; tail -n 27 data/ft_runs.log | grep -v 'exit 0' ; tail -n 27 data/ft_runs.log | grep -c 'exit 0'
echo "== ceilings with the flag"
for R in s WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 ConvOnly w; do echo "RT $R: $(tail -n 1 data/rd_RT_${R}_none_wb.log)"; done
echo "== R2d control rerun"; tail -n 1 data/rd_R2d_w_none_wb.log
python3 tools_paired.py data/traces/rd_R2d_w_none_wb data/traces/rd_R2d_w_O1_g32_wb | tail -n 1
python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/rd_R2d_w_none_wb data/traces/rd_R2d_w_O1_g32_wb
echo "== KEEP along the axis, waiting O1: delta and share (attempted share in ARMS: 0.49, 0.51, 0.51, 0.57, 0.59; ConvOnly 0.42)"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 ConvOnly; do
  python3 tools_paired.py data/traces/red_FSRedAgent${R} data/traces/o1_g32_FSRedAgent${R}_wb data/traces/o1_g32_FSRedAgent${R} | tail -n 2
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb data/traces/red_FSRedAgent${R} data/traces/o1_g32_FSRedAgent${R}_wb
done
echo "== H-MARL along the axis, waiting O1 (attempted share: 0.14, 0.33, 0.43, 0.34, 0.20; ConvOnly -0.33)"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 ConvOnly; do
  python3 tools_paired.py data/traces/hm_${R}_none_g0 data/traces/hm_${R}_O1_g32_wb data/traces/hm_${R}_O1_g32 | tail -n 2
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb data/traces/hm_${R}_none_g0 data/traces/hm_${R}_O1_g32_wb
done
echo "== R2 along the axis, waiting O1 (controls are the attempted-condition R2, so the share is a floor until R2 controls rerun)"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48; do
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb data/traces/rd_R2_${R}_none data/traces/rd_R2_${R}_O1_g32_wb
done
echo "== the six KEEP policies, waiting O1 (attempted endpoints -663, -626, -657, -675, -714, -639)"
python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/red_FSRedAgentWrecker data/traces/wo_O1_g32_wb
for w in k_kft_Wrecker_s1000_final k_kft_Wrecker_s1001_final k_kft_Wrecker_s1002_final k_kft_Wrecker_s1000_long_final k_kft_Wrecker_s1000_lr01_final; do
  python3 tools_paired.py data/traces/${w}_w_none data/traces/${w}_w_O1_g32_wb | tail -n 1
  python3 tools_ceiling.py data/traces/rd_RT_w_none_wb data/traces/${w}_w_none data/traces/${w}_w_O1_g32_wb
done
echo "== execution check on a sample"
python3 tools_dropped.py o1_g32_FSRedAgentWreckerQ32_wb hm_WreckerQ32_O1_g32_wb k_kft_Wrecker_s1000_final_w_O1_g32_wb --episodes 20
