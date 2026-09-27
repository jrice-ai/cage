# CAGE 4 Baseline Reproduction Notes

## Overview

Working record for CybORG CAGE Challenge 4 as a substrate for human supervision
experiments. Sections are chronological; later sections supersede earlier ones
where noted.

What the file establishes, in order of appearance:

- A pinned container that reproduces the published KEEP score, then the
  published H-MARL Expert score, bit-identically across two machines.
- Nine defects in the evaluation tooling: five upstream (one traced to the
  challenge's reference `evaluation.py`, present in two independent
  submissions), four local. Each is recorded with its reproduction.
- A trace logger and a 100-episode reference corpus, with the sampling-noise
  floor and variance decomposition needed to read any arm comparison.
- A programmatic oracle harness. Against the stock red agent, nine rules and a
  seven-point budget sweep show action-substitution supervision loses to
  converged KEEP at every intervention rate.
- Two published recovery-precision criteria that disagree by 350x on the same
  agent, and a ground-truth rule that scores 100 percent on one of them while
  losing by 333 points.
- A cross-paper provenance finding: a benchmark table that mixes a shared
  artifact with a retrained one under the same citation format.
- An impact-focused red agent, hand-specified from a published planner schema,
  under which the same oracle rule that lost by 333 wins on every episode. The
  supervisory condition the programme needs exists from that section on.
- A second defender, H-MARL Expert, through the same ladder under both
  adversaries, in a harness that reproduces its authors' evaluation to the
  digit. The adversary result and the verb result hold across two
  architectures; the investigate result is smaller, takes the form of tail
  compression, and the step records rule out the obvious explanation for it.
- The mechanism test: each defender's own trainer continued under the
  deployment adversary. H-MARL's trainable part does not adapt in five
  million steps. KEEP's trainer from the shipped weights is a random walk
  at the shipped learning rate (a twentieth to a fifth of the excess loss
  recovered at 2,000 episodes, below the start at seventeen of twenty
  checkpoints over 10,000, stock competence lost every time) and stands
  still at a tenth of it; the supervisor recovers about half the excess
  loss of whichever policy it is given, so its endpoint moves by a sixth of
  what retraining changes. Three defects in KEEP's trainer and one in
  H-MARL's, found on the way.

All measurements before "The adversary determines whether supervision helps"
are against `FiniteStateRedAgent`. Arm definitions and per-arm numbers live in
ARMS.md; this file records what they mean.

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
| `adityavs14/Hierarchical-MARL` | H-MARL Expert; built later as `cage-hmarl:dev` (Ray 2.10), weights md5-identical to Trident's copy |

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

**Adversary scope.** Every measurement in this file up to the section "The
adversary determines whether supervision helps" is against
`FiniteStateRedAgent`, the stock CC4 red agent, which selects hosts at random.
Sections from that point on name their adversary explicitly.

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


## Trace logger

Written to replace the unusable `full.txt` output. Standalone, does not import
or extend `evaluation.py`.

Location

```
~/cage/scripts/capture.py
```

Run

```bash
docker run --rm -it -v ~/cage:/work cage-keep:dev \
  bash -c "cd /opt/cage/cage-4-submission && \
    python3 -u /work/scripts/capture.py --episodes 3 --out /work/data/traces/v1"
```

Output is one JSONL file per episode, named `ep_NNNNN.jsonl`. Each file is a
header record, one record per step, and a footer record. A 499 step episode
gives 501 lines.

### Record contents

Header carries episode id, seed, CybORG version, scenario, episode length,
agent name and team, the full host list, the host to subnet map, and the phase
reward table pulled from `BlueRewardMachine.phase_rewards`.

Step records carry step index, mission phase, raw per agent observation, action
index, executed action as a readable string, per agent reward, step reward,
cumulative reward, and a `truth` field holding red session counts and the set
of hosts with red presence.

Footer carries step count, total reward, and wall clock seconds.

### Design decisions

**Raw CybORG observations, not the wrapper encoding.** `Submission.wrap()`
returns KEEP specific graph tuples that are not JSON serializable and would not
transfer to another agent. The logger records
`cyborg.get_observation(agent_name)` instead, which is agent faithful and
wrapper independent.

**Per episode seeding.** Each episode constructs its own `CybORG` instance and
seeds torch, numpy and random from `base_seed + episode_index`. Episode N is
therefore determined by N alone, independent of which process or machine runs
it. This is the fix for the defect found in `run_evaluation_parallel`, applied
from the start rather than retrofitted.

**Sampling mode, not greedy.** Greedy selection scores -550 against -196 and is
a materially different policy. Capture has to run the agent that was actually
evaluated.

**Ground truth kept separate.** Red presence is read from `state.hosts` and
`state.sessions` and written to a distinct `truth` field. This is Tier 3 data.
It exists so decisions can later be scored independent of reward. It must never
reach a human supervisor display.

### Verification

Determinism was confirmed by capturing the same three episodes twice to
different directories and diffing, excluding the footer since `wall_seconds` is
a timing measurement.

```bash
for i in 0 1 2; do
  diff -q <(grep -v '"record": "footer"' ~/cage/data/traces/v1/ep_0000$i.jsonl) \
          <(grep -v '"record": "footer"' ~/cage/data/traces/v1check/ep_0000$i.jsonl) \
    && echo "ep $i identical"
done
```

All three identical. Rewards were -154.00, -179.00 and -195.00 on both runs.

Stronger evidence, episode 0 returned -154.00 in the first pilot run and again
after several rounds of script edits. Determinism has held across code changes,
not just across consecutive invocations.

Throughput is roughly 16 seconds per episode on the Surface, close to the
`evaluation.py` serial figure, so the logging overhead is small.

## CybORG internals discovered

Found by probing rather than from documentation. Recorded here because the
bridge and the escalation gate will need the same handles.

| Need | Location |
|---|---|
| Mission phase | `cyborg.environment_controller.state.mission_phase`, integer |
| Phase reward table | `ec.team_reward_calculators["Blue"]["BlueRewardMachine"].phase_rewards` |
| Red presence per host | `state.hosts[name].sessions`, keys starting `red` |
| Red session totals | `state.sessions["red_agent_N"]` |
| Host to subnet map | `state.hostname_subnet_map` |
| Host to IP map | `state.hostname_ip_map` |
| Executed action | `cyborg.get_last_action(agent_name)` |
| Raw observation | `cyborg.get_observation(agent_name)` |

The scenario holds 97 hosts and six red agents. Only `red_agent_0` has a
session at reset.

### `get_reward_breakdown` is broken in CC4

`cyborg.get_reward_breakdown(agent)` raises

```
AttributeError: 'AgentInterface' object has no attribute 'reward_calculator'
```

The method at `SimulationController.py:1116` returns
`self.agent_interfaces[agent].reward_calculator.host_scores`, but
`AgentInterface` exposes only `create_reward_calculator`. The attribute does
not exist. This is dead code in the released environment, not a calling error.

Per host reward attribution is therefore unavailable through the public API.
`BlueRewardMachine` exposes `phase_rewards` and `get_phase_rewards`, which give
the zone weighting per phase, so the weighting is recoverable even though the
per step attribution is not.

### Reward is broadcast, not per agent

The reward dict returned by `step()` holds the same value for all five blue
agents, for example

```
{'blue_agent_0': -1, 'blue_agent_1': -1, 'blue_agent_2': -1,
 'blue_agent_3': -1, 'blue_agent_4': -1}
```

This is the shared team reward repeated, not five independent signals. The
logger takes one value rather than averaging.

Consequence for later work. There is no reward signal attributable to an
individual agent or an individual decision. Any measure of whether a specific
action was correct has to be built from ground truth, not from reward.

## Observation sparsity

The most consequential finding for the legibility layer.

`get_observation` returns the result of the action that just resolved, plus any
passive alerts raised in that agent's zone. It does not return a standing
picture of network state. There is no such picture anywhere in the environment.

Only the observation from `reset()` is a full inventory. Every subsequent
observation is an event report.

### What a typical step looks like

An agent that ran `AllowTrafficZone` sees

```json
{"success": "FALSE",
 "message": [[false, false, false, false, false, false, false, true],
             [false, false, false, false, false, false, false, true],
             [false, false, false, false, false, false, false, true],
             [false, false, false, false, false, false, false, true]]}
```

A boolean and a four by eight message grid from the other agents. Nothing
about hosts, compromise, or network state.

### What a substantive step looks like

```json
{"admin_network_subnet_user_host_1": {
   "Processes": [{"Connections": [{"local_port": 49473,
                                   "local_address": "10.0.184.135"}]}, ...],
   "Interface": [{"ip_address": "10.0.184.135"}],
   "System info": {"Hostname": "admin_network_subnet_user_host_1",
                   "OSType": "LINUX", "OSDistribution": "KALI", ...}}}
```

Hostname, IP, connections, operating system. Note `OSDistribution: KALI`, which
appears to mark a compromised host. Worth confirming whether that is a
deliberate detection cue or a scenario authoring artifact, since if deliberate
it is a signal a human could read directly.

### Rate

Measured over episode 0, counting observations with more than the two baseline
keys

```
364 substantive observations out of 2,495 agent-steps, 14.6%
```

Notably, the first substantive observation in the episode came from a `Sleep`
step. `Sleep` produces no action result, so that content is passive detection
of activity in the agent's zone rather than a response to anything the agent
did. The observation stream therefore carries both action results and
unsolicited alerts.

### Timing convention

The logger reads observations after `step()`. Because the environment emits
event results, the pre step observation at step N is byte identical to the post
step observation at step N-1. Every observation is captured exactly once. It is
attributed to the step that produced it rather than the step that consumed it.

Recorded here because anyone reading the traces needs to know the convention.

## Three rates that size the human condition

All from the sampled 100 episode run and episode 0 of the trace corpus.

| Measure | Rate | Per episode |
|---|---|---|
| Substantive observations | 14.6% | roughly 364 |
| Consequential actions | 20.3% | roughly 505 |
| Restore only | 3.09% | roughly 77 |

An episode is 499 logged steps across five agents, so 2,495 agent-steps.

A Restore only escalation gate yields roughly 77 decisions per episode, which
is a session length a person could plausibly sustain. Gating all consequential
actions yields roughly 505, which is not. Gating uniformly would mean asking a
supervisor to approve `Sleep` several hundred times.

These numbers were derived from data rather than assumed, and they constrain
the escalation gate design directly.

## Revised open items

1. Capture a real corpus, 50 episodes or more, and parallelize it correctly
   with one environment per episode seeded from its index.
2. Run stratification measures over that corpus. Per episode correctness
   variance, event rate, compromise cascade shape.
3. Fix the parallel seeding in `evaluation.py` and quantify the parallel versus
   serial gap with a matched run.
4. Report the parallel defect and the `get_reward_breakdown` bug upstream.
5. Build the H-MARL image and reproduce its baseline.
6. Re-verify the image, the -196.06 figure, and trace determinism on the
   Alienware and the PowerEdge.
7. Confirm whether `OSDistribution: KALI` is a deliberate compromise marker.
8. Design the accumulation layer. The environment emits events and forgets, so
   a human facing view has to maintain state that neither CybORG nor the agents
   maintain. This is the substance of the legibility problem and it cannot be
   solved by display design alone.

## Trace logger defect found and fixed

The first 100 episode corpus was invalid. Worth recording because the output
looked plausible and nothing failed.

The logger bound a reference to the simulator state once at episode setup

```python
state = cyborg.environment_controller.state
```

`env.reset()` replaces that object rather than mutating it. The reference then
pointed at an orphan for the rest of the episode. Mission phase and red ground
truth were frozen at their initialization values and written unchanged to all
499 step records.

Symptoms that gave it away

```
phase first-seen: {0: 0}
sum of red_hosts counts across episode: 499
```

Phase never advanced, and red presence was exactly one host on every step. Both
are impossible. `mission_phases` for a 500 step episode is `(167, 167, 166)`,
and `SimulationController.py:227` calls the phase check every step, so phases
should advance at 167 and 334.

After the fix, reading through the controller each step

```
phase first-seen: {0: 0, 1: 168, 2: 335}
red hosts min/max/final: 1 45 44
```

The reward was never affected, since it comes from `step()` rather than from
the cached reference. The -196.06 reproduction and the -187.32 corpus mean both
stand. Only the two fields added by the logger were wrong.

Lesson for the bridge. Anything read from simulator state must be read through
the controller at the point of use. Caching references across a reset is silent
and the output stays well formed.

## Red and green action logging

Added after ground truth alone failed to explain reward variance.
`cyborg.get_last_action` works for red and green agents as well as blue.

Red actions come back as readable strings with targets, for example

```
[PrivilegeEscalate contractor_network_subnet_user_host_6]
[DiscoverRemoteSystems 10.0.134.0/24]
[DegradeServices operational_zone_b_subnet_user_host_5]
```

Green actions distinguish `GreenLocalWork` from `GreenAccessService` and carry
the target IP.

Storage decisions. Red actions are filtered to drop `Sleep`, since most of the
six red agents idle most steps. Green is stored as a per step count by action
type rather than as 63 individual records.

## Variance analysis, KEEP against itself

Run over 100 episodes of KEEP in sampling mode, seeds 0 to 99. Reward range
-113 to -527, a 4.7x spread.

Measures that do **not** explain the spread, comparing worst 20 episodes
against best 20

| Measure | Worst 20 | Best 20 |
|---|---|---|
| BlockTrafficZone | 173.8 | 162.2 |
| Restore | 77.5 | 74.5 |
| Remove | 98.2 | 101.7 |
| Analyse | 260.0 | 272.9 |
| Sleep | 934.1 | 934.0 |
| Evictions, Remove plus Restore | 175.7 | 176.2 |
| Mean red hosts held | 22.1 | 23.0 |

Peak red host count also fails to separate. The worst episode peaked at 37
compromised hosts, the best at 41.

The measure that **does** explain it

| Red action | Worst 20 | Best 20 |
|---|---|---|
| Impact | 101.5 | 58.0 |
| DegradeServices | 92.0 | 59.5 |
| PrivilegeEscalate | 22.6 | 22.8 |
| ExploitRemoteService | 338.1 | 353.5 |
| DiscoverRemoteSystems | 28.3 | 29.7 |

Only the damage actions differ. Every reconnaissance and access action is flat.

Normalized by red presence, impacts per thousand host-steps ranged from 4.07 in
the best episode to 24.00 in the worst, with equal eviction pressure from blue
in both.

Conclusion for a fixed policy. Red reaches the same places and holds the same
ground regardless. What varies is how often it chooses to cause damage, drawn
from the `FiniteStateRedAgent` transition matrix and fixed at seed.

## Three policy comparison

Matched seeds 0 to 99, same environment, three action selection policies. Run
to test whether the reward has construct validity, after the within policy
analysis suggested outcome was driven by uncontrollable factors.

| Policy | Mean | Stdev | Min | Max |
|---|---|---|---|---|
| KEEP sampled | -187.3 | 61.2 | -527 | -113 |
| KEEP greedy | -552.2 | 343.7 | -1746 | -125 |
| Sleep only | -6592.7 | 1340.5 | -10426 | -3761 |

The greedy mean of -552.2 matches the -550.45 obtained earlier through
`evaluation.py`, from an independent implementation and a different seeding
scheme.

Red impact actions under each policy

| Policy | Impact mean | Stdev |
|---|---|---|
| KEEP sampled | 161.8 | 48.9 |
| KEEP greedy | 195.2 | 48.0 |
| Sleep only | 738.2 | 81.0 |

### Findings

**The reward measures defensive quality across a 35x range.** A policy that
does nothing scores -6593. KEEP scores -187. Construct validity is not in
question.

**Better policies reduce variance, not just the mean.** Standard deviation
scales with policy quality, 61.2 against 343.7 against 1340.5, a 22x spread.
This is variance reduction rather than a level shift.

**The mechanism is impact suppression.** KEEP cuts red impact actions by 78
percent against doing nothing. The earlier finding that blue cannot influence
red aggression holds only within a fixed policy, where blue behavior is
identical by construction. Across policies blue plainly does influence it.

**Defensive value scales with threat.** Splitting episodes by red aggression
under the Sleep arm, the gap between Sleep and KEEP is 5,621 points in the 20
least aggressive episodes and 7,206 in the 20 most aggressive.

### Consequence for the research design

The constraint is not construct validity. It is headroom.

KEEP is close enough to a ceiling that a supervisor has little room to improve
on it. Working against KEEP means a standard deviation of 61 on a mean of -187
with a best observed episode of -113. Detecting a supervision effect there
would require a large effect against a floor, which is precisely the condition
the meta analysis predicts human AI combinations fail.

This argues directly for running the human arm against a degraded policy rather
than the converged one. A mid training checkpoint in the greedy performance
range, standard deviation around 340, leaves real room for supervision to
matter. That is an argument for building the competence checkpoint pool, now
made from measurement rather than intuition.

### Note on the Sleep baseline

The Sleep arm passes action index 0 through KEEP's graph wrapper. A random
policy arm was attempted and abandoned, since sampling the action space raises

```
IndexError: list index out of range
```

in `wrapper/graph_wrapper.py:40`, where `a_id // MAX_ACTIONS` indexes a subnet
list. The wrapper's action space is not uniformly samplable.

## Capture throughput

100 episodes, 12 workers, on the Surface

```
wall 354s, 3.5s per episode effective
```

Serial is roughly 16s per episode. Parallel per episode wall time rises to
around 40s under contention, but effective throughput is 4.5x better.

Verified that parallel and serial capture produce byte identical episodes,
excluding the footer `wall_seconds` field.

```bash
for i in 0 1 2 3 4 5; do
  diff -q <(grep -v footer ser/ep_0000$i.jsonl) \
          <(grep -v footer par/ep_0000$i.jsonl) && echo "ep $i identical"
done
```

All six identical. This is the property `run_evaluation_parallel` lacks, and
the difference is per episode seeding rather than one seed shared across
prebuilt environments.

## Programmatic oracle experiments

Run to bound the headroom available to a supervisor before building any
display or running any participant. The question was whether perfect knowledge
of the thing blue cannot see, namely which hosts hold red sessions, translates
into better outcomes.

A programmatic oracle rather than a human one, deliberately. It needs no
display, no control surface and no participant, and it answers the stronger
question of what any supervisor could do through this channel.

Script at `scripts/oracle.py`. The override mechanism wraps
`GraphWrapper.action_translator`, which returns a CybORG action object, so
substitutions slot in before execution and all of KEEP's observation
processing runs untouched. Verified transparent by running `--rule none` and
recovering KEEP's exact per episode rewards.

### Rules tested

| Rule | Behavior |
|---|---|
| none | KEEP unmodified, control |
| O1 | Restore any compromised host in the agent's subnets |
| O2 | Override unless KEEP is already acting on a compromised host |
| O3 | As O1 but Remove rather than Restore |
| O4 | Restore only in zones flagged expensive |
| O5 | Budget limited to 77 Restores per episode, targets ranked by phase reward weight |
| O6 | Never adds an action. Replaces Restore or Remove aimed at a clean host with a no-op |
| O7 | Target scramble control. Keeps KEEP's action type, randomizes the hostname to any owned host |
| O8 | As O6 but restricted to Restore, with a 30-step memory permitting restores on hosts impacted recently |

Source-accurate descriptions of all eight rules are in `ARMS.md`.

The budget of 77 in O5 matches KEEP's own observed Restore rate, so the
comparison is perfect targeting against learned targeting at equal action cost.

### Results, 100 episodes each, seeds 0 to 99

| Arm | Mean | Stdev | Delta vs KEEP | Better | Overrides/ep |
|---|---|---|---|---|---|
| KEEP, control | -187.32 | 61.24 | reference | | 0 |
| O6, decline only | -201.49 | 168.93 | -14.17 | | 270.7 |
| O5, budget limited | -238.56 | 48.04 | -51.24 | | 77.0 |
| O5c, alternative cost model | -246.05 | 65.56 | -58.73 | | 77.0 |
| O1 | -520.29 | 93.43 | -332.97 | 1/100 | 401.8 |
| O2 | -523.19 | 97.98 | -335.87 | 1/100 | 403.2 |
| O3 | -5803.89 | 1328.90 | -5616.57 | 0/100 | 2255.1 |

Every rule performs worse than the unmodified policy. O1, O2 and O3 beat KEEP
on at most one episode out of a hundred.

O1 and O2 converge at -520 and -523 despite different logic. O2 was intended as
the conditional rule, overriding only when KEEP is not already acting on a
compromised host, but it agrees just 1.4 times per episode. With 20 to 45 hosts
compromised throughout an episode the condition is always satisfied, so the
conditional never binds and O2 degenerates into O1.

