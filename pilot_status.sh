#!/bin/bash
# One line per pilot run on this machine: updates completed, the last update's average training
# reward and timings, and the container's memory now ("stopped" if no container is running).
cd ~/cage || exit 2
mem=$(docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' 2>/dev/null)
for f in data/kbf_*.log; do
  [ -f "$f" ] || continue
  tag=$(basename "$f" .log)
  clean=$(tr '\r' '\n' < "$f" | grep -E '^(\[[0-9]+\] Loss: |\[[0-9]+\] decisions|Avg reward)')
  e=$(grep -E '^\[[0-9]+\] Loss: ' <<< "$clean" | tail -1 | sed 's/^\[\([0-9]*\)\].*/\1/')
  r=$(grep '^Avg reward' <<< "$clean" | tail -1 | awk '{print $NF}')
  t=$(grep -E '^\[[0-9]+\] decisions' <<< "$clean" | tail -1 | sed 's/^.*agent-episode \([0-9.]*\), generate \([0-9.]*\)s, update \([0-9.]*\)s/decisions \1  gen \2s  upd \3s/')
  m=$(awk -v t="$tag" '$1 == t {print $2}' <<< "$mem")
  printf '%-14s updates %4s  reward %8s  %s  mem %s\n' "$tag" "${e:+$((e / 5 + 1))}" "${r:-none}" "${t:-}" "${m:-stopped}"
done
echo "last entries in data/pilot_runs.log"
tail -4 data/pilot_runs.log | cut -c1-120
