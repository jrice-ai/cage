#!/usr/bin/env python3
"""A person's eyes and hands, R2's triage as a supervisor, the policy's own suspicion, and agent
subsets. Each part is idempotent and every existing path is unchanged, so the O2e smoke and the
H-MARL compat gate must reproduce. Run from ~/cage after tools_add_queue.py.

Eyes (--recall R --false-alarm F; O1 on a learned policy). O1 through a detector: each compromise
is shown for its whole life with probability R, drawn when the supervisor first looks at it, and a
clean owned host raises a false alarm that shows for 16 steps, at the onset rate that keeps a share
F of clean hosts flagged. The supervisor picks one flagged host at random. With either flag given
the pick is random even at R 1, F 0, so that arm is the surface's own zero. Footer eyes_tp, eyes_fp,
eyes_fn, eyes_clean (agent-ticks), from which the realized recall and false-alarm rate are read.

Hands (--delay D --wrong W --skip S; need --queue first, so O1, O15r or O15c). A person at the
prompt: with probability S they let it pass and the next prompt comes a gap later; otherwise they
click, on another owned host with probability W, and the click lands D steps later, held for the
agent if it is busy then. At D 0, W 0, S 0 this is --queue first exactly. Footer h_skip, h_wrong.

O16t, R2's triage as a supervisor: R2's eyes (alerts per owned host since its last restore, the
reset listing and the echo of the agent's own action excluded; a confirmed file) and R2's choice
(restore on a second alert or a confirmed file, else look at a host alerted once), offered at the
gate. No ground truth in the decision. Footer sup_tp, sup_fp, sup_fn, sup_own: R2's restore
candidates against the truth, for its place on the eyes surface.

O17 (KEEP only, --engage T): the policy's own suspicion. Each owned host is scored by the
probability KEEP's actor puts on Remove or Restore of it; at the gate the top host is restored if
its score is at least T. With --engage 1e9 it never acts and the step records carry, per free
agent-tick, [top score, top host compromised, best score on a compromised host, best on a clean
host, compromised hosts]: a survey of whether the policy half-knows. Footer o17_clean.

--agents 0,4: the supervisor acts for these agents only; the others run as the policy alone.

Also: exec_clean in every footer (restores handed to a free agent on a host that was clean), and
CAGE_EPISODE_LENGTH in the environment overrides the 500-step episode (for short-episode arms;
unset, nothing changes).
"""
import hashlib

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


