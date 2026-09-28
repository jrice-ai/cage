#!/bin/bash
# The three queue-F casualties (segfaults), after their partial directories are removed by hand.
# Run from ~/cage; about 12 minutes, two lanes; then ./read_F.sh again.
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
for d in wo_O15a_e2_g32_wb hm_wo_O15r_e10_g32_wb hm_wo_O1_g64_wb; do
  [ -d data/traces/$d ] && { echo "data/traces/$d still exists; remove it first (sudo rm -rf)"; exit 1; }
done
lane1() {
  out=wo_O15a_e2_g32_wb
  $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule O15a --engage 2 --min-gap 32 --budget 99999 --red FSRedAgentWrecker --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
  echo "$out exit $? $(date)" >> data/ft_runs.log
}
lane2() {
  out=hm_wo_O15r_e10_g32_wb
  $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule O15r --engage 10 --min-gap 32 --budget 99999 --red FSRedAgentWrecker --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
  echo "$out exit $? $(date)" >> data/ft_runs.log
  out=hm_wo_O1_g64_wb
  $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule O1 --min-gap 64 --budget 99999 --red FSRedAgentWrecker --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
  echo "$out exit $? $(date)" >> data/ft_runs.log
}
lane1 &
sleep 20
lane2 &
wait
echo "rerun_F done $(date)" >> data/ft_runs.log
