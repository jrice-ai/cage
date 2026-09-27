#!/usr/bin/env python3
"""On-disk analysis of investigation arms (O10 / O13), H-MARL or KEEP traces.

usage: python3 tools_investigate.py DIR [DIR ...]

Per directory, from the footers:
  executed investigations per episode, strict-latch yield = flags_new / analyses,
  latch precision and recall from latch_tp / latch_fp / latch_fn when present.

From the step records (overrides whose replacement is an Analyse):
  repeat share            looks at a host this agent already looked at in the episode
  gate flip               H-MARL only: the expert gate was Investigate at the look and
                          Recover at the next step, i.e. the look put an IoC in the
                          agent's own observation; split by first look / repeat look
  response latency        steps from the look to this agent's next Restore or Remove on
                          that host: median, p90, share within 10 and 50 steps, never
  recover-mode latency    H-MARL only: steps to this agent's next executed Recover-mode
                          step
  executed looks          (2026-09-26) a look counts as executed when an Analyse of that host
                          by that agent appears in the executed-action record within three
                          steps (Analyse takes two ticks; a look handed to a busy agent is
                          dropped by CC4); the response latency is then re-reported over
                          executed looks only, measured from the tick the look ran, and for
                          rule-defender arms split by whether the rule's own "strict" Restore
                          of that host followed within three steps (the look found a file)
"""
import glob, json, os, re, sys
from statistics import median


