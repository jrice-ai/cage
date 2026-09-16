"""--min-gap N: per-agent minimum steps between overrides; deferred overrides are logged."""
import re, shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if "min_gap" in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

# signatures
src = src.replace("def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None):",
                  "def install_oracle(env, cyborg, rule, stats, budget=77, decoys=None, min_gap=0):", 1)
src = src.replace('def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent"):',
                  'def capture_episode(ep, base_seed, out_dir, rule, budget=77, red_agent="FiniteStateRedAgent", min_gap=0):', 1)
assert src.count("min_gap=0") == 2, "signature edits failed"
src = src.replace("    install_oracle(env, cyborg, rule, stats, budget, decoys)\n",
                  "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap)\n", 1)

# wrapper: per-agent step counter and gap enforcement
old = '''    def patched(agent_name, a_id):
        stats["calls"] += 1
        act = original(agent_name, a_id)
        res = _decide(agent_name, act)
        if res is not act:
            stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
        return res
'''
new = '''    _tick = {}; _last = {}
    def patched(agent_name, a_id):
        stats["calls"] += 1
        _tick[agent_name] = _tick.get(agent_name, 0) + 1
        act = original(agent_name, a_id)
        res = _decide(agent_name, act)
        if res is not act:
            if min_gap and _tick[agent_name] - _last.get(agent_name, -10**9) < min_gap:
                stats["override"] -= 1
                stats["deferred"] = stats.get("deferred", 0) + 1
                return act
            _last[agent_name] = _tick[agent_name]
            stats.setdefault("ovr", []).append([agent_name, _fmt(act), _fmt(res)])
        return res
'''
assert src.count(old) == 1, "wrapper not found"
src = src.replace(old, new, 1)

# header + footer
src = src.replace('"budget": budget,', '"budget": budget, "min_gap": min_gap,', 1)
old_f = '            "agreements": stats["agree"],\n'
assert src.count(old_f) == 1
src = src.replace(old_f, old_f + '            "deferred": stats.get("deferred", 0),\n', 1)

# argparse + call sites
src = src.replace('    p.add_argument("--rule", default="O1",',
                  '    p.add_argument("--min-gap", type=int, default=0, help="per-agent minimum steps between overrides")\n'
                  '    p.add_argument("--rule", default="O1",', 1)
old_c = "        delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red)\n"
assert src.count(old_c) == 1, "call site not found"
src = src.replace(old_c, "        delayed(capture_episode)(ep, a.base_seed, a.out, a.rule, a.budget, a.red, a.min_gap)\n", 1)
n = 1
open(p, "w").write(src)
print(f"patched; {n} call site(s); backup at {p}.bak")
