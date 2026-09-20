#!/usr/bin/env python3
"""Make KEEP's trainer (repos/cage-4-submission/train.py) configurable by environment
variable, and add weight provenance to the evaluation path.

train.py
  KEEP_RED               red agent class (default FiniteStateRedAgent); any module under
                         CybORG.Agents.SimpleAgents, e.g. FSRedAgentWrecker
  KEEP_RESTORE           directory holding gnn_ppo-{0..4}.pt to continue from (default: fresh agents)
  KEEP_EPISODES          training_episodes (default 500000, the shipped value)
  KEEP_WORKERS           parallel environments (default 25)
  KEEP_SEED              torch and environment seed (default 1337)
  KEEP_SHARED_ENV_SEED   set to 1 to reproduce the shipped behaviour of seeding every
                         environment identically; default seeds environment i with seed+i
  KEEP_CKPT              interval in episodes for kept checkpoints (default 10000, the shipped
                         value, with the shipped _{k}k naming); any other value names the kept
                         files by episode count, {fname}-{i}_e{episodes}.pt
bin/run
  KEEP_WEIGHTS           name of a directory under ~/cage/keep_weights whose gnn_ppo-*.pt
                         replace the image's weights before the command runs (default shipped)
scripts/oracle.py        header gains "weights" (KEEP_WEIGHTS or "shipped")
scripts/capture_hmarl.py header gains "policy_dir" (HMARL_POLICY_DIR or the shipped path)

Idempotent: each edit tests for the code it inserts. Run from ~/cage.
"""
import os, re

TR = "repos/cage-4-submission/train.py"
RUN = "bin/run"
ORC = "scripts/oracle.py"
HM = "scripts/capture_hmarl.py"


def edit(path, fn):
    src = open(path).read()
    new = fn(src)
    if new != src:
        open(path, "w").write(new); print("patched", path)
    else:
        print("already patched", path)


def patch_train(src):
    if "import os as _os" not in src:
        assert src.startswith("from argparse import ArgumentParser")
        src = src.replace("from argparse import ArgumentParser", "from argparse import ArgumentParser\nimport os as _os, importlib as _importlib", 1)
    if "def _red_class():" not in src:
        assert src.count("SEED = 1337") == 1, "SEED line not found"
        src = src.replace("SEED = 1337", '''def _red_class():
    name = _os.environ.get("KEEP_RED", "FiniteStateRedAgent")
    if name == "FiniteStateRedAgent":
        return FiniteStateRedAgent
    return getattr(_importlib.import_module(f"CybORG.Agents.SimpleAgents.{name}"), name)


SEED = int(_os.environ.get("KEEP_SEED", "1337"))''')
    if "KEEP_WORKERS" not in src:
        src, n = re.subn(r"workers = 25,", 'workers = int(_os.environ.get("KEEP_WORKERS", "25")),', src); assert n == 1
        src, n = re.subn(r"training_episodes = 500_000,", 'training_episodes = int(_os.environ.get("KEEP_EPISODES", "500000")),', src); assert n == 1
    if "red_agent_class=_red_class()," not in src:
        assert src.count("red_agent_class=FiniteStateRedAgent,") == 1
        src = src.replace("red_agent_class=FiniteStateRedAgent,", "red_agent_class=_red_class(),")
    if "KEEP_SHARED_ENV_SEED" not in src:
        old = 'env = CybORG(sg, "sim", seed=seed)'
        assert src.count(old) == 1, "env construction not found"
        src = src.replace(old, 'env = CybORG(sg, "sim", seed=(seed if _os.environ.get("KEEP_SHARED_ENV_SEED") else seed + i))')
    if "KEEP_RESTORE" not in src:
        old = "    ) for _ in range(N_AGENTS)]\n"
        assert src.count(old) == 1, "agent construction not found"
        src = src.replace(old, old + '''    if _os.environ.get("KEEP_RESTORE"):
        from models.cage4 import load as _load_agent
        agents = [_load_agent(f"{_os.environ['KEEP_RESTORE']}/gnn_ppo-{i}.pt") for i in range(N_AGENTS)]
        print("Restored agents from", _os.environ["KEEP_RESTORE"], flush=True)
''')
    if "_a.training = True" not in src:
        # models.cage4.load() ends with agent.eval(), which clears the training flag;
        # the class's train() sets module modes but never sets the flag back, so a
        # restored agent would return evaluation-style actions inside the trainer.
        old = '        print("Restored agents from", _os.environ["KEEP_RESTORE"], flush=True)\n'
        assert src.count(old) == 1, "restore print not found"
        src = src.replace(old, old + "        for _a in agents:\n"
                                     "            _a.training = True  # load() calls eval(); train() does not reset this flag\n")
    if "KEEP_CKPT" not in src:
        old = ("            if e % 10_000 < hp.N and e > hp.N:\n"
               "                agent.save(outf=f'checkpoints/{hp.fnames}-{i}_{e//1000}k.pt')\n")
        assert src.count(old) == 1, "kept-checkpoint block not found"
        src = src.replace(old,
               "            _ckpt = int(_os.environ.get(\"KEEP_CKPT\", \"10000\"))\n"
               "            if e % _ckpt < hp.N and e > hp.N:\n"
               "                agent.save(outf=f'checkpoints/{hp.fnames}-{i}_{e//1000}k.pt' if _ckpt == 10000\n"
               "                           else f'checkpoints/{hp.fnames}-{i}_e{e}.pt')\n")
    return src


