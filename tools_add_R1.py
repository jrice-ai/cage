#!/usr/bin/env python3
"""Add a hand-written (non-learned) blue defender to the oracle harness.

oracle_rules.py
  make_defender(cyborg, kind, stats, decoys) -> propose(agent_name, act), with .note(agent, executed)
    An alert is a substantive observation entry naming an owned host, excluding the reset listing
    and the echo of the rule's own action the step before; a confirmed file (Density >= 0.9)
    always counts. Alerts are counted per host since its last Restore.
    R1   restore only on a confirmed file; analyse alerted hosts; else sleep (forensic-only)
    R2   restore on the second alert or a confirmed file; analyse once-alerted hosts; else sleep
    R2d  as R2, idle steps deploy a decoy on an owned server without one
    R3   restore on the first alert or a confirmed file; else sleep (contain on any alert)
    R4   the playbook: enforce the mission comms policy inbound to my zones; restore on a confirmed
         file; first alert Remove, second alert Restore; idle steps decoy the least-decoyed host
    R4p  posture only; R4d posture and decoys (ablations)
    RT   restore a ground-truth-compromised owned host; else sleep (perfect eyes)
    Windows: no restore of the same host within 30 steps, no analyse within 10.
  make_oracle accepts "R1", "R2", "R2d", "R3", "RT" and "R2+O1", "R2+O10", ... : the defender's proposal
  replaces the policy's (KEEP's or H-MARL's) before the supervisor rule sees it, and whatever is
  executed is fed back to the defender's memory, so a supervisor's Restore clears the rule's flags.
  Unknown rule names raise ValueError instead of passing through.
oracle.py
  --rule accepts the defender forms; step records carry "defender": [[agent, reason, host], ...];
  footers carry defender_restores/analyses/decoys/sleeps/flags_new and defender_tp/fp/fn.

Idempotent: each edit tests for the code it inserts. Run from ~/cage.
"""
import os

RULES = "scripts/oracle_rules.py"
ORC = "scripts/oracle.py"


def edit(path, fn):
    src = open(path).read()
    new = fn(src)
    if new != src:
        open(path, "w").write(new); print("patched", path)
    else:
        print("already patched", path)