SETUP = '''    if rule in ("O16t", "O17") and defender is not None:
        raise ValueError(f"{rule} supervises a learned policy")
    # a person's eyes and hands (tools_add_person.py): all off unless asked for
    noise = dict(noise or {})
    eyes = noise.get("recall") is not None or noise.get("false") is not None
    hands = any(noise.get(k) is not None for k in ("delay", "wrong", "skip"))
    r_ = 1.0 if noise.get("recall") is None else float(noise["recall"])
    f_ = 0.0 if noise.get("false") is None else float(noise["false"])
    d_ = int(noise.get("delay") or 0)
    w_ = float(noise.get("wrong") or 0.0)
    s_ = float(noise.get("skip") or 0.0)
    if eyes and (rule != "O1" or defender is not None):
        raise ValueError("--recall and --false-alarm apply to O1 on a learned policy")
    if eyes and not (0.0 <= r_ <= 1.0 and 0.0 <= f_ < 1.0):
        raise ValueError("recall in [0, 1], false-alarm rate in [0, 1)")
    if hands and queue != "first":
        raise ValueError("--delay, --wrong and --skip need --queue first: a person's click is held for the agent")
    if hands and not (d_ >= 0 and 0.0 <= w_ <= 1.0 and 0.0 <= s_ < 1.0):
        raise ValueError("delay >= 0, wrong in [0, 1], skip in [0, 1)")
    only = None
    if agents is not None:
        if defender is not None:
            raise ValueError("--agents applies to a supervisor on a learned policy")
        only = {a if str(a).startswith("blue_agent_") else f"blue_agent_{int(a)}" for a in agents}
    rng = random.Random(noise_seed)          # private: the environment's and the policy's draws are untouched
    FA_DWELL = 16                            # a false alarm shows for this many steps once raised
    p_fa = f_ / (FA_DWELL * (1.0 - f_)) if f_ else 0.0   # onset rate per step for a stationary share f flagged
    _inst = {}; _fa = {}; _seen_at = {}
    sup_stats = {}
    sup = make_defender(cyborg, "R2", sup_stats, decoys) if rule == "O16t" else None

    def _see(agent_name, comp):
        """O1's view through a detector: a compromise is shown for its whole life with probability
        recall, drawn when first looked at; a clean host raises a false alarm that shows for FA_DWELL
        steps; the person picks one flagged host at random. Returns the pick as O1's list, or []."""
        now = int(getattr(cyborg.environment_controller, "step_count", 0) or 0)
        k = max(1, now - _seen_at.get(agent_name, now - 1)); _seen_at[agent_name] = now
        p_on = 1.0 - (1.0 - p_fa) ** k if p_fa else 0.0     # onsets over the steps since the last look
        cs = {c[0] for c in comp}
        inst = _inst.setdefault(agent_name, {}); fa = _fa.setdefault(agent_name, {})
        for h in list(inst):
            if h not in cs:
                del inst[h]                  # that compromise has ended; a new one draws afresh
        own = owned_hosts(cyborg, agent_name); ownset = set(own)
        hosts = list(own) + sorted(h for h in cs if h not in ownset)
        seen = []
        for h in hosts:
            if h in cs:
                if h not in inst:
                    inst[h] = rng.random() < r_
                if inst[h]:
                    seen.append(h)
            elif fa.get(h, -1) >= now:
                seen.append(h)
            elif p_on and rng.random() < p_on:
                fa[h] = now + FA_DWELL - 1
                seen.append(h)
        tp = sum(1 for h in seen if h in cs)
        stats["eyes_tp"] = stats.get("eyes_tp", 0) + tp
        stats["eyes_fn"] = stats.get("eyes_fn", 0) + len(cs) - tp
        stats["eyes_fp"] = stats.get("eyes_fp", 0) + len(seen) - tp
        stats["eyes_clean"] = stats.get("eyes_clean", 0) + len(hosts) - len(cs)
        if not seen:
            return []
        tgt = rng.choice(sorted(seen))
        return [(tgt, subnet_of(tgt))]

'''

SUP_BLOCKS = '''        if rule == "O16t":
            # R2's triage as a supervisor: its eyes (alerts per owned host since its last restore, a
            # confirmed file) and its choice (restore on a second alert or a confirmed file, else look
            # at a host alerted once), offered at the gate; ground truth is read for bookkeeping only
            p = sup(agent_name, act)
            stats["sup_tp"] = sup_stats.get("d_tp", 0)
            stats["sup_fp"] = sup_stats.get("d_fp", 0)
            stats["sup_fn"] = sup_stats.get("d_fn", 0)
            stats["sup_own"] = stats.get("sup_own", 0) + len(owned_hosts(cyborg, agent_name))
            if min_gap and _tick.get(agent_name, 0) - _last.get(agent_name, -10**9) < min_gap:
                return act                    # the gate is shut: nothing proposed, nothing booked
            if type(p).__name__ not in ("Restore", "Analyse"):
                return act
            if type(act) is type(p) and getattr(act, "hostname", None) == getattr(p, "hostname", None):
                stats["agree"] += 1
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            stats["override"] += 1
            return p

        if rule == "O17":
            # the policy's own suspicion: each owned host scored by the probability the actor puts on
            # Remove or Restore of it; at the gate, restore the top host if its score is at least the
            # threshold. Ground truth is read for bookkeeping only
            pr = stats["probs"].get(agent_name) if isinstance(stats.get("probs"), dict) else None
            if pr is None or NODE_ACTIONS is None:
                return act
            ownset = set(owned_hosts(cyborg, agent_name))
            aid = int(agent_name[-1]); score = {}
            for s_i, sn in enumerate(MY_SUBNETS[aid]):
                for k in (1, 2):                      # NODE_ACTIONS: 1 = Remove, 2 = Restore
                    base = s_i * MAX_ACTIONS + k * MAX_HOSTS
                    for j in range(MAX_HOSTS):
                        h = f"{sn}_user_host_{j-6}" if j > 5 else f"{sn}_server_host_{j}"
                        if h in ownset:
                            score[h] = score.get(h, 0.0) + float(pr[base + j])
            if not score:
                return act
            top = max(sorted(score), key=lambda h: score[h])
            cs = {c[0] for c in comp}
            sig = score[top]
            stats["signal_sum"] = stats.get("signal_sum", 0.0) + sig
            stats["signal_ticks"] = stats.get("signal_ticks", 0) + 1
            stats.setdefault("sig", {})[agent_name] = [
                round(sig, 5), int(top in cs),
                round(max((score.get(h, 0.0) for h in cs), default=0.0), 5),
                round(max((v for h, v in score.items() if h not in cs), default=0.0), 5), len(cs)]
            if sig < engage:
                if comp:
                    stats["quiet_comp"] = stats.get("quiet_comp", 0) + 1
                return act
            stats["engaged"] = stats.get("engaged", 0) + 1
            if type(act).__name__ in ("Restore", "Remove") and getattr(act, "hostname", None) == top:
                stats["agree"] += 1
                return act
            if top in cs:
                stats["engaged_hit"] = stats.get("engaged_hit", 0) + 1
            else:
                stats["o17_clean"] = stats.get("o17_clean", 0) + 1
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=top)

'''

