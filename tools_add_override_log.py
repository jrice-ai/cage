"""Log every override as [agent, from, to] on the step record."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if "def _decide(" in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

old_head = '    def patched(agent_name, a_id):\n        stats["calls"] += 1\n        act = original(agent_name, a_id)\n'
assert src.count(old_head) == 1, "patched head not found as expected"
src = src.replace(old_head, '    def _decide(agent_name, act):\n', 1)

old_install = '    env.action_translator = patched\n'
assert src.count(old_install) == 1
wrapper = '''    def _fmt(a):
        return f"{type(a).__name__}:{getattr(a, 'hostname', '')}"

    def patched(agent_name, a_id):
        stats["calls"] += 1
        act = original(agent_name, a_id)
        res = _decide(agent_name, act)
        if res is not act:
            stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
        return res

'''
src = src.replace(old_install, wrapper + old_install, 1)

old_step = '                "n_compromised_owned": n_comp,\n'
assert src.count(old_step) == 1
src = src.replace(old_step, old_step + '                "overrides": stats.pop("ovr", []),\n', 1)

open(p, "w").write(src)
print("patched; backup at", p + ".bak")
