#!/bin/bash
# Read for queue E. Run from ~/cage after "queue_E done" in data/ft_runs.log.
cd ~/cage || exit 1
echo "== exits"; awk '/Sun Sep 27 1[0-9]:/' data/ft_runs.log | grep -v 'exit 0'; awk '/Sun Sep 27 1[0-9]:/' data/ft_runs.log | grep -c 'exit 0'
echo "== completeness"
for d in data/traces/*_wb; do n=$(for f in $d/ep_*.jsonl; do tail -n 1 "$f" | grep -c '"footer"'; done 2>/dev/null | awk '{s+=$1} END {print s+0}'); [ "$n" -lt 100 ] && echo "$(basename $d): $n"; done; echo "(end of list)"
echo "== the rule ladder under the flag (attempted means in ARMS 'Rule defenders')"
for k in R1 R2 R2d R3 R4 R4t R4p R4d RT; do for a in s w; do f=data/rd_${k}_${a}_none_wb.log; [ -f $f ] && echo "$k $a: $(tail -n 1 $f)"; done; done
echo "== paired against the attempted-condition arm of the same kind"
for k in R1 R3 R4 R4t R4p R4d; do for a in s w; do python3 tools_paired.py data/traces/rd_${k}_${a}_none data/traces/rd_${k}_${a}_none_wb | tail -n 1; done; done
echo "== the look along the axis on KEEP, waiting (O1 shares: 0.70, 0.71, 0.71, 0.75, 0.71 ConvOnly, 0.74 Wrecker)"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 ConvOnly; do
  python3 tools_paired.py data/traces/red_FSRedAgent${R} data/traces/o10_g32_FSRedAgent${R}_wb data/traces/o13_g32_FSRedAgent${R}_wb | tail -n 2
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb data/traces/red_FSRedAgent${R} data/traces/o10_g32_FSRedAgent${R}_wb data/traces/o13_g32_FSRedAgent${R}_wb
done
echo "== executed looks on the axis"
python3 tools_investigate.py data/traces/o10_g32_FSRedAgentWreckerQ16_wb data/traces/o10_g32_FSRedAgentWreckerQ48_wb data/traces/hm_wo_O10_g32_wb 2>&1 | grep -v '^$'
