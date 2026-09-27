#!/bin/bash
# Trial power analysis from existing arms. Run from ~/cage. About two minutes.
cd ~/cage || exit 1
echo "#### KEEP under Wrecker: conditions against the policy alone"
python3 tools_power.py data/traces/red_FSRedAgentWrecker data/traces/wo_O1_g32 data/traces/wo_O10_g32 data/traces/wo_O13_g32 data/traces/wrecker_null_9000 data/traces/wrecker_null_9001
echo; echo "#### KEEP under Wrecker: condition against condition, paired on seeds"
python3 tools_power.py --pair data/traces/wo_O1_g32 data/traces/wo_O10_g32
python3 tools_power.py --pair data/traces/wo_O13_g32 data/traces/wo_O10_g32
python3 tools_power.py --pair data/traces/wo_O1_g32 data/traces/wo_O2_g32
echo; echo "#### KEEP under the stock red"
python3 tools_power.py data/traces/corpus_v1 data/traces/o2_g32 data/traces/o10_g32 data/traces/keep_null
echo; echo "#### H-MARL under Wrecker, and the calibration arm (R2)"
python3 tools_power.py data/traces/hm_w_none data/traces/hm_wo_O1_g32 data/traces/hm_wo_O10_g32
python3 tools_power.py data/traces/rd_R2_w_none data/traces/rd_R2_w_O1_g32 --effects 500,1000,2000
