"""Shared oracle rules and helpers. Imported by oracle.py (KEEP) and capture_hmarl.py (H-MARL).
Rule bodies are moved verbatim from oracle.py; do not edit them here without re-running the
reproduction checks in tools_refactor_oracle.py."""
import json, os, random
from CybORG.Simulator.Actions import Restore, Remove, Monitor, Sleep, Analyse

try:
    from wrapper.globals import MY_SUBNETS, MAX_HOSTS, MAX_ACTIONS, NODE_ACTIONS
except ImportError:
    _j = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cc4_subnets.json")))
    MY_SUBNETS = {int(k): v for k, v in _j.items()}
    MAX_HOSTS = MAX_ACTIONS = NODE_ACTIONS = None

# --- provenance (added 2026-09-15) ---
import os as _os, platform as _platform, subprocess as _subprocess

def _harness_sha():
    sha = _os.environ.get("HARNESS_SHA")
    if sha:
        return sha
    try:
        here = _os.path.dirname(_os.path.abspath(__file__))
        return _subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here,
                                        stderr=_subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"

HARNESS_SHA = _harness_sha()
MACHINE = _platform.node()
RED_AGENT_NAME = "FiniteStateRedAgent"   # overwritten where --red is resolved
# --- end provenance ---

EPISODE_LENGTH = 500
BLUE = [f"blue_agent_{i}" for i in range(5)]
RED = [f"red_agent_{i}" for i in range(6)]

OWNER = {}
for _aid, _sns in MY_SUBNETS.items():
    for _sn in _sns:
        OWNER[_sn] = f"blue_agent_{_aid}"

EXPENSIVE = {"restricted_zone_a_subnet", "restricted_zone_b_subnet"}



def subnet_of(hostname):
    for sn in OWNER:
        if hostname.startswith(sn):
            return sn
    return None


_HOSTS_CACHE = {}
_IMPACT_SEEN = {}


def note_impacts(cyborg, step):
    key = id(cyborg)
    d = _IMPACT_SEEN.setdefault(key, {})
    if step == 0:
        d.clear()   # a recycled id or a reset() must not inherit the last episode's impacts
    for a in [f'red_agent_{i}' for i in range(6)]:
        act = cyborg.get_last_action(a)
        if act is None:
            continue
        txt = str(act)
        if 'Impact' in txt or 'Degrade' in txt:
            parts = txt.strip('[]').split()
            if len(parts) > 1:
                d[parts[1]] = step
    return d


def owned_hosts(cyborg, agent_name):
    # Cached per agent against the live State object (held strongly, so its address
    # cannot be recycled by a later episode) and its host-name tuple, so a fresh
    # CybORG per episode and a reset() of the same CybORG both invalidate it.
    st = cyborg.environment_controller.state
    names = tuple(st.hosts)
    ent = _HOSTS_CACHE.get(agent_name)
    if ent is None or ent[0] is not st or ent[1] != names:
        ent = (st, names, [
            h for h in names
            if "router" not in h and subnet_of(h)
            and OWNER.get(subnet_of(h)) == agent_name])
        _HOSTS_CACHE[agent_name] = ent
    return ent[2]


def compromised_by_agent(cyborg):
    st = cyborg.environment_controller.state
    out = {}
    for hn, h in st.hosts.items():
        if any(a.startswith("red") and s for a, s in h.sessions.items()):
            sn = subnet_of(hn)
            if sn:
                out.setdefault(OWNER[sn], []).append((hn, sn))
    return out


SERVER_W = 2.0


def _zone_weight(cyborg, subnet):
    ph = int(cyborg.environment_controller.state.mission_phase)
    tbl = cyborg.environment_controller.team_reward_calculators[
        "Blue"]["BlueRewardMachine"].get_phase_rewards(ph)
    e = tbl.get(subnet, {})
    return -(e.get("LWF", 0) + e.get("ASF", 0) + e.get("RIA", 0))


def _host_score(cyborg, hostname, decoys):
    sn = subnet_of(hostname)
    w = _zone_weight(cyborg, sn) if sn else 0.0
    if "server" in hostname:
        w *= SERVER_W
    return w / (1.0 + decoys.get(hostname, 0))



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
               "O2e", "O2er", "O2ew", "O2s", "O10", "O11", "O12", "O13", "O14",
               "O2f", "O2fr", "O2fw"}
DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "R4tn", "RT")
ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2, "R4t": 2, "R4t3": 3, "R4tn": 2}   # monitor alerts since the last eviction
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
    """A hand-written blue policy. propose(agent_name, act) ignores act (the learned policy's
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
      R4t  R4 with Analyse on the first alert in place of Remove   (ablation)
      R4t3 R4t with Restore on the third alert instead of the second (ablation)
      R4tn R4t without posture: decoys, triage, two-alert Restore, no blocks (ablation)
      R4d  posture and decoys, no eviction              (ablation)
      RT   restore a ground-truth-compromised owned host; else sleep (perfect eyes)
    Counts go to stats under d_*; per-step reasons to stats["dact"] when the harness keeps it."""
    if kind not in DEFENDERS:
        raise ValueError(f"unknown defender {kind}")
    META = {"success", "action", "message"}
    need = ALERTS_TO_RESTORE.get(kind, 10**9)
    posture = kind in ("R4", "R4p", "R4d", "R4t", "R4t3")
    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t", "R4t3", "R4tn")
    escalate = kind == "R4"                      # Remove on the first alert
    triage = kind in ("R1", "R2", "R2d", "R4t", "R4t3", "R4tn")  # Analyse alerted hosts below the threshold
    decoy = kind in ("R2d", "R4", "R4d", "R4t", "R4t3", "R4tn")
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