EYES = '''        if eyes:
            comp = _see(agent_name, comp)          # O1 through a detector (validated: O1 only)
'''

OLD_INTERCEPT_SHA = "cc8ae93249da60d4ec60196ab16e6fc567de125a59012e555f281fa9e7a2b3f8"

NEW_INTERCEPT = r'''    def _hands(agent_name, res):
        """a person's hands on a directive decided now: None when they let this prompt pass, else the
        directive as clicked, on another owned host with probability wrong"""
        if s_ and rng.random() < s_:
            stats["h_skip"] = stats.get("h_skip", 0) + 1
            return None
        h = getattr(res, "hostname", None)
        if w_ and h and rng.random() < w_:
            pool = [x for x in owned_hosts(cyborg, agent_name) if x != h]
            if pool:
                stats["h_wrong"] = stats.get("h_wrong", 0) + 1
                return type(res)(session=0, agent=agent_name, hostname=rng.choice(pool))
        return res

    def _ran(agent_name, res):
        # a directive handed to a free agent: count a restore on a clean host; clear a false alarm on it
        h = getattr(res, "hostname", None)
        if type(res).__name__ == "Restore" and h:
            if h not in {c[0] for c in compromised_by_agent(cyborg).get(agent_name, [])}:
                stats["exec_clean"] = stats.get("exec_clean", 0) + 1
            if eyes:
                _fa.get(agent_name, {}).pop(h, None)

    _tick = {}; _last = {}; _queued = {}; _due = {}
    def intercept(agent_name, act):
        stats["calls"] += 1
        if only is not None and agent_name not in only:
            return act                           # --agents: this agent runs as the policy alone
        if wait_busy and _busy(agent_name):
            stats["busy"] = stats.get("busy", 0) + 1
            _tick[agent_name] = _tick.get(agent_name, 0) + 1
            if defender is not None:
                defender.observe(agent_name)
                return Sleep()
            if sup is not None:
                sup.observe(agent_name)          # O16t: R2 keeps reading the stream while the agent is busy
            if queue and (queue == "last" or agent_name not in _queued) \
                    and not (min_gap and _tick[agent_name] - _last.get(agent_name, -10**9) < min_gap):
                # the supervisor decides on the busy tick, as a person clicking would, and the
                # directive is held for the agent's next free tick; it is booked when it fires
                q = _decide(agent_name, act)
                if q is not act:
                    stats["override"] -= 1
                    if hands:
                        q = _hands(agent_name, q)
                        if q is None:
                            _last[agent_name] = _tick[agent_name]   # the prompt passes; the next comes a gap later
                            return act
                    if agent_name not in _queued:
                        stats["queued"] = stats.get("queued", 0) + 1
                    _queued[agent_name] = (q, _fmt(act), _tick[agent_name])
                    _due[agent_name] = _tick[agent_name] + d_
                elif queue == "last":
                    _queued.pop(agent_name, None)  # the latest decision is to do nothing
            return act
        if defender is not None:
            act = defender(agent_name, act)      # the rule defender's proposal replaces the policy's
        _tick[agent_name] = _tick.get(agent_name, 0) + 1
        fired = False
        if queue and agent_name in _queued and _tick[agent_name] >= _due.get(agent_name, 0):
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
            _ran(agent_name, res)
            fired = True
        elif queue and agent_name in _queued:
            res = act                            # a click still on its way (--delay): the policy runs meanwhile
        else:
            res = _decide(agent_name, act)
        if res is not act and not fired:
            if min_gap and _tick[agent_name] - _last.get(agent_name, -10**9) < min_gap:
                stats["override"] -= 1
                stats["deferred"] = stats.get("deferred", 0) + 1
                res = act
            else:
                if hands:
                    stats["override"] -= 1       # booked again below if the click lands now
                    clicked = _hands(agent_name, res)
                    if clicked is None:
                        _last[agent_name] = _tick[agent_name]
                        res = act
                    elif d_ > 0:
                        stats["queued"] = stats.get("queued", 0) + 1
                        _queued[agent_name] = (clicked, _fmt(act), _tick[agent_name])
                        _due[agent_name] = _tick[agent_name] + d_
                        res = act
                    else:
                        stats["override"] += 1
                        res = clicked
                if res is not act:
                    _last[agent_name] = _tick[agent_name]
                    _k = "exec_" + type(res).__name__
                    stats[_k] = stats.get(_k, 0) + 1
                    stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
                    _ran(agent_name, res)
        if agent_name in flagged:                # O2f family: the executed action's host, for the echo test
            _h = getattr(res, "hostname", None)
            flagged[agent_name]["acted"] = (_h, flagged[agent_name]["t"]) if _h else None
        if defender is not None:
            defender.note(agent_name, res)       # whatever runs, the rule remembers it
        if sup is not None:
            sup.note(agent_name, res)            # O16t: whatever runs, R2's memory records it
        return res

'''


