#!/usr/bin/env python3
"""O15, the engagement gate: a supervisor with perfect eyes who acts only when a signal they could
watch crosses a threshold.

O1 answers "what should the supervisor do" (Restore a compromised owned host) at a fixed cadence
(the gap floor). O15 separates "when should the supervisor engage" from that: on every free tick
the rule computes a signal a human could see on a dashboard, and only when the signal is at or
above the threshold does it issue O1's Restore (waiting for a free agent under --wait-busy,
spaced by --min-gap as O1 is). Below the threshold the policy's action passes through and the gap
clock keeps running. Three signals:

  O15r  loss over the trailing --window simulator steps (team reward, sign flipped), the score
        trace a supervisor watches; the same for every agent
  O15a  alerts on the agent's own hosts over the trailing --window steps: substantive observation
        entries naming an owned host, excluding the reset listing and the echo of the agent's own
        last action (O2f's rule), the alert feed a supervisor watches; per agent
  O15c  ground-truth compromised hosts in the agent's zones, a count a perfect status board
        would show; per agent. O15c at --engage 1 is O1 at the same gap.

Bookkeeping in the footer: engaged (agent-ticks at or above the threshold), engaged_hit (of those,
with a compromised owned host, so an override was proposed), quiet_comp (agent-ticks below the
threshold while a compromised owned host existed, the gate's misses), signal_sum and signal_ticks
(mean signal per agent-tick), alerts (O15a's count). The step record carries "signal": per agent
[signal, compromised owned hosts] for O15 rules only, for threshold calibration (tools_signal.py).
Header fields engage and window. The harness appends each step's team reward to stats["rew_hist"]
for O15r; nothing else reads it.

Applies to scripts/oracle_rules.py, scripts/oracle.py, scripts/capture_hmarl.py. Idempotent, tests
for the code it inserts. Without --engage no O15 rule can be selected and every other path is
unchanged, so the O2e smoke and the H-MARL compat gate must reproduce. Run from ~/cage after
tools_add_wait.py.
"""
RULES = "scripts/oracle_rules.py"
ORC = "scripts/oracle.py"
HM = "scripts/capture_hmarl.py"

O15 = ("O15r", "O15a", "O15c")


def edit(path, fn):
    src = open(path).read()
    new = fn(src)
    if new != src:
        open(path, "w").write(new); print("patched", path)
    else:
        print("already patched", path)


BLOCK = '''        if rule in ("O15r", "O15a", "O15c"):
            # the engagement gate: act (as O1 would) only when a signal a supervisor could watch is
            # at or above the threshold; the gap floor is intercept's, the wait is the flag's
            now = int(getattr(cyborg.environment_controller, "step_count", 0) or 0)
            if rule == "O15r":                  # loss over the trailing window, team-wide
                hist = stats.get("rew_hist") or []
                sig = -sum(hist[-window:])
            elif rule == "O15a":                # alerts on owned hosts over the trailing window
                obs = cyborg.get_observation(agent_name) or {}
                st = flagged.setdefault(agent_name, {"t": 0, "h": {}})
                st["t"] += 1
                t = st["t"]
                own = set(owned_hosts(cyborg, agent_name))
                al = st.setdefault("al", [])
                for h, v in obs.items():
                    if h in META or not isinstance(v, dict) or h not in own:
                        continue
                    _fl = v.get("Files") or []
                    _conf = any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in _fl)
                    if not _conf and (t == 1 or st.get("acted") == (h, t - 1)):
                        continue           # the reset listing, or the echo of this agent's own action
                    al.append(now)
                    stats["alerts"] = stats.get("alerts", 0) + 1
                while al and al[0] <= now - window:
                    al.pop(0)
                sig = len(al)
            else:                               # compromised owned hosts, ground truth
                sig = len(comp)
            stats["signal_sum"] = stats.get("signal_sum", 0.0) + sig
            stats["signal_ticks"] = stats.get("signal_ticks", 0) + 1
            stats.setdefault("sig", {})[agent_name] = [sig, len(comp)]
            if sig < engage:
                if comp:
                    stats["quiet_comp"] = stats.get("quiet_comp", 0) + 1
                return act
            stats["engaged"] = stats.get("engaged", 0) + 1
            if not comp:
                return act
            stats["engaged_hit"] = stats.get("engaged_hit", 0) + 1
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=comp[0][0])

'''


