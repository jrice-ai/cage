#!/bin/bash
# Run moved pilot runs on this machine one at a time, in legs, so every seed's learning curve grows
# together. Each leg resumes a run from its state file and takes it to the next kept checkpoint
# (100, 200, 300, then 400 updates). A run already past a leg's target finishes that leg at once.
# usage: run_pilot_queue.sh [cpus] [tag ...]
#   cpus  default 0-17. Leaves 6 of the workstation's 24 threads for evaluations.
#   tags  default the four on-flag runs, kbf_F_s4101 to kbf_F_s4104
# To stop after the current leg, touch ~/cage/data/queue.stop. To stop now, also docker stop the run.
# Every leg is logged in data/pilot_runs.log by run_keep_pilot.sh.
set -u
cd ~/cage || exit 2
cpus=${1:-0-17}; shift || true
tags=("$@"); [ ${#tags[@]} -gt 0 ] || tags=(kbf_F_s4101 kbf_F_s4102 kbf_F_s4103 kbf_F_s4104)
rm -f data/queue.stop
for target in 100 200 300 400; do
  for tag in "${tags[@]}"; do
    [ -f data/queue.stop ] && { echo "$(date -Is) queue stopped before $tag leg $target" >> data/pilot_runs.log; exit 0; }
    arm=${tag:4:1}; seed=${tag#kbf_?_s}
    ./run_keep_pilot.sh "$arm" "$seed" "$target" "$cpus" resume
    rc=$?
    echo "$(date -Is) queue $tag leg $target exit $rc" >> data/pilot_runs.log
  done
done
echo "$(date -Is) queue done" >> data/pilot_runs.log
