#!/usr/bin/env python3
"""Run every distinct cmd in a ledger.csv from $CAGE and check that each row's value appears in that
command's output. usage: python3 recompute_check.py paper1/ledger.csv [--only KEY,KEY]"""
import csv, os, re, subprocess, sys
ledger = sys.argv[1]
only = set(sys.argv[sys.argv.index('--only')+1].split(',')) if '--only' in sys.argv else None
cage = os.environ.get('CAGE', os.path.expanduser('~/cage'))
rows = [r for r in csv.DictReader(open(ledger)) if r.get('cmd') and not r['cmd'].startswith(('derived','cited','parameter','container'))]
if only: rows = [r for r in rows if r['key'] in only]
by_cmd = {}
for r in rows: by_cmd.setdefault(r['cmd'], []).append(r)
out_cache = {}
ok = bad = 0
for cmd, rs in by_cmd.items():
    if cmd not in out_cache:
        p = subprocess.run(cmd, shell=True, cwd=cage, capture_output=True, text=True)
        out_cache[cmd] = p.stdout + p.stderr
    out = out_cache[cmd]
    for r in rs:
        v = r['value'].strip()
        forms = {v, '+'+v.lstrip('+'), v.lstrip('-'), f"{float(v):.1f}" if re.fullmatch(r'-?\d+(\.\d+)?', v) else v,
                 f"{float(v):.2f}" if re.fullmatch(r'-?\d+(\.\d+)?', v) else v, f"{float(v):.3f}" if re.fullmatch(r'-?\d+(\.\d+)?', v) else v}
        hit = any(f and f in out for f in forms)
        ok += hit; bad += (not hit)
        print(f"{'ok  ' if hit else 'MISS'} {r['key']:28} {v:>18}   {cmd[:70]}")
print(f"\n{ok} matched, {bad} not found, {len(by_cmd)} commands run")
