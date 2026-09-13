# CAGE 4 Baseline Reproduction Notes

## Overview

Record of the first working session standing up CybORG CAGE Challenge 4 and
reproducing the KEEP baseline. Covers container build, dependency pins not
declared by either repo, a clean reproduction of the published score, and three
defects found in the KEEP evaluation harness that affect reproducibility.

Scope was the go/no-go gate. Reproduce a published autonomous baseline in a
container we control, so later human supervision work has something valid to
compare against. Gate passed.

All numbers below come from a single machine and a single image. Nothing here
has been checked on second hardware yet.

## Environment

### Hardware

Surface Laptop Studio 2, Intel i7-13700H, 14 cores and 20 logical processors,
64GB RAM. Raptor Lake hybrid cores, so wall clock timings are approximate and
should be re-measured on uniform-core hardware before being used for capacity
planning.

WSL2 running Ubuntu 24.04, capped via `C:\Users\<user>\.wslconfig`

```
[wsl2]
memory=32GB
processors=16
swap=8GB
```

Docker Desktop with the WSL2 backend. All project files inside the WSL
filesystem under `~/cage`, never under `/mnt/c`.

### Repositories

Cloned to `~/cage/repos`

| Repo | Purpose |
|---|---|
| `cage-challenge/cage-challenge-4` | CybORG environment |
| `cybermonic/cage-4-submission` | KEEP agent, weights included |
| `adityavs14/Hierarchical-MARL` | H-MARL, not yet built |

CybORG commit recorded automatically by the editable install

```
8c3c50ca54b176c2de199847944e8dcc035497e3
```

### Image

`cage-keep:dev`, built from `~/cage/build/Dockerfile.keep`, base
`python:3.10-slim`. CPU only, no CUDA, no `--gpus` flag anywhere.

Resolved versions

```
torch            2.2.0+cpu
numpy            1.26.4
ray              2.12.0
torch_geometric  2.3.1
pyarrow          15.0.2
```

Full freeze at `~/cage/data/requirements-keep.lock`.

## Build notes

Two pins were required beyond anything declared in the three repos. Both should
be treated as findings rather than incidental fixes.

**CPU torch needs a secondary index.** `--index-url` replaces PyPI entirely, so
torch's own dependencies fail to resolve. Correct form

```dockerfile
RUN pip install --no-cache-dir torch==2.2.0 \
      --index-url https://download.pytorch.org/whl/cpu \
      --extra-index-url https://pypi.org/simple
```

Verify with `python -c "import torch; print(torch.__version__)"`, which must
report `2.2.0+cpu`. Plain `2.2.0` means the CUDA build was installed.

**pyarrow must be pinned to 15.0.2.** Ray 2.12 calls
`pa.PyExtensionType.set_auto_load(True)` on import. That attribute was removed
in later pyarrow, and Ray's own requirement has a floor with no ceiling, so pip
resolved to 25.0.1 and every RLlib import died with

```
AttributeError: module 'pyarrow' has no attribute 'PyExtensionType'
```

The pin must come last in the Dockerfile, after both requirements installs,
otherwise a later step silently upgrades over it.

**Version conflicts between repos.** CC4 asks for `torch_geometric==2.5.0`,
KEEP asks for `2.3.1`. Installing KEEP's requirements last makes 2.3.1 win,
which is correct since KEEP is the agent under test. CC4's `ray[rllib]` is
unpinned, so the pinned Ray must be installed before CC4 to prevent pip pulling
a current release.

KEEP wants `ray==2.12.0` and H-MARL wants `ray==2.10.0`. These are not
compatible. Two separate images required.

## Verification

Environment test suite, run inside the container

```bash
cd /opt/cage/cage-challenge-4
pytest ./CybORG/Tests/test_cc4
```

Result

```
680 passed, 15 skipped, 14 warnings in 542.37s (0:09:02)
```

Includes `test_cc4_seed.py`, which passes. Warnings are cosmetic deprecations
from pygame and matplotlib. The gym unmaintained banner appears on every run
and is harmless.

## Results

Published KEEP score is -193.68, fifth on the final CAGE 4 leaderboard. The
paper does not state which action selection mode produced it.

All runs below are 100 episodes of 500 steps against `FiniteStateRedAgent`,
except where noted.

| Configuration | Mean | Stdev | Reproducible |
|---|---|---|---|
| Sampled, unseeded, 12 workers | -161.50 | 60.30 | No, and roughly 12 effective episodes |
| Sampled, unseeded, serial, n=2 | -196.50 / -181.00 | n/a | No |
| Sampled, torch seeded, serial | **-196.06** | 88.70 | Yes |
| Greedy, torch seeded, serial | -550.45 | 356.22 | Yes |

