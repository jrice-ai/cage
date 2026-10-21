#!/bin/bash
# Checks for tools_patch_keep_readall.py (v4), the KEEP_READ_ALL switch behind arm R. 100-step episodes, 25 episodes
# per update with 5 workers, one container at a time on the evaluation threads. About 6 minutes beside a training run.
# Logs go to a new data/kbr/<time> directory.
set -u
cd ~/cage || exit 2
img=cage-keep:dev
t=kbr_$(hostname)_$(date +%H%M%S)
L=data/kbr/$(date +%Y%m%d_%H%M%S)
mkdir -p "$L"
echo "logs in $L"
grep -q "# busy-pilot patch v4" repos/cage-4-submission/train.py || { echo "train.py lacks the v4 patch"; exit 2; }
CLEAR="-u KEEP_RESTORE -u KEEP_LR_SCALE -u KEEP_RED -u KEEP_WEIGHTS -u KEEP_CKPT -u KEEP_BUSY -u KEEP_RESUME
       -u KEEP_EPISODE_SEEDS -u KEEP_SHARED_ENV_SEED -u KEEP_N -u KEEP_WORKERS -u KEEP_CONCAT_EDGES -u KEEP_READ_ALL
       -u KEEP_MAX_THREADS -u KEEP_EPISODE_LEN -u KEEP_EPISODES -u KEEP_SEED -u CAGE_DOCKER_OPTS
       -u OMP_NUM_THREADS -u MKL_NUM_THREADS"
PILOT="KEEP_N=25 KEEP_WORKERS=5 KEEP_CONCAT_EDGES=1 KEEP_EPISODE_SEEDS=1 KEEP_MAX_THREADS=6"
CPUS=${KBR_CPUS:-18-23}

train() {  # tag, inner (variables set inside the container, may be empty), then VAR=value settings
  local tag=$1 inner=$2; shift 2
  env $CLEAR $PILOT KEEP_EPISODE_LEN=100 KEEP_CKPT=25 CAGE_DOCKER_OPTS="--name $t --memory=16g --cpuset-cpus=$CPUS" "$@" \
      bin/run $img bash -c "cd /work/repos/cage-4-submission && $inner python3 -u train.py $tag" >> "$L/$tag.log" 2>&1
  echo "  $tag exit $?"
}
key() { tr '\r' '\n' < "$L/$1.log" | grep -E '^(\[[0-9]+\] Loss: |Avg reward|\[[0-9]+\] decisions|learner reads)' | sed 's/, generate .*//'; }
verdict() { if [ "$1" = 0 ]; then echo "PASS $2"; else echo "FAIL $2"; fi; }

echo "1. Shipped read (five of twenty-five), 1 update"
train ${t}_s "" KEEP_SEED=4242 KEEP_EPISODES=25
key ${t}_s
grep -q "^learner reads 5 of 25 episodes per agent" "$L/${t}_s.log"; verdict $? "without the switch the learner reads 5 of 25"
grep -q "'N': 25" "$L/${t}_s.log" && ! grep -q "'read_all'" "$L/${t}_s.log"; verdict $? "the run config carries N 25 and no read_all key"

echo "2. Read all (arm R), two runs at one seed, 1 update each"
train ${t}_r1 "KEEP_READ_ALL=1" KEEP_SEED=4242 KEEP_EPISODES=25
train ${t}_r2 "KEEP_READ_ALL=1" KEEP_SEED=4242 KEEP_EPISODES=25
key ${t}_r1
grep -q "^learner reads 25 of 25 episodes per agent" "$L/${t}_r1.log"; verdict $? "with the switch the learner reads 25 of 25"
grep -q "'read_all': True" "$L/${t}_r1.log"; verdict $? "the run config records read_all"
diff <(key ${t}_r1) <(key ${t}_r2) > /dev/null; verdict $? "the second run prints the same losses, rewards and counts"
diff <(key ${t}_s | grep -E "decisions|Avg reward") <(key ${t}_r1 | grep -E "decisions|Avg reward") > /dev/null
verdict $? "the generated episodes are identical with and without the switch (same decisions and rewards), only the read differs"
! diff <(key ${t}_s | grep Loss) <(key ${t}_r1 | grep Loss) > /dev/null; verdict $? "the losses differ, since the learner saw different data"
ls repos/cage-4-submission/checkpoints/${t}_r1-0_u1.pt > /dev/null 2>&1; verdict $? "kept checkpoint named by updates"
echo "update times (generate, update) from the logs"
for x in s r1; do tr '\r' '\n' < "$L/${t}_$x.log" | grep -E '^\[[0-9]+\] decisions' | sed "s/^/  $x: /"; done
