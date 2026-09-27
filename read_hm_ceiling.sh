#!/bin/bash
# H-MARL Expert on the ceiling metric: share of the distance to RT (same adversary, same seeds)
# closed by each supervised arm. Run from ~/cage; RT arms from queue_A.sh and the afternoon.
cd ~/cage || exit 1
echo "== H-MARL, stock and Wrecker"
python3 tools_ceiling.py data/traces/rd_RT_s_none data/traces/hm_s_none data/traces/hm_so_O1_g32 data/traces/hm_so_O10_g32
python3 tools_ceiling.py data/traces/rd_RT_w_none data/traces/hm_w_none data/traces/hm_wo_O1_g32 data/traces/hm_wo_O10_g32 data/traces/hm_wo_O13_g32 data/traces/hm_wo_O14_g32 data/traces/hm_wo_O2f_g32
echo "== H-MARL, targeting axis and ConvOnly"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 ConvOnly; do
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none data/traces/hm_${R}_none_g0 data/traces/hm_${R}_O1_g32 data/traces/hm_${R}_O10_g32
done
echo "== H-MARL, Trident's ten"
for R in TargetARestricted TargetAOperational TargetA TargetB TargetBRestricted TargetBOperational Combined FailureTracker Impacter Degrader; do
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none data/traces/hm_${R}_none_g0 data/traces/hm_${R}_O1_g32 data/traces/hm_${R}_O10_g32
done
echo "== KEEP retrains under Wrecker, for the same column"
for w in k_kft_Wrecker_s1000_final k_kft_Wrecker_s1001_final k_kft_Wrecker_s1002_final k_kft_Wrecker_s1000_long_final k_kft_Wrecker_s1000_lr01_final; do
  python3 tools_ceiling.py data/traces/rd_RT_w_none data/traces/${w}_w_none data/traces/${w}_w_O1_g32
done
