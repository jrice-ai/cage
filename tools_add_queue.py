#!/usr/bin/env python3
"""Three additions for the pre-trial runs: a held click, an as-is supervisor with a look, and an
alert gate with as-is hands. Each part is independent and idempotent; every existing path is
unchanged, so the O2e smoke and the H-MARL compat gate must reproduce.

--queue first|last (oracle.py, capture_hmarl.py; needs --wait-busy; O1, O15r, O15c on a learned
policy). --wait-busy alone consults the supervisor only on free ticks, so a rule re-decides at the
moment its directive can run. A person does not: they click when they notice, and the click is
held. With --queue the supervisor is consulted on a busy tick (the gap floor permitting), its
directive is stored, and it fires at the agent's next free tick as decided, whatever is true by
then. "first" keeps the first decision of a busy stretch (a click, held); "last" replaces it on
every busy tick, and a decision to do nothing cancels it (the least stale case). Header field queue; footer fields queued, queue_fired,
queue_stale (fired on a host no longer compromised), queue_wait (ticks from decision to fire,
summed). The difference between an arm with --queue and the same arm without it is the price of
staleness, which decides whether the interface can afford to hold a click.

O16, the as-is supervisor: eyes are the O2f latch (substantive observation entries naming an
owned host, the reset listing and the echo of the agent's own last action excluded), hands are
a look and a restore. A latched host that no look has confirmed since its last restore gets an
Analyse (one per ANALYSE_WINDOW); a host whose look returned a file at Density >= 0.9 gets a
Restore. No ground truth anywhere. This is the ceiling of the trial's as-is display, which the
O2f family (restore on the latch alone) had read as inside the noise band. Footer field
o16_confirmed.

O15h, the alert gate with as-is hands: O15a's gate (alerts on the agent's own hosts over the
trailing window), but the restore goes to the host of the latest alert rather than to a
ground-truth compromised host. Footer field o15h_clean counts restores that landed on a host
that was not compromised (measurable because the scorer sees ground truth).

Run from ~/cage after tools_add_O15.py.
"""
RULES = "scripts/oracle_rules.py"
ORC = "scripts/oracle.py"
HM = "scripts/capture_hmarl.py"


def edit(path, fn):
    src = open(path).read()
    new = fn(src)
    if new != src:
        open(path, "w").write(new); print("patched", path)
    else:
        print("already patched", path)


def rep(src, old, new, what):
    assert src.count(old) == 1, f"{what}: expected one match, found {src.count(old)}"
    return src.replace(old, new)


O16_BLOCK = '''            if rule == "O16":
                # the as-is supervisor: eyes are the latch, hands are a look at a latched host and a
                # Restore once a look has returned a confirmed file; no ground truth anywhere
                conf = st.setdefault("conf", {}); inv = st.setdefault("inv", {}); rst = st.setdefault("rst", {})
                for h, v in obs.items():
                    if h not in META and isinstance(v, dict):
                        _fl = v.get("Files") or []
                        if any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in _fl):
                            if conf.get(h, -10**9) <= rst.get(h, -10**9):
                                stats["o16_confirmed"] = stats.get("o16_confirmed", 0) + 1
                            conf[h] = t
                if min_gap and _tick.get(agent_name, 0) - _last.get(agent_name, -10**9) < min_gap:
                    return act                # the gate is shut: nothing proposed, nothing booked
                hit = [h for h in ecomp if conf.get(h, -10**9) > rst.get(h, -10**9)]
                if hit:
                    if stats["override"] >= budget:
                        stats["exhausted"] += 1
                        return act
                    tgt = hit[0]; rst[tgt] = t; st["h"].pop(tgt, None)
                    stats["override"] += 1
                    return Restore(session=0, agent=agent_name, hostname=tgt)
                look = [h for h in ecomp if conf.get(h, -10**9) <= rst.get(h, -10**9)
                        and t - inv.get(h, -10**9) >= ANALYSE_WINDOW]
                if look:
                    if stats["override"] >= budget:
                        stats["exhausted"] += 1
                        return act
                    tgt = look[0]; inv[tgt] = t
                    stats["override"] += 1
                    return Analyse(session=0, agent=agent_name, hostname=tgt)
                return act
'''

O15H_BLOCK = '''            if rule == "O15h":                  # as-is hands: restore the host of the latest alert
                if not al:
                    return act
                tgt = al[-1][1]
                if tgt in {c[0] for c in comp}:
                    stats["engaged_hit"] = stats.get("engaged_hit", 0) + 1
                else:
                    stats["o15h_clean"] = stats.get("o15h_clean", 0) + 1
                stats["override"] += 1
                return Restore(session=0, agent=agent_name, hostname=tgt)
'''