O3 at -5803.89 sits close to the do-nothing floor of -6592.68, with a standard
deviation of 1328.90 against the floor's 1340.47. Forcing Remove every step
puts blue in the same performance regime as not playing.

These three were initially reported from two-episode smoke tests at -576.50,
-541.50 and -4963.00. The direction was correct in every case and the magnitude
was optimistic by 10 to 17 percent. Smoke tests carried direction reliably and
magnitude poorly.

O5 is the fair comparison and the informative one. At equal action budget with
correct phase aware zone weighting, perfect targeting loses to learned
targeting by 27 percent.

### Agreement between oracle and policy

Across 77 overrides per episode, O5 and KEEP agreed on the target roughly
**0.2 times per episode**. They are not solving the same problem.

KEEP's Restore targets in a representative episode, by zone

```
operational_zone_b   13
restricted_zone_b    12
restricted_zone_a    12
operational_zone_a    8
office_network        7
admin_network         4
public_access         1
```

Roughly proportional to how many hosts each agent owns, not concentrated on
the zones the reward table weights most heavily.

### Eviction precision against ground truth

Measured over 20 episodes of the KEEP arm, counting every Remove and Restore.

```
evictions on a currently compromised host:   486
evictions on a clean host:                 3,185
```

**Precision is 13 percent.** Roughly seven out of eight evictions target hosts
with no red session at the moment of action.

Checking whether those evictions are anticipatory, using a 20 step window in
each direction

```
of 3,185 clean host evictions
  compromised within the next 20 steps:    146   (4.6%)
  compromised within the prior 20 steps:   821   (25.8%)
  neither:                               2,273   (71.4%)
```

They are not anticipatory. Nearly three quarters have no relationship to red
presence in either direction.

### The result that does not fit

O6 suppresses exactly those apparently wasted evictions and substitutes a
no-op. It never adds an action, so it can only differ from KEEP where ground
truth says KEEP was wrong.

Performance gets worse, -201.5 against -187.3, and the standard deviation
nearly triples, from 61.2 to 168.9.

Verified that this is a property of declining rather than of the substitute.
Running O6 with `Sleep` instead of `Monitor` produced different per step traces
but identical aggregate statistics to full precision, so the choice of no-op
does not drive the result.

### What can and cannot be claimed

**Can be claimed.** Six perfect information oracle rules, including one matched
on action budget with correct phase aware zone weighting, all fail to improve
on a converged MARL policy in CAGE 4. The policy's eviction precision against
current compromise is 13 percent, and those evictions are not anticipatory.
Suppressing them degrades performance and destabilizes outcomes.

**Cannot be claimed.** Why. Something about that eviction behavior is load
bearing in a way that current compromise ground truth does not capture, and the
data collected so far cannot say what.

**Should not be claimed.** That there is no headroom for supervision. These
rules test one intervention channel, remediation retargeting given perfect
knowledge of compromise. They say nothing about escalation timing, novelty
detection outside the training distribution, or objective divergence where an
operator's priority differs from the coded reward.

### Consequence for the research design

**SUPERSEDED — see "Two criteria, two answers" and "The adversary determines whether supervision helps" below.**

**Ground truth compromise is not a valid correctness criterion for blue actions
in this environment.** This is the operationally important finding and it holds
regardless of the unexplained mechanism.

An escalation gate keyed on current compromise would fire on the wrong signal.
A supervisor asked to check whether a host is actually compromised before
approving a Restore would be applying a criterion that measurably degrades
performance. Any per decision correctness metric built on compromise state
inherits the same defect, which is directly relevant to the metrics question
in E4.

The supervision study should not be built around the retargeting channel. The
remaining candidates named in the pathway documents are untested here and
remain open.

### Open hypotheses for the eviction behavior

Listed in rough order of expected payoff, for a later session.

1. **Decoy interaction.** `DeployDecoy` creates fake services. A host where red
   interacts with a decoy would show activity without holding a session, so it
   would read as clean under the current ground truth definition while being a
   legitimate target. Check whether clean host evictions concentrate on hosts
   with decoys previously deployed.
2. **Detection noise.** Green `LocalWork` can raise false positive alerts. If
   clean host evictions cluster on hosts that recently produced alerts, KEEP is
   responding correctly to its observations and the imprecision is measured
   against the wrong reference.
3. **Active versus passive.** O6 substituted passive no-ops. Substituting a
   different active action, `DeployDecoy` or `Analyse` on the same host, would
   show whether the value lies in acting at all rather than in eviction
   specifically.
4. **Training distribution mismatch.** Reading `train.py` would show which red
   agents and reward shaping KEEP trained against. If the training red behaves
   differently from `FiniteStateRedAgent`, the evictions may be vestigial
   responses to patterns that do not occur in evaluation.

Hypotheses 1 and 2 share a script and are cheap. They are the natural opening
for the next session.

## Reading the reward function

After six oracle rules failed to improve on KEEP, the source was read rather
than probed. Four levels down, the mechanism became clear.

### What Restore actually does

`Restore` is a reimage, not an eviction. Its docstring claims a flat -1
penalty, which is **not implemented**. The chain runs

```
Restore.execute
  -> RestoreFromBackup.execute
    -> RestoreFromBackup.execute_targeteted_local_action
      -> Host.restore
```

`Host.restore` rebuilds the host from its original attributes. It resets
`files`, `sessions`, `processes`, `services` and `ephemeral_ports`, and clears
`events`. Red sessions are wiped, because `sessions` is rebuilt from
`original_sessions`.

Decoys are processes. So **restoring a host destroys every decoy blue has
deployed there.**

`Restore` also has `duration = 5`, so the acting agent is occupied for five
steps.

`restore_count` is incremented per host but is used nowhere. The one call site
that would have consumed it is commented out at `SimulationController.py:557`.

### What the reward actually counts

`BlueRewardMachine.calculate_reward` sums exactly three things.

```python
for agent_name, action in action_dict.items():
    if isinstance(action, Impact):            hostname = action.hostname
    elif isinstance(action, GreenAccessService) \
      or isinstance(action, GreenLocalWork):  hostname = state.ip_addresses[...]
    else:                                     continue
```

Every blue action hits the `continue`. **No blue action carries a direct
reward or penalty.**

The three terms are

| Term | Trigger |
|---|---|
| LWF | a green agent's `GreenLocalWork` returns success False |
| ASF | a green agent's `GreenAccessService` returns success False |
| RIA | a red agent's `Impact` returns success True |

Note that despite the name meaning Red Impact slash Access, RIA requires
`isinstance(action, Impact)`. **Red merely holding sessions costs nothing.**
This is why compromise count never correlated with reward across the corpus,
and why an episode with 45 compromised hosts could score -113.

Blue influences the score only by changing whether green can work and whether
red's Impact succeeds. Everything blue does is scored through second order
effects.

### Demonstration: information gathering is reward invisible

Three baseline arms were run over the same 100 seeds. Each produces a
completely different action stream.

| Arm | Every agent, every step | Mean | Stdev |
|---|---|---|---|
| Sleep | `Sleep()` | -6592.68 | 1340.47 |
| Analyse | `Analyse` on host 0 | -6592.68 | 1340.47 |
| Monitor | `Monitor` | -6592.68 | 1340.47 |

Identical to the last decimal, and identical episode by episode across all 100.
Verified that the traces themselves differ while the rewards match.

```
ep 00000 traces differ
ep 00001 traces differ
ep 00002 traces differ
rewards identical: True
first 6 sleep   [-7391.0, -8417.0, -5866.0, -6111.0, -6402.0, -4691.0]
first 6 analyse [-7391.0, -8417.0, -5866.0, -6111.0, -6402.0, -4691.0]
```

**A policy that only gathers information scores identically to one that does
nothing at all.** Three of the eight blue actions are invisible to the reward
in isolation.

### This explains every oracle result

KEEP's target selection weighs at least four considerations, of which current
compromise is one.

1. Does restoring prevent a future Impact
2. Does taking the host offline cause green work to fail
3. Does the reimage destroy decoys already deployed there
4. Does the five step duration lock the agent out of acting

Only the first two enter the reward. The oracle rules optimized against
compromise alone, which is one term of four and the one the reward does not
score directly.

That accounts for the full pattern

- **13 percent eviction precision** against current compromise, because
  compromise is not the criterion
- **0.2 agreements per episode** between oracle and policy, because they
  optimize different objectives
- **O7 at -512** when targets were randomized, because the other three terms
  still carried 325 points of value
- **O1 and O3 collapsing** to near baseline, because forcing Restore every step
  continuously destroys the team's own decoys and locks agents out five steps
  at a time

### Superseding the earlier open question

The earlier oracle section stated that the eviction behavior was load bearing
in a way the data could not explain. It can now be explained. Restore is a
multi cost action whose value depends on accumulated deception investment and
agent availability, neither of which appears in compromise ground truth.

Hypotheses 1 and 2 from that section were tested and neither holds in strong
form. Clean host evictions show a 1.5x enrichment for recent observation
against an 18.1 percent base rate, and 1.3x for recent decoy against 7.9
percent. Real but weak. The mechanism is the cost structure, not the targeting
signal.

## Blocked agent steps

A measurement error found while checking action counts, affecting several
earlier tables.

39.3 percent of blue agent-steps report `success == IN_PROGRESS`. During those
steps `get_last_action` reports `Sleep` regardless of what the agent proposed.
Verified by cross tabulating action against the blocked flag over one episode

```
AllowTrafficZone     blocked=False    679
Analyse              blocked=False    248
BlockTrafficZone     blocked=False    149
DeployDecoy          blocked=False    183
Monitor              blocked=False     99
Remove               blocked=False    140
Restore              blocked=False     57
Sleep                blocked=True     940
```

Every non Sleep action appears only when free. Every Sleep appears only when
blocked. **Voluntary Sleep is zero.** The Sleep counts in the earlier action
mix tables were blocked time, not idling.

Restore, Remove, Analyse and DeployDecoy counts were never inflated, so the
eviction precision figures, the oracle results and the policy comparison all
stand.

A `blocked` flag is now captured per agent per step.

### Corrected action mix, free decisions only

Over 20 episodes per arm, excluding blocked steps.

| Action | KEEP sampled | KEEP greedy |
|---|---|---|
| AllowTrafficZone | 43.0% | 51.7% |
| Analyse | 17.6% | 6.3% |
| DeployDecoy | 10.6% | 14.9% |
| BlockTrafficZone | 10.4% | 6.7% |
| Remove | 6.8% | 0.0% |
| Monitor | 6.4% | 17.4% |
| Restore | 5.2% | 2.9% |

Blocked rates were 38.5 percent for sampled KEEP, 24.8 percent for greedy, and
50.1 percent for the Analyse baseline. Greedy is blocked less because it barely
uses the long duration actions.

Greedy's `Remove` count is 3 out of 37,505 free decisions.

### Corrected rates for gate design

The earlier figures were shares of all agent-steps. These are shares of
decisions the agent was actually free to make, which is the relevant
denominator for an escalation gate.

| Measure | Share of free decisions | Per episode |
|---|---|---|
| Consequential actions | 33.0% | roughly 500 |
| Restore only | 5.2% | roughly 82 |
| Reward invisible, Analyse plus Monitor | 24.0% | roughly 370 |

The last row is new and matters. **Roughly a quarter of blue's free decisions
are actions the reward cannot see.** Escalating those to a human means asking
for approval of decisions whose consequences are unobservable within the
episode score.

## Consolidated consequences for the research design

**SUPERSEDED — see "Two criteria, two answers" and "The adversary determines whether supervision helps" below.**

**Compromise ground truth is not a valid correctness criterion.** Demonstrated
three ways. Precision against it is 13 percent. Perfect knowledge of it does not
beat the policy. And the reward function does not score compromise at all, only
successful Impact.

**Per decision correctness is structurally unmeasurable for a quarter of blue
decisions.** Analyse and Monitor are reward invisible. This is not a limitation
of the reward as a crude summary. It is structural blindness to part of the
action space, and it is a direct finding for the E4 metrics question.

**An escalation gate keyed on compromise would fire on the wrong signal.** A
supervisor asked to verify compromise before approving a Restore would apply a
criterion that measurably degrades performance.

**The retargeting intervention channel has no demonstrated headroom.** Six
perfect information rules, including one matched on action budget with correct
phase aware weighting, all lose to the learned policy.

**Untested channels remain.** Escalation timing, novelty detection outside the
training distribution, and objective divergence where an operator's priority
differs from the coded reward. None of these were addressed by the oracle work.

**A better oracle target now suggests itself.** Since the reward counts green
failures and blue actions cause them, the question worth testing is not which
host to restore but when blue is doing more damage than red. That is a
different rule and it is cheap to build.

## Policy seed decoupling

`capture.py` originally derived one seed per episode

```python
seed = base_seed + ep
torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
cyborg = CybORG(sg, "sim", seed=seed)
```

This ties environment generation and policy sampling to the same value, so
two arms cannot be compared with the environment held fixed. A `--policy-seed`
argument was added

```python
pseed = seed if policy_seed is None else policy_seed + ep
torch.manual_seed(pseed)
```

`np.random.seed` and `random.seed` remain on the environment seed. KEEP samples
through torch only, and leaving the other two streams alone avoids any risk of
CybORG drawing from global numpy state. The header record now carries both
`seed` and `policy_seed`, so an arm is self-describing.

Default behaviour is unchanged. Omitting the flag reproduces prior runs exactly.

Verification, two episodes at `--policy-seed 9000` against `corpus_v1`

```
ep 00000  blue diverges at step 0  reward -186.0 vs -154.0
ep 00001  blue diverges at step 0  reward -192.0 vs -179.0
```

Blue diverges immediately, the environment is unchanged, rewards differ.

## Null arm and the noise floor

`keep_null` is KEEP sampled, same 100 environment seeds as `corpus_v1`,
`--policy-seed 9000`. Only the policy's sampling luck differs. It is the
placebo against which any supervised arm must be read.

| Arm | Mean | Stdev | Better than corpus_v1 | Mean gain | Mean loss |
|---|---|---|---|---|---|
| corpus_v1 (KEEP sampled) | -187.32 | 61.24 | reference | | |
| keep_null (KEEP resampled) | -196.09 | 51.96 | 35/100 | +57.5 | -44.4 |
| oracle_O8 | -253.27 | 197.27 | 51/100 | +67.7 | -205.1 |

### Findings

**Resampling alone moves the mean 8.8 points and flips a third of episodes by
roughly 50.** Every arm comparison in this file is anchored to a single
sampling draw of KEEP. `corpus_v1` is one sample, not a canonical value.

**Per-episode improvement is strongly anti-correlated with baseline score even
when nothing is happening.** Correlation between per-episode delta and
`corpus_v1` score

```
keep_null   -0.712
oracle_O8   -0.272
```

The null arm shows the stronger effect. This is regression to the mean, and its
magnitude here means any claim of the form "the supervisor rescues episodes the
policy handled badly" requires the null arm as a control. Read against that
floor, O8's -0.272 is weaker than chance and carries no rescue signal.

**The oracle's gains are within noise, its losses are not.** O8 gains +67.7
against a null floor of +57.5. It loses -205.1 against a floor of -44.4, a
factor of 4.6, with standard deviation 197.27 against 51.96. An 81 percent
override rate against perfect Tier 3 ground truth reliably destroys value and
does not reliably create it.

### Consequence for the research design

The headroom question is not answered by this arm and cannot be. A rule
overriding 154 times per episode is a replacement policy, not a supervisor.
The human relevant region is a sparse gate near the 77 decisions per episode
sustainability figure, roughly 40 percent of O8's rate, and that region is
untested.

Any future arm comparison reports the null band alongside it.

## Oracle variant series

Rule definitions for O1 through O9 are in ARMS.md, "Rules tested." This section
records outcomes and interpretation only.

Eight rule variants plus revisions, `oracle_O1` through `oracle_O8`, n=100
where noted. None beat KEEP.

| Variant | Mean | Stdev |
|---|---|---|
| oracle_O5 | -238.56 | 48.04 |
| oracle_O5b | -187.32 | 61.24 |
| oracle_O5c | -246.05 | 65.56 |
| oracle_O6 / O6b | -201.49 | 168.93 |
| oracle_O7 | -511.95 | 165.48 |
| oracle_O8 | -253.27 | 197.27 |

`oracle_O5b` reproduces `corpus_v1` exactly on all 100 footers, confirming the
oracle harness is transparent when its rule does not fire. It is a valid k=0
control, captured deliberately with `--rule none`.

`oracle_O5` has the lowest standard deviation of any arm at 48.04, which
initially read as tail suppression. Percentiles refute it

```
corpus_v1    min -527  p10 -245  med -181  max -113
oracle_O5    min -478  p10 -288  med -238  max -155
oracle_O8    min -1092 p10 -536  med -184  max  -51
```

Every O5 percentile above the minimum is worse. The low variance comes from
consistent mediocrity, not from avoiding disasters.

O8's maximum of -51 is better than KEEP's best episode in 100 draws, and its
minimum of -1092 is roughly double KEEP's worst. Median is unchanged.

### Difficulty does not explain the deltas

Red aggression over the first 100 steps, counting `Impact`,
`ExploitRemoteService`, `PrivilegeEscalate` and `DegradeServices`

```
corr(delta, early_aggression)          -0.057
corr(delta, keep_score)                -0.272
corr(keep_score, early_aggression)     -0.183
partial corr(delta, agg | keep_score)  -0.113
```

Early red aggression carries no explanatory power for when supervision helps.

## Note on CC4 red behaviour

Red action distribution over 100 episodes

| Action | Count |
|---|---|
| ExploitRemoteService | 34455 |
| DiscoverDeception | 11727 |
| DegradeServices | 8598 |
| Impact | 8465 |
| AggressiveServiceDiscovery | 6160 |
| StealthServiceDiscovery | 6048 |
| DiscoverRemoteSystems | 2911 |
| PrivilegeEscalate | 2466 |

`DiscoverDeception` is the second most frequent red action, exceeding `Impact`
and `PrivilegeEscalate` combined. Red spends more effort identifying decoys
than on either escalation or damage. This is a property of CC4's red model
independent of any blue policy and is relevant to any work treating decoy
deployment as a defensive action.

## Two defects in local tooling

**Container writes are root owned.** Every trace directory captured so far is
owned by root, since the container runs as root against a bind mount. Symptom
is `Permission denied` on host side cleanup. Fix

```bash
sudo chown -R $(id -u):$(id -g) ~/cage/data/traces
```

and add `--user $(id -u):$(id -g)` to future `docker run` invocations.

**Episode id parsing by substring.** Analysis scripts used

```python
k = f.split('ep_')[1].split('.')[0]
```

Any output directory whose name contains `ep_` collapses every episode to one
key. `keep_null` contains the sequence and silently reduced 100 episodes to a
single data point, producing a well formed mean over n=1. Use positional
parsing

```python
k = os.path.basename(f)[3:-6]
```

This is the third defect in this project that produced plausible output rather
than an error, after the cached state reference that froze phase and ground
truth across a corpus. Arms should be checked for episode count before any
statistic is computed.

### 3. Trace header does not record the harness revision

The header records `rule` and `budget` but not the code revision that defined
the rule. `oracle_O5` and `oracle_O5c` both ran rule O5 and differ by 7.5
points; whether the O5 expression changed between them or only the sampling
did is not recoverable from the traces. Fix: write `harness_sha` from
`git rev-parse HEAD` into the header at run start. Applied from the next
experiment section onward; earlier arms are identified by reproduction where
possible and marked otherwise.

## Schema divergence between capture paths

The oracle harness writes a different record schema than `capture.py`, and
neither is a superset.

| Field | capture.py arms | oracle arms |
|---|---|---|
| raw per-agent observation | yes | no |
| `truth` (red sessions, hosts with red presence) | yes | no |
| `red_action` | no | yes |
| `n_compromised_owned` | no | yes |
| `proposed` / `overridden` | no | no |

The oracle arms lack Tier 3 ground truth, which was the stated reason for
logging it, so an override cannot be scored against the correct answer in the
arms where overrides occur. Neither path logs the counterfactual.

Before further capture, both writers should emit `truth`, `red_action`,
`n_compromised_owned`, `proposed` and `overridden`, so one reader handles every
arm.

## KEEP reference value and the sampling noise floor

Four sampling seeds over the same 100 environment seeds, `--policy-seed`
unset / 9000 / 9001 / 9002.

| Arm | Mean | Stdev |
|---|---|---|
| corpus_v1 | -187.32 | 61.24 |
| keep_null | -196.09 | 51.96 |
| keep_null_9001 | -198.44 | 83.33 |
| keep_null_9002 | -183.51 | 49.40 |

