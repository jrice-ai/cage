#!/usr/bin/env bash
# usage: run_ft_resume.sh <red> <seed> <target_iter>
# Continues saved_policies/ft_<tag>/ up to iter_<target>, restarting from the last
# checkpoint whenever the trainer dies (their handle_extra_ticks off-by-one). Gives up after 3 failures.
r=$1; s=$2; target=$3; tag=ft_${r#FSRedAgent}_s$s
dir=repos/Hierarchical-MARL/h-marl-3policy/saved_policies/$tag
fails=0
while true; do
  last=$(ls -d $dir/iter_* 2>/dev/null | sed 's/.*iter_//' | sort -n | tail -n 1)
  if [ -z "$last" ]; then last=49; restore=saved_policies/sub/iter_49; else restore=saved_policies/$tag/iter_$last; fi
  if [ "$last" -ge "$target" ]; then echo "$tag reached iter_$last $(date)" >> data/ft_runs.log; break; fi
  HMARL_RED=$r HMARL_SEED=$s HMARL_RESTORE=$restore HMARL_ITER0=$((last+1)) HMARL_ITERS=$((target-last)) \
  HMARL_TRAIN_BATCH=100000 HMARL_MODEL_DIR=saved_policies/$tag HMARL_LOGDIR=logs/$tag \
  bin/run cage-hmarl:dev bash -c "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u subpolicies/train_subpolicies.py 12" >> data/$tag.log 2>&1
  if [ $? -ne 0 ]; then
    fails=$((fails+1)); echo "$tag failed after iter_$last, attempt $fails $(date)" >> data/ft_runs.log
    [ $fails -ge 3 ] && break
  fi
done
