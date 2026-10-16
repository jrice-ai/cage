#!/usr/bin/env python3
"""Split a paired difference into the Restore charge and the rest, for arms captured with
scripts/oracle.py --log-policy.

usage: python3 tools_busy_charge.py CONTROL_DIR ARM_DIR

CybORG charges -1 for every Restore the caller passes, executed or dropped (SimulationController.step
sums the cost over the actions passed), and Restore is the only action with a cost. Each step record's
"policy" field is what was passed for each agent, so an episode's charge is minus the number of
Restores in it. Episodes are paired by file name (same environment seed). Prints the mean paired
difference in reward, in charge and in the rest (reward minus charge), each with a seeded
10,000-draw bootstrap 95% interval over episodes, and the Restores passed per episode in each arm,
split by whether the agent was busy.
"""
import glob, json, os, random, sys


def episode(path):
    sent = busy_sent = 0
    reward = None
    rule = None
    for line in open(path):
        r = json.loads(line)
        if r.get("record") == "header":
            rule = r.get("rule")
        elif r.get("record") == "step":
            if "policy" not in r:
                sys.exit(f"{path}: no policy field (capture with --log-policy)")
            busy = set(r["busy"])
            for agent, act in r["policy"].items():
                if act is not None and act.startswith("Restore"):
                    sent += 1
                    busy_sent += agent in busy
        elif r.get("record") == "footer":
            reward = r["total_reward"]
    if reward is None:
        sys.exit(f"{path}: no footer")
    if rule != "none":
        sys.exit(f"{path}: rule {rule}. A supervisor rule can replace what the policy passed, so this split needs rule none")
    return reward, sent, busy_sent


def arm(d):
    eps = {os.path.basename(f): episode(f) for f in sorted(glob.glob(os.path.join(d, "ep_*.jsonl")))}
    if not eps:
        sys.exit(f"{d}: no ep_*.jsonl files")
    return eps


def boot(xs, draws=10000, seed=0):
    rng = random.Random(seed)
    n = len(xs)
    means = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return means[int(0.025 * draws)], means[int(0.975 * draws) - 1]


def main(cdir, adir):
    c, a = arm(cdir), arm(adir)
    keys = sorted(set(c) & set(a))
    if len(keys) != len(c) or len(keys) != len(a):
        print(f"note: pairing {len(keys)} episodes ({len(c)} in control, {len(a)} in arm)")
    for name, eps in ((os.path.basename(os.path.normpath(cdir)), c), (os.path.basename(os.path.normpath(adir)), a)):
        n = len(keys)
        print(f"{name:32} reward {sum(eps[k][0] for k in keys) / n:9.2f}  Restores passed {sum(eps[k][1] for k in keys) / n:7.2f}"
              f"  of them to busy agents {sum(eps[k][2] for k in keys) / n:7.2f}")
    rows = {
        "reward difference": [a[k][0] - c[k][0] for k in keys],
        "charge difference": [-(a[k][1] - c[k][1]) for k in keys],
    }
    rows["rest"] = [d - g for d, g in zip(rows["reward difference"], rows["charge difference"])]
    for label, xs in rows.items():
        lo, hi = boot(xs)
        print(f"  {label:18} {sum(xs) / len(xs):8.2f}  ci95 [{lo:.2f}, {hi:.2f}]")
    d = sum(rows["reward difference"])
    if d:
        print(f"  charge share of the difference {sum(rows['charge difference']) / d:.3f}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