```
grand mean  -191.34
sd of means    7.08    se 3.54
95% CI      -199.66 to -183.02   (t, 3 df)
```

The published KEEP score of -193.68 falls inside this interval. The earlier
point reproduction of -196.06 understated the agreement.

### The bar for any arm comparison

Pairwise deltas between identical policies differing only in sampling seed

| Pair | Delta mean | Per-episode sd | Better |
|---|---|---|---|
| corpus_v1 vs keep_null | -8.77 | 72.82 | 35/100 |
| corpus_v1 vs keep_null_9001 | -11.12 | 101.11 | 43/100 |
| corpus_v1 vs keep_null_9002 | +3.81 | 72.11 | 43/100 |
| keep_null vs keep_null_9001 | -2.35 | 92.71 | 54/100 |
| keep_null vs keep_null_9002 | +12.58 | 62.15 | 66/100 |
| keep_null_9001 vs keep_null_9002 | +14.93 | 94.70 | 52/100 |

Identical policies differ by up to 26 points of mean and win up to 66 of 100
episodes. Arm stdev ranges 49.40 to 83.33, a 1.7x spread from sampling alone,
so `oracle_O5`'s stdev of 48.04 is inside the null range and was never anomalous.

Any arm reporting a delta under roughly 25 points, or a win rate under roughly
66 percent, has reported nothing. `oracle_O8`'s 51/100 is below the null range.

### Variance decomposition

```
mean within-episode sd across seeds   44.50   sampling luck
sd of per-episode means               36.39   situation difficulty
```

Sampling luck exceeds situation difficulty, ratio 1.22. Episodes carry real
intrinsic difficulty, but a perfect difficulty measure would explain at most
about 40 percent of outcome variance.

Consequence for stratification: episode difficulty must be estimated as a mean
over several policy seeds, not read from a single run. Labelling an episode
hard from one observation is mostly labelling sampling luck, which is the same
artifact that produces the -0.712 null correlation above.

Consequence for supervision: with the majority of outcome variance irreducible
at this competence level, a detectable supervision effect must be large. This
is a quantitative argument for running the human arm against a degraded policy,
where both variance terms are larger.

### Difficulty does not transfer across competence levels

Greedy KEEP is deterministic, so all of its between-episode variance is
situation rather than sampling luck.

```
sampled  within-ep sd  44.50   between-ep sd   36.39
greedy   within-ep sd   0.00   between-ep sd  343.75
corr(greedy score, sampled mean score) = -0.059
```

Greedy percentiles, n=100, same environment seeds

```
min -1746  p10 -1142  p25 -758  med -434.5  p75 -293  max -125
```

The distribution is smooth rather than bimodal, so the spread is a difficulty
gradient rather than a failure-mode statistic. Greedy's best episode at -125 is
close to sampled's best at -113: the degraded mode is competent on forgiving
situations and collapses on unforgiving ones.

**Difficulty is a property of the policy-environment pair, not of the
environment.** The same episode is not hard for both action-selection modes.
Stratification therefore cannot be computed once and reused across competence
levels; each level needs its own corpus at multiple policy seeds.

**Difficulty is 9.4x more legible at degraded competence**, with no sampling
noise to separate it from. This supplies a stopping criterion for any
competence checkpoint pool: train until between-episode variance dominates
within-episode variance, measurable in one 100-episode arm per candidate
checkpoint.

### The reward floor is action-insensitive

Three degenerate policies with byte-different action streams produce identical
statistics over 100 episodes.

| Arm | Action distribution (per episode) | Mean | Stdev |
|---|---|---|---|
| `arm_sleep` | Sleep 2495 | -6592.68 | 1340.47 |
| `arm_monitor` | Monitor 2495 | -6592.68 | 1340.47 |
| `arm_analyse` | Sleep 1250, Analyse 1245 | -6592.68 | 1340.47 |

`Monitor` executes automatically each step regardless of selection, and
`Analyse` gathers information without altering state. None of the three changes
the network, and the reward is identical to two decimals across all of them.

This resolves the earlier `arm_sleep` anomaly, where a corrected Sleep arm
returned the same mean as the mislabelled Analyse arm it replaced. Not a stale
output — the two policies genuinely score the same.

**Consequence.** CC4's reward is insensitive to blue actions that do not change
state. Pure information gathering buys nothing. Any supervisory metric built on
reward alone cannot distinguish a well-informed passive defender from an
oblivious one, which bounds what E4 collaboration-quality measures and C2
escalation designs can be validated against.

## Cross-machine reproduction

Verified on a second machine (Alienware, WSL2 Ubuntu, different
microarchitecture) from the repository plus `build/evaluation-fixes.patch`.

```
2.2.0+cpu 1.26.4 2.12.0 2.3.1
--distribute 1 --max-eps 2 --seed 0
  -194, stdev 76.36753236814714
```

Identical to fifteen significant figures against the reference machine.

Run first against pristine upstream `evaluation.py`, before applying the patch,
the same command returned **-154, stdev 32.53**. The difference is entirely the
unseeded policy sampling defect: upstream never calls `torch.manual_seed`, so
the result varies per machine and per invocation. With the fix applied the
output is bit-identical across hardware.

This is the seed-disclosure argument demonstrated rather than asserted.

## Capture throughput

Alienware, Intel Core Ultra 9 275HX, 24 physical cores (8 P + 16 E), no SMT.
24 episodes per configuration, KEEP sampled, seeds 0-23.

| Workers | Mean per-episode wall | Effective | Speedup | Efficiency |
|---|---|---|---|---|
| 1 | 14.45s | 14.45s | 1.00x | 100% |
| 2 | 15.25s | 7.63s | 1.89x | 95% |
| 4 | 15.40s | 3.85s | 3.75x | 94% |
| 8 | 17.30s | 2.16s | 6.68x | 84% |
| 12 | 19.57s | 1.63s | 8.86x | 74% |
| 16 | 21.01s | 1.31s | 11.01x | 69% |
| 20 | 23.85s | 1.19s | 12.13x | 61% |
| 24 | 26.98s | 1.12s | 12.86x | 54% |

Degradation is smooth and roughly linear from four workers onward, with no step
at the P-core/E-core boundary. The limiting factor is contention rather than
core heterogeneity. Throughput still improves at 24 workers but only 6 percent
over 20; the practical operating point is 12 to 16.

For comparison, the reference machine reached 3.5s effective at 12 workers.
This machine reaches 1.63s at the same worker count, a 2.1x improvement that is
mostly parallel efficiency rather than single-thread speed (14.45s vs 16.7s
serial).

Determinism verified across worker counts on this machine: episodes 0, 7 and 19
are byte-identical between 1 and 24 workers, excluding footer `wall_seconds`.
The property holds across hardware and across a 24x range in worker count.

**`oracle.py` parallel path segfaults above six workers on 24-core Arrow Lake.**
`{SIGSEGV(-11)}` from joblib workers at `--workers 12`; stable at 6. The same
machine runs `capture.py` at 24 workers without incident, so the fault is
specific to the oracle harness, which constructs and patches a CybORG instance
per worker.

The failure mode matters more than the cause: joblib reports the batch failed,
but workers that completed had already written their files. The budget-10 arm
left 12 well-formed episodes and the budget-20 arm left 60, in directories
indistinguishable from a successful 100-episode run. Any statistic computed
over them would be silently wrong.

Assert the expected episode count before computing anything over an arm.

## O5 budget sweep

Dose-response for the phase-aware budgeted oracle. 100 episodes per budget,
environment seeds 0-99, six workers, captured on the second machine.

| Budget | Mean | Stdev | Delta vs KEEP | Overrides/ep |
|---|---|---|---|---|
| 0 | -187.32 | 61.24 | reference | 0.0 |
| 10 | -186.33 | 52.32 | +0.99 | 10.0 |
| 20 | -200.44 | 65.00 | -13.12 | 20.0 |
| 40 | -216.15 | 65.21 | -28.83 | 40.0 |
| 77 | -246.05 | 65.56 | -58.73 | 77.0 |
| 150 | -312.01 | 57.15 | -124.69 | 147.8 |
| 300 | -368.92 | 72.59 | -181.60 | 206.2 |

Two incidental reproduction checks passed. Budget 0 returns -187.32 / 61.24,
identical to `corpus_v1` on the reference machine. Budget 77 returns -246.05 /
65.56, identical to `oracle_O5`, captured on different hardware at a different
worker count.

Override counts track the budget exactly up to 77 and saturate below it above
that: 147.8 at a budget of 150 and 206.2 at 300, where the rule's own
low-value-zone skip binds before the cap does.

### Findings

**The response is monotonic with no interior peak.** Reward declines roughly
linearly in override count, about -0.9 points per override from budget 20
onward. There is no intervention rate at which supervision helps.

**Only budgets 0 to 20 are inside the null band** of -11.1 to +14.9. Budget 10
at +0.99 is indistinguishable from doing nothing; budget 20 at -13.12 is inside
the band on the wrong side. From budget 40 the losses clear the floor
decisively.

**Agreements are near zero throughout**, 0.0 to 0.2 per episode. The rule
almost never endorsed KEEP's proposed action, so these arms measure action
substitution rather than review.

### Consequence for the research design

Across eight rules spanning blind intervention (O1, O3, O4), correction (O2,
O5), suppression (O6, O8) and a targeting control (O7), at rates from 10 to
over 400 overrides per episode, no configuration beats KEEP. The dose-response
establishes that the failure is directional rather than a matter of tuning. All
eight rules are now measured at 100 episodes; the three blind-intervention rules
beat KEEP on at most one episode each.

**SUPERSEDED — see "The adversary determines whether supervision helps" below.**
The bound stated here holds against `FiniteStateRedAgent` and does not
generalize. Against a damage-focused red agent the same rule family produces a
monotonic gain over the same budget range.

**Supervision experiments against converged KEEP are not viable.** The oracle
ceiling condition was run to bound achievable gain before any participant saw
anything, and the bound is at or below zero.

This does not bound supervision generally. It bounds action-substitution
supervision informed by ground truth about red presence. A supervisor with
different information, such as reward lookahead or counterfactual rollout, or a
different action space, such as retasking or priority reweighting rather than
per-action override, is untested.

The practical consequence is that the competence checkpoint pool moves from
argued-for to required, with the stopping criterion established earlier: train
until between-episode variance dominates within-episode variance.

## Restore and Remove serve different functions

Measured over 20 episodes of `corpus_v1`, comparing every eviction action
against `truth.red_hosts` at the moment of action. Roughly 29 of 97 hosts are
compromised at any time, so random targeting would hit about 30 percent.

| Action | On compromised host | On clean host | Precision |
|---|---|---|---|
| Remove | 483 | 1605 | 23.1% |
| Restore | 3 | 1580 | **0.2%** |

Remove is approximately at chance. Restore is 150 times below it. That is not
imprecision, it is avoidance: KEEP deliberately does not restore hosts red
currently occupies.

### Restore targeting is driven by host value, not by red

Restores split into two populations. Of 814 clean-host restores over ten
episodes, checked against a 20 step window in each direction

```
compromised within the prior 20 steps    353  43.4%
compromised within the next 20 steps      34   4.2%
neither                                  427  52.5%
```

Restores are ten times more likely to follow a compromise than to precede one,
so the 43.4 percent band is post-eviction repair. Widening the window does not
change this: the prior-only share is 44.8 percent at W=5 and 37.1 percent at
W=80, declining only because hosts reclassify into the forward window. The
repair lag is under five steps, not twenty.

The majority population is different. Of the 427 with no compromise in either
direction, **97.7 percent also have no recorded `DegradeServices` or `Impact`
on that host at any point in the episode.** Red has never touched them.

### What separates the no-history targets

n=417, host universe 107, over ten episodes.

| Host kind | Share of restores | Share of universe | Ratio |
|---|---|---|---|
| server | 66.9% | 38.3% | **1.75x** |
| user | 33.1% | 61.7% | 0.54x |

| Zone | Share of restores | Share of universe | Ratio |
|---|---|---|---|
| restricted_zone_a | 25.2% | 15.0% | 1.68x |
| operational_zone_a | 20.1% | 15.0% | 1.35x |
| operational_zone_b | 18.2% | 14.0% | 1.30x |
| office_network | 15.6% | 15.0% | 1.04x |
| restricted_zone_b | 11.8% | 15.0% | 0.79x |
| public_access_zone | 7.2% | 15.0% | 0.48x |
| admin_network | 1.9% | 11.2% | **0.17x** |

Every host in the top eight by restore count is a server, all in operational or
restricted zones. The eight range from 12 to 24 restores each across ten
episodes.

Mission phase is flat: 154, 146, 117 across three phases of roughly equal
length. This is steady background behaviour, not phase-triggered preparation.

Targets are spread across 85 of 107 hosts, so it is not a fixed small set, and
they carry a mean of 3.75 prior blue actions, so they are not untouched hosts
either.

The zones favoured are those the reward machine weights: operational and
restricted carry the services green agents depend on. `admin_network` at 0.17x
and `public_access_zone` at 0.48x are actively avoided.

Combined with the decoy finding, the behaviour KEEP appears to have learned is
to **periodically reimage valuable servers carrying little deception
investment, whether or not red is visible on them.** Red's damage is narrow and
concentrated while its reconnaissance is broad — 709 `ExploitRemoteService` and
251 `DiscoverDeception` against 148 `Impact` over two episodes — so a valuable
host can accumulate red artifacts without ever showing a session in
`truth.red_hosts`.

### Consequence for the research design

**SUPERSEDED — see "Two criteria, two answers" and "The adversary determines whether supervision helps" below.** The claim in this
section was measured against ground-truth sessions only. Rescored against
observable evidence, the same restores are 69.8 percent precise.

This is the strongest form of the finding. **Compromise state is not merely an
imperfect supervisory signal. It is close to orthogonal to what the best
available policy optimises for its most expensive action.**

- An escalation gate keyed on "is this host compromised" would fire on 45
  percent of restores and miss the majority entirely.
- A per-decision correctness metric built on ground truth scores KEEP's
  majority behaviour as error. That is exactly what the 0.2 percent precision
  figure does.
- A supervisor shown red's location would be shown a variable the policy
  demonstrably ignores most of the time.

This is a property of CAGE 4 rather than of KEEP specifically, and it bears
directly on E4's metrics question and on C2's choice of escalation trigger.

### O9, specified from measurement

The natural confirmation test, and the first rule in this series derived from
data rather than intuition.

Rank Restore candidates by zone reward weight and server status, weighted
inversely by accumulated decoy count on the host, excluding hosts currently
showing a red session. Budget 77 to match KEEP's own rate.

If O9 closes the gap, the oracle failures were targeting and the information
gap is identified. If it still loses, targeting is not the whole story and the
green-disruption channel becomes the next question.

### O9: aggregate target statistics do not reconstruct the decision rule

Two arms built from the measured restore-target skews — servers 1.75x,
operational and restricted zones 1.3 to 1.7x, decoy load half the average.
Ranking is zone penalty exposure summed across LWF, ASF and RIA for the current
phase, doubled for servers, divided by accumulated decoys on the host.

Three episodes, seeds 0 to 2. KEEP baseline on these seeds is -154, -179, -195.

| Arm | Behaviour | Mean | Overrides/ep | Agreements/ep |
|---|---|---|---|---|
| O9r | Rank all owned clean hosts, ignore KEEP's proposal | -260.00 | 77.0 | 0.0 |
| O9s | Keep KEEP's target unless it falls outside the top third | -813.67 | 77.0 | 15.0 |

O9s agrees with KEEP on 15 of 77 restores. A ranking derived from KEEP's own
aggregate target statistics predicts its per-decision choice roughly a fifth of
the time.

An earlier version used `-RIA + LWF`, inherited from O5, which inverts the
ranking: all phase reward entries are penalties, so operational_zone_a in phase
1 at `LWF -10, RIA -10` scored 0 while public_access_zone scored 2. Correcting
to the summed exposure changed agreement from 12.3 to 15.0 and made both arms
slightly worse. The sign was wrong and it was not the cause.

**Aggregate skews describe the distribution of KEEP's targets without
reconstructing the rule that produced them.** The features driving per-decision
selection are not among those measured, and are not visible in the current
trace schema.

O9s intervening less and scoring worse than O9r repeats a pattern seen in O6
and O8: partial intervention is consistently worse than full replacement. No
explanation for this is established.

## Two criteria, two answers

The same restores scored against two different definitions of a correct
recovery action, over 20 episodes of `corpus_v1`.

**Ground truth.** A host is compromised if it holds a red session, read from
`truth.red_hosts`. **Observable evidence.** A host is flagged if any substantive
observation has named it since the last Restore or Remove on that host, read
from the raw per-agent `obs` field. The second definition reconstructs the latch
Team UC describe implementing in their own wrapper: malicious process,
connection and file flags persist until Restore or Remove clears them.

| Criterion | Restore | Remove |
|---|---|---|
| Ground-truth session at decision time | **0.2%** | 23.1% |
| Observable evidence, latched | **69.8%** | 53.3% |

Roughly 29 of 97 hosts hold a red session at any time, so chance is about 30
percent. Against ground truth, Restore is 150 times below chance. Against
observable evidence it is 69.8 percent precise.

Restore's evidence-precision exceeds Remove's, reversing the ground-truth
ordering. This is consistent with Team Punch's report that Analyse on a
phishing-infected host surfaces only root-privilege artifacts, which Remove
cannot clear, so Remove fires on weaker evidence and misses more often.

### Why the two diverge

CC4 generates observable evidence that is not red presence, and red presence
that is not observable.

- `EnterpriseGreenAgent.LocalWork` has four outcomes, one of which raises a
  false-positive alert for blue. `AccessService` has a configurable chance of
  producing a spurious network event resembling red gaining user access.
- The environment emits events and forgets. Any persistence is built by the
  agent, and every top CC4 team built one. A flag therefore records that
  something was seen, not that red is present now.
- Red's damage is narrow and its reconnaissance is broad: 34,455
  `ExploitRemoteService` and 11,727 `DiscoverDeception` against 8,465 `Impact`
  over 100 episodes.

### Consequence

The earlier claim that compromise state is orthogonal to what KEEP optimises is
withdrawn. It was an artifact of scoring a policy against a variable no blue
agent observes.

The oracle series is explained by the same artifact. All nine rules substituted
ground-truth targeting for evidence-based targeting, 77 to 400 times per
episode, in a policy trained on the latter. The dose-response in the O5 budget
sweep measures the cost of that substitution, not the ceiling on supervision.

What survives is target selection **among** flagged hosts. Restores skew 1.75x
toward servers and 1.3 to 1.7x toward operational and restricted zones, and away
from admin at 0.17x and public access at 0.48x. The published phase reward table
explains this directly: Operational Zone A carries -10 for LocalWork failure and
-10 for red impact in phase 2a, against -1 to -5 for the cheaper zones.

### The evidence criterion does not explain the oracle failures either

The natural reading of the 0.2 percent figure is that KEEP acts on observable
evidence where the oracle rules acted on ground truth, and that the two criteria
select different hosts. Tested and refuted.

For every Restore KEEP issued, the first compromised host in the same zone was
taken as the target a ground-truth rule would have chosen, and both targets were
scored against both criteria. 20 episodes of `corpus_v1`.

| | n | Ground-truth precision | Evidence precision |
|---|---|---|---|
| KEEP's target | 1583 | 0.2% | **69.8%** |
| Ground-truth rule's target | 1101 | 100% by construction | **70.1%** |

The two rules agree on the host in **2 of 1101 cases, 0.2 percent**. They select
near-disjoint host sets, and both sets are flagged at the same rate.

So a compromised host is almost always also a flagged host, and the evidence
latch is not the discriminating variable. Criterion substitution does not
explain why O1 loses 333 points per episode to KEEP. Both rules restore flagged
hosts at 70 percent; one is worth 333 points more than the other.

### Five explanations tested, five null

| Hypothesis | Test | Result |
|---|---|---|
| Restore is expensive; adding restores costs reward | Per-action step reward and 30-step lag around a Restore | Restore steps average -0.342 against -0.375 overall; reward improves after (-0.472 before, -0.399 after). No penalty exists |
| Supervision rescues episodes the policy handled badly | Null arm correlation | Null arm shows -0.712, oracle O8 -0.272. Regression to the mean, and O8 is weaker than chance |
| Episode difficulty drives when supervision helps | Early red aggression, partial correlation on baseline score | -0.057 raw, -0.113 partial |
| Intervention volume drives outcome | Overrides per episode against delta, within O8 | -0.052 |
| KEEP targets by host value: server role, zone weight, decoy load | O9r and O9s built from the measured skews | Agrees with KEEP on 15 of 77 restores; both arms worse than baseline |
| KEEP acts on observable evidence rather than ground truth | Above | Both criteria flag at 70 percent; the rules agree on 0.2 percent of hosts |

