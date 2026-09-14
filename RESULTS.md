# CAGE 4 Baseline Reproduction Notes

## Overview

Record of the first working session standing up CybORG CAGE Challenge 4 and
reproducing the KEEP baseline, then extended across later sessions. Covers container build, dependency pins not
declared by either repo, a clean reproduction of the published score, and three
defects found in the KEEP evaluation harness that affect reproducibility. Five
upstream defects and four local ones are recorded across this file.

Scope was the go/no-go gate. Reproduce a published autonomous baseline in a
container we control, so later human supervision work has something valid to
compare against. Gate passed.

Early sections come from a single machine and a single image. The cross-machine
reproduction section supersedes that limitation.

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

**SUPERSEDED — see "Two criteria, two answers" below.**

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

**SUPERSEDED — see "Two criteria, two answers" below.**

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

**SUPERSEDED — see "Two criteria, two answers" below.** The claim in this
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

Rescoring H-MARL's restores against observable evidence is the natural next
measurement and is not yet done. It requires capturing H-MARL traces through
`capture.py`, which currently imports KEEP's `Submission` directly.

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
