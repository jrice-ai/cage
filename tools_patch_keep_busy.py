#!/usr/bin/env python3
"""Busy-flag experiment, trainer and evaluation patches for KEEP (v2). Run from ~/cage on each machine
(repos/ is not tracked, so each machine needs its own run). Every file is checked and every edit is
computed before anything is written, so the tool changes all five files or none. Idempotent.

repos/cage-4-submission/wrapper/graph_wrapper.py
  KEEP_BUSY            unset or "shipped": as shipped. "none": every agent is reported free, so the
                       policy chooses an action every step and CybORG drops what a busy agent is sent.
repos/cage-4-submission/models/memory_buffer.py
  MultiPPOMemory.get_batches shuffles with self.gen when train.py sets one (default None, as shipped).
repos/cage-4-submission/train.py
  KEEP_EPISODE_SEEDS   "1": episode j of the update starting at episode e draws its policy stream and its
                       environment from SeedSequence([KEEP_SEED, e, j]), and agent k's minibatch shuffles
                       from SeedSequence([KEEP_SEED, e, 1000 + k]). Kept checkpoints are then named by
                       updates completed, {fname}-{i}_u{updates}.pt, and the last update is always kept.
                       As shipped, the loky workers' RNGs are never seeded (each process starts from a
                       random seed whatever KEEP_SEED is), and each update ships copies of the parent's
                       environments, whose RNG never advances, so every update starts its episodes from
                       the same layouts (scripts/check_env_replay.py).
  KEEP_N               episodes per update (default 25, as shipped). The shipped learner reads only the
                       first 5 episodes of each update: MultiPPOMemory(bs, agents=5) loops over 5 slots,
                       and train.py hands it one slot per episode. KEEP_N=5 generates just those 5.
  KEEP_CONCAT_EDGES    "1": build the agents with concat_edges=True, as the released weights were built.
                       train.py as shipped builds False.
  KEEP_MAX_THREADS     torch threads for the run (default 36, as shipped). Episode workers get
                       KEEP_MAX_THREADS // workers each, and the learners 1/9 and 5/9 of it, at least 1.
  KEEP_RESUME          "1": continue from checkpoints/{fname}-state.pt, which is now written after every
                       update (weights, Adam moments, the update reached, the reward log, the run config).
                       The run config must match, or the trainer stops.
  KEEP_EPISODE_LEN     steps per training episode (default 500, as shipped). For smoke tests only.
  Also prints the run config and the actor's parameter count at start, and per update the decisions
  per agent-episode and the seconds spent generating and updating.
bin/run
  passes the new variables into the container. When KEEP_BUSY is set, copies
  repos/cage-4-submission/wrapper/graph_wrapper.py over the image's copy, so evaluation reads the same
  switch as training.
scripts/oracle.py
  header gains "busy" (the switch the imported wrapper actually read, "unpatched" if none) and
  "log_policy". --log-policy adds to each step record "policy" (each agent's directive before any rule,
  null when the policy declined because the agent was busy) and "busy" (agents with an action in
  progress when the step began, whose new action CybORG drops).
"""
import hashlib, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
KS = os.path.join(ROOT, "repos/cage-4-submission")
GW = os.path.join(KS, "wrapper/graph_wrapper.py")
MB = os.path.join(KS, "models/memory_buffer.py")
TR = os.path.join(KS, "train.py")
RUN = os.path.join(ROOT, "bin/run")
ORC = os.path.join(ROOT, "scripts/oracle.py")

# Upstream 2afd652d80ce for the first two, upstream plus build/keep-train.patch for train.py.
PRE = {GW: "4df9739c962efe8289821eac2e8fab5e", MB: "1ab2930ed30d1907dc6205eeb9df76ce",
       TR: "8c0d572de74902defbd159b66115dee6"}
# A file carrying its marker is fully patched (each patch function adds its marker last).
MARK = {GW: 'if _KEEP_BUSY == "none":', MB: "getattr(self, 'gen', None)", TR: "# busy-pilot patch v2",
        RUN: "-e KEEP_CONCAT_EDGES", ORC: "--log-policy"}


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()


def sub(src, old, new, what):
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected 1 match, found {n}")
    return src.replace(old, new)


def patch_gw(src):
    src = sub(src, "from wrapper.globals import *\n", '''from wrapper.globals import *

import os as _os

# Busy-flag ablation (cage harness). KEEP_BUSY=none reports every agent as free, so the policy
# chooses an action every step and CybORG drops what it sends to a busy agent. Unset or
# "shipped" keeps the shipped behavior.
_KEEP_BUSY = _os.environ.get("KEEP_BUSY") or "shipped"
if _KEEP_BUSY not in ("shipped", "none"):
    raise ValueError(f"KEEP_BUSY must be shipped or none, not {_KEEP_BUSY}")
''', "graph_wrapper imports")
    old = "            is_blocked = dict_obs['success'] == TernaryEnum.IN_PROGRESS\n"
    return sub(src, old, old + '            if _KEEP_BUSY == "none":\n'
                              '                is_blocked = False\n', "is_blocked line")