**No measured feature reconstructs KEEP's restore target selection.** The
targeting difference is worth roughly 330 points per episode and is not
explained by compromise state, observable evidence, host role, zone reward
weight, accumulated decoy count, recency of compromise, or recorded damage.

Resolving this would require KEEP's internals — graph-attention weights or
feature ablation on the wrapper — rather than further trace analysis.

**The metric finding does not depend on resolving it.** A published
recovery-precision measure reports 0.2 percent for a policy that outperforms
every rule scoring 100 percent on the same measure. That invalidates the measure
regardless of what drives the policy's choices.

## The metric is not yet a metric

Three published or implemented treatments of recovery precision in CAGE 4, with
incompatible criteria.

| Source | Correct recovery defined as |
|---|---|
| H-MARL `COMPUTE_METRICS` (Singh et al. 2024) | Action on a host with `has_session` at decision time, plus a false positive for Remove against a privileged session |
| Silva (2026), safety contract | Restore **without** visible alert evidence counts against the false-positive budget |
| This work | Both, measured on the same policy and episodes |

Scored on KEEP's restores: **0.2 percent** under the first definition, **69.8
percent** under the second. Same agent, same episodes, same construct name, two
orders of magnitude apart.

Silva's budget is a further case. `B_down = 50` Restore actions per episode.
KEEP issues 77.1. Both of the strongest policies evaluated here exceed a
published downtime contract, which is either a finding about the contract or
about the policies and is untested either way.

A recovery-precision measure that reports either number depending on an unstated
choice of criterion is not a settled metric. This is the construct-validity
problem directly, in a case where the two criteria disagree by 350x on the
best-known MARL submission.

## H-MARL Expert reference value

Second baseline, `cage-hmarl:dev`, Ray 2.10.0, weights from
`saved_policies/sub/iter_49`. The master policy is not trained: H-MARL Expert
uses a stated rule, choose Recover if indicators of compromise are present in
the local observation, otherwise Investigate.

