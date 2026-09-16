"""O10: investigate authority (Analyse on compromised-unflagged hosts). O12: O2s restore when a strict
flag exists, else O10 investigate."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if '"O10"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

old = "from CybORG.Simulator.Actions import Restore, Remove, Monitor, Sleep\n"
assert src.count(old) == 1
src = src.replace(old, "from CybORG.Simulator.Actions import Restore, Remove, Monitor, Sleep, Analyse\n", 1)

old = '        if rule in ("O2e", "O2er", "O2ew", "O2s"):\n'
assert src.count(old) == 1
src = src.replace(old, '        if rule in ("O2e", "O2er", "O2ew", "O2s", "O10", "O12"):\n', 1)

old = '                    if rule == "O2s":\n'
assert src.count(old) == 1
src = src.replace(old, '                    if rule in ("O2s", "O10", "O12"):\n', 1)

# branch point: after the confusion counts, before the O2e agree line
old = '''            acting_on = getattr(act, "hostname", None)
            if type(act).__name__ in ("Restore", "Remove") and acting_on in ecomp:
                stats["agree"] += 1
                st["h"].pop(acting_on, None)
                return act
'''
assert src.count(old) == 1
new = old + '''            if rule in ("O10", "O12"):
                if rule == "O12" and ecomp:
                    if stats["override"] >= budget:
                        stats["exhausted"] += 1
                        return act
                    stats["override"] += 1; stats["restores"] = stats.get("restores", 0) + 1
                    tgt = ecomp[0]; st["h"].pop(tgt, None)
                    return Restore(session=0, agent=agent_name, hostname=tgt)
                unflagged = [c[0] for c in comp if c[0] not in st["h"]]
                if not unflagged:
                    return act
                if stats["override"] >= budget:
                    stats["exhausted"] += 1
                    return act
                stats["override"] += 1; stats["analyses"] = stats.get("analyses", 0) + 1
                return Analyse(session=0, agent=agent_name, hostname=unflagged[0])
'''
src = src.replace(old, new, 1)

old = '            "deferred": stats.get("deferred", 0),\n'
assert src.count(old) == 1
src = src.replace(old, old + '            "analyses": stats.get("analyses", 0), "restores": stats.get("restores", 0),\n', 1)

src = src.replace('"O2s", "O11"]', '"O2s", "O11", "O10", "O12"]', 1)
src = src.replace("        the argmax of KEEP's own action distribution over those two verbs",
    "        the argmax of KEEP's own action distribution over those two verbs\n"
    "  O10   Investigate: Analyse a compromised host that is not strictly flagged; KEEP does the recovering\n"
    "  O12   O2s restore if a strictly-flagged host exists, else O10 investigate", 1)
open(p, "w").write(src)
print("patched; backup at", p + ".bak")