The seeded sampled run at -196.06 is the reproduction. It sits about 2.4 points
from the published figure and regenerates exactly.

Commands, run from `/opt/cage/cage-4-submission` inside the container

```bash
python3 -u evaluation.py --distribute 1 --max-eps 100 --seed 0
python3 -u evaluation.py --distribute 1 --max-eps 100 --seed 0 --deterministic
```

Outputs preserved at

```
~/cage/data/keep_sampled_seed0_100ep/
~/cage/data/keep_greedy_seed0_100ep/
```

Reproducibility was verified by running the two episode case twice and
confirming byte identical output, including the standard deviation to full
precision.

```bash
python3 -u evaluation.py --distribute 1 --max-eps 2 --seed 0
```

returns -194 with stdev 76.36753236814714 on every invocation.

## Defects found in `evaluation.py`

All three are in `cage-4-submission/evaluation.py`, the KEEP team's own
evaluation script. Backup of the original at `evaluation.py.bak`.

### 1. Output files never written

Both `run_evaluation` and `run_evaluation_parallel` take
`write_to_file=False` as a default. The `__main__` block never passes the
argument and no CLI flag exists for it, so the entire logging block is
unreachable. The script prints a mean to stdout and writes nothing.

Fix was to add a flag and pass it through. Affected files are `summary.txt`,
`full.txt`, `actions.txt`, `summary.json`, `scores.txt`.

### 2. Policy sampling is unseeded

Lines 380 to 383 of `models/cage4.py` select between `distro.probs.argmax()`
and `distro.sample()` based on `self.deterministic`, which is initialized to
`False` at line 306. The setter `set_deterministic()` at line 347 is never
called from `submission.py`.

So evaluation runs in sampling mode, and nothing seeds torch. `--seed` reaches
`CybORG(sg, "sim", seed=seed)` only, which fixes the environment stream but not
the action draws.

Observed effect. Two identical invocations of the same two episode command gave
-196.5 and -181.

Fix applied, before agent construction

```python
import torch, numpy as np, random
if args.seed is not None:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
```

After this change, repeated runs are identical.

### 3. Parallel path returns correlated episodes

In `run_evaluation_parallel`, `workers` CybORG instances are constructed in a
loop, each with the same `seed=seed`. Episodes are then dispatched with

```python
delayed(evaluate_one_episode)(*envs[i % workers], ...)
```

Two problems compound. Every environment shares one seed, so all workers hold
identical environments. And `i % workers` reuses each environment every N
episodes, with `prefer='processes'` pickling the same starting state to a fresh
process each time.

At 12 workers and 100 episodes the run produces roughly 12 distinct episodes,
each repeated eight or nine times, while reporting a mean and standard
deviation as though over 100 independent samples.

Consistent with this, the parallel run reported a standard deviation of 60.30
against 88.70 from the equivalent serial run. Understated spread is what
correlated sampling looks like.

This is the KEEP team's own addition. The argparse help text says it was added
to speed up evaluation.

Not yet fixed. The intended approach is to seed each episode from its own
index, so episode N is determined by N regardless of which worker runs it.

Unknown and worth checking before making any claim about published numbers.
Whether the leaderboard used this script at all, whether the KEEP paper's
figure came from the parallel path, and whether any third party has used it.

## Action distribution analysis

Script at `~/cage/data/analyse_actions.py`, run against the preserved
`actions.txt` from both 100 episode runs.

```bash
python3 /data/analyse_actions.py \
  /data/keep_sampled_seed0_100ep/actions.txt \
  /data/keep_greedy_seed0_100ep/actions.txt
```

### Behavioral collapse under greedy selection

| Measure | Sampled | Greedy |
|---|---|---|
| Consecutive repeat rate, mean | 30.6% | 61.4% |
| Distinct hosts touched per episode | 13.9 | 7.4 |
| Distinct actions per episode | 45.8 | 10.8 |

Per agent, greedy repeat rates reach 89.6% for `blue_agent_0` and 93.5% for
`blue_agent_1`. Those agents emit essentially one action for the whole episode.

### Action mix, share of 249,000 agent-steps

| Action | Sampled | Greedy |
|---|---|---|
| Sleep | 37.87% | 25.91% |
| AllowTrafficZone | 27.23% | 36.57% |
| Analyse | 10.62% | 6.20% |
| BlockTrafficZone | 6.57% | 5.35% |
| DeployDecoy | 6.45% | 10.03% |
| Remove | 4.16% | **0.06%** |
| Monitor | 4.00% | 13.49% |
| Restore | 3.09% | 2.38% |

