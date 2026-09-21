#!/bin/bash
# Continue KEEP's shipped weights under one adversary.
# usage: run_keep_ft.sh <red> <seed> <episodes> [workers] [suffix]
#   red       FiniteStateRedAgent | FSRedAgentWrecker | FSRedAgentWreckerQ32 | ...
#   seed      KEEP_SEED: torch seed and base of the per-environment seeds (seed+i);
#             keep it away from 0-99 (evaluation seeds) and 9000+ (policy-seed nulls)
#   episodes  KEEP_EPISODES (25 per update; 2000 = 1M environment steps)
#   workers   KEEP_WORKERS (default 25)
#   suffix    appended to the tag as _<suffix>, e.g. "long" for a longer run at a seed already used
# Tag kft_<red minus FSRedAgent>_s<seed>. Trainer output in data/<tag>.log; rolling
# checkpoints in repos/cage-4-submission/checkpoints/<tag>-{i}_checkpoint.pt, kept
# ones every 500 episodes as <tag>-{i}_e<N>.pt; curve in logs/<tag>.pt; exit code
# appended to data/ft_runs.log.
# Run one at a time. joblib caps each worker's threads at cores/workers per
# process, unaware of other containers, so several runs side by side
# oversubscribe the machine (load average 90 to 185 on 24 cores, no update in
# ten minutes); a single run at 12 or 25 workers is clean.
cd ~/cage || exit 1
r=$1; s=$2; n=$3; w=${4:-25}
tag=kft_${r#FSRedAgent}_s$s${5:+_$5}
KEEP_RED=$r KEEP_SEED=$s KEEP_RESTORE=/work/repos/cage-4-submission/weights \
KEEP_EPISODES=$n KEEP_WORKERS=$w KEEP_CKPT=500 \
bin/run cage-keep:dev bash -c "cd /work/repos/cage-4-submission && python3 -u train.py $tag" > data/$tag.log 2>&1
echo "$tag exit $? $(date)" >> data/ft_runs.log
