#!/bin/bash
# Gates for tools_add_O15.py. Run from ~/cage after the patch is applied, about 4 minutes.
#   1. O2e smoke (flag off): expect mean -327.00 stdev 87.68 overrides/ep 77.0 agreements/ep 108.5
#   2. H-MARL compat gate (flag off), 3 episodes: expect -931.00, -1308.00, -469.00 (mean -902.67 sd 420.22)
#   3. O15c at --engage 1 is O1 at the same gap: 10 episodes under Wrecker with the flag, paired
#      against wo_O1_g32_wb's first ten; expect mean delta +0.0 and the same overrides per episode
cd ~/cage || exit 1
K='bin/run cage-keep:dev bash -c'
H='bin/run cage-hmarl:dev bash -c'
echo "== 1. O2e smoke"
$K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule O2e --episodes 2 --workers 2 --out /work/data/traces/o2e_smoke_o15" 2>&1 | tail -n 1
echo "== 2. H-MARL compat gate"
$H "cd /work/repos/Hierarchical-MARL/h-marl-3policy && python3 -u /work/scripts/capture_hmarl.py --compat --rule none --red FSRedAgentWrecker --episodes 3 --out /work/data/traces/hm_compat_gate3o15" 2>&1 | tail -n 4
echo "== 3. O15c e1 g32 wb against O1 g32 wb (same seeds)"
$K "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule O15c --engage 1 --min-gap 32 --budget 99999 --red FSRedAgentWrecker --episodes 10 --workers 6 --wait-busy --out /work/data/traces/gate_wo_O15c_e1_g32_wb" 2>&1 | tail -n 1
python3 tools_paired.py data/traces/wo_O1_g32_wb data/traces/gate_wo_O15c_e1_g32_wb 2>/dev/null | tail -n 1
for i in 0 1 2 3 4 5 6 7 8 9; do
  a=$(tail -n 1 data/traces/wo_O1_g32_wb/ep_0000$i.jsonl | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r["total_reward"], r["overrides"])')
  b=$(tail -n 1 data/traces/gate_wo_O15c_e1_g32_wb/ep_0000$i.jsonl | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r["total_reward"], r["overrides"], "engaged", r["engaged"], "hit", r["engaged_hit"], "quiet_comp", r["quiet_comp"])')
  echo "ep $i  O1: $a   O15c e1: $b"
done
head -c 400 data/traces/gate_wo_O15c_e1_g32_wb/ep_00000.jsonl | tr ',' '\n' | grep -E 'engage|window|wait_busy'