def patch_rules(src):
    if '"O15r", "O15a", "O15c"}' not in src:
        old = '"O2f", "O2fr", "O2fw"}'
        assert src.count(old) == 1, "KNOWN_RULES tail not found"
        src = src.replace(old, '"O2f", "O2fr", "O2fw", "O15r", "O15a", "O15c"}')
    if "wait_busy=False, engage=None, window=16):" not in src:
        old = "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False):\n"
        assert src.count(old) == 1, "make_oracle def not found"
        src = src.replace(old, "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False, engage=None, window=16):\n")
    if "needs an engagement threshold" not in src:
        old = '    if rule not in KNOWN_RULES:\n        raise ValueError(f"unknown rule {rule}")\n'
        assert src.count(old) == 1, "rule check not found"
        src = src.replace(old, old + '    if rule in ("O15r", "O15a", "O15c") and engage is None:\n        raise ValueError(f"{rule} needs an engagement threshold (--engage)")\n')
    if 'if rule in ("O15r", "O15a", "O15c"):\n            # the engagement gate' not in src:
        old = '        if rule == "O8":\n'
        assert src.count(old) == 1, "O8 branch not found"
        src = src.replace(old, BLOCK + old)
    return src


def patch_oracle(src):
    if "min_gap=0, wait_busy=False, engage=None, window=16):\n    \"\"\"Wrap action_translator" not in src:
        old = "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False):\n"
        assert src.count(old) == 1, "install_oracle def not found"
        src = src.replace(old, "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False, engage=None, window=16):\n")
        old = "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy)\n"
        assert src.count(old) == 1, "install_oracle body not found"
        src = src.replace(old, "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window)\n")
    if "workers=0, wait_busy=False, engage=None, window=16):" not in src:
        old = 'red_agent="FiniteStateRedAgent", min_gap=0, workers=0, wait_busy=False):\n'
        assert src.count(old) == 1, "capture_episode def not found"
        src = src.replace(old, 'red_agent="FiniteStateRedAgent", min_gap=0, workers=0, wait_busy=False, engage=None, window=16):\n')
        old = "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy)\n"
        assert src.count(old) == 1, "install_oracle call not found"
        src = src.replace(old, "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy, engage, window)\n")
    if '"engage": engage, "window": window' not in src:
        old = '"wait_busy": wait_busy, "cyborg_version": CYBORG_VERSION,'
        assert src.count(old) == 1, "header line not found"
        src = src.replace(old, '"wait_busy": wait_busy, "engage": engage, "window": window, "cyborg_version": CYBORG_VERSION,')
    if 'stats.setdefault("rew_hist", []).append(step_reward)' not in src:
        old = '            step_reward = float(rew["blue_agent_0"])\n            total += step_reward\n'
        assert src.count(old) == 1, "step reward lines not found"
        src = src.replace(old, old + '            stats.setdefault("rew_hist", []).append(step_reward)   # O15r reads the trailing window\n')
    if '**({"signal": stats.pop("sig")} if "sig" in stats else {}),' not in src:
        old = '                "defender": stats.get("dact") or [],\n'
        assert src.count(old) == 1, "step record defender line not found"
        src = src.replace(old, old + '                **({"signal": stats.pop("sig")} if "sig" in stats else {}),\n')
    if '"engaged": stats.get("engaged", 0)' not in src:
        old = '            "busy_skips": stats.get("busy", 0),\n'
        assert src.count(old) == 1, "footer busy_skips line not found"
        src = src.replace(old, old + '            "engaged": stats.get("engaged", 0), "engaged_hit": stats.get("engaged_hit", 0),\n'
                               '            "quiet_comp": stats.get("quiet_comp", 0), "signal_sum": stats.get("signal_sum", 0.0),\n'
                               '            "signal_ticks": stats.get("signal_ticks", 0), "alerts": stats.get("alerts", 0),\n')
    if 'p.add_argument("--engage", type=float, default=None' not in src:
        old = '    p.add_argument("--wait-busy", action="store_true"'
        assert src.count(old) == 1, "--wait-busy argument not found"
        i = src.index(old); j = src.index("\n", i) + 1
        src = src[:j] + ('    p.add_argument("--engage", type=float, default=None, help="O15 threshold: O15r loss over the window, O15a alerts over the window, O15c compromised owned hosts")\n'
                         '    p.add_argument("--window", type=int, default=16, help="O15r and O15a trailing window in simulator steps")\n') + src[j:]
        old = "a.min_gap, a.workers, a.wait_busy)"
        assert src.count(old) == 1, "Parallel call not found"
        src = src.replace(old, "a.min_gap, a.workers, a.wait_busy, a.engage, a.window)")
    return src


