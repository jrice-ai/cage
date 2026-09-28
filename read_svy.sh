#!/bin/bash
# Read for the O15 signal survey. Run from ~/cage after "svy_O15 done" in data/ft_runs.log.
# For each adversary: the signal's distribution over free agent-ticks, split by whether the agent
# had a compromised owned host, and for a grid of thresholds the recall, false-engagement and
# precision, with interventions per episode projected from O1's count at the same gap and
# adversary (O2's under stock, where no O1 arm at gap 32 exists).
cd ~/cage || exit 1
echo "== exits"; tail -n 11 data/ft_runs.log | grep -v 'exit 0'; tail -n 11 data/ft_runs.log | grep -c 'exit 0'
n() { if [ -f "$1" ]; then tail -n 1 "$1" | sed 's/.*overrides\/ep \([0-9.]*\).*/\1/'; else echo 0; fi; }
echo; echo "==== KEEP under Wrecker (O1 g32 wb: $(tail -n 1 data/wo_O1_g32_wb.log))"
python3 tools_signal.py svy_wo_O15r_wb svy_wo_O15a_wb --o1 $(n data/wo_O1_g32_wb.log)
echo; echo "==== KEEP under stock (O2 g32 wb as the reference: $(tail -n 1 data/o2_g32_wb.log))"
python3 tools_signal.py svy_so_O15r_wb svy_so_O15a_wb --o1 $(n data/o2_g32_wb.log)
for Q in Q16 Q32; do
  echo; echo "==== KEEP under Wrecker$Q (O1 g32 wb: $(tail -n 1 data/o1_g32_FSRedAgentWrecker${Q}_wb.log))"
  python3 tools_signal.py svy_O15r_FSRedAgentWrecker${Q}_wb svy_O15a_FSRedAgentWrecker${Q}_wb --o1 $(n data/o1_g32_FSRedAgentWrecker${Q}_wb.log)
done
echo; echo "==== H-MARL under Wrecker (O1 g32 wb: $(tail -n 1 data/hm_wo_O1_g32_wb.log))"
python3 tools_signal.py svy_hm_wo_O15r_wb svy_hm_wo_O15a_wb --o1 $(n data/hm_wo_O1_g32_wb.log)
echo; echo "==== O15c's signal (compromised owned hosts) is the second element of every record; integer grid from the O15r survey"
python3 - <<'EOF'
import glob, json, os
for d in ("svy_wo_O15r_wb", "svy_so_O15r_wb", "svy_O15r_FSRedAgentWreckerQ16_wb", "svy_O15r_FSRedAgentWreckerQ32_wb", "svy_hm_wo_O15r_wb"):
    cnt = {}
    for f in glob.glob(os.path.join("data/traces", d, "ep_*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r.get("record") == "step":
                for a, (s, nc) in (r.get("signal") or {}).items():
                    cnt[nc] = cnt.get(nc, 0) + 1
    tot = sum(cnt.values()) or 1
    print(f"{d:40} " + "  ".join(f"{k}:{v / tot:.3f}" for k, v in sorted(cnt.items())))
EOF