def patch_rules(src):
    if 'os.environ.get("CAGE_EPISODE_LENGTH"' not in src:
        src = rep(src, "EPISODE_LENGTH = 500\n",
                  'EPISODE_LENGTH = int(os.environ.get("CAGE_EPISODE_LENGTH", "500"))   # 500 unless a short-episode arm sets it\n',
                  "EPISODE_LENGTH")
    if '"O16", "O16t", "O17"}' not in src:
        src = rep(src, '"O15r", "O15a", "O15c", "O15h", "O16"}', '"O15r", "O15a", "O15c", "O15h", "O16", "O16t", "O17"}', "KNOWN_RULES")
    if "queue=None, noise=None, agents=None, noise_seed=0):" not in src:
        src = rep(src, "wait_busy=False, engage=None, window=16, queue=None):\n    \"\"\"Return intercept",
                  "wait_busy=False, engage=None, window=16, queue=None, noise=None, agents=None, noise_seed=0):\n    \"\"\"Return intercept",
                  "make_oracle def")
    if 'if rule in ("O15r", "O15a", "O15c", "O15h", "O17") and engage is None:' not in src:
        src = rep(src, 'if rule in ("O15r", "O15a", "O15c", "O15h") and engage is None:',
                  'if rule in ("O15r", "O15a", "O15c", "O15h", "O17") and engage is None:', "engage check")
    if "def _see(agent_name, comp):" not in src:
        anchor = '            raise ValueError("--queue applies to O1, O15r and O15c on a learned policy, with --wait-busy")\n'
        src = rep(src, anchor, anchor + SETUP, "queue validation")
    if 'if rule == "O16t":' not in src:
        anchor = '        comp = compromised_by_agent(cyborg).get(agent_name, [])\n\n'
        src = rep(src, anchor, anchor + SUP_BLOCKS, "comp line")
    if "comp = _see(agent_name, comp)" not in src:
        anchor = '        if rule == "O4":\n            comp = [c for c in comp if c[1] in EXPENSIVE]\n'
        src = rep(src, anchor, EYES + anchor, "O4 filter")
    if "_due = {}" not in src:
        i = src.index("    _tick = {}; _last = {}; _queued = {}\n")
        j = src.index("    return intercept\n")
        old = src[i:j]
        got = hashlib.sha256(old.encode()).hexdigest()
        assert got == OLD_INTERCEPT_SHA, f"intercept is not the one tools_add_queue.py left ({got[:12]}); stop and check"
        src = src[:i] + NEW_INTERCEPT + src[j:]
    return src