Their `evaluation.py` and `evaluation_metrics.py` carry the same unseeded
sampling defect as KEEP's harness. `--seed` reaches `CybORG(sg, "sim",
seed=seed)` and nothing else. **Two independent submissions sharing the defect
points upstream to the challenge evaluation template rather than to either
team.** Fix recorded in `build/hmarl-fixes.patch`; verified by running `--seed 0`
twice and obtaining identical means, stdevs and action streams.

Four seeds, 100 episodes each. Note `--seed` moves the environment as well as
policy sampling, so this interval is over both, unlike KEEP's `--policy-seed`
interval which holds environments fixed.

| Seed | Mean | Stdev |
|---|---|---|
| 0 | -124.11 | 45.80 |
| 1 | -138.31 | 40.97 |
| 2 | -132.10 | 45.40 |
| 3 | -130.86 | 47.45 |

```
grand mean  -131.35
sd of means    5.87    se 2.94
95% CI      -138.25 to -124.44   (t, 3 df)
```

The unseeded 100-episode run returned -131.99, near the centre of the interval.

`capture_hmarl.py --compat` reproduces the seed-0 run to the digit (-124.11,
sd 45.80) and the seed-0 Wrecker run (-863.86, sd 365.65); see "H-MARL Expert
through the ladder".

### Against the published leaderboard

Kiely et al. 2025, 100 episodes of 500 steps each.

| Team | Type | CC4 score |
|---|---|---|
| Team UC | Heuristic | -113 ± 35 |
| Team Lancer | Heuristic | -118 ± 40 |
| **H-MARL Expert (reproduced here)** | Hierarchical | **-131.35 [-138.25, -124.44]** |
| Team Punch | Heuristic | -142 ± 44 |
| Team Cybermonic (KEEP) | MARL | -193 ± 84 |

Our KEEP reference of -191.34 [-199.66, -183.02] contains the published -193.
H-MARL Expert was not a CC4 submission, so it displaces nobody, but it beats the
best submitted MARL entry by about 60 points with lower variance and would rank
third on this table.

Caveat: leaderboard figures come from Codalabs under the organisers' protocol;
ours come from each team's own harness after fixing the seeding. Same red agent
and episode count, but the protocols are not verified identical.

### Instrumented run

`COMPUTE_METRICS = True`, 100 episodes, unseeded, 21 minutes.

```
True pos across subnets  6.02      False pos across subnets  1.94
```

Roughly 76 percent under their ground-truth definition, against KEEP's 13
percent combined. False positives concentrate in the cheap zones —
public_access 4.20, office_network 4.42, admin_network 4.25 — while operational
and restricted run 0.12 to 0.21. KEEP's pattern is the inverse: it avoids acting
in those zones at 0.17x and 0.48x.

`contractor_network_subnet` shows 0.18 noninfection and no tp/fp entry. It is
the only subnet with red presence and no blue agent, the supply-chain foothold
where red begins, outside blue's control entirely.

Rescoring against observable evidence on H-MARL is now measured (see "H-MARL
Expert through the ladder"): the passive latch is 0.087 precise and 0.019
complete on that defender, against 0.24 and 0.58 on KEEP, because the
criterion is a function of the defender's own action mix.

## CC4 details recovered from the papers

Sourced rather than re-derived.

Action durations in steps: Sleep, Monitor, BlockTrafficZone, AllowTrafficZone 1;
Analyse, DeployDecoy 2; Remove 3; **Restore 5**. This is the published source
for the 39.3 percent blocked-agent-step rate measured earlier.

`Remove` clears only non-privileged, user-level sessions; privileged sessions
assume a persistence mechanism and require `Restore`. Team Punch report that
adding Remove to their round-robin gave no measurable benefit, because Analyse
on a phishing-infected host surfaces only root-privilege artifacts. Consistent
with greedy KEEP's Remove count collapsing from 10,353 to 148.

Phase reward table, AI Magazine Table 2. Operational Zone A in phase 2a and
Operational Zone B in phase 2b carry -10 for LocalWork failure and -10 for red
impact. All other entries range -1 to -5. Contractor network is 0 in phases 2a
and 2b.

### Cross-paper comparison requires artifact identity, and Table 2 does not have it

Trident (arXiv 2608.04317) evaluates adaptive red agents against four CAGE 4
blue baselines. Two of those baselines are agents evaluated here.

| Agent | Trident weights | Weights used here | Trident score | Score here |
|---|---|---|---|---|
| H-MARL 3-policy | shipped `saved_policies/sub/iter_49` | same | -132.63 +/- 0.87 | -131.35 [-138.25, -124.44] |
| GNN / KEEP | `DR_cybermonic_Dec15_{0..4}`, 6,738,258 bytes each | published `gnn_ppo-{0..4}`, 3,536,882 bytes each | -202.34 +/- 1.42 | -191.34 [-199.66, -183.02] |

Where the artifact is shared the two evaluations agree to within about one
point. Where it is not, they differ by eleven, and the checkpoints differ in
size by a factor of 1.9, so the models are not the same size let alone the same
weights.

The Trident table cites this column as "GNN (King et al. 2025)", which reads as
the published submission. The repository shows otherwise. This is not an error
in either score. It is an absence of artifact provenance in a benchmark table,
and it is the same class of problem as the undeclared action-selection mode and
the unseeded evaluation harness recorded above.

Note also that Trident's reported standard deviations are across three runs of
500 episodes, not across episodes, which is why they are so much tighter than
the episode-level spreads reported elsewhere in this file.

Checkpoint inspection, `torch.load` on `gnn_ppo-0.pt` and
`DR_cybermonic_Dec15_0_checkpoint.pt`. Both carry keys `actor`, `critic`,
`agent`, with 40 and 28 tensors respectively, so the architecture family is the
same. The dimensions are not.

| | KEEP published | Trident |
|---|---|---|
| hidden1 | 256 | 320 |
| conv2 width | 128 | 280 |
| actor parameters | 476,167 | 966,623 |
| critic parameters | 401,537 | 711,689 |
| PPO clip | 0.2 | 0.3 |
| learning rate | 3e-4 | 3e-5 |

The hyperparameters are stored in the checkpoint's `agent` tuple, so this is
recorded rather than inferred. Trident evaluated a retrained model roughly twice
the size of the published submission under a row cited as "GNN (King et al.
2025)".

## The adversary determines whether supervision helps
From this section on, the adversary is stated per table.

Every oracle result recorded above was measured against `FiniteStateRedAgent`,
the stock CC4 red agent that selects hosts at random. That condition was never
stated as a scope limit. It should have been.

### Twelve heuristic red agents

Trident's Appendix B ships twelve heuristic red agents used only to generate
training trajectories; none has a published score. Captured with
`capture.py --red`, 100 episodes each, KEEP sampled, seeds 0-99.

| Red agent | Mean | Stdev | Min | Max |
|---|---|---|---|---|
| FiniteStateRedAgent (control) | -187.32 | 61.24 | -527 | -113 |
| TargetARestricted | -98.52 | 48.61 | -228 | -22 |
| TargetAOperational | -99.89 | 55.40 | -415 | -22 |
| TargetA | -104.18 | 55.60 | -315 | -22 |
| TargetB | -116.25 | 54.19 | -262 | -22 |
| TargetBRestricted | -117.93 | 63.29 | -488 | -22 |
| TargetBOperational | -127.31 | 88.17 | -607 | -22 |
| Combined | -165.87 | 84.76 | -523 | -22 |
| FailureTracker | -205.66 | 90.26 | -755 | -99 |
| Impacter | -228.73 | 129.53 | -608 | -70 |
| Degrader | -268.80 | 122.38 | -852 | -120 |

Seven of ten make blue's task easier, five by 60 to 89 points: focusing red
on one zone stops it exploring. Only the action-biased agents hurt, and
Impacter doubles between-episode variance for 41 points. Red holding sessions
costs nothing; only Impact and DegradeServices move the reward. That is the
reward-function reading confirmed from the other side of the board, and it is
what Wrecker is built on. `red_FiniteStateRedAgent` reproduces `corpus_v1`
exactly, so the `--red` path is transparent. The agents carry a compounding
bug in `_choose_host_and_action` (`host_action_options[opt] *= 4` inside a
loop); numbers are as-shipped.

**The -22 optimum is a fixed penalty structure.** Seven arms share a maximum
of exactly -22. It is reached by one or two episodes per arm, never more, and
every such episode has the same step-reward composition: 478 steps at 0,
twenty at -1, one at -2. Identical structure across six different red agents
means a cost no blue action avoids, most likely the seeded initial foothold or
phase-transition penalties. Whether the 21 penalised steps fall at the same
indices is unchecked. With the do-nothing floor at -6592.68, the reward span
of the environment is bracketed at both ends.

**The -22 optimum is seed-determined.** The ten episodes that reach it, across
seven red agents, share two step-index templates exactly: 21 penalised steps
under one environment seed, 22 under another, the same indices regardless of
adversary. The cost is the green agents' scheduled activity under that seed,
charged whether or not red acts, and no blue action avoids it. -22 is the
floor of the penalty the environment levies on its own, not a ceiling blue
reaches.

### An impact-focused adversary, with the defender held at deployment competence

Trident (arXiv 2608.04317) trains an LLM planner via RLVR to generate red
policies. Reading `agentic/prompts/planner_prompts.py` shows the planner's
entire output is a JSON object with `host_state_priority` (eight values over
host states K, KD, S, SD, U, UD, R, RD, summing to 100) and `state_action_probs`
(eight rows, each a distribution over that state's legal actions), plus one
bugfix flag. The prompt states the constraint directly. The LLM and the GRPO
loop are a search procedure over roughly thirty numbers, not the artifact.

`red_agents/FSRedAgentWrecker.py` is one hand-specified point in that space. It
raises the adversary's damage conversion rather than weakening the defender: 64
percent of host-state priority on R and RD, root-state rediscovery reduced from
the base 0.50 to 0.05, Impact and DegradeServices raised from 0.50 combined to
0.95. The default red is persistence-heavy and converts little of what it holds;
Wrecker is impact-heavy and converts nearly all of it. This is a threat-model
axis, not a difficulty setting. Thirty lines, no LLM, no GPU, no search.

| Agent | vs FiniteStateRedAgent | vs Wrecker | Factor |
|---|---|---|---|
| KEEP | -187.32 | -1115.65 | 5.95x |
| H-MARL Expert | -124.11 | -863.86 | 6.96x |

Trident's RLVR-trained agent reaches -849.85 against HMARL3. Their Table 2
reports mean and standard deviation across three independent runs, each the
mean of 500 randomized 500-step episodes, so their ±6.46 is the spread of three
run-means and is not comparable to a per-episode standard deviation. Their red
policy for that row was trained by GRPO specifically against HMARL3. Their
HMARL3 weights are byte-identical to ours, verified by md5 across all fifteen
policy files and `algorithm_state.pkl`, so the comparison is like for like on
the artifact and differs only in episode count (100 here) and seeding.
**A hand-specified point in their own published schema, tuned against nothing,
matches their trained and target-specific optimum to within 1.6 percent on the
one baseline where the artifact is shared.**

Their GNN row is not comparable: 966,623 actor parameters against the published
476,167, hidden1 320 against 256, under a different clip and learning rate.

### The defender is not pushed off distribution

KEEP's action mix under Wrecker, 20 episodes, against `corpus_v1`.

| Action | corpus_v1 | Wrecker |
|---|---|---|
| Sleep | 38.49% | 37.65% |
| AllowTrafficZone | 26.46% | 27.51% |
| Analyse | 10.85% | 10.15% |
| DeployDecoy | 6.50% | 6.50% |
| BlockTrafficZone | 6.40% | 6.61% |
| Remove | 4.18% | 4.36% |
| Monitor | 3.94% | 4.20% |
| Restore | 3.17% | 3.04% |

Every action within one percentage point, same rank order. **The policy is
executing its learned strategy unchanged and losing six times as badly.** It
does not adapt.

Wrecker also leaves *fewer* hosts compromised, 26.3 of 97 at step 400 against
32.1 for the default. Territory is not the threat. What red does with what it
holds is the threat, which is what the reward function counts.

### Noise floor at the new difficulty

Three sampling seeds, environments fixed.

| Arm | Mean | Stdev |
|---|---|---|
| Wrecker, policy_seed unset | -1115.65 | 272.91 |
| Wrecker, policy_seed 9000 | -1196.35 | 336.69 |
| Wrecker, policy_seed 9001 | -1107.05 | 297.93 |

```
grand mean  -1139.68
95% CI      -1262.07 to -1017.30   (t, 2 df)
```

Pairwise deltas between identical policies run -80.70 and +8.60, with win rates
45/100 and 51/100. **The bar at this difficulty is roughly 81 points of mean
delta and a win rate outside 45 to 51 of 100**, against 25 points and 66/100 at
normal difficulty.

Variance decomposition

```
within-episode sd (sampling luck)   256.41
between-episode sd (difficulty)     185.56
ratio 0.72
```

At normal difficulty the same figures were 44.50 and 36.39, ratio 0.82. Both
terms scaled roughly fivefold and the ratio moved the wrong way. **Wrecker
manufactures headroom but not legibility**, and it does not satisfy the
stopping criterion recorded earlier.

That criterion is withdrawn. It was derived from a comparison against
deterministic greedy KEEP, where within-episode variance is zero by
construction, so any positive between-episode term satisfies it for reasons
unrelated to supervisability. For a sampled policy the ratio may never exceed 1
at any difficulty, and the quantity it was standing in for is now measured
directly.

The replacement criterion: a supervisory condition is viable when the oracle
effect at a human-sustainable budget exceeds the identical-policy noise band.
Under Wrecker at budget 77 that is +241 against a band of roughly ±81, a ratio
near 3. Under the default red no rule at any budget clears the band. The
variance decomposition is retained as a description of the condition, not as a
test of it.

### Oracle rules under Wrecker

100 episodes each, environment seeds 0-99; worker count not recorded.

| Rule | Mean | Stdev | Delta | Better | Overrides/ep | Agreements/ep |
|---|---|---|---|---|---|---|
| KEEP, control | -1115.65 | 272.91 | reference | | 0 | |
| O8, suppression | -1396.42 | 534.72 | -280.77 | 32/100 | 186.8 | 34.9 |
| O6, suppression | -1296.47 | 525.48 | -180.82 | 38/100 | 293.7 | 69.9 |
| O5, budgeted phase-aware | -1013.89 | 373.83 | +101.76 | 61/100 | 77.0 | 0.1 |
| **O2, conditional correction** | **-654.88** | **69.86** | **+460.77** | **100/100** | 403.8 | 1.1 |

`--rule none --red FSRedAgentWrecker` reproduces the unsupervised arm exactly,
confirming the harness is transparent at this difficulty.

O2 beats KEEP on **every episode**. The distributions do not overlap: O2's worst
episode is -848 against KEEP's best of -646. Standard deviation collapses from
272.91 to 69.86, and the range narrows from 1,175 points to 340.

At normal difficulty O2 scored -523.19 against KEEP's -187.32, losing by 336 and
winning 1 episode in 100. **Same rule, opposite sign.**

Unbounded O2 is not a supervisory condition. At 404 overrides and 1.1
agreements per episode it is a different policy that consults KEEP, and its
score is the ceiling of the rule rather than of supervision. The supervisory
condition is the budgeted version below, where the rule intervenes at a rate a
person could sustain and agrees with KEEP more often than it overrides.

### O2 budget sweep under Wrecker

`--budget k` stops the rule after its k-th override in each episode. Wins are
paired over environment seeds 0-99; sign test two-sided exact binomial.

| Budget | Mean | Delta | Stdev | Wins | Overrides/ep | Agreements/ep |
|---|---|---|---|---|---|---|
| 0 (KEEP) | -1115.65 | reference | 272.91 | | 0 | |
| 10 | -1093.77 | +21.88 | 357.78 | 55/100 | 10.0 | 62.2 |
| 20 | -1012.49 | +103.16 | 345.35 | 64/100 | 20.0 | 59.1 |
| 40 | -958.31 | +157.34 | 315.42 | 68/100 | 40.0 | 55.3 |
| 77 | -874.27 | +241.38 | 280.66 | 74/100 | 77.0 | 49.3 |
| 150 | -767.85 | +347.80 | 211.17 | 86/100 | 150.0 | 34.6 |
| 300 | -628.50 | +487.15 | 102.43 | 97/100 | 299.6 | 12.3 |
| unbounded | -654.88 | +460.77 | 69.86 | 100/100 | 403.8 | 1.1 |

Budget 10 is inside the null band (55 wins, p 0.37); budget 20 is the first
to clear it (p 0.007). Gain is monotonic to budget 300, then reverses slightly.

**A budget is not a rate.** Logging each override's proposed and executed
action showed that 7,690 of the 7,700 overrides at budget 77 fall in mission
phase 0, and 99 percent before step 150. The rule spends its budget on the
first k eligible steps, so every row above is a burst at the start of the
episode followed by silence. The sweep confounds how many interventions with
when they happen, and the earlier claim that budget 77 was "the sustainable
human decision rate" described a rate of one intervention every two steps for
the opening fifth of the episode and none thereafter.

### What the override replaces

Every override at budget 77 under Wrecker, logged as (proposed, executed)
after the step record gained an `overrides` field. `wo_O2_b77x` reproduces
`wo_O2_b77` on all 100 footers; the field changes nothing.

| KEEP proposed | Oracle executed | Count | Share |
|---|---|---|---|
| Monitor (idle) | Restore | 6,357 | 82.6% |
| AllowTrafficZone | Restore | 563 | 7.3% |
| Analyse | Restore | 197 | 2.6% |
| DeployDecoy | Restore | 178 | 2.3% |
| Remove | Restore | 151 | 2.0% |
| BlockTrafficZone | Restore | 129 | 1.7% |
| Restore (other host) | Restore | 125 | 1.6% |

Same host, different action: 27 of 7,700 (0.4 percent). blue_agent_4, the HQ
network and red's entry point, receives 3,559 of 7,700 (46 percent); the other
four split the rest evenly. By step: 20 percent in steps 0-24, 25 percent in
25-49, 26 percent in 50-74, 18 percent in 75-99, and 7 percent in 100-124;
nothing after step 199.

The gate decision is not "wrong target" but "act now": the agent is idle while
a compromised host sits in its subnet. The supervisory task is vigilance, not
diagnosis. Load is not uniform across agents, which any fan-out design has to
reflect. And the budget-77 condition as run is a phase-0 burst, which the
spread sweep below separates from count.

### Rate, not count: the spread sweep

`--min-gap N` enforces at least N steps between overrides by the same agent,
budget released, so intervention rate is set by the gap alone and spread over
the whole episode.

| Gap | Overrides/ep | Mean | Delta | Stdev | Wins | Sign p | Points/override | Agreements/ep |
|---|---|---|---|---|---|---|---|---|
| 2 | 277.4 | -539.45 | +576.20 | 69.55 | 100/100 | 1.6e-30 | 2.1 | 3.0 |
| 4 | 187.9 | -466.01 | +649.64 | 62.37 | 100/100 | 1.6e-30 | 3.5 | 6.0 |
| 8 | 110.1 | -457.77 | +657.88 | 97.61 | 100/100 | 1.6e-30 | 6.0 | 11.6 |
| 16 | 80.6 | -572.78 | +542.87 | 137.12 | 99/100 | 1.6e-28 | 6.7 | 25.4 |
| 32 | 52.7 | -680.42 | +435.23 | 158.46 | 93/100 | 2.7e-20 | 8.3 | 37.7 |
| 64 | 32.0 | -797.25 | +318.40 | 229.27 | 82/100 | 6.2e-11 | 9.9 | 47.3 |
| 128 | 18.1 | -889.95 | +225.70 | 255.82 | 73/100 | 4.7e-06 | 12.5 | 55.3 |
| unbounded | 403.8 | -654.88 | +460.77 | 69.86 | 100/100 | 1.6e-30 | 1.1 | 1.1 |

Three things the budget sweep could not show.

**Timing is worth more than count.** Eighteen interventions spread across the
episode (gap 128) match seventy-seven concentrated in its opening (budget 77):
-889.95 against -874.27. Fifty-three spread (gap 32) beat the burst by 194
points with a third fewer interventions, and halve its standard deviation.
The burst restored hosts that Wrecker re-rooted within the phase and then
left the defender alone for 350 steps.

**The rate-return curve has an interior maximum.** Spread intervention at 110
per episode (gap 8) exceeds the unbounded rule at 404 per episode by 197
points. The maximum is a plateau: gaps 4 and 8 (188 and 110 per episode)
differ by 8 points, within noise, and the decline from there is monotonic —
+576 at 277 per episode, +461 at 404. Constant substitution displaces the
policy's own actions and restores hosts before they have converted; periodic
substitution does not. This is the inverted-U that the budget sweep did not
produce, in the variable — rate — where the supervision literature predicts
it.

**Scheduling does not create value where there is none.** O2 at gap 32 under
the default red scores -203.42 against KEEP's -187.32: delta -16, 39 wins of
100, sign p 0.035. The mean sits at the edge of the default-red null band (-11
to +15) and the win rate inside its null range (35 to 66 of 100). Spreading
removes nearly all of the harm the burst rules did there (unbounded O2: -336,
1 win of 100) and produces no gain. Schedule changes how much supervision
helps where the adversary makes it helpful; it does not change whether. The
adversary finding stands with schedule controlled.

**Marginal value per decision falls with rate**, from 12.5 points at 18 per
episode to 6.0 at 110. The fewer decisions a supervisor makes, the more each
is worth, provided they are spread.

**Consequence for the human condition.** The ceiling is a curve indexed by
sustainable rate, not a single number. A participant who can hold 32 decisions
per episode — one every sixteen steps across five agents — is scored against
+318; one who holds 18 is scored against +226; the noise band is ±81 in both
cases. Realized fraction is reported against the ceiling at the participant's
own rate.

### Paired test over fixed environments

Every Wrecker arm shares environment seeds 0-99 with the control, so each
episode is a paired comparison. Wins are episodes where the arm scored higher
than KEEP alone; the sign test is two-sided exact binomial.

| Arm | Delta | Wins | Sign p | Paired t |
|---|---|---|---|---|
| null, policy_seed 9000 | -80.70 | 45/100 | 0.37 | -2.05 |
| null, policy_seed 9001 | +8.60 | 51/100 | 0.92 | +0.21 |
| O2, budget 10 | +21.88 | 55/100 | 0.37 | +0.55 |
| O2, budget 20 | +103.16 | 64/100 | 0.0066 | +2.38 |
| O2, budget 40 | +157.34 | 68/100 | 0.00041 | +4.11 |
| **O2, budget 77** | **+241.38** | **74/100** | **1.7e-06** | **+6.09** |
| O2, budget 150 | +347.80 | 86/100 | 8.3e-14 | +10.16 |
| O2, budget 300 | +487.15 | 97/100 | 2.6e-25 | +17.18 |
| O2, unbounded | +460.77 | 100/100 | 1.6e-30 | +17.03 |
| O5, budget 77 | +101.76 | 61/100 | 0.035 | +2.40 |
| O6 | -180.82 | 38/100 | 0.021 | -3.11 |
| O8 | -280.77 | 32/100 | 0.00041 | -4.69 |
| O2e, budget 77 | -54.40 | 45/100 | 0.37 | -1.25 |
| O2er, budget 77 | -86.37 | 48/100 | 0.76 | -1.89 |
| O2ew, budget 77 | -69.28 | 52/100 | 0.76 | -1.48 |
| O2e, unbounded | -80.25 | 40/100 | 0.057 | -2.18 |
| O2f, budget 77 (corrected latch) | +34.9 | 54/100 | 0.48 | |
| O2fr, budget 77 | +11.2 | 51/100 | 0.92 | |
| O2fw, budget 77 | +11.2 | 51/100 | 0.92 | |
| O2f, unbounded | -42.9 | 43/100 | 0.19 | |
| O2f, gap 32 | -11.5 | 51/100 | 0.92 | |

An identical policy reaches |t| = 2.05 by sampling seed alone, so the paired
t overstates; the sign test is the statistic reported. Win rate is monotonic
in budget. Budget 10 is inside the null; budget 20 is the first to clear it,
which sets the minimum detectable intervention rate near 20 decisions per
episode. All three evidence rules at budget 77 are indistinguishable from the
null arms.

### Observable evidence does not recover the ground-truth gain

O2e is O2 with the compromised set replaced by the latched evidence criterion
from "Two criteria, two answers": a host is a candidate if a substantive raw
observation has named it since its last Restore or Remove. Two further
variants rule out ordering as the cause: O2er takes the most recently observed
host first; O2ew additionally expires a flag 30 steps after the last
observation naming the host.

| Rule | Criterion | Ordering | Budget | Mean | Stdev | Delta | Overrides/ep | Agreements/ep |
|---|---|---|---|---|---|---|---|---|
| O2 | ground truth | first compromised | 77 | -874.27 | 280.66 | +241.38 | 77.0 | 49.3 |
| O2e | evidence | oldest flag | 77 | -1170.05 | 341.22 | -54.40 | 77.0 | 106.4 |
| O2er | evidence | most recent | 77 | -1202.02 | 335.55 | -86.37 | 77.0 | 106.4 |
| O2ew | evidence | most recent, 30-step window | 77 | -1184.93 | 348.62 | -69.28 | 77.0 | 63.9 |
| O2 | ground truth | first compromised | unbounded | -654.88 | 69.86 | +460.77 | 403.8 | 1.1 |
| O2e | evidence | oldest flag | unbounded | -1195.90 | 228.23 | -80.25 | 347.4 | 9.3 |
| O2f | evidence, corrected | oldest flag | 77 | -1080.73 | | +34.9 | 77.0 | 80.5 |
| O2fr | evidence, corrected | most recent | 77 | -1104.42 | | +11.2 | 77.0 | 80.8 |
| O2fw | evidence, corrected | most recent, 30-step window | 77 | -1104.42 | | +11.2 | 77.0 | 51.1 |
| O2f | evidence, corrected | oldest flag | unbounded | -1158.58 | | -42.9 | 292.4 | 7.8 |
| O2f | evidence, corrected | oldest flag | gap 32 | -1127.15 | | -11.5 | 63.6 | 10.0 |

The O2e rows counted two entries that are not evidence: the reset
observation at step 0, which names every owned host, and the echo of the
agent's own action on a host the step before (ARMS.md, Known issues,
found 2026-09-26 while building the rule defenders). The O2f rows are
the same rules with both excluded, run the same day; the originals are
kept for provenance. The correction moves every arm by 20 to 80 points
toward zero and none of them out of the band: the best corrected
evidence arm is +35 at 54 of 100, and at gap 32, the cadence at which
ground truth is worth +452 and strict evidence +56, the passive
criterion is -11.5. On H-MARL the corrected rule is -164.7 at 31 of 100
against the original's -150.2 ("H-MARL Expert through the ladder").

All evidence arms are inside the noise band, within 80 points of
one another. Ordering and expiry do not matter. The evidence rule
agrees with KEEP twice as often as the ground-truth rule does at the same
budget: the policy already acts on the observable signal, and an oracle
limited to that signal has nothing to add.

Under the default red, `o2e_b77` scores -256.48 against ground-truth O5 at the
same budget at -246.05. Where no criterion helps, both cost the same.

**A supervisor reading the observation stream cannot beat KEEP under Wrecker,
however the stream is ordered or aged. The ground-truth gain is carried by the
difference between the compromised set and the flagged set.** Whether that
difference is a recall gap (compromised hosts unflagged) or a precision gap
(flagged set too broad) is not yet measured, and the two have opposite
consequences: the first calls for an investigate authority that generates
evidence; the second for a representation that discriminates within it.

### The evidence latch is uninformative

Confusion between the latched evidence set and ground truth, per agent-host-
step. The first two rows are the original latch (20 episodes of O2e at
budget 77), which counted the reset listing and the agent's own echo; the
corrected rows are O2f at budget 77, summed over the 100-episode arms'
footers (`tools_latch_sum.py`).

| Latch | Adversary | Precision | Recall | Flagged/step | Compromised/step | Lift |
|---|---|---|---|---|---|---|
| O2e | Wrecker | 0.245 | 0.584 | 48.5% | 20.4% | 1.2x |
| O2e | FiniteStateRedAgent | 0.237 | 0.611 | 52.3% | 20.3% | 1.2x |
| O2f, corrected | Wrecker | 0.279 | 0.480 | 34.5% | 20.1% | 1.4x |
| O2f, corrected | FiniteStateRedAgent | 0.285 | 0.521 | 38.0% | 20.8% | 1.4x |

The original latch marked half the network; the listing accounted for a
third of its flags. Corrected, the criterion marks a third of the
network and is 1.4x better than chance at identifying the compromised
fifth. Half of compromised host-steps are unflagged. The adversary does not change any of this to within a few points, on
either latch: Wrecker changes what compromise costs, not what it looks
like, at least as KEEP operates the network. (Under a defender that
evicts almost nothing the two reds do look different, ARMS.md "What the
observation supports": with compromise accumulating to two fifths of
host-steps the stock red's repeated namings become informative and
Wrecker's do not. Single episodes.)

This retires the evidence criterion as a recovery-quality metric. KEEP's 69.8
percent evidence-precision, reported above, is a 1.4x lift over a 50 percent
flag rate. Neither published criterion measures what it claims to.

It also locates the supervisory problem. The observation stream is alert-
shaped and half the alerts are noise; the ground-truth oracle's +241 is the
value of triage done perfectly. A supervisor reading the same stream as the
agents cannot do that triage, because the stream does not support it. Whatever
the interface supplies has to come from outside the per-agent observation:
the view across agents, a stricter reading of indicators, or the authority to
generate evidence by directing investigation. Each is one arm.

### The active stream is precise and starved

Feature-level precision against ground truth over 20 `corpus_v1` episodes:
Monitor-type host entries (97 percent of all entries) 0.23, chance;
Analyse-produced Files entries 0.84; Files with Density 0.9, 0.88.

O2s flags a host only on an Analyse-confirmed file (Density >= 0.9), most
recent first, spread at gap 32.

| Adversary | Mean | Delta | Overrides/ep | Latch precision | Latch recall | Points/override |
|---|---|---|---|---|---|---|
| Wrecker | -1059.73 | +55.92 | 4.5 | 0.967 | 0.001 | 12.4 |
| FiniteStateRedAgent | -186.79 | +0.53 | 5.1 | 0.926 | 0.001 | - |

The strict signal is as good as ground truth where it exists and exists
almost nowhere. Each strict-evidence intervention under Wrecker is worth what
a ground-truth intervention is worth at the same low rate (12.5 at gap 128);
the gain is bounded by supply, not quality. The observation stream can
support supervision; the defender does not generate the observations that
would let it. Whether directing investigation closes that gap is the next arm.

### The authority ladder

Five supervisory authorities, each a rule on the same harness, all spread at
gap 32 under Wrecker on environment seeds 0-99. Ground truth is used only
where stated.

| Authority | Rule | Truth used for | Mean | Delta | Wins | Sign p | Executed/ep |
|---|---|---|---|---|---|---|---|
| Substitute | O1 | the target host | -663.38 | +452.27 | 95/100 | 1.2e-22 | 52.3 |
| Investigate | O10 | where to look | -988.35 | +127.30 | 66/100 | 1.8e-03 | 61.2 |
| Investigate, then restore on confirmation | O12 | where to look | -989.90 | +125.75 | 67/100 | 8.7e-04 | 61.5 |
| Constrain the verb, KEEP picks the host | O11 | whether to act | -1087.58 | +28.07 | 53/100 | 0.62 | 58.7 |
| Read strict evidence | O2s | nothing | -1059.73 | +55.92 | 53/100 | 0.62 | 4.5 |
| Read passive evidence | O2e | nothing | -1170.05 | -54.40 | 45/100 | 0.37 | 77.0 |

O1 is reported rather than O2 because the two are indistinguishable under
Wrecker: paired directly at gap 32, O1 - O2 is +17.04 with O1 winning 49 of
100 (sign p 0.92). O2's conditional preserves 37.7 of KEEP's own recovery
actions per episode and changes nothing measurable.

**Naming the target is worth +452. Naming where to look is worth +127.
Naming only the verb is worth nothing.** The three tiers order the
supervisory authorities by how much of the targeting problem the supervisor
takes on. A constraint that leaves targeting to the agent fails because the
agent's targeting is the deficit (Restore precision against compromise, 0.2
percent). An investigation that generates evidence on the right host
succeeds without any recovery authority: KEEP acts on Analyse-confirmed
files it did not request, and adding an explicit restore-on-confirmation
step (O12) changes nothing, because the agent has already acted by the time
the confirmation exists.

The strict latch's recall rises from 0.001 (O2s) to 0.019 under O10. The
figure is low because a Restore clears the flag; low recall under
investigation is evidence of follow-through, not of failure.

The footer's `analyses` and `restores` counts for O10 and O12 record
attempts (1,726 and 1,751 per episode), not executions, because the rule
increments them before the gap wrapper decides; executed counts (61.2 and
61.5) are the `overrides` figure and the step records' `overrides` field.

Against the default red, O10 scores -179.75 (+7.6), inside the null band.
No authority helps there.

**Consequence.** The investigate authority is the deployable supervisory
role: it needs no ground truth at the point of action, never overrides a
recovery decision, and has a measured ceiling of +127 at 61 decisions per
episode against a noise band of +/-81. The 325-point gap to substitution is
the cost of routing through the agent's response; whether that cost is
latency, incomplete follow-through, or re-compromise before response is
recoverable from the step records and is the next analysis.

### Why investigation is worth a third of substitution

From `wo_O10_g32`'s step records, 6,125 executed investigations:

- **Response is slow and incomplete.** KEEP recovers an investigated host at
  roughly twice the background rate at every window (within 10 steps: 15.3
  against 5.8 percent; within 50: 49.8 against 25.8) — but the median
  response is 36 steps, the 90th percentile 133, and 22.4 percent are never
  followed. Under Wrecker a rooted host converts within a handful of steps;
  most of the response lands after the damage.
- **Detection yield is 0.16.** Five of six investigations of a ground-truth-
  compromised host produce no Analyse-confirmed file. A red session is not a
  detectable artefact until red acts on the host. "Compromised" and
  "detectable" are different sets, and investigate authority reaches only
  their intersection.
- **Half the budget was repeats.** 54.5 percent of investigations targeted a
  host investigated within the previous 50 steps; the five most-investigated
  hosts were each zone's `user_host_0`, first in the `comp` ordering. HQ's
  `public_access_zone_subnet_user_host_0` alone took 714.
- **Load equalised.** 1,562 / 1,192 / 1,179 / 1,099 / 1,093 across agents,
  against 46 percent on agent_4 under substitution: the gap sets the rate
  regardless of where the threat is.

(Added 2026-09-26: a rule defender that restores the step after a
confirmed file has the same median, 38 steps, and the same share within
10 steps; the latency is the sensor's yield, not the policy's response.
See "A defender that was never trained".)

O13 rotates: least-recently-investigated compromised host first, none
repeated within 50 steps.

| Rule | Mean | Delta | Wins | Sign p | Executed/ep | Yield | Points/look |
|---|---|---|---|---|---|---|---|
| O10 | -988.35 | +127.30 | 66/100 | 1.8e-03 | 61.2 | 0.16 | 2.1 |
| O13 | -960.57 | +155.08 | 71/100 | 3.2e-05 | 45.5 | 0.22 | 3.4 |

Rotation raises the ceiling by 28 points with a quarter fewer looks. The
remaining gap to substitution is attributed in order to detection yield,
response latency, and non-response. **The investigate ceiling for a human
condition is +155 at about 45 decisions per episode**, and the display must
show what has been investigated and when, or a supervisor repeats O10's
error.

### The adversary axis is targeting, not conversion

Two sweeps over hand-specified points in Trident's red schema, each with a
KEEP control (`capture.py --red`) and O1 at gap 32, paired over seeds 0-99.

**Conversion sweep.** Wrecker's host-state priority held fixed; the R-row
split between rediscovery and damage varied from 0.10 to 0.95. P95 is
Wrecker and reproduces `red_FSRedAgentWrecker` and `wo_O1_g32` to the digit.

| R-row damage p | KEEP alone | O1 gap 32 | Delta | Wins | Sign p |
|---|---|---|---|---|---|
| 0.10 | -1061.55 | -643.17 | +418.38 | 91/100 | 3.3e-18 |
| 0.30 | -1025.48 | -672.71 | +352.77 | 90/100 | 3.1e-17 |
| 0.50 | -1069.08 | -640.65 | +428.43 | 90/100 | 3.1e-17 |
| 0.70 | -1093.24 | -646.02 | +447.22 | 91/100 | 3.3e-18 |
| 0.85 | -1081.40 | -656.84 | +424.56 | 91/100 | 3.3e-18 |
| 0.95 (Wrecker) | -1115.65 | -663.38 | +452.27 | 95/100 | 1.2e-22 |

Flat. Ninety points of variation in KEEP's score across a tenfold range of
damage probability, and supervision worth +350 to +450 at every point. The
RD row — root and discovered — admits only Impact, Degrade and Withdraw in
this schema, and Wrecker never withdraws, so a host that reaches RD is
damaged on every subsequent action regardless of the R-row split. Conversion
is saturated by the schema; the R-row is not a lever.

**The off-axis point.** `FSRedAgentConvOnly` keeps Wrecker's transitions and
drops the priority list, so red chooses uniformly among reachable hosts as
the stock agent does (`FiniteStateRedAgent._choose_host`, `None` branch).

| Red | Targeting | KEEP alone | O1 gap 32 | Delta | Wins | Sign p |
|---|---|---|---|---|---|---|
| FiniteStateRedAgent | uniform | -187.32 | -203.42 | -16.10 | 39/100 | 0.035 |
| ConvOnly | uniform, Wrecker transitions | -316.62 | -268.19 | +48.43 | 63/100 | 0.012 |
| Wrecker | 64% on R/RD, Wrecker transitions | -1115.65 | -663.38 | +452.27 | 95/100 | 1.2e-22 |

Removing the priority and keeping the transitions costs KEEP 130 points
against the stock red, not 930, and reduces the supervisory gain from +452
to +48. **Of Wrecker's effect, roughly six-sevenths is targeting — red
returning its attention to hosts it has already rooted — and the supervisory
value follows the targeting.** With a priority list, red chooses a host
state with the listed weights renormalised over the states currently present,
then a host within that state; without one, it picks uniformly, so its share
of actions on rooted hosts is whatever fraction of its known hosts happen to
be rooted.

**Priority sweep.** Wrecker's transitions held fixed; R/RD priority mass at
4, 16, 32, 48 and 64 of 100, the remainder in Wrecker's proportions over the
other six states. Win rates climb monotonically 63, 71, 80, 81, 93, 95.

| R/RD mass | KEEP alone | O1 gap 32 | Delta | Wins | Sign p | Delta / excess |
|---|---|---|---|---|---|---|
| uniform (ConvOnly) | -316.62 | -268.19 | +48.43 | 63/100 | 0.012 | 0.37 |
| 4 | -325.11 | -250.60 | +74.51 | 71/100 | 3.2e-05 | 0.54 |
| 16 | -539.17 | -376.15 | +163.02 | 80/100 | 1.1e-09 | 0.46 |
| 32 | -773.08 | -510.80 | +262.28 | 81/100 | 2.7e-10 | 0.45 |
| 48 | -928.16 | -579.43 | +348.73 | 93/100 | 2.7e-20 | 0.47 |
| 64 (Wrecker) | -1115.65 | -663.38 | +452.27 | 95/100 | 1.2e-22 | 0.49 |

KEEP's score and the supervisory gain are both close to linear in the
priority mass red places on rooted hosts: about -13 points of KEEP score and
+6 points of gain per point of mass. Expressed against KEEP's excess loss
over the stock red, substitution at gap 32 recovers 45 to 54 percent of what
the adversary's targeting costs at every point from 4 to 64. There is no
threshold. **The value of a supervisor is continuous in how much attention
the adversary pays to what it already holds, and it is near zero only where
that attention is near zero.** ConvOnly's null seed (-301.66 against
-316.62, +14.96, 51 wins of 100) puts the band at that difficulty near +/-15, so its +48 is the
bottom of the curve, not off it.

This is the adversary axis for the human study: the stock red is the origin,
Wrecker is the far end, and the intermediate points are one line each.

### Consequences

**The earlier bound was conditional, and the condition was the adversary.**
Nine rules and a budget sweep established that action substitution loses to a
converged policy against `FiniteStateRedAgent` at every rate and schedule. The
same rule wins on 95 to 100 of 100 paired episodes against an impact-focused
adversary. Nothing tried — information, schedule, authority — creates value
against the default red; the adversary's conversion of compromise to damage is
the variable that sets the sign.

**Schedule sets the magnitude.** Interventions spread across the episode are
worth up to four times as much per decision as the same count concentrated in
its opening, the rate-return curve has an interior plateau at 110 to 190
interventions per episode, and marginal value per decision falls
monotonically with rate. The ceiling for any human condition is a curve
indexed by sustainable rate.

**The value is not in what the agents see.** The passive observation stream
flags half the network at chance precision under both adversaries. Analyse-
confirmed files are 97 percent precise and cover 0.1 percent of compromised
host-steps. The signal is truth-grade and starved, because nothing points the
sensor.

**Authority orders as targeting does.** Naming the target, +452; naming where
to look, +155 with rotation (+127 without); naming only the verb, +28 and
inside noise. Investigation succeeds without any recovery authority because
the agent acts on evidence it did not request — slowly (median 36 steps),
incompletely (22 percent never), and only where Analyse can find something
(detection yield 0.16 to 0.22). That is the deployable supervisory role, and
it has a measured ceiling.

**Two architectures, one sign.** H-MARL Expert, a hierarchical defender with
a hand-written Investigate/Recover gate, loses to a perfect-information
substitute against the stock red (-24, 22/100) and gains from it under
Wrecker (+98, 65/100). Its gain is a fifth of KEEP's because its own loss is
smaller; the supervised endpoints are within a null band of each other.
Authority over the verb is worth nothing in either architecture (O11 on
KEEP, O14 on H-MARL). Directed investigation on H-MARL is at the edge of the
band (+101 and +39, 55 wins each, indistinguishable from each other), trims
the lower tail rather than lifting the median, and is answered no faster
than on KEEP. The passive-evidence criterion collapses on H-MARL (precision
0.087) because its Analyse-heavy action mix floods the latch. The adversary
result and the verb result are about the class; the evidence criterion is
about the defender.

**The adversary axis is targeting.** Conversion is saturated by the schema
and its sweep is flat. Supervisory value is linear in the priority mass red
places on hosts it has already rooted, from +48 at uniform targeting to +452
at Wrecker, recovering about half of the targeting-induced loss at every
point. There is no threshold; the stock red is the origin of the axis, not
an exception to it.

**Both published recovery-precision criteria are non-measures.** Ground truth
punishes a good policy; evidence is 1.2x chance.

**The competence checkpoint pool is displaced.** A thirty-line adversary with
the defender at full competence replaced weeks of training and a reviewer
objection.

**The study is specified.** Converged defender, impact-focused adversary,
spread intervention, two authority conditions with oracle ceilings (+452
substitute at 52 decisions per episode, +155 investigate at 45), a noise
band of +/-81, paired design over fixed seeds, and a decision type —
prompt an idle agent — that is vigilance rather than diagnosis. A human at
that gate is the experiment. The defender is KEEP; H-MARL Expert is the
generalization arm, with too little headroom under Wrecker (+98 against a
+/-75 band) for a human fraction to be estimated at any affordable study
size.

## H-MARL Expert through the ladder

The second defender through the same rules, the same schedule and the same
paired design, so that the adversary and authority findings are about a class
of converged defenders rather than about KEEP. H-MARL Expert (Singh et al.)
is architecturally unlike KEEP: five masters each choose Investigate or
Recover per step through a hand-written IoC gate, and a PPO sub-policy for
the chosen mode picks the action. The gate is the action mask the master
sees, `[1,0]` Investigate or `[0,1]` Recover, set by `observation_change`
from whether an indicator of compromise is present in the agent's own
observation.

### Harness

`scripts/capture_hmarl.py` installs `oracle_rules.make_oracle` (the rules
shared with `oracle.py`, moved verbatim into a module) on the H-MARL wrapper
by wrapping `env_step`: the sub-policy's action index becomes a CybORG action
object, the rule sees it and may replace it, and a replacement goes back as
an index so the stock path executes it. The master phase (mode choice, no
simulator step) is untouched, so `overrides`, `agreements`,
`translator_calls` and gap ticks count per simulator step exactly as for
KEEP. Step records carry each agent's executed mode and the expert gate's own
choice.

Two seeding modes, because H-MARL's `evaluation.py` and the oracle harness
seed differently. `--compat` mirrors `evaluation.py` with the seeding fix
(seed once, load policies, one `CybORG(seed)` reset per episode, sequential)
and reproduces the reference runs to the digit: seed 0, 100 episodes,
`FiniteStateRedAgent` -124.11 sd 45.80, `FSRedAgentWrecker` -863.86 sd
365.65, and the three-episode running means and standard deviation match
their harness exactly (-931.00, -1119.50, -902.67, sd 420.22). The default
mode is a fresh `CybORG(seed=ep)` per episode with sampling reseeded per
episode, run in parallel, so arms pair seed by seed as the KEEP arms do. Its
controls are -842.76 sd 312.94 under Wrecker (against -863.86 for one seed
reset a hundred times) and -136.43 sd 49.60 against the stock red, inside the
four-seed interval [-138.25, -124.44].

Twelve seconds an episode: a 100-episode arm takes four minutes at six
workers, about the same as a KEEP `oracle.py` arm (4.7 minutes measured on
2026-09-20; an earlier version of this sentence said an hour, which was
wrong).

### Noise band

Two policy-seed nulls under Wrecker and one against the stock red, paired
against the control on the same environment seeds.

| Adversary | Null | Mean | Delta | Wins | Sign p |
|---|---|---|---|---|---|
| Wrecker | `hm_w_none_p9000` | -915.97 | -73.2 | 43/100 | 0.19 |
| Wrecker | `hm_w_none_p9001` | -898.46 | -55.7 | 47/100 | 0.62 |
| Wrecker | `hm_w_none_p9002` | -896.31 | -53.5 | 44/100 | 0.27 |
| Wrecker | `hm_w_none_p9003` | -890.41 | -47.6 | 43/100 | 0.19 |
| Wrecker | `hm_w_none_p9004` | -854.60 | -11.8 | 48/100 | 0.76 |
| stock | `hm_s_none_p9000` | -136.36 | +0.1 | 51/100 | 0.92 |
| Q32 | `hm_WreckerQ32_none_g0_p9000` | -591.85 | -6.1 | 52/100 | 0.76 |

Under Wrecker the band is about +/-75 on the mean and 43 to 48 wins, the
same width as KEEP's; all five nulls fall below the control, so the
control is the best of six draws and a gain quoted against it is about 40
smaller than against the null centre (-883). Against the stock red and
under Q32 the band is nearly zero: the expert gate is deterministic given
the observation, and against an adversary that converts little, the
sub-policies' sampling barely moves the score.

### The adversary sets the sign for both defenders

Substitution at gap 32, paired over seeds 0-99, both defenders, both
adversaries.

| Defender | Adversary | Control | O1 gap 32 | Delta | Wins | Sign p |
|---|---|---|---|---|---|---|
| KEEP | stock | -187.32 | -203 | -16 | 39/100 | inside band |
| KEEP | Wrecker | -1115.65 | -663.38 | +452.27 | 95/100 | 1.2e-22 |
| H-MARL Expert | stock | -136.43 | -160.69 | -24.3 | 22/100 | 2e-08 |
| H-MARL Expert | Wrecker | -842.76 | -744.22 | +98.5 | 65/100 | 0.004 |

Same sign pattern on a second architecture. Against the stock red a
perfect-information substitute costs H-MARL 24 points and loses 78 of 100
episodes; under Wrecker it gains 98 and wins 65. Directed investigation
against the stock red is +7.2 (54/100, p 0.36) for H-MARL and +7.6 for
KEEP, both inside their bands.

**The magnitude is the defender's own deficit.** H-MARL loses -843 to
Wrecker where KEEP loses -1116, and its unsupervised gate already spends 263
agent-steps per episode in Recover mode. The supervised endpoints are -744
and -663, within one Wrecker null band of each other. A supervisor with
ground truth brings both defenders to about the same place; how far each
travels is how far it was from there.

### The ladder under Wrecker

All arms gap 32, seeds 0-99, paired against `hm_w_none`.

| Authority | Rule | Truth used for | Mean | Delta | Wins | Sign p | Executed/ep |
|---|---|---|---|---|---|---|---|
| Substitute | O1 | the target host | -744.22 | +98.5 | 65/100 | 0.004 | 54.0 restores |
| Investigate | O10 | where to look | -741.90 | +100.9 | 55/100 | 0.37 | 59.4 analyses |
| Investigate, rotating | O13 | where to look | -804.14 | +38.6 | 55/100 | 0.37 | 44.7 analyses |
| Mode, force Recover | O14 | whether to recover | -880.27 | -37.5 | 43/100 | 0.23 | 57.8 gate flips |
| Read passive evidence | O2e | nothing | -993.01 | -150.2 | 36/100 | 0.007 | 72.3 restores |
| Read passive evidence, corrected latch | O2f | nothing | -1007.49 | -164.7 | 31/100 | <0.001 | 71.6 restores |
| null | | | -916, -898 | -73, -56 | 43, 47 | | |

O14 is the rule KEEP cannot express: when ground truth says the agent's
subnets hold a compromised host and the gate says Investigate, the gate is
flipped to Recover before the master acts, exactly as an observed IoC would
flip it, and the recover sub-policy picks the host. It counts 293 agreements
per episode (truth said compromised and the gate already said Recover), 58
flips, and 87 more Recover agent-steps than the control, for nothing.

Reading the ladder against KEEP's:

- **Naming the target is worth +98 (65/100) here and +452 (95/100) for
  KEEP.** Same authority, same rule, a fifth of the gain, for the reason
  above.
- **Naming where to look is at the edge of the band, and O10 and O13 are
  not distinguishable.** +101 and +39 in mean, 55 wins each, against a band
  of −73 to −56 and 43 to 47 wins. The 62-point gap between them is inside
  the band, and on every step-record measure below they are the same arm.
  What investigation does on this defender is compress the lower tail (see
  "Investigation on H-MARL, from the step records"), which is why O10 has
  O1's mean and not O1's wins.
- **Authority over the verb is worth nothing in either architecture.** O11
  on KEEP (+28, 53/100) and O14 on H-MARL (-37, 43/100). The recover
  sub-policy without an IoC pointing at the host does not find it, as KEEP
  did not. The target is the deficit, not the decision to act.
- **Passive evidence is harmful here and inert for KEEP, because the
  criterion depends on the defender.** -150 (36/100, p 0.007) against -54
  inside the band. The passive latch is 0.087 precise on H-MARL against 0.24
  on KEEP: H-MARL spends most of its steps in Investigate mode running
  Analyse, and every Analyse that returns ordinary files names a host, so
  "any substantive observation" floods with clean hosts. O2e's 72 restores
  per episode are then 91 percent wasted, and restores cost green
  availability. Corrected for the reset listing and the agent's own echo
  (O2f, 2026-09-26) the latch is 0.174 precise on H-MARL, still below the
  0.19 base rate, and the arm is -165 at 31 of 100; on KEEP the corrected
  arm at the same cadence (`wo_O2f_g32`) is -11.5. The correction removes
  the caveat about cadence: at gap 32 on both defenders, passive evidence
  is a null on KEEP and a harm on H-MARL.

### Investigation on H-MARL, from the step records

`tools_investigate.py` on both defenders' O10 and O13 arms. "Response" is
the acting agent's next Restore or Remove on the investigated host; "gate
flip" is H-MARL's expert gate going from Investigate at the look to Recover
at the next step, the event that would mean the look put an IoC in the
agent's own observation.

| Measure | KEEP O10 | KEEP O13 | H-MARL O10 | H-MARL O13 |
|---|---|---|---|---|
| Executed investigations / ep | 61.2 | 45.5 | 59.4 | 44.7 |
| Strict-latch yield (flags_new / analyses) | 0.163 | 0.216 | 0.181 | 0.233 |
| Repeat share (host already looked at this episode) | 66.3% | 46.8% | 66.1% | 48.0% |
| Gate already Recover at the look | | | 13.1% | 10.8% |
| Gate flip at next step (first / repeat looks) | | | 2.6% (3.8 / 2.0) | 1.9% (2.2 / 1.6) |
| Response median / p90 | 36 / 133 | 36 / 135 | 31 / 139 | 32 / 145 |
| Response within 10 / within 50 | 15.3% / 49.8% | 14.2% / 45.8% | 16.1% / 44.5% | 14.2% / 42.0% |
| Never responds | 22.4% | 23.7% | 32.8% | 33.3% |
| Host recovered within 50, look landed / missed | | | 80.1% / 42.8% | 67.5% / 41.7% |

Three things follow. The sensor is the same on both defenders: yield 0.16 to
0.23, rotation raising it by the same third. The response is the same: H-MARL
answers a directed look at KEEP's tempo and less completely (a third never
against a fifth). And the gate almost never flips on a directed look, 2.6
percent, against a sensor yield of 18 percent: whatever H-MARL's IoC gate
counts, it is not what a strict-latch file is. When the gate does flip the
host is recovered within 50 steps 80 percent of the time, so the mechanism
exists and the directed look does not trigger it. The "architectural
response" explanation proposed when the ladder first ran is withdrawn.

What investigation does do on H-MARL is visible in the paired delta
distribution against the control, with the two nulls as calibration.

| Arm | Median delta | p10 | p90 | Arm stdev |
|---|---|---|---|---|
| null 9000 | -88 | -727 | +468 | 354 |
| null 9001 | -35 | -654 | +441 | 355 |
| O1 gap 32 | +137 | -519 | +581 | 330 |
| O10 gap 32 | +60 | -266 | +562 | 240 |
| O13 gap 32 | +48 | -422 | +525 | 252 |

Substitution moves the median by about 200 points relative to a null and
keeps a null's lower tail. Investigation moves the median by about 100 and
cuts the lower tail by about 400 points, and its own standard deviation is a
quarter below the control's (240 against 313). It prevents the worst
episodes and does little to typical ones, which is a different supervisory
product from KEEP's and one that a per-episode sign test undercounts. (A
delta conditioned on the control's own worst quartile is not usable for
this: the nulls show +238 and +317 there by regression to the mean.)

The strict latch is truth-grade on both defenders (precision 1.000 on
H-MARL under O10, 6,322 true against 2 false; 0.94 on KEEP) and half as
complete (recall 0.010 against 0.019), because this defender clears flags
faster by restoring.

### The targeting axis on H-MARL

The conversion and priority sweep's adversaries, each with a control, an
O1 arm and an O10 arm at gap 32 on H-MARL, paired on seeds 0-99 (ARMS.md,
"H-MARL Expert on the targeting axis"). The measure is the fraction of the
point's excess loss the rule recovers, with a paired bootstrap interval;
KEEP's O1 line from the same points is beside it.

| Adversary | H-MARL excess | H-MARL O1 | H-MARL O10 | KEEP excess | KEEP O1 |
|---|---|---|---|---|---|
| ConvOnly | -97 | -0.11 [-0.38, 0.12] | 0.16 [-0.05, 0.34] | -129 | 0.38 [0.17, 0.53] |
| Q04 | -103 | 0.09 [-0.14, 0.28] | 0.32 [0.14, 0.48] | -138 | 0.54 [0.40, 0.66] |
| Q16 | -304 | 0.24 [0.14, 0.33] | 0.20 [0.09, 0.29] | -352 | 0.46 [0.37, 0.54] |
| Q32 | -449 | 0.31 [0.23, 0.38] | 0.17 [0.06, 0.26] | -586 | 0.45 [0.38, 0.51] |
| Q48 | -602 | 0.24 [0.15, 0.32] | 0.17 [0.08, 0.25] | -741 | 0.47 [0.42, 0.52] |
| Q64 (Wrecker) | -706 | 0.14 [0.02, 0.25] | 0.14 [0.05, 0.23] | -928 | 0.49 [0.44, 0.53] |

**KEEP's line is flat; H-MARL's is a hump under it.** KEEP recovers 0.45
to 0.54 of its excess at every depth from Q04 up, with intervals that
overlap each other and exclude every H-MARL value. H-MARL recovers
nothing measurable where its deficit is within a hundred points of stock
(ConvOnly, Q04: fifty restores per episode against a deficit that small
has nothing to buy, and at ConvOnly the O1 arm loses 60 of 100), 0.24 to
0.31 from Q16 to Q48, and 0.14 at Wrecker, 0.19 against the null centre.
In absolute terms H-MARL's O1 gain rises from +73 at Q16 to +145 at Q48
and falls to +99 at Q64 (+139 against the null centre), while KEEP's
rises monotonically to +452. The fall at the deepest point is at the edge
of what the intervals allow (Q32's lower bound 0.23, Q64's upper 0.25),
and the fairer Q64 value sits inside Q48's interval, so the honest
statement is a plateau at about a quarter from Q16 up with a possible
decline at the extreme, not a peak.

Two things for the framework. Amenability has a defender-level component:
H-MARL's line sits under KEEP's at every depth by a factor of two to four,
so which defender a supervisor is paired with sets the scale of what
naming the target is worth. And it has a pairing component: KEEP's
fraction does not depend on depth and H-MARL's does, rising from nothing
to a quarter as the adversary concentrates. The policy layer is not two
parallel lines, which is what H1 predicted; it is one flat line and one
that saturates, and a study that measured H-MARL at a single depth would
have got a different fraction at each.

**Investigation on H-MARL is worth as much as substitution at the ends of
the axis.** O10's fraction is flat at 0.14 to 0.20 from Q16 up (0.32 at
Q04, where both rules are inside wide intervals), and it equals or beats
O1 at ConvOnly, Q04 and Q64. On KEEP, investigation at Wrecker was a
third of substitution. On this defender, where to look is as good as what
to do wherever substitution has little to offer, which is consistent with
the tail-compression reading above: the directed look prevents the bad
episodes, and at the extremes of the axis that is most of what there is
to prevent.

### Adversaries that differ in kind

Trident's ten heuristic reds, which differ in what red does rather than in
how hard it targets, each with a control, an O1 arm and an O10 arm on both
defenders (ARMS.md, "Trident's heuristic reds on both defenders"). Seven of
the ten leave both defenders better off than the stock red does (their
excess loss is positive, 21 to 89 points), FailureTracker is within 20 of
zero on both, and only Degrader (KEEP -82, H-MARL -56) and, on KEEP,
Impacter (-41) produce a deficit.

| Red agent | KEEP excess | KEEP O1 | KEEP O10 | H-MARL excess | H-MARL O1 | H-MARL O10 |
|---|---|---|---|---|---|---|
| seven easier-than-stock reds | +21 to +89 | -2 to -25 | -4 to +16 | +39 to +86 | -23 to -30 | -2 to +8 |
| FailureTracker | -18 | +1 | +13 | -3 | -26 | +10 |
| Impacter | -41 | +69 (1.67 [1.19, 3.54]) | +27 | +3 | 0 | +19 |
| Degrader | -82 | +58 (0.72 [0.51, 0.92]) | -2 | -56 | +1 (0.02) | +14 (0.25 [-0.36, 0.64]) |

**The sign of supervision's value is the sign of the deficit, whatever the
adversary's kind.** Where the adversary leaves blue better off, naming the
target costs 8 to 30 points on both defenders, the same sign and size as
O1's cost against the stock red itself (-16 and -24), and investigation is
inert. The adversary result holds across kind as it held across depth: a
supervisor with perfect information harms where there is nothing to
recover.

**Where a deficit exists, KEEP recovers most or all of it and H-MARL
recovers none.** Degrader costs KEEP 82 and O1 returns 58; Impacter costs
KEEP 41 and O1 returns 69, taking KEEP above its stock-red score. The same
two adversaries cost H-MARL 56 and 3, and O1 returns +1 and 0, with O10
returning +14 and +19 on intervals that include zero. On these
action-biased reds KEEP's fraction sits at or above its depth-axis line
and H-MARL's at zero, below its depth-axis plateau. Kind does something
the depth axis does not capture, and in opposite directions on the two
defenders; but the deficits are small enough (41 to 82 points) that the
intervals are wide, and this is a hint for the framework's threat layer,
not a result for the papers. A red agent that is both action-biased and
targeting-concentrated, which none of Trident's twelve or the Q sweep is,
would be the pairing to test it on.

(Added 2026-09-26. RT under each of the ten reds puts a ceiling under
this table: KEEP is 7 to 37 points below perfect eyes on the seven
easier-than-stock reds and on FailureTracker, 110 below on Impacter and
123 on Degrader, and O1 closes -0.8 to -2.5 of the first group's gap,
0.63 and 0.47 of the last two. "A defender that was never trained",
"Distance to the ceiling".)

### What this does to the study

KEEP stays the study defender. Its ceilings, +452 substitute and +155
investigate, leave room for a human fraction to be estimated; H-MARL's +98
and +101 against a +/-75 band do not, at any study size the protocol can
afford. H-MARL's role is the generalization arm: the adversary result and the
verb result hold across two architectures; the investigate result is smaller
and takes the form of tail compression; and the passive-evidence criterion
turns out to be a property of the defender's action mix, which is a
disclosure point for Paper 1 as much as a finding for Paper 2.

The O14 result is also a design finding. A hierarchical agent offers a human
exactly one natural seat, the mode gate, approve or force Recover, and that
seat is worth nothing with perfect information. The leverage is in naming
the host, or where to look, which the hierarchy does not expose. An interface
built on the agent's own decision structure would put the person at the
wrong gate.

### Bookkeeping

`owned_hosts` in `oracle_rules.py` cached the host list under
`(id(cyborg), agent)`. A freed CybORG's address can be recycled by the next
one a worker builds, and CC4 redraws host counts per episode, so a stale list
could in principle have reached the evidence latch and O7/O9. The cache is
now per agent, validated against the live `State` object and its host-name
tuple, and `_IMPACT_SEEN` is cleared at step 0. `wo_O2e_b77`, the arm most
exposed, reproduced footer-for-footer under the fix (100 episodes, every
shared key identical), so the hazard never fired in a reported number. The
`--compat` mode, which resets one CybORG per episode, needed the fix
regardless.

## Retraining as the mechanism test

Everything under Wrecker so far says the supervisor's gain is the defender's
deficit: a perfect-information substitute brings KEEP from -1116 and H-MARL
from -843 to about the same place, and each travels as far as it was from
there. That leaves the question a reader will ask first. Is the deficit a
distribution shift, which the defender's own trainer would close if it were
shown the adversary, or a limit of what the architecture can represent? The
two readings give the supervisor different values. Under shift, the human is
a stand-in for a retraining run and is worth at most what that run costs;
under capacity, the human supplies something training cannot, at this budget
and in this architecture. The test is the same for both defenders: continue
the shipped weights under the deployment adversary with the authors' own
pipeline, at the authors' hyperparameters, and put the result through the
same ladder as the shipped policy. Pipelines, runs, gates and per-arm numbers
are in ARMS.md, "Retrained defenders".

### H-MARL: the trainable part does not adapt

H-MARL Expert trains its ten sub-policies (Investigate and Recover for each
of five agents) with RLlib PPO; the expert master is a rule on `iocs_exist`
with no parameters. Continuing the shipped `iter_49` checkpoint therefore
trains the sub-policies under a frozen gate, which is the only continuation
the shipped architecture admits. Iterations of 100k environment steps at the
shipped learning rate, SGD passes and entropy; RLlib seeds 0 and 1; three
adversaries.

| Adversary | Seed | Env steps | Curve |
|---|---|---|---|
| stock | 0 | 5M | -140.5 over the first 25 iterations, -145.3 over the last 25 |
| stock | 1 | 1M | flat |
| Wrecker | 0 | 5M | -893.0 over the first 25, -892.7 over the last 25; sd across iterations 34; slope +0.01 per iteration |
| Wrecker | 1 | 1M | -881 to -840, inside the iteration noise |
| Q32 | 0 | 1M | flat |
| Q32 | 1 | 0.5M | -575 to -569, flat |

Curve values are training-time window means in score units, not evaluation
numbers (ARMS.md, Known issues). Two things in the table matter. The Wrecker
curve has no slope at all over five million steps, so this is not a budget
that a longer run would have converted; and the stock control drifted five
points the wrong way, small but three standard errors, so the optimizer was
changing the parameters throughout. The trainer worked and found nothing.

The 5M-step Wrecker checkpoint through the harness, seeds 0-99, paired
against the shipped-policy arms:

| Arm | Adversary | Mean | Stdev | Against | Delta | Wins | Sign p |
|---|---|---|---|---|---|---|---|
| `hm_ft_w99_w_none` | Wrecker | -945.59 | 402.48 | control `hm_w_none` | -102.8 | 43/100 | 0.19 |
| | | | | null `hm_w_none_p9000` | -29.6 | 48/100 | 0.76 |
| `hm_ft_w99_s_none` | stock | -143.21 | 59.13 | control `hm_s_none` | -6.8 | 47/100 | 0.84 |

Against the shipped control it wins 43 of 100, which is exactly what the
sampling null wins; against that null, 48 of 100. Five million steps of the
authors' trainer under Wrecker produced a policy that the paired design
cannot tell from a different sampling seed of the shipped one, at no cost
against the stock red. The single behavioural change is a fifth fewer
Recover-mode agent-steps (263 to 204 under Wrecker, 247 to 201 under stock),
that is, fewer IoC-bearing observations reaching the gate, which bought
nothing either way. The sub-policies drifted; drift is not adaptation.

For this architecture the capacity reading holds, and it holds by
construction rather than by exhaustion: the deficit under Wrecker lives in
what the gate can see, and a sub-policy cannot learn to look for what the
gate never sends it to look for. Two caveats travel with that. Five million
steps is a tenth of the shipped training budget, and the zero slope, not the
step count, is the answer to that objection. And "capacity" here means the
capacity of the trainable part; a retrained gate is a different agent, which
is the point.

Read with the ladder, this closes both seats a hierarchical agent offers.
Forcing the gate with truth (O14) was worth nothing; training the policies
under the gate is worth nothing; naming the target host (O1) is worth +98.
Whatever a supervisor is for on H-MARL under Wrecker, it is the target, and
neither of the agent's own decision points can be taught or told it.

### KEEP: a random walk from the shipped weights, and an endpoint that barely moves

KEEP trains one GNN-PPO policy per agent end to end, verb and target
together, so its continuation is the version of the test with nothing
frozen. The authors' `train.py` is used from the shipped weights with the
adversary, seed, episode budget, worker count and checkpoint interval lifted
to environment variables, and the evaluation harness swaps a named weight
set into the image and records its name in every trace header.

Two defects in the shipped trainer surfaced on the way, neither of which the
shipped pipeline could have hit. `models.cage4.load()` ends with `eval()`,
which clears the agent's `training` flag, and the class's `train()` sets the
network modes without setting the flag back, so a restored agent inside the
trainer returns evaluation-style actions and the worker fails; the shipped
pipeline never restores. And the trainer builds all 25 parallel environments
with the same seed, so they start from the same scenario draw and diverge
only as far as blue's own sampling pushes them apart; the continuation seeds
them `seed+i` and keeps the shipped behaviour behind a switch. The second
belongs with the nine evaluation defects as a disclosure for Paper 1.

Three continuations of 2,000 episodes (1M environment steps, the H-MARL
first budget; 80 updates of 25 episodes at the shipped learning rate, batch
and epochs), three seeds, one at a time: the stock red as control, Wrecker,
and Q32 as the intermediate point on the targeting axis; then one
10,000-episode continuation under Wrecker with a checkpoint every 500.
KEEP's training curve is in score units (the same stochastic policy on
different seeds), so it can be read directly; seeds 1001 and 1002 also
kept checkpoints at 500, 1000 and 1500 episodes.

| Trained under | Seed | First 10 updates | Last 10 | Halves | Slope per update |
|---|---|---|---|---|---|
| stock | 1000 | -209 | -217 | -217.5, -217.2 | -0.05 +/- 0.07 |
| stock | 1001 | -218 | -250 | -221.9, -221.4 | -0.17 +/- 0.10, died at update 77 |
| stock | 1002 | -199 | -252 | -229.0, -283.5 | -1.11 +/- 0.24, mid-run collapse to -398 |
| Wrecker | 1000 | -1129 | -1038 | -1092, -1026 (t 4.1) | +1.41 +/- 0.35 |
| Wrecker | 1001 | -1109 | -985 | -1089.9, -1084.2 | +0.73 +/- 0.46 |
| Wrecker | 1002 | -1170 | -1112 | -1167.0, -1223.7 | +0.01 +/- 0.64, down to -1573 at update 48 |
| Q32 | 1000 | -770 | -851 | -804, -858 (t -3.4) | -1.51 +/- 0.33 |
| Q32 | 1001 | -753 | -682 | -747.1, -695.4 | +1.35 +/- 0.24 |
| Q32 | 1002 | -788 | -877 | -796.1, -873.2 | -1.60 +/- 0.32 |
| Wrecker, 10,000 ep | 1000 | | | 500-episode means -1159 to -1297, mean -1280 | never above the start |
| Wrecker, learning rate 0.1x | 1000 | -1158 | -1118 | -1148.0, -1112.5 | +0.78 +/- 0.34 |
| stock, learning rate 0.1x | 1000 | -194 | -180 | -186.8, -184.3 | +0.09 +/- 0.06 |

The curves have no common shape. Under Wrecker seed 1000 gains in its
first thousand episodes and stops, seed 1001 gains in its last five
hundred, seed 1002 falls to -1573 and climbs back to where it began. The
stock control at every seed is knocked off its optimum within a few
updates (a fresh optimizer state at the shipped learning rate) and then
wanders, twice into a collapse. Q32 goes down, up, down across the three
seeds. The long run spends all 10,000 episodes at or below its starting
level, 400 below it at 2,500 episodes. At a tenth of both learning rates
(actor 3e-5, critic 1e-4) there is no knock and no wander: the stock
control's sd across updates is 13 against 15 to 56 at the shipped rate,
and the Wrecker curve drifts up by 36 in training units over the run.

The weights through the harness, seeds 0-99, paired against the
shipped-policy arms (band under Wrecker +/-81 and 45-51 wins; under stock
+/-15 and 35-66):

| Weights | Adversary | Seed 1000 | Seed 1001 | Seed 1002 |
|---|---|---|---|---|
| Wrecker-trained, final | Wrecker | +95.4 (60/100) | +167.2 (70/100) | +28.9 (55/100) |
| Wrecker-trained, 500 / 1000 / 1500 ep | Wrecker | | +24, +16, +177 | -104, -240, +11 |
| Wrecker-trained, final | stock | -63.6 | -64.5 | -91.6 |
| Wrecker-trained, final | Q32 | +75.0 | +109.8 | -5.8 |
| stock-trained, 500 / 1000 / 1500 / final | stock | -11.2 (final) | -50, -4, -74 | -50, -152, -89, -46 |
| stock-trained, final | Wrecker | -45.7 | -351.3 | -213.0 |
| Q32-trained, final | Q32 | -65.7 | +92.9 | -119.3 |
| Q32-trained, final | Wrecker | -130.7 | +45.5 | -115.2 |
| Q32-trained, final | stock | -52.3 | -27.1 | -151.5 |

The long run's twenty checkpoints under Wrecker: -82, -131, -88, -456,
-278, -240, -107, -250, +31, +151, -103, -120, -139, -248, -334, -286,
-238, -72, -191, -213 (the final). Two positive, seventeen below the band,
mean -170; the final is -123 against the stock red.

The 0.1x learning rate, every checkpoint inside its band: Wrecker-trained
under Wrecker -60, +8, +21, +19 (final 55/100, p 0.37); the same weights
under stock +6, +5, +4, -4; the stock control under stock -8, +14, +6, +17
(the last at 66/100, the band's edge) and under Wrecker -53 (50/100).

The supervisor on every retrained policy, O1 at gap 32 under Wrecker:

| Policy | Control | With O1 | O1's gain | Against shipped + O1 (-663) |
|---|---|---|---|---|
| shipped | -1115.65 | -663.38 | +452 | |
| Wrecker seed 1000 | -1020.23 | -626.33 | +394 | +37, 55/100, p 0.37 |
| Wrecker seed 1001 | -948.46 | -657.39 | +291 | +6, 50/100, p 1.0 |
| Wrecker seed 1002 | -1086.71 | -674.79 | +412 | -11, 52/100, p 0.69 |
| Wrecker 10,000 ep | -1328.96 | -713.67 | +615 | -50, 38/100, p 0.021 |
| Wrecker, learning rate 0.1x | -1096.79 | -638.59 | +458 | +25, 54/100, p 0.48 |

Least squares over the six: `endpoint = -458 + 0.186 x control`, r 0.78,
residuals within 24. O1's gain as a fraction of each policy's own excess
loss: 0.49, 0.47, 0.38, 0.46, 0.54, 0.50. Investigation behaves the same
way: O10 at gap 32 on the gentle-rate policy is +121 (60/100), a fraction
of 0.133, against +127 and 0.137 on the shipped policy.

Four things follow.

**From the shipped weights, the shipped recipe is a random walk.** Under
Wrecker at 2,000 episodes it is positive at all three seeds and outside
the band at two (+95, +167, +29: 0.10, 0.18 and 0.03 of the excess loss,
against 0.49 for O1), with the gain arriving at a different time in each.
Over 10,000 episodes it is below the band at seventeen checkpoints of
twenty, -456 at the worst, and ends 213 worse than it began. Under the
stock red it costs 4 to 152 points at every seed and every checkpoint,
twice through a collapse. Under Q32 the sign depends on the seed. The
first update's knock (a fresh optimizer at 3e-4 and 1e-3 on a converged
policy) and the failure to settle afterwards are the same phenomenon. At
a tenth of the learning rate both disappear, and so does the gain: the
gentle recipe is stable at every checkpoint, costs nothing against the
stock red, and moves the Wrecker score by +19, a null. The shipped rate
walks and costs; the gentle rate sits still; neither recovers the deficit.
Whatever the target is as information, this trainer does not extract it
from 2,000 episodes of Wrecker at either step size.

**At the shipped rate, retraining costs stock competence every time.**
-64, -64 and -92 for the Wrecker-trained policies, -123 for the long run,
and the stock-trained controls themselves never inside the band at seeds
1001 and 1002. The gentle rate costs nothing because it changes nothing.
O1 at gap 32 costs -16 against the stock red for its +452, and is the only
intervention in this study that gains under the adversary without either
losing against the default or doing nothing at all.

**The supervisor's endpoint moves by a sixth of the policy's deficit.** Six
policies from -948 to -1329 unsupervised are brought by the same rule to
-626 to -714, a fit with slope 0.186. For the five policies within 170 of
shipped the endpoints are inside the shipped-plus-O1 band, which is why
the result first looked exactly invariant; the long run's policy, 213
worse, lands 50 worse with O1. The cleaner statement is that O1 at gap 32
recovers a constant fraction, 0.38 to 0.54, of whatever excess loss the
policy it supervises has. What retraining supplies is subtracted from the
supervisor's marginal gain at about five parts in six, and the sum lands
where the environment and the supervision rate put it. Supervision and
retraining are substitutes at this budget, to within that sixth.

**The budget and recipe objections are both closed, downward.** 2,000
episodes is four percent of where KEEP's own training stopped improving;
10,000 is a fifth. The long run did not approach -663, did not hold its
one good checkpoint (+151 at 5,000 episodes, -103 at 5,500), and finished
worse than it started. More budget at the shipped recipe is more walk;
a gentler recipe is no walk and no gain.

### What the mechanism test does to the study

The mechanism test was set up to bound the supervisor's value from a third
side, and it does. On H-MARL the bound is zero by construction: the gate is
the deficit and nothing below it can be trained toward the target. On KEEP
the bound is a twentieth to a fifth of the excess at 2,000 episodes and
negative at 10,000, paid for against the stock red every time, and the
supervisor recovers a constant fraction of whatever deficit is left. The
formal question's three terms are now all measured on the same pairing:
what the defender lacks (the target), what the environment pays for it
(the O1 endpoint, -463 + 0.185 x the unsupervised score under Wrecker at
gap 32), and what the trainer could have supplied instead (a random walk
whose best checkpoint in 16 hours was +151 and whose typical one was
-170).

For the human study this fixes the comparison. The human's ceiling under
Wrecker is not +452 against a shipped defender but +290 to +410 against a
retrained one, and the honest control arm is the retrained defender, not
the shipped one, because a deployed defender that has met its adversary
would have been retrained. That control is cheap (three hours of training
and five minutes of evaluation per adversary) but it has to be chosen by
evaluation, not by training budget, because the trainer wanders: a
checkpoint is a control arm only once its stock-red and Wrecker arms have
been run, and a fair study reports the human against the best retrained
checkpoint it could find, not the last one. The gentle-rate Wrecker policy
is that arm by construction: retrained on its adversary with a recipe that
does no harm, and indistinguishable from the shipped defender.

For Paper 1 the shared training seed is a tenth defect and the trainer's
non-reproducibility from its seed (two runs at `KEEP_SEED` 1000 diverge
within 500 episodes; the joblib workers sample from unseeded generators)
an eleventh, and the trainer's behaviour on restore (a fresh optimizer
walking a converged policy off its optimum in a few updates, then
wandering) is a caution for anyone who fine-tunes a published CC4 agent:
report the stock-red cost alongside the gain, and report the checkpoint
by evaluation, not by episode count.

## A defender that was never trained

The mechanism test left the supervisor's value measured on two learned
defenders and six retrains of one of them, and the cleanest statement it
produced, that O1 at gap 32 recovers a constant fraction of whatever
excess loss the policy has, was a statement about six policies within 400
points of one another. A third defender that was never trained bounds
the claim from the other side: a policy whose every decision is written
down, whose only source of information about compromise is the
observation stream the learned defenders also read, and which can be
made deliberately blind, deliberately all-seeing, or anything between.
It also answers a question the human trial will be asked, which is
whether the supervisory gain is a property of the supervisor or of the
particular network it happened to be tested on. Definitions, pilots,
diagnostics and per-arm numbers are in ARMS.md, "Rule defenders".

### The defenders

Eight rules, all with the same hands (Restore, Remove, Analyse,
DeployDecoy, BlockTrafficZone, AllowTrafficZone, Sleep) and different
eyes. An alert is a substantive observation entry naming an owned host,
excluding the reset listing and the echo of the rule's own action; a
confirmed file is an Analyse result at Density 0.9 or above. R1 restores
only on a confirmed file and spends idle steps analysing alerted hosts.
R2 restores on the second alert as well, R3 on the first. R2d adds a
decoy per server. R4 is the analyst's playbook: enforce the mission's
comms policy inbound to its zones, restore on a confirmed file, Remove
on the first alert and Restore on the second, decoy the least-decoyed
host between; R4p and R4d are its posture-only and posture-plus-decoys
ablations. RT restores any owned host that is compromised in ground
truth: perfect eyes, the same hands. The rules run inside the oracle
harness as the policy, so every supervisor rule, pairing and tool built
for KEEP applies unchanged, and the harness gates (O2e smoke, H-MARL
compat, footer-identical rerun) all reproduce.

### The ladder alone

100 episodes, seeds 0-99, paired with every other arm in the study.

| Defender | stock | Wrecker |
|---|---|---|
| RT (ground truth) | -168.60 | -348.90 |
| H-MARL Expert | -136.43 | -842.76 |
| KEEP shipped | -187.32 | -1115.65 |
| R2d | -772.75 | -3147.38 |
| R2 | -886.41 | -3158.98 |
| R3 | -989.54 | -3341.76 |
| R1 | -994.58 | -3294.39 |
| R4 | -1294.34 | -3564.25 |
| R4t (R4, Analyse for Remove) | -954.63 | -2763.38 |
| R4tn (R4t, no posture) | | -2766.20 |
| R4t3 (R4t, third alert) | | -2956.92 |
| R4d | -6011.80 | -4993.63 |
| R4p | -6507.40 | -5263.93 |
| do nothing | -6592.68 | |

Three things in the table. First, the whole of the adversary's effect on
the learned defenders is detection (under the adversary; under mild reds
H-MARL's selective hand beats RT's blunt one by about thirty, "Distance
to the ceiling" below). A one-line rule with ground truth
scores -349 under Wrecker, 767 better than KEEP and 494 better than
H-MARL, and under the stock red it is within 20 of KEEP and 32 worse than
H-MARL. Given the target, the hands the environment offers are enough;
what the learned defenders lose under Wrecker is the target. Second, the
observation stream on its own carries a rule nine tenths of the way from
doing nothing to KEEP under the stock red and half of the way under
Wrecker. The best evidence ladder (R2, look twice then restore) lands at
-886 and -3159, against a floor of -6593 and about -5264 (R4p). The twenty-episode diagnostic says why (ARMS.md, "What the observation
supports"): as KEEP operates the network the stream is 1.2x chance under
both reds and repeated namings lift it to 0.3 or 0.4 at best; under a
blind defender the stream is richer and the reds separate, repeated
namings reaching 0.68 under stock and 0.5 under Wrecker, and a look at an
alerted host confirms a file one time in seven under stock and one time
in twelve under Wrecker. The flagged set the rules
act on is precise enough (tp 111 against fp 94 under stock) and covers
almost nothing (10,500 compromised host-steps unflagged in three
episodes). Third, the playbook's Remove is its deficit. Posture alone is the
do-nothing floor, because the simulator never enforces the comms policy
on red and red uses allowed routes; decoys alone are the floor plus 500;
and R4 is 400 behind R2 under both reds. R4t, the playbook with an
Analyse on the first alert in place of the Remove and nothing else
changed, recovers +340 under stock and +801 under Wrecker against R4
(70 and 82 of 100): a Remove of a rooted host evicts nothing and the
alert is spent, where an Analyse confirms a file one time in seven and
restores at once. With the Remove gone the rest of the playbook earns
its keep under the adversary: R4t is 396 ahead of R2 under Wrecker
(-2763, the best unsupervised rule defender) and 68 behind it under
stock, so three decoys per host are worth about 400 against a targeting
red and nothing against a spreading one. For the human trial this is
worth knowing before an interface is designed around a runbook: in CC4
the analyst's block scores nothing (R4tn, the playbook without it, is
R4t to within 3 points), the analyst's remove costs 400, and the
analyst's decoys pay only against the adversary that targets, and only
while no one is supplying the target (below).

### The same supervisor on six kinds of policy

O1 at gap 32 under Wrecker, paired against each policy's own control:

| Policy | Wrecker control | With O1 | O1's gain | Fraction of excess | Distance to RT closed |
|---|---|---|---|---|---|
| H-MARL Expert | -842.76 | -744.22 | +98.5 | 0.14 (0.19 against the null centre) | 0.20 |
| KEEP shipped | -1115.65 | -663.38 | +452.3 | 0.49 | 0.59 |
| R4 | -3564.25 | -1581.07 | +1983.2 | 0.87 | 0.62 |
| R4t | -2763.38 | -1256.04 | +1507.3 | 0.83 | 0.62 |
| R2 | -3158.98 | -949.63 | +2209.3 | 0.97 | 0.79 |
| R1 | -3294.39 | -915.58 | +2378.8 | 1.03 | 0.81 |
| RT | -348.90 | -343.75 | +5.2 | | |

The same rule, the same cadence, the same information, is worth +98 on
one policy and +2,379 on another, a factor of 24, and every ordering in
the table is the inverse of the policies' own competence under the
adversary. The fraction of excess loss recovered runs 0.14, 0.49, 0.83, 0.87,
0.97, 1.03 (R4t, the playbook without its Remove, at 0.83). The retrains had put the fraction at 0.38 to 0.54 for six
KEEP policies and the endpoint on a line with slope 0.186; the line
extrapolated 2,000 points beyond its data lands within 180 of R1, R2, RT
and H-MARL and 460 from R4, so it was a KEEP-family fact with a
wider reach than it had any right to, and the constant fraction is an
architecture property, not a supervisor property. What is constant is
the direction: supervision and the policy's own competence are
substitutes, and the supervisor's marginal value is the information the
policy lacks, in the currency of the score.

The fraction stops being a fraction when the policy is far from
competent. It exceeds 1 on R4 at Q16 and R2 at Q32, and its confidence
interval includes 1 on R1 and R2 under Wrecker, because the stock
control of a blind policy is not a ceiling and O1 lifts the rule above
it. For those policies the measure that keeps its meaning is the share
of the distance to RT that the supervisor closes: 0.20 on H-MARL, 0.59
on KEEP, 0.62 on R4, 0.79 on R2, 0.81 on R1. RT with O1 on top is +5.2
at 50 of 100, the check that O1 supplies nothing RT does not have.

The endpoints keep the controls' order to within swaps of neighbours
(KEEP passes H-MARL, R1 passes R2, and R2 and R1 pass R4t) and compress
the spread
by three fifths (3,215 points across the controls, 1,237 across the
endpoints; four fifths without R4). The supervisor does not equalise
policies. It compresses them, and a policy that was better without a
supervisor is usually still better with one.

### The directed look

O10 at gap 32 (Analyse the ground-truth-compromised host, the rest is
the policy's) recovers 0.55 of R2's and R4's excess under Wrecker
against 0.14 on KEEP and 0.14 on H-MARL. The step records say why, and
they revise an earlier attribution. On a rule defender the response to a
look is by construction: a confirmed file is a Restore the next step, an
empty result is nothing. Its latency distribution is therefore the look's
outcome, the share within 10 steps is the look's yield (0.12 to 0.20),
and the rest is the wait for the next passive alert. That distribution
has median 38 and 15 percent within 10 steps on R4, 38 and 13 percent on
R2. KEEP's has median 36 and 15 percent within 10. "Why investigation is
worth a third of substitution" attributed KEEP's slow response to the
policy; the rule shows the same numbers with no policy in the loop. KEEP
acts on a confirmed file about as reliably as a rule that always does,
and does nothing with an empty look, which is correct. The gap between
the look and the substitution is the sensor's yield, one confirmed file
in five to eight looks at a host that is in fact compromised, and no
policy closes it. What differs between policies is what the rest of the
policy does with the time: the rules gain 0.55 of their excess from the
looks because the looks are most of the evidence they will ever get;
KEEP gains 0.14 because it was already looking.

### Along the targeting axis

R4 at Q04, Q16, Q32, Q48 and Q64 (Wrecker), O1 fractions n/a (no
deficit: R4 does 121 better against Q04 than against the stock red),
1.17, 0.95, 0.88, 0.87; R2 on the same points n/a, 1.37, 1.10, 1.04,
0.97. KEEP 0.54, 0.46, 0.45, 0.47, 0.49. The rules' share declines with
the adversary's concentration while KEEP's does not, and every endpoint
falls with it (R4 from -698 at Q04 to -1581 at Q64, R2 from -286 to
-950, KEEP from -251 to -663). The next section shows that the decline
is an artefact of the fraction's denominator. A
supervisor that names the target every 32 steps per agent is worth
proportionally less against an adversary that does its damage between
namings, and a blind policy feels that more than one that fills the
gaps itself.

### Distance to the ceiling

The fraction of excess loss divides the supervisor's gain by the
adversary's cost to the policy, and for a policy whose stock score is far
from the environment's best that denominator is the wrong one: R2's
stock control is -886, so a supervisor that lifts it past that under Q16
scores 1.37. RT supplies the right denominator. It is a policy with
perfect eyes and the same hands, run under the same adversary on the
same seeds, so the share of the distance to RT that a supervised arm
closes is defined whenever the policy is below RT and cannot pass 1
without beating perfect eyes. RT was run under every adversary in the
study (seventeen ceilings, ARMS.md "RT ceilings across adversaries";
`tools_ceiling.py`), and the axis reads differently on it.

| Adversary | H-MARL gap to RT | H-MARL closed | KEEP gap | KEEP closed | R2 gap | R2 closed | R4 closed |
|---|---|---|---|---|---|---|---|
| stock | -32 | above RT (O1 -24) | 19 | -0.86 | 718 | 0.87 | |
| Q04 | 65 | 0.14 [-0.26, 0.41] | 151 | 0.49 [0.36, 0.61] | 625 | 0.82 [0.79, 0.85] | 0.48 |
| Q16 | 224 | 0.33 [0.19, 0.44] | 323 | 0.51 [0.41, 0.58] | 1,585 | 0.79 [0.75, 0.82] | 0.55 |
| Q32 | 324 | 0.43 [0.33, 0.52] | 511 | 0.51 [0.44, 0.58] | 2,184 | 0.79 [0.76, 0.81] | 0.59 |
| Q48 | 426 | 0.34 [0.22, 0.45] | 616 | 0.57 [0.50, 0.62] | 2,463 | 0.80 [0.77, 0.83] | 0.59 |
| Q64 (Wrecker) | 494 | 0.20 [0.03, 0.35] | 767 | 0.59 [0.53, 0.64] | 2,810 | 0.79 [0.76, 0.81] | 0.62 |

O1 at gap 32 closes four fifths of R2's distance to perfect eyes at every
point on the axis and under the stock red, half of KEEP's rising slowly
with concentration, half to three fifths of R4's, and a fifth to two
fifths of H-MARL's, peaking at Q32. The six KEEP policies of the
retraining test sit at 0.49 to 0.63 on this measure (shipped 0.59), so
within an architecture the share still holds and across architectures it
still does not. The fraction's
decline on the rules was its denominator moving; the share of what a
supervisor can do that this supervisor does is flat on the policy that
has no eyes of its own and nearly flat on the one that has. What
concentration changes is the size of the gap, not the supervisor's
reach into it. The directed look on Wrecker closes 0.17 of KEEP's gap
(O10) and 0.20 (O13), and 0.45 of R2's.

One caution before the reds. RT is perfect eyes with one fixed hand,
restore whatever is compromised as soon as it is seen, and under mild
adversaries that hand is not the best one: H-MARL sits 32 above RT under
the stock red and 28 to 39 above it under the eight Trident reds that
leave it better off than stock, because its IoC-gated Recover leaves
low-value compromises alone and saves the restore cost. KEEP is below
RT under every adversary. So the metric reads wherever RT is above the
policy, which is every adversary that produces a deficit, and where a
policy is at or above RT the supervisor's share is undefined and its
delta is negative (H-MARL -24 to -30 on those nine, KEEP -8 to -25), the
same statement either way. Detection is the whole game under the
adversary; under a mild red, selectivity of response is worth thirty
points over perfect detection with a blunt one.

The ceiling also settles the seven Trident reds that the fraction
could not read. Under TargetA, TargetB and their variants, and Combined,
KEEP sits 7 to 37 points below RT, and O1 at gap 32 closes a negative
share (-0.8 to -2.5, five of seven intervals excluding zero): each
override is a Restore the policy would not have made, on a network with
almost nothing left to recover. That is the stock-red result (KEEP 19
below RT, O1 -16) seen seven more times, and it is the operational
statement of "the sign of supervision's value is the sign of the
deficit". Where a gap exists, Impacter (110) and Degrader (123), O1
closes 0.63 and 0.47, KEEP's usual half.

### What this does to the framework and the trial

The four-layer framework puts the supervisor's value at the difference
between what the environment pays for a decision and what the policy
would have decided alone. The rule defenders make that difference
measurable across its whole range on one pairing: zero at RT, a fifth of
the excess on H-MARL, half on KEEP, all of it on a policy with no eyes.
The claim to carry forward is not "the supervisor recovers half the
deficit" but "the supervisor recovers the part of the deficit that is
the information it supplies, and how much of the deficit that is depends
on the policy", and the measure to carry it in is the share of the
distance to the ground-truth ceiling closed, which reads the same on a
blind policy as on a trained one and turns negative where the policy is
already at the ceiling. Under Wrecker, for every policy tested, that part is the
target. A gate flip, posture and decoys are worth nothing, and the one
other thing worth anything, the directed look, is worth what the policy
makes of it: as much as the substitution on H-MARL (+101 against +98), a
quarter of it on KEEP (+127 against +452), half on R2 (+1,252 against
+2,209).

For the human trial the table settles which policy to supervise, and it
is not the one with the largest effect. On a rule defender a supervisor
who can identify compromised hosts produces +2,200 at 100 wins of 100,
which no interface condition will fail to show and none will be
distinguished by, because the fraction is at its ceiling; on H-MARL the
same supervisor produces +98, 1.3 noise bands, which a trial of a few
dozen episodes would struggle to show at all. KEEP's 0.49 is the working range:
a good supervisor and a poor one land on different sides of it, and the
+452 ceiling at 95 of 100 gives a trial of a few dozen episodes room to
tell them apart. The rules are the calibration arm (what a supervisor is
worth when the policy has nothing, and a check that a human's effect is
the information and not the interface) and RT is the ceiling. The
runbook finding is the second thing the trial takes: an interface that
invites the analyst's habitual first moves invites the moves that score
nothing here, and the display should put the eviction decision, with
its evidence, first.

For the papers: the mechanism-test section's "constant fraction" becomes
"constant within an architecture, set by what the architecture lacks
across them", with the six-kinds table as its figure; the O10 latency
attribution is corrected; and the evidence-criterion results (O2e family
and the latch confusion table), which the rule defenders showed to have
counted the reset listing as evidence, were rerun the same day with the
listing excluded and stand with corrected figures ("Observable evidence
does not recover the ground-truth gain", "The evidence latch is
uninformative").

### Open items from this section

- Done 2026-09-26: the O2e family rerun as O2f with the listing and echo
  excluded, seven arms. Conclusion unchanged; figures corrected in place.
- Done 2026-09-26: R4t attributes the playbook's 400 to the Remove.
  The reversal under O1 (R4t -1256 against R2 -950, though R4t leads
  R2 by 396 alone) is located and not explained: R4t3 holds the gap at
  R2's own restore count, so it is not the ladder's use of the decoys'
  alerts; R4tn holds it without posture, so it is the decoys. Three
  decoys per host are +400 alone and -244 supervised, and the network
  carries 8 percent fewer compromised host-steps with them alone and 10
  percent more supervised. What red does on a decoyed host once hosts
  are restored on ground truth is in the `red_action` step records and
  is the next analysis, not the next arm.
- Split the O10 response latency by the look's outcome (`flags_new` at
  the step), and rerun `wo_O10_g32` under the current harness so the KEEP
  arm carries the flags.
- Done 2026-09-26: the eyes diagnostic at twenty episodes per red. Under
  KEEP the two reds look alike (1.2x chance); under a blind defender the
  stock red is the more visible (repeated namings 0.68 against 0.5, a
  look confirming one in seven against one in twelve).

## Sizing the human trial

The arms already contain what a power analysis needs: for every
supervised condition, one hundred per-episode paired deltas against the
policy alone on the same seeds, whose spread is the environment's and
the policy's own episode-to-episode noise. `tools_power.py` resamples
those deltas at each candidate N with the mean shifted to a hypothetical
effect and reports the power of the paired t-test and of the sign test
at alpha 0.05, and the smallest effect detectable at 80 percent power.
A human supervisor adds variance the oracle does not have (attention,
latency, error), so every N below is a floor. Read 2026-09-26
(`read_power.sh`, `data/read_power.txt`).

| Comparison | Mean delta | sd of paired deltas | Smallest effect at 80% power, N = 10 / 20 / 30 / 50 / 100 |
|---|---|---|---|
| KEEP + O1 against KEEP, Wrecker | +452 | 328 | 319 / 216 / 170 / 131 / 90 |
| KEEP + O10 against KEEP, Wrecker | +127 | 384 | 372 / 250 / 199 / 154 / 109 |
| KEEP + O13 against KEEP, Wrecker | +155 | 345 | 356 / 232 / 186 / 141 / 96 |
| sampling nulls against KEEP, Wrecker | -81, +9 | 393, 409 | 396 to 421 / 265 to 273 / 212 to 218 / 161 to 169 / 110 to 115 |
| O1 against O10 (two conditions, paired on seeds), Wrecker | +325 | 315 | 291 / 198 / 160 / 123 / 86 |
| O13 against O10, Wrecker | +28 | 355 | 345 / 230 / 186 / 139 / 100 |
| O1 against O2, Wrecker | +17 | 151 | 165 / 106 / 86 / 61 / 44 |
| KEEP + O2 against KEEP, stock | -16 | 79 | 80 / 56 / 43 / 32 / 23 |
| KEEP + O10 against KEEP, stock | +8 | 70 | 65 / 45 / 36 / 28 / 19 |
| H-MARL + O1 against H-MARL, Wrecker | +98 | 450 | 462 / 304 / 242 / 187 / 129 |
| H-MARL + O10 against H-MARL, Wrecker | +101 | 344 | 324 / 215 / 176 / 140 / 95 |
| R2 + O1 against R2, Wrecker | +2,209 | 594 | 613 / 411 / 320 / 245 / 172 |

Power for particular effects, KEEP under Wrecker, condition against
policy alone (paired t / sign): the full substitution effect of +450 is
seen at N = 10 (0.99 / 0.91); +300 at N = 20 (0.98 / 0.73); +200 at
N = 30 (0.92 / 0.64); +100 needs N = 100 (0.88 / 0.31). Between two
conditions: a 300-point difference at N = 20 (0.99 / 0.89), 200 at
N = 30 (0.95 / 0.77), 100 at N = 100 (0.90 / 0.17).

Five things follow for the design.

**The trial can be sized for substitution-sized effects and not for
look-sized ones.** Under Wrecker the per-episode noise on KEEP is about
330 points, so a condition has to move the score by 170 to be seen in
30 episodes and by 90 in 100. Naming the target is worth up to +452
and is visible in ten; directing a look is worth +127 to +155 and needs
a hundred. A human whose information is the target, delivered at half
O1's precision, lands near +200 and is visible in 30. A human whose
contribution is where to look is not measurable at any budget a trial
can afford. The trial measures target supply, which is what the
framework says the supervisor is for.

**Interface comparisons need 200-point separations.** Two conditions
that differ by 100 need a hundred paired episodes; by 200, thirty; by
300, twenty. O13 against O10 (28 points, the size of a plausible
display tweak) would need about 1,300. So conditions have to differ in
what information reaches the human, not in how it is drawn, unless the
drawing changes what they find.

**The sign test is the wrong statistic at trial sizes.** It is what the
study reports on 100-episode arms, where it is conservative and
sufficient, but at N = 30 it has half the paired t-test's power for a
200-point effect (0.64 against 0.92) because a third of episodes under
Wrecker go the wrong way even under O1 (95 wins of 100 is the best any
arm achieves; O10 wins 66). The trial pre-registers the paired t-test
or Wilcoxon on per-episode deltas with seeds fixed and reports the sign
test alongside.

**The rule defender is the cheap first stage.** On R2 the same
supervisor is worth +2,209 at a sd of 594, a signal-to-noise of 3.7
against KEEP's 1.4, so a human's effect on R2 is measurable at N = 10
with room and interface conditions 320 apart separate at N = 30. A
two-stage design uses R2 to validate that the interface delivers the
target (the information question, cheap and high-signal) and KEEP to
answer the real question (does the human improve a competent policy),
with the KEEP stage sized from the human effect observed on R2 rather
than from the oracle's.

**Episodes are the budget, and a human's are slow.** At gap 32 a
supervisor makes about 78 decisions an episode (five agents, 500
steps); at ten seconds a decision that is a quarter of an hour of
attention per episode, so thirty episodes is a working day per
participant per condition. The choice between few participants with
many episodes and many participants with few is the next design
decision, and it needs the between-participant variance that no oracle
arm can supply; the numbers above are the within-participant floor for
either.

The stock red is the wrong place to run a trial: effects there are 8 to
16 points and mostly costs, on a noise of 70 to 80. `keep_null` does not
share episode names with `corpus_v1` and is not in the table; the stock
sampling band is +/-15 from "Interpretation floor".
