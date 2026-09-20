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


def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0):
    """Return intercept(agent_name, act) -> act. Rule bodies are verbatim from oracle.py.install_oracle."""
    if decoys is None:
        decoys = {}

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
        if rule in ("O2e", "O2er", "O2ew", "O2s", "O10", "O12", "O13"):
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
                    if h in st["h"]:
                        st["h"][h][1] = t
                    else:
                        st["h"][h] = [t, t]; stats["flags_new"] = stats.get("flags_new", 0) + 1
            own = set(owned_hosts(cyborg, agent_name))
            live = {h: fl for h, fl in st["h"].items() if h in own}
            if rule == "O2ew":
                live = {h: fl for h, fl in live.items() if t - fl[1] <= 30}
            if rule == "O2e":
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

    return intercept
