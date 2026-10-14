#!/usr/bin/env python3
"""Whether CybORG charges a team for a directive it discards.

SimulationController.step stores a new action for an agent only when that agent has no action in progress and drops
it otherwise, but it computes the team's action_cost term from the actions the caller passed in. This script prints
the cost of each blue action class, then runs the same seed twice. Run A asserts one Restore for blue_agent_0 at step 0
and nothing after. Run B asserts the same Restore at every step. The Restore takes five steps, so run B's directives at
steps 1 to 4 reach a busy agent and are dropped, and both runs execute the same actions through step 4. Any difference in
reward at those steps is the charge for directives that never ran. Run B is then repeated through BlueFlatWrapper, the
interface the challenge documents, with the Restore asserted by its action index as a submission would.

With --keep N it also runs KEEP unsupervised for N episodes and checks that the team's summed action cost equals minus
the number of Restores KEEP started, executed or still running at the end, which is what a defender that waits for its
agents is charged.

Run inside either image, for example  bin/run cage-keep:dev bash -c "python3 -u /work/tools_billing.py"
Options  --seed N (default 0), --steps N (default 8), --keep N (cage-keep image only, default 0).
"""
import argparse, importlib, inspect, pkgutil, sys

import CybORG as cyborg_pkg
from CybORG import CybORG, CYBORG_VERSION
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Agents.Wrappers import BlueFlatWrapper
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Simulator.Actions import Action, Restore

AGENT = "blue_agent_0"
BLUE_ACTIONS = ("Sleep", "Monitor", "Analyse", "Remove", "Restore", "DeployDecoy",
                "BlockTrafficZone", "AllowTrafficZone", "InvalidAction")


def costs():
    import CybORG.Simulator.Actions as A
    found = {}
    for m in pkgutil.walk_packages(A.__path__, A.__name__ + "."):
        try:
            mod = importlib.import_module(m.name)
        except Exception:
            continue
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if name in BLUE_ACTIONS and issubclass(cls, Action) and cls.__module__ == mod.__name__:
                found[name] = cls
    out = []
    for name in BLUE_ACTIONS:
        cls = found.get(name)
        if cls is None:
            out.append(f"{name} missing")
            continue
        owner = next((k for k in cls.__mro__ if "cost" in k.__dict__), None)
        attr = owner.__dict__["cost"] if owner else None
        try:
            c = attr.fget(None) if isinstance(attr, property) else attr
        except Exception as e:
            c = f"unreadable {type(e).__name__}"
        out.append(f"{name} {c}" + ("" if owner is cls else f" (from {owner.__name__})"))
    return out


def make(seed):
    sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, green_agent_class=EnterpriseGreenAgent,
                                     red_agent_class=FiniteStateRedAgent, steps=500)
    return CybORG(sg, "sim", seed=seed)


def raw_run(seed, steps, every, host):
    env = make(seed)
    env.reset()
    ec = env.environment_controller
    team = next(t for t, members in ec.team.items() if AGENT in members)
    rows = []
    for t in range(steps):
        busy = ec.actions_in_progress.get(AGENT) is not None
        acts = {AGENT: Restore(session=0, agent=AGENT, hostname=host)} if (every or t == 0) else {}
        env.parallel_step(acts)
        r = ec.reward[team]
        rows.append({"busy": busy, "asserted": AGENT in acts, "executed": str(env.get_last_action(AGENT)),
                     "cost": float(r.get("action_cost", 0.0)), "reward": float(sum(r.values()))})
    return rows


def wrapped_run(seed, steps, every):
    env = BlueFlatWrapper(env=make(seed))
    env.reset()
    labels = env.action_labels(AGENT)
    idx = next(k for k, lab in enumerate(labels) if lab.startswith("Restore "))
    sleep = labels.index("Sleep")
    rewards = []
    for t in range(steps):
        _, rew, _, _, _ = env.step(actions={AGENT: idx if (every or t == 0) else sleep})
        rewards.append(float(rew[AGENT]))
    return labels[idx].split(" ", 1)[1], rewards


