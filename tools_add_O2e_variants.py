"""O2er (most-recent-first) and O2ew (30-step window) variants of O2e."""
import shutil, sys, re
p = "scripts/oracle.py"
src = open(p).read()
if 'rule == "O2ew"' in src:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

start = src.index('        if rule == "O2e":')
end = src.index('            return Restore(session=0, agent=agent_name, hostname=tgt)\n', start) \
      + len('            return Restore(session=0, agent=agent_name, hostname=tgt)\n')

new = '''        if rule in ("O2e", "O2er", "O2ew"):
            obs = cyborg.get_observation(agent_name) or {}
            st = flagged.setdefault(agent_name, {"t": 0, "h": {}})   # h: host -> [first_seen, last_seen]
            st["t"] += 1
            t = st["t"]
            for h, v in obs.items():
                if h not in META and isinstance(v, dict):
                    if h in st["h"]:
                        st["h"][h][1] = t
                    else:
                        st["h"][h] = [t, t]
            own = set(owned_hosts(cyborg, agent_name))
            live = {h: fl for h, fl in st["h"].items() if h in own}
            if rule == "O2ew":
                live = {h: fl for h, fl in live.items() if t - fl[1] <= 30}
            if rule == "O2e":
                ecomp = sorted(live, key=lambda h: live[h][0])       # oldest flag first
            else:
                ecomp = sorted(live, key=lambda h: -live[h][1])      # most recently seen first
            acting_on = getattr(act, "hostname", None)
            if type(act).__name__ in ("Restore", "Remove") and acting_on in ecomp:
                stats["agree"] += 1
                st["h"].pop(acting_on, None)
                return act
            if not ecomp:
                return act
            if stats["override"] >= budget:
                stats["exhausted"] += 1
                return act
            stats["override"] += 1
            tgt = ecomp[0]
            st["h"].pop(tgt, None)
            return Restore(session=0, agent=agent_name, hostname=tgt)
'''
src = src[:start] + new + src[end:]
src = src.replace('"O9s", "O2e"]', '"O9s", "O2e", "O2er", "O2ew"]', 1)
src = src.replace("        substantive raw obs since their last Restore/Remove), not ground truth",
    "        substantive raw obs since their last Restore/Remove), not ground truth\n"
    "  O2er  As O2e, most-recently-observed host first\n"
    "  O2ew  As O2er, flags expire 30 steps after the last observation naming the host", 1)
open(p, "w").write(src)
print("patched; backup at", p + ".bak")
