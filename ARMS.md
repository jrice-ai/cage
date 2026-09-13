# Trace arms

Every arm is 100 episodes of 499 steps against `FiniteStateRedAgent`,
environment seeds 0-99, unless noted. `policy_seed` is the `--policy-seed`
value; unset means it tracks the environment seed.

Schema A = `capture.py`: raw per-agent observation, `truth`, action, rewards.
Schema B = oracle harness: `red_action`, `n_compromised_owned`, action, rewards.
Neither is a superset. See RESULTS.md, "Schema divergence between capture paths".

## Reference arms

| Directory | Policy | policy_seed | Schema | n | Mean | Stdev | Notes |
|---|---|---|---|---|---|---|---|
| `corpus_v1` | KEEP sampled | unset | A | 100 | -187.32 | 61.24 | First corpus. One sampling draw, not canonical. |
| `arm_keep` | KEEP sampled | unset | A | 100 | -187.32 | 61.24 | Byte-identical duplicate of `corpus_v1`. Delete or keep as a checksum. |
| `keep_null` | KEEP sampled | 9000 | A | 100 | -196.09 | 51.96 | Placebo arm. Same envs, different sampling. |
| `keep_null_9001` | KEEP sampled | 9001 | A | 100 | -198.44 | 83.33 | |
| `keep_null_9002` | KEEP sampled | 9002 | A | 100 | -183.51 | 49.40 | |

KEEP reference: grand mean **-191.34**, 95% CI [-199.66, -183.02], 4 seeds.

## Baseline ladder

| Directory | Policy | Schema | n | Mean | Stdev | Notes |
|---|---|---|---|---|---|---|
| `arm_keep_greedy` | KEEP argmax | A | 100 | -552.2 | 343.7 | Deterministic. All variance is situation. |
| `arm_analyse` | Always Analyse | A | 100 | -6592.7 | 1340.5 | Acts without targeting logic. |
| `arm_sleep` | Always Sleep | A | 100 | ? | ? | True do-nothing floor. **Reported -6592.68, same as arm_analyse — unresolved, see below.** |
| `arm_monitor` | ? | ? | ? | ? | ? | **Undocumented — needs a line.** |

A random-policy arm was attempted and abandoned: KEEP's action space is not
uniformly samplable (`wrapper/graph_wrapper.py:40`, `IndexError` on
`a_id // MAX_ACTIONS`).

## Oracle variants

Rule descriptions below are **incomplete**. Fill from the oracle script's git
history or from memory before the details are lost.

| Directory | Rule | Schema | n | Mean | Stdev | Overrides/ep | Notes |
|---|---|---|---|---|---|---|---|
| `o_smoke` | ? | B | 2 | -166.50 | 17.68 | | Smoke test |
| `o_smoke_O1` | ? | B | 2 | -576.50 | 188.80 | | |
| `o_smoke_O2` | ? | B | 2 | -541.50 | 140.71 | | |
| `o_smoke_O3` | ? | B | 2 | -4963.00 | 431.34 | | |
| `o_smoke_O4` | ? | B | 2 | -260.50 | 102.53 | | |
| `o_smoke_O5` | ? | B | 2 | -237.00 | 62.23 | | |
| `o5b` | ? | B | 2 | -223.50 | 81.32 | | |
| `oracle_O5` | ? | B | 100 | -238.56 | 48.04 | | Stdev inside null range; not anomalous. |
| `oracle_O5b` | ? | B | 100 | -187.32 | 61.24 | 0 | Rule never fired or always agreed. Valid k=0 control. |
| `oracle_O5c` | ? | B | 100 | -246.05 | 65.56 | | |
| `oracle_O6` | ? | B | 100 | -201.49 | 168.93 | | |
| `oracle_O6b` | ? | B | 100 | -201.49 | 168.93 | | Rerun of O6; differs from it only in footer `wall_seconds`. |
| `oracle_O7` | ? | B | 100 | -511.95 | 165.48 | | |
| `oracle_O8` | ? | B | 100 | -253.27 | 197.27 | 154.0 | 35.6 agreements/ep. 81% override rate. |

