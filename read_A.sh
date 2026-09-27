#!/bin/bash
# Morning read for queue A. Run from ~/cage after "queue_A done" appears in data/ft_runs.log.
cd ~/cage || exit 1
echo "== exits"; grep -c 'exit 0' <(tail -n 30 data/ft_runs.log); grep -v 'exit 0' <(tail -n 30 data/ft_runs.log)
echo "== RT ceilings"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 ConvOnly TargetARestricted TargetAOperational TargetA TargetB TargetBRestricted TargetBOperational Combined FailureTracker Impacter Degrader; do
  echo "RT $R: $(tail -n 1 data/rd_RT_${R}_none.log)"
done
echo "== KEEP, distance to ceiling closed by O1 at gap 32 (and O10 where run)"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 ConvOnly; do
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none data/traces/red_FSRedAgent${R} data/traces/o1_g32_FSRedAgent${R}
done
python3 tools_ceiling.py data/traces/rd_RT_w_none data/traces/red_FSRedAgentWrecker data/traces/wo_O1_g32 data/traces/wo_O10_g32 data/traces/wo_O13_g32
for R in TargetARestricted TargetAOperational TargetA TargetB TargetBRestricted TargetBOperational Combined FailureTracker Impacter Degrader; do
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none data/traces/red_FSRedAgent${R} data/traces/o1_g32_FSRedAgent${R} data/traces/o10_g32_FSRedAgent${R}
done
echo "== rule defenders, distance to ceiling closed"
python3 tools_ceiling.py data/traces/rd_RT_w_none data/traces/rd_R2_w_none data/traces/rd_R2_w_O1_g32 data/traces/rd_R2_w_O10_g32
python3 tools_ceiling.py data/traces/rd_RT_w_none data/traces/rd_R4t_w_none data/traces/rd_R4t_w_O1_g32
python3 tools_ceiling.py data/traces/rd_RT_s_none data/traces/rd_R2_s_none data/traces/rd_R2_s_O1_g32
python3 tools_ceiling.py data/traces/rd_RT_s_none data/traces/corpus_v1 data/traces/so_O1_g32
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48; do
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none data/traces/rd_R4_${R}_none data/traces/rd_R4_${R}_O1_g32
done
echo "== R2 along the targeting axis"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48; do
  python3 tools_fraction_ci.py data/traces/rd_R2_s_none data/traces/rd_R2_${R}_none data/traces/rd_R2_${R}_O1_g32
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none data/traces/rd_R2_${R}_none data/traces/rd_R2_${R}_O1_g32
done
echo "== eyes, twenty episodes"
for f in data/eyes_*.log; do echo "-- $f"; grep -v '^episode seed' "$f" | tail -n 14; done