def patch_oracle(src):
    # repair of the first cut (2026-09-29): capture_episode's new parameter was named agents and was
    # shadowed by its local agents = Submission.AGENTS, so the header carried the five policy objects
    # (TypeError: not JSON serializable, before the first step) and install_oracle received them in
    # place of the list. The parameter is only_agents from here.
    if "window=16, queue=None, noise=None, agents=None):\n    seed" in src:
        src = rep(src, "window=16, queue=None, noise=None, agents=None):\n    seed",
                  "window=16, queue=None, noise=None, only_agents=None):\n    seed", "repair def")
        src = rep(src, "                   noise=noise, agents=agents, noise_seed=seed)\n",
                  "                   noise=noise, agents=only_agents, noise_seed=seed)\n", "repair call")
        src = rep(src, '"noise": noise, "agents": agents, "cyborg_version"',
                  '"noise": noise, "agents": only_agents, "cyborg_version"', "repair header")
    if "queue=None, noise=None, agents=None, noise_seed=0):\n    \"\"\"Wrap action_translator" not in src:
        src = rep(src, "engage=None, window=16, queue=None):\n    \"\"\"Wrap action_translator",
                  "engage=None, window=16, queue=None, noise=None, agents=None, noise_seed=0):\n    \"\"\"Wrap action_translator", "install_oracle def")
        src = rep(src, "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue)\n",
                  "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue,\n"
                  "                            noise=noise, agents=agents, noise_seed=noise_seed)\n", "install_oracle body")
    if "window=16, queue=None, noise=None, only_agents=None):\n    seed" not in src:
        src = rep(src, "wait_busy=False, engage=None, window=16, queue=None):\n    seed",
                  "wait_busy=False, engage=None, window=16, queue=None, noise=None, only_agents=None):\n    seed", "capture_episode def")
        src = rep(src, "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue)\n",
                  "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window, queue,\n"
                  "                   noise=noise, agents=only_agents, noise_seed=seed)\n", "install_oracle call")
    if 'if rule in ("O11", "O17"):' not in src:
        src = rep(src, '    if rule == "O11":\n        stats["probs"] = {}\n', '    if rule in ("O11", "O17"):\n        stats["probs"] = {}\n', "probs wrapper")
    if '"noise": noise, "agents": only_agents' not in src:
        src = rep(src, '"queue": queue, "cyborg_version": CYBORG_VERSION,', '"queue": queue, "noise": noise, "agents": only_agents, "cyborg_version": CYBORG_VERSION,', "header")
    if '"exec_clean": stats.get("exec_clean", 0)' not in src:
        old = '            "o16_confirmed": stats.get("o16_confirmed", 0), "o15h_clean": stats.get("o15h_clean", 0),\n'
        src = rep(src, old, old + (
            '            "exec_clean": stats.get("exec_clean", 0), "h_skip": stats.get("h_skip", 0), "h_wrong": stats.get("h_wrong", 0),\n'
            '            "eyes_tp": stats.get("eyes_tp", 0), "eyes_fp": stats.get("eyes_fp", 0), "eyes_fn": stats.get("eyes_fn", 0), "eyes_clean": stats.get("eyes_clean", 0),\n'
            '            "sup_tp": stats.get("sup_tp", 0), "sup_fp": stats.get("sup_fp", 0), "sup_fn": stats.get("sup_fn", 0), "sup_own": stats.get("sup_own", 0),\n'
            '            "o17_clean": stats.get("o17_clean", 0),\n'), "footer")
    if 'p.add_argument("--recall"' not in src:
        old = '    p.add_argument("--queue", choices=["first", "last"], default=None,'
        i = src.index(old); j = src.index("\n", i) + 1
        src = src[:j] + (
            '    p.add_argument("--recall", type=float, default=None, help="O1 through a detector: probability a compromise is ever shown (drawn per compromise)")\n'
            '    p.add_argument("--false-alarm", type=float, default=None, help="O1 through a detector: stationary share of clean owned hosts flagged")\n'
            '    p.add_argument("--delay", type=int, default=None, help="with --queue first: steps from a person\'s decision to the click landing")\n'
            '    p.add_argument("--wrong", type=float, default=None, help="with --queue first: probability the click lands on another owned host")\n'
            '    p.add_argument("--skip", type=float, default=None, help="with --queue first: probability a person lets a prompt pass")\n'
            '    p.add_argument("--agents", default=None, help="supervise only these agents, e.g. 0,4")\n') + src[j:]
        src = rep(src, "    a = p.parse_args()\n", "    a = p.parse_args()\n"
                  '    noise = {k: v for k, v in (("recall", a.recall), ("false", a.false_alarm), ("delay", a.delay),\n'
                  '                               ("wrong", a.wrong), ("skip", a.skip)) if v is not None} or None\n'
                  '    agents = [int(x) for x in a.agents.split(",")] if a.agents else None\n', "parse_args")
        src = rep(src, "a.min_gap, a.workers, a.wait_busy, a.engage, a.window, a.queue)", "a.min_gap, a.workers, a.wait_busy, a.engage, a.window, a.queue, noise, agents)", "Parallel call")
    return src


