#!/bin/bash
# The held-directive axis in the two framework-page metrics, for the figure update.
# Per point (uniform, Q04, Q16, Q32, Q48, Wrecker) and defender (KEEP, H-MARL, R2):
#   paired delta and wins, fraction of excess loss with a bootstrap interval (learned defenders
#   only; the denominator is not a ceiling for R2), share of the distance to RT with an interval.
# Run from ~/cage.
cd ~/cage || exit 1
pt() { case $1 in ConvOnly) echo uniform;; Wrecker) echo Wrecker;; *) echo ${1#Wrecker};; esac; }
echo "==== KEEP, O1 g32, directive held (stock control corpus_v1)"
for R in ConvOnly WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 Wrecker; do
  ctl=data/traces/red_FSRedAgent$R
  arm=data/traces/o1_g32_FSRedAgent${R}_wb; [ $R = Wrecker ] && arm=data/traces/wo_O1_g32_wb
  echo "-- $(pt $R)"
  python3 tools_paired.py $ctl $arm 2>/dev/null | tail -n 1
  python3 tools_fraction_ci.py data/traces/corpus_v1 $ctl $arm 2>/dev/null | tail -n 1
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb $ctl $arm 2>/dev/null | tail -n 1
done
echo; echo "==== H-MARL, O1 g32, directive held (stock control hm_s_none)"
for R in ConvOnly WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 Wrecker; do
  ctl=data/traces/hm_${R}_none_g0; arm=data/traces/hm_${R}_O1_g32_wb
  [ $R = Wrecker ] && { ctl=data/traces/hm_w_none; arm=data/traces/hm_wo_O1_g32_wb; }
  echo "-- $(pt $R)"
  python3 tools_paired.py $ctl $arm 2>/dev/null | tail -n 1
  python3 tools_fraction_ci.py data/traces/hm_s_none $ctl $arm 2>/dev/null | tail -n 1
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb $ctl $arm 2>/dev/null | tail -n 1
done
echo; echo "==== R2, O1 g32, directive held (share of the distance to RT only)"
for R in WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 Wrecker; do
  ctl=data/traces/rd_R2_${R}_none_wb; arm=data/traces/rd_R2_${R}_O1_g32_wb
  [ $R = Wrecker ] && { ctl=data/traces/rd_R2_w_none_wb; arm=data/traces/rd_R2_w_O1_g32_wb; }
  echo "-- $(pt $R)"
  python3 tools_paired.py $ctl $arm 2>/dev/null | tail -n 1
  python3 tools_ceiling.py data/traces/rd_RT_${R}_none_wb $ctl $arm 2>/dev/null | tail -n 1
done
echo; echo "==== the stock point, directive held"
python3 tools_paired.py data/traces/corpus_v1 data/traces/so_O1_g32_wb data/traces/o2_g32_wb 2>/dev/null | tail -n 2
python3 tools_ceiling.py data/traces/rd_RT_s_none_wb data/traces/corpus_v1 data/traces/so_O1_g32_wb data/traces/o2_g32_wb 2>/dev/null | tail -n 2
python3 tools_ceiling.py data/traces/rd_RT_s_none_wb data/traces/rd_R2_s_none_wb data/traces/rd_R2_s_O1_g32_wb 2>/dev/null | tail -n 1
echo; echo "==== RT under each point, held (the ceilings)"
for R in s ConvOnly WreckerQ04 WreckerQ16 WreckerQ32 WreckerQ48 w; do echo "$R: $(tail -n 1 data/rd_RT_${R}_none_wb.log)"; done