## Interpretation floor

Identical policies differing only in sampling seed produce deltas up to 26
points and win rates up to 66/100. An arm reporting less than roughly 25 points
of mean delta, or under roughly 66 percent of episodes improved, has reported
nothing.

## Known issues

- **Ownership.** All directories captured before `--user` was adopted are
  root-owned. `sudo chown -R $(id -u):$(id -g) ~/cage/data/traces`.
- **`arm_sleep` mean.** Reported -6592.68 both before and after the policy was
  corrected from always-Analyse to true Sleep, though a 2-episode check gave
  -7904 and an action counter confirmed all-Sleep. Unresolved.
- **`arm_monitor`.** Present on disk, not documented anywhere.
- **Episode id parsing.** Never use `f.split('ep_')[1]`; any directory name
  containing `ep_` collapses all episodes to one key silently. Use
  `os.path.basename(f)[3:-6]`.

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
| `arm_analyse` | Always Analyse | A | -6592.7 | 1340.5 | Acts without targeting logic. |
| `arm_sleep` | Always Sleep | A | TBD | TBD | See known issues. |
| `arm_monitor` | TBD | TBD | TBD | TBD | Undocumented. |

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

---

## Oracle arms

Smoke tests are n=2 and carry no information — `o_smoke_O5` at -237.00 agreeing
with `oracle_O5` at -238.56 is coincidence, not validation.

| Directory | Rule | n | Mean | Stdev | Overrides/ep |
|---|---|---|---|---|---|
| `o_smoke` | TBD | 2 | -166.50 | 17.68 | |
| `o_smoke_O1` | O1 | 2 | -576.50 | 188.80 | |
| `o_smoke_O2` | O2 | 2 | -541.50 | 140.71 | |
| `o_smoke_O3` | O3 | 2 | -4963.00 | 431.34 | |
| `o_smoke_O4` | O4 | 2 | -260.50 | 102.53 | |
| `o_smoke_O5` | O5 | 2 | -237.00 | 62.23 | |
| `o5b` | TBD | 2 | -223.50 | 81.32 | |
| `oracle_O5` | O5 | 100 | -238.56 | 48.04 | |
| `oracle_O5b` | none | 100 | -187.32 | 61.24 | 0 |
| `oracle_O5c` | TBD | 100 | -246.05 | 65.56 | |
| `oracle_O6` | O6 | 100 | -201.49 | 168.93 | |
| `oracle_O6b` | O6 | 100 | -201.49 | 168.93 | |
| `oracle_O7` | O7 | 100 | -511.95 | 165.48 | |
| `oracle_O8` | O8 | 100 | -253.27 | 197.27 | 154.0 |

The `rule` field is in every header from `oracle.py`; TBD rows can be filled
with `python3 -c "import json; print(json.loads(open('DIR/ep_00000.jsonl').readline()))"`.
`budget` was added to the header after these captures, so O5 arms do not record
which budget produced them.

`oracle_O6` and `oracle_O6b` differ only in footer `wall_seconds`; O6b is a
rerun. `oracle_O5b` was captured with `--rule none` and is a valid zero-
intervention control.

`oracle_O5`'s stdev of 48.04 is inside the null range (49.40 to 83.33) and is
not anomalous. Its percentiles are uniformly worse than `corpus_v1` above the
minimum: min -478, p10 -288, med -238, max -155.

### What is established about O8

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

- **Ownership.** Directories captured before `--user` was adopted are
  root-owned. `sudo chown -R $(id -u):$(id -g) ~/cage/data/traces`.
- **`arm_sleep` mean.** Reported -6592.68 both before and after the policy was
  corrected from always-Analyse to true Sleep, though a two-episode check gave
  -7904 and an action counter confirmed all-Sleep. Unresolved.
- **`arm_monitor`.** Present on disk, undocumented.
- **Episode id parsing.** Never `f.split('ep_')[1]` — any directory whose name
  contains `ep_` collapses all episodes to one key silently. Use
  `os.path.basename(f)[3:-6]`.
- **Budget provenance.** O5 arms predate the `budget` header field.
