#!/bin/bash
# Queue D, 2026-09-27: the two queue-C casualties (partial directories deleted first), R2 controls
# at the Q points, and Trident's ten reds under --wait-busy on KEEP and H-MARL with RT ceilings.
# Two lanes. Exit lines in data/ft_runs.log.
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
# the two partial directories are removed in the launch block, before this runs
TRIDENT="FSRedAgentTargetARestricted FSRedAgentTargetAOperational FSRedAgentTargetA FSRedAgentTargetB FSRedAgentTargetBRestricted FSRedAgentTargetBOperational FSRedAgentCombined FSRedAgentFailureTracker FSRedAgentImpacter FSRedAgentDegrader"
lane1() {
  WAIT=1 ./run_rd.sh RT FSRedAgentWreckerQ32
  WAIT=1 ./run_rd.sh R2 FSRedAgentWreckerQ16 O1 32
  for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ32 FSRedAgentWreckerQ48; do WAIT=1 ./run_rd.sh R2 $red; done
  for red in $TRIDENT; do WAIT=1 ./run_rd.sh RT $red; done
}
lane2() {
  for red in $TRIDENT; do
    $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule O1 --min-gap 32 --budget 99999 --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/o1_g32_${red}_wb" > data/o1_g32_${red}_wb.log 2>&1
    echo "o1_g32_${red}_wb exit $? $(date)" >> data/ft_runs.log
  done
  for red in $TRIDENT; do
    n=${red#FSRedAgent}
    $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule O1 --min-gap 32 --budget 99999 --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/hm_${n}_O1_g32_wb" > data/hm_${n}_O1_g32_wb.log 2>&1
    echo "hm_${n}_O1_g32_wb exit $? $(date)" >> data/ft_runs.log
  done
}
lane1 &
sleep 30
lane2 &
wait
echo "queue_D done $(date)" >> data/ft_runs.log
