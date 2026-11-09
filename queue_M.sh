#!/usr/bin/env bash
# 2026-10-12 referee runs, H-MARL side. Sequential. Logs in data/queue_M.log.
cd ~/cage
H="python3 -u /work/scripts/capture_hmarl.py"
bin/run cage-hmarl:dev $H --rule O1 --min-gap 32 --budget 99999 --red FiniteStateRedAgent --wait-busy --episodes 100 --workers 6 --out /work/data/traces/hm_so_O1_g32_wb
for p in 9001 9002; do bin/run cage-hmarl:dev $H --rule none --red FiniteStateRedAgent --policy-seed $p --episodes 100 --workers 6 --out /work/data/traces/hm_s_none_p$p; done
echo QUEUE_M_DONE
