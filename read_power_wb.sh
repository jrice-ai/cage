#!/bin/bash
# Trial power analysis re-based on the waiting-directive arms. Run from ~/cage.
cd ~/cage || exit 1
echo "#### KEEP under Wrecker, waiting directives: conditions against the policy alone"
python3 tools_power.py data/traces/red_FSRedAgentWrecker data/traces/wo_O1_g32_wb data/traces/wo_O10_g32_wb data/traces/wo_O13_g32_wb
echo; echo "#### KEEP under Wrecker: condition against condition, paired on seeds"
python3 tools_power.py --pair data/traces/wo_O1_g32_wb data/traces/wo_O10_g32_wb
python3 tools_power.py --pair data/traces/wo_O13_g32_wb data/traces/wo_O10_g32_wb
python3 tools_power.py --pair data/traces/wo_O1_g32_wb data/traces/wo_O1_g32
echo; echo "#### KEEP under the stock red"
python3 tools_power.py data/traces/corpus_v1 data/traces/o2_g32_wb data/traces/o10_g32_wb
echo; echo "#### H-MARL under Wrecker, and the calibration arm (R2, busy-aware)"
python3 tools_power.py data/traces/hm_w_none data/traces/hm_wo_O1_g32_wb data/traces/hm_wo_O10_g32_wb
python3 tools_power.py data/traces/rd_R2_w_none_wb data/traces/rd_R2_w_O1_g32_wb --effects 300,500,1000,1500
python3 tools_power.py data/traces/rd_R2_s_none_wb data/traces/rd_R2_s_O1_g32_wb --effects 25,50,100
