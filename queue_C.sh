#!/bin/bash
# Queue C, 2026-09-26 night: the targeting axis, the ceilings and the retraining endpoints with
# waiting directives (--wait-busy), two lanes; plus the R2d control that segfaulted in queue B.
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
lane1() {
  WAIT=1 ./run_rd.sh R2d FSRedAgentWrecker
  for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ32 FSRedAgentWreckerQ48 FSRedAgentConvOnly FiniteStateRedAgent; do
    WAIT=1 ./run_rd.sh RT $red
  done
  for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ32 FSRedAgentWreckerQ48; do
    WAIT=1 ./run_rd.sh R2 $red O1 32
  done
  for w in k_kft_Wrecker_s1000_final k_kft_Wrecker_s1001_final k_kft_Wrecker_s1002_final k_kft_Wrecker_s1000_long_final k_kft_Wrecker_s1000_lr01_final; do
    KEEP_WEIGHTS=${w#k_} $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule O1 --min-gap 32 --budget 99999 --red FSRedAgentWrecker --episodes 100 --workers 6 --wait-busy --out /work/data/traces/${w}_w_O1_g32_wb" > data/${w}_w_O1_g32_wb.log 2>&1
    echo "${w}_w_O1_g32_wb exit $? $(date)" >> data/ft_runs.log
  done
}
lane2() {
  for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ32 FSRedAgentWreckerQ48 FSRedAgentConvOnly; do
    n=${red#FSRedAgent}
    $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule O1 --min-gap 32 --budget 99999 --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/o1_g32_${red}_wb" > data/o1_g32_${red}_wb.log 2>&1
    echo "o1_g32_${red}_wb exit $? $(date)" >> data/ft_runs.log
  done
  for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ32 FSRedAgentWreckerQ48 FSRedAgentConvOnly; do
    n=${red#FSRedAgent}
    $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule O1 --min-gap 32 --budget 99999 --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/hm_${n}_O1_g32_wb" > data/hm_${n}_O1_g32_wb.log 2>&1
    echo "hm_${n}_O1_g32_wb exit $? $(date)" >> data/ft_runs.log
  done
}
lane1 &
sleep 30
lane2 &
wait
echo "queue_C done $(date)" >> data/ft_runs.log
