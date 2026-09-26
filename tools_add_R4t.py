#!/usr/bin/env python3
"""Add R4t, the playbook with triage in place of Remove, to the rule defenders.

R4  posture, decoys (three per host), Remove on the first alert, Restore on the second or a confirmed file
R4t posture, decoys (three per host), Analyse on the first alert, Restore on the second or a confirmed file
R2d triage, Restore on the second alert or a confirmed file, one decoy per server (no posture)

R4 is 400 behind R2 and R2d under both reds; R4t attributes that to the Remove (if R4t lands near
R2d) or to posture and the heavier decoy load (if it lands near R4). Applies after tools_add_R1.py
v3.1; idempotent, tests for the code it inserts. Run from ~/cage.
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
    assert 'and st["last"][h] > st["removed"].get(h, -10**9)),' in src, "tools_add_R1.py v3.1 is not installed"
    # (old, new, key): key is the part of new that proves the edit is present, and survives later
    # kinds being appended to the same line (R4t3 and any after it)
    steps = [
        ('DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "RT")',
         'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "RT")',
         'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t",'),
        ('ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2}',
         'ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2, "R4t": 2}',
         '"R4": 2, "R4t": 2'),
        ('    posture = kind in ("R4", "R4p", "R4d")\n',
         '    posture = kind in ("R4", "R4p", "R4d", "R4t")\n',
         '    posture = kind in ("R4", "R4p", "R4d", "R4t"'),
        ('    evict = kind in ("R1", "R2", "R2d", "R3", "R4")\n',
         '    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t")\n',
         '    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t"'),
        ('    triage = kind in ("R1", "R2", "R2d")         # Analyse once-alerted hosts\n',
         '    triage = kind in ("R1", "R2", "R2d", "R4t")  # Analyse once-alerted hosts\n',
         '    triage = kind in ("R1", "R2", "R2d", "R4t"'),
        ('    decoy = kind in ("R2d", "R4", "R4d")\n',
         '    decoy = kind in ("R2d", "R4", "R4d", "R4t")\n',
         '    decoy = kind in ("R2d", "R4", "R4d", "R4t"'),
        ('      R4p  posture only, then sleep                     (ablation)\n',
         '      R4p  posture only, then sleep                     (ablation)\n'
         '      R4t  R4 with Analyse on the first alert in place of Remove   (ablation)\n',
         '      R4t  R4 with Analyse on the first alert in place of Remove'),
    ]
    for old, new, key in steps:
        if key in src:
            continue
        assert src.count(old) == 1, f"not found: {old.strip()[:60]}"
        src = src.replace(old, new)
    return src


def patch_oracle(src):
    steps = [
        ('"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "RT",\n',
         '"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "RT",\n',
         '"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t",'),
        ('"R4d+O1", "RT+O1"]', '"R4d+O1", "R4t+O1", "RT+O1"]', '"R4d+O1", "R4t+O1",'),
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
