"""Executed-by-type counters in the gap wrapper; workers in header; drop duplicate red_agent key."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if 'stats["exec_"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")
def rep(old, new):
    global src
    assert src.count(old) == 1, f"anchor: {old[:60]!r} count={src.count(old)}"
    src = src.replace(old, new, 1)

# 1. attempts -> executions
rep('stats["override"] += 1; stats["restores"] = stats.get("restores", 0) + 1\n', 'stats["override"] += 1\n')
rep('stats["override"] += 1; stats["analyses"] = stats.get("analyses", 0) + 1\n', 'stats["override"] += 1\n')
rep('''            _last[agent_name] = _tick[agent_name]
            stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
''', '''            _last[agent_name] = _tick[agent_name]
            _k = "exec_" + type(res).__name__
            stats[_k] = stats.get(_k, 0) + 1
            stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
''')
rep('            "analyses": stats.get("analyses", 0), "restores": stats.get("restores", 0),\n',
    '            "analyses": stats.get("exec_Analyse", 0), "restores": stats.get("exec_Restore", 0),\n'
    '            "removes": stats.get("exec_Remove", 0), "sleeps": stats.get("exec_Sleep", 0),\n')

# 2. workers -> header
rep('def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent", min_gap=0):',
    'def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent", min_gap=0, workers=0):')
rep('"rule": rule, "budget": budget, "min_gap": min_gap, "red_agent": red_agent, "cyborg_version": CYBORG_VERSION,',
    '"rule": rule, "budget": budget, "min_gap": min_gap, "workers": workers, "cyborg_version": CYBORG_VERSION,')
rep('        delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red, a.min_gap)\n',
    '        delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red, a.min_gap, a.workers)\n')

open(p, "w").write(src)
print("patched; backup at", p + ".bak")
