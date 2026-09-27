#!/usr/bin/env python3
"""Directives wait for a free agent (--wait-busy), and the rule parser accepts any defender+rule.

CC4 actions have durations (Restore 5, Remove 3, Analyse 2, DeployDecoy 2) and the controller
drops any action handed to an agent that is mid-action (SimulationController: actions_in_progress
is set only when empty; the agent executes Sleep for the remaining ticks). Every supervisor
override in the study so far was attempted at its tick whether or not the agent was busy, so 35
to 60 percent of them never ran (tools_dropped.py), and the rule defenders booked proposals that
were never executed.

With --wait-busy (header field wait_busy, footer busy_skips):
  * the supervisor rule is not consulted on a tick where the agent is mid-action; the policy's
    action passes through (it is dropped by the controller anyway) and the gap clock keeps
    running, so an override due on a busy tick fires at the agent's next free tick;
  * a rule defender proposes Sleep on a busy tick and books nothing; its own clock (windows,
    echo test) advances only on free ticks, which also makes the echo exclusion hold for
    multi-tick actions (the result of a Restore arrives at the completion tick, which is the
    rule's next tick);
  * evidence rules (O2f family, O10, O12, O13) likewise read the observation only on free ticks,
    where the results of their own looks arrive.
Without the flag every path is unchanged, so the O2e smoke and the compat gate must reproduce.

Also: oracle.py's --rule accepts any KNOWN rule, any DEFENDER, or DEFENDER+RULE, instead of a
hand-written list (R2d+O1 was missing from it on 2026-09-26).

Idempotent, tests for the code it inserts. Run from ~/cage after tools_add_R4tn.py.
"""
import re

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


def patch_rules(src):
    # 1. make_oracle signature
    if "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False):" not in src:
        old = "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0):\n"
        assert src.count(old) == 1, "make_oracle def not found"
        src = src.replace(old, "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False):\n")
    # 2. defender observe: on a busy tick the rule still reads the observation and advances its
    #    clock, but proposes nothing; the echo of its own action is the host of its last executed
    #    action, cleared when it next acts, so a multi-tick action's result is excluded too
    if "propose.observe = observe" not in src:
        old = "    propose.note = note\n    return propose\n"
        assert src.count(old) == 1, "propose.note not found"
        src = src.replace(old, "    def observe(agent_name):\n        st = _st(agent_name); st[\"t\"] += 1\n        _latch(agent_name, st)\n\n    propose.note = note\n    propose.observe = observe\n    return propose\n")
    if 'if h == st.get("echo") and not confirmed:' not in src:
        old = '            if st["acted"].get(h) == t - 1 and not confirmed:   # echo of our own action\n'
        assert src.count(old) == 1, "echo test not found"
        src = src.replace(old, '            if h == st.get("echo") and not confirmed:              # the result of our own last action on this host\n')
        old = '        if h:\n            st["acted"][h] = t\n'
        assert src.count(old) == 1, "note acted line not found"
        src = src.replace(old, '        if h:\n            st["acted"][h] = t\n        st["echo"] = h if h else None\n')
    # 3. busy test and the skip in intercept
    if "def _busy(agent_name):" not in src:
        old = "    _tick = {}; _last = {}\n    def intercept(agent_name, act):\n        stats[\"calls\"] += 1\n"
        assert src.count(old) == 1, "intercept head not found"
        src = src.replace(old, '''    def _busy(agent_name):
        # the controller's own test: an action handed to an agent whose previous action still has
        # ticks remaining is dropped
        try:
            return cyborg.environment_controller.actions_in_progress.get(agent_name) is not None
        except AttributeError:
            return False

    _tick = {}; _last = {}
    def intercept(agent_name, act):
        stats["calls"] += 1
        if wait_busy and _busy(agent_name):
            stats["busy"] = stats.get("busy", 0) + 1
            _tick[agent_name] = _tick.get(agent_name, 0) + 1
            if defender is not None:
                defender.observe(agent_name)
                return Sleep()
            return act
''')
    return src


