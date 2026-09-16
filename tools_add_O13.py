"""O13: O10 with rotation - least-recently-investigated compromised host first, no repeat within 50 steps."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if 'rule == "O13"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")
def rep(old, new):
    global src
    assert src.count(old) == 1, f"anchor: {old[:60]!r} count={src.count(old)}"
    src = src.replace(old, new, 1)

rep('        if rule in ("O2e", "O2er", "O2ew", "O2s", "O10", "O12"):\n',
    '        if rule in ("O2e", "O2er", "O2ew", "O2s", "O10", "O12", "O13"):\n')
rep('                    if rule in ("O2s", "O10", "O12"):\n',
    '                    if rule in ("O2s", "O10", "O12", "O13"):\n')
rep('''                unflagged = [c[0] for c in comp if c[0] not in st["h"]]
                if not unflagged:
                    return act
''', '''                unflagged = [c[0] for c in comp if c[0] not in st["h"]]
                if not unflagged:
                    return act
''')
rep('            if rule in ("O10", "O12"):\n',
    '''            if rule == "O13":
                inv = st.setdefault("inv", {})            # host -> agent-step of last investigation
                cands = [c[0] for c in comp if c[0] not in st["h"] and t - inv.get(c[0], -10**9) >= 50]
                if not cands:
                    return act
                if stats["override"] >= budget:
                    stats["exhausted"] += 1
                    return act
                cands.sort(key=lambda h: inv.get(h, -10**9))   # least recently investigated first
                tgt = cands[0]; inv[tgt] = t
                stats["override"] += 1
                return Analyse(session=0, agent=agent_name, hostname=tgt)
            if rule in ("O10", "O12"):
''')
rep('"O2s", "O11", "O10", "O12"]', '"O2s", "O11", "O10", "O12", "O13"]')
src = src.replace("  O12   O2s restore if a strictly-flagged host exists, else O10 investigate",
    "  O12   O2s restore if a strictly-flagged host exists, else O10 investigate\n"
    "  O13   As O10, rotating: least-recently-investigated host first, none repeated within 50 steps")
open(p, "w").write(src)
print("patched; backup at", p + ".bak")
