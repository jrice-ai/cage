#!/usr/bin/env python3
"""Footer means for arms. usage: python3 means.py ARM [ARM ...]"""
import glob, json, os, sys
for a in sys.argv[1:]:
    d = a if os.path.isdir(a) else os.path.join("data", "traces", a)
    xs = []
    sc = os.path.join(d, "scores.txt")
    if not glob.glob(os.path.join(d, "ep_*.jsonl")) and os.path.exists(sc):   # the H-MARL evaluator's summary file
        kv = dict(l.split(":", 1) for l in open(sc) if ":" in l)
        print(f"{os.path.basename(d):40} evaluator summary  mean {float(kv['reward_mean']):10.2f}  sd {float(kv['reward_stdev']):8.2f}")
        continue
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        last = [l for l in open(f) if l.strip()][-1]
        rec = json.loads(last)
        if rec.get("record") == "footer": xs.append(rec["total_reward"])
    m = sum(xs) / len(xs) if xs else float("nan")
    sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5 if len(xs) > 1 else float("nan")
    print(f"{os.path.basename(d):40} n {len(xs):3}  mean {m:10.2f}  sd {sd:8.2f}  min {min(xs) if xs else float('nan'):9.1f}  max {max(xs) if xs else float('nan'):9.1f}")

# summary over the arms given, for ledger rows that cite a grand mean or a null centre
import statistics as _st
_ms = []
for _a in sys.argv[1:]:
    _d = _a if os.path.isdir(_a) else os.path.join("data", "traces", _a)
    _sc = os.path.join(_d, "scores.txt")
    if not glob.glob(os.path.join(_d, "ep_*.jsonl")) and os.path.exists(_sc):
        _ms.append(float(dict(l.split(":", 1) for l in open(_sc) if ":" in l)["reward_mean"])); continue
    _xs = [json.loads([l for l in open(_f) if l.strip()][-1])["total_reward"] for _f in sorted(glob.glob(os.path.join(_d, "ep_*.jsonl")))]
    _xs = [x for x in _xs if isinstance(x, (int, float))]
    if _xs: _ms.append(sum(_xs) / len(_xs))
if len(_ms) > 1:
    _g = _st.mean(_ms); _sd = _st.stdev(_ms); _se = _sd / len(_ms) ** 0.5
    print(f"grand mean {_g:.2f}  sd of means {_sd:.2f}  se {_se:.2f}  first arm minus grand mean {_ms[0]-_g:.2f}  n arms {len(_ms)}")
    _t = {2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}.get(len(_ms) - 1)
    if _t: print(f"95% t interval, {len(_ms)-1} df (t {_t}): [{_g - _t*_se:.2f}, {_g + _t*_se:.2f}]  half-width {_t*_se:.2f}")