def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0):
    """Return intercept(agent_name, act) -> act. Rule bodies are verbatim from oracle.py.install_oracle."""
    if decoys is None:
        decoys = {}

    defender = None
    if rule in DEFENDERS or "+" in rule:
        _dk, _, rule = rule.partition("+")
        rule = rule or "none"
        defender = make_defender(cyborg, _dk, stats, decoys)
    if rule not in KNOWN_RULES:
        raise ValueError(f"unknown rule {rule}")

    flagged = {}   # O2e: agent_name -> hosts named by a substantive obs since last Restore/Remove
    META = {"success", "action", "message"}

    def _decide(agent_name, act):
        if rule == "none":
            return act

        if rule in ("O9r", "O9s"):
            name = type(act).__name__
            if name == "DeployDecoy":
                t = getattr(act, "hostname", None)
                if t:
                    decoys[t] = decoys.get(t, 0) + 1
                return act

            dirty = {c[0] for c in
                     compromised_by_agent(cyborg).get(agent_name, [])}
            pool = [h for h in owned_hosts(cyborg, agent_name)
                    if h not in dirty]
            if not pool:
                return act
            ranked = sorted(pool,
                            key=lambda h: -_host_score(cyborg, h, decoys))

            if rule == "O9s":
                if name != "Restore":
                    return act
                tgt = getattr(act, "hostname", None)
                cutoff = set(ranked[:max(1, len(ranked) // 3)])
                if tgt in cutoff:
                    stats["agree"] += 1
                    return act
                if stats["override"] >= budget:
                    stats["exhausted"] += 1
                    return act
                stats["override"] += 1
                decoys[ranked[0]] = 0
                return Restore(session=0, agent=agent_name,
                               hostname=ranked[0])

            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            if name == "Restore" and getattr(act, "hostname", None) == ranked[0]:
                stats["agree"] += 1
                return act
            stats["override"] += 1
            decoys[ranked[0]] = 0
            return Restore(session=0, agent=agent_name, hostname=ranked[0])

        comp = compromised_by_agent(cyborg).get(agent_name, [])

        if rule == "O8":
            if type(act).__name__ == "Restore":
                tgt = getattr(act, "hostname", None)
                dirty = {c[0] for c in comp}
                hist = _IMPACT_SEEN.get(id(cyborg), {})
                step_now = cyborg.environment_controller.step_count
                recent = tgt in hist and (step_now - hist[tgt]) <= 30
                if tgt not in dirty and not recent:
                    stats["override"] += 1
                    return Sleep()
                stats["agree"] += 1
            return act

        if rule == "O7":
            if type(act).__name__ in ("Restore", "Remove"):
                pool = owned_hosts(cyborg, agent_name)
                if pool:
                    stats["override"] += 1
                    return type(act)(session=0, agent=agent_name,
                                     hostname=random.choice(pool))
            return act

        if rule == "O6":
            if type(act).__name__ in ("Restore", "Remove"):
                tgt = getattr(act, "hostname", None)
                if tgt not in {c[0] for c in comp}:
                    stats["override"] += 1
                    return Sleep()
                stats["agree"] += 1
            return act
        if rule in ("O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O10", "O12", "O13"):
            obs = cyborg.get_observation(agent_name) or {}
            st = flagged.setdefault(agent_name, {"t": 0, "h": {}})   # h: host -> [first_seen, last_seen]
            st["t"] += 1
            t = st["t"]
            for h, v in obs.items():
                if h not in META and isinstance(v, dict):
                    if rule in ("O2s", "O10", "O12", "O13"):
                        _fl = v.get("Files") or []
                        if not any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in _fl):
                            continue
                    if rule in ("O2f", "O2fr", "O2fw"):
                        _fl = v.get("Files") or []
                        _conf = any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in _fl)
                        if not _conf and (t == 1 or st.get("acted") == (h, t - 1)):
                            continue           # the reset listing, or the echo of this agent's own action
                    if h in st["h"]:
                        st["h"][h][1] = t
                    else:
                        st["h"][h] = [t, t]; stats["flags_new"] = stats.get("flags_new", 0) + 1
            own = set(owned_hosts(cyborg, agent_name))
            live = {h: fl for h, fl in st["h"].items() if h in own}
            if rule in ("O2ew", "O2fw"):
                live = {h: fl for h, fl in live.items() if t - fl[1] <= 30}
            if rule in ("O2e", "O2f"):
                ecomp = sorted(live, key=lambda h: live[h][0])       # oldest flag first
            else:
                ecomp = sorted(live, key=lambda h: -live[h][1])      # most recently seen first
            _gt = {c[0] for c in comp}; _ev = set(ecomp)
            stats["tp"] = stats.get("tp", 0) + len(_gt & _ev)
            stats["fp"] = stats.get("fp", 0) + len(_ev - _gt)
            stats["fn"] = stats.get("fn", 0) + len(_gt - _ev)
            stats["own"] = stats.get("own", 0) + len(own)
            acting_on = getattr(act, "hostname", None)
            if type(act).__name__ in ("Restore", "Remove") and acting_on in ecomp:
                stats["agree"] += 1
                st["h"].pop(acting_on, None)
                return act
            if rule == "O13":
                inv = st.setdefault("inv", {})            # host -> agent-step of last investigation
                cands = [c[0] for c in comp if c[0] not in st["h"] and t - inv.get(c[0], -10**9) >= 50]
                if not cands:
                    return act
                if stats["override"] >= budget:
                    stats["exhausted"] += 1
                    return act
                cands.sort(key=lambda h: inv.get(h, -10**9))   # least recently investigated first
                tgt = cands[0]; inv[tgt] = t
                stats["override"] += 1
                return Analyse(session=0, agent=agent_name, hostname=tgt)
            if rule in ("O10", "O12"):
                if rule == "O12" and ecomp:
                    if stats["override"] >= budget:
                        stats["exhausted"] += 1
                        return act
                    stats["override"] += 1
                    tgt = ecomp[0]; st["h"].pop(tgt, None)
                    return Restore(session=0, agent=agent_name, hostname=tgt)
                unflagged = [c[0] for c in comp if c[0] not in st["h"]]
                if not unflagged:
                    return act
                if stats["override"] >= budget:
                    stats["exhausted"] += 1
                    return act
                stats["override"] += 1
                return Analyse(session=0, agent=agent_name, hostname=unflagged[0])
            if not ecomp:
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            stats["override"] += 1
            tgt = ecomp[0]
            st["h"].pop(tgt, None)
            return Restore(session=0, agent=agent_name, hostname=tgt)

        if rule == "O4":
            comp = [c for c in comp if c[1] in EXPENSIVE]
        if not comp:
            return act

        target = comp[0][0]
        dirty = {c[0] for c in comp}
        name = type(act).__name__

        if rule == "O1":
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=target)
        if rule == "O11":
            if name in ("Restore", "Remove") and getattr(act, "hostname", None) in dirty:
                stats["agree"] += 1
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            if NODE_ACTIONS is None:
                return act
            pr = stats["probs"].get(agent_name) if isinstance(stats.get("probs"), dict) else None
            if pr is None:
                return act
            aid = int(agent_name[-1]); nslots = len(MY_SUBNETS[aid])
            best, bestp = None, 0.0
            for s in range(nslots):
                for k in (1, 2):                      # NODE_ACTIONS: 1 = Remove, 2 = Restore
                    base = s * MAX_ACTIONS + k * MAX_HOSTS
                    for t in range(MAX_HOSTS):
                        p_ = float(pr[base + t])
                        if p_ > bestp:
                            bestp, best = p_, (s, k, t)
            if best is None:
                return act
            s, k, t = best
            sn = MY_SUBNETS[aid][s]
            host = f"{sn}_user_host_{t-6}" if t > 5 else f"{sn}_server_host_{t}"
            stats["override"] += 1
            return NODE_ACTIONS[k](session=0, agent=agent_name, hostname=host)
        if rule == "O3":
            stats["override"] += 1
            return Remove(session=0, agent=agent_name, hostname=target)
        if rule == "O4":
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=target)
        if rule == "O5":
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            ph = int(cyborg.environment_controller.state.mission_phase)
            tbl = cyborg.environment_controller.team_reward_calculators[
                "Blue"]["BlueRewardMachine"].get_phase_rewards(ph)
            def _w(sn):
                e = tbl.get(sn, {})
                return -e.get("RIA", 0) + e.get("LWF", 0)
            ranked = sorted(comp, key=lambda c: -_w(c[1]))
            best, best_sn = ranked[0]
            if _w(best_sn) < 2:
                stats["skipped"] += 1
                return act
            name2 = type(act).__name__
            if name2 == "Restore" and getattr(act, "hostname", None) in dirty:
                stats["agree"] += 1
                return act
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=best)

        if rule == "O2":
            acting_on = getattr(act, "hostname", None)
            if name in ("Restore", "Remove") and acting_on in dirty:
                stats["agree"] += 1
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=target)
        return act

    def _fmt(a):
        return f"{type(a).__name__}:{getattr(a, 'hostname', '')}"

    _tick = {}; _last = {}
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
        if agent_name in flagged:                # O2f family: the executed action's host, for the echo test
            _h = getattr(res, "hostname", None)
            flagged[agent_name]["acted"] = (_h, flagged[agent_name]["t"]) if _h else None
        if defender is not None:
            defender.note(agent_name, res)       # whatever runs, the rule remembers it
        return res

    return intercept
