"""O11: constrain authority. When a compromised host is in the agent's subnets, force Restore/Remove
but let KEEP choose the host via argmax of its own action distribution over those verbs."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if 'rule == "O11"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

old = "from wrapper.globals import MY_SUBNETS\n"
assert src.count(old) == 1, "globals import not found"
src = src.replace(old, "from wrapper.globals import MY_SUBNETS, MAX_HOSTS, MAX_ACTIONS, NODE_ACTIONS\n", 1)

old = "    install_oracle(env, cyborg, rule, stats, budget, decoys, min_gap)\n"
assert src.count(old) == 1, "install_oracle call not found"
new = old + '''    if rule == "O11":
        stats["probs"] = {}
        for _n, _ag in agents.items():
            def _wrap(obs, *a, _orig=_ag.get_action, _ag=_ag, _n=_n):
                state, is_blocked = obs
                if is_blocked:
                    stats["probs"][_n] = None
                else:
                    with torch.no_grad():
                        stats["probs"][_n] = _ag.actor(*state).probs.detach().flatten()
                return _orig(obs, *a)
            _ag.get_action = _wrap
'''
src = src.replace(old, new, 1)

old = '''        if rule == "O1":
            stats["override"] += 1
            return Restore(session=0, agent=agent_name, hostname=target)
'''
assert src.count(old) == 1, "O1 block not found"
new = old + '''        if rule == "O11":
            if name in ("Restore", "Remove") and getattr(act, "hostname", None) in dirty:
                stats["agree"] += 1
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
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
'''
src = src.replace(old, new, 1)

if '"O11"' not in src:
    src = src.replace('"O2e", "O2er", "O2ew", "O2s"]', '"O2e", "O2er", "O2ew", "O2s", "O11"]', 1)
src = src.replace("  O2s   As O2er, but a host is flagged only by a Files entry with Density >= 0.9 (Analyse-confirmed)",
    "  O2s   As O2er, but a host is flagged only by a Files entry with Density >= 0.9 (Analyse-confirmed)\n"
    "  O11   Constrain: when a compromised host exists, force Restore/Remove but take the host from\n"
    "        the argmax of KEEP's own action distribution over those two verbs", 1)
open(p, "w").write(src)
print("patched; backup at", p + ".bak")
