# Trace arms

Every arm is 100 episodes of 499 steps against `FiniteStateRedAgent`,
environment seeds 0-99, unless noted. Arms against any other red agent are in
"Red-agent arms" below and name their adversary per row.

`policy_seed` is `capture.py --policy-seed`; unset means policy sampling tracks
the environment seed. Oracle arms are produced by `scripts/oracle.py --rule`.

**Schema A** (`capture.py`): raw per-agent observation, `truth`, action,
per-agent and step rewards, cumulative reward.
**Schema B** (`oracle.py`): `red_action`, `n_compromised_owned`, action,
rewards, and footer `overrides` / `agreements` / `translator_calls`. From
2026-09-15 the header also carries `harness_sha`, `machine`, `red_agent` and
`min_gap`; the step record carries `overrides` as `[[agent, from, to], ...]`;
and the footer carries `latch_tp/fp/fn/own` and `flags_new` (evidence rules),
`deferred` (gap), and executed-override counts by type `analyses` /
`restores` / `removes` / `sleeps`. From commit `d974f69` the header also
carries `workers`. Arms between `dd22fff` and `d974f69` report `analyses` /
`restores` as attempts; see Known issues. From 2026-09-20 the header carries
`weights`: `shipped`, or the name of a `keep_weights/` directory swapped in
by `KEEP_WEIGHTS` (see "Retrained defenders").

