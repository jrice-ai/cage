#!/usr/bin/env python3
"""Busy-flag experiment, patch v3 on top of v2 (tools_patch_keep_busy.py). Run from ~/cage on each machine.
Adds one seeding mode to repos/cage-4-submission/train.py, for the shipped-recipe control (arm S).

  KEEP_EPISODE_SEEDS=workers   each episode's policy stream is seeded from SeedSequence([KEEP_SEED, e, j]) as in
                               mode 1, and the minibatch shuffles, kept-checkpoint names and KEEP_RESUME work as in
                               mode 1, but the environment is NOT reseeded. It arrives as the parent's copy, whose
                               RNG never advances, so every episode starts from the parent's layout, as shipped.
                               With KEEP_SHARED_ENV_SEED=1 (one seed for every parent) that is one layout for the
                               whole run, which is the shipped recipe with its sampling made reproducible.
  KEEP_ENV_FINGERPRINT=1       append "update=<e> episode=<j> <md5>" to checkpoints/<fname>-fp.txt after each
                               episode's reset, an md5 of the network's IP table (or of the reset observation if the
                               table is not reachable), so a test can see whether episodes share a layout. A file,
                               because the loky workers' stdout does not reach the trainer's log.

The run config stored in a state file is unchanged for modes unset and 1, so the state files of running F and N
arms still match after this patch. Mode workers stores "episode_seeds": "workers". All-or-nothing on one file,
idempotent, refuses a train.py that does not carry the v2 marker."""
import hashlib, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
TR = os.path.join(ROOT, "repos/cage-4-submission/train.py")
V2, V3 = "# busy-pilot patch v2", "# busy-pilot patch v3"


def sub(src, old, new, what):
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected 1 match, found {n}")
    return src.replace(old, new)


OLD_FP = """    if ENV_FINGERPRINT:
        print(f"[fp] update={hp.update} episode={i} {_env_fingerprint(env, _obs0)}", flush=True)
"""
NEW_FP = """    if ENV_FINGERPRINT:
        with open(f"checkpoints/{hp.fnames}-fp.txt", "a") as _f:
            _f.write(f"update={hp.update} episode={i} {_env_fingerprint(env, _obs0)}\\n")
"""


def patch(src):
    src = sub(src, '''for _v in ("KEEP_EPISODE_SEEDS", "KEEP_RESUME", "KEEP_CONCAT_EDGES"):
    if _os.environ.get(_v, "") not in ("", "0", "1"):
        raise SystemExit(f"{_v} must be 1 or unset")
EPISODE_SEEDS = _os.environ.get("KEEP_EPISODE_SEEDS") == "1"
''', '''for _v in ("KEEP_RESUME", "KEEP_CONCAT_EDGES", "KEEP_ENV_FINGERPRINT"):
    if _os.environ.get(_v, "") not in ("", "0", "1"):
        raise SystemExit(f"{_v} must be 1 or unset")
SEED_MODE = _os.environ.get("KEEP_EPISODE_SEEDS", "")
if SEED_MODE not in ("", "0", "1", "workers"):
    raise SystemExit("KEEP_EPISODE_SEEDS must be 1, workers or unset")
EPISODE_SEEDS = SEED_MODE in ("1", "workers")
ENV_FINGERPRINT = _os.environ.get("KEEP_ENV_FINGERPRINT") == "1"


def _env_fingerprint(env, obs):
    \'\'\'md5 of the network's IP table after reset, or of the reset observation if the table is not reachable.\'\'\'
    import hashlib as _hashlib
    try:
        key = repr(sorted((str(k), str(v)) for k, v in env.env.environment_controller.state.ip_addresses.items()))
    except Exception:
        key = repr(obs)
    return _hashlib.md5(key.encode()).hexdigest()[:12]
''', "seed mode")
    src = sub(src, '    return {"seed": SEED, "episode_seeds": EPISODE_SEEDS, ',
              '    return {"seed": SEED, "episode_seeds": "workers" if SEED_MODE == "workers" else EPISODE_SEEDS, ',
              "run config")
    src = sub(src, '''        _sp, _se = _stream_seeds(hp.update, i)
        torch.manual_seed(_sp); _np.random.seed(_sp); _random.seed(_sp)
        env.env.set_seed(_se)

    # Initialize environment
    env.reset()
''', '''        _sp, _se = _stream_seeds(hp.update, i)
        torch.manual_seed(_sp); _np.random.seed(_sp); _random.seed(_sp)
        if SEED_MODE == "1":
            env.env.set_seed(_se)
        # In mode workers the environment is left as it arrived, the parent's copy, so every
        # episode starts from the parent's layout as the shipped trainer's do.

    # Initialize environment
    _obs0 = env.reset()
    if ENV_FINGERPRINT:
        with open(f"checkpoints/{hp.fnames}-fp.txt", "a") as _f:
            _f.write(f"update={hp.update} episode={i} {_env_fingerprint(env, _obs0)}\\n")
''', "episode job")
    return V3 + " (tools_patch_keep_seedmode.py in the cage harness)\n" + src


if not os.path.exists(TR):
    sys.exit(f"{TR} is missing")
src = open(TR).read()
if V3 in src and "-fp.txt" in src:
    print("already patched", TR)
elif V3 in src:   # the first v3, whose fingerprint went to stdout and was lost from the workers
    new = sub(src, OLD_FP, NEW_FP, "fingerprint output")
    tmp = TR + ".tmp"
    open(tmp, "w").write(new)
    os.chmod(tmp, os.stat(TR).st_mode)
    os.replace(tmp, TR)
    print("patched (fingerprint to file)", TR)
elif V2 not in src:
    sys.exit(f"{TR} does not carry the v2 patch. Run tools_patch_keep_busy.py first. No file was changed.")
else:
    try:
        new = patch(src)
    except ValueError as err:
        sys.exit(f"{TR}: {err}. No file was changed.")
    tmp = TR + ".tmp"
    open(tmp, "w").write(new)
    os.chmod(tmp, os.stat(TR).st_mode)
    os.replace(tmp, TR)
    print("patched", TR)
print(hashlib.md5(open(TR).read().encode()).hexdigest(), os.path.relpath(TR, ROOT))
print("done")
