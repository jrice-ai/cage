#!/bin/bash
# Queue B, 2026-09-27: the supervisor and the rule defenders with --wait-busy (directives wait for
# a free agent; rules sleep while busy), so every intervention the simulator accepted is one it ran.
# Two lanes side by side (the concurrency test); H-MARL after lane 1. Exit lines in data/ft_runs.log.
# Run only after tools_add_wait.py is applied and both gates reproduce.
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
lane1() {
  for spec in "O1 FSRedAgentWrecker wo_O1_g32_wb" "O10 FSRedAgentWrecker wo_O10_g32_wb" "O13 FSRedAgentWrecker wo_O13_g32_wb" "O2 FiniteStateRedAgent o2_g32_wb" "O10 FiniteStateRedAgent o10_g32_wb"; do
    set -- $spec
    $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $1 --min-gap 32 --budget 99999 --red $2 --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$3" > data/$3.log 2>&1
    echo "$3 exit $? $(date)" >> data/ft_runs.log
  done
  for spec in "O1 FSRedAgentWrecker hm_wo_O1_g32_wb" "O10 FSRedAgentWrecker hm_wo_O10_g32_wb"; do
    set -- $spec
    $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule $1 --min-gap 32 --budget 99999 --red $2 --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$3" > data/$3.log 2>&1
    echo "$3 exit $? $(date)" >> data/ft_runs.log
  done
}
lane2() {
  for k in R2 RT R4tn R2d; do WAIT=1 ./run_rd.sh $k FSRedAgentWrecker; done
  WAIT=1 ./run_rd.sh R2 FiniteStateRedAgent
  for k in R2 RT R4tn R2d; do WAIT=1 ./run_rd.sh $k FSRedAgentWrecker O1 32; done
  WAIT=1 ./run_rd.sh R2 FiniteStateRedAgent O1 32
}
lane1 &
sleep 30
lane2 &
wait
echo "queue_B done $(date)" >> data/ft_runs.log
