#!/usr/bin/env python3
"""The engagement gate's arms against a control, a reference supervisor and the ceiling. Pure Python.

usage: python3 tools_gate.py --ceiling RT_DIR --control CTL_DIR [--ref O1_DIR] ARM_DIR [ARM_DIR ...] [--n N]

Paired on shared episode file names (the first N if --n is given). Per arm: mean score, delta
against the control and against the reference, interventions per episode (overrides accepted by
the gap floor), deferred, the gate's bookkeeping (eng: agent-ticks with the gate open; hit: of
those, with a compromised owned host; quiet: gate shut while a host was compromised), the share
of the distance from the control to the ceiling closed, and that share per intervention.
Directory names may be bare (looked up under data/traces).
"""
import glob, json, os, sys


def foot(d, n=None):
    d = d if os.path.isdir(d) else os.path.join("data", "traces", d)
    out = {}
    files = sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))
    if n:
        files = files[:n]
    for f in files:
        last = None
        for l in open(f):
            if l.strip():
                last = l
        if not last:
            continue
        try:
            r = json.loads(last)
        except json.JSONDecodeError:
            continue
        if r.get("record") == "footer":
            out[os.path.basename(f)] = r
    if files and len(out) < len(files):
        print(f"warning: {os.path.basename(d.rstrip('/'))}: {len(out)} footers in {len(files)} files, a partial arm", file=sys.stderr)
    return out


def m(d, k, eps):
    return sum(d[e].get(k, 0) for e in eps) / len(eps)


def main():
    argv = sys.argv[1:]; n = None; ceil = ctl = ref = None
    for flag in ("--ceiling", "--control", "--ref", "--n"):
        if flag in argv:
            i = argv.index(flag); v = argv[i + 1]; del argv[i:i + 2]
            if flag == "--ceiling": ceil = v
            elif flag == "--control": ctl = v
            elif flag == "--ref": ref = v
            else: n = int(v)
    if not (ceil and ctl and argv):
        sys.exit(__doc__)
    R, C = foot(ceil, n), foot(ctl, n)
    O = foot(ref, n) if ref else {}
    base = set(R) & set(C) & (set(O) if ref else set(R))
    eps = sorted(base)
    print(f"{'arm':34} {'n':>3} {'mean':>8} {'d.ctl':>7} {'d.ref':>7} {'ovr':>5} {'def':>6} {'eng':>6} {'hit':>6} {'quiet':>6} {'closed':>7} {'per ovr':>8}")
    print(f"{'control ' + os.path.basename(ctl.rstrip('/')):34} {len(eps):3} {m(C, 'total_reward', eps):8.1f}")
    gap = m(R, 'total_reward', eps) - m(C, 'total_reward', eps)
    if ref:
        d = m(O, 'total_reward', eps) - m(C, 'total_reward', eps); ov = m(O, 'overrides', eps)
        print(f"{'ref ' + os.path.basename(ref.rstrip('/')):34} {len(eps):3} {m(O, 'total_reward', eps):8.1f} {d:+7.1f} {'':7} {ov:5.1f} {m(O, 'deferred', eps):6.1f} {'':6} {'':6} {'':6} {d / gap if gap else float('nan'):7.3f} {d / gap / ov if gap and ov else float('nan'):8.4f}")
    print(f"{'ceiling ' + os.path.basename(ceil.rstrip('/')):34} {len(eps):3} {m(R, 'total_reward', eps):8.1f}")
    for arm in argv:
        A = foot(arm, n)
        e = sorted(base & set(A))
        if not e:
            print(f"{os.path.basename(arm.rstrip('/')):34} no shared episodes"); continue
        g = m(R, 'total_reward', e) - m(C, 'total_reward', e)
        d = m(A, 'total_reward', e) - m(C, 'total_reward', e); ov = m(A, 'overrides', e)
        dr = m(A, 'total_reward', e) - m(O, 'total_reward', e) if ref else float('nan')
        print(f"{os.path.basename(arm.rstrip('/')):34} {len(e):3} {m(A, 'total_reward', e):8.1f} {d:+7.1f} {dr:+7.1f} {ov:5.1f} {m(A, 'deferred', e):6.1f} "
              f"{m(A, 'engaged', e):6.0f} {m(A, 'engaged_hit', e):6.0f} {m(A, 'quiet_comp', e):6.0f} {d / g if g else float('nan'):7.3f} {d / g / ov if g and ov else float('nan'):8.4f}")


if __name__ == "__main__":
    main()
