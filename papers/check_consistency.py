#!/usr/bin/env python3
"""Mechanical consistency: figure JSON vs ledger, ledger RESULTS.md line references vs values, the all-arms table vs ARMS.md."""
import csv, json, os, re, glob
L = {r['key']: r for r in csv.DictReader(open('ledger.csv', newline=''))}
CAGE = os.path.expanduser('~/cage')
def close(a, b):
    try: a = float(a); b = float(b)
    except Exception: return str(a) == str(b)
    return abs(a - b) <= 0.5 * 10 ** -min(len((str(b).split('.') + [''])[1]), 3) + 1e-9
bad = 0
# 1. figures
d = json.load(open('fig/drop.json'))
for name, pre in (('KEEP', 'keep'), ('H-MARL', 'hmarl')):
    x = d[name]
    for key, val in [(pre+'execshare', x['fired']['exec']), (pre+'busyattempt', x['fired']['busy']), (pre+'execsharewb', x['held']['exec']),
                     ('dir'+pre+'firedceiling', x['share_fired']), ('dir'+pre+'held', x['share_held']),
                     (pre+'heldvsfired', x['paired_mean']), (pre+'heldvsfiredwins', x['paired_wins']), (pre+'gainfired', x['gain_fired']), (pre+'gainheld', x['gain_held'])]:
        if key not in L: print(f'FIG  no row {key}'); continue
        if not close(val, L[key]['value']): bad += 1; print(f'FIG  {key:24s} figure {val:.4g}  ledger {L[key]["value"]}')
n = json.load(open('fig/noise.json'))
for key, val in [('samplingvarshare', n['stock'][0]), ('samplingvarsharelo', n['stock'][1]), ('samplingvarsharehi', n['stock'][2]),
                 ('samplingvarsharewrecker', n['wrecker'][0]), ('samplingvarsharewreckerlo', n['wrecker'][1]), ('samplingvarsharewreckerhi', n['wrecker'][2]),
                 ('hmarlnullcentre', n['centre']), ('hmarlwreckercontrol', n['draws']['hm_w_none']),
                 ('contsignone', n['continuations']['s1000'][0]), ('contsigntwo', n['continuations']['s1001'][0]), ('contsignthree', n['continuations']['s1002'][0]),
                 ('contsignonewins', n['continuations']['s1000'][1]), ('contsigntwowins', n['continuations']['s1001'][1]), ('contsignthreewins', n['continuations']['s1002'][1])]:
    if key not in L: print(f'FIG  no row {key}'); continue
    if not close(val, L[key]['value']): bad += 1; print(f'FIG  {key:24s} figure {val:.4g}  ledger {L[key]["value"]}')
# 2. RESULTS.md line references
R = open(os.path.join(CAGE, 'RESULTS.md')).read().splitlines()
for k, r in L.items():
    m = re.search(r'RESULTS\.md\s*~?\s*(\d+)(?:\s*(?:-|to|–)\s*(\d+))?(?![\d.])', r['source'] + ' ' + r['note'])
    if not m: continue
    a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
    lo, hi = max(1, a - 15), min(len(R), b + 15)
    text = '\n'.join(R[lo - 1:hi])
    v = r['value']; forms = {v, v.lstrip('-'), v.rstrip('0').rstrip('.') if '.' in v else v}
    try: forms |= {f'{float(v):.1f}', f'{float(v):.2f}', f'{float(v)*100:.1f}', f'{float(v)*100:.0f}'}
    except Exception: pass
    if '.' in v and len(v) >= 5: forms.add(v[:5])
    if not any(f and f in text for f in forms) and not any(close(x, v) for x in re.findall(r'-?\d+\.\d+', text)): bad += 1; print(f'REF  {k:24s} value {v:>10s} not on RESULTS.md {a}-{b} (+-15)')
# 3. the all-arms table vs ARMS.md
A = open(os.path.join(CAGE, 'ARMS.md')).read().splitlines(); rowsn = 0
for line in open('fig/tab_arms.tex'):
    if not line.startswith(r'\texttt'): continue
    cells = [c.strip() for c in line.split('&')]
    arm = cells[0].replace(r'\textunderscore\allowbreak{}', '_').replace(r'\textunderscore', '_').replace(r'\_', '_').replace(r'\allowbreak{}', '')[len(r'\texttt{'):-1]
    mean = cells[5].replace('$-$', '-'); rowsn += 1
    hits = [l for l in A if f'`{arm}`' in l]
    if not hits: bad += 1; print(f'ARMS no line for {arm}'); continue
    if not any(mean in l or f'{float(mean):.1f}' in l for l in hits): bad += 1; print(f'ARMS {arm:44s} all-arms table mean {mean} not on its ARMS.md line(s): {hits[0][:90]}')
print(f'{rowsn} all-arms rows checked against ARMS.md')
print(f'{bad} mismatches')
