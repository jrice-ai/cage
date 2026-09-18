"""Move install_oracle's rule body and helpers into scripts/oracle_rules.py, verbatim."""
import re, shutil, sys
p = "scripts/oracle.py"; src = open(p).read()
if "from oracle_rules import" in src:
    print("already refactored"); sys.exit(0)
shutil.copy(p, p + ".bak")

def cut(s, start_pat, end_pat, inclusive_end=True):
    a = s.index(start_pat); b = s.index(end_pat, a)
    if inclusive_end: b += len(end_pat)
    return s[a:b], s[:a] + s[b:]

prov, src = cut(src, "# --- provenance (added 2026-09-15) ---", "# --- end provenance ---\n")
helpers, src = cut(src, "EPISODE_LENGTH = 500\n", "\n\ndef install_oracle(", inclusive_end=False)
block, src = cut(src, "def install_oracle(", "    env.action_translator = patched\n")

# --- transform install_oracle -> make_oracle ---
assert block.count("    original = env.action_translator\n") == 1
block = block.replace("def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0):\n",
                      "def make_oracle(cyborg, rule, stats, budget=77, decoys=None, min_gap=0):\n", 1)
block = block.replace('    """Wrap action_translator so overrides slot in before execution."""\n',
                      '    """Return intercept(agent_name, act) -> act. Rule bodies are verbatim from oracle.py.install_oracle."""\n', 1)
block = block.replace("    original = env.action_translator\n", "", 1)
old = '''    def patched(agent_name, a_id):
        stats["calls"] += 1
        _tick[agent_name] = _tick.get(agent_name, 0) + 1
        act = original(agent_name, a_id)
        res = _decide(agent_name, act)
'''
new = '''    def intercept(agent_name, act):
        stats["calls"] += 1
        _tick[agent_name] = _tick.get(agent_name, 0) + 1
        res = _decide(agent_name, act)
'''
assert block.count(old) == 1; block = block.replace(old, new, 1)
block = block.replace("    env.action_translator = patched\n", "    return intercept\n", 1)
# O11 must not crash where wrapper.globals is absent
old = '            pr = stats["probs"].get(agent_name) if isinstance(stats.get("probs"), dict) else None\n'
assert block.count(old) == 1
block = block.replace(old, '            if NODE_ACTIONS is None:\n                return act\n' + old, 1)

rules_mod = '''"""Shared oracle rules and helpers. Imported by oracle.py (KEEP) and capture_hmarl.py (H-MARL).
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

''' + prov + "\n" + helpers + "\n\n" + block
open("scripts/oracle_rules.py", "w").write(rules_mod)

# --- oracle.py: import the shared names, keep the loop ---
imp = '''from oracle_rules import (make_oracle, note_impacts, owned_hosts, compromised_by_agent, subnet_of,
                          EPISODE_LENGTH, BLUE, RED, OWNER, EXPENSIVE, HARNESS_SHA, MACHINE,
                          _IMPACT_SEEN, _HOSTS_CACHE)
'''
anchor = "from wrapper.globals import MY_SUBNETS, MAX_HOSTS, MAX_ACTIONS, NODE_ACTIONS\n"
assert src.count(anchor) == 1
src = src.replace(anchor, anchor + imp, 1)
src = src.replace("\n\n\ndef capture_episode(", '''

def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0):
    """Wrap action_translator so overrides slot in before execution."""
    intercept = make_oracle(cyborg, rule, stats, budget, decoys, min_gap)
    original = env.action_translator
    def patched(agent_name, a_id):
        return intercept(agent_name, original(agent_name, a_id))
    env.action_translator = patched


def capture_episode(''', 1)
src = re.sub(r"\n{4,}", "\n\n\n", src)
open(p, "w").write(src)
print("wrote scripts/oracle_rules.py and rewrote scripts/oracle.py; backup at", p + ".bak")
