# SUPERSEDED 2026-10-11 by recompute_criteria.py: this script scores against the same-step truth, which capture.py writes after the step ran. Kept for the record.
#!/usr/bin/env python3
"""Restore and Remove precision under two criteria, asserted and executed.
  truth   : the host held a red session at the step the directive was asserted (truth.red_hosts)
  latch   : the host was in the asserting agent's latched evidence set, i.e. named by a substantive
            entry of that agent's raw observation at some step since that agent's last executed
            Restore or Remove on it (the O2e definition, reconstructing the H-MARL wrapper's latch)
A directive counts as executed when the agent was not blocked (mid-action) at that step.
usage: python3 recompute_evidence.py DIR [--episodes N]"""
import glob, json, os, sys
from collections import Counter

argv = sys.argv[1:]; max_eps = 10**9
if "--episodes" in argv:
    i = argv.index("--episodes"); max_eps = int(argv[i+1]); del argv[i:i+2]
d = argv[0] if os.path.isdir(argv[0]) else os.path.join("data", "traces", argv[0])
META = {"success", "message", "action"}

# ---------------------------------------------------------------------------
# --rule-targets GAP: the targets the O1 rule would have chosen on these traces, scored on the
# agent's latch. O1 (oracle_rules.py line 745): target = first compromised owned host in the
# simulator's host order; fires when the agent's tick is at least GAP past its last firing.
def _owner_map(path):
    j = json.load(open(path))
    return {sn: f"blue_agent_{int(aid)}" for aid, sns in j.items() for sn in sns}


# --rule-at-restores: at every step where an agent executed a Restore, the target the O1 rule would
# have chosen for that agent (first compromised owned host in simulator order), scored on the
# agent's latch. RESULTS.md: "taken as the target a ground-truth rule would have chosen", 20 ep.
if "--rule-at-restores" in sys.argv:
    OWNER = _owner_map(os.path.expanduser("~/cage/scripts/cc4_subnets.json"))
    def owner(h):
        for sn, ag in OWNER.items():
            if h.startswith(sn): return ag
        return None
    from collections import defaultdict
    res = defaultdict(lambda: [0, 0])     # (truth_lag, latch_lag) -> [targets, on_latch]
    n = 0; restores = 0
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))[:max_eps]:
        rows = [json.loads(l) for l in open(f) if l.strip()]
        if rows[-1].get("record") != "footer": continue
        n += 1; order = {h: i for i, h in enumerate(rows[0].get("hosts") or [])}
        flagged = {}; prev_flagged = {}; prev_red = []
        for r in rows:
            if r.get("record") != "step": continue
            prev_flagged = {a: set(v) for a, v in flagged.items()}
            for agent, o in (r.get("obs") or {}).items():
                if isinstance(o, dict):
                    flagged.setdefault(agent, set()).update(h for h, v in o.items() if h not in META and isinstance(v, dict))
            red = sorted((r.get("truth") or {}).get("red_hosts") or [], key=lambda h: order.get(h, 10**9))
            for agent, a in (r.get("action") or {}).items():
                parts = a.strip("[]").split()
                if len(parts) < 2 or parts[0] not in ("Restore", "Remove"): continue
                if parts[0] == "Restore":
                    restores += 1
                    for tl, reds in ((0, red), (1, prev_red)):
                        comp = [h for h in reds if owner(h) == agent]
                        if not comp: continue
                        for ll, fl in ((0, flagged), (1, prev_flagged)):
                            res[(tl, ll)][0] += 1; res[(tl, ll)][1] += comp[0] in fl.get(agent, set())
                flagged.get(agent, set()).discard(parts[1].rstrip("]"))
            prev_red = red
    print(f"{os.path.basename(d)}: {n} episodes, KEEP Restores {restores}")
    for (tl, ll), (t, k) in sorted(res.items()):
        print(f"  truth {'same' if tl == 0 else 'prev'} step, latch {'same' if ll == 0 else 'prev'} step: targets {t}, on latch {100*k/max(t,1):.2f}%")
    raise SystemExit