def patch_hm(src):
    if '"O14", "O15r", "O15a", "O15c"]' not in src:
        old = '"O13", "O14"]'
        assert src.count(old) == 1, "RULES tail not found"
        src = src.replace(old, '"O13", "O14", "O15r", "O15a", "O15c"]')
    if 'hdr.get("wait_busy", False), hdr.get("engage"), hdr.get("window", 16))' not in src:
        old = 'stats, budget, {}, min_gap, hdr.get("wait_busy", False))\n'
        assert src.count(old) == 1, "make_oracle call not found"
        src = src.replace(old, 'stats, budget, {}, min_gap, hdr.get("wait_busy", False), hdr.get("engage"), hdr.get("window", 16))\n')
    if 'stats.setdefault("rew_hist", []).append(r)' not in src:
        old = '            r = float(np.mean([v for k, v in rew.items() if "master" not in k]))\n            total += r\n'
        assert src.count(old) == 1, "step reward lines not found"
        src = src.replace(old, old + '            stats.setdefault("rew_hist", []).append(r)     # O15r reads the trailing window\n')
    if '**({"signal": stats.pop("sig")} if "sig" in stats else {}),' not in src:
        old = '                "reward": r, "cum_reward": total, "overrides": stats.get("ovr", [])[n0:],\n'
        assert src.count(old) == 1, "step record line not found"
        src = src.replace(old, old + '                **({"signal": stats.pop("sig")} if "sig" in stats else {}),\n')
    if '"wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"]}' not in src:
        old = '           "workers": a["workers"], "wait_busy": a["wait_busy"]}\n'
        assert src.count(old) == 1, "episode hdr not found"
        src = src.replace(old, '           "workers": a["workers"], "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"]}\n')
        old = '"workers": 0, "wait_busy": a["wait_busy"]}\n'
        assert src.count(old) == 1, "compat hdr not found"
        src = src.replace(old, '"workers": 0, "wait_busy": a["wait_busy"], "engage": a["engage"], "window": a["window"]}\n')
    if 'ap.add_argument("--engage", type=float, default=None' not in src:
        old = '    ap.add_argument("--wait-busy", action="store_true"'
        assert src.count(old) == 1, "--wait-busy not found"
        i = src.index(old); j = src.index("\n", i) + 1
        src = src[:j] + ('    ap.add_argument("--engage", type=float, default=None, help="O15 threshold (see oracle_rules)")\n'
                         '    ap.add_argument("--window", type=int, default=16, help="O15r and O15a trailing window in simulator steps")\n') + src[j:]
    return src


if __name__ == "__main__":
    edit(RULES, patch_rules)
    edit(ORC, patch_oracle)
    edit(HM, patch_hm)
    print("done")
