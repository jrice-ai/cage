#!/bin/bash
# Checks for tools_patch_keep_seedmode.py (v3), the KEEP_EPISODE_SEEDS=workers mode behind the arm S control.
# 100-step episodes, 5 episodes per update, one container at a time. About 8 minutes beside a training run.
# Logs go to a new data/kbs/<time> directory, fingerprints to checkpoints/<tag>-fp.txt. Run after tools_patch_keep_seedmode.py from ~/cage.
set -u
cd ~/cage || exit 2
img=cage-keep:dev
t=kbs_$(hostname)_$(date +%H%M%S)   # fresh tags, so the fingerprint files start empty
L=data/kbs/$(date +%Y%m%d_%H%M%S)
ck=repos/cage-4-submission/checkpoints
mkdir -p "$L"
echo "logs in $L"
grep -q "# busy-pilot patch v3" repos/cage-4-submission/train.py || { echo "train.py lacks the v3 patch"; exit 2; }
CLEAR="-u KEEP_RESTORE -u KEEP_LR_SCALE -u KEEP_RED -u KEEP_WEIGHTS -u KEEP_CKPT -u KEEP_BUSY -u KEEP_RESUME
       -u KEEP_EPISODE_SEEDS -u KEEP_SHARED_ENV_SEED -u KEEP_N -u KEEP_WORKERS -u KEEP_CONCAT_EDGES
       -u KEEP_MAX_THREADS -u KEEP_EPISODE_LEN -u KEEP_EPISODES -u KEEP_SEED -u CAGE_DOCKER_OPTS
       -u OMP_NUM_THREADS -u MKL_NUM_THREADS"
PILOT="KEEP_N=5 KEEP_WORKERS=5 KEEP_CONCAT_EDGES=1 KEEP_MAX_THREADS=6"
CPUS=${KBS_CPUS:-18-23}   # the threads the workstation's pilot evaluations use beside training

train() {  # tag, inner (variables set inside the container, may be empty), then VAR=value settings
  local tag=$1 inner=$2; shift 2
  env $CLEAR $PILOT KEEP_EPISODE_LEN=100 KEEP_CKPT=5 CAGE_DOCKER_OPTS="--name $t --memory=12g --cpuset-cpus=$CPUS" "$@" \
      bin/run $img bash -c "cd /work/repos/cage-4-submission && $inner python3 -u train.py $tag" >> "$L/$tag.log" 2>&1
  echo "  $tag exit $?"
}
key() { tr '\r' '\n' < "$L/$1.log" | grep -E '^(\[[0-9]+\] Loss: |Avg reward|\[[0-9]+\] decisions)' | sed 's/, generate .*//'; }
fps() { grep '^update=' "$ck/$1-fp.txt" 2>/dev/null; }   # written by the episode workers
verdict() { if [ "$1" = 0 ]; then echo "PASS $2"; else echo "FAIL $2"; fi; }
FP="KEEP_ENV_FINGERPRINT=1"
SH="KEEP_SHARED_ENV_SEED=1"

echo "1. Arm S configuration (workers seeded, one parent seed), two runs at one seed, 2 updates each"
train ${t}_s1 "$FP $SH" KEEP_EPISODE_SEEDS=workers KEEP_SEED=4242 KEEP_EPISODES=10
train ${t}_s2 "$FP $SH" KEEP_EPISODE_SEEDS=workers KEEP_SEED=4242 KEEP_EPISODES=10
key ${t}_s1
grep -q "'episode_seeds': 'workers'" "$L/${t}_s1.log" && grep -q "'shared_env_seed': True" "$L/${t}_s1.log"
verdict $? "the run config records mode workers and the shared parent seed"
[ "$(key ${t}_s1 | wc -l)" = 6 ]; verdict $? "two updates logged"
diff <(key ${t}_s1) <(key ${t}_s2) > /dev/null; verdict $? "the second run prints the same losses, rewards and counts (sampling seeded)"
[ "$(fps ${t}_s1 | wc -l)" = 10 ] && [ "$(fps ${t}_s1 | awk '{print $NF}' | sort -u | wc -l)" = 1 ]
verdict $? "all ten episodes start from one layout (environment never reseeded, one parent seed)"
fps ${t}_s1 | head -2
ls $ck/${t}_s1-0_u1.pt $ck/${t}_s1-4_u2.pt > /dev/null 2>&1; verdict $? "kept checkpoints u1 and u2"

echo "2. Mode 1 (the F and N arms), 1 update, for contrast"
train ${t}_m1 "$FP" KEEP_EPISODE_SEEDS=1 KEEP_SEED=4242 KEEP_EPISODES=5
[ "$(fps ${t}_m1 | wc -l)" = 5 ] && [ "$(fps ${t}_m1 | awk '{print $NF}' | sort -u | wc -l)" = 5 ]
verdict $? "five episodes, five layouts (environment reseeded per episode)"

echo "3. Mode workers without the shared parent seed, 2 updates (the harness's seed+i parents, replayed)"
train ${t}_w "$FP" KEEP_EPISODE_SEEDS=workers KEEP_SEED=4242 KEEP_EPISODES=10
u0=$(fps ${t}_w | grep 'update=0 ' | awk '{print $NF}' | sort); u1=$(fps ${t}_w | grep 'update=5 ' | awk '{print $NF}' | sort)
[ "$(echo "$u0" | sort -u | wc -l)" = 5 ] && [ "$u0" = "$u1" ]
verdict $? "five layouts in an update, and the second update replays the first's"

echo "4. Resume in mode workers, 1 update and then on to 2, and a resume under mode 1 is refused"
train ${t}_r "$SH" KEEP_EPISODE_SEEDS=workers KEEP_SEED=4242 KEEP_EPISODES=5
train ${t}_r "$SH" KEEP_EPISODE_SEEDS=workers KEEP_SEED=4242 KEEP_EPISODES=10 KEEP_RESUME=1
grep -q "Resumed ${t}_r at episode 5" "$L/${t}_r.log"; verdict $? "the second call resumed after update 1"
diff <(key ${t}_s1 | tail -3) <(key ${t}_r | tail -3) > /dev/null; verdict $? "the resumed update matches the straight run"
train ${t}_r "$SH" KEEP_EPISODE_SEEDS=1 KEEP_SEED=4242 KEEP_EPISODES=15 KEEP_RESUME=1
grep -q "KEEP_RESUME: .* was written under" "$L/${t}_r.log"; verdict $? "a resume under mode 1 is refused"