DEFENDER_CODE = """
try:
    from CybORG.Simulator.Actions import DeployDecoy
except ImportError:      # older CybORG layouts
    DeployDecoy = None
try:
    from CybORG.Simulator.Actions import BlockTrafficZone, AllowTrafficZone
except ImportError:
    try:
        from CybORG.Simulator.Actions.ConcreteActions.ControlTraffic import BlockTrafficZone, AllowTrafficZone
    except ImportError:
        BlockTrafficZone = AllowTrafficZone = None

KNOWN_RULES = {"none", "O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9r", "O9s",
               "O2e", "O2er", "O2ew", "O2s", "O10", "O11", "O12", "O13", "O14"}
DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "RT")
ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2}   # monitor alerts since the last eviction
RESTORE_WINDOW = 30      # O8's window: do not restore the same host twice within it
REMOVE_WINDOW = 10       # do not remove from the same host twice within it
ANALYSE_WINDOW = 10      # do not analyse the same host twice within it
DECOYS_PER_HOST = 3

# CC4's mission comms policy (EnterpriseScenarioGenerator._set_allowed_subnets_per_mission_phase),
# the pairs of zones allowed to communicate in each phase; symmetric. Everything else is fair
# game for a firewall rule at no cost to green, which never tries a disallowed route.
_HQ = ("public_access_zone_subnet", "admin_network_subnet", "office_network_subnet")
_C, _RA, _OA, _RB, _OB = ("contractor_network_subnet", "restricted_zone_a_subnet", "operational_zone_a_subnet",
                          "restricted_zone_b_subnet", "operational_zone_b_subnet")
_HQ_LINKS = [(h, z) for h in _HQ for z in (_C, _RA, _RB)]
COMMS_POLICY = {
    0: _HQ_LINKS + [(_RA, _C), (_OA, _RA), (_RB, _C), (_RB, _RA), (_OB, _RB)],
    1: _HQ_LINKS + [(_RB, _C), (_OB, _RB)],
    2: _HQ_LINKS + [(_RA, _C), (_OA, _RA)],
}
ALL_SUBNETS = _HQ + (_C, _RA, _OA, _RB, _OB, "internet_subnet")


def allowed_pairs(phase):
    p = COMMS_POLICY.get(int(phase), COMMS_POLICY[0])
    return {(a, b) for a, b in p} | {(b, a) for a, b in p}


def make_defender(cyborg, kind, stats, decoys):
    \"\"\"A hand-written blue policy. propose(agent_name, act) ignores act (the learned policy's
    proposal) and returns the rule's action; note(agent_name, executed) records whatever was
    executed for that agent this step, whoever chose it, so a supervisor's Restore clears the
    rule's alerts and starts its window.

    Eyes: an alert is a substantive observation entry naming an owned host, excluding the reset
    listing (the first observation names every host) and excluding the echo of the rule's own
    action on that host the step before, unless the entry carries a file at Density >= 0.9
    (which always counts and is the confirmed criterion). Alerts are counted per host since its
    last Restore; a Remove is the first rung and the next alert escalates.
      R1   restore only on a confirmed file; analyse alerted hosts; else sleep (forensic-only)
      R2   restore on the second alert or a confirmed file; analyse once-alerted hosts; else sleep
      R2d  as R2, idle steps deploy a decoy on an owned server without one
      R3   restore on the first alert or a confirmed file; else sleep (contain on any alert)
      R4   the playbook: enforce the mission comms policy inbound to my zones (block what the
           phase disallows, allow what it allows, re-converge on phase change); restore on a
           confirmed file; first alert Remove, second alert Restore; idle steps deploy a decoy
           on the owned host with the fewest (servers first, up to DECOYS_PER_HOST); else sleep
      R4p  posture only, then sleep                     (ablation)
      R4d  posture and decoys, no eviction              (ablation)
      RT   restore a ground-truth-compromised owned host; else sleep (perfect eyes)
    Counts go to stats under d_*; per-step reasons to stats["dact"] when the harness keeps it.\"\"\"
    if kind not in DEFENDERS:
        raise ValueError(f"unknown defender {kind}")
    META = {"success", "action", "message"}
    need = ALERTS_TO_RESTORE.get(kind, 10**9)
    posture = kind in ("R4", "R4p", "R4d")
    evict = kind in ("R1", "R2", "R2d", "R3", "R4")
    escalate = kind == "R4"                      # Remove on the first alert
    triage = kind in ("R1", "R2", "R2d")         # Analyse once-alerted hosts
    decoy = kind in ("R2d", "R4", "R4d")
    mem = {}

    def _st(agent_name):
        return mem.setdefault(agent_name, {"t": 0, "alerts": {}, "last": {}, "strict": {}, "restored": {},
                                           "removed": {}, "analysed": {}, "acted": {}, "blocked": set()})

    def _zones(agent_name):
        try:
            return list(MY_SUBNETS[int(agent_name[-1])])
        except Exception:
            return sorted({subnet_of(h) for h in owned_hosts(cyborg, agent_name) if subnet_of(h)})

    def _latch(agent_name, st):
        obs = cyborg.get_observation(agent_name) or {}
        t = st["t"]
        for h, v in obs.items():
            if h in META or not isinstance(v, dict):
                continue
            fl = v.get("Files") or []
            confirmed = any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in fl)
            if confirmed:
                if h not in st["strict"]:
                    stats["d_flags_new"] = stats.get("d_flags_new", 0) + 1
                st["strict"][h] = t
            if t == 1:                                   # reset listing, not evidence
                continue
            if st["acted"].get(h) == t - 1 and not confirmed:   # echo of our own action
                continue
            st["alerts"][h] = st["alerts"].get(h, 0) + 1
            st["last"][h] = t
            stats["d_alerts"] = stats.get("d_alerts", 0) + 1

    def _count(key):
        stats[key] = stats.get(key, 0) + 1

    def _reason(agent_name, why, host):
        if isinstance(stats.get("dact"), list):
            stats["dact"].append([agent_name, why, host])

    def _posture(agent_name, st):
        if BlockTrafficZone is None:
            return None
        phase = int(cyborg.environment_controller.state.mission_phase)
        ok = allowed_pairs(phase)
        want = {(s, z) for z in _zones(agent_name) for s in ALL_SUBNETS if s != z and (s, z) not in ok}
        to_block = sorted(want - st["blocked"])
        to_allow = sorted(st["blocked"] - want)
        if to_block:
            s, z = to_block[0]; _count("d_block"); _reason(agent_name, "block", f"{s}->{z}")
            return BlockTrafficZone(session=0, agent=agent_name, from_subnet=s, to_subnet=z)
        if to_allow:
            s, z = to_allow[0]; _count("d_allow"); _reason(agent_name, "allow", f"{s}->{z}")
            return AllowTrafficZone(session=0, agent=agent_name, from_subnet=s, to_subnet=z)
        return None

    def propose(agent_name, act):
        st = _st(agent_name)
        st["t"] += 1
        t = st["t"]
        own = owned_hosts(cyborg, agent_name)
        ownset = set(own)
        comp = {c[0] for c in compromised_by_agent(cyborg).get(agent_name, [])}
        if kind == "RT":
            cands = [h for h in own if h in comp
                     and t - st["restored"].get(h, -10**9) > RESTORE_WINDOW]
            if cands:
                tgt = cands[0]; _count("d_restore"); _reason(agent_name, "truth", tgt)
                return Restore(session=0, agent=agent_name, hostname=tgt)
            _count("d_sleep"); _reason(agent_name, "idle", "")
            return Sleep()
        _latch(agent_name, st)
        if posture:
            a_ = _posture(agent_name, st)
            if a_ is not None:
                return a_
        okr = lambda h: h in ownset and t - st["restored"].get(h, -10**9) > RESTORE_WINDOW
        flagged = {h for h in st["strict"] if okr(h)} | ({h for h, n in st["alerts"].items() if n >= need and okr(h)} if evict else set())
        stats["d_tp"] = stats.get("d_tp", 0) + len(comp & flagged)
        stats["d_fp"] = stats.get("d_fp", 0) + len(flagged - comp)
        stats["d_fn"] = stats.get("d_fn", 0) + len(comp - flagged)
        if flagged and (evict or kind in ("R4p", "R4d")):
            # confirmed files first, then by host value (zone exposure this phase, servers doubled,
            # divided by decoy load), then the most-alerted, most recent host
            tgt = sorted(flagged, key=lambda h: (h not in st["strict"], -_host_score(cyborg, h, decoys),
                                                 -st["alerts"].get(h, 0), -st["last"].get(h, 0)))[0]
            why = "strict" if tgt in st["strict"] else "alerts"
            _count("d_restore"); _reason(agent_name, why, tgt)
            return Restore(session=0, agent=agent_name, hostname=tgt)
        if escalate:
            rm = sorted((h for h, n in st["alerts"].items() if okr(h) and n >= 1 and h not in st["strict"]
                         and t - st["removed"].get(h, -10**9) > REMOVE_WINDOW
                         and st["last"][h] > st["removed"].get(h, -10**9)),      # one Remove per alert
                        key=lambda h: (-_host_score(cyborg, h, decoys), -st["alerts"][h], -st["last"][h]))
            if rm:
                tgt = rm[0]; _count("d_remove"); _reason(agent_name, "remove", tgt)
                return Remove(session=0, agent=agent_name, hostname=tgt)
        if triage:
            tr = sorted((h for h, n in st["alerts"].items() if okr(h) and n < need and h not in st["strict"]
                         and t - st["analysed"].get(h, -10**9) > ANALYSE_WINDOW
                         and st["last"][h] > st["analysed"].get(h, -10**9) + 1),   # alerted again since the last look
                        key=lambda h: (-st["alerts"][h], -st["last"][h]))
            if tr:
                tgt = tr[0]; _count("d_analyse"); _reason(agent_name, "triage", tgt)
                return Analyse(session=0, agent=agent_name, hostname=tgt)
        if decoy and DeployDecoy is not None:
            cap = 1 if kind == "R2d" else DECOYS_PER_HOST
            pool = [h for h in own if decoys.get(h, 0) < cap and (kind != "R2d" or "server" in h)]
            if pool:
                tgt = sorted(pool, key=lambda h: (decoys.get(h, 0), "server" not in h, h))[0]
                _count("d_decoy"); _reason(agent_name, "decoy", tgt)
                return DeployDecoy(session=0, agent=agent_name, hostname=tgt)
        _count("d_sleep"); _reason(agent_name, "idle", "")
        return Sleep()

    def note(agent_name, executed):
        st = _st(agent_name); t = st["t"]
        name = type(executed).__name__; h = getattr(executed, "hostname", None)
        if h:
            st["acted"][h] = t
        if name == "Restore" and h:
            st["restored"][h] = t
            st["strict"].pop(h, None); st["alerts"].pop(h, None); st["last"].pop(h, None)
            decoys[h] = 0
        elif name == "Remove" and h:
            st["removed"][h] = t                 # alerts are kept: the next one escalates to Restore
        elif name == "Analyse" and h:
            st["analysed"][h] = t
        elif name == "DeployDecoy" and h:
            decoys[h] = decoys.get(h, 0) + 1
        elif name == "BlockTrafficZone":
            st["blocked"].add((getattr(executed, "from_subnet", None), getattr(executed, "to_subnet", None)))
        elif name == "AllowTrafficZone":
            st["blocked"].discard((getattr(executed, "from_subnet", None), getattr(executed, "to_subnet", None)))

    propose.note = note
    return propose


"""


