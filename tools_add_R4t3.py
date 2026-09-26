#!/usr/bin/env python3
"""Add R4t3: R4t with a three-alert threshold for Restore (posture, three decoys per host, Analyse
on alerted hosts, Restore on the third alert or a confirmed file).

R4t generates 371 alerts an episode to R2's 212 (decoys are alert sources) and converts them to
145 restores against R2's 82; under O1 the gap widens (167 to 78) at lower precision, and R4t + O1
falls 306 behind R2 + O1 though R4t leads R2 by 396 alone. R4t3 raises the bar one alert to test
whether those evictions are the cost under supervision. Applies after tools_add_R4t.py;
idempotent, tests for the code it inserts. Run from ~/cage.
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
    assert 'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t",' in src, "tools_add_R4t.py is not installed"
    # (old, new, key): key proves the edit is present and survives later kinds appended to the line
    steps = [
        ('DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "RT")',
         'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "RT")',
         'DEFENDERS = ("R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3",'),
        ('ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2, "R4t": 2}',
         'ALERTS_TO_RESTORE = {"R1": 10**9, "R2": 2, "R2d": 2, "R3": 1, "R4": 2, "R4t": 2, "R4t3": 3}',
         '"R4t": 2, "R4t3": 3'),
        ('    posture = kind in ("R4", "R4p", "R4d", "R4t")\n',
         '    posture = kind in ("R4", "R4p", "R4d", "R4t", "R4t3")\n',
         '    posture = kind in ("R4", "R4p", "R4d", "R4t", "R4t3"'),
        ('    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t")\n',
         '    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t", "R4t3")\n',
         '    evict = kind in ("R1", "R2", "R2d", "R3", "R4", "R4t", "R4t3"'),
        ('    triage = kind in ("R1", "R2", "R2d", "R4t")  # Analyse once-alerted hosts\n',
         '    triage = kind in ("R1", "R2", "R2d", "R4t", "R4t3")  # Analyse alerted hosts below the threshold\n',
         '    triage = kind in ("R1", "R2", "R2d", "R4t", "R4t3"'),
        ('    decoy = kind in ("R2d", "R4", "R4d", "R4t")\n',
         '    decoy = kind in ("R2d", "R4", "R4d", "R4t", "R4t3")\n',
         '    decoy = kind in ("R2d", "R4", "R4d", "R4t", "R4t3"'),
        ('      R4t  R4 with Analyse on the first alert in place of Remove   (ablation)\n',
         '      R4t  R4 with Analyse on the first alert in place of Remove   (ablation)\n'
         '      R4t3 R4t with Restore on the third alert instead of the second (ablation)\n',
         '      R4t3 R4t with Restore on the third alert'),
    ]
    for old, new, key in steps:
        if key in src:
            continue
        assert src.count(old) == 1, f"not found: {old.strip()[:60]}"
        src = src.replace(old, new)
    return src


def patch_oracle(src):
    steps = [
        ('"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "RT",\n',
         '"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3", "RT",\n',
         '"R1", "R2", "R2d", "R3", "R4", "R4p", "R4d", "R4t", "R4t3",'),
        ('"R4d+O1", "R4t+O1", "RT+O1"]', '"R4d+O1", "R4t+O1", "R4t3+O1", "RT+O1"]', '"R4t+O1", "R4t3+O1",'),
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
