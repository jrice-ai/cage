#!/bin/bash
# Read for queue D. Run from ~/cage after "queue_D done" (the second one) in data/ft_runs.log.
cd ~/cage || exit 1
echo "== exits after the phantom run (23:39 onward)"
awk '/23:39:|Sun Sep 27/' data/ft_runs.log | grep -v 'exit 0' ; awk '/Sun Sep 27/' data/ft_runs.log | grep -c 'exit 0'
echo "== completeness: every _wb directory with fewer than 100 footers"
for d in data/traces/*_wb; do n=$(for f in $d/ep_*.jsonl; do tail -n 1 "$f" | grep -c '"footer"'; done 2>/dev/null | awk '{s+=$1} END {print s+0}'); [ "$n" -lt 100 ] && echo "$(basename $d): $n"; done; echo "(end of list)"
echo "== the two reruns"
echo "RT Q32: $(tail -n 1 data/rd_RT_WreckerQ32_none_wb.log)"
python3 tools_ceiling.py data/traces/rd_RT_WreckerQ32_none_wb data/traces/red_FSRedAgentWreckerQ32 data/traces/o1_g32_FSRedAgentWreckerQ32_wb
python3 tools_ceiling.py data/traces/rd_RT_WreckerQ32_none_wb data/traces/hm_WreckerQ32_none_g0 data/traces/hm_WreckerQ32_O1_g32_wb
echo "== R2 along the axis, its own controls under the flag"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48; do
  echo "R2 $R: $(tail -n 1 data/rd_R2_${R}_none_wb.log)"
  python3 tools_paired.py data/traces/rd_R2_${R}_none_wb data/traces/rd_R2_${R}_O1_g32_wb | tail -n 1
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb data/traces/rd_R2_${R}_none_wb data/traces/rd_R2_${R}_O1_g32_wb
done
echo "== RT ceilings under the flag, Trident"
for R in TargetARestricted TargetAOperational TargetA TargetB TargetBRestricted TargetBOperational Combined FailureTracker Impacter Degrader; do echo "RT $R: $(tail -n 1 data/rd_RT_${R}_none_wb.log)"; done
echo "== KEEP, Trident, waiting O1 (attempted: seven negative shares, Impacter 0.63, Degrader 0.47)"
for R in TargetARestricted TargetAOperational TargetA TargetB TargetBRestricted TargetBOperational Combined FailureTracker Impacter Degrader; do
  python3 tools_paired.py data/traces/red_FSRedAgent${R} data/traces/o1_g32_FSRedAgent${R}_wb data/traces/o1_g32_FSRedAgent${R} | tail -n 2
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb data/traces/red_FSRedAgent${R} data/traces/o1_g32_FSRedAgent${R}_wb
done
echo "== H-MARL, Trident, waiting O1 (attempted: eight above RT, Impacter 0.01, Degrader 0.03)"
for R in TargetARestricted TargetAOperational TargetA TargetB TargetBRestricted TargetBOperational Combined FailureTracker Impacter Degrader; do
  python3 tools_paired.py data/traces/hm_${R}_none_g0 data/traces/hm_${R}_O1_g32_wb data/traces/hm_${R}_O1_g32 | tail -n 2
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb data/traces/hm_${R}_none_g0 data/traces/hm_${R}_O1_g32_wb
done
