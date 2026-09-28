#!/bin/bash
# Queue F, 2026-09-27: the engagement gate (O15) at 100 episodes under --wait-busy, gap 32.
# Lane 1, KEEP under Wrecker: the O15r ladder (16, 24, 40), O15a (1, 2), O15c (2, 3), and O1 at
#   gaps 64 and 96 as matched cadences; KEEP under stock: O15r 3, O15c 2, O1 at gaps 32 and 64.
# Lane 2, the middle rung on the axis and on H-MARL, each with O15a 1, O15c 2 and O1 at gap 64:
#   Q16 (O15r 6), Q32 (O15r 11), H-MARL under Wrecker (O15r 10).
# Thresholds off Wrecker sit at the survey recall of Wrecker's 24 (about 0.75, read_svy.txt).
# 25 arms, about 75 minutes. Arms whose directory already holds 100 episodes are skipped.
# Exit lines in data/ft_runs.log.
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
have() { [ -d data/traces/$1 ] && [ "$(ls data/traces/$1 2>/dev/null | wc -l)" -ge 100 ]; }
keep() {   # keep RULE RED OUT [--engage E] [--min-gap G]
  local rule=$1 red=$2 out=$3; shift 3
  have $out && { echo "$out skipped, exists $(date)" >> data/ft_runs.log; return; }
  $K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $rule $* --budget 99999 --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
  echo "$out exit $? $(date)" >> data/ft_runs.log
}
hm() {     # hm RULE RED OUT [--engage E] [--min-gap G]
  local rule=$1 red=$2 out=$3; shift 3
  have $out && { echo "$out skipped, exists $(date)" >> data/ft_runs.log; return; }
  $H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --rule $rule $* --budget 99999 --red $red --episodes 100 --workers 6 --wait-busy --out /work/data/traces/$out" > data/$out.log 2>&1
  echo "$out exit $? $(date)" >> data/ft_runs.log
}
lane1() {
  W=FSRedAgentWrecker; S=FiniteStateRedAgent
  for e in 16 24 40; do keep O15r $W wo_O15r_e${e}_g32_wb --engage $e --min-gap 32; done
  for e in 1 2; do keep O15a $W wo_O15a_e${e}_g32_wb --engage $e --min-gap 32; done
  for e in 2 3; do keep O15c $W wo_O15c_e${e}_g32_wb --engage $e --min-gap 32; done
  for g in 64 96; do keep O1 $W wo_O1_g${g}_wb --min-gap $g; done
  keep O15r $S so_O15r_e3_g32_wb --engage 3 --min-gap 32
  keep O15c $S so_O15c_e2_g32_wb --engage 2 --min-gap 32
  for g in 32 64; do keep O1 $S so_O1_g${g}_wb --min-gap $g; done
}
lane2() {
  for spec in "FSRedAgentWreckerQ16 6" "FSRedAgentWreckerQ32 11"; do
    set -- $spec; red=$1; er=$2
    keep O15r $red o15r_e${er}_g32_${red}_wb --engage $er --min-gap 32
    keep O15a $red o15a_e1_g32_${red}_wb --engage 1 --min-gap 32
    keep O15c $red o15c_e2_g32_${red}_wb --engage 2 --min-gap 32
    keep O1 $red o1_g64_${red}_wb --min-gap 64
  done
  W=FSRedAgentWrecker
  hm O15r $W hm_wo_O15r_e10_g32_wb --engage 10 --min-gap 32
  hm O15a $W hm_wo_O15a_e1_g32_wb --engage 1 --min-gap 32
  hm O15c $W hm_wo_O15c_e2_g32_wb --engage 2 --min-gap 32
  hm O1 $W hm_wo_O1_g64_wb --min-gap 64
}
lane1 &
sleep 30
lane2 &
wait
echo "queue_F done $(date)" >> data/ft_runs.log
