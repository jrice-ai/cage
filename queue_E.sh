#!/bin/bash
# Queue E, 2026-09-27: the remaining rule kinds under --wait-busy (lane 1) and the directed look
# along the targeting axis on KEEP under --wait-busy (lane 2). 22 arms, two lanes, about an hour.
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
lane1() {
  for k in R1 R3 R4 R4t R4p R4d; do
    WAIT=1 ./run_rd.sh $k FiniteStateRedAgent
    WAIT=1 ./run_rd.sh $k FSRedAgentWrecker
  done
}
lane2() {
  for rule in O10 O13; do
    for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ32 FSRedAgentWreckerQ48 FSRedAgentConvOnly; do
      lc=$(echo $rule | tr 'A-Z' 'a-z')
      $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $rule --min-gap 32 --budget 99999 --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/${lc}_g32_${red}_wb" > data/${lc}_g32_${red}_wb.log 2>&1
      echo "${lc}_g32_${red}_wb exit $? $(date)" >> data/ft_runs.log
    done
  done
}
lane1 &
sleep 30
lane2 &
wait
echo "queue_E done $(date)" >> data/ft_runs.log
