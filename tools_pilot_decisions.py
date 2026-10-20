#!/usr/bin/env python3
"""Decisions per agent-episode at one update of the busy-flag pilot runs, from their logs.

usage: python3 tools_pilot_decisions.py [update] [log ...]
  update  the update whose line is read (default 400)
  logs    default data/kbf_[FN]_s*.log

Each update prints "[e] decisions per agent-episode D, generate ..." with e the update's first episode, so
update u is the line with e = (u - 1) * 5. A resumed run can print an update twice, and the last print is
kept. With the check as shipped an agent's transitions are its decisions, fewer than the episode's steps,
and without it every step is a decision. Prints one line per run and the mean per arm.
"""
import glob, os, re, statistics as st, sys

args = sys.argv[1:]
update = int(args.pop(0)) if args and args[0].isdigit() else 400
logs = args or sorted(glob.glob("data/kbf_[FN]_s*.log"))
e = (update - 1) * 5
by_arm = {}
for path in logs:
    text = open(path, errors="replace").read().replace("\r", "\n")
    hits = re.findall(r"^\[%d\] decisions per agent-episode (-?[0-9.]+)" % e, text, re.M)
    name = os.path.basename(path)[:-4]
    if not hits:
        print(f"{name:14} update {update} not in this log")
        continue
    d = float(hits[-1])
    print(f"{name:14} update {update} decisions per agent-episode {d:.1f}")
    by_arm.setdefault(name.split("_")[1], []).append(d)
for arm, xs in sorted(by_arm.items()):
    print(f"arm {arm} at update {update}: mean decisions per agent-episode {st.mean(xs):.1f} over {len(xs)} runs"
          + (f", sd {st.stdev(xs):.1f}" if len(xs) > 1 else ""))
