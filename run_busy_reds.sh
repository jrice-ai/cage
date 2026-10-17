#!/bin/bash
# The released KEEP weights with the busy check as shipped and switched off, at each heuristic red
# agent of the red-agent table and at Wrecker. 100 episodes per arm on seeds 0 to 99, one container
# at a time. Skips arms whose trace directory exists, so it can be rerun after an interruption.
# Traces in data/traces/keep_released_busy_<busy>_<red>, logs in data/evals/, and the charge split
# for each adversary appended to data/evals/busy_reds.txt. Run with nohup.
set -u
cd ~/cage || exit 2
mkdir -p data/evals
for r in FSRedAgentWrecker FSRedAgentTargetARestricted FSRedAgentTargetAOperational FSRedAgentTargetA \
         FSRedAgentTargetB FSRedAgentTargetBRestricted FSRedAgentTargetBOperational FSRedAgentCombined \
         FSRedAgentFailureTracker; do
  [ -f red_agents/$r.py ] || { echo "$(date -Is) no red_agents/$r.py, skipped" >> data/evals/busy_reds.txt; continue; }
  for b in shipped none; do
    d=keep_released_busy_${b}_$r
    [ -e data/traces/$d ] && continue
    env -u CAGE_DOCKER_OPTS -u KEEP_WEIGHTS KEEP_BUSY=$b bin/run cage-keep:dev bash -c \
      "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule none --episodes 100 --workers 20 --log-policy --red $r --out /work/data/traces/$d" \
      > data/evals/$d.log 2>&1
    echo "$(date -Is) $d exit $? $(tail -1 data/evals/$d.log)" >> data/evals/busy_reds.txt
  done
  { echo "== $r"; python3 tools_busy_charge.py data/traces/keep_released_busy_shipped_$r data/traces/keep_released_busy_none_$r; } \
    >> data/evals/busy_reds.txt 2>&1
done
echo "$(date -Is) done" >> data/evals/busy_reds.txt
