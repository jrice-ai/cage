#!/bin/bash
# Read for the O15 pilots. Run from ~/cage after "pilot_O15 done" in data/ft_runs.log.
# Each pilot paired on its ten seeds against the control (red_FSRedAgentWrecker), O1 g32 wb (full
# cadence) and RT (rd_RT_w_none_wb, the ceiling): score, interventions per episode, gate
# bookkeeping, and the share of the distance to RT closed per intervention.
cd ~/cage || exit 1
echo "== exits"; tail -n 9 data/ft_runs.log | grep -v 'exit 0'; tail -n 9 data/ft_runs.log | grep -c 'exit 0'
python3 - <<'EOF'
import glob, json, os
def foot(d, n=10):
    out = {}
    for f in sorted(glob.glob(os.path.join("data/traces", d, "ep_*.jsonl")))[:n]:
        last = None
        for l in open(f):
            if l.strip(): last = l
        r = json.loads(last)
        if r.get("record") == "footer": out[os.path.basename(f)] = r
    return out
C = foot("red_FSRedAgentWrecker"); O = foot("wo_O1_g32_wb"); R = foot("rd_RT_w_none_wb")
m = lambda d, k: sum(v[k] for v in d.values()) / len(d)
print(f"{'arm':28} {'n':>2} {'mean':>8} {'d.ctl':>7} {'d.O1':>7} {'ovr':>5} {'def':>5} {'eng':>6} {'hit':>6} {'quiet':>6} {'closed':>7} {'per ovr':>8}")
print(f"{'control':28} {len(C):2} {m(C,'total_reward'):8.1f}")
print(f"{'O1 g32 wb':28} {len(O):2} {m(O,'total_reward'):8.1f} {m(O,'total_reward')-m(C,'total_reward'):+7.1f} {'':7} {m(O,'overrides'):5.1f} {m(O,'deferred'):5.1f} {'':6} {'':6} {'':6} {(m(O,'total_reward')-m(C,'total_reward'))/(m(R,'total_reward')-m(C,'total_reward')):7.3f} {(m(O,'total_reward')-m(C,'total_reward'))/(m(R,'total_reward')-m(C,'total_reward'))/m(O,'overrides'):8.4f}")
print(f"{'RT (ceiling)':28} {len(R):2} {m(R,'total_reward'):8.1f}")
for d in sorted(glob.glob("data/traces/pilot_wo_O15*_wb")):
    A = foot(os.path.basename(d))
    eps = sorted(set(A) & set(C) & set(O) & set(R))
    if not eps:
        print(os.path.basename(d), "no shared episodes"); continue
    a = {e: A[e] for e in eps}; c = {e: C[e] for e in eps}; o = {e: O[e] for e in eps}; r = {e: R[e] for e in eps}
    gap = m(r, 'total_reward') - m(c, 'total_reward'); delta = m(a, 'total_reward') - m(c, 'total_reward')
    ovr = m(a, 'overrides')
    print(f"{os.path.basename(d)[9:]:28} {len(eps):2} {m(a,'total_reward'):8.1f} {delta:+7.1f} {m(a,'total_reward')-m(o,'total_reward'):+7.1f} {ovr:5.1f} {m(a,'deferred'):5.1f} {m(a,'engaged'):6.0f} {m(a,'engaged_hit'):6.0f} {m(a,'quiet_comp'):6.0f} {delta/gap:7.3f} {delta/gap/ovr if ovr else float('nan'):8.4f}")
print("\nclosed: share of the distance from the control to RT closed on these ten seeds; per ovr: that share per intervention")
print("eng: agent-ticks with the gate open; hit: of those, with a compromised owned host (O1 would act); quiet: gate shut while a host was compromised")
EOF
