#!/bin/bash
# Evaluate one KEEP continuation checkpoint through oracle.py.
# usage: run_keep_eval.sh <tag> <N|final> <red> [rule] [gap] [budget]
#   tag    training tag, e.g. kft_Wrecker_s1000
#   N      kept checkpoint episode count (500, 1000, ...), or "final" for the
#          rolling <tag>-{i}_checkpoint.pt written after the last update
#   red    FSRedAgentWrecker | FiniteStateRedAgent | ...
#   rule   oracle rule (default none); gap = --min-gap (default 0); budget = --budget if given
# Copies the five checkpoint files to keep_weights/<tag>_<N>/gnn_ppo-{i}.pt once,
# then runs 100 episodes, seeds 0-99, six workers, with KEEP_WEIGHTS naming them.
# Output data/traces/k_<tag>_<N>_<w|s|red>_<rule>[_g<gap>], log data/<same>.log,
# exit line in data/ft_runs.log.
cd ~/cage || exit 1
tag=$1; n=$2; red=$3; rule=${4:-none}; gap=${5:-0}; budget=$6
ck=repos/cage-4-submission/checkpoints
w=keep_weights/${tag}_$n
if [ ! -f $w/gnn_ppo-4.pt ]; then
  mkdir -p $w
  for i in 0 1 2 3 4; do
    if [ "$n" = final ]; then f=$ck/${tag}-${i}_checkpoint.pt; else f=$ck/${tag}-${i}_e$n.pt; fi
    cp $f $w/gnn_ppo-$i.pt || { echo "$tag $n: missing $f $(date)" >> data/ft_runs.log; exit 1; }
  done
fi
case $red in FSRedAgentWrecker) a=w;; FiniteStateRedAgent) a=s;; *) a=${red#FSRedAgent};; esac
out=k_${tag}_${n}_${a}_$rule; [ "$gap" != 0 ] && out=${out}_g$gap
extra=""; [ -n "$budget" ] && extra="--budget $budget"
KEEP_WEIGHTS=${tag}_$n bin/run cage-keep:dev bash -c "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $rule --red $red --episodes 100 --workers 6 --min-gap $gap $extra --out /work/data/traces/$out" > data/$out.log 2>&1
echo "$out exit $? $(date)" >> data/ft_runs.log
