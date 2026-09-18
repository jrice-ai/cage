#!/usr/bin/env python3
"""Compare two trace directories footer by footer.

usage: python3 tools_compare_footers.py DIR_A DIR_B [--ignore k1,k2,...]

Reports keys present in only one side, the number of episodes differing on each
shared key, and a verdict on the core keys. Exits 1 on a core difference or when
no footers are found, so it cannot pass vacuously.
"""
import argparse, glob, json, os, sys
from collections import Counter

CORE = ["total_reward", "overrides", "agreements", "deferred", "translator_calls"]


def footers(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl"))):
        last = None
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    last = line
        if last:
            out[os.path.basename(f)] = json.loads(last)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--ignore", default="wall_seconds")
    ns = ap.parse_args()
    ignore = set(filter(None, ns.ignore.split(",")))

    A, B = footers(ns.a), footers(ns.b)
    eps = sorted(set(A) & set(B))
    if not eps:
        sys.exit(f"no shared footers under {ns.a} and {ns.b}")
    ka = set().union(*(A[e].keys() for e in eps))
    kb = set().union(*(B[e].keys() for e in eps))
    print(f"{ns.a} vs {ns.b}: {len(eps)} shared footers "
          f"({len(A)} / {len(B)} present)")
    print("  keys only in A:", sorted(ka - kb) or "none")
    print("  keys only in B:", sorted(kb - ka) or "none")

    per_key = Counter()
    for e in eps:
        for k in (ka & kb) - ignore:
            if A[e][k] != B[e][k]:
                per_key[k] += 1
    print("  episodes differing, by shared key:", dict(sorted(per_key.items())) or "none")

    core = [e for e in eps if any(k in A[e] and k in B[e] and A[e][k] != B[e][k] for k in CORE)]
    if core:
        e = core[0]
        print(f"  CORE keys differ in {len(core)} episodes, e.g. {e}: "
              + ", ".join(f"{k} {A[e].get(k)} vs {B[e].get(k)}" for k in CORE if A[e].get(k) != B[e].get(k)))
        sys.exit(1)
    print("  CORE keys differ in 0 episodes -> IDENTICAL on core")


if __name__ == "__main__":
    main()
