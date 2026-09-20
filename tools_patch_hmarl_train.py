#!/usr/bin/env python3
"""Make H-MARL's sub-policy trainer and policy loader configurable by environment
variable, so retrained variants are the authors' pipeline with one setting changed.

train_subpolicies.py
  HMARL_RED          red agent class name (default FiniteStateRedAgent); any module under
                     CybORG.Agents.SimpleAgents, e.g. FSRedAgentWrecker
  HMARL_SEED         RLlib seed (default unset)
  HMARL_TRAIN_BATCH  train_batch_size (default 1000000, the shipped value)
  HMARL_RESTORE      checkpoint dir to continue from, e.g. saved_policies/sub/iter_49
  HMARL_ITER0        first iteration number to save as (default 0)
  HMARL_ITERS        number of iterations (default 50)
  HMARL_MODEL_DIR    where iter_N checkpoints go (default saved_policies/sub)
  HMARL_LOGDIR       TensorBoard log dir (default logs/train_subpolicies)
Ray_BlueAgent.py
  HMARL_POLICY_DIR   policies dir to load (default saved_policies/sub/iter_49/policies/)
bin/run
  passes those variables into the container and gives Ray 2g of shared memory.

Idempotent: each edit tests for the code it inserts. Run from ~/cage.
"""
import os, re, sys

H3P = "repos/Hierarchical-MARL/h-marl-3policy"
TR = os.path.join(H3P, "subpolicies", "train_subpolicies.py")
RB = os.path.join(H3P, "subpolicies", "Ray_BlueAgent.py")
RUN = "bin/run"


def edit(path, fn):
    src = open(path).read()
    new = fn(src)
    if new != src:
        open(path, "w").write(new)
        print("patched", path)
    else:
        print("already patched", path)


def patch_train(src):
    if "def _red_class():" not in src:
        helper = '''import os as _os, importlib as _importlib


def _red_class():
    name = _os.environ.get("HMARL_RED", "FiniteStateRedAgent")
    if name == "FiniteStateRedAgent":
        return FiniteStateRedAgent
    return getattr(_importlib.import_module(f"CybORG.Agents.SimpleAgents.{name}"), name)


def env_creator_CC4('''
        assert src.count("def env_creator_CC4(") == 1
        src = src.replace("def env_creator_CC4(", helper, 1)
        assert src.count("red_agent_class=FiniteStateRedAgent,") == 1
        src = src.replace("red_agent_class=FiniteStateRedAgent,", "red_agent_class=_red_class(),")
    if "HMARL_SEED" not in src:
        old = '.debugging(logger_config={"logdir":"logs/train_subpolicies", "type":"ray.tune.logger.TBXLogger"})'
        assert src.count(old) == 1, "debugging() line not found"
        src = src.replace(old, '.debugging(logger_config={"logdir": _os.environ.get("HMARL_LOGDIR", "logs/train_subpolicies"), "type":"ray.tune.logger.TBXLogger"}, '
                               'seed=(int(_os.environ["HMARL_SEED"]) if _os.environ.get("HMARL_SEED") else None))')
    if "HMARL_TRAIN_BATCH" not in src:
        old = "train_batch_size = 1000000,"
        assert src.count(old) == 1, "train_batch_size line not found"
        src = src.replace(old, 'train_batch_size = int(_os.environ.get("HMARL_TRAIN_BATCH", "1000000")),')
    if "HMARL_RESTORE" not in src:
        old = 'model_dir = "saved_policies/sub"'
        assert src.count(old) == 1
        src = src.replace(old, '''model_dir = _os.environ.get("HMARL_MODEL_DIR", "saved_policies/sub")
    if _os.environ.get("HMARL_RESTORE"):
        print("Restoring from", _os.environ["HMARL_RESTORE"], flush=True)
        algo.restore(_os.environ["HMARL_RESTORE"])
    _iter0 = int(_os.environ.get("HMARL_ITER0", "0"))
    _iters = int(_os.environ.get("HMARL_ITERS", "50"))''')
        src, n = re.subn(r"for i in range\(50\):\n(\s+)iteration = i[^\n]*",
                         r"for i in range(_iters):\n\1iteration = _iter0 + i", src)
        assert n == 1, "training loop not found"
    return src


def patch_agent(src):
    old = 'pkl_cp_dir = os.path.join("saved_policies/sub/iter_49/policies/", self.name)'
    new = 'pkl_cp_dir = os.path.join(os.environ.get("HMARL_POLICY_DIR", "saved_policies/sub/iter_49/policies/"), self.name)'
    if new in src:
        return src
    assert src.count(old) == 1, "policy path line not found"
    return src.replace(old, new)


def patch_run(src):
    if "HMARL_POLICY_DIR" in src:
        return src
    old = '-e HARNESS_SHA="$(git -C ~/cage rev-parse HEAD)" \\'
    assert src.count(old) == 1, "bin/run HARNESS_SHA line not found"
    return src.replace(old, old + '''
  --shm-size=2g \\
  -e HMARL_RED -e HMARL_SEED -e HMARL_TRAIN_BATCH -e HMARL_RESTORE -e HMARL_ITER0 -e HMARL_ITERS \\
  -e HMARL_MODEL_DIR -e HMARL_LOGDIR -e HMARL_POLICY_DIR \\''')


edit(TR, patch_train)
edit(RB, patch_agent)
edit(RUN, patch_run)
print("done. Regenerate the fixes patch: git -C repos/Hierarchical-MARL diff > build/hmarl-fixes.patch")
