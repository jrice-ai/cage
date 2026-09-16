"""O2s: evidence rule restricted to Analyse-produced Files with Density >= 0.9."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if '"O2s"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

old = '        if rule in ("O2e", "O2er", "O2ew"):\n'
assert src.count(old) == 1
src = src.replace(old, '        if rule in ("O2e", "O2er", "O2ew", "O2s"):\n', 1)

old = '''            for h, v in obs.items():
                if h not in META and isinstance(v, dict):
                    if h in st["h"]:'''
assert src.count(old) == 1
new = '''            for h, v in obs.items():
                if h not in META and isinstance(v, dict):
                    if rule == "O2s":
                        _fl = v.get("Files") or []
                        if not any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in _fl):
                            continue
                    if h in st["h"]:'''
src = src.replace(old, new, 1)

src = src.replace('"O2e", "O2er", "O2ew"]', '"O2e", "O2er", "O2ew", "O2s"]', 1)
src = src.replace("  O2ew  As O2er, flags expire 30 steps after the last observation naming the host",
    "  O2ew  As O2er, flags expire 30 steps after the last observation naming the host\n"
    "  O2s   As O2er, but a host is flagged only by a Files entry with Density >= 0.9 (Analyse-confirmed)", 1)
open(p, "w").write(src)
print("patched; backup at", p + ".bak")
