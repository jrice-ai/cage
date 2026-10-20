#!/usr/bin/env python3
"""Busy-mask switch for H-MARL at evaluation, and policy logging in capture_hmarl.py. Run from
~/cage. Every edit is computed before anything is written, so the tool changes all three files
or none. Idempotent.

repos/Hierarchical-MARL/h-marl-3policy/subpolicies/BlueFlatWrapper_CC4.py
  HMARL_BUSY           unset or "shipped": as shipped. While an agent's action is in progress the
                       wrapper masks every action but Sleep and blanks the observation. "none": the
                       wrapper builds the observation and masks as on a free tick, so the policy
                       chooses an action every step and CybORG drops what a busy agent is sent.
scripts/capture_hmarl.py
  header gains "busy" (the switch, "unpatched" if the wrapper under H3P has none) and
  "log_policy". --log-policy adds to each step record "policy" (each agent's action as the
  sub-policy chose it, before any rule; "Sleep" is what the shipped mask leaves a busy agent) and
  "busy" (agents with an action in progress when the step began, whose new action CybORG drops).
bin/run
  passes HMARL_BUSY into the container. The H-MARL image reads the wrapper from /work/repos, so
  no copy is needed.
"""
import os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
BW = os.path.join(ROOT, "repos/Hierarchical-MARL/h-marl-3policy/subpolicies/BlueFlatWrapper_CC4.py")
CH = os.path.join(ROOT, "scripts/capture_hmarl.py")
RUN = os.path.join(ROOT, "bin/run")
MARK = {BW: 'and _HMARL_BUSY != "none":', CH: "--log-policy", RUN: "-e HMARL_BUSY"}


def sub(src, old, new, what):
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected 1 match, found {n}")
    return src.replace(old, new)


def patch_bw(src):
    src = sub(src, "FULL_MASK = True\n", '''FULL_MASK = True

import os as _os
# Busy-mask ablation (cage harness). HMARL_BUSY=none drops the in-progress branch below, so
# the policy chooses an action every step and CybORG drops what a busy agent is sent.
_HMARL_BUSY = _os.environ.get("HMARL_BUSY") or "shipped"
if _HMARL_BUSY not in ("shipped", "none"):
    raise ValueError(f"HMARL_BUSY must be shipped or none, not {_HMARL_BUSY}")
''', "FULL_MASK line")
    return sub(src, "        if observation['success'].name == 'IN_PROGRESS':\n",
               "        if observation['success'].name == 'IN_PROGRESS' and _HMARL_BUSY != \"none\":\n",
               "in-progress branch")


def patch_ch(src):
    src = sub(src, "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # oracle_rules.py\n",
              "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # oracle_rules.py\n"
              "_BW = open(os.path.join(H3P, \"subpolicies\", \"BlueFlatWrapper_CC4.py\")).read()\n"
              "BUSY = (os.environ.get(\"HMARL_BUSY\") or \"shipped\") if \"_HMARL_BUSY\" in _BW else \"unpatched\"\n"
              "if BUSY == \"unpatched\" and os.environ.get(\"HMARL_BUSY\"):\n"
              "    sys.exit(\"HMARL_BUSY is set but the wrapper under H3P has no busy switch\")\n", "path setup")
    src = sub(src, '    holder = {"intercept": None, "space": {}}\n',
              '    holder = {"intercept": None, "space": {}, "pol": None}\n', "holder")
    src = sub(src, "            res = icp(agent, act)\n",
              "            if holder[\"pol\"] is not None:      # --log-policy: the sub-policy's own choice\n"
              "                holder[\"pol\"][agent] = str(act)\n"
              "            res = icp(agent, act)\n", "env_step intercept")
    src = sub(src, '''            "rule": rule, "budget": budget, "min_gap": min_gap,
            "cyborg_version": CYBORG_VERSION, "episode_length": EPISODE_LENGTH, **hdr,
''', '''            "rule": rule, "budget": budget, "min_gap": min_gap, "busy": BUSY,
            "cyborg_version": CYBORG_VERSION, "episode_length": EPISODE_LENGTH, **hdr,
''', "header")
    src = sub(src, '''                n0 = len(stats.get("ovr", []))
                obs, rew, term, trunc, info = env.step(actions)
''', '''                n0 = len(stats.get("ovr", []))
                if hdr.get("log_policy"):
                    busy = [n for n in BLUE if cyborg.environment_controller.actions_in_progress.get(n) is not None]
                    holder["pol"] = {}
                obs, rew, term, trunc, info = env.step(actions)
''', "sub-policy step")
    src = sub(src, '''                **({"signal": stats.pop("sig")} if "sig" in stats else {}),
            }) + "\\n")
            t += 1
''', '''                **({"signal": stats.pop("sig")} if "sig" in stats else {}),
                **({"policy": holder["pol"], "busy": busy} if hdr.get("log_policy") else {}),
            }) + "\\n")
            if hdr.get("log_policy"):
                holder["pol"] = None
            t += 1
''', "step record")
    src = sub(src, '''           "noise": a["noise"], "agents": a["agents"]}
    foot = _run_episode(''', '''           "noise": a["noise"], "agents": a["agents"], "log_policy": a["log_policy"]}
    foot = _run_episode(''', "episode header")
    src = sub(src, '''               "noise": a["noise"], "agents": a["agents"]}
        foots.append(_run_episode(''', '''               "noise": a["noise"], "agents": a["agents"], "log_policy": a["log_policy"]}
        foots.append(_run_episode(''', "compat header")
    return sub(src, '    ap.add_argument("--compat", action="store_true", help="mirror evaluation.py seeding, sequential")\n',
               '    ap.add_argument("--compat", action="store_true", help="mirror evaluation.py seeding, sequential")\n'
               '    ap.add_argument("--log-policy", action="store_true", help="record each agent\'s action as the sub-policy '
               'chose it, before any rule, and the agents busy when each step began")\n', "argparse")


def patch_run(src):
    return sub(src, "-e HMARL_MODEL_DIR -e HMARL_LOGDIR -e HMARL_POLICY_DIR \\\n",
               "-e HMARL_MODEL_DIR -e HMARL_LOGDIR -e HMARL_POLICY_DIR -e HMARL_BUSY \\\n", "bin/run HMARL line")


plan, problems = [], []
for path, fn in ((BW, patch_bw), (CH, patch_ch), (RUN, patch_run)):
    if not os.path.exists(path):
        problems.append(f"{path} is missing")
        continue
    src = open(path).read()
    if MARK[path] in src:
        plan.append((path, None))
        continue
    try:
        plan.append((path, fn(src)))
    except ValueError as err:
        problems.append(f"{path}: {err}")
if problems:
    sys.exit("No file was changed.\n" + "\n".join(problems))
for path, new in plan:
    if new is None:
        print("already patched", path)
        continue
    tmp = path + ".tmp"
    open(tmp, "w").write(new)
    os.chmod(tmp, os.stat(path).st_mode)
    os.replace(tmp, path)
    print("patched", path)
print("done")
