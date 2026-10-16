#!/usr/bin/env python3
"""Per-episode directive counts from traces captured with scripts/oracle.py --log-policy.

usage: python3 tools_busy_restores.py data/traces/<arm> [data/traces/<arm> ...]

For each arm, mean and sd over its episodes of
  reward              the episode's total reward
  busy agent-steps    steps that began with the agent's action in progress (CybORG drops the new one)
  sent at busy        busy agent-steps where the policy sent an action (null means it declined)
  Restores at busy    policy Restores sent to a busy agent, each dropped and charged -1
  Restores at free    policy Restores sent to a free agent
  declined at free    free agent-steps where the policy declined. Should be 0 in every arm, since KEEP
                      declines only when its busy flag is set and the flag tracks the controller.
"""
import glob, json, os, statistics as st, sys

ROWS = ["reward", "busy agent-steps", "sent at busy", "Restores at busy", "Restores at free", "declined at free"]


def episode(path):
    head, foot, c = None, None, dict.fromkeys(ROWS[1:], 0)
    for line in open(path):
        r = json.loads(line)
        kind = r.get("record")
        if kind == "header":
            head = r
        elif kind == "footer":
            foot = r
        elif kind == "step":
            if "policy" not in r:
                sys.exit(f"{path}: step records carry no policy field (capture with --log-policy)")
            busy = set(r["busy"])
            for agent, act in r["policy"].items():
                restore = act is not None and act.startswith("Restore")
                if agent in busy:
                    c["busy agent-steps"] += 1
                    c["sent at busy"] += act is not None
                    c["Restores at busy"] += restore
                else:
                    c["Restores at free"] += restore
                    c["declined at free"] += act is None
    if head is None or foot is None:
        sys.exit(f"{path}: missing header or footer")
    c["reward"] = foot["total_reward"]
    return head, c


def main(dirs):
    for d in dirs:
        files = sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))
        if not files:
            sys.exit(f"{d}: no ep_*.jsonl files")
        eps = [episode(f) for f in files]
        heads = {(h.get("busy"), h.get("weights"), h.get("red_agent"), h.get("rule")) for h, _ in eps}
        if len(heads) != 1:
            sys.exit(f"{d}: episodes disagree on busy, weights, red agent or rule: {sorted(heads, key=str)}")
        busy, weights, red, rule = heads.pop()
        print(f"{os.path.basename(os.path.normpath(d))}  busy {busy}  weights {weights}  red {red}  rule {rule}  "
              f"episodes {len(eps)}")
        for row in ROWS:
            xs = [c[row] for _, c in eps]
            sd = st.stdev(xs) if len(xs) > 1 else 0.0
            print(f"  {row:<18} mean {st.mean(xs):9.2f}  sd {sd:8.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
