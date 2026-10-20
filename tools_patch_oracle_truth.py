#!/usr/bin/env python3
"""scripts/oracle.py gains --log-truth. Run from ~/cage. Requires the v2 busy patch (--log-policy) first.

  --log-truth   each step record gains "truth": {"red_hosts": {hostname: {red agent: sessions}}}, the hosts
                holding a red session in the post-step state, built exactly as scripts/capture.py builds it
                (red_presence), so a rule arm can be scored by ~/papers/recompute_criteria.py on the same
                basis as the policy arms. The header records "log_truth".

Exact strings with count checks, all or nothing, idempotent."""
import hashlib, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
ORC = os.path.join(ROOT, "scripts/oracle.py")
MARK = "--log-truth"


def sub(src, old, new, what):
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected 1 match, found {n}")
    return src.replace(old, new)


def patch(src):
    src = sub(src, "import wrapper.graph_wrapper as _gw\n", '''import wrapper.graph_wrapper as _gw


def _red_presence(state):
    """Which hosts hold red sessions, and how many. As scripts/capture.py's red_presence."""
    out = {}
    for hostname, host in state.hosts.items():
        red = {a: len(s) for a, s in host.sessions.items() if a.startswith("red") and s}
        if red:
            out[hostname] = red
    return out
''', "helper")
    src = sub(src, "only_agents=None, policy_seed=None, log_policy=False):\n",
              "only_agents=None, policy_seed=None, log_policy=False, log_truth=False):\n", "capture_episode signature")
    src = sub(src, '"busy": getattr(_gw, "_KEEP_BUSY", "unpatched"), "log_policy": log_policy, ',
              '"busy": getattr(_gw, "_KEEP_BUSY", "unpatched"), "log_policy": log_policy, "log_truth": log_truth, ',
              "header")
    src = sub(src, '                **({"policy": stats["pol"], "busy": busy} if log_policy else {}),\n',
              '                **({"policy": stats["pol"], "busy": busy} if log_policy else {}),\n'
              '                **({"truth": {"red_hosts": _red_presence(cyborg.environment_controller.state)}} if log_truth else {}),\n',
              "step record")
    src = sub(src, "a.window, a.queue, noise, agents, a.policy_seed, a.log_policy)\n",
              "a.window, a.queue, noise, agents, a.policy_seed, a.log_policy, a.log_truth)\n", "Parallel call")
    return sub(src, '    p.add_argument("--log-policy", action="store_true", help="record each agent\'s directive before any '
                    'rule, and the agents busy when each step began")\n',
               '    p.add_argument("--log-policy", action="store_true", help="record each agent\'s directive before any '
               'rule, and the agents busy when each step began")\n'
               '    p.add_argument("--log-truth", action="store_true", help="record the hosts holding a red session after '
               'each step, as capture.py does, so the arm can be scored by recompute_criteria.py")\n', "argparse")


if not os.path.exists(ORC):
    sys.exit(f"{ORC} is missing")
src = open(ORC).read()
if MARK in src:
    print("already patched", ORC)
elif "--log-policy" not in src:
    sys.exit(f"{ORC} lacks the v2 busy patch (--log-policy). Run tools_patch_keep_busy.py first. No file was changed.")
else:
    try:
        new = patch(src)
    except ValueError as err:
        sys.exit(f"{ORC}: {err}. No file was changed.")
    tmp = ORC + ".tmp"
    open(tmp, "w").write(new)
    os.chmod(tmp, os.stat(ORC).st_mode)
    os.replace(tmp, ORC)
    print("patched", ORC)
print(hashlib.md5(open(ORC).read().encode()).hexdigest(), os.path.relpath(ORC, ROOT))
print("done")
