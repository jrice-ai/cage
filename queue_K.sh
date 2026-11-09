#!/usr/bin/env bash
# 2026-10-12 referee runs, KEEP side. Sequential. Logs in data/queue_K.log.
cd ~/cage
R="python3 /work/scripts/oracle.py"; C="python3 /work/scripts/capture.py"
bin/run cage-keep:dev $R --rule O1 --min-gap 32 --budget 99999 --red FiniteStateRedAgent --episodes 100 --workers 6 --out /work/data/traces/so_O1_g32
bin/run cage-keep:dev $R --rule O1 --wait-busy --red FiniteStateRedAgent --episodes 100 --workers 6 --out /work/data/traces/so_O1_n100_wb
for p in 9002 9003 9004; do bin/run cage-keep:dev $C --episodes 100 --red FSRedAgentWrecker --policy-seed $p --workers 12 --out /work/data/traces/wrecker_null_$p; done
bin/run cage-keep:dev $C --episodes 100 --red FSRedAgentWreckerQ32 --policy-seed 9001 --workers 12 --out /work/data/traces/red_FSRedAgentWreckerQ32_null9001
for s in 1000 1001 1002; do for p in 9000 9001; do
  KEEP_WEIGHTS=kft_Wrecker_s${s}_final    bin/run cage-keep:dev $R --rule none --red FSRedAgentWrecker    --policy-seed $p --episodes 100 --workers 6 --out /work/data/traces/k_kft_Wrecker_s${s}_final_w_none_p$p
  KEEP_WEIGHTS=kft_WreckerQ32_s${s}_final bin/run cage-keep:dev $R --rule none --red FSRedAgentWreckerQ32 --policy-seed $p --episodes 100 --workers 6 --out /work/data/traces/k_kft_WreckerQ32_s${s}_final_WreckerQ32_none_p$p
done; done
echo QUEUE_K_DONE
