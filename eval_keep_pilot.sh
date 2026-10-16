#!/bin/bash
# Evaluate one kept pilot checkpoint at the stock adversary, 100 episodes on seeds 0 to 99, with
# scripts/oracle.py --rule none --log-policy.
# usage: eval_keep_pilot.sh <tag> <update> [busy] [workers]
#   tag      kbf_F_s4101, kbf_N_s4101, and so on
#   update   a kept update count, such as 100
#   busy     shipped or none. Default is the arm's own (F shipped, N none). The other value is the
#            crossed evaluation.
#   workers  parallel episodes (default 12)
# Reads pilot_ckpt/<tag>-<agent>_u<update>.pt, copied from the server's
# repos/cage-4-submission/checkpoints, stages them as keep_weights/<tag>_u<update>/gnn_ppo-<agent>.pt,
# and writes the traces to data/traces/<tag>_u<update>_<busy> (the container writes there) and the log
# to data/evals/. Refuses to overwrite, and checks that the traces record the weights and busy setting
# asked for. Results go to data/pilot_evals.log.
set -u
tag=${1:-}; update=${2:-}; busy=${3:-}; workers=${4:-12}
case $tag in kbf_[FN]_s[0-9]*) ;; *) echo "tag must look like kbf_F_s4101" >&2; exit 2 ;; esac
case $update in ''|*[!0-9]*) echo "update must be a number" >&2; exit 2 ;; esac
arm=${tag:4:1}
if [ -z "$busy" ]; then busy=shipped; [ "$arm" = N ] && busy=none; fi
case $busy in shipped|none) ;; *) echo "busy must be shipped or none" >&2; exit 2 ;; esac
cd ~/cage || exit 2
ck=pilot_ckpt
name=${tag}_u$update
stage=keep_weights/$name
out=data/traces/${name}_$busy
for i in 0 1 2 3 4; do
  [ -f "$ck/$tag-${i}_u$update.pt" ] || { echo "missing $ck/$tag-${i}_u$update.pt" >&2; exit 2; }
done
if [ -d "$stage" ]; then
  for i in 0 1 2 3 4; do
    cmp -s "$ck/$tag-${i}_u$update.pt" "$stage/gnn_ppo-$i.pt" || { echo "$stage exists and differs from the checkpoints" >&2; exit 2; }
  done
else
  mkdir -p "$stage" || { echo "cannot create $stage" >&2; exit 2; }
  for i in 0 1 2 3 4; do cp "$ck/$tag-${i}_u$update.pt" "$stage/gnn_ppo-$i.pt" || exit 2; done
fi
[ -e "$out" ] && { echo "$out exists. Move it away to evaluate again." >&2; exit 2; }
mkdir -p data/evals || { echo "cannot create data/evals" >&2; exit 2; }
log=data/evals/${name}_$busy.log
grep -qF -e "--log-policy" scripts/oracle.py || { echo "scripts/oracle.py is not patched" >&2; exit 2; }
env -u KEEP_RESTORE -u KEEP_LR_SCALE -u KEEP_RED -u KEEP_RESUME -u KEEP_EPISODE_SEEDS -u KEEP_N -u KEEP_CONCAT_EDGES \
    -u CAGE_DOCKER_OPTS KEEP_WEIGHTS=$name KEEP_BUSY=$busy \
    bin/run cage-keep:dev bash -c "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule none --episodes ${EVAL_EPISODES:-100} --workers $workers --log-policy --out /work/$out" > "$log" 2>&1
rc=$?
echo "$name busy=$busy exit $rc"
[ "$rc" = 0 ] || exit $rc
python3 - "$out" "$name" "$busy" <<'EOF' || exit 1
import glob, json, sys
out, name, busy = sys.argv[1:]
bad = []
for f in sorted(glob.glob(f"{out}/ep_*.jsonl")):
    h = json.loads(open(f).readline())
    if h.get("weights") != name or h.get("busy") != busy or not h.get("log_policy"):
        bad.append((f, h.get("weights"), h.get("busy"), h.get("log_policy")))
if bad:
    sys.exit(f"traces do not record the requested weights and busy setting, for example {bad[0]}")
EOF
python3 tools_busy_restores.py "$out" | tee -a data/pilot_evals.log