def patch_oracle(src):
    if "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False):" not in src:
        old = "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0):\n"
        assert src.count(old) == 1, "install_oracle def not found"
        src = src.replace(old, "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0, wait_busy=False):\n")
        old = "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap)\n"
        assert src.count(old) == 1, "install_oracle body not found"
        src = src.replace(old, "    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap, wait_busy)\n")
    if "min_gap=0, workers=0, wait_busy=False):" not in src:
        old = 'def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent", min_gap=0, workers=0):\n'
        assert src.count(old) == 1, "capture_episode def not found"
        src = src.replace(old, 'def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent", min_gap=0, workers=0, wait_busy=False):\n')
        old = "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap)\n"
        assert src.count(old) == 1, "install_oracle call not found"
        src = src.replace(old, "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap, wait_busy)\n")
    if '"wait_busy": wait_busy' not in src:
        old = '"rule": rule, "budget": budget, "min_gap": min_gap, "workers": workers, "cyborg_version": CYBORG_VERSION,'
        assert src.count(old) == 1, "header line not found"
        src = src.replace(old, '"rule": rule, "budget": budget, "min_gap": min_gap, "workers": workers, "wait_busy": wait_busy, "cyborg_version": CYBORG_VERSION,')
    if '"busy_skips": stats.get("busy", 0)' not in src:
        old = '            "deferred": stats.get("deferred", 0),\n'
        assert src.count(old) == 1, "footer deferred line not found"
        src = src.replace(old, old + '            "busy_skips": stats.get("busy", 0),\n')
    if 'p.add_argument("--wait-busy", action="store_true"' not in src:
        old = '    p.add_argument("--min-gap", type=int, default=0, help="per-agent minimum steps between overrides")\n'
        assert src.count(old) == 1, "--min-gap argument not found"
        src = src.replace(old, old + '    p.add_argument("--wait-busy", action="store_true", help="a directive to a busy agent waits for its next free tick instead of being dropped by the simulator; rule defenders sleep while busy")\n')
        old = "delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red, a.min_gap, a.workers)"
        assert src.count(old) == 1, "Parallel call not found"
        src = src.replace(old, "delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red, a.min_gap, a.workers, a.wait_busy)")
    if "def _rule_arg(s):" not in src:
        pat = re.compile(r'    p\.add_argument\("--rule", default="O1",\n\s+choices=\[.*?\],\n\s+help="[^"]*"\)\n', re.S)
        m = pat.search(src)
        assert m, "--rule choices block not found"
        src = src[:m.start()] + ('    p.add_argument("--rule", default="O1", type=_rule_arg,\n'
                                 '                   help="a supervisor rule on KEEP, or a rule defender (R1 to R4, RT), optionally with a supervisor rule on top (R4+O1)")\n') + src[m.end():]
        old = "def main():\n    p = argparse.ArgumentParser(\"Oracle arms\")\n"
        assert src.count(old) == 1, "main head not found"
        src = src.replace(old, '''def _rule_arg(s):
    from oracle_rules import KNOWN_RULES, DEFENDERS
    d, _, r = s.partition("+")
    if s in KNOWN_RULES or (d in DEFENDERS and (r == "" or r in KNOWN_RULES)):
        return s
    raise argparse.ArgumentTypeError(f"unknown rule {s}")


''' + old)
    return src


def patch_hm(src):
    if "stats, budget, {}, min_gap, hdr.get(\"wait_busy\", False))" not in src:
        old = '    holder["intercept"] = make_oracle(cyborg, "none" if rule == "O14" else rule,\n                                      stats, budget, {}, min_gap)\n'
        assert src.count(old) == 1, "make_oracle call not found"
        src = src.replace(old, '    holder["intercept"] = make_oracle(cyborg, "none" if rule == "O14" else rule,\n                                      stats, budget, {}, min_gap, hdr.get("wait_busy", False))\n')
    if '"busy_skips": stats.get("busy", 0)' not in src:
        old = '"translator_calls": stats["calls"], "deferred": stats["deferred"],'
        assert src.count(old) == 1, "footer line not found"
        src = src.replace(old, '"translator_calls": stats["calls"], "deferred": stats["deferred"], "busy_skips": stats.get("busy", 0),')
    if '"wait_busy": a["wait_busy"]' not in src:
        old = '    hdr = {"red_agent": a["red"], "seed_mode": "episode", "policy_seed": pseed,\n           "workers": a["workers"]}\n'
        assert src.count(old) == 1, "episode hdr not found"
        src = src.replace(old, '    hdr = {"red_agent": a["red"], "seed_mode": "episode", "policy_seed": pseed,\n           "workers": a["workers"], "wait_busy": a["wait_busy"]}\n')
        old = '        hdr = {"red_agent": a["red"], "seed_mode": "compat", "policy_seed": s, "workers": 0}\n'
        assert src.count(old) == 1, "compat hdr not found"
        src = src.replace(old, '        hdr = {"red_agent": a["red"], "seed_mode": "compat", "policy_seed": s, "workers": 0, "wait_busy": a["wait_busy"]}\n')
    if 'ap.add_argument("--wait-busy", action="store_true"' not in src:
        old = '    ap.add_argument("--min-gap", type=int, default=0)\n'
        assert src.count(old) == 1, "--min-gap not found"
        src = src.replace(old, old + '    ap.add_argument("--wait-busy", action="store_true", help="a directive to a busy agent waits for its next free tick")\n')
    return src


if __name__ == "__main__":
    edit(RULES, patch_rules)
    edit(ORC, patch_oracle)
    edit(HM, patch_hm)
    print("done")
