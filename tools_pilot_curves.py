#!/usr/bin/env python3
"""Training curves of the busy-flag pilot runs, from their logs.

usage: python3 tools_pilot_curves.py [window] [log ...]
  window  updates per bin (default 25)
  logs    default data/kbf_*.log

Each update prints "[e] Loss: [...]" and then "Avg reward for episode: R", the mean team reward of the
update's 5 training episodes, with e the update's first episode. A resumed run can print an update
twice, and the last print is kept. Prints one row per run with the mean training reward in each bin
of updates, and the number of updates logged.
"""
import glob, os, re, sys

args = sys.argv[1:]
window = int(args.pop(0)) if args and args[0].isdigit() else 25
logs = args or sorted(glob.glob("data/kbf_*.log"))
rows = []
for path in logs:
    text = open(path, errors="replace").read().replace("\r", "\n")
    rewards, e = {}, None
    for line in text.split("\n"):
        m = re.match(r"\[(\d+)\] Loss: ", line)
        if m:
            e = int(m.group(1))
            continue
        m = re.match(r"Avg reward for episode: (-?[0-9.]+)", line)
        if m and e is not None:
            rewards[e // 5 + 1] = float(m.group(1))
            e = None
    rows.append((os.path.basename(path)[:-4], rewards))
last = max((max(r) for _, r in rows if r), default=0)
bins = [(lo, min(lo + window - 1, last)) for lo in range(1, last + 1, window)]
print(f"{'run':14}" + "".join(f"{f'u{lo}-{hi}':>11}" for lo, hi in bins) + "   updates")
for name, r in rows:
    cells = []
    for lo, hi in bins:
        xs = [r[u] for u in range(lo, hi + 1) if u in r]
        cells.append(f"{sum(xs) / len(xs):11.0f}" if xs else f"{'':11}")
    print(f"{name:14}" + "".join(cells) + f"   {len(r):7d}")