**Schema B-H** (`capture_hmarl.py`, H-MARL Expert): Schema B plus per-step
`mode` (the sub-policy each agent executed, `investigate` or `recover`) and
`expert_mode` (the gate's own choice before any rule), and footer
`env_steps`, `mode_overrides`, `recover_agent_steps`; header `harness`,
`defender`, `seed_mode` (`episode` or `compat`), `policy_seed`, `workers`,
and from 2026-09-20 `policy_dir` (the sub-policy checkpoint loaded,
`saved_policies/sub/iter_49/policies/` for the shipped defender).
Every simulator step is recorded, so these arms are 500 steps, not 499.

Neither is a superset of the other. Schema B lacks Tier-3 ground truth; Schema A
lacks `red_action`. Neither logs the counterfactual. See RESULTS.md,
"Schema divergence between capture paths".

---

## Reference arms

| Directory | Policy | policy_seed | Schema | Mean | Stdev |
|---|---|---|---|---|---|
| `corpus_v1` | KEEP sampled | unset | A | -187.32 | 61.24 |
| `arm_keep` | KEEP sampled | unset | A | -187.32 | 61.24 |
| `keep_null` | KEEP sampled | 9000 | A | -196.09 | 51.96 |
| `keep_null_9001` | KEEP sampled | 9001 | A | -198.44 | 83.33 |
| `keep_null_9002` | KEEP sampled | 9002 | A | -183.51 | 49.40 |

`arm_keep` is byte-identical to `corpus_v1` on all 100 footers. Redundant.

`corpus_v1` exists on both machines and reproduces bit-identically.

**KEEP reference value: -191.34, 95% CI [-199.66, -183.02]**, four sampling
seeds. Published KEEP is -193.68, inside the interval.

### Interpretation floor

Identical policies differing only in sampling seed produce mean deltas from
-11.12 to +14.93 and win rates from 35/100 to 66/100. Arm stdev ranges 49.40 to
83.33.

**An arm reporting under ~25 points of mean delta, or under ~66 percent of
episodes improved, has reported nothing.** Always report a null arm alongside.

### H-MARL Expert

Directories under `data/`, not `data/traces`; produced by the H-MARL
`evaluation.py` with the seeding fix (`build/hmarl-fixes.patch`). Ladder arms
from `capture_hmarl.py` are under `data/traces` and listed in "H-MARL Expert
ladder".

| Directory | Seeding | Adversary | Mean | Stdev |
|---|---|---|---|---|
| `hmarl_expert_output` | unseeded | FiniteStateRedAgent | -131.99 | 48.51 |
| `hmarl_s0` | seed 0 | FiniteStateRedAgent | -124.11 | 45.80 |
| `hmarl_s1` | seed 1 | FiniteStateRedAgent | -138.31 | 40.97 |
| `hmarl_s2` | seed 2 | FiniteStateRedAgent | -132.10 | 45.40 |
| `hmarl_s3` | seed 3 | FiniteStateRedAgent | -130.86 | 47.45 |
| `hmarl_red_FiniteStateRedAgent` | seed 0 | FiniteStateRedAgent | -124.11 | 45.80 |
| `hmarl_red_FSRedAgentWrecker` | seed 0 | FSRedAgentWrecker | -863.86 | 365.65 |

**H-MARL Expert reference value: -131.35, 95% CI [-138.25, -124.44]**, four
seeds (`hmarl_s0`–`s3`). Published is -132.63 ± 0.87 (Trident, three-run
spread). The Wrecker comparison in RESULTS.md uses seed 0 (-124.11) because
the Wrecker run is seed 0; the factor is 6.96x on seed 0, 6.58x on the
four-seed mean.

`evaluation.py --seed` reseeds sampling once and resets one CybORG per
episode, so its episode k is not environment seed k. `capture_hmarl.py
--compat` mirrors that order and reproduces both seed-0 rows to the digit
(`data/traces/hm_compat_FiniteStateRedAgent`, `hm_compat_FSRedAgentWrecker`,
100 episodes each; the three-episode running means and standard deviation also
match, -931.00 / -1119.50 / -902.67, sd 420.22). Those two directories are the
harness gate, not arms, and must not be paired against default-mode arms.

---

## Baseline ladder

| Directory | Policy | Schema | Mean | Stdev | Notes |
|---|---|---|---|---|---|
| `arm_keep_greedy` | KEEP argmax | A | -552.2 | 343.7 | Deterministic. All variance is situation, none sampling. |
| `arm_sleep` | Always Sleep | A | -6592.68 | 1340.47 | Verified all-Sleep, 2495/2495 agent-steps |
| `arm_monitor` | Always Monitor | A | -6592.68 | 1340.47 | Monitor executes automatically each step; selecting it is a no-op |
| `arm_analyse` | Sleep/Analyse alternation | A | -6592.68 | 1340.47 | 1250 Sleep / 1245 Analyse per episode |

The three degenerate arms are identical to two decimals despite byte-different
action streams. None alters state, and CC4's reward is insensitive to blue
actions that do not. See RESULTS.md, "The reward floor is action-insensitive".

A random-policy arm was attempted and abandoned: KEEP's action space is not
uniformly samplable (`wrapper/graph_wrapper.py:40`, `IndexError` on
`a_id // MAX_ACTIONS`).

`arm_keep_greedy` percentiles: min -1746, p10 -1142, p25 -758, med -434.5,
p75 -293, max -125. Smooth, not bimodal.

---

## Oracle rules

All rules live in `scripts/oracle_rules.py` (`make_oracle`) and are installed
by `oracle.py` as a wrapper on KEEP's `env.action_translator`, or by
`capture_hmarl.py` as a wrapper on the H-MARL wrapper's `env_step`, in both
cases intercepting each agent's action after translation and before execution.
`translator_calls == 2495` (KEEP, 499 steps) or `2500` (H-MARL, 500 steps) per
episode confirms exactly one interception per agent-step. O11 needs KEEP's
actor and is a no-op on H-MARL; O14 exists only on H-MARL.

`comp` is the list of `(hostname, subnet)` pairs currently compromised within
the acting agent's own subnets, derived from simulator ground truth.

**Blind intervention** — discards KEEP's proposal whenever any compromised host
exists in the agent's subnets:

| Rule | Behaviour |
|---|---|
| `O1` | `Restore` the first compromised host |
| `O3` | `Remove` the first compromised host |
| `O4` | As O1, but `comp` is filtered to expensive zones for the current mission phase |

**Correction** — reads KEEP's proposal and acts on whether it is justified:

| Rule | Behaviour |
|---|---|
| `O2` | Keeps `Restore`/`Remove` on a genuinely compromised host; replaces everything else with `Restore` on the first compromised host |
| `O5` | Budgeted and phase-aware. Ranks `comp` by `-RIA + LWF` from `BlueRewardMachine.get_phase_rewards(phase)`; skips if the best zone weight is under 2; agrees if KEEP already restores a dirty host; otherwise restores the highest-weighted host. Stops overriding once `--budget` is reached (default 77, reset per episode). |
| `O6` | Suppression only. `Restore`/`Remove` on a clean host becomes `Sleep`. Never adds an action. |
| `O8` | As O6, restricted to `Restore`, with a 30-step memory: a restore is permitted if the host is dirty **or** an impact was seen on it within the last 30 steps. |

**Controls:**

| Rule | Behaviour |
|---|---|
| `none` | KEEP unmodified. Reproduces `corpus_v1` exactly. |
| `O7` | Target scramble. Keeps KEEP's action type, randomizes the hostname to any owned host. Isolates targeting from action choice. |

**Value-ranked** — built from the measured restore-target skews rather than
from compromise. Candidates are all owned hosts not currently showing a red
session, ranked by

```
score = zone_penalty_exposure(phase) x (2.0 if server) / (1 + decoys_on_host)
```

where `zone_penalty_exposure` is `-(LWF + ASF + RIA)` from
`BlueRewardMachine.get_phase_rewards(phase)`. All entries in that table are
penalties, so summing and negating gives exposure, with operational_zone_a in
phase 1 at 20 against public_access_zone at 5.

Decoy counts are maintained per episode from `DeployDecoy` passing through the
translator, and reset to zero for a host when it is restored, since the reimage
destroys them.

| Rule | Behaviour |
|---|---|
| `O9r` | Reconstruction. Ignores KEEP's proposal and restores the top-ranked host, up to `--budget`. |
| `O9s` | Supervision. Keeps KEEP's Restore target if it falls in the top third of the ranking; otherwise substitutes the top-ranked host, up to `--budget`. |

**Evidence-criterion** — as O2, but the compromised set is replaced by a latch
over the acting agent's raw observation (`cyborg.get_observation`). A host
enters the latch when named by a substantive observation and leaves it on
Restore or Remove. Footer reports the latch's confusion against ground truth.

| Rule | Behaviour |
|---|---|
| `O2e` | Any substantive entry naming the host; oldest flag first |
| `O2er` | As O2e, most recently observed host first |
| `O2ew` | As O2er, flags expire 30 steps after the last observation naming the host |
| `O2s` | Flag only on a `Files` entry with `Density >= 0.9` (Analyse-confirmed); most recent first |

**Authority** — vary what the supervisor is allowed to decide, ground truth
used only where stated:

| Rule | Behaviour |
|---|---|
| `O10` | Investigate. `Analyse` a ground-truth-compromised host that is not strictly flagged. Never issues a recovery action; KEEP does the recovering. |
| `O11` | Constrain. When a compromised host exists, force `Restore`/`Remove` but take the host from the argmax of KEEP's own action distribution over those two verbs (cached from `agent.actor(*state).probs`). Truth decides whether, KEEP decides where. |
| `O12` | O2s restore if a strictly-flagged host exists, else O10 investigate. |
| `O13` | As O10, rotating: least-recently-investigated compromised host first, none repeated within 50 steps. |
| `O14` | Mode authority (H-MARL only). When a ground-truth-compromised host exists in the agent's subnets and the expert gate says Investigate, the gate is flipped to Recover before the master acts, exactly as an observed IoC would flip it (mask, `high_actionmask`, `return_agent` set together); the recover sub-policy picks the host. Counted as an override, subject to `--min-gap`; agreement when the gate already said Recover. |

**Scheduling** — `--min-gap N` (any rule): an override is discarded, and
booked as `deferred`, if the same agent overrode within its last N steps.
Gap 0 is a no-op. `--budget` still applies; `99999` releases it.

The O5 budget sweep and `oracle_O5c` share a revision and seeding, and the sweep
reproduces O5c exactly. `oracle_O5` predates that revision.

---

## Oracle arms

| Directory | Rule | n | Mean | Stdev | Overrides/ep |
|---|---|---|---|---|---|
| `oracle_O5b` | none | 100 | -187.32 | 61.24 | 0 |
| `oracle_O6` | O6 | 100 | -201.49 | 168.93 | 270.7 |
| `oracle_O6b` | O6 | 100 | -201.49 | 168.93 | 270.7 |
| `oracle_O5` | O5 | 100 | -238.56 | 48.04 | 77.0 |
| `oracle_O5c` | O5 (rev. 2026-09-13) | 100 | -246.05 | 65.56 | 77.0 |
| `o2e_b77` | O2e, budget 77 | 100 | -256.48 | 53.46 | 77.0 |
| `oracle_O8` | O8 | 100 | -253.27 | 197.27 | 154.0 |
| `oracle_O7` | O7 | 100 | -511.95 | 165.48 | |
| `oracle_O1_n100` | O1 | 100 | -520.29 | 93.43 | 401.8 |
| `oracle_O2_n100` | O2 | 100 | -523.19 | 97.98 | 403.2 |
| `oracle_O3_n100` | O3 | 100 | -5803.89 | 1328.90 | 2255.1 |
| `o10_g32` | O10, gap 32 | 100 | -179.75 | 53.82 | 60.9 |
| `o2s_g32` | O2s, gap 32 | 100 | -186.79 | 52.86 | 5.1 |
| `o2_g32` | O2, gap 32 | 100 | -203.42 | 63.60 | 52.9 |

`o2e_b77` is the evidence-criterion rule at the human budget under the default
red. It costs about what ground-truth O5 costs at the same budget (-69 against
-59): where no criterion helps, both cost the same.

`o2_g32`, `o2s_g32` and `o10_g32` are the spread-schedule controls under the
default red: -16 (39/100, sign p 0.035, edge of the null band), +0.5 and +7.6.
Scheduling and authority do not create value against the default red.

Against `corpus_v1`, O1 and O2 beat KEEP on 1 episode of 100 each; O3 on none.

O1 and O2 converge despite different logic. O2's conditional never binds: with
20 to 45 hosts compromised throughout an episode, "is any host compromised" is
always true, so it agrees only 1.4 times per episode and degenerates into O1.

O3 at -5803.89 sits near the do-nothing floor of -6592.68, with a comparable
standard deviation (1328.90 vs 1340.47).

`oracle_O6` and `oracle_O6b` differ only in footer `wall_seconds`; O6b is a
rerun. `oracle_O5b` was captured with `--rule none` and is a valid
zero-intervention control.

`oracle_O5`'s stdev of 48.04 is inside the null range (49.40 to 83.33) and is
not anomalous. Its percentiles are uniformly worse than `corpus_v1` above the
minimum: min -478, p10 -288, med -238, max -155.

`oracle_O5` and `oracle_O5c` both ran rule O5 and differ by 7.5 points, inside
the null band. RESULTS.md labels O5c "alternative cost model"; the header
records rule and budget only, so whether the expression changed between them or
only the sampling did is not recoverable from the traces. O5c is identified by
reproduction: `o5_b77` regenerates it exactly on the other machine, so O5c is
O5 at the sweep's revision and seeding, and `oracle_O5` predates that revision.

### Smoke arms

Two episodes each, retained for provenance only. Directions were correct in
every case; magnitudes were optimistic by 10 to 17 percent where n=100 values
now exist.

| Directory | Rule | Mean | Stdev | n=100 equivalent |
|---|---|---|---|---|
| `o_smoke` | none (identified by reproduction, 2026-09-15) | -166.50 | 17.68 | |
| `o_smoke_O1` | O1 | -576.50 | 188.80 | -520.29 |
| `o_smoke_O2` | O2 | -541.50 | 140.71 | -523.19 |
| `o_smoke_O3` | O3 | -4963.00 | 431.34 | -5803.89 |
| `o_smoke_O4` | O4 | -260.50 | 102.53 | not run |
| `o_smoke_O5` | O5 | -237.00 | 62.23 | -238.56 |
| `o5b` | not recorded | -223.50 | 81.32 | |
| `smoke_O9r` | O9r | -260.00 | 32.05 | n/a |
| `smoke_O9s` | O9s | -813.67 | 290.34 | n/a |

`o_smoke_O5` agreeing with `oracle_O5` to 1.5 points is coincidence, not
validation.

### O9 result

Three episodes, seeds 0 to 2, where KEEP scores -154, -179, -195 (mean -176).

| Arm | Mean | Stdev | Overrides/ep | Agreements/ep |
|---|---|---|---|---|
| `smoke_O9r` | -260.00 | 32.05 | 77.0 | 0.0 |
| `smoke_O9s` | -813.67 | 290.34 | 77.0 | 15.0 |

O9s agrees with KEEP on 15 of 77 restores. A ranking derived from KEEP's own
aggregate target statistics predicts its per-decision choice about a fifth of
the time.

An earlier version inherited O5's `-RIA + LWF`, which inverts the ranking.
Correcting it moved agreement from 12.3 to 15.0 and made both arms slightly
worse: -246.67 to -260.00 and -685.00 to -813.67. The sign was wrong and was
not the cause.

Neither arm was run at n=100. **Aggregate skews describe the distribution of
KEEP's targets without reconstructing the rule that produced them.**

O9s intervening less and scoring worse than O9r repeats a pattern from O6 and
O8: partial intervention is consistently worse than full replacement across
this series, and no explanation for it is established.

---

## O5 budget sweep

`--rule O5 --budget N`, 100 episodes each, six workers. Captured on the second
machine.

| Directory | Budget | Mean | Stdev | Delta vs KEEP | Overrides/ep |
|---|---|---|---|---|---|
| `o5_b0` | 0 | -187.32 | 61.24 | reference | 0.0 |
| `o5_b10` | 10 | -186.33 | 52.32 | +0.99 | 10.0 |
| `o5_b20` | 20 | -200.44 | 65.00 | -13.12 | 20.0 |
| `o5_b40` | 40 | -216.15 | 65.21 | -28.83 | 40.0 |
| `o5_b77` | 77 | -246.05 | 65.56 | -58.73 | 77.0 |
| `o5_b150` | 150 | -312.01 | 57.15 | -124.69 | 147.8 |
| `o5_b300` | 300 | -368.92 | 72.59 | -181.60 | 206.2 |

Monotonic decline, roughly -0.9 points per override from budget 20 onward. No
interior peak. Only budgets 0 to 20 fall inside the null band.

`o5_b0` reproduces `corpus_v1` and `o5_b77` reproduces `oracle_O5c`, both from
the reference machine at a different worker count. `o5_b77` does not reproduce
`oracle_O5` (-238.56); see the O5/O5c note under Oracle arms.

---

## Red-agent arms

Adversary named per row. KEEP sampled, `policy_seed` unset, Schema A via
`capture.py --red`, unless noted. Captured on the Alienware.

### Heuristic red agents from Trident Appendix B

| Directory | Red agent | Mean | Stdev | Min | Max |
|---|---|---|---|---|---|
| `red_FiniteStateRedAgent` | FiniteStateRedAgent | -187.32 | 61.24 | -527 | -113 |
| `red_FSRedAgentTargetARestricted` | TargetARestricted | -98.52 | 48.61 | -228 | -22 |
| `red_FSRedAgentTargetAOperational` | TargetAOperational | -99.89 | 55.40 | -415 | -22 |
| `red_FSRedAgentTargetA` | TargetA | -104.18 | 55.60 | -315 | -22 |
| `red_FSRedAgentTargetB` | TargetB | -116.25 | 54.19 | -262 | -22 |
| `red_FSRedAgentTargetBRestricted` | TargetBRestricted | -117.93 | 63.29 | -488 | -22 |
| `red_FSRedAgentTargetBOperational` | TargetBOperational | -127.31 | 88.17 | -607 | -22 |
| `red_FSRedAgentCombined` | Combined | -165.87 | 84.76 | -523 | -22 |
| `red_FSRedAgentFailureTracker` | FailureTracker | -205.66 | 90.26 | -755 | -99 |
| `red_FSRedAgentImpacter` | Impacter | -228.73 | 129.53 | -608 | -70 |
| `red_FSRedAgentDegrader` | Degrader | -268.80 | 122.38 | -852 | -120 |

`red_FiniteStateRedAgent` reproduces `corpus_v1`: the `--red` path is
transparent.

`red_FSRedAgentTargetA` was captured serially after a segfault under parallel
capture.

Seven arms share a maximum of exactly -22. It is reached only by environment
seeds 90 (seven arms) and 92 (three arms), each with fixed penalised step
indices regardless of adversary (21 and 22 steps; composition 478 x 0,
20 x -1, 1 x -2). A seed-fixed green-activity cost no blue action avoids.

Seven of the ten non-default agents make blue's task easier, five by 60 to 89
points. Only the action-biased agents (Degrader, Impacter, FailureTracker) hurt
blue. Concentrating red on one zone reduces exploration and narrows the problem
the five blue agents face; the reward counts green work failures and successful
impacts, so biasing toward those actions is what moves it.

These agents carry a compounding bug in `_choose_host_and_action`
(`host_action_options[opt] *= 4` inside a loop); numbers are as-shipped.

**The -22 optimum is seed-determined.** The ten episodes that reach it, across
seven red agents, share two step-index templates exactly: 21 penalised steps
under one environment seed, 22 under another, the same indices regardless of
adversary. The cost is the green agents' scheduled activity under that seed,
charged whether or not red acts, and no blue action avoids it. -22 is the
floor of the penalty the environment levies on its own, not a ceiling blue
reaches.

### Wrecker

`red_agents/FSRedAgentWrecker.py`. Hand-specified point in Trident's planner
schema: 64 percent of host-state priority on R and RD, root-state rediscovery
0.50 to 0.05, Impact and DegradeServices 0.50 combined to 0.95. Impact-focused
adversary; the defender is unchanged and at deployment competence.

| Directory | Policy | policy_seed | Rule | Budget | Mean | Stdev | Overrides/ep | Agreements/ep |
|---|---|---|---|---|---|---|---|---|
| `red_FSRedAgentWrecker` | KEEP sampled | unset | none | | -1115.65 | 272.91 | 0 | |
| `wrecker_null_9000` | KEEP sampled | 9000 | none | | -1196.35 | 336.69 | 0 | |
| `wrecker_null_9001` | KEEP sampled | 9001 | none | | -1107.05 | 297.93 | 0 | |
| `data/hmarl_red_FSRedAgentWrecker` | H-MARL Expert | seed 0 | none | | -863.86 | 365.65 | 0 | |
| `wo_O8` | KEEP sampled | unset | O8 | | -1396.42 | 534.72 | 186.8 | 34.9 |
| `wo_O6` | KEEP sampled | unset | O6 | | -1296.47 | 525.48 | 293.7 | 69.9 |
| `wo_O5` | KEEP sampled | unset | O5 | 77 | -1013.89 | 373.83 | 77.0 | 0.1 |
| `wo_O2_b10` | KEEP sampled | unset | O2 | 10 | -1093.77 | 357.78 | 10.0 | 62.2 |
| `wo_O2_b20` | KEEP sampled | unset | O2 | 20 | -1012.49 | 345.35 | 20.0 | 59.1 |
| `wo_O2_b40` | KEEP sampled | unset | O2 | 40 | -958.31 | 315.42 | 40.0 | 55.3 |
| `wo_O2_b77` | KEEP sampled | unset | O2 | 77 | -874.27 | 280.66 | 77.0 | 49.3 |
| `wo_O2_b77x` | KEEP sampled | unset | O2 | 77 | -874.27 | 280.66 | 77.0 | 49.3 |
| `wo_O2_b150` | KEEP sampled | unset | O2 | 150 | -767.85 | 211.17 | 150.0 | 34.6 |
| `wo_O2_b300` | KEEP sampled | unset | O2 | 300 | -628.50 | 102.43 | 299.6 | 12.3 |
| `wo_O2_b99999` | KEEP sampled | unset | O2 | 99999 | -654.88 | 69.86 | 403.8 | 1.1 |
| `wo_O2` | KEEP sampled | unset | O2 | 99999 | -654.88 | 69.86 | 403.8 | 1.1 |
| `wo_O2_g2` | KEEP sampled | unset | O2, gap 2 | 99999 | -539.45 | 69.55 | 277.4 | 3.0 |
| `wo_O2_g4` | KEEP sampled | unset | O2, gap 4 | 99999 | -466.01 | 62.37 | 187.9 | 6.0 |
| `wo_O2_g8` | KEEP sampled | unset | O2, gap 8 | 99999 | -457.77 | 97.61 | 110.1 | 11.6 |
| `wo_O2_g16` | KEEP sampled | unset | O2, gap 16 | 99999 | -572.78 | 137.12 | 80.6 | 25.4 |
| `wo_O2_g32` | KEEP sampled | unset | O2, gap 32 | 99999 | -680.42 | 158.46 | 52.7 | 37.7 |
| `wo_O2_b77_g32` | KEEP sampled | unset | O2, gap 32 | 77 | -680.42 | 158.46 | 52.7 | 37.7 |
| `wo_O2_g64` | KEEP sampled | unset | O2, gap 64 | 99999 | -797.25 | 229.27 | 32.0 | 47.3 |
| `wo_O2_g128` | KEEP sampled | unset | O2, gap 128 | 99999 | -889.95 | 255.82 | 18.1 | 55.3 |
| `wo_O2e_b77` | KEEP sampled | unset | O2e | 77 | -1170.05 | 341.22 | 77.0 | 106.4 |
| `wo_O2e_b77_r` | KEEP sampled | unset | O2e | 77 | -1170.05 | 341.22 | 77.0 | 106.4 |
| `wo_O2e_bmax` | KEEP sampled | unset | O2e | 100000 | -1195.90 | 228.23 | 347.4 | 9.3 |
| `wo_O2er_b77` | KEEP sampled | unset | O2er | 77 | -1202.02 | 335.55 | 77.0 | 106.4 |
| `wo_O2ew_b77` | KEEP sampled | unset | O2ew | 77 | -1184.93 | 348.62 | 77.0 | 63.9 |
| `latch_wrecker` | KEEP sampled | unset | O2e | 77 | -1178.65 | 326.33 | 77.0 | 108.6 |
| `wo_O1_g32` | KEEP sampled | unset | O1, gap 32 | 99999 | -663.38 | 174.23 | 52.3 | 0.0 |
| `wo_O2s_g32` | KEEP sampled | unset | O2s, gap 32 | 99999 | -1059.73 | 290.19 | 4.5 | 2.7 |
| `wo_O10_g32` | KEEP sampled | unset | O10, gap 32 | 99999 | -988.35 | 276.10 | 61.2 | 9.6 |
| `wo_O11_g32` | KEEP sampled | unset | O11, gap 32 | 99999 | -1087.58 | 328.71 | 58.7 | 51.0 |
| `wo_O12_g32` | KEEP sampled | unset | O12, gap 32 | 99999 | -989.90 | 289.54 | 61.5 | 3.8 |
| `wo_O13_g32` | KEEP sampled | unset | O13, gap 32 | 99999 | -960.57 | 261.47 | 45.5 | 9.5 |
| `wo_O10_g32y` | KEEP sampled | unset | O10, gap 32 | 99999 | -988.35 | 276.10 | 61.2 | 9.6 |

`wo_O10_g32y` reproduces `wo_O10_g32` on all 100 footers and adds the
`flags_new` field (detection yield 0.16 per investigation; O13, 0.22).

`wo_O2` is byte-identical to `wo_O2_b99999` and `wo_O2_b77_g32` to
`wo_O2_g32` (the gap never lets the count reach 77); both redundant.
`wo_O2_b77x` reproduces `wo_O2_b77` on all 100 footers and adds the
per-step `overrides` field; it supersedes it for analysis. `latch_wrecker` is
20 episodes, captured for the confusion counts. Gap arms carry `min_gap` in
the header; earlier arms do not (gap 0).
`--rule none --red FSRedAgentWrecker` reproduces the unsupervised arm exactly.

**Wrecker noise floor**, three policy seeds: grand mean -1139.68, 95% CI
[-1262.07, -1017.30]. Pairwise deltas between identical policies -80.70 and
+8.60; win rates 45/100 and 51/100. **The bar at this difficulty is roughly 81
points of mean delta and a win rate outside 45 to 51 of 100**, against 25 points
and 66/100 at normal difficulty.

Variance decomposition under Wrecker: within-episode 256.41, between-episode
185.56, ratio 0.72. At normal difficulty, 44.50 and 36.39, ratio 0.82.

O2 unbounded beats KEEP on 100/100 episodes; distributions do not overlap (O2
worst -848, KEEP best -646). At 403.8 overrides and 1.1 agreements it is a
substitute policy, not a supervisory condition. Supervisory conditions are the
spread arms: O1/O2 at gap 32 (+452 / +435, 95 and 93 of 100) and O10 at gap 32
(+127, 66 of 100).

O1 and O2 are indistinguishable under Wrecker: paired at gap 32, O1 - O2 is
+17.04, 49/100, sign p 0.92. O1 is the rule reported.

Paired wins against `red_FSRedAgentWrecker`, spread arms: O1 95, O2 93, O12
67, O10 66, O11 53, O2s 53 (of 100); O11 and O2s are inside the null.

KEEP's action mix under Wrecker is within one percentage point of `corpus_v1`
on every action, same rank order. Wrecker leaves fewer hosts compromised (26.3
of 97 at step 400, against 32.1).

### Conversion and priority sweeps

Generated from `FSRedAgentWrecker` by `tools_gen_conversion_sweep.py` (P:
Wrecker priority, R-row damage probability varied; `ConvOnly`: Wrecker
transitions, no priority list) and `tools_gen_priority_sweep.py` (Q: Wrecker
transitions, R/RD priority mass varied, remainder in Wrecker's proportions).
Each point has a KEEP control (`capture.py --red`, Schema A, 12 workers) and
an O1 arm at gap 32 (`oracle.py`, Schema B, 6 workers). P95 reproduces
`red_FSRedAgentWrecker` and `wo_O1_g32` to the digit.

| Control directory | Oracle directory | Red agent | KEEP | O1 gap 32 | Delta | Wins |
|---|---|---|---|---|---|---|
| `red_FSRedAgentWreckerP10` | `o1_g32_FSRedAgentWreckerP10` | P10 | -1061.55 | -643.17 | +418.38 | 91/100 |
| `red_FSRedAgentWreckerP30` | `o1_g32_FSRedAgentWreckerP30` | P30 | -1025.48 | -672.71 | +352.77 | 90/100 |
| `red_FSRedAgentWreckerP50` | `o1_g32_FSRedAgentWreckerP50` | P50 | -1069.08 | -640.65 | +428.43 | 90/100 |
| `red_FSRedAgentWreckerP70` | `o1_g32_FSRedAgentWreckerP70` | P70 | -1093.24 | -646.02 | +447.22 | 91/100 |
| `red_FSRedAgentWreckerP85` | `o1_g32_FSRedAgentWreckerP85` | P85 | -1081.40 | -656.84 | +424.56 | 91/100 |
| `red_FSRedAgentWreckerP95` | `o1_g32_FSRedAgentWreckerP95` | P95 (= Wrecker) | -1115.65 | -663.38 | +452.27 | 95/100 |
| `red_FSRedAgentConvOnly` | `o1_g32_FSRedAgentConvOnly` | ConvOnly | -316.62 | -268.19 | +48.43 | 63/100 |
| `red_FSRedAgentConvOnly_null9000` | | ConvOnly, policy_seed 9000 | -301.66 | | +14.96 vs control | 51/100 |
| `red_FSRedAgentWreckerQ32_null9000` | | Q32, policy_seed 9000 | -764.96 | | +8.1 vs control | 56/100 |
| `red_FSRedAgentWreckerQ04` | `o1_g32_FSRedAgentWreckerQ04` | Q04 | -325.11 | -250.60 | +74.51 | 71/100 |
| `red_FSRedAgentWreckerQ16` | `o1_g32_FSRedAgentWreckerQ16` | Q16 | -539.17 | -376.15 | +163.02 | 80/100 |
| `red_FSRedAgentWreckerQ32` | `o1_g32_FSRedAgentWreckerQ32` | Q32 | -773.08 | -510.80 | +262.28 | 81/100 |
| `red_FSRedAgentWreckerQ48` | `o1_g32_FSRedAgentWreckerQ48` | Q48 | -928.16 | -579.43 | +348.73 | 93/100 |

Q64 is Wrecker. Stdevs for the control arms are in the footers; the O1 arms:
P10 155.12, P30 199.10, P50 147.04, P70 165.91, P85 203.96, ConvOnly 81.52,
Q04 75.73, Q16 102.11, Q32 128.44, Q48 148.02.

### H-MARL Expert ladder

Produced by `scripts/capture_hmarl.py` in `cage-hmarl:dev`, Schema B-H.
Default seeding is the oracle convention: fresh `CybORG(seed=ep)` per episode,
sampling reseeded per episode (`--policy-seed P` uses `P+ep`), environment
seeds 0-99, six spawn workers, twelve seconds an episode. All arms gap 32
unless noted. Delta, wins and sign p are paired against the control on the
same environment seeds, from `tools_paired.py`.

| Directory | Adversary | Rule | policy_seed | Mean | Stdev | Delta | Wins | Sign p | Executed/ep | Agreements/ep |
|---|---|---|---|---|---|---|---|---|---|---|
| `hm_w_none` | FSRedAgentWrecker | none | ep | -842.76 | 312.94 | control | | | 0 | |
| `hm_w_none_p9000` | FSRedAgentWrecker | none | 9000+ep | -915.97 | 354.28 | -73.2 | 43/100 | 0.19 | 0 | |
| `hm_w_none_p9001` | FSRedAgentWrecker | none | 9001+ep | -898.46 | 354.60 | -55.7 | 47/100 | 0.62 | 0 | |
| `hm_w_none_p9002` | FSRedAgentWrecker | none | 9002+ep | -896.31 | | -53.5 | 44/100 | 0.27 | 0 | |
| `hm_w_none_p9003` | FSRedAgentWrecker | none | 9003+ep | -890.41 | | -47.6 | 43/100 | 0.19 | 0 | |
| `hm_w_none_p9004` | FSRedAgentWrecker | none | 9004+ep | -854.60 | | -11.8 | 48/100 | 0.76 | 0 | |
| `hm_wo_O1_g32` | FSRedAgentWrecker | O1 | ep | -744.22 | 330.34 | +98.5 | 65/100 | 0.004 | 54.0 restores | 0.0 |
| `hm_wo_O10_g32` | FSRedAgentWrecker | O10 | ep | -741.90 | 239.51 | +100.9 | 55/100 | 0.37 | 59.4 analyses | 10.6 |
| `hm_wo_O13_g32` | FSRedAgentWrecker | O13 | ep | -804.14 | 252.39 | +38.6 | 55/100 | 0.37 | 44.7 analyses | 10.3 |
| `hm_wo_O14_g32` | FSRedAgentWrecker | O14 | ep | -880.27 | 298.60 | -37.5 | 43/100 | 0.23 | 57.8 gate flips | 293.1 |
| `hm_wo_O2e_g32` | FSRedAgentWrecker | O2e | ep | -993.01 | 307.02 | -150.2 | 36/100 | 0.007 | 72.3 restores | 9.6 |
| `hm_s_none` | FiniteStateRedAgent | none | ep | -136.43 | 49.60 | control | | | 0 | |
| `hm_s_none_p9000` | FiniteStateRedAgent | none | 9000+ep | -136.36 | 48.56 | +0.1 | 51/100 | 0.92 | 0 | |
| `hm_so_O1_g32` | FiniteStateRedAgent | O1 | ep | -160.69 | 38.29 | -24.3 | 22/100 | 1.6e-08 | 53.1 restores | 0.0 |
| `hm_so_O10_g32` | FiniteStateRedAgent | O10 | ep | -129.23 | 46.26 | +7.2 | 54/100 | 0.36 | 57.7 analyses | 7.9 |

Recover agent-steps per episode, of 2,500: `hm_w_none` 263.1, `hm_s_none`
247.3; under Wrecker O1 200.5, O10 281.0, O13 264.3, O14 350.4, O2e 236.7.

`hm_s_none` (-136.43) sits inside the four-seed interval [-138.25, -124.44].
`hm_w_none` (-842.76) is the per-episode-seeded counterpart of the compat
-863.86; they are different seedings and are not expected to agree.

**H-MARL noise floor under Wrecker**, five policy seeds against the
control: deltas -73.2, -55.7, -53.5, -47.6, -11.8 (mean -48.4, sd 22.6),
wins 43 to 48 of 100, every one below the control, so `hm_w_none`
(-842.76) is the best of six sampling draws and the six-draw mean is
-883.1. **The bar is roughly 75 points of mean delta and a win rate
outside 43 to 48 of 100**, the same width as KEEP's under Wrecker; a
delta quoted against `hm_w_none` understates a gain by about 40 relative
to the null centre. Against the stock red the single null is +0.1 and
51/100, and under Q32 (`hm_WreckerQ32_none_g0_p9000`, -591.85) -6.1 and
52/100: this defender's sampling barely moves its score away from Wrecker.

`hm_wo_O14_g32` was first launched with a version of the rule that overrode
the master's output and patched `return_agent` by hand; the wrapper's HITL
consistency check tripped mid-run and the directory was deleted. The reported
arm is the gate-flip form described under Oracle rules. `hm_compat_gate3b`,
`hm_compat_wrecker_3`, `hm_gate_patch`, `hm_gate_pilot` and
`hm_compat_gate3k` are three-episode harness gates, not arms (all -931.00,
-1308.00, -469.00 except `hm_gate_pilot`, which loads the one-iteration
`pilot_wrecker` checkpoint: -829, -2551, -1556); `data/hm_gate3` is the
matching three-episode `evaluation.py` run.

`wo_O2e_b77_r` (under Wrecker, above) is `wo_O2e_b77` rerun after the
`owned_hosts` cache fix: identical on every shared footer key across all 100
episodes, and it adds the latch and executed-count fields the original
predates.

Latch confusion against ground truth, summed over 100 episodes
(`tools_investigate.py`; the H-MARL arms above carry the counters under the
raw keys `tp` / `fp` / `fn` / `own`, later traces also under `latch_*`):

| Arm | Latch | tp | fp | fn | Precision | Recall |
|---|---|---|---|---|---|---|
| `hm_wo_O2e_g32` | passive | 12,078 | 126,572 | 630,311 | 0.087 | 0.019 |
| `hm_wo_O10_g32` | strict | 6,322 | 2 | 640,313 | 1.000 | 0.010 |
| `hm_wo_O13_g32` | strict | 5,375 | 1 | 640,557 | 1.000 | 0.008 |
| `wo_O10_g32y` (KEEP) | strict | 13,775 | 875 | 704,425 | 0.940 | 0.019 |
| `wo_O13_g32` (KEEP) | strict | 14,066 | 931 | 675,368 | 0.938 | 0.020 |

Investigation measures per arm (response = the acting agent's next Restore
or Remove on the investigated host): H-MARL O10 median 31, p90 139, within
50 44.5%, never 32.8%, gate flip at next step 2.6%; H-MARL O13 32 / 145 /
42.0% / 33.3% / 1.9%; KEEP O10 36 / 133 / 49.8% / 22.4%; KEEP O13 36 / 135
/ 45.8% / 23.7%. Yields (flags_new / analyses) 0.181, 0.233, 0.163, 0.216.
Repeat share 66.1%, 48.0%, 66.3%, 46.8%.

### H-MARL Expert on the targeting axis

The conversion and priority sweep's adversaries on H-MARL, Schema B-H,
default seeding, seeds 0-99, six workers, four minutes an arm (2026-09-22,
`hm_<red>_<rule>_g<gap>`). Each point: control, O1 at gap 32, O10 at gap
32, paired against the control on the same seeds. Fraction = delta over
the point's excess loss (control minus `hm_s_none`, -136.43), paired
bootstrap interval from `tools_fraction_ci.py`. Q64 is Wrecker
(`hm_w_none`, `hm_wo_O1_g32`, `hm_wo_O10_g32`, above).

| Red agent | Control | Excess | O1 mean | O1 delta | Wins | Fraction [95% CI] | O10 mean | O10 delta | Wins | Fraction [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|
| ConvOnly | -232.99 | -96.5 | -243.39 | -10.4 | 40/100 | -0.108 [-0.382, 0.120] | -217.28 | +15.7 | 55/100 | 0.163 [-0.051, 0.340] |
| Q04 | -239.10 | -102.7 | -230.20 | +8.9 | 51/100 | 0.087 [-0.143, 0.277] | -205.96 | +33.2 | 67/100 | 0.323 [0.141, 0.475] |
| Q16 | -440.29 | -303.8 | -367.39 | +72.9 | 68/100 | 0.240 [0.136, 0.332] | -379.77 | +60.5 | 66/100 | 0.199 [0.094, 0.294] |
| Q32 | -585.79 | -449.4 | -446.89 | +138.9 | 74/100 | 0.309 [0.229, 0.383] | -511.62 | +74.2 | 63/100 | 0.165 [0.061, 0.260] |
| Q48 | -738.05 | -601.6 | -593.45 | +144.6 | 67/100 | 0.240 [0.150, 0.321] | -635.73 | +102.3 | 62/100 | 0.170 [0.080, 0.251] |
| Q64 (Wrecker) | -842.76 | -706.3 | -744.22 | +98.5 | 65/100 | 0.140 [0.016, 0.249] | -741.90 | +100.9 | 55/100 | 0.143 [0.052, 0.225] |

Executed per episode: O1 52.9 to 54.3 restores; O10 57.8 to 59.5 analyses
with 10.0 to 13.2 agreements. Recover agent-steps per episode, control /
O1 / O10: ConvOnly 265.0 (O10) and 211.5 (O1); Q04 247.4 / 326.3; Q16
236.3 / 312.8; Q32 230.0 / 303.3; Q48 220.6 / 291.7 (O1 / O10).

KEEP's O1 fractions on the same points, from `corpus_v1`, `red_*` and
`o1_g32_*` (Wrecker: `wo_O1_g32`): ConvOnly 0.375 [0.166, 0.533], Q04
0.541 [0.397, 0.663], Q16 0.463 [0.374, 0.540], Q32 0.448 [0.381, 0.506],
Q48 0.471 [0.415, 0.521], Q64 0.487 [0.437, 0.534].

Against the Wrecker null centre (-883.1) rather than the control, H-MARL's
Q64 O1 gain is +138.9 and its fraction 0.186.

---

## Retrained defenders

Chapter 4's mechanism question: whether a deployed defender's deficit under an
unseen adversary is a distribution shift its own trainer would close, or a
capacity limit. Both trainers are the authors' pipelines with settings lifted
to environment variables (`tools_patch_hmarl_train.py`,
`tools_patch_keep_train.py`; the resulting diffs are `build/hmarl-fixes.patch`
and `build/keep-train.patch`). Every retrained policy is evaluated through the
same harnesses as the shipped one, and the trace header names the weights.

### H-MARL sub-policy continuation

`subpolicies/train_subpolicies.py` in `cage-hmarl:dev`, restored from the
shipped `saved_policies/sub/iter_49`, shipped hyperparameters (lr 5e-5, 30 SGD
iterations, entropy 0.001, minibatch 32,768), `HMARL_TRAIN_BATCH=100000` so
one iteration is 100k environment steps (the shipped iteration is 1M), twelve
rollout workers, `HMARL_RED` the adversary, `HMARL_SEED` the RLlib seed.
Checkpoints under `repos/Hierarchical-MARL/h-marl-3policy/saved_policies/<run>/iter_N`
(root-owned). Only the ten sub-policies train; the expert master is a rule on
`iocs_exist` and has no parameters, so this is continuation under a frozen
gate by construction. Launchers `run_ft.sh` (ten iterations) and
`run_ft_resume.sh` (to a target iteration, restarting from the last
checkpoint after a trainer crash); completion lines in `data/ft_runs.log`;
trainer output in `data/<run>.log`.

Curve values are RLlib `episode_reward_mean` divided by ten (it sums the ten
policy-agents' rewards), a trailing window of 100 training episodes under
sampling, so not evaluation numbers; the window resets after every restore.
Read with
`grep -o "episode_reward_mean': [-0-9.]*" data/<run>.log | awk -F': ' '$2!=p{printf "%.0f ", $2/10; p=$2}'`
(the trainer prints each iteration twice).

| Run | Adversary | RLlib seed | Iterations | Env steps | Curve, score units |
|---|---|---|---|---|---|
| `pilot_wrecker` | FSRedAgentWrecker | unset | 50 | 100k | timing pilot, 8m33s wall; evaluated as `hm_gate_pilot` |
| `ft_FiniteStateRedAgent_s0` | FiniteStateRedAgent | 0 | 50-99 | 5M | iterations 50-74 mean -140.5, 75-99 mean -145.3; sd across iterations 6.1; slope -0.17 per iteration |
| `ft_FiniteStateRedAgent_s1` | FiniteStateRedAgent | 1 | 50-59 | 1M | flat, `data/ft_FiniteStateRedAgent_s1.log` |
| `ft_Wrecker_s0` | FSRedAgentWrecker | 0 | 50-99 | 5M | iterations 50-74 mean -893.0, 75-99 mean -892.7; sd 34.0; slope +0.01 per iteration |
| `ft_Wrecker_s1` | FSRedAgentWrecker | 1 | 50-59 | 1M | -881 first iteration, -840 last, inside the iteration noise |
| `ft_WreckerQ32_s0` | FSRedAgentWreckerQ32 | 0 | 50-59 | 1M | flat, `data/ft_WreckerQ32_s0.log` |
| `ft_WreckerQ32_s1` | FSRedAgentWreckerQ32 | 1 | 50-54 | 500k | -575 -574 -580 -603 -569; the resume to 59 was lost (Known issues) |

`ft_FiniteStateRedAgent_s0` restarted twice from its last checkpoint (after
iter_59 and iter_66) on the trainer crash below; the curve is continuous
across the restarts apart from the window reset.

Evaluation of the 5M-step Wrecker checkpoint (`HMARL_POLICY_DIR=saved_policies/ft_Wrecker_s0/iter_99/policies/`),
Schema B-H, default seeding, environment seeds 0-99, `--rule none`; paired
against the shipped-policy arms on the same seeds:

| Directory | Weights | Adversary | Mean | Stdev | Paired against | Delta | Wins | Sign p | Recover agent-steps/ep |
|---|---|---|---|---|---|---|---|---|---|
| `hm_ft_w99_w_none` | `ft_Wrecker_s0/iter_99` | FSRedAgentWrecker | -945.59 | 402.48 | `hm_w_none` | -102.8 | 43/100 | 0.19 | 203.6 |
| | | | | | `hm_w_none_p9000` | -29.6 | 48/100 | 0.76 | |
| `hm_ft_w99_s_none` | `ft_Wrecker_s0/iter_99` | FiniteStateRedAgent | -143.21 | 59.13 | `hm_s_none` | -6.8 | 47/100 | 0.84 | 200.6 |

Against the shipped control the fine-tuned policy scores exactly what the
p9000 sampling null scores (43/100), and against that null it is 48/100. Five
million steps of sub-policy training under Wrecker produced a policy
indistinguishable from a sampling-seed draw of the shipped one, with no slope
in the curve to extend, and no measurable cost against the stock red. The one
behavioural change is fewer Recover-mode agent-steps (263.1 to 203.6 under
Wrecker, 247.3 to 200.6 under stock): fewer IoC-bearing observations, either
fewer looks that land or faster clearing, and worth nothing either way. These
two arms were captured before the `policy_dir` header field existed; their
provenance is the directory name and `data/hm_ft_w99_*.log`.

### KEEP continuation

`train.py` in `cage-keep:dev`, run from the `/work` mount so the patched
trainer is used; evaluation (`oracle.py`) uses the image's copy at
`/opt/cage/cage-4-submission`, whose weights `KEEP_WEIGHTS=<name>` replaces
with `keep_weights/<name>/gnn_ppo-{0..4}.pt` before the command runs
(`keep_weights/` is not in git). Shipped hyperparameters: 25 episodes per
update, batch 2,500, 4 epochs, `SEED` 1337 for torch and the environments.
Patched: `KEEP_RED`, `KEEP_RESTORE` (a directory of `gnn_ppo-{i}.pt`),
`KEEP_EPISODES`, `KEEP_WORKERS`, `KEEP_SEED`, `KEEP_SHARED_ENV_SEED`,
`KEEP_CKPT`. Restored agents have `training` set back to true (Known
issues). Environments are seeded `seed+i` unless `KEEP_SHARED_ENV_SEED` is
set. The trainer prints `Avg reward for episode` once per update (the 25
episodes' mean under sampling) and writes `logs/<tag>.pt`, a list of
`(avg_reward, episode, loss)`; rolling checkpoints
`checkpoints/<tag>-{i}_checkpoint.pt` every update, kept ones
`<tag>-{i}_e<episodes>.pt` every `KEEP_CKPT` episodes. Launcher
`run_keep_ft.sh <red> <seed> <episodes> [workers]`, tag `kft_<red>_s<seed>`,
one run at a time (Known issues).

Gates for the patched pipeline, 2026-09-20:

| Directory | What | Result |
|---|---|---|
| `o2e_smoke_k` | O2e smoke, 2 episodes, stock red | -327.00, 87.68, 77.0 / 108.5, unchanged; header `weights: shipped` |
| `hm_compat_gate3k` | H-MARL compat, 3 episodes, Wrecker | -931.00, -1308.00, -469.00, unchanged; header `policy_dir` |
| `pilot_wrecker` (checkpoints) | 50 episodes from the shipped weights under Wrecker, 12 workers, `KEEP_SEED` 0 | 5m03s wall, two updates, `Avg reward` -1277.16 then -1167.48 |
| `pilot_wrecker25` (checkpoints) | as above, 25 workers | 4m25s wall |
| `k_pilot_w_gate3` | `KEEP_WEIGHTS=pilot_wrecker`, `--rule none --red FSRedAgentWrecker`, 3 episodes | -852, -1020, -956 against the shipped control's -740, -1484, -1183 on the same seeds; header `weights: pilot_wrecker` |

Continuation runs, 2,000 episodes each (1M environment steps, the H-MARL
first budget, 80 updates), 25 workers, `KEEP_SEED` 1000 (environments
1000-1024, disjoint from the evaluation seeds), one at a time, about 2.2
minutes an update. Curve values are the trainer's `Avg reward for episode`:
25-episode means under sampling on the training seeds, directly comparable
to evaluation values for this defender (same stochastic policy, different
seeds), unlike H-MARL's. No intermediate checkpoints were kept (Known
issues, `KEEP_CKPT`); the `final` weights are the rolling checkpoint after
update 80.

| Tag | Adversary | First 10 updates | Last 10 | Halves | Slope per update | sd |
|---|---|---|---|---|---|---|
| `kft_Wrecker_s1000` | FSRedAgentWrecker | -1128.9 | -1037.6 | -1092.3 / -1026.1 (t 4.1) | +1.41 +/- 0.35 | 79.3 |
| `kft_FiniteStateRedAgent_s1000` | FiniteStateRedAgent | -209.0 | -216.8 | -217.5 / -217.2 | -0.05 +/- 0.07 | 14.6 |
| `kft_WreckerQ32_s1000` | FSRedAgentWreckerQ32 | -769.9 | -850.7 | -804.0 / -858.2 (t -3.4) | -1.51 +/- 0.33 | 76.9 |
| `kft_Wrecker_s1001` | FSRedAgentWrecker | -1108.8 | -985.3 | -1089.9 / -1084.2 | +0.73 +/- 0.46 | 96.2 |
| `kft_FiniteStateRedAgent_s1001` | FiniteStateRedAgent | -218.4 | -249.5 | -221.9 / -221.4 (76 updates) | -0.17 +/- 0.10 | 20.0 |
| `kft_WreckerQ32_s1001` | FSRedAgentWreckerQ32 | -752.7 | -681.6 | -747.1 / -695.4 | +1.35 +/- 0.24 | 59.0 |
| `kft_Wrecker_s1002` | FSRedAgentWrecker | -1170.4 | -1112.2 | -1167.0 / -1223.7 | +0.01 +/- 0.64 | 131.0 |
| `kft_FiniteStateRedAgent_s1002` | FiniteStateRedAgent | -198.5 | -251.5 | -229.0 / -283.5 | -1.11 +/- 0.24 | 56.3 |
| `kft_WreckerQ32_s1002` | FSRedAgentWreckerQ32 | -788.0 | -877.1 | -796.1 / -873.2 | -1.60 +/- 0.32 | 74.8 |
| `kft_Wrecker_s1000_long` | FSRedAgentWrecker, 10,000 episodes | | | 500-episode means -1159 ... -1297, mean -1280 | | |
| `kft_Wrecker_s1000_lr01` | FSRedAgentWrecker, `KEEP_LR_SCALE` 0.1 | -1158.3 | -1117.7 | -1148.0 / -1112.5 | +0.78 +/- 0.34 | 71.5 |
| `kft_FiniteStateRedAgent_s1000_lr01` | FiniteStateRedAgent, `KEEP_LR_SCALE` 0.1 | -193.9 | -179.8 | -186.8 / -184.3 | +0.09 +/- 0.06 | 13.2 |

Quarters, seed 1000: Wrecker -1130, -1055, -1009, -1043 (the gain is in the
first thousand episodes); stock -216, -219, -218, -216 after a first update
at -174; Q32 -771, -837, -840, -876. Seed 1001: Wrecker -1088, -1092,
-1157, -1011 (the gain is in the last quarter); stock -219, -225, -209,
-234, with updates 69-76 at -259 before the run died (Known issues); Q32
-763, -731, -712, -679, the opposite sign from seed 1000. Seed 1002:
Wrecker -1131, -1203, -1337, -1111 (down to -1573 at update 48, then back);
stock -203, -255, -311, -256 (a mid-run collapse to -398, partly recovered);
Q32 -780, -812, -879, -867. Seeds 1001 and 1002 kept checkpoints at 500,
1000 and 1500 episodes (`KEEP_CKPT` forwarded from 18:52 on 2026-09-20);
`kft_FiniteStateRedAgent_s1001`'s `final` is the rolling checkpoint after
update 76.

`kft_*_s1000_lr01` are the shipped recipe with both learning rates
multiplied by 0.1 (actor 3e-5, critic 1e-4; `KEEP_LR_SCALE=0.1`), seed
1000, 2,000 episodes, checkpoints at 500, 1000 and 1500. Quarters: Wrecker
-1145, -1151, -1123, -1102; stock -188, -185, -185, -183. No first-update
knock (the stock curve's first value is -213 against -174 at the shipped
rate, and its sd across updates is 13 against 15 to 56).

`kft_Wrecker_s1000_long` is 10,000 episodes (400 updates, 5M environment
steps) under Wrecker at `KEEP_SEED` 1000 with a kept checkpoint every 500
episodes, 16 hours. Its twenty 500-episode training means: -1159, -1231,
-1181, -1328, -1537, -1328, -1286, -1267, -1195, -1091, -1077, -1222,
-1225, -1306, -1419, -1447, -1432, -1318, -1254, -1297. It diverged from
`kft_Wrecker_s1000` (same seed, same settings apart from `KEEP_EPISODES`)
within the first 500 episodes; see Known issues.

Evaluation of the final weights, `oracle.py`, 100 episodes, seeds 0-99, six
workers, 4.7 minutes an arm (nine arms in 37 minutes on 2026-09-20). Paired
against the shipped-policy arm on the same seeds; band under Wrecker +/-81
and 45-51 wins, under the stock red +/-15 and 35-66 wins; no Q32 null exists
yet.

| Directory | Weights | Adversary | Rule | Mean | Stdev | Against | Delta | Wins | Sign p |
|---|---|---|---|---|---|---|---|---|---|
| `k_kft_Wrecker_s1000_final_w_none` | Wrecker-trained | Wrecker | none | -1020.23 | 301.79 | `red_FSRedAgentWrecker` | +95.4 | 60/100 | 0.057 |
| `k_kft_Wrecker_s1000_final_s_none` | Wrecker-trained | stock | none | -250.93 | 95.47 | `corpus_v1` | -63.6 | 25/100 | 0.000 |
| `k_kft_Wrecker_s1000_final_WreckerQ32_none` | Wrecker-trained | Q32 | none | -698.04 | | `red_FSRedAgentWreckerQ32` | +75.0 | 56/100 | 0.27 |
| `k_kft_Wrecker_s1000_final_w_O1_g32` | Wrecker-trained | Wrecker | O1, gap 32, budget 99999 | -626.33 | | `k_kft_Wrecker_s1000_final_w_none` | +393.9 | 93/100 | 0.000 |
| | | | | | | `wo_O1_g32` (shipped + O1) | +37.0 | 55/100 | 0.37 |
| `k_kft_FiniteStateRedAgent_s1000_final_w_none` | stock-trained | Wrecker | none | -1161.37 | 310.62 | `red_FSRedAgentWrecker` | -45.7 | | |
| `k_kft_FiniteStateRedAgent_s1000_final_s_none` | stock-trained | stock | none | -198.52 | 54.48 | `corpus_v1` | -11.2 | 39/100 | 0.044 |
| `k_kft_WreckerQ32_s1000_final_WreckerQ32_none` | Q32-trained | Q32 | none | -838.79 | | `red_FSRedAgentWreckerQ32` | -65.7 | 38/100 | 0.021 |
| `k_kft_WreckerQ32_s1000_final_w_none` | Q32-trained | Wrecker | none | -1246.31 | | `red_FSRedAgentWrecker` | -130.7 | 38/100 | 0.021 |
| `k_kft_WreckerQ32_s1000_final_s_none` | Q32-trained | stock | none | -239.65 | | `corpus_v1` | -52.3 | 25/100 | 0.000 |

Seed 1001, same pairings (`k_kft_<tag>_<N|final>_<w|s|WreckerQ32>_<rule>`):

| Directory | Weights | Adversary | Mean | Against | Delta | Wins | Sign p |
|---|---|---|---|---|---|---|---|
| `k_kft_Wrecker_s1001_500_w_none` | Wrecker-trained, 500 ep | Wrecker | -1091.30 | `red_FSRedAgentWrecker` | +24.4 | 59/100 | 0.089 |
| `k_kft_Wrecker_s1001_1000_w_none` | Wrecker-trained, 1000 ep | Wrecker | -1100.11 | `red_FSRedAgentWrecker` | +15.5 | 51/100 | 0.92 |
| `k_kft_Wrecker_s1001_1500_w_none` | Wrecker-trained, 1500 ep | Wrecker | -938.73 | `red_FSRedAgentWrecker` | +176.9 | 67/100 | 0.001 |
| `k_kft_Wrecker_s1001_final_w_none` | Wrecker-trained | Wrecker | -948.46 | `red_FSRedAgentWrecker` | +167.2 | 70/100 | 0.000 |
| `k_kft_Wrecker_s1001_final_s_none` | Wrecker-trained | stock | -251.87 | `corpus_v1` | -64.5 | 32/100 | 0.001 |
| `k_kft_Wrecker_s1001_final_WreckerQ32_none` | Wrecker-trained | Q32 | -663.29 | `red_FSRedAgentWreckerQ32` | +109.8 | 63/100 | 0.012 |
| `k_kft_Wrecker_s1001_final_w_O1_g32` | Wrecker-trained | Wrecker | -657.39 | `k_kft_Wrecker_s1001_final_w_none` | +291.1 | 83/100 | 0.000 |
| | | | | `wo_O1_g32` (shipped + O1) | +6.0 | 50/100 | 1.000 |
| `k_kft_FiniteStateRedAgent_s1001_1000_s_none` | stock-trained, 1000 ep | stock | -236.83 | `corpus_v1` | -49.5 | 24/100 | 0.000 |
| `k_kft_FiniteStateRedAgent_s1001_1500_s_none` | stock-trained, 1500 ep | stock | -191.10 | `corpus_v1` | -3.8 | 44/100 | 0.27 |
| `k_kft_FiniteStateRedAgent_s1001_final_s_none` | stock-trained, 76 updates | stock | -261.28 | `corpus_v1` | -74.0 | 17/100 | 0.000 |
| `k_kft_FiniteStateRedAgent_s1001_1000_w_none` | stock-trained, 1000 ep | Wrecker | -1182.58 | `red_FSRedAgentWrecker` | -66.9 | 45/100 | 0.37 |
| `k_kft_FiniteStateRedAgent_s1001_1500_w_none` | stock-trained, 1500 ep | Wrecker | -1239.53 | `red_FSRedAgentWrecker` | -123.9 | 46/100 | 0.48 |
| `k_kft_FiniteStateRedAgent_s1001_final_w_none` | stock-trained, 76 updates | Wrecker | -1466.92 | `red_FSRedAgentWrecker` | -351.3 | 27/100 | 0.000 |
| `k_kft_FiniteStateRedAgent_s1001_final_WreckerQ32_none` | stock-trained, 76 updates | Q32 | -1000.97 | `red_FSRedAgentWreckerQ32` | -227.9 | 27/100 | 0.000 |
| `k_kft_WreckerQ32_s1001_1000_WreckerQ32_none` | Q32-trained, 1000 ep | Q32 | -698.84 | `red_FSRedAgentWreckerQ32` | +74.2 | 56/100 | 0.27 |
| `k_kft_WreckerQ32_s1001_final_WreckerQ32_none` | Q32-trained | Q32 | -680.19 | `red_FSRedAgentWreckerQ32` | +92.9 | 63/100 | 0.012 |
| `k_kft_WreckerQ32_s1001_final_w_none` | Q32-trained | Wrecker | -1070.11 | `red_FSRedAgentWrecker` | +45.5 | 55/100 | 0.32 |
| `k_kft_WreckerQ32_s1001_final_s_none` | Q32-trained | stock | -214.44 | `corpus_v1` | -27.1 | 34/100 | 0.002 |

Seed 1002, same pairings:

| Directory | Weights | Adversary | Mean | Against | Delta | Wins | Sign p |
|---|---|---|---|---|---|---|---|
| `k_kft_Wrecker_s1002_500_w_none` | Wrecker-trained, 500 ep | Wrecker | -1219.79 | `red_FSRedAgentWrecker` | -104.1 | 51/100 | 0.92 |
| `k_kft_Wrecker_s1002_1000_w_none` | Wrecker-trained, 1000 ep | Wrecker | -1355.35 | `red_FSRedAgentWrecker` | -239.7 | 31/100 | 0.000 |
| `k_kft_Wrecker_s1002_1500_w_none` | Wrecker-trained, 1500 ep | Wrecker | -1104.79 | `red_FSRedAgentWrecker` | +10.9 | 47/100 | 0.62 |
| `k_kft_Wrecker_s1002_final_w_none` | Wrecker-trained | Wrecker | -1086.71 | `red_FSRedAgentWrecker` | +28.9 | 55/100 | 0.37 |
| `k_kft_Wrecker_s1002_500_s_none` | Wrecker-trained, 500 ep | stock | -241.93 | `corpus_v1` | -54.6 | 36/100 | 0.009 |
| `k_kft_Wrecker_s1002_1000_s_none` | Wrecker-trained, 1000 ep | stock | -318.12 | `corpus_v1` | -130.8 | 10/100 | 0.000 |
| `k_kft_Wrecker_s1002_1500_s_none` | Wrecker-trained, 1500 ep | stock | -239.65 | `corpus_v1` | -52.3 | 31/100 | 0.000 |
| `k_kft_Wrecker_s1002_final_s_none` | Wrecker-trained | stock | -278.92 | `corpus_v1` | -91.6 | 23/100 | 0.000 |
| `k_kft_Wrecker_s1002_final_WreckerQ32_none` | Wrecker-trained | Q32 | -778.89 | `red_FSRedAgentWreckerQ32` | -5.8 | 54/100 | 0.48 |
| `k_kft_Wrecker_s1002_final_w_O1_g32` | Wrecker-trained | Wrecker | -674.79 | `wo_O1_g32` (shipped + O1) | -11.4 | 52/100 | 0.69 |
| `k_kft_FiniteStateRedAgent_s1002_500_s_none` | stock-trained, 500 ep | stock | -237.58 | `corpus_v1` | -50.3 | 36/100 | 0.007 |
| `k_kft_FiniteStateRedAgent_s1002_1000_s_none` | stock-trained, 1000 ep | stock | -339.27 | `corpus_v1` | -151.9 | 12/100 | 0.000 |
| `k_kft_FiniteStateRedAgent_s1002_1500_s_none` | stock-trained, 1500 ep | stock | -276.49 | `corpus_v1` | -89.2 | 32/100 | 0.000 |
| `k_kft_FiniteStateRedAgent_s1002_final_s_none` | stock-trained | stock | -233.70 | `corpus_v1` | -46.4 | 35/100 | 0.004 |
| `k_kft_FiniteStateRedAgent_s1002_final_w_none` | stock-trained | Wrecker | -1328.62 | `red_FSRedAgentWrecker` | -213.0 | 36/100 | 0.007 |
| `k_kft_FiniteStateRedAgent_s1002_final_WreckerQ32_none` | stock-trained | Q32 | -879.54 | `red_FSRedAgentWreckerQ32` | -106.5 | 47/100 | 0.62 |
| `k_kft_WreckerQ32_s1002_500_WreckerQ32_none` | Q32-trained, 500 ep | Q32 | -761.16 | `red_FSRedAgentWreckerQ32` | +11.9 | 54/100 | 0.48 |
| `k_kft_WreckerQ32_s1002_1000_WreckerQ32_none` | Q32-trained, 1000 ep | Q32 | -860.46 | `red_FSRedAgentWreckerQ32` | -87.4 | 43/100 | 0.19 |
| `k_kft_WreckerQ32_s1002_1500_WreckerQ32_none` | Q32-trained, 1500 ep | Q32 | -917.41 | `red_FSRedAgentWreckerQ32` | -144.3 | 33/100 | 0.001 |
| `k_kft_WreckerQ32_s1002_final_WreckerQ32_none` | Q32-trained | Q32 | -892.35 | `red_FSRedAgentWreckerQ32` | -119.3 | 40/100 | 0.057 |
| `k_kft_WreckerQ32_s1002_final_w_none` | Q32-trained | Wrecker | -1230.90 | `red_FSRedAgentWrecker` | -115.2 | 37/100 | 0.012 |
| `k_kft_WreckerQ32_s1002_{500,1000,1500,final}_s_none` | Q32-trained | stock | -263.15, -254.85, -312.81, -338.82 | `corpus_v1` | -75.8, -67.5, -125.5, -151.5 | 23, 26, 12, 10 /100 | all 0.000 |

The 10,000-episode run, every kept checkpoint under Wrecker
(`k_kft_Wrecker_s1000_long_<N>_w_none`, paired against
`red_FSRedAgentWrecker`), then its final under stock and O1:

| Episodes | 500 | 1000 | 1500 | 2000 | 2500 | 3000 | 3500 | 4000 | 4500 | 5000 |
|---|---|---|---|---|---|---|---|---|---|---|
| Delta | -81.5 | -131.4 | -87.6 | -455.5 | -277.8 | -239.8 | -107.3 | -249.5 | +30.5 | +150.7 |
| Wins | 40 | 43 | 39 | 15 | 29 | 24 | 42 | 29 | 52 | 69 |

| Episodes | 5500 | 6000 | 6500 | 7000 | 7500 | 8000 | 8500 | 9000 | 9500 | final |
|---|---|---|---|---|---|---|---|---|---|---|
| Delta | -103.4 | -119.5 | -138.8 | -248.0 | -334.4 | -286.1 | -237.8 | -72.2 | -191.4 | -213.3 |
| Wins | 40 | 42 | 35 | 28 | 24 | 28 | 31 | 44 | 38 | 34 |

Mean delta over the twenty checkpoints -170, median -165; two positive,
seventeen below the band. `k_kft_Wrecker_s1000_long_final_s_none` -310.75
(-123.4 against `corpus_v1`, 11/100); `k_kft_Wrecker_s1000_long_final_w_O1_g32`
-713.67 (+615.3 over its own control, -50.3 against `wo_O1_g32`, 38/100,
p 0.021; 54.1 restores per episode).

Learning rate 0.1x (`k_kft_<tag>_lr01_...`), same pairings:

| Directory | Weights | Adversary | Mean | Against | Delta | Wins | Sign p |
|---|---|---|---|---|---|---|---|
| `k_kft_Wrecker_s1000_lr01_{500,1000,1500,final}_w_none` | Wrecker-trained | Wrecker | -1176.09, -1107.89, -1094.81, -1096.79 | `red_FSRedAgentWrecker` | -60.4, +7.8, +20.8, +18.9 | 39, 47, 57, 55 /100 | 0.035, 0.62, 0.19, 0.37 |
| `k_kft_Wrecker_s1000_lr01_{500,1000,1500,final}_s_none` | Wrecker-trained | stock | -180.89, -181.88, -183.08, -191.12 | `corpus_v1` | +6.4, +5.4, +4.2, -3.8 | 47, 59, 51, 51 /100 | 0.62, 0.07, 0.92, 0.84 |
| `k_kft_Wrecker_s1000_lr01_final_w_O1_g32` | Wrecker-trained | Wrecker | -638.59 | `k_kft_Wrecker_s1000_lr01_final_w_none` | +458.2 | 92/100 | 0.000 |
| | | | | `wo_O1_g32` (shipped + O1) | +24.8 | 54/100 | 0.48 |
| `k_kft_FiniteStateRedAgent_s1000_lr01_{500,1000,1500,final}_s_none` | stock-trained | stock | -195.35, -173.23, -181.28, -170.24 | `corpus_v1` | -8.0, +14.1, +6.0, +17.1 | 39, 57, 57, 66 /100 | 0.044, 0.10, 0.16, 0.001 |
| `k_kft_FiniteStateRedAgent_s1000_lr01_final_w_none` | stock-trained | Wrecker | -1168.26 | `red_FSRedAgentWrecker` | -52.6 | 50/100 | 1.000 |

Every cell inside its band. The stock control's final, +17.1 at 66/100,
sits on the band's edge on both measures.

Executed restores under O1 on the retrained policies: 53.7 (seed 1000),
55.2 (seed 1001), 52.1 (seed 1002), 54.1 (long run), 52.5 (learning rate
0.1x) per episode; shipped policy (`wo_O1_g32`) 52.3.

Supervised endpoint against unsupervised control, six KEEP policies under
Wrecker (shipped, three Wrecker-trained seeds, the long run, the 0.1x
learning rate): controls -1115.65, -1020.23, -948.46, -1086.71, -1328.96,
-1096.79; O1 gap-32 endpoints -663.38, -626.33, -657.39, -674.79, -713.67,
-638.59. Least squares `endpoint = -458 + 0.186 x control`, r 0.78,
residuals within 24. O1's gain as a fraction of each policy's own excess
loss over `corpus_v1`: 0.49, 0.47, 0.38, 0.46, 0.54, 0.50.

Reading, three seeds and the long run. Wrecker training, 2,000 episodes:
+95, +167, +29 under Wrecker (0.10, 0.18, 0.03 of the excess loss of -928;
O1 recovers 0.49), at -64, -64, -92 against the stock red; positive at
every seed, outside the band at two. The stock control never stays put:
-11 at seed 1000; -50, -4, -74 along seed 1001 (the last after a collapse
and crash); -50, -152, -89, -46 along seed 1002 (a mid-run collapse to
-398 in training units). Q32 training is -66, +93, -119 on Q32 across the
three seeds. The 10,000-episode Wrecker run is below the band at
seventeen of twenty checkpoints, -456 at its worst, +151 at its best
(5,000 episodes), -213 at the end, and -123 against the stock red. From
the shipped weights at the shipped recipe, continued training is a random
walk with a small positive drift under Wrecker at 2,000 episodes and a
negative one by 10,000, and it costs stock competence at every seed and
every checkpoint. The supervisor's endpoint moves by 0.185 of the
unsupervised policy's deficit: inside the shipped-plus-O1 band for the
four policies within 170 of shipped, -50 for the long run's policy at
-213. At a tenth of the learning rate the trainer is stable and learns
nothing: no first-update knock, no wander, no collapse, no stock-red cost
(+6, +5, +4, -4 along the Wrecker-trained run) and no Wrecker gain (-60,
+8, +21, +19, all inside the band); O1 on that policy lands at -639, on
the six-policy line. The shipped rate walks and costs; the gentle rate
sits still; neither recovers the deficit.

---

## Known issues

- **`oracle.py` segfaults above six workers** on 24-core Arrow Lake.
  `{SIGSEGV(-11)}` at `--workers 12`, stable at 6. `capture.py` runs at 24 on
  the same machine. Crashed runs leave partial directories that look complete:
  assert the expected episode count before computing anything over an arm.
- **Ownership.** Directories captured before `--user` was adopted are
  root-owned. `sudo chown -R $(id -u):$(id -g) ~/cage/data/traces`.
- **Episode id parsing.** Never `f.split('ep_')[1]` — any directory whose name
  contains `ep_` collapses all episodes to one key silently. Use
  `os.path.basename(f)[3:-6]`.
- **Budget provenance.** `oracle_O5`, `O5b` and `O5c` predate the `budget`
  header field. The `o5_b*` sweep arms record it.
- **Provenance before 2026-09-15.** Arms captured before commit `dd22fff`
  record neither harness revision, machine, nor adversary. The `o5_b*` sweep,
  `oracle_O*_n100`, all `red_*`, `wrecker_*` and `wo_*` arms are from the
  Alienware; everything earlier is from the Surface. From `dd22fff` the
  header carries `harness_sha`, `machine`, `red_agent`, `min_gap`; run
  through `bin/run` so the SHA and hostname are passed in.
- **H-MARL reference — resolved.** -131.99 is the unseeded run
  (`hmarl_expert_output`); -131.35 is the four-seed grand mean (`hmarl_s0`-`s3`);
  -124.11 is seed 0 alone, used in the Wrecker comparison because that run is
  seed 0. Cite the grand mean.
- **Attempts versus executions — resolved at `d974f69`.** Before that commit,
  footer `analyses` / `restores` (O10/O12) counted rule attempts; `wo_O10_g32`
  and `wo_O12_g32` carry attempt counts (1,726 and 1,751 per episode) and the
  executed figures are `overrides`. From `d974f69` the footer counts executed
  overrides by type.
- **Duplicate header key — resolved at `d974f69`.**
- **Token-based idempotency checks.** `tools_add_*.py` scripts that test for a
  string (e.g. `"O11"` in the source) rather than for the code they guard will
  skip silently once the token exists for another reason — this cost one
  launch on 2026-09-16. Test for the code (`rule == "O11"`).
- **Worker count not recorded before `d974f69`.** The Wrecker oracle-rule
  arms (`wo_O8`, `wo_O6`, `wo_O5`, the `wo_O2*` budget series) ran at six or
  twelve; which is not recoverable. The header carries `workers` from
  `d974f69`, and every `capture_hmarl.py` trace records it.
- **`id(cyborg)`-keyed caches — resolved.** `owned_hosts` cached the host
  list under `(id(cyborg), agent)` and `_IMPACT_SEEN` under `id(cyborg)`. A
  freed CybORG's address can be recycled by the next one a worker builds, and
  CC4 redraws host counts per episode, so a stale list could in principle
  have reached the evidence latch (O2e family, O10, O12, O13) and O7/O9; a
  `reset()` of one CybORG (`capture_hmarl --compat`) has the same exposure.
  Fixed by `tools_fix_owned_cache.py`: the cache is per agent, validated
  against the live `State` object and its host-name tuple, and the impact
  memory is cleared at step 0. `wo_O2e_b77` reproduced footer-for-footer
  under the fix (`wo_O2e_b77_r`), so no reported arm was affected.
- **Footer comparison.** Use `tools_compare_footers.py DIR_A DIR_B`: it
  compares shared keys only, reports per-key differences, and exits non-zero
  on a core-key difference or an empty intersection. An ad hoc comparison
  once reported "identical" on zero footers (wrong path), and whole-dict
  comparison flags schema growth (fields added at `d974f69`) as behaviour.
  Core keys: `total_reward`, `overrides`, `agreements`, `deferred`,
  `translator_calls`.
- **H-MARL seeding is not KEEP's.** `evaluation.py --seed` reseeds once and
  resets one CybORG per episode. `capture_hmarl.py --compat` reproduces it
  exactly; the default mode is the oracle convention (fresh CybORG per
  episode, seed = episode). Never pair a compat run against a default-mode
  arm, and never compare a compat mean with a KEEP arm as if seeds matched.
- **Latch counter names.** `oracle.py` footers name the latch confusion
  `latch_tp` / `latch_fp` / `latch_fn` / `latch_own`; `capture_hmarl.py`
  traces captured on 2026-09-18 carry them under the raw stats keys `tp` /
  `fp` / `fn` / `own` (the harness dumps every numeric stat) and later traces
  under both. `tools_investigate.py` reads either.
- **O14's first form.** Overriding the master's output after it acts leaves
  the wrapper's `high_actionmask`/`return_agent` bookkeeping in a state no
  genuine step produces, and `BlueFlatWrapper.step` calls `exit()` under
  `HITL`. Edit the gate before the master acts (mask, `high_actionmask`,
  `return_agent` together), which is also the honest definition of the rule.
- **H-MARL trainer crash.** `train_subpolicies.py` dies at random iteration
  boundaries with `ValueError: operands could not be broadcast together with
  shapes (459,) (458,)` inside a RolloutWorker (the wrapper's
  `handle_extra_ticks` off by one). It killed `ft_WreckerQ32_s1` at its
  fifth iteration and the `ft_FiniteStateRedAgent_s0` continuation twice.
  `run_ft_resume.sh` restarts from the last saved iteration, up to three
  failures.
- **A killed loop leaves no line.** `run_ft_resume.sh` writes to
  `ft_runs.log` only when its trainer exits; if the loop shell itself dies
  nothing is written and the resume silently stops (`ft_WreckerQ32_s1`
  stopped at iter_54 with no record). Launch loops under `nohup`, and never
  overwrite a script that is running: bash reads scripts incrementally, and
  the three `run_keep_ft.sh` instances overwritten on 2026-09-20 exited with
  a syntax error (`Exit 2`) once their containers were killed, before their
  log line.
- **KEEP `load()` clears the training flag.** `models/cage4.py`: `eval()`
  sets `self.training = False`, `train()` sets the module modes only, and
  `load()` ends with `eval()`. A restored agent inside `train.py` returns
  evaluation-style actions and the worker fails with `TypeError: cannot
  unpack non-iterable int object`. The shipped pipeline never restores, so
  it never saw this. `tools_patch_keep_train.py` sets `training = True` on
  restored agents.
- **KEEP seeds all training environments identically.** The shipped
  `train.py` builds every environment with `CybORG(sg, "sim", seed=seed)` in
  a loop over workers, so all 25 start from the same scenario draw and
  diverge only through blue's sampled actions. Patched to `seed+i`;
  `KEEP_SHARED_ENV_SEED=1` reproduces the shipped behaviour. Counts against
  the published training claim alongside the nine Paper 1 defects.
- **Training runs must not share the machine.** joblib caps each worker's
  BLAS threads at cores over workers per process, unaware of other
  containers. Three 8-worker KEEP runs side by side put the load average at
  90 on 24 cores with no update in ten minutes; a single run at 12 or 25
  workers is clean (5m03s and 4m25s for 50 episodes). The
  `OMP_NUM_THREADS=1` remedy was never tested cleanly: the first
  `docker kill` did not take (it printed no IDs), so the relaunch stacked
  three more runs on the first three (load 185). Verify the kill with
  `docker ps` before relaunching.
- **Curve values are not evaluation values.** RLlib's `episode_reward_mean`
  sums the ten H-MARL policy-agents (divide by ten), is a trailing window
  under training-time sampling, and resets on restore; KEEP's `Avg reward
  for episode` is a 25-episode mean under sampling on the training seeds.
  The shipped H-MARL policy reads -894 in its first Wrecker training
  iteration against -842.76 (per-episode seeding) and -863.86 (compat) in
  evaluation; `ft_Wrecker_s0/iter_99` reads -893 in training and -945.59
  in evaluation. Compare curves with curves and arms with arms.
- **`KEEP_CKPT` was not passed into the container** until 2026-09-20 18:52:
  `train.py` read it, `bin/run` did not forward it, so the three `kft_*_s1000`
  runs kept no intermediate checkpoints (the queue's three `missing` lines in
  `ft_runs.log`). Fixed in `tools_patch_keep_train.py` (`-e KEEP_CKPT`);
  `kft_*_s1001` onward keep them.
- **Evaluation script must be executable.** `run_keep_eval.sh` launched
  without `chmod +x` fails every arm with `Exit 126` and writes nothing; the
  first queue on 2026-09-20 was lost this way. `ls keep_weights/` after the
  first minute is the check: the arm's weight directory appears at once.
- **KEEP evaluation time.** `oracle.py --rule none`, 100 episodes, six
  workers: 4.7 minutes an arm on the Alienware (nine arms, 17:43 to 18:21 on
  2026-09-20), not the hour recorded in RESULTS.md under "Harness" for the
  H-MARL comparison. Evaluation is cheap; training is the budget.
- **KEEP trainer worker termination and late collapse.**
  `kft_FiniteStateRedAgent_s1001` died at update 77 of 80 with
  `joblib.externals.loky.process_executor.TerminatedWorkerError` (a worker
  segfault or an OOM kill; the log does not say which), after its curve fell
  from -216 (updates 61-68) to -259 (69-76). The rolling checkpoint is from
  after the fall and evaluates at -261 under stock and -1467 under Wrecker;
  the 1500-episode kept checkpoint (update 60) is inside both bands. Use the
  kept checkpoints, not `final`, for that run. Whether the collapse caused
  the crash or preceded it by coincidence is not recoverable from the log.
- **KEEP training is not reproducible from its seed.** `kft_Wrecker_s1000`
  and `kft_Wrecker_s1000_long` share `KEEP_SEED`, adversary, workers and
  every other setting except `KEEP_EPISODES`, and their curves differ from
  the first 500 episodes (first-quarter means -1130 and -1159, then -1055
  against -1231). `KEEP_SEED` seeds torch in the parent and CybORG per
  environment; the joblib workers sample actions from their own torch
  generators, which the trainer never seeds, and the order in which
  episodes return sets the batch. Report KEEP continuations as draws, not
  as reproducible runs, and count this beside the shared-seed defect for
  Paper 1.