# the line that distinguishes the current defender block from every earlier one: a Remove fires
# once per alert (v3.1); earlier blocks re-fired it every REMOVE_WINDOW
CURRENT = 'and st["last"][h] > st["removed"].get(h, -10**9)),'
assert CURRENT in DEFENDER_CODE


def patch_rules(src):
    if "def make_defender(" not in src:
        old = "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0):\n"
        assert src.count(old) == 1, "make_oracle def not found"
        src = src.replace(old, DEFENDER_CODE + old)
    elif CURRENT not in src:
        # an earlier make_defender (R1/R1d/RT, or the v3 R4 with the Remove loop) is installed:
        # replace the whole block
        i = src.index("\ntry:\n    from CybORG.Simulator.Actions import DeployDecoy")
        j = src.index("def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0):\n")
        src = src[:i] + DEFENDER_CODE + src[j:]
    if "defender = make_defender(" not in src:
        old = ("    if decoys is None:\n"
               "        decoys = {}\n"
               "\n"
               "    flagged = {}")
        assert src.count(old) == 1, "make_oracle prologue not found"
        src = src.replace(old,
               "    if decoys is None:\n"
               "        decoys = {}\n"
               "\n"
               "    defender = None\n"
               "    if rule in DEFENDERS or \"+\" in rule:\n"
               "        _dk, _, rule = rule.partition(\"+\")\n"
               "        rule = rule or \"none\"\n"
               "        defender = make_defender(cyborg, _dk, stats, decoys)\n"
               "    if rule not in KNOWN_RULES:\n"
               "        raise ValueError(f\"unknown rule {rule}\")\n"
               "\n"
               "    flagged = {}")
    if "defender.note(" not in src:
        old = ('''    _tick = {}; _last = {}
    def intercept(agent_name, act):
        stats["calls"] += 1
        _tick[agent_name] = _tick.get(agent_name, 0) + 1
        res = _decide(agent_name, act)
        if res is not act:
            if min_gap and _tick[agent_name] - _last.get(agent_name, -10**9) < min_gap:
                stats["override"] -= 1
                stats["deferred"] = stats.get("deferred", 0) + 1
                return act
            _last[agent_name] = _tick[agent_name]
            _k = "exec_" + type(res).__name__
            stats[_k] = stats.get(_k, 0) + 1
            stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
        return res
''')
        assert src.count(old) == 1, "intercept body not found"
        src = src.replace(old, '''    _tick = {}; _last = {}
    def intercept(agent_name, act):
        stats["calls"] += 1
        if defender is not None:
            act = defender(agent_name, act)      # the rule defender's proposal replaces the policy's
        _tick[agent_name] = _tick.get(agent_name, 0) + 1
        res = _decide(agent_name, act)
        if res is not act:
            if min_gap and _tick[agent_name] - _last.get(agent_name, -10**9) < min_gap:
                stats["override"] -= 1
                stats["deferred"] = stats.get("deferred", 0) + 1
                res = act
            else:
                _last[agent_name] = _tick[agent_name]
                _k = "exec_" + type(res).__name__
                stats[_k] = stats.get(_k, 0) + 1
                stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
        if defender is not None:
            defender.note(agent_name, res)       # whatever runs, the rule remembers it
        return res
''')
    return src