def patch_run(src):
    if "KEEP_WEIGHTS" in src:
        return src
    old = '-e HMARL_MODEL_DIR -e HMARL_LOGDIR -e HMARL_POLICY_DIR \\'
    assert src.count(old) == 1, "bin/run HMARL line not found (apply tools_patch_hmarl_train.py first)"
    src = src.replace(old, old + '\n  -e KEEP_WEIGHTS -e KEEP_RED -e KEEP_RESTORE -e KEEP_EPISODES -e KEEP_WORKERS -e KEEP_SEED -e KEEP_SHARED_ENV_SEED \\')
    old = "bash -c 'cp /work/red_agents/*.py /opt/cage/cage-challenge-4/CybORG/Agents/SimpleAgents/ && exec \"$@\"' _ \"$@\""
    assert src.count(old) == 1, "bin/run exec line not found"
    return src.replace(old, "bash -c 'cp /work/red_agents/*.py /opt/cage/cage-challenge-4/CybORG/Agents/SimpleAgents/ && "
                            "if [ -n \"$KEEP_WEIGHTS\" ]; then cp /work/keep_weights/$KEEP_WEIGHTS/gnn_ppo-*.pt /opt/cage/cage-4-submission/weights/; fi && "
                            "exec \"$@\"' _ \"$@\"")


def patch_oracle(src):
    if '"weights":' in src:
        return src
    old = '"machine": MACHINE, "red_agent": _rc.__name__,'
    assert src.count(old) == 1, "oracle.py header literal not found"
    return src.replace(old, '"machine": MACHINE, "weights": os.environ.get("KEEP_WEIGHTS", "shipped"), "red_agent": _rc.__name__,')


def patch_hmarl(src):
    if '"policy_dir":' in src:
        return src
    old = '"harness_sha": HARNESS_SHA, "machine": MACHINE, "episode": ep, "seed": seed,'
    assert src.count(old) == 1, "capture_hmarl.py header literal not found"
    return src.replace(old, '"harness_sha": HARNESS_SHA, "machine": MACHINE, '
                            '"policy_dir": os.environ.get("HMARL_POLICY_DIR", "saved_policies/sub/iter_49/policies/"), '
                            '"episode": ep, "seed": seed,')


edit(TR, patch_train)
edit(RUN, patch_run)
edit(ORC, patch_oracle)
edit(HM, patch_hmarl)
print("done")
