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
`restores` as attempts; see Known issues.

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
`evaluation.py` (with the seeding fix) or `capture_hmarl.py`, not `capture.py`.

| Directory | Seeding | Adversary | Mean | Stdev |
|---|---|---|---|---|
| `hmarl_expert_output` | unseeded | FiniteStateRedAgent | -131.99 | 48.51 |
| `hmarl_s0` | seed 0 | FiniteStateRedAgent | -124.11 | 45.80 |
| `hmarl_s1` | seed 1 | FiniteStateRedAgent | -138.31 | 40.97 |
| `hmarl_s2` | seed 2 | FiniteStateRedAgent | -132.10 | 45.40 |
| `hmarl_s3` | seed 3 | FiniteStateRedAgent | -130.86 | 47.45 |
| `hmarl_red_FiniteStateRedAgent` | seed 0 | FiniteStateRedAgent | -124.11 | [ ] |
| `hmarl_red_FSRedAgentWrecker` | seed 0 | FSRedAgentWrecker | -863.86 | [ ] |

**H-MARL Expert reference value: -131.35, 95% CI [-138.25, -124.44]**, four
seeds (`hmarl_s0`–`s3`). Published is -132.63 ± 0.87 (Trident, three-run
spread). The Wrecker comparison in RESULTS.md uses seed 0 (-124.11) because
the Wrecker run is seed 0; the factor is 6.96x on seed 0, 6.58x on the
four-seed mean.

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

All rules wrap `env.action_translator`, intercepting each agent's action before
execution. `translator_calls == 2495` per episode confirms exactly one
interception per agent-step.

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
| `data/hmarl_red_FSRedAgentWrecker` | H-MARL Expert | seed 0 | none | | -863.86 | | | |
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
| `red_FSRedAgentWreckerQ04` | `o1_g32_FSRedAgentWreckerQ04` | Q04 | -325.11 | -250.60 | +74.51 | 71/100 |
| `red_FSRedAgentWreckerQ16` | `o1_g32_FSRedAgentWreckerQ16` | Q16 | -539.17 | -376.15 | +163.02 | 80/100 |
| `red_FSRedAgentWreckerQ32` | `o1_g32_FSRedAgentWreckerQ32` | Q32 | -773.08 | -510.80 | +262.28 | 81/100 |
| `red_FSRedAgentWreckerQ48` | `o1_g32_FSRedAgentWreckerQ48` | Q48 | -928.16 | -579.43 | +348.73 | 93/100 |

Q64 is Wrecker. Stdevs for the control arms are in the footers; the O1 arms:
P10 155.12, P30 199.10, P50 147.04, P70 165.91, P85 203.96, ConvOnly 81.52,
Q04 75.73, Q16 102.11, Q32 128.44, Q48 148.02.

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
  `d974f69`.
  six or twelve; which is not recoverable. Header field pending.