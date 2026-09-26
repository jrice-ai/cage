#!/usr/bin/env python3
"""Latch confusion from footers: precision, recall, flagged and compromised share of owned
host-steps, and lift over chance, summed over an arm's episodes.

usage: python3 tools_latch_sum.py DIR [DIR ...]      (directories under data/traces or full paths)
Reads latch_tp/fp/fn/own (oracle.py) or tp/fp/fn/own (early capture_hmarl.py) from each footer.
"""
import glob, json, os, sys


def main():
    for d in sys.argv[1:]:
        path = d if os.path.isdir(d) else os.path.join("data", "traces", d)
        tp = fp = fn = own = 0; n = 0
        for f in sorted(glob.glob(os.path.join(path, "ep_*.jsonl"))):
            last = None
            with open(f) as fh:
                for line in fh:
                    if line.strip():
                        last = line
            if not last:
                continue
            try:
                r = json.loads(last)
            except json.JSONDecodeError:
                continue
            if r.get("record") != "footer":
                continue
            if "latch_tp" not in r and "tp" not in r:
                continue
            tp += r.get("latch_tp", r.get("tp", 0)); fp += r.get("latch_fp", r.get("fp", 0))
            fn += r.get("latch_fn", r.get("fn", 0)); own += r.get("latch_own", r.get("own", 0)); n += 1
        name = os.path.basename(path.rstrip("/"))
        if not n or not own or not (tp + fp) or not (tp + fn):
            print(f"{name:18} {n:3} ep  no usable latch footer (tp {tp} fp {fp} fn {fn} own {own})")
            continue
        prec = tp / (tp + fp); rec = tp / (tp + fn); base = (tp + fn) / own
        print(f"{name:18} {n:3} ep  precision {prec:.3f}  recall {rec:.3f}  flagged/step {(tp + fp) / own:.3f}  "
              f"compromised/step {base:.3f}  lift {prec / base:.2f}x")


if __name__ == "__main__":
    main()
