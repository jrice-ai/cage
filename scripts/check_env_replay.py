"""Does KEEP's trainer replay the same environments every update? Builds the environments as
repos/cage-4-submission/train.py does (all on one seed as shipped, or seed + i as the harness default),
ships them to loky workers the way the trainer's Parallel call does each update, and prints the network
layout (an md5 of the sorted host names, and the host count) each episode starts from.

usage, inside cage-keep:dev:  python3 /work/scripts/check_env_replay.py
"""
import hashlib, sys
sys.path.insert(0, "/opt/cage/cage-4-submission")
from joblib import Parallel, delayed
from CybORG import CybORG
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from wrapper.graph_wrapper import GraphWrapper

W = 4   # environments and episodes per update; the trainer uses 25


def layout(env):
    env.reset()
    hosts = sorted(env.env.environment_controller.state.hosts)
    return hashlib.md5(" ".join(hosts).encode()).hexdigest()[:8], len(hosts)


def build(seeds):
    out = []
    for s in seeds:
        sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, green_agent_class=EnterpriseGreenAgent,
                                         red_agent_class=FiniteStateRedAgent, steps=500)
        out.append(GraphWrapper(CybORG(sg, "sim", seed=s)))
    return out


for name, seeds in (("one seed (shipped)", [1337] * W), ("seed + i", [1337 + i for i in range(W)])):
    envs = build(seeds)
    seen = []
    for update in range(3):
        res = Parallel(prefer="processes", n_jobs=W)(delayed(layout)(envs[i % len(envs)]) for i in range(W))
        seen += res
        print(f"{name:18}  update {update}  " + "  ".join(f"{h}/{n}" for h, n in res), flush=True)
    print(f"{name:18}  distinct layouts in 3 updates of {W} episodes: {len(set(seen))}", flush=True)
live = build([1337])[0]
print("one environment reset in place 3 times: " + "  ".join(f"{h}/{n}" for h, n in (layout(live) for _ in range(3))))