def load(d):
    eps = {}
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        recs = [json.loads(l) for l in open(f) if l.strip()]
        eps[os.path.basename(f)] = recs
    return eps


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def q(xs, p):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def analyse(d):
    eps = load(d)
    if not eps:
        print(f"{d}: no episodes"); return
    foots = [r[-1] for r in eps.values() if r and r[-1].get("record") == "footer"]
    n = len(foots)
    analyses = sum(f.get("analyses", 0) or 0 for f in foots)
    flags = sum(f.get("flags_new", 0) or 0 for f in foots)
    print(f"\n{d}: {n} episodes")
    print(f"  footer: analyses/ep {analyses / n:.1f}, flags_new/ep {flags / n:.2f}, "
          f"yield flags_new/analyses {flags / analyses if analyses else float('nan'):.3f}")
    g = lambda f, k: f.get("latch_" + k, f.get(k, 0)) or 0     # oracle.py names them latch_*, early capture_hmarl traces tp/fp/fn
    tp = sum(g(f, "tp") for f in foots)
    fp = sum(g(f, "fp") for f in foots)
    fn = sum(g(f, "fn") for f in foots)
    if tp + fp + fn:
        print(f"  latch: tp {tp} fp {fp} fn {fn}  precision {tp / (tp + fp) if tp + fp else float('nan'):.3f}  "
              f"recall {tp / (tp + fn) if tp + fn else float('nan'):.3f}")

    inv = []          # dicts per executed investigation
    has_mode = False
    for name, recs in eps.items():
        steps = [r for r in recs if r.get("record") == "step"]
        if not steps:
            continue
        by_t = {s.get("step", s.get("t", i)): s for i, s in enumerate(steps)}
        T = max(by_t)
        akey = next((k for k in ("actions", "action", "executed") if k in steps[0]), None)
        has_mode = has_mode or ("mode" in steps[0])
        seen = {}
        for t in sorted(by_t):
            s = by_t[t]
            for o in s.get("overrides", []) or []:
                agent, frm, to = o[0], o[1], o[2]
                if not str(to).startswith("Analyse:"):
                    continue
                host = str(to).split(":", 1)[1]
                k = (agent, host)
                rec = {"ep": name, "agent": agent, "host": host, "t": t,
                       "repeat": k in seen, "gate_t": None, "gate_t1": None,
                       "resp": None, "recov": None, "exec": None, "found": False}
                apat = re.compile(r"Analyse\s+" + re.escape(host) + r"(?!\w)")
                for u in range(t, min(T, t + 3) + 1):
                    su = by_t.get(u)
                    if su is not None and akey and apat.search(str(su.get(akey, {}).get(agent, ""))):
                        rec["exec"] = u - t; break
                if rec["exec"] is not None:
                    for u in range(t + rec["exec"] + 1, min(T, t + rec["exec"] + 3) + 1):
                        su = by_t.get(u)
                        if su and any(x[0] == agent and x[1] == "strict" and x[2] == host for x in (su.get("defender") or [])):
                            rec["found"] = True; break
                seen[k] = seen.get(k, 0) + 1
                if "expert_mode" in s:
                    rec["gate_t"] = s["expert_mode"].get(agent)
                    nxt = by_t.get(t + 1)
                    rec["gate_t1"] = nxt["expert_mode"].get(agent) if nxt and "expert_mode" in nxt else None
                pat = re.compile(r"(Restore|Remove)\s+" + re.escape(host) + r"(?!\w)")
                for u in range(t + 1, T + 1):
                    su = by_t.get(u)
                    if su is None:
                        continue
                    if rec["resp"] is None and akey and pat.search(str(su.get(akey, {}).get(agent, ""))):
                        rec["resp"] = u - t
                    if rec["recov"] is None and "mode" in su and su["mode"].get(agent) == "recover":
                        rec["recov"] = u - t
                    if rec["resp"] is not None and (rec["recov"] is not None or "mode" not in su):
                        break
                inv.append(rec)

    if not inv:
        print("  steps: no attempted investigations in the step records"); return
    N = len(inv)
    rep = [r for r in inv if r["repeat"]]
    first = [r for r in inv if not r["repeat"]]
    print(f"  steps: {N} attempted investigations (overrides handed to the agent), {N / n:.1f}/ep, repeat share {pct(len(rep), N):.1f}%")

    if any(r["gate_t"] is not None for r in inv):
        def flip(rs):
            el = [r for r in rs if r["gate_t"] == "investigate" and r["gate_t1"] is not None]
            f = sum(1 for r in el if r["gate_t1"] == "recover")
            return f, len(el)
        fa, na = flip(inv); ff, nf = flip(first); fr, nr = flip(rep)
        already = sum(1 for r in inv if r["gate_t"] == "recover")
        print(f"  gate: already Recover at the look {pct(already, N):.1f}%; "
              f"flip Investigate->Recover at next step {pct(fa, na):.1f}% of {na} "
              f"(first looks {pct(ff, nf):.1f}% of {nf}, repeat looks {pct(fr, nr):.1f}% of {nr})")

    resp = [r["resp"] for r in inv if r["resp"] is not None]
    never = N - len(resp)
    print(f"  response over attempts (Restore/Remove on that host by that agent): median {median(resp) if resp else float('nan'):.0f}, "
          f"p90 {q(resp, 0.9):.0f}, within 10 {pct(sum(1 for x in resp if x <= 10), N):.1f}%, "
          f"within 50 {pct(sum(1 for x in resp if x <= 50), N):.1f}%, never {pct(never, N):.1f}%")
    ex = [r for r in inv if r["exec"] is not None]
    if ex:
        er = [r["resp"] - r["exec"] for r in ex if r["resp"] is not None]
        print(f"  executed looks: {len(ex)} of {N} ({pct(len(ex), N):.1f}%), {len(ex) / n:.1f}/ep; response from the tick the look ran: "
              f"median {median(er) if er else float('nan'):.0f}, p90 {q(er, 0.9):.0f}, within 10 {pct(sum(1 for x in er if x <= 10), len(ex)):.1f}%, "
              f"within 50 {pct(sum(1 for x in er if x <= 50), len(ex)):.1f}%, never {pct(len(ex) - len(er), len(ex)):.1f}%")
        dr = [r for r in inv if r["exec"] is None]
        dn = sum(1 for r in dr if r["resp"] is None)
        print(f"  dropped looks: {len(dr)}; host later recovered by that agent anyway {pct(len(dr) - dn, len(dr)):.1f}%")
        fd = [r for r in ex if r["found"]]
        if fd:
            nf_ = [r for r in ex if not r["found"]]
            for lab, rs in (("look found a file (rule's strict Restore followed)", fd), ("look found nothing", nf_)):
                rr = [r["resp"] - r["exec"] for r in rs if r["resp"] is not None]
                print(f"    {lab}: n {len(rs)} ({pct(len(rs), len(ex)):.1f}% of executed), response median {median(rr) if rr else float('nan'):.0f}, "
                      f"within 10 {pct(sum(1 for x in rr if x <= 10), len(rs)):.1f}%, never {pct(len(rs) - len(rr), len(rs)):.1f}%")
    if has_mode:
        rec_ = [r["recov"] for r in inv if r["recov"] is not None]
        print(f"  recover mode (next executed Recover-mode step by that agent): median {median(rec_) if rec_ else float('nan'):.0f}, "
              f"within 1 {pct(sum(1 for x in rec_ if x <= 1), N):.1f}%, within 10 {pct(sum(1 for x in rec_ if x <= 10), N):.1f}%, "
              f"never {pct(N - len(rec_), N):.1f}%")
        # response conditioned on the gate flipping
        fl = [r for r in inv if r["gate_t"] == "investigate" and r["gate_t1"] == "recover"]
        nf_ = [r for r in inv if r["gate_t"] == "investigate" and r["gate_t1"] == "investigate"]
        for lab, rs in (("look landed (gate flipped)", fl), ("look missed (gate stayed)", nf_)):
            if rs:
                w50 = sum(1 for r in rs if r["resp"] is not None and r["resp"] <= 50)
                nv = sum(1 for r in rs if r["resp"] is None)
                print(f"    {lab}: n {len(rs)}, host recovered within 50 {pct(w50, len(rs)):.1f}%, never {pct(nv, len(rs)):.1f}%")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        analyse(d)