def patch_oracle(src):
    if '"R4+O1"' not in src:
        old = 'choices=["none", "O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9r", "O9s", "O2e", "O2er", "O2ew", "O2s", "O11", "O10", "O12", "O13"])'
        if src.count(old) != 1:      # an earlier version of this patch installed the R1 list
            import re as _re
            src, n = _re.subn(r'choices=\["none", "O1"[^)]*"RT\+O1"\],\n\s*help="[^"]*"\)', "CHOICES_PLACEHOLDER)", src, flags=_re.S)
            assert n == 1, "--rule choices not found"
            old = "CHOICES_PLACEHOLDER)"
        src = src.replace(old,
               'choices=["none", "O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9r", "O9s", "O2e", "O2er", "O2ew", "O2s", "O11", "O10", "O12", "O13",\n'
               '                            "R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "RT",\n'
               '                            "R1+O1", "R2+O1", "R2+O10", "R3+O1", "R4+O1", "R4+O10", "R4+O13", "R4+O2s", "R4d+O1", "RT+O1"],\n'
               '                   help="a supervisor rule on KEEP, or a rule defender (R1 to R4, RT), optionally with a supervisor rule on top (R4+O1)")')
    if 'stats["dact"] = []' not in src:
        old = "    stats = Counter()\n    decoys = {}\n"
        assert src.count(old) == 1, "stats init not found"
        src = src.replace(old, "    stats = Counter()\n    stats[\"dact\"] = []      # rule defender's per-step reasons; emptied into each step record\n    decoys = {}\n")
    if '"defender": stats.get("dact")' not in src:
        old = '                "overrides": stats.pop("ovr", []),\n            }) + "\\n")\n'
        assert src.count(old) == 1, "step record not found"
        src = src.replace(old,
               '                "overrides": stats.pop("ovr", []),\n'
               '                "defender": stats.get("dact") or [],\n'
               '            }) + "\\n")\n'
               '            stats["dact"] = []\n')
    if '"defender_restores"' not in src:
        old = '            "latch_fn": stats.get("fn", 0), "latch_own": stats.get("own", 0),\n'
        assert src.count(old) == 1, "footer latch line not found"
        src = src.replace(old, old +
               '            "defender_restores": stats.get("d_restore", 0), "defender_analyses": stats.get("d_analyse", 0),\n'
               '            "defender_decoys": stats.get("d_decoy", 0), "defender_sleeps": stats.get("d_sleep", 0),\n'
               '            "defender_flags_new": stats.get("d_flags_new", 0), "defender_alerts": stats.get("d_alerts", 0),\n'
               '            "defender_removes": stats.get("d_remove", 0), "defender_blocks": stats.get("d_block", 0), "defender_allows": stats.get("d_allow", 0),\n'
               '            "defender_tp": stats.get("d_tp", 0), "defender_fp": stats.get("d_fp", 0), "defender_fn": stats.get("d_fn", 0),\n')
    else:
        # earlier versions of this patch installed shorter footers; bring them up to date
        if '"defender_alerts"' not in src:
            old = '            "defender_flags_new": stats.get("d_flags_new", 0),\n'
            assert src.count(old) == 1, "installed flags_new line not found"
            src = src.replace(old, '            "defender_flags_new": stats.get("d_flags_new", 0), "defender_alerts": stats.get("d_alerts", 0),\n')
        if '"defender_removes"' not in src:
            old = '            "defender_flags_new": stats.get("d_flags_new", 0), "defender_alerts": stats.get("d_alerts", 0),\n'
            assert src.count(old) == 1, "installed alerts line not found"
            src = src.replace(old, old + '            "defender_removes": stats.get("d_remove", 0), "defender_blocks": stats.get("d_block", 0), "defender_allows": stats.get("d_allow", 0),\n')
    return src


edit(RULES, patch_rules)
edit(ORC, patch_oracle)
print("done")
