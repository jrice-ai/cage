#!/bin/bash
# Checks for tools_patch_keep_busy.py (v2) in the pilot configuration (5 episodes per update, 5
# workers, concat_edges, seeded episodes). Steps 1 to 5 use 100-step episodes. Step 6 runs two
# full-length updates per arm on 9 CPUs, the size of one server slot, and records time and peak
# memory. One container at a time. About 25 minutes. Logs go to a new data/kbt/<time> directory.
set -u
cd ~/cage || exit 2
img=cage-keep:dev
t=kbt_$(hostname)
L=data/kbt/$(date +%Y%m%d_%H%M%S)
ck=repos/cage-4-submission/checkpoints
mkdir -p "$L"
echo "logs in $L"
CLEAR="-u KEEP_RESTORE -u KEEP_LR_SCALE -u KEEP_RED -u KEEP_WEIGHTS -u KEEP_CKPT -u KEEP_BUSY -u KEEP_RESUME
       -u KEEP_EPISODE_SEEDS -u KEEP_SHARED_ENV_SEED -u KEEP_N -u KEEP_WORKERS -u KEEP_CONCAT_EDGES
       -u KEEP_MAX_THREADS -u KEEP_EPISODE_LEN -u KEEP_EPISODES -u KEEP_SEED -u CAGE_DOCKER_OPTS
       -u OMP_NUM_THREADS -u MKL_NUM_THREADS"
PILOT="KEEP_N=5 KEEP_WORKERS=5 KEEP_CONCAT_EDGES=1 KEEP_EPISODE_SEEDS=1"

train() {  # tag, then VAR=value settings on top of the pilot configuration; appends to $L/<tag>.log
  local tag=$1; shift
  env $CLEAR $PILOT KEEP_EPISODE_LEN=100 KEEP_CKPT=5 "$@" \
      bin/run $img bash -c "cd /work/repos/cage-4-submission && python3 -u train.py $tag" >> "$L/$tag.log" 2>&1
  echo "  $tag exit $?"
}
key() {  # per-update lines without the timings
  tr '\r' '\n' < "$L/$1.log" | grep -E '^(\[[0-9]+\] Loss: |Avg reward|\[[0-9]+\] decisions)' | sed 's/, generate .*//'
}
verdict() { if [ "$1" = 0 ]; then echo "PASS $2"; else echo "FAIL $2"; fi; }

echo "1. Two runs at one seed, 2 updates each"
train ${t}_a1 KEEP_SEED=4242 KEEP_EPISODES=10
train ${t}_a2 KEEP_SEED=4242 KEEP_EPISODES=10
key ${t}_a1
[ "$(key ${t}_a1 | wc -l)" = 6 ]; verdict $? "two updates logged"
diff <(key ${t}_a1) <(key ${t}_a2) > /dev/null; verdict $? "the second run prints the same losses, rewards and counts"
grep -q "actor parameters 476167 " "$L/${t}_a1.log"; verdict $? "agents built as the released weights (476,167 actor parameters)"
ls $ck/${t}_a1-0_u1.pt $ck/${t}_a1-4_u2.pt > /dev/null 2>&1; verdict $? "kept checkpoints u1 and u2, including the last update"

echo "2. Resume, 1 update and then on to 2"
train ${t}_r KEEP_SEED=4242 KEEP_EPISODES=5
train ${t}_r KEEP_SEED=4242 KEEP_EPISODES=10 KEEP_RESUME=1
grep -q "Resumed ${t}_r at episode 5" "$L/${t}_r.log"; verdict $? "the second call resumed after update 1"
diff <(key ${t}_a1 | tail -3) <(key ${t}_r | tail -3) > /dev/null; verdict $? "the resumed update matches the straight run"
train ${t}_r KEEP_SEED=4243 KEEP_EPISODES=15 KEEP_RESUME=1
grep -q "KEEP_RESUME: .* was written under" "$L/${t}_r.log"; verdict $? "a resume under another seed is refused"

echo "3. Busy flag removed, 1 update"
train ${t}_n KEEP_SEED=4242 KEEP_EPISODES=5 KEEP_BUSY=none
key ${t}_n
grep -q "'busy': 'none'" "$L/${t}_n.log" && key ${t}_n | grep -q "decisions per agent-episode 100.0$"
verdict $? "the policy chose an action at every step"

echo "4. Environments the shipped trainer sends its workers, 3 updates"
if [ -f scripts/check_env_replay.py ]; then
  bin/run $img python3 /work/scripts/check_env_replay.py 2>&1 | grep -E "update|distinct|in place" | tee "$L/env_replay.log"
else
  echo "FAIL scripts/check_env_replay.py is missing"
fi

echo "5. Evaluation with --log-policy, released weights, 4 episodes per arm"
for b in shipped none; do
  env $CLEAR KEEP_BUSY=$b bin/run $img bash -c "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule none --episodes 4 --workers 4 --log-policy --out /work/$L/eval_$b" > "$L/eval_$b.log" 2>&1
  echo "  eval_$b exit $?"
  tail -1 "$L/eval_$b.log"
done
python3 tools_busy_restores.py "$L/eval_shipped" "$L/eval_none"

echo "6. Full length, 2 updates per arm on 9 CPUs, time and peak memory"
cpus=0-8; [ "$(nproc)" -ge 9 ] || cpus=""
for arm in F N; do
  b=shipped; [ $arm = N ] && b=none
  name=kbt_full_$arm
  ( while sleep 5; do docker stats --no-stream --format '{{.MemUsage}}' $name 2>/dev/null | cut -d/ -f1; done ) > "$L/mem_$arm.txt" &
  sampler=$!
  env $CLEAR $PILOT KEEP_BUSY=$b KEEP_SEED=4242 KEEP_EPISODES=10 KEEP_MAX_THREADS=9 \
      CAGE_DOCKER_OPTS="--name $name --memory=24g ${cpus:+--cpuset-cpus=$cpus}" \
      bin/run $img bash -c "cd /work/repos/cage-4-submission && python3 -u train.py ${t}_full_$arm" > "$L/${t}_full_$arm.log" 2>&1
  echo "  ${t}_full_$arm exit $?"
  kill $sampler 2>/dev/null
  tr '\r' '\n' < "$L/${t}_full_$arm.log" | grep -E '^\[[0-9]+\] decisions'
  awk '{v=$1; u=v; sub(/[0-9.]+/, "", u); sub(/[A-Za-z]+/, "", v); m=v; if (u=="GiB") m=v*1024; else if (u=="KiB") m=v/1024; else if (u=="B") m=v/1048576; if (m>p) p=m} END {printf "  peak memory %.1f GiB\n", p/1024}' "$L/mem_$arm.txt"
done
free -g | head -2
nproc