def patch_mb(src):
    return sub(src, "idx = torch.randperm(cnt) + offset",
               "idx = torch.randperm(cnt, generator=getattr(self, 'gen', None)) + offset", "MultiPPOMemory shuffle")


def patch_train(src):
    src = sub(src, "import os as _os, importlib as _importlib\n",
              "import os as _os, importlib as _importlib\n"
              "import random as _random, time as _time\n"
              "import numpy as _np\n", "imports")
    src = sub(src, "    N = 25,", '    N = int(_os.environ.get("KEEP_N", "25")),', "N")
    src = sub(src, "    episode_len = 500,\n",
              '    episode_len = int(_os.environ.get("KEEP_EPISODE_LEN", "500")),\n', "episode_len")
    src = sub(src, "MAX_THREADS = 36 #", 'MAX_THREADS = int(_os.environ.get("KEEP_MAX_THREADS", "36")) #', "MAX_THREADS")
    src = sub(src, "torch.set_num_threads(MAX_THREADS)\n", '''torch.set_num_threads(MAX_THREADS)

for _v in ("KEEP_EPISODE_SEEDS", "KEEP_RESUME", "KEEP_CONCAT_EDGES"):
    if _os.environ.get(_v, "") not in ("", "0", "1"):
        raise SystemExit(f"{_v} must be 1 or unset")
EPISODE_SEEDS = _os.environ.get("KEEP_EPISODE_SEEDS") == "1"
CONCAT_EDGES = _os.environ.get("KEEP_CONCAT_EDGES") == "1"


def _stream_seeds(*key):
    \'\'\'Two 32-bit seeds (policy, environment) from SeedSequence([SEED, *key]).\'\'\'
    return [int(x) for x in _np.random.SeedSequence([SEED, *key]).generate_state(2)]


def _run_config():
    import wrapper.graph_wrapper as _gw
    return {"seed": SEED, "episode_seeds": EPISODE_SEEDS, "busy": getattr(_gw, "_KEEP_BUSY", "unpatched"),
            "concat_edges": CONCAT_EDGES, "red": _os.environ.get("KEEP_RED", "FiniteStateRedAgent"),
            "shared_env_seed": bool(_os.environ.get("KEEP_SHARED_ENV_SEED")),
            "restore": _os.environ.get("KEEP_RESTORE", ""), "lr_scale": _os.environ.get("KEEP_LR_SCALE", ""),
            "N": HYPER_PARAMS.N, "episode_len": HYPER_PARAMS.episode_len}


def _save_state(agents, hp, e, log):
    path = f'checkpoints/{hp.fnames}-state.pt'
    torch.save({"e": e, "config": _run_config(), "log": log, "torch_rng": torch.get_rng_state(),
                "agents": [{"actor": a.actor.state_dict(), "critic": a.critic.state_dict(),
                            "actor_opt": a.actor.opt.state_dict(), "critic_opt": a.critic.opt.state_dict()}
                           for a in agents]}, path + ".tmp")
    _os.replace(path + ".tmp", path)


def _load_state(agents, fname):
    path = f'checkpoints/{fname}-state.pt'
    st = torch.load(path)
    if st["config"] != _run_config():
        raise SystemExit(f"KEEP_RESUME: {path} was written under {st['config']}, this run is {_run_config()}")
    for a, s in zip(agents, st["agents"]):
        a.actor.load_state_dict(s["actor"]); a.critic.load_state_dict(s["critic"])
        a.actor.opt.load_state_dict(s["actor_opt"]); a.critic.opt.load_state_dict(s["critic_opt"])
    torch.set_rng_state(st["torch_rng"])
    return st["e"] + HYPER_PARAMS.N, st["log"]
''', "after set_num_threads")
    src = sub(src, '''    torch.set_num_threads(MAX_THREADS // hp.workers)

    # Initialize environment
    env.reset()
''', '''    torch.set_num_threads(max(1, MAX_THREADS // hp.workers))

    if EPISODE_SEEDS:
        # Episode i of the update starting at hp.update gets its own policy and environment
        # streams. As shipped, the worker RNGs are never seeded, and the environment arrives
        # as a copy of the parent's, whose RNG state never advances.
        _sp, _se = _stream_seeds(hp.update, i)
        torch.manual_seed(_sp); _np.random.seed(_sp); _random.seed(_sp)
        env.env.set_seed(_se)

    # Initialize environment
    env.reset()
''', "episode job start")
    src = sub(src, "def train(agents, hp, seed=SEED):\n    [agent.train() for agent in agents]\n    log = []\n",
              "def train(agents, hp, seed=SEED, start=0, log=None):\n    [agent.train() for agent in agents]\n"
              "    log = [] if log is None else log\n", "train signature")
    src = sub(src, "                torch.set_num_threads(MAX_THREADS // 9)\n",
              "                torch.set_num_threads(max(1, MAX_THREADS // 9))\n", "learner threads")
    src = sub(src, "                torch.set_num_threads((MAX_THREADS // 9) * N_AGENTS)\n",
              "                torch.set_num_threads(max(1, MAX_THREADS // 9) * N_AGENTS)\n", "agent 4 threads")
    src = sub(src, "            return agents[i].learn()\n", '''            if not EPISODE_SEEDS:
                return agents[i].learn()
            # Minibatch shuffles from this agent's own generator, so the five learner
            # threads do not race on torch's global RNG
            agents[i].memory.gen = torch.Generator().manual_seed(_stream_seeds(hp.update, 1000 + i)[0])
            try:
                return agents[i].learn()
            finally:
                agents[i].memory.gen = None
''', "learn return")
    src = sub(src, "    for e in range(hp.training_episodes // hp.N):\n        e *= hp.N\n",
              "    for e in range(start // hp.N, hp.training_episodes // hp.N):\n        e *= hp.N\n"
              "        hp.update = e\n        _t0 = _time.time()\n", "training loop head")
    src = sub(src, '        print("Updating")\n', '        _t1 = _time.time()\n'
              '        _dec = sum(len(m.a) for ms in memories for m in ms) / (N_AGENTS * hp.N)\n'
              '        print("Updating")\n', "Updating print")
    src = sub(src, '        print(f"[{e}] Loss: [{losses}]")\n',
              '        print(f"[{e}] Loss: [{losses}]")\n'
              '        print(f"[{e}] decisions per agent-episode {_dec:.1f}, generate {_t1 - _t0:.1f}s, '
              'update {_time.time() - _t1:.1f}s", flush=True)\n', "Loss print")
    old = ("            if e % _ckpt < hp.N and e > hp.N:\n"
           "                agent.save(outf=f'checkpoints/{hp.fnames}-{i}_{e//1000}k.pt' if _ckpt == 10000\n"
           "                           else f'checkpoints/{hp.fnames}-{i}_e{e}.pt')\n")
    src = sub(src, old, '''            if EPISODE_SEEDS:
                # Named by updates completed, and the last update of a leg is always kept
                _done = e + hp.N
                if _done % _ckpt == 0 or _done + hp.N > hp.training_episodes:
                    agent.save(outf=f'checkpoints/{hp.fnames}-{i}_u{_done // hp.N}.pt')
            elif e % _ckpt < hp.N and e > hp.N:
                agent.save(outf=f'checkpoints/{hp.fnames}-{i}_{e//1000}k.pt' if _ckpt == 10000
                           else f'checkpoints/{hp.fnames}-{i}_e{e}.pt')

        # Full state for KEEP_RESUME, written after every update
        _save_state(agents, hp, e, log)
''', "kept-checkpoint block")
    src = sub(src, "        clip=0.2,\n        epochs=HYPER_PARAMS.epochs\n    ) for _ in range(N_AGENTS)]\n",
              "        clip=0.2,\n        epochs=HYPER_PARAMS.epochs,\n        concat_edges=CONCAT_EDGES,\n"
              "    ) for _ in range(N_AGENTS)]\n", "agent construction")
    src = sub(src, "    HYPER_PARAMS.fnames = args.fname\n    train(agents, HYPER_PARAMS)",
              '''    HYPER_PARAMS.fnames = args.fname
    print("KEEP run", _run_config(), flush=True)
    print("actor parameters", sum(p.numel() for p in agents[0].actor.parameters()),
          "max threads", MAX_THREADS, "workers", HYPER_PARAMS.workers, flush=True)
    _start, _log = 0, None
    if _os.environ.get("KEEP_RESUME") == "1":
        _start, _log = _load_state(agents, args.fname)
        print(f"Resumed {args.fname} at episode {_start}", flush=True)
    train(agents, HYPER_PARAMS, start=_start, log=_log)''', "main tail")
    return "# busy-pilot patch v2 (tools_patch_keep_busy.py in the cage harness)\n" + src


