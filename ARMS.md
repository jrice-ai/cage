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
by `KEEP_WEIGHTS` (see "Retrained defenders"). From 2026-09-26 (rule
defenders) the step record carries `defender` as `[[agent, reason, host],
...]` (the rule's own decisions that step, empty for policy arms) and the
footer `defender_restores/analyses/decoys/sleeps/removes/blocks/allows/
flags_new/alerts/tp/fp/fn`; a `--rule` of the form `R2+O1` runs the rule
defender under the supervisor, and the header's `rule` field keeps the
full form.

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
| `hmarl_metrics_s0` | seed 0, authors' `evaluation_metrics.py` 2026-10-12 (same trajectory as `hmarl_s0`; recovery precision by their counter 75.4 percent, log at `data/hmarl_metrics/evaluation_metrics_s0.log`) | FiniteStateRedAgent | -124.11 | 45.80 |
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
| `O2f`, `O2fr`, `O2fw` | O2e, O2er, O2ew with the reset listing (the agent's first observation, `t == 1`) and the echo of the agent's own executed action the step before excluded, unless the entry carries a confirmed file. Added 2026-09-26 (`tools_add_O2f.py`); the originals keep their behaviour for provenance |

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
| `o2f_b77` | O2f, budget 77 (corrected latch) | 100 | -262.71 | | 77.0 |
| `oracle_O8` | O8 | 100 | -253.27 | 197.27 | 154.0 |
| `oracle_O7` | O7 | 100 | -511.95 | 165.48 | |
| `oracle_O1_n100` | O1 | 100 | -520.29 | 93.43 | 401.8 |
| `oracle_O1_n100x` | O1, rerun 2026-10-12 with the intervention record; reproduces `oracle_O1_n100` on all 100 footers; 0.650 of executed Restores are O1's own | 100 | -520.29 | 93.43 | 401.8 |
| `oracle_O1_n100t` | O1, recapture 2026-10-19 with `--log-truth` (the post-step red-host set in the step record); reproduces `oracle_O1_n100x` on all 100 footers; Restore precision 65.24% on KEEP's basis (red session at t-1, `recompute_criteria.py`), within a quarter of a point of the rule's own share | 100 | -520.29 | 93.43 | 401.8 |
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
| `wrecker_null_9002` | KEEP sampled | 9002 | none | | -1124.73 | 316.14 | 0 | 2026-10-12 |
| `wrecker_null_9003` | KEEP sampled | 9003 | none | | -1159.41 | 347.01 | 0 | 2026-10-12 |
| `wrecker_null_9004` | KEEP sampled | 9004 | none | | -1157.75 | 361.52 | 0 | 2026-10-12 |
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
| `wo_O2f_b77` | KEEP sampled | unset | O2f | 77 | -1080.73 | | 77.0 | 80.5 |
| `wo_O2fr_b77` | KEEP sampled | unset | O2fr | 77 | -1104.42 | | 77.0 | 80.8 |
| `wo_O2fw_b77` | KEEP sampled | unset | O2fw | 77 | -1104.42 | | 77.0 | 51.1 |
| `wo_O2f_bmax` | KEEP sampled | unset | O2f | 100000 | -1158.58 | | 292.4 | 7.8 |
| `wo_O2f_g32` | KEEP sampled | unset | O2f, gap 32 | 99999 | -1127.15 | | 63.6 | 10.0 |
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
| `red_FSRedAgentWreckerQ32_null9001` | | Q32, policy_seed 9001, 2026-10-12 | -743.65 | | +29.4 vs control | 52/100 |
| `red_FSRedAgentWreckerQ04_null9000` | | Q04, policy_seed 9000 | -314.55 | | +10.6 vs control | 53/100 |
| `red_FSRedAgentWreckerQ16_null9000` | | Q16, policy_seed 9000 | -559.98 | | -20.8 vs control | 49/100 |
| `red_FSRedAgentWreckerQ48_null9000` | | Q48, policy_seed 9000 | -961.80 | | -33.6 vs control | 37/100, p 0.012 |
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
| `hm_wo_O2f_g32` | FSRedAgentWrecker | O2f | ep | -1007.49 | | -164.7 | 31/100 | <0.001 | 71.6 restores | 9.6 |
| `hm_s_none` | FiniteStateRedAgent | none | ep | -136.43 | 49.60 | control | | | 0 | |
| `hm_s_none_p9000` | FiniteStateRedAgent | none | 9000+ep | -136.36 | 48.56 | +0.1 | 51/100 | 0.92 | 0 | |
| `hm_s_none_p9001` | FiniteStateRedAgent | none | 9001+ep | -136.76 | 52.55 | -0.3 | 46/100 | 0.547 | 0 | rerun 2026-10-12, the first run died in a worker |
| `hm_s_none_p9002` | FiniteStateRedAgent | none | 9002+ep | -134.60 | | +1.8 | 53/100 | 0.547 | 0 | |
| `hm_s_none_p9003` | FiniteStateRedAgent | none | 9003+ep | -130.04 | 50.55 | +6.4 | 52/100 | 0.688 | 0 | row added 2026-10-14 from the footers |
| `hm_s_none_p9004` | FiniteStateRedAgent | none | 9004+ep | -137.63 | 54.58 | -1.2 | 51/100 | 0.920 | 0 | row added 2026-10-14 from the footers |
| `hm_so_O1_g32` | FiniteStateRedAgent | O1 | ep | -160.69 | 38.29 | -24.3 | 22/100 | 1.6e-08 | 53.1 restores | 0.0 |
| `hm_so_O1_g32_wb` | FiniteStateRedAgent | O1 gap 32, held, 2026-10-12 | ep | -133.09 | | +3.3 | 43/100 | 0.228 | 45.8 restores | 0.0 |
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
| `hm_wo_O2f_g32` | passive, corrected | | | | 0.174 | 0.016 |
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

### Trident's heuristic reds on both defenders

The ten non-default agents of Appendix B, each with an O1 and an O10 arm at
gap 32 (budget 99999) on both defenders, paired on seeds 0-99, 2026-09-23.
H-MARL: `hm_<Name>_none_g0`, `hm_<Name>_O1_g32`, `hm_<Name>_O10_g32`
(Schema B-H). KEEP: controls are the `red_FSRedAgent<Name>` arms above
(Schema A); rules `o1_g32_FSRedAgent<Name>`, `o10_g32_FSRedAgent<Name>`
(Schema B). Excess is control minus the defender's stock control
(`hm_s_none` -136.43, `corpus_v1` -187.32); a positive excess means the
adversary leaves the defender better off than the stock red and there is
no deficit for a rule to recover, so no fraction is given. Fractions with
paired bootstrap intervals where the excess is negative.

| Red agent | H-MARL control | Excess | O1 delta | O10 delta | KEEP control | Excess | O1 delta | O10 delta |
|---|---|---|---|---|---|---|---|---|
| TargetARestricted | -50.0 | +86.4 | -30.1 | -0.6 | -98.52 | +88.8 | -12.2 | +4.4 |
| TargetAOperational | -54.5 | +81.9 | -29.1 | +2.0 | -99.89 | +87.4 | -24.8 | -3.5 |
| TargetA | -51.9 | +84.5 | -26.4 | +2.9 | -104.18 | +83.1 | -19.3 | +5.8 |
| TargetB | -72.7 | +63.7 | -23.8 | +6.6 | -116.25 | +71.1 | -17.9 | +2.3 |
| TargetBRestricted | -71.5 | +64.9 | -23.4 | +8.1 | -117.93 | +69.4 | -17.0 | -0.4 |
| TargetBOperational | -78.3 | +58.1 | -24.7 | +6.4 | -127.31 | +60.0 | -8.2 | +12.2 |
| Combined | -97.3 | +39.1 | -25.8 | -2.1 | -165.87 | +21.4 | -2.4 | +16.0 |
| FailureTracker | -139.2 | -2.8 | -26.1 | +9.8 | -205.66 | -18.3 | +1.0 | +12.5 |
| Impacter | -133.5 | +2.9 | +0.2 | +18.7 | -228.73 | -41.4 | +69.3 | +26.5 |
| Degrader | -192.1 | -55.7 | +1.2 | +14.1 | -268.80 | -81.5 | +58.3 | -1.9 |

Fractions where a deficit exists: KEEP Degrader O1 0.715 [0.505, 0.917],
O10 -0.023 [-0.542, 0.353]; KEEP Impacter O1 1.673 [1.188, 3.539] (O1
takes KEEP above its stock-red score), O10 0.640 [-0.629, 1.484]; H-MARL
Degrader O1 0.021 [-0.816, 0.460], O10 0.253 [-0.359, 0.636]; FailureTracker
on either defender and Impacter on H-MARL have an excess within 20 of zero
and no usable fraction. The three original H-MARL arms for
TargetARestricted and the KEEP O1 arm failed or were killed on the first
launch (Known issues) and were rerun; the reported arms are the reruns.

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

`k_kft_Wrecker_s1000_lr01_final_w_O10_g32`: O10 at gap 32 on the
0.1x-learning-rate policy, -975.61, +121.2 over its control (60/100, p
0.057), 59.7 analyses and 9.2 agreements per episode; the shipped policy's
O10 (`wo_O10_g32`) is +127.4 from -1115.65. Fractions 0.133 and 0.137.

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

## Rule defenders

A third defender that was never trained: a hand-written blue policy inside
the oracle harness, so that every arm, tool and pairing built for KEEP
applies to it unchanged. `tools_add_R1.py` (idempotent, tests for the code
it inserts, upgrades an earlier installed block) adds `make_defender` to
`scripts/oracle_rules.py` and restructures `make_oracle`'s intercept: with
a defender rule, the defender's proposal replaces the policy's action
before the supervisor rule sees it, the supervisor may override it as it
would KEEP's, and whatever executes is fed back to the defender's memory
(`note`), so a supervisor's Restore clears the rule's flags for that host.
A `--rule` of `R2` runs the defender alone, `R2+O1` under a supervisor;
unknown rule names now raise `ValueError` instead of passing through as
`none`. `run_rd.sh <kind> <red> [sup] [gap] [budget]` runs one arm through
`bin/run cage-keep:dev`, 100 episodes at six workers, into
`data/traces/rd_<kind>_<w|s|red>_<sup>[_g<gap>]`. Diagnostics that shaped
the rules: `tools_diag_eyes.py` (what the observation supports, one
episode) and `tools_diag_posture.py` (KEEP's block/allow/decoy posture,
five episodes).

Gates. The O2e smoke reproduced after each of the three patch versions
(`o2e_smoke_r1`, `o2e_smoke_r4`, `o2e_smoke_r41`: -327.00, 87.68, 77.0 /
108.5) and after `tools_add_O2f.py` (`o2e_smoke_f`), the H-MARL compat
gate after the first and the last (`hm_compat_gate3r`, `hm_compat_gate3f`,
-902.67, sd 420.22). Determinism: `rd_R4_w_none` and `rerun_rd_R4_w_none`
are identical on every core key over all 100 footers.

### Definitions

An alert is a substantive observation entry naming an owned host, with
two exclusions: the reset listing at step 0, which names every owned host
(see Known issues, the O2e latch), and the echo of the rule's own action
the step before, unless it carries a confirmed file. A confirmed file is
an Analyse result with `Density >= 0.9`. Alerts are counted per host
since its last Restore. Windows: no Restore of the same host within 30
steps (O8's window), no Remove within 10, no Analyse within 10, and one
Remove per alert. Restore and Remove targets are ordered by confirmed
file first, then `_host_score` (the zone's phase penalty, servers
doubled, divided by decoy load), then alert count and recency.

| Kind | Restore on | Else, in order | Notes |
|---|---|---|---|
| `R1` | confirmed file | Analyse an alerted host not looked at in 10 steps and alerted since | forensic-only |
| `R2` | second alert or confirmed file | Analyse once-alerted hosts | the ladder |
| `R2d` | as R2 | as R2, then a decoy on an owned server without one | |
| `R3` | first alert or confirmed file | sleep | contain on any alert |
| `R4` | second alert or confirmed file | block a disallowed inbound zone pair for this phase (one per step) or re-allow one; Remove a once-alerted host; a decoy on the least-decoyed owned host up to three | the analyst playbook |
| `R4p` | never | posture only | ablation |
| `R4t` | second alert or confirmed file | posture; Analyse a once-alerted host (as R2); a decoy on the least-decoyed owned host up to three | R4 with triage in place of Remove (ablation, `tools_add_R4t.py`, 2026-09-26) |
| `R4t3` | third alert or confirmed file | as R4t | R4t with one more alert before a Restore (`tools_add_R4t3.py`) |
| `R4tn` | second alert or confirmed file | as R4t without posture (no blocks) | R4t minus posture (`tools_add_R4tn.py`) |
| `R4d` | never | posture, then decoys | ablation |
| `RT` | any ground-truth-compromised owned host | sleep | perfect eyes, the same hands |

The comms policy for `R4` is written from
`EnterpriseScenarioGenerator._set_allowed_subnets_per_mission_phase`: HQ
to contractor, restricted A and restricted B in every phase; phase 0 adds
(RA, C), (OA, RA), (RB, C), (RB, RA), (OB, RB); phase 1 adds (RB, C),
(OB, RB); phase 2 adds (RA, C), (OA, RA). Pairs are symmetric. The
simulator enforces none of it on the network (`_update_agents_allowed_subnets`
only redirects the greens), which is why posture cannot matter: red uses
allowed routes.

### Pilots

Three episodes each (seeds 0-2, `OUTPREFIX=pilot_`), Wrecker and stock,
in the order they were run. Means only.

| Kind | Wrecker | stock | What it showed |
|---|---|---|---|
| `R1` | -3105 | -710 | the strict criterion fires about eight times an episode |
| `R2` | -3141 | -874 | |
| `R3` | -3302 | -1042 | |
| `R2d` | -3000 | -1132 | |
| `R4` (v3) | -3777.67 | -1380.33 | 1,424 and 1,314 Removes in three episodes: alerts were cleared on Remove and re-fired every 10 steps |
| `R4p` | -5779.67 | -6387.00 | posture alone is the do-nothing floor |
| `R4d` | -4696.67 | -6745.33 | decoys alone are the floor |
| `R4` (v3.1) | -2990.00 | -1669.33 | 147 and 181 Removes against 311 and 471 alerts |

The v3.1 pilot footers under Wrecker and stock: restores 129 / 185,
decoys 579 / 731, flagged-set tp 50 / 111, fp 88 / 94, fn 11,484 / 10,549
(compromised host-steps not flagged). The flagged set is precise enough;
it covers almost nothing.

### What the observation supports

`tools_diag_eyes.py`, twenty episodes each (seeds 0-19, counts summed;
`queue_A.sh`, 2026-09-26), the reset listing excluded. "Passive" is a
substantive observation entry naming an owned host; unlike the defender's
alert it does not exclude the echo of the agent's own action, so KEEP's
own Analyses count as namings here. Precision is the share of namings
that name a compromised host; the base rate is the compromised share of
owned host-steps (71 hosts, 499 steps); coverage is the share of
compromised host-steps on which the host had been named at least k times
since its last Restore or Remove. Under KEEP compromise is kept near a
fifth of owned host-steps; under R1 it accumulates to a third, which
raises every precision figure.

| Acting policy | Adversary | Namings | Precision | Base rate | by count 1 / 2 / 3 / 4 / 5+ | Coverage >=1 / >=2 / >=3 | Analyses | Confirmed files, compromised / clean |
|---|---|---|---|---|---|---|---|---|
| KEEP | Wrecker | 7,618 | 0.257 | 0.207 | 0.21 / 0.26 / 0.32 / 0.32 / 0.30 | 0.61 / 0.33 / 0.18 | KEEP's own | 173 / 5 |
| KEEP | stock | 7,886 | 0.264 | 0.220 | 0.18 / 0.26 / 0.32 / 0.35 / 0.39 | 0.64 / 0.38 / 0.23 | KEEP's own | 158 / 29 |
| R1 | Wrecker | 4,350 | 0.395 | 0.294 | 0.25 / 0.43 / 0.51 / 0.52 / 0.47 | 0.70 / 0.38 / 0.17 | 3,960 | 333 / 0 |
| R1 | stock | 6,002 | 0.497 | 0.340 | 0.26 / 0.53 / 0.64 / 0.68 / 0.68 | 0.86 / 0.54 / 0.27 | 5,172 | 698 / 0 |

As KEEP operates the network the stream is 1.2x chance under both reds
and the count of namings lifts it to 0.3 or 0.4 at best; the two reds
look alike, which is what the corrected O2f latch (1.4x under both) also
says. Under a defender that evicts almost nothing the stream is more
informative and the reds separate: repeated namings reach 0.68 under
stock and 0.5 under Wrecker, and a look at an alerted host confirms a
file one time in 7.4 under stock (698 of 5,172) and one time in 12 under
Wrecker (333 of 3,960). A confirmed file under R1 is always on a
compromised host (1,031 of 1,031); under KEEP 29 of 187 confirmed files
under stock and 5 of 178 under Wrecker sit on hosts with no live red
session, hosts red has been removed from but not restored. The
single-episode runs of the morning (precision 0.18 to 0.57, a look
confirming one time in thirty under Wrecker) are superseded by these.

### Arms

100 episodes, seeds 0-99, six workers, all from the Alienware on
2026-09-26. Controls (`rd_<kind>_<a>_none`):

| Kind | stock mean | sd | Wrecker mean | sd |
|---|---|---|---|---|
| `R1` | -994.58 | 505.05 | -3294.39 | 483.79 |
| `R2` | -886.41 | 456.75 | -3158.98 | 544.84 |
| `R2d` | -772.75 | 413.67 | -3147.38 | 577.35 |
| `R3` | -989.54 | 514.06 | -3341.76 | 718.95 |
| `R4` | -1294.34 | 582.75 | -3564.25 | 726.18 |
| `R4t` | -954.63 | 477.40 | -2763.38 | 633.39 |
| `R4t3` | | | -2956.92 | |
| `R4tn` | | | -2766.20 | |
| `R4p` | -6507.40 | 1315.60 | -5263.93 | 871.89 |
| `R4d` | -6011.80 | 1376.12 | -4993.63 | 682.58 |
| `RT` | -168.60 | 36.29 | -348.90 | 76.33 |

For reference: `arm_sleep` (do nothing, stock) -6592.68; KEEP shipped
-187.32 / -1115.65; H-MARL Expert -136.43 / -842.76.

Supervisors, paired against the same kind's control under the same red:

| Directory | Rule | Red | Mean | Delta | Wins | Sign p | Executed/ep |
|---|---|---|---|---|---|---|---|
| `rd_R2_w_O1_g32` | R2 + O1 gap 32 | Wrecker | -949.63 | +2209.3 | 100/100 | <1e-3 | 55.9 restores |
| `rd_R2_s_O1_g32` | | stock | -264.65 | +621.8 | 98/100 | <1e-3 | 57.0 |
| `rd_R4_w_O1_g32` | R4 + O1 gap 32 | Wrecker | -1581.07 | +1983.2 | 98/100 | <1e-3 | 59.4 |
| `rd_R4_s_O1_g32` | | stock | -626.56 | +667.8 | 88/100 | <1e-3 | 62.3 |
| `rd_R1_w_O1_g32` | R1 + O1 gap 32 | Wrecker | -915.58 | +2378.8 | 100/100 | <1e-3 | 56.7 |
| `rd_R1_s_O1_g32` | | stock | -299.90 | +694.7 | 94/100 | <1e-3 | 59.3 |
| `rd_RT_w_O1_g32` | RT + O1 gap 32 | Wrecker | -343.75 | +5.2 | 50/100 | 1.0 | 43.1 |
| `rd_R4t_w_O1_g32` | R4t + O1 gap 32 | Wrecker | -1256.04 | +1507.3 | 92/100 | <1e-3 | 59.2 |
| `rd_R4t3_w_O1_g32` | R4t3 + O1 gap 32 | Wrecker | -1264.91 | +1692.0 | | | 59.0 |
| `rd_R4tn_w_O1_g32` | R4tn + O1 gap 32 | Wrecker | -1193.23 | +1573.0 | | | 58.9 |
| `rd_R2_w_O10_g32` | R2 + O10 gap 32 | Wrecker | -1906.84 | +1252.1 | 94/100 | <1e-3 | 65.7 analyses, 13.3 agreements |
| `rd_R2_s_O10_g32` | | stock | -436.41 | +450.0 | 85/100 | <1e-3 | 69.1, 19.4 |
| `rd_R4_w_O10_g32` | R4 + O10 gap 32 | Wrecker | -2330.17 | +1234.1 | 91/100 | <1e-3 | 67.2, 7.9 |
| `rd_R4_s_O10_g32` | | stock | -882.75 | +411.6 | 72/100 | <1e-3 | 69.2, 10.2 |

The targeting axis on R4 (`rd_R4_<Q>_none`, `rd_R4_<Q>_O1_g32`; Q64 is
Wrecker) and R2 (`rd_R2_<Q>_none`, `rd_R2_<Q>_O1_g32`; Q04, Q16 and Q48
from `queue_A.sh`, 2026-09-26):

| Kind | Red | Control | O1 gap 32 | Delta | Excess over own stock | Fraction | 95% CI |
|---|---|---|---|---|---|---|---|
| `R4` | Q04 | -1173.1 | -697.8 | +475.3 | +121.2 | n/a (no deficit) | |
| `R4` | Q16 | -2239.6 | -1133.6 | +1106.0 | -945.3 | 1.170 | [1.017, 1.375] |
| `R4` | Q32 | -2954.6 | -1370.1 | +1584.5 | -1660.3 | 0.954 | [0.874, 1.044] |
| `R4` | Q48 | -3303.6 | -1526.5 | +1777.1 | -2009.3 | 0.884 | [0.807, 0.970] |
| `R4` | Q64 | -3564.25 | -1581.07 | +1983.2 | -2269.9 | 0.874 | [0.806, 0.948] |
| `R2` | Q04 | -798.9 | -286.0 | +512.9 | +87.5 | n/a (no deficit) | |
| `R2` | Q16 | -1801.3 | -549.6 | +1251.7 | -914.9 | 1.368 | [1.236, 1.543] |
| `R2` | Q32 | -2446.5 | -729.8 | +1716.7 | -1560.1 | 1.100 | [1.029, 1.187] |
| `R2` | Q48 | -2774.9 | -802.9 | +1972.0 | -1888.5 | 1.044 | [0.983, 1.110] |
| `R2` | Q64 | -3158.98 | -949.63 | +2209.3 | -2272.6 | 0.972 | [0.923, 1.026] |
| `R4t` | Q64 | -2763.38 | -1256.04 | +1507.3 | -1808.8 | 0.833 | [0.762, 0.904] |
| `R1` | Q64 | -3294.39 | -915.58 | +2378.8 | -2299.8 | 1.034 | [0.981, 1.092] |

(Controls and endpoints at Q04 to Q48 are recovered from the fraction
tool's excess and delta over the stock control; the directories carry the
exact figures.) KEEP on the same axis (`o1_g32_FSRedAgentWreckerQ*`):
0.541, 0.463, 0.448, 0.471, 0.487.

O10 fractions under Wrecker: R2 0.551 [0.491, 0.610], R4 0.544 [0.479,
0.609]; KEEP 0.137, H-MARL 0.14.

### RT ceilings across adversaries

`queue_A.sh`, 2026-09-26: RT (Restore any ground-truth-compromised owned
host, else sleep) under every adversary KEEP has been run on, 100
episodes, seeds 0-99 (`rd_RT_<red>_none`). With the two of the afternoon:

| Adversary | RT mean | sd | KEEP control | KEEP's gap to RT |
|---|---|---|---|---|
| stock | -168.60 | 36.29 | -187.32 | 18.7 |
| Q04 | -174.34 | 61.31 | -325.11 | 150.8 |
| Q16 | -216.63 | 54.10 | -539.17 | 322.5 |
| Q32 | -262.18 | 65.22 | -773.08 | 510.9 |
| Q48 | -312.34 | 69.12 | -928.16 | 615.8 |
| Q64 (Wrecker) | -348.90 | 76.33 | -1115.65 | 766.8 |
| ConvOnly | -201.74 | 46.95 | -316.62 | 114.9 |
| TargetARestricted | -85.18 | 58.99 | -98.52 | 13.3 |
| TargetAOperational | -82.59 | 61.94 | -99.89 | 17.3 |
| TargetA | -80.38 | 60.09 | -104.18 | 23.8 |
| TargetB | -109.24 | 62.10 | -116.25 | 7.0 |
| TargetBRestricted | -109.51 | 60.64 | -117.93 | 8.4 |
| TargetBOperational | -117.03 | 71.22 | -127.31 | 10.3 |
| Combined | -129.04 | 25.73 | -165.87 | 36.8 |
| FailureTracker | -170.18 | 44.47 | -205.66 | 35.5 |
| Impacter | -118.22 | 120.35 | -228.73 | 110.5 |
| Degrader | -145.90 | 30.36 | -268.80 | 122.9 |

### Distance to the ceiling closed

`tools_ceiling.py CEILING CONTROL ARM`: closed = (arm - control) /
(ceiling - control), paired bootstrap interval, seed 0, 10,000 resamples.
The ceiling is RT under the same adversary. Unlike the fraction of
excess loss it is defined whenever the policy is below RT, and it does
not exceed 1 unless the arm beats perfect eyes.

KEEP, O1 at gap 32 (`o1_g32_FSRedAgent<red>`, `wo_O1_g32`; stock is O2
at gap 32, `o2_g32`, which is O1's twin at this cadence):

| Adversary | Gap | O1 delta | Closed | 95% CI | O10 delta | O10 closed |
|---|---|---|---|---|---|---|
| stock | 18.7 | -16.1 | -0.86 | | | |
| Q04 | 150.8 | +74.5 | 0.494 | [0.360, 0.607] | | |
| Q16 | 322.5 | +163.0 | 0.505 | [0.413, 0.583] | | |
| Q32 | 510.9 | +262.3 | 0.513 | [0.444, 0.575] | | |
| Q48 | 615.8 | +348.7 | 0.566 | [0.504, 0.621] | | |
| Q64 | 766.8 | +452.3 | 0.590 | [0.533, 0.643] | +127.3 | 0.166 [0.073, 0.251]; O13 +155.1, 0.202 [0.119, 0.277] |
| ConvOnly | 114.9 | +48.4 | 0.422 | [0.193, 0.587] | | |
| TargetARestricted | 13.3 | -12.2 | -0.92 | [-4.60, -0.23] | +4.4 | 0.33 [-0.32, 1.09] |
| TargetAOperational | 17.3 | -24.8 | -1.43 | [-5.68, -0.56] | -3.5 | -0.20 |
| TargetA | 23.8 | -19.3 | -0.81 | [-1.87, -0.32] | +5.8 | 0.24 [-0.13, 0.57] |
| TargetB | 7.0 | -17.9 | -2.55 | [-29.5, -0.52] | +2.3 | 0.33 |
| TargetBRestricted | 8.4 | -17.0 | -2.02 | [-26.7, -0.32] | -0.4 | -0.05 |
| TargetBOperational | 10.3 | -8.2 | -0.80 | [-13.7, 0.35] | +12.2 | 1.18 [-0.08, 8.19] |
| Combined | 36.8 | -2.4 | -0.07 | [-0.82, 0.30] | +16.0 | 0.44 [-0.07, 0.71] |
| FailureTracker | 35.5 | +1.0 | 0.03 | [-0.74, 0.38] | +12.5 | 0.35 [-0.34, 0.73] |
| Impacter | 110.5 | +69.3 | 0.627 | [0.454, 0.863] | +26.5 | 0.24 [-0.17, 0.55] |
| Degrader | 122.9 | +58.3 | 0.474 | [0.322, 0.593] | -1.9 | -0.02 [-0.34, 0.24] |

Rule defenders, O1 at gap 32 unless stated:

| Defender | Adversary | Gap | Delta | Closed | 95% CI |
|---|---|---|---|---|---|
| R2 | stock | 717.8 | +621.8 | 0.866 | [0.829, 0.896] |
| R2 | Q04 | 624.5 | +512.9 | 0.821 | [0.785, 0.854] |
| R2 | Q16 | 1,584.7 | +1,251.7 | 0.790 | [0.754, 0.822] |
| R2 | Q32 | 2,184.3 | +1,716.7 | 0.786 | [0.758, 0.813] |
| R2 | Q48 | 2,462.5 | +1,972.0 | 0.801 | [0.771, 0.827] |
| R2 | Q64 | 2,810.1 | +2,209.3 | 0.786 | [0.757, 0.813] |
| R2, O10 | Q64 | 2,810.1 | +1,252.1 | 0.446 | [0.399, 0.489] |
| R4 | Q04 | 998.8 | +475.3 | 0.476 | [0.388, 0.557] |
| R4 | Q16 | 2,023.0 | +1,106.0 | 0.547 | [0.500, 0.589] |
| R4 | Q32 | 2,692.5 | +1,584.5 | 0.589 | [0.545, 0.630] |
| R4 | Q48 | 2,991.3 | +1,777.1 | 0.594 | [0.555, 0.632] |
| R4 | Q64 | 3,215.4 | +1,983.2 | 0.617 | |
| R4t | Q64 | 2,414.5 | +1,507.3 | 0.624 | [0.573, 0.670] |

H-MARL Expert (`read_hm_ceiling.sh`, 2026-09-26; controls `hm_<red>_none_g0`,
`hm_s_none`, `hm_w_none`; arms at gap 32). Where the control is above RT
the gap is negative and no share is given; the delta is still reported.

| Adversary | H-MARL control | Gap to RT | O1 delta | O1 closed | 95% CI | O10 delta | O10 closed | 95% CI |
|---|---|---|---|---|---|---|---|---|
| stock | -136.43 | -32.2 | -24.3 | above RT | | +7.2 | above RT | |
| Q04 | -239.10 | 64.8 | +8.9 | 0.138 | [-0.258, 0.405] | +33.2 | 0.512 | [0.242, 0.727] |
| Q16 | -440.29 | 223.6 | +72.9 | 0.326 | [0.192, 0.439] | +60.5 | 0.270 | [0.131, 0.395] |
| Q32 | -585.79 | 323.6 | +138.9 | 0.429 | [0.326, 0.523] | +74.2 | 0.229 | [0.086, 0.357] |
| Q48 | -738.05 | 425.7 | +144.6 | 0.340 | [0.218, 0.446] | +102.3 | 0.240 | [0.116, 0.349] |
| Q64 (Wrecker) | -842.76 | 493.9 | +98.5 | 0.200 | [0.025, 0.346] | +100.9 | 0.204 | [0.076, 0.315] |
| ConvOnly | -232.99 | 31.2 | -10.4 | -0.334 | [-2.149, 0.292] | +15.7 | 0.502 | [-0.248, 1.018] |
| TargetARestricted | -50.0 | -35.2 | -30.1 | above RT | | -0.6 | above RT | |
| TargetAOperational | -54.5 | -28.1 | -29.1 | above RT | | +2.0 | above RT | |
| TargetA | -51.9 | -28.4 | -26.4 | above RT | | +2.9 | above RT | |
| TargetB | -72.7 | -36.5 | -23.8 | above RT | | +6.6 | above RT | |
| TargetBRestricted | -71.6 | -37.9 | -23.4 | above RT | | +8.1 | above RT | |
| TargetBOperational | -78.4 | -38.7 | -24.7 | above RT | | +6.4 | above RT | |
| Combined | -97.4 | -31.7 | -25.8 | above RT | | -2.1 | above RT | |
| FailureTracker | -139.3 | -30.9 | -26.1 | above RT | | +9.8 | above RT | |
| Impacter | -133.5 | 15.3 | +0.2 | 0.014 | [-6.2, 1.9] | +18.7 | 1.22 | [-0.09, 9.8] |
| Degrader | -192.1 | 46.2 | +1.2 | 0.025 | [-1.09, 0.53] | +14.1 | 0.305 | [-0.50, 0.72] |

Under Wrecker the rest of H-MARL's ladder: O13 +38.6, 0.078 [-0.069,
0.202]; O14 -37.5, -0.076; O2f -164.7, -0.334 [-0.533, -0.168].

The five KEEP retrains under Wrecker, O1 at gap 32 against `rd_RT_w_none`:
seed 1000 0.587 [0.530, 0.638], seed 1001 0.485 [0.398, 0.558], seed 1002
0.558 [0.492, 0.620], 10,000 episodes 0.628 [0.571, 0.678], learning rate
0.1x 0.613 [0.557, 0.663]; shipped 0.590.

RT is a reference, not a ceiling, for H-MARL under mild adversaries: it
sits 28 to 39 above RT on the eight Trident reds that leave it better off
than stock, and 32 above under the stock red itself, so restoring every
ground-truth-compromised host at once is a worse hand than H-MARL's
IoC-gated one where detection is not the binding constraint. KEEP is
below RT everywhere. Under Wrecker RT is 494 above H-MARL and 767 above
KEEP.

R2's controls along the axis (`rd_R2_<Q>_none`): Q04 -798.9, Q16
-1801.3, Q32 -2446.5, Q48 -2774.9, Q64 -3158.98; its O1 endpoints -286.0,
-549.6, -729.8, -802.9, -949.63. The fraction of excess loss on the same
arms: n/a (excess +87.5), 1.368 [1.236, 1.543], 1.100 [1.029, 1.187],
1.044 [0.983, 1.110], 0.972 [0.923, 1.026].

### Against the learned defenders, O1 at gap 32 under Wrecker

| Policy | Stock control | Wrecker control | Excess | O1 endpoint | O1 gain | Fraction | Endpoint vs `wo_O1_g32` | Six-policy fit residual | Distance to RT closed |
|---|---|---|---|---|---|---|---|---|---|
| H-MARL Expert | -136.43 | -842.76 | -706 | -744.22 | +98.5 | 0.14 (0.19 vs null centre) | -81 | -129 | 0.20 |
| KEEP shipped | -187.32 | -1115.65 | -928 | -663.38 | +452.3 | 0.49 | 0 | +2 | 0.59 |
| `R4` | -1294.34 | -3564.25 | -2270 | -1581.07 | +1983.2 | 0.87 | -917.7 (4/100) | -460 | 0.62 |
| `R4t` | -954.63 | -2763.38 | -1809 | -1256.04 | +1507.3 | 0.83 | -592.7 (7/100) | -284 | 0.62 |
| `R2` | -886.41 | -3158.98 | -2273 | -949.63 | +2209.3 | 0.97 | -286.2 (27/100) | +96 | 0.79 |
| `R1` | -994.58 | -3294.39 | -2300 | -915.58 | +2378.8 | 1.03 | -252.2 (28/100) | +155 | 0.81 |
| `RT` | -168.60 | -348.90 | -180 | -343.75 | +5.2 | 0.03 | +319.6 (98/100) | +179 | |

The six-policy fit is `endpoint = -458 + 0.186 x control` from the KEEP
retrains ("Retrained defenders"). "Distance to RT closed" is the O1 gain
over the gap between the policy's Wrecker control and `rd_RT_w_none`
(-348.90). Wrecker controls span 3,215 points from RT to R4 and the O1
endpoints 1,237; without R4, 2,945 and 606.

### The directed look, from the step records

`tools_investigate.py` on the O10 arms. Response is a Restore or Remove
of the investigated host by the investigating agent.

| Arm | Investigations/ep | Yield (files/looks) | Repeat share | Median | p90 | Within 10 | Within 50 | Never |
|---|---|---|---|---|---|---|---|---|
| `rd_R4_w_O10_g32` | 67.2 | 0.118 | 73.4% | 38 | 152 | 15.0% | 37.1% | 38.4% |
| `rd_R2_w_O10_g32` | 65.7 | 0.203 | 72.7% | 38 | 187 | 12.8% | 31.6% | 45.9% |
| `wo_O10_g32` (KEEP) | 61.2 | 0.16 (from RESULTS.md) | 66.3% | 36 | 133 | 15.3% | 49.8% | 22.4% |

A rule defender restores the step after a confirmed file by construction,
so its latency distribution is the look's outcome: the share within 10
steps is the yield, and the rest is the wait for the next passive alert.
KEEP's is the same shape with the same median. Recomputed 2026-09-26
over executed looks (an Analyse of the host by the agent within three
steps of the override; `tools_investigate.py`), measured from the tick
the look ran:

| Arm | Looks executed | Median | Within 10 | Never | Found a file | Response given a hit | Response given a miss |
|---|---|---|---|---|---|---|---|
| `wo_O10_g32` (KEEP) | 3,774 of 6,125 (61.6%) | 33 | 16.4% | 22.7% | | | |
| `wo_O13_g32` (KEEP) | 2,746 of 4,554 (60.3%) | 32 | 16.3% | 23.1% | | | |
| `rd_R2_w_O10_g32` | 5,566 of 6,573 (84.7%) | 37 | 13.5% | 45.3% | 625 (11.2%) | median 5, 98.7% within 10 | median 53, 50.9% never |
| `rd_R4_w_O10_g32` | 4,817 of 6,721 (71.7%) | 37 | 17.5% | 38.9% | 632 (13.1%) | median 5, 97.6% within 10 | median 50, 44.6% never |

A hit is the rule's own strict Restore of the host within three steps of
the look. The dropped looks' hosts were later recovered by the same
agent anyway 78% (KEEP O10), 75% (O13), 50% (R2), 63% (R4) of the time.

### Reading

The same supervisor rule is worth +98 on H-MARL, +452 on KEEP and +1,983
to +2,379 on the rule defenders, in inverse order of what the policy can
do on its own under the adversary, and it recovers a share of the excess
loss that rises from 0.14 through 0.49 to about 1 in the same order. The
share is constant across retrains of one architecture (0.38 to 0.54) and
not across architectures; it exceeds 1 on R4 at Q16 and R2 at Q16 to
Q48, where the rule's stock control is not a ceiling, so for policies far
from competent the distance to RT closed is the measure that keeps its
meaning (0.20, 0.59, 0.62, 0.79, 0.81). On that measure the targeting
axis reads cleanly where the fraction did not: O1 at gap 32 closes 0.79
to 0.82 of R2's distance to perfect eyes at every point from Q04 to Q64
and 0.87 under stock, 0.49 to 0.59 of KEEP's rising slowly with
concentration, and 0.48 to 0.62 of R4's. Under the seven Trident reds
that leave KEEP better off than stock, KEEP sits 7 to 37 points below RT
and O1 closes a negative share (-0.8 to -2.5, intervals excluding zero on
five): a supervisor with perfect information costs where the policy is
already at the ceiling, which is the stock-red result (-16 against a gap
of 19) seen seven more times. Endpoints keep the controls'
order to within swaps of neighbours (KEEP passes H-MARL, R1 passes R2,
R2 and R1 pass R4t) and compress the spread by three fifths, four fifths
without R4. RT
under Wrecker is 767 better than KEEP and 494 better than H-MARL, and
under stock within 20 of KEEP and 32 worse than H-MARL: the adversary's
whole effect is on detection. The directed look recovers 0.55 of a rule
defender's excess against 0.14 on the learned defenders, with the same
median latency as KEEP's, which locates the latency in the sensor's
yield rather than in the policy. On the playbook: posture is the floor
(`R4p`), decoys alone add about 500 to the floor and about 110 to R2
under stock and nothing under Wrecker (`R2d`), and Remove-first without
triage costs about 400 against R2 under both reds and 630 under O1. The
ablation `R4t` (Analyse in place of Remove, everything else as R4)
attributes it: paired against R4 it is +340 (70/100) under stock and
+801 (82/100) under Wrecker, which puts it 68 behind R2 under stock and
396 ahead of it under Wrecker (-2763, the best unsupervised rule
defender). So the Remove is the whole of the playbook's deficit, and the
playbook's other parts, three decoys per host on top of posture, are
worth about 400 under Wrecker once the Remove is gone and nothing under
stock (R4t against R2d: -182 stock, +384 Wrecker). With O1 on top the
order reverses: R4t + O1 is -1256 against R2 + O1's -950, fraction 0.83
against 0.97, and 592 behind KEEP + O1 at 7/100. Two more ablations
locate the reversal without explaining it. R4t3 (a third alert before a
Restore) brings R4t's own restores under O1 down from 167 to 86 per
episode, R2's count, and the gap to R2 + O1 stays at 315 (-1265,
28/100), so the ladder's use of the decoys' alerts is not the cost; alone
it gives up 194 against R4t (43/100, inside the band). R4tn (no
posture) equals R4t alone (-2.8, 50/100) and under O1 is -1193, 244
behind R2 + O1 (26/100), so posture is worth nothing in either regime
and the decoys are the cost under supervision. Footers per episode,
R4tn + O1 against R2 + O1: alerts 389 against 214, analyses 175 against
122, own restores 157 against 78, decoys 773 against 0, compromised
host-steps 5,422 against 4,932; without a supervisor the same comparison
is 8,461 against 9,242. Three decoys per host are worth +400 when the
defender is alone against Wrecker and -244 when a supervisor names the
target every 32 steps, and the network carries 8 percent fewer
compromised host-steps with them in the first case and 10 percent more
in the second. The mechanism was found the same evening and is not in
red's behaviour: deploying decoys keeps the agent busy, and a
supervisor's directive to a busy agent is dropped by the simulator (Known
issues, first entry); R4tn under O1 executed 32 ground-truth restores per
episode to R2's 41.

---

## Waiting-directive arms

From 2026-09-26 22:00 the harness runs with `--wait-busy` (`tools_add_wait.py`;
header `wait_busy`, footer `busy_skips`; `run_rd.sh` with `WAIT=1`;
directories suffixed `_wb`). Gates with the flag off: `o2e_smoke_wb0`
(-327.00, 87.68, 77.0 / 108.5) and `hm_compat_gate3wb` (-902.67, 420.22).
Pilot with the flag on: `pilot_rd_R2_w_O1_g32_wb`, three episodes, override
share 0.986, rule shares 0.93, `busy_skips` 579 per episode. `queue_B.sh`,
nineteen arms in two lanes, 21:25 to 22:13: arms took 4.5 to 6.2 minutes
each side by side against 4.6 alone, so two lanes are the default for
evaluation queues; one worker `SIGSEGV` in nineteen (`rd_R2d_w_none_wb`,
rerun in `queue_C.sh`). Execution shares (`tools_dropped.py`, 30
episodes): overrides 0.990 to 0.998 on KEEP, H-MARL and the rules; rule
proposals 0.92 to 0.96, the remainder being `replace_action_if_invalid`.
Busy shares with the flag: KEEP 0.39, H-MARL 0.54, R2 0.23, R4tn 0.41
(its decoys now execute, 427 per episode), RT 0.12.

| Directory | Policy | Red | Rule | Mean | sd | Against | Delta | Wins | Sign p | Executed/ep |
|---|---|---|---|---|---|---|---|---|---|---|
| `wo_O1_g32_wb` | KEEP | Wrecker | O1 gap 32 | -490.72 | | `red_FSRedAgentWrecker` | +624.9 | 100/100 | <1e-3 | 48.1 restores |
| | | | | | | `wo_O1_g32` | +172.7 | 79/100 | <1e-3 | |
| `wo_O10_g32_wb` | KEEP | Wrecker | O10 gap 32 | -927.30 | | control | +188.3 | 73/100 | <1e-3 | 58.6 analyses, 11.4 agreements |
| | | | | | | `wo_O10_g32` | +61.0 | 61/100 | 0.035 | |
| `wo_O13_g32_wb` | KEEP | Wrecker | O13 gap 32 | -949.10 | | control | +166.6 | 69/100 | <1e-3 | 40.8, 11.0 |
| `o2_g32_wb` | KEEP | stock | O2 gap 32 | -175.11 | | `corpus_v1` | +12.2 | 61/100 | 0.027 | 47.2, 23.0 |
| `o10_g32_wb` | KEEP | stock | O10 gap 32 | -184.97 | | `corpus_v1` | +2.4 | 56/100 | 0.23 | 59.0, 9.0 |
| `hm_wo_O1_g32_wb` | H-MARL | Wrecker | O1 gap 32 | -427.96 | | `hm_w_none` | +414.8 | 92/100 | <1e-3 | 46.4 restores; 133.2 Recover steps |
| `hm_wo_O10_g32_wb` | H-MARL | Wrecker | O10 gap 32 | -756.18 | | `hm_w_none` | +86.6 | 60/100 | 0.057 | 57.3, 12.3 |
| `rd_R2_w_none_wb` | R2 | Wrecker | none | -1851.15 | 618.45 | `rd_R2_w_none` | +1307.8 | 96/100 | <1e-3 | |
| `rd_RT_w_none_wb` | RT | Wrecker | none | -274.88 | 34.58 | `rd_RT_w_none` | +74.0 | 90/100 | <1e-3 | |
| `rd_R4tn_w_none_wb` | R4tn | Wrecker | none | -2267.33 | 619.16 | `rd_R4tn_w_none` | +498.9 | 71/100 | <1e-3 | |
| `rd_R2d_w_none_wb` | R2d | Wrecker | none | worker SIGSEGV | | | | | | rerun in queue C |
| `rd_R2_s_none_wb` | R2 | stock | none | -222.70 | 77.38 | | | | | |
| `rd_R2_w_O1_g32_wb` | R2 | Wrecker | O1 gap 32 | -372.64 | | `rd_R2_w_none_wb` | +1478.5 | 100/100 | <1e-3 | 48.7 |
| `rd_RT_w_O1_g32_wb` | RT | Wrecker | O1 gap 32 | -276.91 | | `rd_RT_w_none_wb` | -2.0 | 38/100 | 0.82 | 36.2 |
| `rd_R4tn_w_O1_g32_wb` | R4tn | Wrecker | O1 gap 32 | -413.37 | | `rd_R4tn_w_none_wb` | +1854.0 | 100/100 | <1e-3 | 48.2 |
| `rd_R2d_w_O1_g32_wb` | R2d | Wrecker | O1 gap 32 | | | (control pending) | | | | |
| `rd_R2_s_O1_g32_wb` | R2 | stock | O1 gap 32 | -193.67 | | `rd_R2_s_none_wb` | +29.0 | 57/100 | 0.13 | 50.4 |

Distance to the ceiling closed, ceiling `rd_RT_w_none_wb` (-274.88) under
Wrecker and `rd_RT_s_none` under stock: `wo_O1_g32_wb` 0.743 [0.706,
0.777], `wo_O10_g32_wb` 0.224 [0.156, 0.285], `wo_O13_g32_wb` 0.198
[0.119, 0.270], `hm_wo_O1_g32_wb` 0.730 [0.652, 0.795], `hm_wo_O10_g32_wb`
0.152 [0.016, 0.270], `rd_R2_w_O1_g32_wb` 0.938 [0.928, 0.947],
`rd_R4tn_w_O1_g32_wb` 0.930 [0.917, 0.943], `rd_R2_s_O1_g32_wb` 0.537
[0.354, 0.673]. Points per executed override: KEEP 13.1, H-MARL 9.2, R2
31.1, R4tn 37.6.

The directed look over executed looks (`tools_investigate.py`):
`wo_O10_g32_wb` 5,841 of 5,856 looks ran, median 34, 15.5% within 10,
23.1% never; `wo_O13_g32_wb` 4,073 of 4,080, 34, 15.3%, 25.0%;
`hm_wo_O10_g32_wb` 5,714 of 5,730, median 25, 19.3%, 34.8% (the tool's
gate-flip test reads the tick after the look, which under the flag is the
look's own busy tick, hence 0.0%; to be read at the completion tick).

`queue_C.sh` (2026-09-26 22:19 to 23:29, 26 arms, two segfaults rerun in
D) and `queue_D.sh` (2026-09-27 00:10 to 01:08 after a phantom launch
without Docker access at 23:38 that left 31 `exit 1` lines; 36 arms, two
segfaults rerun at 10:12 into root-owned directories). Ceilings under the
flag (`rd_RT_<red>_none_wb`): stock -148.10, Q04 -146.84, Q16 -176.41,
Q32 -216.83, Q48 -245.92, ConvOnly -175.04, Wrecker -274.88;
TargetARestricted -66.57, TargetAOperational -67.15, TargetA -67.73,
TargetB -88.87, TargetBRestricted -90.59, TargetBOperational -90.57,
FailureTracker -142.35, Impacter -79.07, Degrader -127.70, Combined
-106.1 (rerun 10:12).

| Directory | Policy | Red | Mean | Against | Delta | Wins | Closed | 95% CI |
|---|---|---|---|---|---|---|---|---|
| `o1_g32_FSRedAgentWreckerQ04_wb` | KEEP | Q04 | -200.80 | `red_FSRedAgentWreckerQ04` | +124.3 | 89/100 | 0.697 | [0.612, 0.774] |
| `o1_g32_FSRedAgentWreckerQ16_wb` | KEEP | Q16 | -280.75 | control | +258.4 | 95/100 | 0.712 | [0.664, 0.757] |
| `o1_g32_FSRedAgentWreckerQ32_wb` | KEEP | Q32 | -379.19 | control | +393.9 | 95/100 | 0.708 | [0.649, 0.757] |
| `o1_g32_FSRedAgentWreckerQ48_wb` | KEEP | Q48 | -418.20 | control | +510.0 | 97/100 | 0.747 | [0.705, 0.785] |
| `o1_g32_FSRedAgentConvOnly_wb` | KEEP | ConvOnly | -216.50 | control | +100.1 | 75/100 | 0.707 | [0.607, 0.789] |
| `hm_WreckerQ04_O1_g32_wb` | H-MARL | Q04 | -149.38 | `hm_WreckerQ04_none_g0` | +89.8 | 84/100 | 0.972 | [0.855, 1.116] |
| `hm_WreckerQ16_O1_g32_wb` | H-MARL | Q16 | -228.28 | control | +212.0 | 97/100 | 0.803 | [0.754, 0.849] |
| `hm_WreckerQ32_O1_g32_wb` | H-MARL | Q32 | -305.21 | control | +280.6 | 92/100 | 0.760 | [0.692, 0.823] |
| `hm_WreckerQ48_O1_g32_wb` | H-MARL | Q48 | -376.47 | control | +361.6 | 90/100 | 0.735 | [0.656, 0.799] |
| `hm_ConvOnly_O1_g32_wb` | H-MARL | ConvOnly | -174.47 | control | +58.5 | 74/100 | 1.010 | [0.829, 1.212] |
| `rd_R2_WreckerQ04_none_wb` | R2 | Q04 | -332.17 (sd 160.22) | | | | | |
| `rd_R2_WreckerQ16_none_wb` | R2 | Q16 | -588.80 (276.88) | | | | | |
| `rd_R2_WreckerQ32_none_wb` | R2 | Q32 | -854.59 (374.31) | | | | | |
| `rd_R2_WreckerQ48_none_wb` | R2 | Q48 | -1224.66 (525.86) | | | | | |
| `rd_R2_WreckerQ04_O1_g32_wb` | R2 | Q04 | -193.43 | R2 control | +138.7 | 91/100 | 0.749 | [0.685, 0.804] |
| `rd_R2_WreckerQ16_O1_g32_wb` | R2 | Q16 | -244.40 | control | +344.4 | 100/100 | 0.835 | [0.800, 0.865] |
| `rd_R2_WreckerQ32_O1_g32_wb` | R2 | Q32 | -295.45 | control | +559.1 | 100/100 | 0.877 | [0.852, 0.898] |
| `rd_R2_WreckerQ48_O1_g32_wb` | R2 | Q48 | -338.40 | control | +886.3 | 100/100 | 0.906 | [0.890, 0.919] |
| `rd_R2d_w_none_wb` | R2d | Wrecker | -1864.18 (634.66) | | | | | |
| `rd_R2d_w_O1_g32_wb` | R2d | Wrecker | -380.56 | R2d control | +1483.6 | 100/100 | 0.934 | [0.922, 0.944] |
| `k_kft_Wrecker_s1000_final_w_O1_g32_wb` | KEEP seed 1000 | Wrecker | -494.19 | its control | +526.0 | 98/100 | 0.706 | [0.659, 0.749] |
| `k_kft_Wrecker_s1001_final_w_O1_g32_wb` | seed 1001 | Wrecker | -446.19 | control | +502.3 | 99/100 | 0.746 | [0.709, 0.779] |
| `k_kft_Wrecker_s1002_final_w_O1_g32_wb` | seed 1002 | Wrecker | -517.98 | control | +568.7 | 97/100 | 0.701 | [0.653, 0.746] |
| `k_kft_Wrecker_s1000_long_final_w_O1_g32_wb` | 10,000 ep | Wrecker | -599.95 | control | +729.0 | 99/100 | 0.692 | [0.654, 0.727] |
| `k_kft_Wrecker_s1000_lr01_final_w_O1_g32_wb` | 0.1x rate | Wrecker | -480.36 | control | +616.4 | 98/100 | 0.750 | [0.712, 0.785] |

Six KEEP policies: endpoints -490.72, -494.19, -446.19, -517.98, -599.95,
-480.36 against controls -1115.65, -1020.23, -948.46, -1086.71,
-1328.96, -1096.79; least squares `endpoint = -87 + 0.38 x control`, r
0.93 (attempted: `-458 + 0.186 x control`).

Trident under the flag, O1 at gap 32, delta against the defender's own
control, share against `rd_RT_<red>_none_wb`:

| Red agent | KEEP +O1 wb | delta | wins | closed | H-MARL +O1 wb | delta | wins | closed |
|---|---|---|---|---|---|---|---|---|
| TargetARestricted | -105.98 | -7.5 | 33/100 | -0.23 [-0.74, 0.11] | -63.71 | -13.7 | 16/100 | above RT |
| TargetAOperational | -106.14 | -6.2 | 25/100 | -0.19 [-0.57, 0.08] | -64.37 | -9.8 | 21/100 | above RT |
| TargetA | -103.98 | +0.2 | 29/100 | 0.01 [-0.30, 0.24] | -65.70 | -13.8 | 14/100 | above RT |
| TargetB | -123.49 | -7.2 | 35/100 | -0.26 [-0.90, 0.09] | -77.76 | -5.0 | 26/100 | above RT |
| TargetBRestricted | -126.94 | -9.0 | 28/100 | -0.33 [-0.97, 0.01] | -76.73 | -5.2 | 30/100 | above RT |
| TargetBOperational | -123.31 | +4.0 | 33/100 | 0.11 [-0.41, 0.39] | -78.63 | -0.3 | 36/100 | above RT |
| Combined | -145.31 | +20.6 | 58/100 | 0.34 [0.13, 0.50] | -96.60 | +0.8 | 37/100 | above RT (gap -9) |
| FailureTracker | -180.78 | +24.9 | 52/100 | 0.39 [0.16, 0.56] | -135.06 | +4.2 | 42/100 | above RT (gap -3) |
| Impacter | -118.36 | +110.4 | 87/100 | 0.74 [0.67, 0.79] | -71.33 | +62.2 | 66/100 | 1.14 [1.06, 1.27] |
| Degrader | -163.22 | +105.6 | 91/100 | 0.75 [0.69, 0.80] | -131.39 | +60.7 | 65/100 | 0.94 [0.79, 1.09] |

`queue_E.sh` (2026-09-27 10:47 to 11:54, 22 arms, one segfault, O10 at Q48,
rerun at 14:45, complete). The rule ladder under the flag, 100 episodes each,
paired against the attempted-condition arm of the same kind:

| Kind | stock mean (sd) | against attempted | Wrecker mean (sd) | against attempted |
|---|---|---|---|---|
| `R1` | -190.43 (118.62) | +804.1 (98/100) | -1867.39 (570.93) | +1427.0 (98/100) |
| `R2` | -222.70 (77.38) | +663.7 | -1851.15 (618.45) | +1307.8 (96/100) |
| `R2d` | | | -1864.18 (634.66) | |
| `R3` | -311.17 (87.67) | +678.4 (98/100) | -1923.54 (665.58) | +1418.2 (93/100) |
| `R4` | -490.19 (315.23) | +804.1 (92/100) | -3325.32 (652.26) | +238.9 (60/100, p 0.057) |
| `R4t` | -287.70 (160.17) | +666.9 (92/100) | -2388.51 (703.42) | +374.9 (65/100) |
| `R4p` | -6507.40 (1315.60) | +0.0 (0/100 differ) | -5263.93 (871.89) | +0.0 (0/100 differ) |
| `R4d` | -5564.57 (1349.93) | +447.2 (67/100) | -4672.61 (764.79) | +321.0 (60/100) |
| `RT` | -148.10 (31.00) | +20.5 | -274.88 (34.58) | +74.0 (90/100) |

`R4p` issues no multi-tick action and is byte-identical under the flag, a
determinism check for free. Reference: KEEP -187.32 / -1115.65, H-MARL
-136.43 / -842.76.

The directed look along the axis on KEEP under the flag
(`o10_g32_FSRedAgent<red>_wb`, `o13_g32_FSRedAgent<red>_wb`), delta against
the KEEP control, share against `rd_RT_<red>_none_wb`:

| Adversary | O10 mean | delta | wins | closed | O13 mean | delta | wins | closed |
|---|---|---|---|---|---|---|---|---|
| Q04 | -280.12 | +45.0 | 63/100 | 0.252 [0.082, 0.390] | -278.44 | +46.7 | 64/100 | 0.262 [0.087, 0.404] |
| Q16 | -473.43 | +65.7 | 58/100 | 0.181 [0.058, 0.290] | -475.07 | +64.1 | 61/100 | 0.177 [0.064, 0.276] |
| Q32 | -624.47 | +148.6 | 66/100 | 0.267 [0.173, 0.352] | -629.16 | +143.9 | 69/100 | 0.259 [0.160, 0.347] |
| Q48 | -777.12 | +151.0 | 73/100 | 0.221 [0.122, 0.312] | -829.92 | +98.2 | 58/100 | 0.144 [0.025, 0.253] |
| Q64 (Wrecker) | -927.30 | +188.3 | 73/100 | 0.224 [0.156, 0.285] | -949.10 | +166.6 | 69/100 | 0.198 [0.119, 0.270] |
| ConvOnly | -264.81 | +51.8 | 63/100 | 0.366 [0.202, 0.501] | -282.65 | +34.0 | 59/100 | 0.240 [0.020, 0.403] |

Executed looks 99.9% at Q16 (median response 30, 16.7% within 10, 23.0%
never). H-MARL's gate flip read at the completion tick
(`hm_wo_O10_g32_wb`): Investigate to Recover within two steps of the look
14.4% (first looks 20.4%, repeats 10.9%); host recovered within 50 steps
93.5% when the gate flipped, 36.5% when it did not; never 4.0% against
39.9%.

Reading. With directives executed, O1 at gap 32 is +625 on KEEP (from
+452) and +415 on H-MARL (from +99); the two learned defenders close the
same share of their distance to RT (0.74, 0.73), so the earlier
difference between them was the busy share (0.39 against 0.53); the
rules close 0.93 to 0.94; the rule defenders themselves are 660 to 1,300
better once they book only what they do (R2 under stock -223, 36 behind
KEEP); and under a waiting supervisor the endpoints sit within 118 of
one another with R2 + O1 (-373) above H-MARL + O1 (-428) and KEEP + O1
(-491). The look gains 61 on KEEP from execution and nothing on H-MARL,
with the same latency distribution.

---

## Engagement-gate arms

`tools_add_O15.py` (2026-09-27) adds three supervisor rules that hold the
intervention fixed at O1's and vary the rule for when to engage. Each
issues O1's Restore (a ground-truth compromised owned host, first in the
list) only when its signal is at or above `--engage`, otherwise passes the
policy's action through with the gap clock running; `--min-gap` spaces
the interventions as it does for O1 and `--wait-busy` holds them.

- `O15r`: team loss over the trailing `--window` (16) simulator steps, from
  `stats["rew_hist"]`, which the harness now appends each step.
- `O15a`: alerts on the agent's own hosts over the trailing window, an
  alert being a substantive observation entry naming an owned host,
  excluding the reset listing and the echo of the agent's own last action
  (O2f's test), counted in simulator steps.
- `O15c`: ground-truth compromised hosts in the agent's zones. At
  `--engage 1` it is O1.

Header fields `engage` and `window`. Footer fields `engaged` (agent-ticks
with the gate open), `engaged_hit` (open with a compromised owned host,
so a Restore was proposed), `quiet_comp` (shut with one present),
`signal_sum`, `signal_ticks`, `alerts`. Step records carry `"signal":
{agent: [signal, compromised owned hosts]}` for O15 rules only. Tools:
`tools_signal.py` (signal distribution split by compromise, recall and
precision over a threshold grid, from a survey arm), `tools_gate.py`
(arms against a control, a reference and the ceiling with the gate
bookkeeping and the share per intervention), `gate_O15.sh`, `svy_O15.sh`,
`read_svy.sh`, `pilot_O15.sh`, `read_pilot.sh`, `queue_F.sh`,
`rerun_F.sh`, `read_F.sh`.

Gates (`data/gate_O15.txt`): `o2e_smoke_o15` -327.00, 87.68, 77.0 /
108.5; `hm_compat_gate3o15` -931.00, -1308.00, -469.00; and
`gate_wo_O15c_e1_g32_wb`, ten episodes of `O15c --engage 1` under Wrecker
with the flag, identical to `wo_O1_g32_wb` in total and override count on
all ten seeds (`engaged_hit` equals overrides plus deferred).

### Survey and pilots

Survey arms (`svy_O15.sh`, ten episodes each, `--engage 1e9`, the policy
alone with the signal logged): `svy_wo_O15r_wb`, `svy_wo_O15a_wb`,
`svy_so_O15r_wb`, `svy_so_O15a_wb`, `svy_O15r_FSRedAgentWreckerQ16_wb`,
`svy_O15a_FSRedAgentWreckerQ16_wb`, `svy_O15r_FSRedAgentWreckerQ32_wb`,
`svy_O15a_FSRedAgentWreckerQ32_wb`, `svy_hm_wo_O15r_wb`,
`svy_hm_wo_O15a_wb`. Read in `data/read_svy.txt`; the summary table is in
RESULTS.md "When to engage". Pilots (`pilot_O15.sh`, ten episodes, seeds
0 to 9, KEEP under Wrecker, gap 32, held): `pilot_wo_O15r_e{16,24,40}`,
`pilot_wo_O15a_e{1,2}`, `pilot_wo_O15c_e{2,3,4}`, all `_g32_wb`; read in
`data/read_pilot.txt`. On ten seeds against `wo_O1_g32_wb` (0.653 of the
distance to RT on those seeds): O15r 0.666 / 0.623 / 0.479 at 37 / 28 /
19 interventions, O15a 0.669 / 0.469 at 43 / 27, O15c 0.550 / 0.132 /
0.047 at 37 / 26 / 18. The pilots chose the queue's thresholds; they are
not arms.

### Queue F

`queue_F.sh`, 25 arms, two lanes, 15:40 to 16:44; three worker segfaults
(`wo_O15a_e2_g32_wb` at 12 episodes, `hm_wo_O15r_e10_g32_wb` at 96,
`hm_wo_O1_g64_wb` at 63) rerun from clean directories by `rerun_F.sh`,
22:47 to 22:59. All 100 episodes on seeds 0 to 99, `--wait-busy`, gap 32
for the gate arms, budget 99999, six workers. Read in `data/read_F.txt`.
Shares are of the distance from the control to RT under the same
adversary (`rd_RT_*_none_wb`); "per ovr" is that share per intervention
the gap floor accepted.

KEEP under Wrecker (control `red_FSRedAgentWrecker` -1,115.7, RT -274.9):

| Directory | Rule | Mean | Against control | Interventions / ep | Deferred | Engaged / hit / quiet | Closed | Per ovr |
|---|---|---|---|---|---|---|---|---|
| `wo_O1_g32_wb` | O1 gap 32 (reference) | -490.7 | +624.9 | 48.1 | 399 | | 0.743 | 0.0154 |
| `wo_O1_g64_wb` | O1 gap 64 | -613.6 | +502.1 | 31.3 | 610 | | 0.597 | 0.0191 |
| `wo_O1_g96_wb` | O1 gap 96 | -691.3 | +424.4 | 23.0 | 710 | | 0.505 | 0.0219 |
| `wo_O15r_e16_g32_wb` | O15r, 16 | -589.1 | +526.6 | 34.3 | 219 | 803 / 253 / 375 | 0.626 | 0.0183 |
| `wo_O15r_e24_g32_wb` | O15r, 24 | -646.0 | +469.7 | 27.5 | 149 | 533 / 176 / 536 | 0.559 | 0.0203 |
| `wo_O15r_e40_g32_wb` | O15r, 40 | -731.4 | +384.2 | 17.4 | 68 | 226 / 85 / 736 | 0.457 | 0.0263 |
| `wo_O15a_e1_g32_wb` | O15a, 1 | -638.4 | +477.3 | 41.4 | 279 | 680 / 320 / 358 | 0.568 | 0.0137 |
| `wo_O15a_e2_g32_wb` | O15a, 2 | -776.7 | +339.0 | 26.2 | 116 | 225 / 142 / 733 | 0.403 | 0.0154 |
| `wo_O15c_e2_g32_wb` | O15c, 2 | -763.6 | +352.0 | 34.3 | 282 | 316 / 316 / 578 | 0.419 | 0.0122 |
| `wo_O15c_e3_g32_wb` | O15c, 3 | -996.4 | +119.2 | 23.9 | 215 | 238 / 238 / 777 | 0.142 | 0.0059 |

Paired against the cadences: O15r 24 against O1 gap 64 -32.4 (47/100,
p 0.617); O15r 40 against gap 96 -40.1 (43/100, p 0.193); O15r 16
against gap 32 -98.3 (27/100, p <0.001); O15a 1 against gap 32 -147.7
(25/100); O15a 2 against gap 64 -163.1 (27/100); O15c 2 against gap 64
-150.1 (32/100, p 0.001).

KEEP under stock (control `corpus_v1` -187.3, RT `rd_RT_s_none_wb` -148.1):

| Directory | Rule | Mean | Against control | Interventions / ep | Engaged / hit / quiet | Closed |
|---|---|---|---|---|---|---|
| `so_O1_g32_wb` | O1 gap 32 | -174.8 | +12.5 (57/100, p 0.13) | 48.0 | | 0.318 [-0.01, 0.55] |
| `so_O1_g32` | O1 gap 32, fired, 2026-10-12 | -200.16 | -12.8 (35/100, p 0.005) | 52.3 | | held minus fired +25.3 (77/100, bootstrap 15.6 to 35.2) |
| `so_O1_n100_wb` | O1, no gap, no budget, held, 2026-10-12 | -192.84 | -5.5 (43/100, p 0.266, bootstrap -21.3 to 10.1) | 74.3 | | the held counterpart of `oracle_O1_n100`, inside the null band |
| `so_O1_g64_wb` | O1 gap 64 | -169.4 | +17.9 | 30.8 | | 0.457 |
| `so_O15r_e3_g32_wb` | O15r, 3 | -178.3 | +9.1 | 39.4 | 961 / 306 / 257 | 0.231 |
| `so_O15c_e2_g32_wb` | O15c, 2 | -195.3 | -7.9 | 34.5 | 323 / 323 / 560 | -0.202 |

`so_O1_g32_wb` is the first O1 arm under the stock red at gap 32; it and
`o2_g32_wb` (-175.1) are the same arm to within a point. O15r 3 against
gap 64 -8.9 (44/100, p 0.27); O15c 2 against gap 64 -25.9 (26/100).

KEEP on the axis (controls `red_FSRedAgentWreckerQ16` -539.2, `Q32`
-773.1; RT -176.4, -216.8):

| Directory | Rule | Mean | Against control | / ep | Engaged / hit / quiet | Closed | Per ovr |
|---|---|---|---|---|---|---|---|
| `o15r_e6_g32_FSRedAgentWreckerQ16_wb` | O15r, 6 | -305.1 | +234.1 | 37.0 | 868 / 274 / 328 | 0.645 | 0.0174 |
| `o15a_e1_g32_FSRedAgentWreckerQ16_wb` | O15a, 1 | -339.4 | +199.7 | 42.1 | 688 / 316 / 331 | 0.551 | 0.0131 |
| `o15c_e2_g32_FSRedAgentWreckerQ16_wb` | O15c, 2 | -408.8 | +130.4 | 35.2 | 330 / 330 / 570 | 0.360 | 0.0102 |
| `o1_g64_FSRedAgentWreckerQ16_wb` | O1 gap 64 | -332.6 | +206.6 | 30.9 | | 0.569 | 0.0184 |
| `o15r_e11_g32_FSRedAgentWreckerQ32_wb` | O15r, 11 | -406.0 | +367.1 | 32.6 | 762 / 231 / 394 | 0.660 | 0.0202 |
| `o15a_e1_g32_FSRedAgentWreckerQ32_wb` | O15a, 1 | -435.0 | +338.1 | 41.8 | 693 / 318 / 319 | 0.608 | 0.0146 |
| `o15c_e2_g32_FSRedAgentWreckerQ32_wb` | O15c, 2 | -512.5 | +260.6 | 35.2 | 322 / 322 / 572 | 0.468 | 0.0133 |
| `o1_g64_FSRedAgentWreckerQ32_wb` | O1 gap 64 | -460.1 | +312.9 | 30.7 | | 0.563 | 0.0183 |

Paired against gap 64: Q16 O15r +27.6 (58/100, p 0.085), O15c -76.2
(26/100); Q32 O15r +54.2 (62/100, p 0.021), O15c -52.3 (36/100,
p 0.007). The reference O1 gap 32 arms are `o1_g32_FSRedAgentWrecker{Q16,
Q32}_wb` (0.712, 0.708).

H-MARL under Wrecker (control `hm_w_none` -842.8, RT -274.9):

| Directory | Rule | Mean | Against control | / ep | Engaged / hit / quiet | Closed | Per ovr |
|---|---|---|---|---|---|---|---|
| `hm_wo_O15r_e10_g32_wb` | O15r, 10 | -487.9 | +354.8 | 33.7 | 687 / 236 / 248 | 0.625 | 0.0185 |
| `hm_wo_O15a_e1_g32_wb` | O15a, 1 | -551.1 | +291.6 | 36.1 | 435 / 230 / 309 | 0.514 | 0.0142 |
| `hm_wo_O15c_e2_g32_wb` | O15c, 2 | -640.6 | +202.2 | 31.4 | 269 / 269 / 403 | 0.356 | 0.0113 |
| `hm_wo_O1_g64_wb` | O1 gap 64 | -530.1 | +312.6 | 30.1 | | 0.551 | 0.0183 |

Paired against gap 64: O15r +42.2 (58/100, p 0.133), O15c -110.5
(33/100, p 0.001). Reference `hm_wo_O1_g32_wb` -428.0, 0.730.

Execution shares (`tools_dropped.py`, 20 episodes): `wo_O15r_e24_g32_wb`
0.993, `wo_O1_g64_wb` 0.992, `hm_wo_O15r_e10_g32_wb` 0.993. Trial sizing
(`tools_power.py`): O15r 24 against O1 gap 64, mean -32.4, sd 203.2,
smallest effect at 80 percent power 141 / 111 / 84 at N = 20 / 30 / 50;
O15r 24 against the control, +469.7, sd 324.1, 210 / 169 / 129.

Reading. With the intervention fixed, the engagement rule spans 0.14 to
0.60 of the distance to the ceiling at about thirty interventions an
episode. A loss thermostat and a fixed cadence are the same at matched
effort on five pairings; a status count at two hosts is below the cadence
on every pairing and at three hosts collapses; the alert gate matches the
cadence's score at a third more effort. Value per intervention rises
from 0.015 at 48 an episode to 0.026 at 17 on cadence and thermostat
alike. The full reading is in RESULTS.md "When to engage".

---

## Queue G: delivered-directive arms

`tools_add_queue.py` (2026-09-28) adds three things to the harness, each
guarded so an unpatched run is unchanged.

- `--queue first|last` (O1, O15r and O15c on a learned policy, requires
  `--wait-busy`). On a busy tick with the gap floor open the supervisor
  is consulted and its directive stashed for the agent; `first` keeps the
  first stash of a busy spell, `last` replaces it on every busy tick. On
  the agent's next free tick the stash fires as decided and is counted as
  an override, with `queue_fired`, `queue_stale` (its host was no longer
  compromised when it fired; it fires anyway) and `queue_wait` (ticks
  held). Header field `queue`; footer fields `queued`, `queue_fired`,
  `queue_stale`, `queue_wait`.
- `O16`, the as-is supervisor: O2f's latch for eyes; on a free tick with
  the floor open, Restore a latched host whose Analyse returned a file
  with Density at or above 0.9 since its last restore, otherwise Analyse
  the latched host not looked at within `ANALYSE_WINDOW`; nothing while
  the floor is shut; the restore is booked on proposal only. Footer
  `o16_confirmed`.
- `O15h`, O15a's gate with the Restore sent to the host of the latest
  alert in the window. Footer `o15h_clean` (gate-open ticks whose target
  was clean by ground truth; `engaged_hit` the ones where it was
  compromised).

`capture_hmarl.py` carries `--queue` and the same header and footer
fields. The O2e smoke and the H-MARL compat gate reproduce under the
patch. `queue_G.sh` launches the 25 arms on two lanes and, called with
`read`, prints the tables below from the footers and `tools_gate.py`.

Run 2026-09-28, launched 22:27, done 23:36. `wo_O1_g8_wb` lost a worker
at 22:52 and was rerun from a clean directory after the queue finished
(`mean -332.46 stdev 54.64 overrides/ep 72.8`). All arms 100 episodes on
seeds 0 to 99, `--wait-busy`, budget 99999 except where noted, six
workers. Shares are of the distance from the control to RT under the
same adversary.

The held click (KEEP control `red_FSRedAgentWrecker` -1,115.7; H-MARL
`hm_w_none` -842.8; RT `rd_RT_w_none_wb` -274.9):

| Directory | Rule | Mean | Against control | Against the free-tick arm | Ovr / ep | Deferred | Queued / fired / stale | Wait, ticks | Closed |
|---|---|---|---|---|---|---|---|---|---|
| `wo_O1_g32_qf_wb` | O1 gap 32, queue first | -491.9 | +623.8 | -1.2 (40/100, p 0.826) | 48.2 | 401.5 | 18.9 / 18.9 / 1.4 | 1.6 | 0.742 |
| `wo_O1_g32_ql_wb` | O1 gap 32, queue last | -500.5 | +615.2 | -9.8 (36/100, p 0.731) | 48.1 | 402.8 | 18.9 / 18.9 / 1.3 | 1.0 | 0.732 |
| `hm_wo_O1_g32_qf_wb` | O1 gap 32, queue first | -457.8 | +384.9 | -29.9 (32/100, p 0.023) | 47.9 | 332.0 | 30.9 / 30.8 / 1.4 | 1.1 | 0.678 |
| `hm_wo_O1_g32_ql_wb` | O1 gap 32, queue last | -459.0 | +383.8 | -31.0 (30/100, p 0.012) | 48.0 | 333.2 | 30.9 / 30.8 / 1.3 | 1.0 | 0.676 |

The rate curve, KEEP under Wrecker (gaps 32, 64 and 96 are queue C and
F arms, listed for the curve):

| Directory | Rule | Mean | Against control | Ovr / ep | Deferred | Closed | Per ovr |
|---|---|---|---|---|---|---|---|
| `wo_O1_g4_wb` | O1 gap 4 | -324.5 | +791.1 | 74.7 | 0.0 | 0.941 | 0.0126 |
| `wo_O1_g8_wb` | O1 gap 8 | -332.5 | +783.2 | 72.8 | 44.9 | 0.932 | 0.0128 |
| `wo_O1_g16_wb` | O1 gap 16 | -353.7 | +761.9 | 65.1 | 189.3 | 0.906 | 0.0139 |
| `wo_O1_g32_wb` | O1 gap 32 | -490.7 | +624.9 | 48.1 | 399.2 | 0.743 | 0.0154 |
| `wo_O1_g64_wb` | O1 gap 64 | -613.6 | +502.1 | 31.3 | 609.7 | 0.597 | 0.0191 |
| `wo_O1_g96_wb` | O1 gap 96 | -691.3 | +424.4 | 23.0 | 710.0 | 0.505 | 0.0219 |
| `wo_O1_g128_wb` | O1 gap 128 | -744.0 | +371.7 | 18.2 | 770.0 | 0.442 | 0.0243 |
| `wo_O2_g0_b77_wb` | O2, no gap, budget 77 | -327.5 | +788.1 | 71.0 | 0.0 | 0.937 | 0.0132 |
| `wo_O2_g32_wb` | O2 gap 32 | -490.4 | +625.3 | 47.5 | 373.7 | 0.744 | 0.0157 |
| `hm_wo_O1_g16_wb` | H-MARL, O1 gap 16 | -329.0 | +513.8 | 63.3 | 163.7 | 0.905 | 0.0143 |
| `hm_wo_O1_g128_wb` | H-MARL, O1 gap 128 | -661.5 | +181.2 | 17.8 | 590.0 | 0.319 | 0.0180 |

`wo_O2_g0_b77_wb` paired against `wo_O2_g32_wb`: +162.9, 96/100,
p <0.001. Its restores by fifty-step bin run 6.6 to 7.9 an episode with
the last at step 490; the budget is never reached.

The as-is supervisor (stock control `corpus_v1` -187.3, RT
`rd_RT_s_none_wb` -148.1; mass 16 and 32 controls -539.2 and -773.1):

| Directory | Pairing | Mean | Against control | Ovr / ep | Analyses / restores / confirmed | Agreements | Closed | Per ovr |
|---|---|---|---|---|---|---|---|---|
| `wo_O16_g32_wb` | KEEP, Wrecker | -1033.1 | +82.6 (60/100, p 0.057) | 71.2 | 66.9 / 4.3 / 6.2 | 60.5 | 0.098 | 0.0014 |
| `wo_O16_g8_wb` | KEEP, Wrecker, gap 8 | -920.1 | +195.6 (73/100, p <0.001) | 228.9 | 222.3 / 6.5 / 7.4 | 56.9 | 0.233 | 0.0010 |
| `so_O16_g32_wb` | KEEP, stock | -188.0 | -0.7 (49/100, p 0.92) | 71.8 | 66.9 / 5.0 / 6.5 | 59.0 | -0.018 | -0.0002 |
| `o16_g32_FSRedAgentWreckerQ16_wb` | KEEP, mass 16 | -491.0 | +48.2 | 71.4 | 65.2 / 6.2 / 8.5 | 63.4 | 0.133 | 0.0019 |
| `o16_g32_FSRedAgentWreckerQ32_wb` | KEEP, mass 32 | -690.8 | +82.3 | 71.7 | 66.4 / 5.3 / 7.8 | 63.2 | 0.148 | 0.0021 |
| `hm_wo_O16_g32_wb` | H-MARL, Wrecker | -851.6 | -8.9 (48/100, p 0.76) | 71.9 | 70.4 / 1.4 / 2.1 | 25.0 | -0.016 | -0.0002 |

The directed look on the same pairings for reference: `wo_O10_g32_wb`
0.224, `o10_g32_wb` (stock) 0.060, `o10_g32_FSRedAgentWreckerQ16_wb`
0.181, `o10_g32_FSRedAgentWreckerQ32_wb` 0.267, `hm_wo_O10_g32_wb`
0.152.

The alert gate with as-is hands:

| Directory | Pairing | Mean | Against control | Restores / ep | Deferred | Engaged / hit / quiet | `o15h_clean` | Closed |
|---|---|---|---|---|---|---|---|---|
| `wo_O15h_e1_g32_wb` | KEEP, Wrecker | -1015.6 | +100.1 | 56.5 | 594.3 | 651 / 89 / 477 | 561.5 | 0.119 |
| `hm_wo_O15h_e1_g32_wb` | H-MARL, Wrecker | -860.2 | -17.5 | 49.1 | 388.0 | 437 / 62 / 396 | 375.5 | -0.031 |

`wo_O15h_e1_g32_wb` paired against `wo_O15a_e1_g32_wb`: -377.2, 9/100,
p <0.001.

The thermostat at mass 16 and 32 (gap-64 cadences and the mid rungs are
queue F arms, listed for the ladder):

| Directory | Rule | Mean | Against control | Ovr / ep | Deferred | Engaged / hit / quiet | Closed | Per ovr |
|---|---|---|---|---|---|---|---|---|
| `o15r_e3_g32_FSRedAgentWreckerQ16_wb` | O15r, 3 | -301.3 | +237.9 | 44.4 | 328.3 | 1179 / 373 / 150 | 0.656 | 0.0148 |
| `o15r_e6_g32_FSRedAgentWreckerQ16_wb` | O15r, 6 | -305.1 | +234.1 | 37.0 | 237.0 | 868 / 274 / 328 | 0.645 | 0.0174 |
| `o15r_e12_g32_FSRedAgentWreckerQ16_wb` | O15r, 12 | -350.3 | +188.9 | 27.2 | 149.3 | 539 / 177 / 543 | 0.521 | 0.0191 |
| `o1_g64_FSRedAgentWreckerQ16_wb` | O1 gap 64 | -332.6 | +206.6 | 30.9 | 605.1 | | 0.569 | 0.0184 |
| `o15r_e6_g32_FSRedAgentWreckerQ32_wb` | O15r, 6 | -391.0 | +382.1 | 38.5 | 275.8 | 1008 / 314 / 254 | 0.687 | 0.0178 |
| `o15r_e11_g32_FSRedAgentWreckerQ32_wb` | O15r, 11 | -406.0 | +367.1 | 32.6 | 198.6 | 762 / 231 / 394 | 0.660 | 0.0202 |
| `o15r_e22_g32_FSRedAgentWreckerQ32_wb` | O15r, 22 | -480.2 | +292.8 | 22.7 | 99.6 | 363 / 122 / 642 | 0.526 | 0.0232 |
| `o1_g64_FSRedAgentWreckerQ32_wb` | O1 gap 64 | -460.1 | +312.9 | 30.7 | 588.5 | | 0.563 | 0.0183 |

H-MARL's mode gate held: `hm_wo_O14_g32_wb` -880.27, -37.5 against the
control (43/100, p 0.228), 57.8 overrides an episode, identical to
`hm_wo_O14_g32` fired at its tick. The mode gate edits the policy's own
action on its own tick and carries nothing across a busy spell.

Execution shares from the step records of twenty episodes
(`tools_dropped.py`): `wo_O1_g32_qf_wb` Restore 47.8 of 48.2 an episode
executed, 0.991, busy share of agent-steps 0.397; `wo_O16_g32_wb`
Analyse 65.9 of 66.2, 0.996, Restore 4.2 of 4.2, 0.988, busy share
0.393; `hm_wo_O1_g32_qf_wb` Restore 46.6 of 47.1, 0.990, busy share
0.538.

## Queue H: a person's eyes and hands

`tools_add_person.py` (2026-09-29) adds five things to the harness, each
guarded so an unpatched run is unchanged. Run after
`tools_add_queue.py`.

- `--recall R --false-alarm F` (O1 on a learned policy): O1 sees the
  truth through a detector. A compromise is shown for its whole life
  with probability R, drawn when the supervisor first looks at it and
  redrawn if the host is compromised again; a clean owned host raises a
  false alarm that shows for 16 steps, at the per-step onset rate F /
  (16 (1 - F)) that keeps a share F of clean hosts flagged; the
  supervisor restores one flagged host chosen at random by its own
  generator, seeded by the episode, so the environment's and the
  policy's draws are untouched. A restore clears a false alarm on its
  host. With either flag the pick is random even at R 1, F 0. Footer
  `eyes_tp`, `eyes_fp`, `eyes_fn`, `eyes_clean` (agent-ticks).
- `--delay D --wrong W --skip S` (with `--queue first`; O1, O15r,
  O15c): a person's hands. At a decision, with probability S the prompt
  passes and the gap clock restarts; otherwise the click lands on
  another owned host with probability W, and it lands D steps after the
  decision, held for the agent if it is busy then (a delayed click is
  a queued directive with a due tick). At D 0, W 0, S 0 the arm is
  `--queue first` directive for directive. Footer `h_skip`, `h_wrong`.
- `O16t`: R2's triage at the gate. A private R2 instance reads the
  agent's observations (on busy ticks too) and proposes as it would as a
  defender: Restore on a second alert or a confirmed file, Analyse on a
  first alert. The supervisor offers that proposal when the gap floor
  is open; a proposal equal to the policy's own action is an agreement.
  Footer `sup_tp`, `sup_fp`, `sup_fn`, `sup_own`: R2's restore
  candidates against the truth per tick.
- `O17` (KEEP only, `--engage T`): the policy's own suspicion. Each
  owned host is scored by the probability the actor puts on Remove or
  Restore of it (the O11 wrapper's `stats["probs"]`); at the gate the
  top host is restored if its score is at least T. At T 1e9 it never
  acts and the step records carry `"signal": {agent: [top score, top
  host compromised, best score on a compromised host, best on a clean
  host, compromised hosts]}`. Footer `o17_clean`, plus the O15 gate
  fields. The actor pass leaves the policy's sampling untouched
  (`gate_svy_wo_O17_wb` identical to the control on ten seeds).
- `--agents 0,4`: the supervisor acts for the listed agents only. All
  five is O1 (`gate_wo_O1_a01234_g32_wb`, ten seeds identical).
- Every footer now carries `exec_clean`, restores handed to a free agent
  on a host that was clean at that tick, and `CAGE_EPISODE_LENGTH` in
  the environment overrides the 500-step episode (unused).

Gates (`o2e_smoke_person`, `hm_compat_gate3person`,
`gate_wo_O1h_zero_g32_wb` against `wo_O1_g32_qf_wb`,
`gate_hm_wo_O1h_zero_g32_wb` against `hm_wo_O1_g32_qf_wb`,
`gate_wo_O1_a01234_g32_wb` against `wo_O1_g32_wb`, `gate_svy_wo_O17_wb`
against `red_FSRedAgentWrecker`, and six two-episode smokes): all
reproduce. The first cut of the patch named `capture_episode`'s new
parameter `agents`, which the function's own `agents = Submission.AGENTS`
shadowed, so every KEEP run died writing its header; the parameter is
`only_agents`, the tool repairs the earlier state in place, and the gate
directories from the first attempt were overwritten by the rerun.

`queue_H.sh`: 44 arms on two lanes, launched 14:15, done 16:21. An arm
with fewer than 100 footers is cleared through the container (no sudo)
and rerun once; `wo_O1n_r050_f005_g32_wb` (15:06) and `wo_O16t_g32_wb`
(16:04) lost a worker and reran clean. The two O17 arms ran after the
read, 17:07 to 17:25. `./queue_H.sh read` prints the tables; read in
`data/read_H.txt`. Shares are of the distance from the control to RT.

The eyes surface (control `red_FSRedAgentWrecker` -1,115.7, RT
-274.9; `rates` in the read prints the realized per-tick recall and
false-alarm share from the footers):

| Directory | Recall, false | Mean | Against control | Ovr / ep | Deferred | eyes tp / fp / fn / clean per ep | Closed |
|---|---|---|---|---|---|---|---|
| `wo_O1n_r100_f000_g32_wb` | 1, 0 | -466.4 | +649.2 | 47.6 | 402.8 | | 0.772 |
| `wo_O1n_r075_f000_g32_wb` | 0.75, 0 | -611.1 | +504.6 | 41.2 | 295.2 | | 0.600 |
| `wo_O1n_r050_f000_g32_wb` | 0.5, 0 | -807.0 | +308.7 | 30.1 | 153.5 | | 0.367 |
| `wo_O1n_r025_f000_g32_wb` | 0.25, 0 | -958.4 | +157.3 | 14.8 | 33.4 | | 0.187 |
| `wo_O1n_r100_f002_g32_wb` | 1, 0.02 | -537.6 | +578.0 | 57.4 | 552.0 | | 0.687 |
| `wo_O1n_r100_f005_g32_wb` | 1, 0.05 | -615.2 | +500.4 | 66.5 | 754.8 | | 0.595 |
| `wo_O1n_r100_f010_g32_wb` | 1, 0.10 | -696.0 | +419.6 | 73.0 | 964.2 | | 0.499 |
| `wo_O1n_r100_f020_g32_wb` | 1, 0.20 | -852.5 | +263.2 | 77.6 | 1189.3 | | 0.313 |
| `wo_O1n_r075_f005_g32_wb` | 0.75, 0.05 | -775.7 | +340.0 | 63.2 | 653.8 | | 0.404 |
| `wo_O1n_r050_f005_g32_wb` | 0.5, 0.05 | -887.5 | +228.2 | 60.1 | 563.4 | | 0.271 |
| `wo_O1n_r050_f010_g32_wb` | 0.5, 0.10 | -1021.9 | +93.8 | 70.0 | 841.5 | | 0.112 |
| `wo_O2f_g32_wb` | the latch | -1011.8 | +103.9 | 45.8 | 62.3 | | 0.124 |
| `wo_O1n_latch_g32_wb` | 0.010, 0.0058 (void) | -1170.5 | -54.9 | 9.8 | 10.8 | | -0.065 |
| `hm_wo_O1n_r050_f000_g32_wb` | 0.5, 0 | -669.1 | +173.7 | 29.6 | 129.1 | | 0.306 |
| `hm_wo_O1n_r100_f005_g32_wb` | 1, 0.05 | -539.5 | +303.3 | 65.0 | 586.2 | | 0.534 |
| `hm_wo_O1n_r050_f005_g32_wb` | 0.5, 0.05 | -783.6 | +59.2 | 59.3 | 450.4 | | 0.104 |

Per-episode `eyes_*` sums are in the footers; the read's `rates` table
gives them as rates. `wo_O1n_r100_f000_g32_wb` paired against
`wo_O1_g32_wb`: +24.3, 58/100, p 0.133.

A person's hands (reference `wo_O1_g32_qf_wb` -491.9, 0.742;
`hm_wo_O1_g32_qf_wb` -457.8, 0.678):

| Directory | Hands | Mean | Against the reference | Ovr / ep | Queued / stale | h_skip / h_wrong | exec_clean | Closed |
|---|---|---|---|---|---|---|---|---|
| `wo_O1h_d2_g32_wb` | delay 2 | -517.7 | -25.8 (53/100, p 0.617) | 46.9 | 47.3 / 2.3 | | 2.3 | 0.711 |
| `wo_O1h_d4_g32_wb` | delay 4 | -549.9 | -58.0 (36/100, p 0.007) | 45.3 | 45.6 / 3.4 | | 3.4 | 0.673 |
| `wo_O1h_d8_g32_wb` | delay 8 | -563.3 | -71.4 (29/100, p <0.001) | 42.4 | 43.2 / 4.9 | | 4.9 | 0.657 |
| `wo_O1h_w10_g32_wb` | wrong 0.10 | -548.2 | -56.3 (32/100, p 0.001) | 49.5 | 19.7 / 3.3 | 0 / 5.3 | 6.2 | 0.675 |
| `wo_O1h_w25_g32_wb` | wrong 0.25 | -630.6 | -138.7 (23/100) | 52.0 | 21.0 / 5.9 | 0 / 13.3 | 13.2 | 0.577 |
| `wo_O1h_w50_g32_wb` | wrong 0.50 | -788.4 | -296.5 (9/100) | 55.1 | 21.9 / 10.4 | 0 / 27.5 | 25.6 | 0.389 |
| `wo_O1h_s25_g32_wb` | skip 0.25 | -590.8 | -98.9 (29/100) | 38.0 | 14.9 / 0.9 | 13.3 / 0 | 0.9 | 0.624 |
| `wo_O1h_s50_g32_wb` | skip 0.50 | -739.6 | -247.7 (13/100) | 27.4 | 10.3 / 0.7 | 28.2 / 0 | 0.7 | 0.447 |
| `wo_O1h_typ_g32_wb` | 2, 0.10, 0.20 | -609.8 | -117.9 (24/100) | 40.1 | 40.3 / 5.8 | 10.5 / 4.3 | 5.8 | 0.602 |
| `wo_O1h_tired_g32_wb` | 4, 0.25, 0.40 | -806.6 | -314.7 (4/100) | 30.9 | 31.3 / 8.6 | 21.6 / 7.9 | 8.6 | 0.368 |
| `wo_O1h_typ_r075_f005_g32_wb` | typical, detector 0.75 / 0.05 | -856.7 | -364.8 (8/100) | 49.7 | 49.9 / 25.1 | 12.8 / 5.0 | 25.1 | 0.308 |
| `hm_wo_O1h_typ_g32_wb` | 2, 0.10, 0.20 | -577.8 | -120.0 (28/100) | 39.1 | 39.3 / 5.7 | 10.2 / 4.2 | | 0.467 |
| `hm_wo_O1h_tired_g32_wb` | 4, 0.25, 0.40 | -677.9 | -220.1 (18/100) | 30.1 | 30.5 / 9.8 | 21.2 / 8.0 | | 0.290 |

The thermostat with the click held:

| Directory | Rule | Mean | Against control | Ovr / ep | Engaged / hit / quiet | Queued / stale | Closed |
|---|---|---|---|---|---|---|---|
| `wo_O1_g64_qf_wb` | O1 gap 64, queue first | -616.1 | +499.6 | 31.5 | | 12.3 / 1.0 | 0.594 |
| `wo_O15r_e24_g32_qf_wb` | O15r 24, queue first | -637.9 | +477.8 | 27.6 | 594 / 179 / 859 | 10.9 / 1.2 | 0.568 |
| `wo_O15r_e24_g32_typ_wb` | O15r 24, queue first, typical hands | -755.0 | +360.7 | 25.5 | 727 / 292 / 774 | 25.6 / 4.0 | 0.429 |
| `hm_wo_O15r_e10_g32_qf_wb` | H-MARL O15r 10, queue first | -508.2 | +334.5 | 36.2 | 1031 / 255 / 428 | | 0.589 |

Paired: `wo_O15r_e24_g32_qf_wb` against `wo_O1_g64_qf_wb` -21.8 (48/100,
p 0.764), against `wo_O15r_e24_g32_wb` +8.1 (37/100, p 0.440);
`wo_O15r_e24_g32_typ_wb` against `wo_O15r_e24_g32_wb` -109.0 (31/100);
`hm_wo_O15r_e10_g32_qf_wb` against `hm_wo_O15r_e10_g32_wb` -20.3 (36/100,
p 0.434).

R2's triage (O16t) and the policy's own suspicion (O17):

| Directory | Pairing | Mean | Against control | Ovr / ep | Analyses / restores | exec_clean | sup tp / fp / fn / own per ep | Closed |
|---|---|---|---|---|---|---|---|---|
| `wo_O16t_g32_wb` | KEEP, Wrecker | -990.0 | +125.7 (64/100, p 0.007) | 68.9 | 28.5 / 40.4 | 30.3 | 4.1 / 13.2 / 18.1 / 222 (per tick 0.185 recall, 0.059 false) | 0.149 |
| `wo_O16t_g8_wb` | KEEP, Wrecker, gap 8 | -863.8 | +251.8 (78/100) | 157.5 | 91.4 / 66.1 | 46.4 | | 0.300 |
| `so_O16t_g32_wb` | KEEP, stock | -209.1 | -21.8 (28/100, p <0.001) | 69.1 | 26.1 / 43.0 | 32.3 | | -0.555 |
| `hm_wo_O16t_g32_wb` | H-MARL, Wrecker | -745.6 | +97.2 (56/100, p 0.271) | 67.2 | 21.5 / 45.7 | | | 0.171 |
| `svy_wo_O17_wb` | KEEP, Wrecker, `--engage 1e9` | -1115.65 | +0.0 (identical to the control) | 0 | | | | |
| `wo_O17_e00173_g32_wb` | O17 at 0.0173 (the median score) | -924.5 | +191.1 (74/100, p <0.001) | 46.8 | 0 / 46.8 | | engaged 462, hit 128, o17_clean 301, quiet 649, agreements 32.5 | 0.227 |
| `wo_O17_e00694_g32_wb` | O17 at 0.0694 (the 90th percentile) | -1053.8 | +61.9 (57/100, p 0.193) | 18.9 | 0 / 18.9 | | engaged 72, hit 32, o17_clean 21, quiet 978, agreements 19.1 | 0.074 |

`wo_O16t_g32_wb` against `wo_O16_g32_wb`: +43.1, 51/100, p 0.920. The
`sup_*` per-episode figures above are the footer sums divided by 100;
the per-tick rates are what the read prints.

Agent subsets (`--agents`):

| Directory | Agents | Mean | Against control | Ovr / ep | Deferred | Closed | Per ovr |
|---|---|---|---|---|---|---|---|
| `wo_O1_a0_g32_wb` | 0 | -1021.6 | +94.0 | 8.8 | 68.2 | 0.112 | 0.0128 |
| `wo_O1_a1_g32_wb` | 1 | -953.7 | +162.0 | 8.0 | 49.3 | 0.193 | 0.0242 |
| `wo_O1_a2_g32_wb` | 2 | -1058.7 | +57.0 | 8.8 | 57.5 | 0.068 | 0.0077 |
| `wo_O1_a3_g32_wb` | 3 | -1034.0 | +81.7 | 7.8 | 46.8 | 0.097 | 0.0124 |
| `wo_O1_a4_g32_wb` | 4 | -990.7 | +125.0 | 14.9 | 188.0 | 0.149 | 0.0100 |
| `wo_O1_a04_g32_wb` | 0 and 4, the two O1 acts for most | -885.7 | +230.0 | 23.9 | 256.0 | 0.273 | 0.0115 |

Cut-off reads (no arms; from the step records of the arms above and of
`red_FSRedAgentWrecker`, `rd_RT_w_none_wb`, `wo_O10_g32_wb`): the O1
cut-off table, the paired-gain and power table, and the O17 cut-off
line are in RESULTS.md under "Cut-off episodes and the trial's power";
the commands are in the conversation log of 2026-09-29 and take a
minute to rerun.

## Known issues

- **Queue H: the latch arm is void, H-MARL footers lack `exec_clean`, two
  reruns (2026-09-29).** `wo_O1n_latch_g32_wb` was meant to run O1
  through the model at the O2f latch's own recall and false-alarm rate,
  read from `wo_O2f_g32_wb`'s `latch_*` footer fields; those are
  per-tick counts, and O2f pops a host from the latch when it restores
  it, so its per-tick recall reads 0.010 while the model's `--recall`
  is the share of compromises ever shown. The arm ran at recall 0.01 and
  says nothing; placing the latch on the surface needs a
  per-compromise counter in the footer (open item). `capture_hmarl.py`
  builds its footer from every numeric stat except keys starting
  `exec_`, so `exec_clean` never reaches H-MARL footers and the read's
  clean share prints 0.00 for H-MARL arms; the KEEP figures are right.
  `wo_O1n_r050_f005_g32_wb` (15:06) and `wo_O16t_g32_wb` (16:04) lost a
  worker and were cleared through the container and rerun by
  `queue_H.sh` itself; both hold 100 footers.
- **`tools_add_person.py`, first cut (2026-09-29).** The new
  `capture_episode` parameter was named `agents` and shadowed by the
  function's local `agents = Submission.AGENTS`, so the header write
  raised `TypeError: Object of type InductiveGraphPPOAgent is not JSON
  serializable` before the first step on every KEEP run; H-MARL was
  unaffected. Caught by the gate, fixed before any arm ran (the
  parameter is `only_agents`; rerunning the tool repairs the earlier
  state), and the patch's offline check now verifies that no function in
  either harness file reassigns one of its own parameters. Any KEEP trace written between 14:00 and
  14:05 on 2026-09-29 is a gate directory from the failed attempt and
  was overwritten by the rerun.
- **Queue G segfault and the rerun (2026-09-28).** `wo_O1_g8_wb` lost a
  worker at 22:52 (exit 1, SIGSEGV in a worker) and `queue_G.sh` went on
  with the other 24 arms. The partial root-owned directory was removed
  with `sudo rm -rf` and the arm rerun from a clean directory after the
  queue finished; every queue G directory holds 100 footers. Two rerun
  attempts before that were stopped by the shell, because the `sudo rm`
  was inside the `nohup` job and waited for a password in the background:
  `sudo` runs as its own foreground line, and the background job starts
  after it. `queue_G.sh read` prints the exits and a completeness check
  first.
- **The commit history was rewritten on 2026-09-28; `harness_sha` values
  recorded from 2026-09-18 onward no longer resolve.** 
  Session trailers were stripped from 30 commit messages with `git
  filter-branch`, and the two commits that had carried commit-message drafts as
  repo files were rebuilt without them. No file content changed in the rewrite
  beyond the removal of those two drafts. The range covers every commit from
  2026-09-18 onward, beginning with `bin/run: copy red_agents/ into the
  container's CybORG SimpleAgents`; commits before it keep their SHAs, so the
  `d974f69` and `dd22fff` citations in this file still resolve. Everything from
  that boundary forward is renumbered, so a trace captured on or after
  2026-09-18 carries a `harness_sha` that names a commit the current history
  does not contain. `sha-map-2026-09-28.txt` maps old to new, one pair per
  line, oldest first, the boundary commit on the first line. The pre-rewrite
  history is preserved outside the repository in
  `~/cage-history-2026-09-28-pre-cleanup.bundle`.

- **Queue F segfaults and the survey reader's grid (2026-09-27).** Three of
  25 arms lost a worker (`wo_O15a_e2_g32_wb` at 12 episodes,
  `hm_wo_O15r_e10_g32_wb` at 96, `hm_wo_O1_g64_wb` at 63); the partial
  directories were removed (`sudo rm -rf`) and the arms rerun from clean
  directories by `rerun_F.sh`, so every queue F directory holds 100
  footers. `queue_F.sh` skips an arm whose directory already holds 100
  files, which a partial directory with 100 files (96 footers) would
  satisfy; remove partials before any rerun through the queue.
  `tools_signal.py` first took the integer-valued loss signal for a count
  and printed thresholds 1 to 12 in `data/read_svy.txt`; the quantiles
  there are right and the grid rule now applies only to signals whose
  maximum is 12 or less.
- **Directives to a busy agent are dropped by the simulator; every "executed"
  count in the study is an attempt count. Found 2026-09-26.** CC4 actions
  have durations (`Restore` 5 ticks, `Remove` 3, `Analyse` 2, `DeployDecoy`
  2, `ExploitRemoteService` 4 on the red side) and
  `SimulationController.step` sets `actions_in_progress[agent]` only when
  it is empty, with no else branch: an action handed to an agent that is
  mid-action is discarded, the agent executes `Sleep` for each remaining
  tick and its observation carries `IN_PROGRESS`. The harness counted an
  override as executed when the intercept returned it, so the entry above
  that resolved attempts against executions at `d974f69` resolved the
  wrong boundary. Measured from the step records (`tools_dropped.py`: an
  override is executed if an action of its type on its host by its agent
  appears in `get_last_action` within the duration), share of overrides
  the simulator ran and the agents' busy share of ticks:

  | Arm | Busy share | Overrides/ep attempted | executed | share | Points per executed |
  |---|---|---|---|---|---|
  | `wo_O1_g32` (KEEP, Wrecker) | 0.385 | 52.3 | 33.8 | 0.645 | 13.4 |
  | `wo_O10_g32` | 0.377 | 61.2 | 37.7 | 0.616 | 3.4 |
  | `wo_O13_g32` | 0.378 | 45.5 | 27.5 | 0.603 | 5.6 |
  | `o2_g32` (KEEP, stock) | 0.390 | 52.9 | 32.7 | 0.619 | -0.5 |
  | `hm_wo_O1_g32` (H-MARL, 20 ep) | 0.529 | 56.5 | 22.3 | 0.395 | 4.4 |
  | `hm_wo_O10_g32` (20 ep) | 0.526 | 57.6 | 28.2 | 0.490 | 3.6 |
  | `rd_R2_w_O1_g32` (O1 on R2) | 0.185 | 55.9 | 41.2 | 0.737 | 53.6 |
  | `rd_R4tn_w_O1_g32` (O1 on R4tn) | 0.317 | 58.9 | 32.1 | 0.544 | 49.0 |

  The rule defenders booked every proposal as executed (`note()`), so
  they cleared alerts on hosts never restored and counted decoys never
  deployed: R2 alone executed 61 of 76 Restores and 86 of 112 Analyses,
  RT 73 of 96 Restores, R4tn 168 of 607 decoys. Consequences: (1) paired
  scores and everything computed from them stand; (2) "executed",
  "points per override", "decisions per episode", the O2 budget sweep's
  budgets (77 attempts is about 48 executions) and the investigate
  ceiling's "45 decisions" are attempt figures; (3) the O10 latency and
  yield analysis counted attempted looks, a third of which never ran, and
  is to be recomputed over executed looks; (4) every supervised gain is a
  lower bound, by 35 to 60 percent of the intended interventions; (5) the
  decoy reversal under O1 (R4t, R4tn) is this: decoys occupy the agent
  and the supervisor's directive is dropped, 32.1 executed against R2's
  41.2. `tools_add_wait.py` adds `--wait-busy` to both harnesses (a
  directive waits for the agent's next free tick; a rule sleeps while
  busy and reads its observation without booking; the rule's echo test
  becomes host-based so a multi-tick action's result is excluded), the
  header records `wait_busy`, the footer `busy_skips`, and `--rule`
  accepts any `<defender>+<rule>` (the hand-written list lacked `R2d+O1`,
  which cost the 2026-09-26 concurrency test). Without the flag every
  path is unchanged. The rerun set is `queue_B.sh`.
- **Partial directories after a segfault.** A worker `SIGSEGV` leaves the
  arm's directory with whatever episodes had finished (six in
  `rd_RT_WreckerQ32_none_wb`, none in two others) and the pairing tools
  pair on whatever is there, printing `n 6` and nothing louder. Before
  any read, list every directory with fewer than 100 footers (`read_D.sh`
  has the loop) and rerun those; the directories the crashed run created
  are root-owned and need `sudo rm`, though the container overwrites
  them without it. Two-lane segfault count: 5 in 81 arms (B 1/19, C 2/26,
  D 2/36); single lane, none in about 70 the same day.
- **A launch without Docker access writes phantom exit lines.** `queue_D.sh`
  launched once at 23:38 on 2026-09-26 from an environment that could not
  see the rootless Docker socket; every `bin/run` failed in the same
  second and wrote `exit 1` and `queue_D done` to `ft_runs.log`. The
  second launch a minute later was the real one. Read `ft_runs.log` by
  timestamp, and the definitive check is the footer count per directory.
- **Two evaluation lanes at once.** Tested 2026-09-26 (`queue_B.sh`,
  `queue_C.sh`): two `bin/run` containers at six workers each take 4.5 to
  6.2 minutes an arm against 4.6 alone, so a queue runs in 55 to 60 percent
  of its sequential time. One worker `SIGSEGV` in nineteen arms
  (`rd_R2d_w_none_wb`), the same flakiness as the single-container entry
  above; the arm is rerun, not the lane. Training runs still may not
  share the machine.
- **Attempted against waiting directives.** Every arm before 2026-09-26
  22:00 was captured with directives that the simulator dropped when the
  agent was busy (first entry above); they are the "attempted"
  condition and pair only with one another. Arms with `wait_busy: true`
  in the header (directories `_wb`) are the study's condition from here
  and pair only with one another and with unsupervised controls.
- **Trial sizing tools.** `tools_power.py CONTROL ARM...` and
  `tools_power.py --pair A B` resample per-episode paired deltas into
  power curves (paired t and sign test) and the smallest detectable effect
  at each N; `read_power.sh` runs the set reported in RESULTS.md "Sizing
  the human trial" (2026-09-26). `keep_null` does not share episode file
  names with `corpus_v1` (an early capture naming) and cannot be paired.
- **The O2e-family latch was seeded by the reset listing. Resolved
  2026-09-26.** The observation at step 0 names every owned host with a
  substantive entry (71 hosts), and the evidence latch (`O2e`, `O2er`,
  `O2ew`, and the confusion table in RESULTS.md "The evidence latch is
  uninformative") counted it, along with the echo of the agent's own action
  on a host the step before (so a restored host was re-flagged by its own
  Restore result). Every host therefore started flagged, "oldest flag
  first" was dictionary order, and the listing accounted for about a third
  of the flags in the 48 to 52 percent flag rate. Found while building the
  rule defenders, which exclude both. `tools_add_O2f.py` adds `O2f`, `O2fr`
  and `O2fw` with the two exclusions and leaves the originals untouched; a
  scripted stream test shows the original rules' decisions unchanged by
  the patch. Rerun the same day, seven arms (`wo_O2f_b77`, `wo_O2fr_b77`,
  `wo_O2fw_b77`, `wo_O2f_bmax`, `wo_O2f_g32`, `o2f_b77`, `hm_wo_O2f_g32`):
  every KEEP arm moved 20 to 80 points toward zero and stayed inside the
  band (best +34.9 at 54/100), the H-MARL arm went from -150 to -165, and
  the corrected latch is 0.28 precise at 0.48 recall over a third of the
  network (1.4x chance) under both reds. The conclusions stand with the
  corrected figures, which are now the ones cited. `tools_latch_sum.py`
  recomputes the confusion from footers.
- **R4's first version looped on Remove** (`tools_add_R1.py` v3): alerts
  were cleared on Remove and re-fired every `REMOVE_WINDOW`, 1,424 Removes
  in three episodes. Fixed in v3.1 (one Remove per alert, `st["last"][h]
  > st["removed"][h]`). Only the three-episode pilot ran on v3; every
  100-episode arm is v3.1, and the upgrade guard keys on the v3.1 code.
- **R4's comms table is hand-written** from the scenario generator and not
  validated against the live `allowed_subnets` at runtime. `R4p` sits at
  the do-nothing floor under stock (+85 on `arm_sleep`, inside its sd), so
  the blocks are not costing green traffic, but the table has not been
  checked pair by pair.
- **`tools_investigate.py` on a rule defender** attributes the response to
  the investigating agent's Restore or Remove of that host; a supervisor
  O1 Restore is not present in O10 arms, so the attribution is clean, but
  the "never" share counts hosts the rule never saw again, which is a
  property of the alert stream, not of the rule. Conditioning the latency
  on the look's outcome (a `flags_new` at that step) is the next change,
  and `wo_O10_g32` predates the `flags_new` footer (0.00 recorded), so the
  KEEP arm must be rerun under the current harness before that split can
  be made for KEEP.

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
- **H-MARL's time-to-recover metric and the contractor network.**
  `BlueFlatWrapper_CC4.update_time_to_recover_metric` (under their
  `COMPUTE_METRICS = True`) keys a dictionary by blue subnet and raises
  `KeyError: 'contractor_network_subnet'` when a red agent's activity marks
  a contractor host as infected; Trident's `TargetA*` family does this on
  the first step. The metric feeds no reward and nothing the harness
  records. From 2026-09-22 `capture_hmarl.py` wraps the call on the wrapper
  instance to swallow `KeyError`; their code is untouched, and the
  three-episode compat gate reproduces under the guard
  (`hm_compat_gate3m`). The failed arms were rerun; the KEEP O1 arm for the
  same adversary was killed mid-run by the recovery and rerun from a clean
  directory.
- **`pkill -f` patterns.** `\|` is not alternation in `pkill`'s extended
  regex; a pattern written that way matches nothing and reports nothing.
  Use `pkill -f 'a|b'` or kill by PID.

## Continuation redraws, 2026-10-13

Each continuation checkpoint scored under two further policy seeds (`oracle.py --policy-seed 9000` and `9001`, so the policy stream is 9000+ep or 9001+ep on environment seeds 0-99), paired against the same controls as the first draw. `tools_cont.py` gives the decomposition with training seed as the factor. Q32: seed means -52.1, +69.8, -124.2, between-seed sd 98.1, within-seed sd 31.5, between share 0.904, permutation p 0.004. Wrecker: seed means +72.4, +109.3, +25.5, between-seed sd 42.0, within-seed sd 45.3, between share 0.344, permutation p 0.127. `k_kft_Wrecker_s1000_final_w_none_p9000` was rerun alone after its first run lost workers at 62 episodes.

| Directory | Mean | Stdev | Delta vs control | Wins |
|---|---|---|---|---|
| `k_kft_WreckerQ32_s1000_final_WreckerQ32_none_p9000` | -794.66 | 261.47 | -21.6 | 51/100 |
| `k_kft_WreckerQ32_s1000_final_WreckerQ32_none_p9001` | -842.15 | 285.20 | -69.1 | 43/100 |
| `k_kft_WreckerQ32_s1001_final_WreckerQ32_none_p9000` | -688.79 | 225.45 | +84.3 | 60/100 |
| `k_kft_WreckerQ32_s1001_final_WreckerQ32_none_p9001` | -740.75 | 249.37 | +32.3 | 55/100 |
| `k_kft_WreckerQ32_s1002_final_WreckerQ32_none_p9000` | -934.08 | 290.62 | -161.0 | 28/100 |
| `k_kft_WreckerQ32_s1002_final_WreckerQ32_none_p9001` | -865.55 | 240.50 | -92.5 | 38/100 |
| `k_kft_Wrecker_s1000_final_w_none_p9000` | -1084.14 | 291.08 | +31.5 | 52/100 |
| `k_kft_Wrecker_s1000_final_w_none_p9001` | -1025.35 | 270.09 | +90.3 | 61/100 |
| `k_kft_Wrecker_s1001_final_w_none_p9000` | -1036.34 | 362.56 | +79.3 | 61/100 |
| `k_kft_Wrecker_s1001_final_w_none_p9001` | -1034.39 | 351.91 | +81.3 | 62/100 |
| `k_kft_Wrecker_s1002_final_w_none_p9000` | -1140.53 | 366.93 | -24.9 | 50/100 |
| `k_kft_Wrecker_s1002_final_w_none_p9001` | -1043.22 | 325.63 | +72.4 | 54/100 |

## Busy-flag arms, 2026-10-15

Released KEEP weights at the stock adversary (`FiniteStateRedAgent`), 100 episodes on environment seeds 0-99, `oracle.py --rule none --workers 20 --log-policy`, A51. `KEEP_BUSY=shipped` runs the wrapper with its busy check as shipped. `KEEP_BUSY=none` reports every agent as free, so the policy acts every step and CybORG drops what a busy agent is sent. Restores passed per episode are counted from the step records' `policy` field by `tools_busy_charge.py`.

| Directory | KEEP_BUSY | Mean | Stdev | Delta vs control | Wins | Restores passed | To busy agents |
|---|---|---|---|---|---|---|---|
| `keep_released_busy_shipped` | shipped | -187.32 | 61.24 | control | | 77.46 | 0.00 |
| `keep_released_busy_none` | none | -286.90 | 62.62 | -99.6 [-115.5, -82.8] | 8/100 | 180.91 | 102.58 |

The control reproduces `corpus_v1` (-187.32, 61.24) to the digit. Split of the paired difference by `tools_busy_charge.py` (10,000-draw bootstrap over episodes, seed 0): charge -103.45 [-108.22, -98.75], rest +3.87 [-10.55, 19.49].

### Released KEEP with its busy check off, nine adversaries

As the stock pair above, by `run_busy_reds.sh` (A51, 2026-10-16). Each shipped arm reproduces its `red_*` row to the digit. Delta, charge and rest are paired over 100 episodes, 10,000-draw bootstrap over episodes, seed 0 (`tools_busy_charge.py`).

| Adversary | Shipped mean | sd | Check off mean | sd | Delta | Charge | Rest | Restores to busy agents |
|---|---|---|---|---|---|---|---|---|
| Wrecker | -1115.65 | 272.91 | -1270.70 | 308.69 | -155.05 [-232.30, -77.91] | -93.61 [-99.14, -87.76] | -61.44 [-138.78, 16.15] | 95.36 |
| TargetARestricted | -98.52 | 48.61 | -185.88 | 80.92 | -87.36 [-100.48, -74.72] | -79.95 [-87.38, -72.47] | -7.41 [-18.58, 3.12] | 78.35 |
| TargetAOperational | -99.89 | 55.40 | -196.56 | 95.50 | -96.67 [-111.21, -82.63] | -81.44 [-89.36, -73.52] | -15.23 [-26.59, -4.40] | 81.46 |
| TargetA | -104.18 | 55.60 | -185.97 | 83.58 | -81.79 [-94.91, -68.44] | -79.53 [-87.58, -71.68] | -2.26 [-12.83, 8.47] | 79.54 |
| TargetB | -116.25 | 54.19 | -206.86 | 80.87 | -90.61 [-104.65, -77.47] | -85.23 [-92.19, -78.27] | -5.38 [-16.50, 5.46] | 83.99 |
| TargetBRestricted | -117.93 | 63.29 | -213.24 | 86.12 | -95.31 [-110.47, -80.93] | -87.33 [-95.03, -79.57] | -7.98 [-20.07, 3.53] | 86.39 |
| TargetBOperational | -127.31 | 88.17 | -211.39 | 78.90 | -84.08 [-100.63, -65.98] | -83.66 [-90.04, -77.06] | -0.42 [-15.13, 16.28] | 83.71 |
| Combined | -165.87 | 84.76 | -267.09 | 75.76 | -101.22 [-122.14, -79.74] | -101.17 [-105.90, -96.42] | -0.05 [-20.82, 20.67] | 99.85 |
| FailureTracker | -205.66 | 90.26 | -299.18 | 68.01 | -93.52 [-113.64, -72.07] | -99.98 [-104.79, -95.35] | 6.46 [-13.77, 28.39] | 100.41 |

Directories `keep_released_busy_{shipped,none}_FSRedAgent<name>`, logs in `data/evals/`, summary in `data/evals/busy_reds.txt`.

By directory, for the all-arms table (mean and sd over the 100 footers):

| Directory | Mean | sd |
|---|---|---|
| `keep_released_busy_shipped_FSRedAgentWrecker` | -1115.65 | 272.91 |
| `keep_released_busy_none_FSRedAgentWrecker` | -1270.70 | 308.69 |
| `keep_released_busy_shipped_FSRedAgentTargetARestricted` | -98.52 | 48.61 |
| `keep_released_busy_none_FSRedAgentTargetARestricted` | -185.88 | 80.92 |
| `keep_released_busy_shipped_FSRedAgentTargetAOperational` | -99.89 | 55.40 |
| `keep_released_busy_none_FSRedAgentTargetAOperational` | -196.56 | 95.50 |
| `keep_released_busy_shipped_FSRedAgentTargetA` | -104.18 | 55.60 |
| `keep_released_busy_none_FSRedAgentTargetA` | -185.97 | 83.58 |
| `keep_released_busy_shipped_FSRedAgentTargetB` | -116.25 | 54.19 |
| `keep_released_busy_none_FSRedAgentTargetB` | -206.86 | 80.87 |
| `keep_released_busy_shipped_FSRedAgentTargetBRestricted` | -117.93 | 63.29 |
| `keep_released_busy_none_FSRedAgentTargetBRestricted` | -213.24 | 86.12 |
| `keep_released_busy_shipped_FSRedAgentTargetBOperational` | -127.31 | 88.17 |
| `keep_released_busy_none_FSRedAgentTargetBOperational` | -211.39 | 78.90 |
| `keep_released_busy_shipped_FSRedAgentCombined` | -165.87 | 84.76 |
| `keep_released_busy_none_FSRedAgentCombined` | -267.09 | 75.76 |
| `keep_released_busy_shipped_FSRedAgentFailureTracker` | -205.66 | 90.26 |
| `keep_released_busy_none_FSRedAgentFailureTracker` | -299.18 | 68.01 |

### Busy-flag pilot checkpoints

KEEP trained from scratch by `run_keep_pilot.sh`, arm F (check as shipped) and arm N (check off), seeds 4101 to 4104, every hundredth checkpoint scored by `eval_keep_pilot.sh` (100 paired episodes, stock adversary, `--log-policy`). N is scored its own way (`_none`) and with the check on (`_shipped`). Recomputed by `~/papers/paper1/fig/fig_curves.py`.

| Arm | Updates | Seed | F | N check off | N check on | Restores at busy (N) | F minus N (check on) | Wins |
|---|---|---|---|---|---|---|---|---|
| `kbf_F_s4101_u100_shipped`, `kbf_N_s4101_u100_none`, `kbf_N_s4101_u100_shipped` | 100 | 4101 | -2864.72 | -1469.00 | -1210.73 | 227.0 | -1654.0 [-1845.6, -1466.9] | 4/100 |
| `kbf_F_s4102_u100_shipped`, `kbf_N_s4102_u100_none`, `kbf_N_s4102_u100_shipped` | 100 | 4102 | -2140.24 | -1102.42 | -815.98 | 232.2 | -1324.3 [-1444.6, -1207.6] | 3/100 |
| `kbf_F_s4103_u100_shipped`, `kbf_N_s4103_u100_none`, `kbf_N_s4103_u100_shipped` | 100 | 4103 | -2297.17 | -1197.18 | -878.42 | 301.0 | -1418.8 [-1565.0, -1272.6] | 1/100 |
| `kbf_F_s4104_u100_shipped`, `kbf_N_s4104_u100_none`, `kbf_N_s4104_u100_shipped` | 100 | 4104 | -1539.99 | -1376.62 | -1085.62 | 282.8 | -454.4 [-542.3, -367.8] | 14/100 |
| `kbf_F_s4101_u200_shipped`, `kbf_N_s4101_u200_none`, `kbf_N_s4101_u200_shipped` | 200 | 4101 | -809.76 | -1037.22 | -890.65 | 180.4 | +80.9 [2.4, 160.6] | 54/100 |
| `kbf_F_s4102_u200_shipped`, `kbf_N_s4102_u200_none`, `kbf_N_s4102_u200_shipped` | 200 | 4102 | -593.43 | -960.57 | -805.77 | 222.9 | +212.3 [137.5, 290.5] | 67/100 |
| `kbf_F_s4103_u200_shipped`, `kbf_N_s4103_u200_none`, `kbf_N_s4103_u200_shipped` | 200 | 4103 | -796.96 | -970.76 | -891.80 | 161.2 | +94.8 [6.2, 183.6] | 58/100 |
| `kbf_F_s4104_u200_shipped`, `kbf_N_s4104_u200_none`, `kbf_N_s4104_u200_shipped` | 200 | 4104 | -672.80 | -1017.77 | -866.40 | 186.1 | +193.6 [120.2, 268.0] | 75/100 |
| `kbf_F_s4101_u300_shipped`, `kbf_N_s4101_u300_none`, `kbf_N_s4101_u300_shipped` | 300 | 4101 | -546.44 | -831.65 | -645.60 | 170.5 | +99.2 [45.3, 155.7] | 59/100 |
| `kbf_F_s4102_u300_shipped`, `kbf_N_s4102_u300_none`, `kbf_N_s4102_u300_shipped` | 300 | 4102 | -454.01 | -981.40 | -725.28 | 201.2 | +271.3 [200.5, 351.2] | 85/100 |
| `kbf_F_s4103_u300_shipped`, `kbf_N_s4103_u300_none`, `kbf_N_s4103_u300_shipped` | 300 | 4103 | -481.34 | -697.76 | -543.95 | 171.3 | +62.6 [19.8, 106.5] | 61/100 |
| `kbf_F_s4104_u300_shipped`, `kbf_N_s4104_u300_none`, `kbf_N_s4104_u300_shipped` | 300 | 4104 | -673.97 | -1289.66 | -900.08 | 224.5 | +226.1 [138.3, 315.4] | 67/100 |
| `kbf_F_s4101_u400_shipped`, `kbf_N_s4101_u400_none`, `kbf_N_s4101_u400_shipped` | 400 | 4101 | -482.58 | -703.26 | -564.69 | 148.0 | +82.1 [30.0, 132.5] | 61/100 |
| `kbf_F_s4102_u400_shipped`, `kbf_N_s4102_u400_none`, `kbf_N_s4102_u400_shipped` | 400 | 4102 | -354.73 | -823.35 | -605.62 | 173.1 | +250.9 [191.5, 312.1] | 83/100 |
| `kbf_F_s4103_u400_shipped`, `kbf_N_s4103_u400_none`, `kbf_N_s4103_u400_shipped` | 400 | 4103 | -423.98 | -748.42 | -630.28 | 107.6 | +206.3 [136.4, 276.4] | 73/100 |
| `kbf_F_s4104_u400_shipped`, `kbf_N_s4104_u400_none`, `kbf_N_s4104_u400_shipped` | 400 | 4104 | -569.98 | -1160.40 | -1029.95 | 180.6 | +460.0 [375.5, 548.4] | 88/100 |
