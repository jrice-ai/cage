#!/bin/bash
# O15 signal survey: each rule with --engage 1e9 (never engages) records the signal at every free
# agent-tick under the policy alone. 10 episodes each, two lanes, about 6 minutes. Run from ~/cage
# after gate_O15.sh passes; then read_svy.sh picks the thresholds.
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
lane1() {
  for spec in "O15r FSRedAgentWrecker svy_wo_O15r_wb" "O15a FSRedAgentWrecker svy_wo_O15a_wb" \
              "O15r FiniteStateRedAgent svy_so_O15r_wb" "O15a FiniteStateRedAgent svy_so_O15a_wb" \
              "O15r FSRedAgentWreckerQ16 svy_O15r_FSRedAgentWreckerQ16_wb" "O15a FSRedAgentWreckerQ16 svy_O15a_FSRedAgentWreckerQ16_wb" \
              "O15r FSRedAgentWreckerQ32 svy_O15r_FSRedAgentWreckerQ32_wb" "O15a FSRedAgentWreckerQ32 svy_O15a_FSRedAgentWreckerQ32_wb"; do
    set -- $spec
    $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $1 --engage 1e9 --min-gap 32 --budget 99999 --red $2 --episodes 10 --workers 6 --wait-busy --out /work/data/traces/$3" > data/$3.log 2>&1
    echo "$3 exit $? $(date)" >> data/ft_runs.log
  done
}
lane2() {
  for spec in "O15r FSRedAgentWrecker svy_hm_wo_O15r_wb" "O15a FSRedAgentWrecker svy_hm_wo_O15a_wb"; do
    set -- $spec
    $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule $1 --engage 1e9 --min-gap 32 --budget 99999 --red $2 --episodes 10 --workers 6 --wait-busy --out /work/data/traces/$3" > data/$3.log 2>&1
    echo "$3 exit $? $(date)" >> data/ft_runs.log
  done
}
lane1 &
sleep 30
lane2 &
wait
echo "svy_O15 done $(date)" >> data/ft_runs.log
