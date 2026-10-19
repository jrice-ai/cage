#!/bin/bash
# Busy-flag pilot. KEEP trained from scratch with the busy flag as shipped (arm F) or removed (arm N),
# and the shipped-recipe control (arm S): flag as shipped, every parent environment on one seed and never
# reseeded, so every episode starts from one layout as in the released trainer, with the workers' sampling
# seeded so the run is reproducible (KEEP_EPISODE_SEEDS=workers, tools_patch_keep_seedmode.py).
# usage: run_keep_pilot.sh <F|N|S> <seed> <updates> [cpus] [resume]
#   updates  PPO updates to reach. One update is 5 seeded episodes (KEEP_N=5), the 5 that KEEP's
#            learner reads, so 400 updates match KEEP's 10,000 shipped episodes.
#   cpus     a --cpuset-cpus list such as 0-8, or "all" (default). KEEP_MAX_THREADS is set to its size.
#   resume   continue the run from repos/cage-4-submission/checkpoints/<tag>-state.pt, for example to
#            extend it to more updates
# All arms build the agents as the released weights were built (concat_edges=True). F and N runs at one
# seed share initial weights and every episode's environment seed. Kept checkpoints every 100 updates and
# at the last update, as checkpoints/<tag>-<agent>_u<updates>.pt. If the run fails after its state
# file has advanced, it is resumed automatically, up to 5 attempts. To stop a run for good,
#   touch ~/cage/data/<tag>.stop && docker stop <tag>
# Log in data/<tag>.log, starts, ends and code versions in data/pilot_runs.log. Launch with nohup.
set -u
arm=${1:-}; seed=${2:-}; updates=${3:-}; cpus=${4:-all}; resume=${5:-}
case $arm in F) busy=shipped; seeds=1; shared="" ;; N) busy=none; seeds=1; shared="" ;;
            S) busy=shipped; seeds=workers; shared="KEEP_SHARED_ENV_SEED=1 " ;;
            *) echo "arm must be F, N or S" >&2; exit 2 ;; esac
case $seed in ''|*[!0-9]*) echo "seed must be a number" >&2; exit 2 ;; esac
case $updates in ''|*[!0-9]*) echo "updates must be a number" >&2; exit 2 ;; esac
if [ "$seed" -lt 1000 ] || [ "$seed" -ge 9000 ]; then
  echo "use a seed from 1000 to 8999" >&2; exit 2
fi
tag=kbf_${arm}_s${seed}
cd ~/cage || exit 2
K=repos/cage-4-submission
state=$K/checkpoints/$tag-state.pt
unset KEEP_RESTORE KEEP_LR_SCALE KEEP_RED KEEP_SHARED_ENV_SEED KEEP_WEIGHTS KEEP_EPISODE_LEN KEEP_RESUME \
      OMP_NUM_THREADS MKL_NUM_THREADS
for m in "$K/wrapper/graph_wrapper.py|_KEEP_BUSY = " "$K/models/memory_buffer.py|getattr(self, 'gen', None)" \
         "$K/train.py|# busy-pilot patch v2" "$K/train.py|# busy-pilot patch v3" "bin/run|-e KEEP_CONCAT_EDGES" "scripts/oracle.py|--log-policy"; do
  grep -qF -e "${m#*|}" "${m%%|*}" || { echo "${m%%|*} is not patched. Run tools_patch_keep_busy.py and tools_patch_keep_seedmode.py first." >&2; exit 2; }
done
if [ -n "$resume" ]; then
  [ "$resume" = resume ] || { echo "the fifth argument must be resume" >&2; exit 2; }
  [ -f "$state" ] || { echo "no state file $state" >&2; exit 2; }
  export KEEP_RESUME=1
elif [ -f "$state" ]; then
  echo "$state exists. Pass resume to continue that run, or move the file away to start over." >&2; exit 2
fi
if [ "$cpus" = all ]; then
  threads=36; opts=""
else
  threads=0
  IFS=, read -ra parts <<< "$cpus"
  for p in "${parts[@]}"; do
    case $p in
      *-*) threads=$((threads + ${p#*-} - ${p%-*} + 1)) ;;
      *) threads=$((threads + 1)) ;;
    esac
  done
  opts="--cpuset-cpus=$cpus"
fi
rm -f data/$tag.stop
export CAGE_DOCKER_OPTS="--name $tag --memory=${PILOT_MEM:-24g} $opts"
export KEEP_BUSY=$busy KEEP_EPISODE_SEEDS=$seeds KEEP_SEED=$seed KEEP_N=5 KEEP_WORKERS=5 KEEP_CONCAT_EDGES=1 \
       KEEP_MAX_THREADS=$threads KEEP_EPISODES=$((updates * 5)) KEEP_CKPT=500
code=$(md5sum $K/train.py $K/wrapper/graph_wrapper.py $K/models/memory_buffer.py $K/models/cage4.py | cut -c1-8 | tr '\n' ' ')
image=$(docker image inspect -f '{{.Id}}' cage-keep:dev | cut -c8-19)
attempt=0
while :; do
  attempt=$((attempt + 1))
  before=$(stat -c %Y "$state" 2>/dev/null || echo none)
  echo "$(date -Is) start $tag attempt=$attempt host=$(hostname) cpus=$cpus threads=$threads updates=$updates resume=${KEEP_RESUME:-0} sha=$(git rev-parse --short HEAD) code=[$code] image=$image" >> data/pilot_runs.log
  bin/run cage-keep:dev bash -c "cd /work/repos/cage-4-submission && ${shared}python3 -u train.py $tag" >> data/$tag.log 2>&1
  rc=$?
  echo "$(date -Is) end $tag attempt=$attempt exit $rc" >> data/pilot_runs.log
  [ "$rc" = 0 ] && break
  [ -f data/$tag.stop ] && { echo "$(date -Is) $tag stopped by request" >> data/pilot_runs.log; break; }
  [ "$rc" = 125 ] && break          # docker could not start the container
  after=$(stat -c %Y "$state" 2>/dev/null || echo none)
  if [ "$after" = none ] || [ "$after" = "$before" ] || [ "$attempt" -ge 5 ]; then break; fi
  export KEEP_RESUME=1
  sleep 60
done
exit $rc
