#!/usr/bin/env bash
# usage: run_ft.sh <red> <seed>   e.g. run_ft.sh FiniteStateRedAgent 0
r=$1; s=$2; tag=ft_${r#FSRedAgent}_s$s
HMARL_RED=$r HMARL_SEED=$s HMARL_RESTORE=saved_policies/sub/iter_49 HMARL_ITER0=50 HMARL_ITERS=10 \
HMARL_TRAIN_BATCH=100000 HMARL_MODEL_DIR=saved_policies/$tag HMARL_LOGDIR=logs/$tag \
bin/run cage-hmarl:dev bash -c "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u subpolicies/train_subpolicies.py 12" \
  > data/$tag.log 2>&1
echo "$tag done $(date)" >> data/ft_runs.log