QUEUE_INTERCEPT = '''    _tick = {}; _last = {}; _queued = {}
    def intercept(agent_name, act):
        stats["calls"] += 1
        if wait_busy and _busy(agent_name):
            stats["busy"] = stats.get("busy", 0) + 1
            _tick[agent_name] = _tick.get(agent_name, 0) + 1
            if defender is not None:
                defender.observe(agent_name)
                return Sleep()
            if queue and (queue == "last" or agent_name not in _queued) \\
                    and not (min_gap and _tick[agent_name] - _last.get(agent_name, -10**9) < min_gap):
                # the supervisor decides on the busy tick, as a person clicking would, and the
                # directive is held for the agent's next free tick; it is booked when it fires
                q = _decide(agent_name, act)
                if q is not act:
                    stats["override"] -= 1
                    if agent_name not in _queued:
                        stats["queued"] = stats.get("queued", 0) + 1
                    _queued[agent_name] = (q, _fmt(act), _tick[agent_name])
                elif queue == "last":
                    _queued.pop(agent_name, None)  # the latest decision is to do nothing
            return act
        if defender is not None:
            act = defender(agent_name, act)      # the rule defender's proposal replaces the policy's
        _tick[agent_name] = _tick.get(agent_name, 0) + 1
        fired = False
        if queue and agent_name in _queued:
            res, _from, _at = _queued.pop(agent_name)      # fires as decided, whatever is true now
            _h = getattr(res, "hostname", None)
            if _h and _h not in {c[0] for c in compromised_by_agent(cyborg).get(agent_name, [])}:
                stats["queue_stale"] = stats.get("queue_stale", 0) + 1
            stats["queue_wait"] = stats.get("queue_wait", 0) + (_tick[agent_name] - _at)
            stats["queue_fired"] = stats.get("queue_fired", 0) + 1
            stats["override"] += 1
            _last[agent_name] = _tick[agent_name]
            _k = "exec_" + type(res).__name__
            stats[_k] = stats.get(_k, 0) + 1
            stats.setdefault("ovr", []).append([agent_name, _from, _fmt(res)])
            fired = True
        else:
            res = _decide(agent_name, act)
        if res is not act and not fired:
'''


def patch_rules(src):
    # ---- names
    if '"O15h", "O16"}' not in src:
        src = rep(src, '"O2f", "O2fr", "O2fw", "O15r", "O15a", "O15c"}',
                  '"O2f", "O2fr", "O2fw", "O15r", "O15a", "O15c", "O15h", "O16"}', "KNOWN_RULES")
    # ---- queue: signature, validation, intercept
    if "engage=None, window=16, queue=None):" not in src:
        src = rep(src, "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False, engage=None, window=16):\n",
                  "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False, engage=None, window=16, queue=None):\n", "make_oracle def")
    if "--queue applies to O1, O15r and O15c" not in src:
        old = '    if rule in ("O15r", "O15a", "O15c") and engage is None:\n        raise ValueError(f"{rule} needs an engagement threshold (--engage)")\n'
        new = ('    if rule in ("O15r", "O15a", "O15c", "O15h") and engage is None:\n        raise ValueError(f"{rule} needs an engagement threshold (--engage)")\n'
               '    if queue is not None:\n'
               '        if queue not in ("first", "last"):\n'
               '            raise ValueError(f"queue must be first or last, not {queue}")\n'
               '        if rule not in ("O1", "O15r", "O15c") or defender is not None or not wait_busy:\n'
               '            raise ValueError("--queue applies to O1, O15r and O15c on a learned policy, with --wait-busy")\n')
        src = rep(src, old, new, "engage check")
    if "_queued = {}" not in src:
        old = ('    _tick = {}; _last = {}\n    def intercept(agent_name, act):\n        stats["calls"] += 1\n'
               '        if wait_busy and _busy(agent_name):\n            stats["busy"] = stats.get("busy", 0) + 1\n'
               '            _tick[agent_name] = _tick.get(agent_name, 0) + 1\n            if defender is not None:\n'
               '                defender.observe(agent_name)\n                return Sleep()\n            return act\n'
               '        if defender is not None:\n            act = defender(agent_name, act)      # the rule defender\'s proposal replaces the policy\'s\n'
               '        _tick[agent_name] = _tick.get(agent_name, 0) + 1\n        res = _decide(agent_name, act)\n        if res is not act:\n')
        src = rep(src, old, QUEUE_INTERCEPT, "intercept head")
    # ---- O15h
    if 'elif rule in ("O15a", "O15h"):' not in src:
        src = rep(src, '        if rule in ("O15r", "O15a", "O15c"):\n            # the engagement gate',
                  '        if rule in ("O15r", "O15a", "O15c", "O15h"):\n            # the engagement gate', "O15 block head")
        src = rep(src, '            elif rule == "O15a":                # alerts on owned hosts over the trailing window\n',
                  '            elif rule in ("O15a", "O15h"):      # alerts on owned hosts over the trailing window\n', "O15a branch")
        src = rep(src, "                    al.append(now)\n", "                    al.append((now, h))\n", "alert append")
        src = rep(src, "                while al and al[0] <= now - window:\n", "                while al and al[0][0] <= now - window:\n", "alert prune")
        src = rep(src, '            if not comp:\n                return act\n            stats["engaged_hit"] = stats.get("engaged_hit", 0) + 1\n',
                  O15H_BLOCK + '            if not comp:\n                return act\n            stats["engaged_hit"] = stats.get("engaged_hit", 0) + 1\n', "O15 firing")
    # ---- O16
    if 'if rule == "O16":' not in src:
        src = rep(src, 'if rule in ("O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O10", "O12", "O13"):',
                  'if rule in ("O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O10", "O12", "O13", "O16"):', "evidence branch")
        src = rep(src, '                    if rule in ("O2f", "O2fr", "O2fw"):\n',
                  '                    if rule in ("O2f", "O2fr", "O2fw", "O16"):\n', "O2f exclusion")
        src = rep(src, '            if rule == "O13":\n', O16_BLOCK + '            if rule == "O13":\n', "O13 branch")
    return src


