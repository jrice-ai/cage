"""Per-episode confusion counts between the evidence latch and ground truth, for O2e/O2er/O2ew."""
import shutil, sys
p = "scripts/oracle.py"
src = open(p).read()
if '"latch_tp"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

# count right after ecomp is built (both orderings end with the same next line)
marker = '            acting_on = getattr(act, "hostname", None)\n            if type(act).__name__ in ("Restore", "Remove") and acting_on in ecomp:'
assert src.count(marker) == 1, "O2e agree-line not unique"
count = '''            _gt = {c[0] for c in comp}; _ev = set(ecomp)
            stats["tp"] = stats.get("tp", 0) + len(_gt & _ev)
            stats["fp"] = stats.get("fp", 0) + len(_ev - _gt)
            stats["fn"] = stats.get("fn", 0) + len(_gt - _ev)
            stats["own"] = stats.get("own", 0) + len(own)
'''
src = src.replace(marker, count + marker, 1)

# footer
old = '            "agreements": stats["agree"],\n'
assert src.count(old) == 1, "footer agreements line not unique"
new = old + '            "latch_tp": stats.get("tp", 0), "latch_fp": stats.get("fp", 0),\n' \
            '            "latch_fn": stats.get("fn", 0), "latch_own": stats.get("own", 0),\n'
src = src.replace(old, new, 1)

open(p, "w").write(src)
print("patched; backup at", p + ".bak")
