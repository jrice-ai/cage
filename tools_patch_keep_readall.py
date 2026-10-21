#!/usr/bin/env python3
"""Busy-flag experiment, patch v4 on top of v3. Run from ~/cage on each machine. Lets the learner read every episode an
update generates, behind a switch, for the read-all control (arm R).

repos/cage-4-submission/train.py
  KEEP_READ_ALL=1   after each update's episodes are handed to the agents' memories, set each memory's slot count to the
                    number of buffers it holds, so the learner reads all KEEP_N episodes. As shipped the count stays at
                    the five the memory was built with (MultiPPOMemory(bs, agents=5)), so the learner reads the first
                    five of the twenty-five episodes generated. The run config stores "read_all": True only when the
                    switch is on, so the state files of running F, N and S arms still match. Every update prints
                    "learner reads K of N episodes per agent".
bin/run             passes KEEP_READ_ALL into the container.
eval_keep_pilot.sh  accepts kbf_R_ tags.
All or nothing, idempotent."""
import hashlib, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
TR = os.path.join(ROOT, "repos/cage-4-submission/train.py")
RUN = os.path.join(ROOT, "bin/run")
EV = os.path.join(ROOT, "eval_keep_pilot.sh")
V3, V4 = "# busy-pilot patch v3", "# busy-pilot patch v4"
MARK = {TR: V4, RUN: "-e KEEP_READ_ALL", EV: "kbf_[FNSR]_s"}


def sub(src, old, new, what):
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected 1 match, found {n}")
    return src.replace(old, new)


def patch_train(src):
    if V3 not in src:
        raise ValueError("train.py lacks the v3 patch (tools_patch_keep_seedmode.py)")
    src = sub(src, 'ENV_FINGERPRINT = _os.environ.get("KEEP_ENV_FINGERPRINT") == "1"\n',
              'ENV_FINGERPRINT = _os.environ.get("KEEP_ENV_FINGERPRINT") == "1"\n'
              'if _os.environ.get("KEEP_READ_ALL", "") not in ("", "0", "1"):\n'
              '    raise SystemExit("KEEP_READ_ALL must be 1 or unset")\n'
              'READ_ALL = _os.environ.get("KEEP_READ_ALL") == "1"\n', "switch")
    src = sub(src, '            "N": HYPER_PARAMS.N, "episode_len": HYPER_PARAMS.episode_len}\n',
              '            "N": HYPER_PARAMS.N, "episode_len": HYPER_PARAMS.episode_len, **({"read_all": True} if READ_ALL else {})}\n', "run config")
    src = sub(src, '''        for i in range(N_AGENTS):
            agents[i].memory.mems = memories[i]
''', '''        for i in range(N_AGENTS):
            agents[i].memory.mems = memories[i]
            if READ_ALL:
                # As shipped the slot count stays at the five the memory was built with, so the
                # learner reads the first five of the N buffers it was just handed
                agents[i].memory.tot = len(memories[i])
        print(f"learner reads {min(agents[0].memory.tot, len(memories[0]))} of {len(memories[0])} episodes per agent", flush=True)
''', "memory hand-over")
    return V4 + " (tools_patch_keep_readall.py in the cage harness)\n" + src


def patch_run(src):
    return sub(src, "-e KEEP_N -e KEEP_MAX_THREADS -e KEEP_CONCAT_EDGES",
               "-e KEEP_N -e KEEP_MAX_THREADS -e KEEP_CONCAT_EDGES -e KEEP_READ_ALL", "bin/run KEEP variables")


def patch_ev(src):
    return sub(src, 'case $tag in kbf_[FNS]_s[0-9]*) ;;', 'case $tag in kbf_[FNSR]_s[0-9]*) ;;', "tag check")


plan, problems = [], []
for path, fn in ((TR, patch_train), (RUN, patch_run), (EV, patch_ev)):
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
print(hashlib.md5(open(TR).read().encode()).hexdigest(), os.path.relpath(TR, ROOT))
print("done")
