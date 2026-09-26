#!/usr/bin/env python3
"""Add R4tn: R4t without posture (three decoys per host, Analyse on the first alert, Restore on the
second or a confirmed file, no BlockTrafficZone / AllowTrafficZone).

Under O1 at gap 32, R4t and R4t3 both land about 310 behind R2 though R4t leads R2 by 396 alone
and R4t3's own restores match R2's; what remains between them is posture and decoys. R4tn splits
the two. Applies after tools_add_R4t3.py; idempotent, tests for the code it inserts. Run from ~/cage.
"""
RULES = "scripts/oracle_rules.py"
ORC = "scripts/oracle.py"


def edit(path, fn):
    src = open(path).read()
    new = fn(src)
    if new != src:
        open(path, "w").write(new); print("patched", path)
    else:
        print("already patched", path)


def patch_rules(src):
    assert 'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3",' in src, \
        "tools_add_R4t3.py is not installed"
    # (old, new, key): key proves the edit is present and survives later kinds appended to the line
    steps = [
        ('DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "RT")',
         'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "R4tn", "RT")',
         'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "R4tn",'),
        ('ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2, "R4t": 2, "R4t3": 3}',
         'ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2, "R4t": 2, "R4t3": 3, "R4tn": 2}',
         '"R4t3": 3, "R4tn": 2'),
        ('    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t", "R4t3")\n',
         '    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t", "R4t3", "R4tn")\n',
         '    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t", "R4t3", "R4tn"'),
        ('    triage = kind in ("R1", "R2", "R2d", "R4t", "R4t3")  # Analyse alerted hosts below the threshold\n',
         '    triage = kind in ("R1", "R2", "R2d", "R4t", "R4t3", "R4tn")  # Analyse alerted hosts below the threshold\n',
         '    triage = kind in ("R1", "R2", "R2d", "R4t", "R4t3", "R4tn"'),
        ('    decoy = kind in ("R2d", "R4", "R4d", "R4t", "R4t3")\n',
         '    decoy = kind in ("R2d", "R4", "R4d", "R4t", "R4t3", "R4tn")\n',
         '    decoy = kind in ("R2d", "R4", "R4d", "R4t", "R4t3", "R4tn"'),
        ('      R4t3 R4t with Restore on the third alert instead of the second (ablation)\n',
         '      R4t3 R4t with Restore on the third alert instead of the second (ablation)\n'
         '      R4tn R4t without posture: decoys, triage, two-alert Restore, no blocks (ablation)\n',
         '      R4tn R4t without posture'),
    ]
    for old, new, key in steps:
        if key in src:
            continue
        assert src.count(old) == 1, f"not found: {old.strip()[:60]}"
        src = src.replace(old, new)
    # posture stays ("R4", "R4p", "R4d", "R4t", "R4t3"): R4tn is deliberately absent from it
    assert '"R4tn"' not in src.split("    posture = kind in (")[1].split("\n")[0], "R4tn must not have posture"
    return src


def patch_oracle(src):
    steps = [
        ('"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "RT",\n',
         '"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "R4tn", "RT",\n',
         '"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "R4tn",'),
        ('"R4t+O1", "R4t3+O1", "RT+O1"]', '"R4t+O1", "R4t3+O1", "R4tn+O1", "RT+O1"]', '"R4t3+O1", "R4tn+O1",'),
    ]
    for old, new, key in steps:
        if key in src:
            continue
        assert src.count(old) == 1, f"not found: {old.strip()[:60]}"
        src = src.replace(old, new)
    return src


if __name__ == "__main__":
    edit(RULES, patch_rules)
    edit(ORC, patch_oracle)
    print("done")