def patch_run(src):
    src = sub(src, "-e KEEP_CKPT -e KEEP_LR_SCALE",
              "-e KEEP_CKPT -e KEEP_LR_SCALE -e KEEP_BUSY -e KEEP_EPISODE_SEEDS -e KEEP_RESUME -e KEEP_EPISODE_LEN "
              "-e KEEP_N -e KEEP_MAX_THREADS -e KEEP_CONCAT_EDGES", "bin/run KEEP variables")
    return sub(src, "/opt/cage/cage-4-submission/weights/; fi && exec \"$@\"'",
               "/opt/cage/cage-4-submission/weights/; fi && "
               "if [ -n \"$KEEP_BUSY\" ]; then grep -q _KEEP_BUSY /work/repos/cage-4-submission/wrapper/graph_wrapper.py "
               "|| { echo \"KEEP_BUSY is set but repos/cage-4-submission has no busy switch\" >&2; exit 1; }; "
               "cp /work/repos/cage-4-submission/wrapper/graph_wrapper.py /opt/cage/cage-4-submission/wrapper/graph_wrapper.py; fi && "
               "exec \"$@\"'", "bin/run exec line")


def patch_oracle(src):
    src = sub(src, "from submission import Submission\n",
              "from submission import Submission\nimport wrapper.graph_wrapper as _gw\n", "oracle imports")
    src = sub(src, '''    def patched(agent_name, a_id):
        return intercept(agent_name, original(agent_name, a_id))
''', '''    def patched(agent_name, a_id):
        base = original(agent_name, a_id)
        if "pol" in stats:   # --log-policy: the policy's own directive, before any rule
            stats["pol"][agent_name] = None if a_id is None else str(base)
        return intercept(agent_name, base)
''', "translator")
    src = sub(src, "only_agents=None, policy_seed=None):\n",
              "only_agents=None, policy_seed=None, log_policy=False):\n", "capture_episode signature")
    src = sub(src, "    stats = Counter()\n", "    stats = Counter()\n"
              "    if log_policy:\n        stats[\"pol\"] = {}\n", "stats init")
    src = sub(src, '"weights": os.environ.get("KEEP_WEIGHTS", "shipped"), ',
              '"weights": os.environ.get("KEEP_WEIGHTS", "shipped"), '
              '"busy": getattr(_gw, "_KEEP_BUSY", "unpatched"), "log_policy": log_policy, ', "header")
    src = sub(src, "            actions = {n: agents[n].get_action(wrapped_obs[n],\n",
              "            busy = [n for n in BLUE if cyborg.environment_controller.actions_in_progress.get(n) is not None]\n"
              "            actions = {n: agents[n].get_action(wrapped_obs[n],\n", "busy before step")
    src = sub(src, '''                **({"signal": stats.pop("sig")} if "sig" in stats else {}),
            }) + "\\n")
''', '''                **({"signal": stats.pop("sig")} if "sig" in stats else {}),
                **({"policy": stats["pol"], "busy": busy} if log_policy else {}),
            }) + "\\n")
            if log_policy:
                stats["pol"] = {}
''', "step record")
    src = sub(src, "a.window, a.queue, noise, agents, a.policy_seed)\n",
              "a.window, a.queue, noise, agents, a.policy_seed, a.log_policy)\n", "Parallel call")
    return sub(src, '    p.add_argument("--red", default="FiniteStateRedAgent")\n',
               '    p.add_argument("--red", default="FiniteStateRedAgent")\n'
               '    p.add_argument("--log-policy", action="store_true", help="record each agent\'s directive before any '
               'rule, and the agents busy when each step began")\n', "argparse")


# Pass 1. Read every file, decide its state, and compute every edit. Nothing is written yet.
plan, problems = [], []
for path, fn in ((GW, patch_gw), (MB, patch_mb), (TR, patch_train), (RUN, patch_run), (ORC, patch_oracle)):
    if not os.path.exists(path):
        problems.append(f"{path} is missing")
        continue
    src = open(path).read()
    if MARK[path] in src:
        plan.append((path, None))
        continue
    if path in PRE and md5(src) != PRE[path]:
        problems.append(f"{path} is neither the expected pre-patch file (md5 {md5(src)}, expected {PRE[path]}) "
                        "nor fully patched")
        continue
    try:
        plan.append((path, fn(src)))
    except ValueError as err:
        problems.append(f"{path}: {err}")
if problems:
    sys.exit("No file was changed.\n" + "\n".join(problems))

# Pass 2. Write.
for path, new in plan:
    if new is None:
        print("already patched", path)
        continue
    tmp = path + ".tmp"
    open(tmp, "w").write(new)
    os.chmod(tmp, os.stat(path).st_mode)
    os.replace(tmp, path)
    print("patched", path)
for path in (GW, MB, TR):
    print(md5(open(path).read()), os.path.relpath(path, ROOT))
print("done")
