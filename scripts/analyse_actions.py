import re, sys
from collections import Counter, defaultdict
from statistics import mean

PAIR = re.compile(r"'(blue_agent_\d)':\s*\[([^\]]*)\]")
BLOCK = re.compile(r"\{[^{}]*\}")

def load(path):
    raw = open(path).read()
    episodes = []
    for chunk in raw.split("actions:"):
        if "blue_agent" not in chunk:
            continue
        steps = []
        for b in BLOCK.findall(chunk):
            d = dict(PAIR.findall(b))
            if d:
                steps.append(d)
        if steps:
            episodes.append(steps)
    return episodes

def analyse(path):
    eps = load(path)
    agents = sorted(eps[0][0].keys())
    repeats, hosts, acts = defaultdict(list), defaultdict(list), defaultdict(list)
    verbs = Counter()
    for ep in eps:
        for a in agents:
            seq = [s.get(a, "") for s in ep]
            rep = sum(1 for i in range(1, len(seq)) if seq[i] == seq[i-1])
            repeats[a].append(rep / max(1, len(seq) - 1))
            hosts[a].append(len({x.split(" ", 1)[1] for x in seq if " " in x}))
            acts[a].append(len(set(seq)))
            verbs.update(x.split(" ", 1)[0] for x in seq if x)
    total = sum(verbs.values())
    return eps, agents, repeats, hosts, acts, verbs, total

def report(label, path):
    eps, agents, repeats, hosts, acts, verbs, total = analyse(path)
    print(f"\n=== {label} ===")
    print(f"episodes {len(eps)}  steps/ep {len(eps[0])}  agent-steps {total}")
    print(f"{'agent':<14}{'repeat%':>9}{'hosts/ep':>10}{'actions/ep':>12}")
    for a in agents:
        print(f"{a:<14}{100*mean(repeats[a]):>8.1f}%{mean(hosts[a]):>10.1f}{mean(acts[a]):>12.1f}")
    print(f"{'MEAN':<14}"
          f"{100*mean(mean(repeats[a]) for a in agents):>8.1f}%"
          f"{mean(mean(hosts[a]) for a in agents):>10.1f}"
          f"{mean(mean(acts[a]) for a in agents):>12.1f}")
    print("action mix:")
    for v, c in verbs.most_common():
        print(f"  {v:<20}{100*c/total:>6.2f}%  ({c})")

for label, path in [("SAMPLED", sys.argv[1]), ("GREEDY", sys.argv[2])]:
    report(label, path)
