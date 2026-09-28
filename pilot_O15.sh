#!/bin/bash
# O15 threshold pilots on KEEP under Wrecker, 10 episodes each (seeds 0..9, the same as
# wo_O1_g32_wb's first ten), two lanes, about 4 minutes. Run from ~/cage after read_svy.sh.
# Thresholds bracket recall 0.6 from the survey: O15r 16, 24, 40 (loss over 16 steps);
# O15a 1, 2 (alerts over 16 steps); O15c 2, 3, 4 (compromised owned hosts).
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
arm() {
  $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $1 --engage $2 --min-gap 32 --budget 99999 --red FSRedAgentWrecker --episodes 10 --workers 6 --wait-busy --out /work/data/traces/pilot_wo_$1_e$2_g32_wb" > data/pilot_wo_$1_e$2_g32_wb.log 2>&1
  echo "pilot_wo_$1_e$2_g32_wb exit $? $(date)" >> data/ft_runs.log
}
lane1() { arm O15r 16; arm O15r 24; arm O15r 40; arm O15a 1; }
lane2() { arm O15a 2; arm O15c 2; arm O15c 3; arm O15c 4; }
lane1 &
sleep 20
lane2 &
wait
echo "pilot_O15 done $(date)" >> data/ft_runs.log