if "--rule-targets" in sys.argv:
    gap = int(sys.argv[sys.argv.index("--rule-targets") + 1])
    budget = 77
    OWNER = _owner_map(os.path.expanduser("~/cage/scripts/cc4_subnets.json"))
    def owner(h):
        for sn, ag in OWNER.items():
            if h.startswith(sn): return ag
        return None
    n = 0; targets = 0; on_latch = 0; exhausted = 0
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))[:max_eps]:
        rows = [json.loads(l) for l in open(f) if l.strip()]
        if rows[-1].get("record") != "footer": continue
        n += 1; order = {h: i for i, h in enumerate(rows[0].get("hosts") or [])}
        flagged = {}; tick = {}; last = {}; fired = 0
        for r in rows:
            if r.get("record") != "step": continue
            for agent, o in (r.get("obs") or {}).items():
                if isinstance(o, dict):
                    flagged.setdefault(agent, set()).update(h for h, v in o.items() if h not in META and isinstance(v, dict))
            red = sorted((r.get("truth") or {}).get("red_hosts") or [], key=lambda h: order.get(h, 10**9))
            for agent in sorted(set(list(flagged) + [owner(h) for h in red if owner(h)])):
                tick[agent] = tick.get(agent, 0) + 1
                comp = [h for h in red if owner(h) == agent]
                if not comp: continue
                if fired >= budget: exhausted += 1; continue
                if gap and tick[agent] - last.get(agent, -10**9) < gap: continue
                last[agent] = tick[agent]; fired += 1; targets += 1
                on_latch += comp[0] in flagged.get(agent, set())
            # clear latch on executed Restore/Remove, as above
            for agent, a in (r.get("action") or {}).items():
                parts = a.strip("[]").split()
                if len(parts) >= 2 and parts[0] in ("Restore", "Remove"):
                    flagged.get(agent, set()).discard(parts[1].rstrip("]"))
    print(f"{os.path.basename(d)}: {n} episodes, O1 targets at gap {gap}: {targets} ({targets/max(n,1):.1f} per episode), on latch {100*on_latch/max(targets,1):.2f}%, budget-exhausted skips {exhausted}")
    raise SystemExit

c = Counter(); n = 0; exec_truth_per_ep = []
for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))[:max_eps]:
    rows = [json.loads(l) for l in open(f) if l.strip()]
    if rows[-1].get("record") != "footer": continue
    n += 1; flagged = {}; ep_exec_truth = 0
    for r in rows:
        if r.get("record") != "step": continue
        obs = r.get("obs") or {}
        for agent, o in obs.items():
            if isinstance(o, dict):
                flagged.setdefault(agent, set()).update(h for h, v in o.items() if h not in META and isinstance(v, dict))
        red = set((r.get("truth") or {}).get("red_hosts") or [])
        blocked = r.get("blocked") or {}
        for agent, a in (r.get("action") or {}).items():
            parts = a.strip("[]").split()
            if len(parts) < 2 or parts[0] not in ("Restore", "Remove"): continue
            typ, host = parts[0], parts[1].rstrip("]")
            executed = not blocked.get(agent, False)
            on_truth = host in red; on_latch = host in flagged.get(agent, set())
            for mode in (("asserted",) + (("executed",) if executed else ())):
                c[(typ, mode, "n")] += 1
                c[(typ, mode, "truth")] += on_truth
                c[(typ, mode, "latch")] += on_latch
            if executed:
                flagged.get(agent, set()).discard(host)
                if typ == "Restore" and on_truth: ep_exec_truth += 1
    exec_truth_per_ep.append(ep_exec_truth)
print(f"{os.path.basename(d)}: {n} episodes")
for typ in ("Restore", "Remove"):
    for mode in ("asserted", "executed"):
        k = c[(typ, mode, "n")]
        if not k: continue
        print(f"  {typ:8} {mode:9} n {k:6}  truth {100*c[(typ,mode,'truth')]/k:6.2f}%  latch {100*c[(typ,mode,'latch')]/k:6.2f}%")
if exec_truth_per_ep:
    print(f"  executed ground-truth Restores per episode {sum(exec_truth_per_ep)/n:.1f}")
