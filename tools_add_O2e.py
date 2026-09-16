"""Add rule O2e: O2 with the latched observable-evidence set in place of ground truth."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if 'rule == "O2e"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

# 1. docstring line
src = src.replace(
    "  O2    Override only when KEEP's choice is wrong given ground truth",
    "  O2    Override only when KEEP's choice is wrong given ground truth\n"
    "  O2e   As O2, but 'compromised' is the latched observable-evidence set (hosts named by a\n"
    "        substantive raw obs since their last Restore/Remove), not ground truth", 1)

# 2. per-episode latch state, just before def patched
marker = "    def patched("
assert src.count(marker) == 1, "def patched not unique"
src = src.replace(marker,
    "    flagged = {}   # O2e: agent_name -> hosts named by a substantive obs since last Restore/Remove\n"
    "    META = {\"success\", \"action\", \"message\"}\n\n" + marker, 1)

# 3. the rule, inserted before O4 (which is where ground-truth comp starts being used)
marker = '        if rule == "O4":\n            comp = [c for c in comp if c[1] in EXPENSIVE]'
assert src.count(marker) == 1, "O4 block not unique"
o2e = '''        if rule == "O2e":
            obs = cyborg.get_observation(agent_name) or {}
            lst = flagged.setdefault(agent_name, [])
            for h, v in obs.items():
                if h not in META and isinstance(v, dict) and h not in lst:
                    lst.append(h)
            own = set(owned_hosts(cyborg, agent_name))
            ecomp = [h for h in lst if h in own]
            acting_on = getattr(act, "hostname", None)
            if type(act).__name__ in ("Restore", "Remove") and acting_on in ecomp:
                stats["agree"] += 1
                lst.remove(acting_on)
                return act
            if not ecomp:
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            stats["override"] += 1
            tgt = ecomp[0]
            lst.remove(tgt)
            return Restore(session=0, agent=agent_name, hostname=tgt)

'''
src = src.replace(marker, o2e + marker, 1)

# 4. argparse choice
src = src.replace('"O9r", "O9s"]', '"O9r", "O9s", "O2e"]', 1)

open(p, "w").write(src)
print("patched; backup at", p + ".bak")