def patch_hm(src):
    if '"O15h", "O16", "O16t"]' not in src:
        src = rep(src, '"O15h", "O16"]', '"O15h", "O16", "O16t"]', "RULES")
    if 'noise=hdr.get("noise")' not in src:
        src = rep(src, 'hdr.get("window", 16), hdr.get("queue"))\n',
                  'hdr.get("window", 16), hdr.get("queue"),\n'
                  '                                      noise=hdr.get("noise"), agents=hdr.get("agents"), noise_seed=seed)\n', "make_oracle call")
    if '"noise": a["noise"], "agents": a["agents"]}' not in src:
        src = rep(src, '"workers": a["workers"], "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"], "queue": a["queue"]}\n',
                  '"workers": a["workers"], "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"], "queue": a["queue"],\n'
                  '           "noise": a["noise"], "agents": a["agents"]}\n', "episode hdr")
        src = rep(src, '"workers": 0, "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"], "queue": a["queue"]}\n',
                  '"workers": 0, "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"], "queue": a["queue"],\n'
                  '               "noise": a["noise"], "agents": a["agents"]}\n', "compat hdr")
    if 'ap.add_argument("--recall"' not in src:
        old = '    ap.add_argument("--queue", choices=["first", "last"], default=None,'
        i = src.index(old); j = src.index("\n", i) + 1
        src = src[:j] + (
            '    ap.add_argument("--recall", type=float, default=None, help="O1 through a detector (see oracle.py)")\n'
            '    ap.add_argument("--false-alarm", type=float, default=None, help="O1 through a detector (see oracle.py)")\n'
            '    ap.add_argument("--delay", type=int, default=None, help="with --queue first: a person\'s delay in steps")\n'
            '    ap.add_argument("--wrong", type=float, default=None, help="with --queue first: probability of the wrong host")\n'
            '    ap.add_argument("--skip", type=float, default=None, help="with --queue first: probability a prompt passes")\n'
            '    ap.add_argument("--agents", default=None, help="supervise only these agents, e.g. 0,4")\n') + src[j:]
        src = rep(src, "    a = vars(ap.parse_args())\n", "    a = vars(ap.parse_args())\n"
                  '    a["noise"] = {k: a[j] for k, j in (("recall", "recall"), ("false", "false_alarm"), ("delay", "delay"),\n'
                  '                                        ("wrong", "wrong"), ("skip", "skip")) if a[j] is not None} or None\n'
                  '    a["agents"] = [int(x) for x in a["agents"].split(",")] if a["agents"] else None\n', "parse_args")
    return src


if __name__ == "__main__":
    edit(RULES, patch_rules)
    edit(ORC, patch_oracle)
    edit(HM, patch_hm)
    print("done")