Note that `Analyse` is spelled as CybORG spells it.

`Remove` drops from 10,353 uses to 148. The greedy policy has effectively lost
its cheap eviction action, and `Restore` does not compensate. That is the most
plausible mechanism for both the worse mean and the inflated variance, since
compromise accumulates unchecked and episode outcomes become bimodal.

The mechanism appears to be lock-in under partial observability. CC4 alerts are
memoryless, so a deterministic policy facing a recurring observation emits the
same action indefinitely. Sampling provides coverage across hosts that the
policy has no memory to achieve otherwise. This matches the known result that
stochastic policies can strictly dominate deterministic ones in partially
observable settings.

### Consequential action rate

From the sampled run, treating Restore, Remove, DeployDecoy and
BlockTrafficZone as consequential

```
20.3% of agent-steps, roughly 505 decisions per episode
```

Narrower gates

```
Restore only          3.09%,  roughly  77 decisions per episode
Restore + Remove      7.25%,  roughly 180 decisions per episode
```

An episode is 498 logged steps across 5 agents, so 2,490 agent-steps.

This directly sizes the escalation gate for later human supervision work. A
Restore-only gate yields a session length a person could plausibly sustain.

## Throughput

Measured on the Surface, single-threaded per process via `OMP_NUM_THREADS=1`.

| Configuration | Rate |
|---|---|
| Serial, sampled | roughly 15.5 s per episode |
| Serial, greedy | 17.36 s per episode |
| 12 workers, per worker | roughly 12.5 env-steps per second |
| 12 workers, aggregate | roughly 150 env-steps per second |

100 episodes serial takes about 29 minutes. These figures should be re-measured
on uniform-core hardware before being used to size the server workload.

## Summary of outcomes

**The gate passed.** CybORG CAGE 4 builds, its test suite is clean, and KEEP
reproduces the published baseline at -196.06 against -193.68. The reproduction
is exact on repeat runs.

**The reference evaluation harness is not reproducible as shipped.** Policy
sampling is unseeded, so two identical commands give different answers. Fixed
locally with three lines.

**The parallel evaluation path returns correlated samples.** At 12 workers and
100 episodes it yields roughly 12 distinct episodes repeated, while reporting
statistics over 100. Not yet fixed. Any number produced with `--distribute`
should be treated as suspect.

**Action selection mode is worth 2.8x in score and is undocumented.** Sampling
gives -196.06, greedy gives -550.45. The published figure carries no mode
annotation, so anyone reproducing KEEP can land anywhere in that range with no
way to detect the error. Explained mechanistically by a doubling of the repeat
rate, a halving of host coverage, and the near-total loss of the `Remove`
action.

**Two dependency pins are required that no repo declares.** Without
`pyarrow==15.0.2` nothing imports at all. Without the secondary pip index the
CPU torch install fails.

**Trace capture must run in sampling mode with per-episode torch seeding.** The
earlier plan to capture in greedy mode for determinism is dead, since greedy is
a materially different and much worse policy.

**Two metrics discriminated on first trial.** Consecutive repeat rate and
distinct hosts touched cleanly separated two policies of known differing
quality. Both are candidates for the collaboration quality metrics work.

## Open items

1. Fix the parallel seeding so each episode is seeded from its own index.
2. Port the local `evaluation.py` edits to `~/cage/repos` and rebuild the image,
   or they are lost with the container.
3. Quantify the parallel versus serial gap with a matched run, to turn a code
   reading into a measured effect.
4. Report the parallel defect to Cybermonic.
5. Write a standalone trace logger. `full.txt` is unusable, since observations
   are written as truncated torch tensor reprs with elided values.
6. Build the H-MARL image and reproduce its baseline.
7. Re-verify the image and the -196.06 figure on the Alienware and the
   PowerEdge, as a portability check.

## Notes on the trace format

`actions.txt` is usable. Actions are logged per step for all five agents with
readable names, for example `Remove public_access_zone_subnet_user_host_0`.
Host names carry zone, subnet, host type and index.

`full.txt` is not usable. Observations appear as

```
tensor([[ 1.,  0.,  0.,  ...,  0.,  0., -1.],
```

The ellipsis is real elision from `str()` on a tensor. Values are gone and
cannot be recovered.

Also absent from all output files. Per-step reward, mission phase, ground truth
red state, episode boundaries, and timestamps. Episodes are concatenated with
`actions: (` as the only separator.

The logger should be written fresh rather than extending this. Borrow the setup
code from `run_evaluation` and discard the rest.