def keep_check(episodes, seed0):
    """Run KEEP unsupervised and compare the team's summed action cost with its Restores, executed or still running."""
    import os, random
    sys.path.insert(0, "/opt/cage/cage-4-submission")
    os.chdir("/opt/cage/cage-4-submission")
    import numpy as np, torch
    from submission import Submission
    blue = [f"blue_agent_{i}" for i in range(5)]
    for ep in range(episodes):
        seed = seed0 + ep
        torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
        cyborg = make(seed)
        env = Submission.wrap(cyborg)
        agents = Submission.AGENTS
        obs, _ = env.reset()
        for ag in agents.values():
            if hasattr(ag, "reset"):
                ag.reset()
        ec = cyborg.environment_controller
        team = next(t for t, members in ec.team.items() if AGENT in members)
        score = cost = 0.0
        executed = 0
        for t in range(500):
            actions = {n: agents[n].get_action(obs[n], env.action_space(n)) for n in blue}
            obs, rew, term, trunc, _ = env.step(actions)
            score += float(rew[AGENT])
            cost += float(ec.reward[team].get("action_cost", 0.0))
            executed += sum(1 for n in blue if str(cyborg.get_last_action(n)).startswith("[Restore"))
            if term.get(AGENT) or trunc.get(AGENT):
                break
        running = sum(1 for n in blue if type((ec.actions_in_progress.get(n) or {}).get("action")).__name__ == "Restore")
        ok = abs(cost + executed + running) < 1e-9
        print(f"KEEP seed {seed} score {score:.2f}, action cost {cost:.2f}, Restores executed {executed} "
              f"and running at the end {running}, cost equals minus their sum {ok}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--keep", type=int, default=0, help="also run KEEP for this many episodes (cage-keep image only)")
    a = p.parse_args()
    print(f"CybORG {CYBORG_VERSION} at {cyborg_pkg.__file__}, python {sys.version.split()[0]}")
    print("cost by class  " + ", ".join(costs()))
    host, wa = wrapped_run(a.seed, a.steps, every=False)
    _, wb = wrapped_run(a.seed, a.steps, every=True)
    ra = raw_run(a.seed, a.steps, every=False, host=host)
    rb = raw_run(a.seed, a.steps, every=True, host=host)
    print(f"seed {a.seed}, {AGENT}, Restore on {host}")
    print("step | A asserted busy executed cost | B asserted busy executed cost | B-A reward raw, wrapped")
    for t in range(a.steps):
        x, y = ra[t], rb[t]
        print(f"{t:4} | {int(x['asserted'])} {int(x['busy'])} {x['executed'][:28]:28} {x['cost']:5.2f} | "
              f"{int(y['asserted'])} {int(y['busy'])} {y['executed'][:28]:28} {y['cost']:5.2f} | "
              f"{y['reward'] - x['reward']:6.2f} {wb[t] - wa[t]:6.2f}")
    # Compare only the steps before run B's agent accepts a second Restore, after which the two runs' states differ.
    second = next((t for t in range(1, a.steps) if rb[t]["asserted"] and not rb[t]["busy"]), a.steps)
    clean = [t for t in range(1, second) if rb[t]["asserted"] and rb[t]["busy"]]
    same = all(ra[t]["executed"] == rb[t]["executed"] for t in range(second))
    raw = [round(rb[t]["reward"] - ra[t]["reward"], 6) for t in clean]
    wrp = [round(wb[t] - wa[t], 6) for t in clean]
    prop = Restore.__dict__.get("cost")
    rc = prop.fget(None) if isinstance(prop, property) else prop
    charged = bool(clean) and same and all(abs(v - rc) < 1e-9 for v in raw + wrp)
    print(f"verdict {'CHARGED' if charged else 'NOT AS EXPECTED'}. Run B's directives at steps {clean} reached a busy "
          f"agent and were dropped, executions through step {second - 1} {'identical' if same else 'DIFFER'}, "
          f"reward difference at those steps raw {raw} wrapped {wrp}, Restore cost {rc}")
    if a.keep:
        keep_check(a.keep, a.seed)


if __name__ == "__main__":
    main()
