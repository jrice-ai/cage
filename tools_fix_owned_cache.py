#!/usr/bin/env python3
"""Fix two id(cyborg)-keyed caches in scripts/oracle_rules.py.

owned_hosts cached the host list under (id(cyborg), agent). Once a CybORG object is
freed, a later one can be allocated at the same address, so a worker running several
episodes could serve a previous episode's host list (CC4 redraws host counts per
episode). The same key also breaks the H-MARL harness's --compat mode, where one
CybORG is reset per episode. The cache is now per agent and validated against the
live State object and its host-name tuple.

note_impacts kept the impact memory under id(cyborg) across episodes for the same
reason. It is now cleared at step 0.

Idempotent: tests for the replacement code, not a token. Run from ~/cage.
"""
import sys

P = "scripts/oracle_rules.py"
src = open(P).read()

OLD_OWNED = '''def owned_hosts(cyborg, agent_name):
    key = (id(cyborg), agent_name)
    if key not in _HOSTS_CACHE:
        st = cyborg.environment_controller.state
        _HOSTS_CACHE[key] = [
            h for h in st.hosts
            if "router" not in h and subnet_of(h)
            and OWNER.get(subnet_of(h)) == agent_name]
    return _HOSTS_CACHE[key]
'''
NEW_OWNED = '''def owned_hosts(cyborg, agent_name):
    # Cached per agent against the live State object (held strongly, so its address
    # cannot be recycled by a later episode) and its host-name tuple, so a fresh
    # CybORG per episode and a reset() of the same CybORG both invalidate it.
    st = cyborg.environment_controller.state
    names = tuple(st.hosts)
    ent = _HOSTS_CACHE.get(agent_name)
    if ent is None or ent[0] is not st or ent[1] != names:
        ent = (st, names, [
            h for h in names
            if "router" not in h and subnet_of(h)
            and OWNER.get(subnet_of(h)) == agent_name])
        _HOSTS_CACHE[agent_name] = ent
    return ent[2]
'''
OLD_IMP = '''    key = id(cyborg)
    d = _IMPACT_SEEN.setdefault(key, {})
'''
NEW_IMP = '''    key = id(cyborg)
    d = _IMPACT_SEEN.setdefault(key, {})
    if step == 0:
        d.clear()   # a recycled id or a reset() must not inherit the last episode's impacts
'''

changed = False
if NEW_OWNED in src:
    print("owned_hosts: already fixed")
else:
    assert src.count(OLD_OWNED) == 1, "owned_hosts: expected code not found exactly once"
    src = src.replace(OLD_OWNED, NEW_OWNED); changed = True
    print("owned_hosts: patched")

if NEW_IMP in src:
    print("note_impacts: already fixed")
else:
    assert src.count(OLD_IMP) == 1, "note_impacts: expected code not found exactly once"
    src = src.replace(OLD_IMP, NEW_IMP); changed = True
    print("note_impacts: patched")

if changed:
    open(P, "w").write(src)
    print("wrote", P)
