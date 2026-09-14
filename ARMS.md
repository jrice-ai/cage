# Trace arms

Every arm is 100 episodes of 499 steps against `FiniteStateRedAgent`,
environment seeds 0-99, unless noted.

`policy_seed` is `capture.py --policy-seed`; unset means policy sampling tracks
the environment seed. Oracle arms are produced by `scripts/oracle.py --rule`.

**Schema A** (`capture.py`): raw per-agent observation, `truth`, action,
per-agent and step rewards, cumulative reward.
**Schema B** (`oracle.py`): `red_action`, `n_compromised_owned`, action,
rewards, and footer `overrides` / `agreements` / `translator_calls`.

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

Note that `O5`'s inline zone weight uses the earlier `-RIA + LWF` expression and
is deliberately unchanged, so the O5 arms and the budget sweep remain valid
against their original definition.

---

## Oracle arms

| Directory | Rule | n | Mean | Stdev | Overrides/ep |
|---|---|---|---|---|---|
| `oracle_O5b` | none | 100 | -187.32 | 61.24 | 0 |
| `oracle_O6` | O6 | 100 | -201.49 | 168.93 | 270.7 |
| `oracle_O6b` | O6 | 100 | -201.49 | 168.93 | 270.7 |
| `oracle_O5` | O5 | 100 | -238.56 | 48.04 | 77.0 |
| `oracle_O5c` | TBD | 100 | -246.05 | 65.56 | 77.0 |
| `oracle_O8` | O8 | 100 | -253.27 | 197.27 | 154.0 |
| `oracle_O7` | O7 | 100 | -511.95 | 165.48 | |
| `oracle_O1_n100` | O1 | 100 | -520.29 | 93.43 | 401.8 |
| `oracle_O2_n100` | O2 | 100 | -523.19 | 97.98 | 403.2 |
| `oracle_O3_n100` | O3 | 100 | -5803.89 | 1328.90 | 2255.1 |

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

### Smoke arms

Two episodes each, retained for provenance only. Directions were correct in
every case; magnitudes were optimistic by 10 to 17 percent where n=100 values
now exist.

| Directory | Rule | Mean | Stdev | n=100 equivalent |
|---|---|---|---|---|
| `o_smoke` | TBD | -166.50 | 17.68 | |
| `o_smoke_O1` | O1 | -576.50 | 188.80 | -520.29 |
| `o_smoke_O2` | O2 | -541.50 | 140.71 | -523.19 |
| `o_smoke_O3` | O3 | -4963.00 | 431.34 | -5803.89 |
| `o_smoke_O4` | O4 | -260.50 | 102.53 | not run |
| `o_smoke_O5` | O5 | -237.00 | 62.23 | -238.56 |
| `o5b` | TBD | -223.50 | 81.32 | |
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

`o5_b0` reproduces `corpus_v1` and `o5_b77` reproduces `oracle_O5`, both from
the reference machine at a different worker count.

---

## What is established about O8

Four candidate explanations for its per-episode delta were tested and all
returned null:

```
corr(delta, keep baseline score)      -0.272   (null arm shows -0.712)
corr(delta, early red aggression)     -0.057
partial corr(delta, agg | keep)       -0.113
corr(delta, overrides per episode)    -0.052
```

Gains average +67.7 against a null floor of +57.5; losses average -205.1
against a floor of -44.4. **Wins are inside the noise floor, losses are 4.6x
outside it.** Nothing observable predicts which episodes go which way.

Override count ranges 72 to 408 per episode (median 146) against KEEP's 77.1
executed `Restore`/ep. The excess is trajectory divergence — suppression
changes the state, and KEEP subsequently proposes more restores — not double
counting. It does not correlate with outcome.

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
- **Machine provenance.** No arm records which machine captured it. The `o5_b*`
  sweep and the `oracle_O*_n100` arms are from the Alienware; everything else
  is from the Surface.
