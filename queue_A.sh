#!/bin/bash
# Overnight queue A, 2026-09-26. One arm at a time; exit lines go to data/ft_runs.log.
#   1. RT (ground-truth ceiling) under every adversary KEEP has been run on: the Q sweep, ConvOnly,
#      and Trident's ten heuristic reds (15 arms, about 75 minutes)
#   2. R2 and R2 + O1 at Q04, Q16, Q48, to complete the second rule line on the targeting axis
#      (6 arms, about 30 minutes)
#   3. The eyes diagnostic at twenty episodes for KEEP and R1 under both reds, sequential
#      (4 runs, about an hour), logs in data/eyes_<rule>_<red>.log
cd ~/cage || exit 1
for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ32 FSRedAgentWreckerQ48 FSRedAgentConvOnly \
           FSRedAgentTargetARestricted FSRedAgentTargetAOperational FSRedAgentTargetA FSRedAgentTargetB \
           FSRedAgentTargetBRestricted FSRedAgentTargetBOperational FSRedAgentCombined FSRedAgentFailureTracker \
           FSRedAgentImpacter FSRedAgentDegrader; do
  ./run_rd.sh RT $red
done
for red in FSRedAgentWreckerQ04 FSRedAgentWreckerQ16 FSRedAgentWreckerQ48; do
  ./run_rd.sh R2 $red
  ./run_rd.sh R2 $red O1 32
done
for spec in "none FSRedAgentWrecker" "none FiniteStateRedAgent" "R1 FSRedAgentWrecker" "R1 FiniteStateRedAgent"; do
  set -- $spec
  bin/run cage-keep:dev bash -c "cd /opt/cage/cage-4-submission && python3 -u /work/tools_diag_eyes.py --red $2 --rule $1 --seed 0 --episodes 20" > data/eyes_$1_$2.log 2>&1
  echo "eyes_$1_$2 exit $? $(date)" >> data/ft_runs.log
done
echo "queue_A done $(date)" >> data/ft_runs.log
