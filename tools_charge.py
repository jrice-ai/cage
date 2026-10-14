#!/usr/bin/env python3
"""How much of a score, or of a paired difference, is the simulator's charge for Restore directives.

CybORG charges the team one point for every Restore asserted, whether it runs or is dropped because the agent was busy
(SimulationController.step sums action costs over the caller's actions, and Restore.cost is -1, see tools_billing.py).
A Restore is charged once when asserted, so the charge an arm paid in an episode is the number of Restores executed
plus the number of Restore interventions that never executed, under the exact rule of tools_dropped.py (an accepted
directive completes at t + d - 1). KEEP and H-MARL never assert a Restore at a busy agent, since both read the busy
flag. Four things are charged and not counted here. A rule defender delivered fired asserts its own Restores at busy
agents too, and those that are dropped are missed. A defender's own Restore that the controller replaces as invalid
is missed (a recorded intervention replaced as invalid is counted). Interventions in arms captured before the
per-step overrides field are missed. And a defender's own Restore still running when the episode ends is missed, at
most one per agent per episode (an intervention still running then is counted as never executed).

For a rule defender the footer also counts the Restores the rule proposed (defender_restores, from 2026-09-26),
under fired delivery including those proposed at busy agents. An intervention can replace a proposal, and the
override's "from" entry names it, so the rule's own Restores asserted are the proposals less the Restore proposals
the interventions replaced. Describe mode prints all three when every footer carries the key and at least one count
is nonzero, and says how many footers lack the key when others carry a nonzero count. It prints nothing about a rule
defender when no footer carries a nonzero count.

usage
  python3 tools_charge.py ARM                  per-episode means for one arm
  python3 tools_charge.py BASE OTHER           both arms, then OTHER minus BASE paired by episode, split into the
                                               charge part and the rest, each with the seeded 10,000-draw bootstrap
                                               interval of tools_paired.py, and the number of paired episodes on
                                               which the two arms executed exactly the same actions
Arms are directories under data/traces, or paths.
"""
import glob, hashlib, json, os, random, sys

DUR = {"Restore": 5, "Remove": 3, "Analyse": 2, "DeployDecoy": 2}


def _acts(r):
    return r.get("action") or r.get("actions") or {}


def _executed_at(steps, i, agent, typ, host):
    k = DUR.get(typ, 1) - 1
    if i + k >= len(steps):
        return False
    a = _acts(steps[i + k]).get(agent, "")
    return a.startswith(f"[{typ} {host}") or (host == "" and a.startswith(f"[{typ}"))


def arm(d):
    d = d if os.path.isdir(d) else os.path.join("data", "traces", d)
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        rows = [json.loads(l) for l in open(f) if l.strip()]
        if not rows or rows[-1].get("record") != "footer":
            continue
        steps = [r for r in rows if r.get("record") == "step"]
        executed = sum(1 for r in steps for a in _acts(r).values() if str(a).startswith("[Restore"))
        asserted = never = 0
        for i, r in enumerate(steps):
            for agent, _frm, to in r.get("overrides", []):
                typ, _, host = to.partition(":")
                if typ == "Restore":
                    asserted += 1
                    never += not _executed_at(steps, i, agent, typ, host)
        seq = hashlib.md5(json.dumps([_acts(r) for r in steps], sort_keys=True).encode()).hexdigest()
        replaced = sum(1 for r in steps for _agent, frm, _to in r.get("overrides", []) if str(frm).startswith("Restore"))
        prop = rows[-1].get("defender_restores")
        out[os.path.basename(f)] = {"score": float(rows[-1]["total_reward"]), "executed": executed,
                                    "interventions": asserted, "never": never, "charged": executed + never, "seq": seq,
                                    "proposed": None if prop is None else float(prop), "replaced": replaced}
    return out


def _mean(v):
    return sum(v) / len(v)


def _interval(v):
    rng = random.Random(0)
    n = len(v)
    boots = sorted(_mean(rng.choices(v, k=n)) for _ in range(10000))
    return boots[250], boots[9749]


def describe(name, e):
    v = list(e.values())
    m = {k: _mean([x[k] for x in v]) for k in ("score", "executed", "interventions", "never", "charged")}
    props = [x["proposed"] for x in v]
    tail = ""
    if any(props):
        missing = sum(1 for p in props if p is None)
        if missing:
            tail = f", rule defender's footer count missing in {missing} of {len(v)} episodes"
        else:
            mp, mr = _mean(props), _mean([x["replaced"] for x in v])
            tail = (f", rule defender's own Restores proposed {mp:.1f} per episode, {mr:.1f} of them replaced by "
                    f"interventions, {mp - mr:.1f} asserted")
    print(f"{os.path.basename(name.rstrip('/'))}, {len(v)} episodes, score {m['score']:.2f}, Restores executed "
          f"{m['executed']:.1f} per episode, Restore interventions {m['interventions']:.1f} of which {m['never']:.1f} "
          f"never executed, charged {m['charged']:.1f}, charge share of score {m['charged'] / -m['score']:.3f}{tail}")


def compare(a_name, A, b_name, B):
    common = sorted(set(A) & set(B))
    ds = [B[k]["score"] - A[k]["score"] for k in common]
    dc = [A[k]["charged"] - B[k]["charged"] for k in common]
    rest = [s - c for s, c in zip(ds, dc)]
    same = sum(1 for k in common if A[k]["seq"] == B[k]["seq"])
    cells = []
    for label, v in (("score difference", ds), ("charge part", dc), ("rest", rest)):
        lo, hi = _interval(v)
        cells.append(f"{label} {_mean(v):.1f} ({lo:.1f} to {hi:.1f})")
    share = _mean(dc) / _mean(ds) if _mean(ds) else float("nan")
    print(f"{os.path.basename(b_name.rstrip('/'))} minus {os.path.basename(a_name.rstrip('/'))}, "
          f"{len(common)} paired episodes, {', '.join(cells)}, charge share {share:.3f}, "
          f"executed actions identical on {same} of {len(common)} paired episodes")


def main():
    argv = sys.argv[1:]
    if len(argv) not in (1, 2):
        sys.exit(__doc__)
    arms = [arm(a) for a in argv]
    for a, e in zip(argv, arms):
        if not e:
            sys.exit(f"{a}: no complete episodes")
        describe(a, e)
    if len(argv) == 2:
        compare(argv[0], arms[0], argv[1], arms[1])


if __name__ == "__main__":
    main()
