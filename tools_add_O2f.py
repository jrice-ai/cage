#!/usr/bin/env python3
"""Add the corrected evidence rules O2f, O2fr, O2fw to the oracle harness.

O2e, O2er and O2ew flag a host on any substantive observation entry naming it. Two entries
are not evidence and were counted: the reset observation at step 0, which names every owned
host (so every host started flagged and "oldest flag first" was dictionary order), and the
echo of the agent's own action on a host the step before (so a restored host was re-flagged
by its own Restore result). The rule defenders (tools_add_R1.py) exclude both. O2f, O2fr and
O2fw are O2e, O2er and O2ew with the same two exclusions; an entry that carries a file at
Density >= 0.9 always counts. Everything else (ordering, expiry, budget, the tp/fp/fn latch
confusion, flags_new) is unchanged, so the corrected arms pair with the originals and the
confusion table recomputes from their footers. The original rule names keep their behaviour
for provenance.

Edits (each tested for the code it inserts; run from ~/cage):
  scripts/oracle_rules.py   KNOWN_RULES; the evidence branch of _decide; intercept records
                            the executed action's host per agent as "acted"
  scripts/oracle.py         --rule choices
  scripts/capture_hmarl.py  RULES
"""
RULES = "scripts/oracle_rules.py"
ORC = "scripts/oracle.py"
HM = "scripts/capture_hmarl.py"


def edit(path, fn):
    src = open(path).read()
    new = fn(src)
    if new != src:
        open(path, "w").write(new); print("patched", path)
    else:
        print("already patched", path)


def patch_rules(src):
    if '"O2f", "O2fr", "O2fw"' not in src.split("def make_oracle")[0]:
        old = '"O2e", "O2er", "O2ew", "O2s", "O10", "O11", "O12", "O13", "O14"}'
        assert src.count(old) == 1, "KNOWN_RULES not found"
        src = src.replace(old, '"O2e", "O2er", "O2ew", "O2s", "O10", "O11", "O12", "O13", "O14",\n'
                               '               "O2f", "O2fr", "O2fw"}')
    if 'if rule in ("O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O10", "O12", "O13"):' not in src:
        old = 'if rule in ("O2e", "O2er", "O2ew", "O2s", "O10", "O12", "O13"):'
        assert src.count(old) == 1, "evidence branch not found"
        src = src.replace(old, 'if rule in ("O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O10", "O12", "O13"):')
    if 'st.get("acted") == (h, t - 1)' not in src:
        old = ('''                    if rule in ("O2s", "O10", "O12", "O13"):
                        _fl = v.get("Files") or []
                        if not any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in _fl):
                            continue
''')
        assert src.count(old) == 1, "strict filter not found"
        src = src.replace(old, old + '''                    if rule in ("O2f", "O2fr", "O2fw"):
                        _fl = v.get("Files") or []
                        _conf = any(isinstance(x, dict) and float(x.get("Density") or 0) >= 0.9 for x in _fl)
                        if not _conf and (t == 1 or st.get("acted") == (h, t - 1)):
                            continue           # the reset listing, or the echo of this agent's own action
''')
    if 'if rule in ("O2ew", "O2fw"):' not in src:
        old = '            if rule == "O2ew":\n'
        assert src.count(old) == 1, "O2ew expiry not found"
        src = src.replace(old, '            if rule in ("O2ew", "O2fw"):\n')
    if 'if rule in ("O2e", "O2f"):' not in src:
        old = '            if rule == "O2e":\n                ecomp = sorted(live, key=lambda h: live[h][0])'
        assert src.count(old) == 1, "O2e ordering not found"
        src = src.replace(old, '            if rule in ("O2e", "O2f"):\n                ecomp = sorted(live, key=lambda h: live[h][0])')
    if 'flagged[agent_name]["acted"] = ' not in src:
        old = ('''        if defender is not None:
            defender.note(agent_name, res)       # whatever runs, the rule remembers it
        return res
''')
        assert src.count(old) == 1, "intercept tail not found"
        src = src.replace(old, '''        if agent_name in flagged:                # O2f family: the executed action's host, for the echo test
            _h = getattr(res, "hostname", None)
            flagged[agent_name]["acted"] = (_h, flagged[agent_name]["t"]) if _h else None
        if defender is not None:
            defender.note(agent_name, res)       # whatever runs, the rule remembers it
        return res
''')
    return src


def patch_oracle(src):
    if '"O2ew", "O2f", "O2fr", "O2fw", "O2s"' not in src:
        old = '"O2e", "O2er", "O2ew", "O2s", "O11", "O10", "O12", "O13",'
        assert src.count(old) == 1, "--rule choices not found"
        src = src.replace(old, '"O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O11", "O10", "O12", "O13",')
    return src


def patch_hm(src):
    if '"O2ew", "O2f", "O2fr", "O2fw", "O2s"' not in src:
        old = '"O2e", "O2er", "O2ew", "O2s", "O10", "O12", "O13", "O14"]'
        assert src.count(old) == 1, "RULES not found"
        src = src.replace(old, '"O2e", "O2er", "O2ew", "O2f", "O2fr", "O2fw", "O2s", "O10", "O12", "O13", "O14"]')
    return src


if __name__ == "__main__":
    edit(RULES, patch_rules)
    edit(ORC, patch_oracle)
    edit(HM, patch_hm)
    print("done")