def patch_oracle(src):
    if "engage=None, window=16, queue=None):\n    \"\"\"Wrap action_translator" not in src:
        src = rep(src, "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False, engage=None, window=16):\n",
                  "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False, engage=None, window=16, queue=None):\n", "install_oracle def")
        src = rep(src, "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window)\n",
                  "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue)\n", "install_oracle body")
    if "wait_busy=False, engage=None, window=16, queue=None):\n    seed" not in src:
        src = rep(src, 'min_gap=0, workers=0, wait_busy=False, engage=None, window=16):\n',
                  'min_gap=0, workers=0, wait_busy=False, engage=None, window=16, queue=None):\n', "capture_episode def")
        src = rep(src, "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window)\n",
                  "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue)\n", "install_oracle call")
    if '"queue": queue' not in src:
        src = rep(src, '"engage": engage, "window": window, "cyborg_version": CYBORG_VERSION,',
                  '"engage": engage, "window": window, "queue": queue, "cyborg_version": CYBORG_VERSION,', "header")
    if '"queue_stale": stats.get("queue_stale", 0)' not in src:
        old = '            "signal_ticks": stats.get("signal_ticks", 0), "alerts": stats.get("alerts", 0),\n'
        src = rep(src, old, old + ('            "queued": stats.get("queued", 0), "queue_fired": stats.get("queue_fired", 0),\n'
                                   '            "queue_stale": stats.get("queue_stale", 0), "queue_wait": stats.get("queue_wait", 0),\n'
                                   '            "o16_confirmed": stats.get("o16_confirmed", 0), "o15h_clean": stats.get("o15h_clean", 0),\n'), "footer")
    if 'p.add_argument("--queue"' not in src:
        old = '    p.add_argument("--window", type=int, default=16, help="O15r and O15a trailing window in simulator steps")\n'
        src = rep(src, old, old + '    p.add_argument("--queue", choices=["first", "last"], default=None, help="with --wait-busy: decide on a busy tick and hold the directive for the free tick (first: keep the first decision; last: replace it each busy tick)")\n', "--window arg")
        src = rep(src, "a.min_gap, a.workers, a.wait_busy, a.engage, a.window)", "a.min_gap, a.workers, a.wait_busy, a.engage, a.window, a.queue)", "Parallel call")
    return src


def patch_hm(src):
    if '"O15c", "O15h", "O16"]' not in src:
        src = rep(src, '"O14", "O15r", "O15a", "O15c"]', '"O14", "O15r", "O15a", "O15c", "O15h", "O16"]', "RULES")
    if 'hdr.get("window", 16), hdr.get("queue"))' not in src:
        src = rep(src, 'hdr.get("wait_busy", False), hdr.get("engage"), hdr.get("window", 16))\n',
                  'hdr.get("wait_busy", False), hdr.get("engage"), hdr.get("window", 16), hdr.get("queue"))\n', "make_oracle call")
    if '"window": a["window"], "queue": a["queue"]}' not in src:
        src = rep(src, '"workers": a["workers"], "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"]}\n',
                  '"workers": a["workers"], "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"], "queue": a["queue"]}\n', "episode hdr")
        src = rep(src, '"workers": 0, "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"]}\n',
                  '"workers": 0, "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"], "queue": a["queue"]}\n', "compat hdr")
    if 'ap.add_argument("--queue"' not in src:
        old = '    ap.add_argument("--window", type=int, default=16, help="O15r and O15a trailing window in simulator steps")\n'
        src = rep(src, old, old + '    ap.add_argument("--queue", choices=["first", "last"], default=None, help="with --wait-busy: decide on a busy tick and hold the directive for the free tick")\n', "--window arg")
    return src


if __name__ == "__main__":
    edit(RULES, patch_rules)
    edit(ORC, patch_oracle)
    edit(HM, patch_hm)
    print("done")
