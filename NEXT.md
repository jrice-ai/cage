# CAGE 4 Work, Status and Pathways

Written at the end of the first working session. Companion to RESULTS.md, which
records what was found. This file records where things stand and what could
come next.

## Status

### Accomplished

Started with no CAGE installation. Ended with a pinned reproducible container, a
reproduced published baseline, a working trace logger, and a 300 episode
dataset across three policy arms.

The go/no-go cleared. KEEP reproduces at -196.06 against a published -193.68,
exactly on rerun. The whole program rested on this and it holds.

Artifacts in place

| Artifact | Location | State |
|---|---|---|
| Container definition | `build/Dockerfile.keep` | Working, pinned |
| H-MARL container | `build/Dockerfile.marl` | Written, not yet built |
| Dependency lock | `data/requirements-keep.lock` | Captured |
| Trace logger | `scripts/capture.py` | Working, parallel verified |
| Action analysis | `scripts/analyse_actions.py` | Working |
| Three policy corpus | `data/traces/arm_{keep,keep_greedy,sleep}` | 100 episodes each |
| Findings record | `RESULTS.md` | Current |

### Found

**Four defects in published tooling.** Output files never written in
`evaluation.py`. Policy sampling unseeded, so identical commands return
different answers. A parallel path that returns roughly 12 distinct episodes
when asked for 100. And `get_reward_breakdown` broken in CC4 itself. Plus two
dependency pins that no repository declares, without which nothing imports.

**Action selection mode is worth 2.8x and is undocumented.** Sampling scores
-196, greedy scores -552. Explained mechanistically. Repeat rate doubles, host
coverage halves, and the `Remove` action drops from 10,353 uses to 148.

**One defect of our own, caught by cross checking.** A cached simulator state
reference froze mission phase and red ground truth across an entire corpus
while producing well formed plausible output. Only checking phase against the
known mission structure caught it.

**A characterization of the environment that has not been published.** Reward
measures defensive quality across a 35x range. Better policies compress
variance rather than shifting level, a 22x spread in standard deviation across
three policies. The mechanism is impact suppression, with KEEP cutting red
damage actions by 78 percent against doing nothing. Defensive value scales with
threat.

### The constraint this creates

KEEP is close to a ceiling. Supervising it means trying to improve on a strong
performer with a standard deviation of 61 on a mean of -187 and a best observed
episode of -113.

That is exactly the condition under which the meta analysis predicts human AI
combinations underperform. Running the human arm against converged KEEP is
close to predicting the null in advance.

The implication is that the human arm wants a degraded policy, which makes the
competence checkpoint pool load bearing rather than optional.

## Pathways

Four directions. They are genuinely different in what they buy, not stages of
one plan.

### 1. Consolidate and publish the E material

**What.** A tools or reproducibility paper. Four defects, quantified costs, a
validated instrument, and a characterization of what the environment measures.
The contribution framed as a seed and configuration disclosure standard, with
the findings as evidence.

**Scope.** Perhaps six weeks. Most of the content exists in RESULTS.md. The
work is framing, a related work section, and a clean set of figures.

**For it.** Nearly done already. Waiting risks someone else finding the same
things. A published artifact makes later requests for weights, data, or
collaboration substantially easier to make.

**Against it.** Pathway E was explicitly scoped as the instrument that A
through D depend on, not as a peer of them. Six weeks writing is six weeks not
spent on the research question.

**Right when.** A citable output is wanted before Pathway B clears, or the
defect reports to Cybermonic prompt a conversation worth formalizing.

**First step.** Send the defect reports. They cost an hour and should go out
regardless of what else happens.

### 2. Build the competence checkpoint pool

**What.** Train KEEP from scratch, saving checkpoints at intervals, producing a
graded set of policies spanning from near random to converged. Roughly 25
million environment steps per seed, since KEEP converges after about 50k
episodes.

**Scope.** The largest single time investment on this list. Weeks, and training
runs fail in ways that consume more.

**For it.** The headroom finding makes this necessary for the human arm to mean
anything. It also forces the PowerEdge to be properly configured, which has to
happen eventually. And it produces the teammate competence manipulation that
the Team Defense Game design depends on.

**Against it.** Reimplementing someone else's training loop. High risk of long
silent failures. And the target competence level is currently a guess.

**Right when.** Committed to running the human arm against a degraded policy,
and the difficulty target is known.

**Dependency.** Pathway 4 should come first, since it determines where in the
competence range to aim.

### 3. Stratification and the replay harness

**What.** Compute episode difficulty measures over the corpus, build matched
stimulus sets, then write the player that reads traces and drives a display at
a controlled clock.

**Scope.** Several weeks. Red aggression is already a computable difficulty
score, so the stratification half is partly done.

**For it.** Closest to the actual research question. Produces something a
person can look at. First work in the programme that is not instrumentation.

**Against it.** Designing a display before settling what the human is able to
do. That decision was deliberately placed after the environment work for good
reason.

**Right when.** Momentum toward Pathway A is wanted while Pathway B is blocked.

### 4. The oracle ceiling condition

**What.** Run a supervisor with full Tier 3 simulator ground truth against a
small stimulus set. Bound the achievable gain before any participant sees
anything.

**Scope.** Smallest of the four. Needs a minimal display and a control surface,
so not free, but days rather than weeks.

**For it.** Cheapest experiment with the highest information value in the whole
programme. If an oracle cannot beat KEEP, the human arm against KEEP is
hopeless and months are saved. If an oracle can, the available headroom has
been measured rather than guessed. Either answer reshapes everything
downstream.

**Against it.** Requires enough of a display and control surface to be usable,
so it is not zero cost. And a single person acting as the oracle is a pilot
rather than a result.

**Right when.** Now. It is the question the other three are downstream of.

## Recommended ordering

**4, then 2, with 1 running in the background.**

The oracle condition measures how much headroom exists against a given policy.
That number determines whether the checkpoint pool is necessary at all, and if
so, where in the competence range to target it. Building the pool first risks
training at the wrong difficulty.

Pathway 1 needs no scheduling. The defect reports go out this week. Whether
they grow into a paper can be decided later.

Pathway 3 is the one to defer, since the display question is downstream of
knowing what the human can usefully do, which is what the oracle condition
establishes.

## Open items carried forward

1. Build the H-MARL image and reproduce its baseline. Second baseline, and the
   `COMPUTE_METRICS` flag in that repository is worth reading before inventing
   metrics.
2. Report the `--distribute` correlation defect to Cybermonic, and the
   `get_reward_breakdown` bug to the CAGE maintainers.
3. Fix the parallel seeding in `evaluation.py` and quantify the parallel versus
   serial gap with a matched run.
4. Verify the image, the -196.06 figure, and trace determinism on the Alienware
   and the PowerEdge. Three independent machines is a portability claim most
   release papers cannot make.
5. Confirm whether `OSDistribution: KALI` is a deliberate compromise marker or
   a scenario authoring artifact.
6. Design the accumulation layer. The environment emits events and forgets, so
   a human facing view must maintain state that neither CybORG nor the agents
   maintain. Display design alone cannot solve this.
7. Test whether blue influences which states red occupies, rather than only how
   much presence red holds. The current claim that red aggression is
   independent of blue rests on aggregate correlation, not mechanism.

## A note on priorities

Pathway B remains blocked on advisor feedback and is still the fastest route to
a first submission. It requires none of the infrastructure built here, since it
runs on synthetic topologies without agents.

This work has been good use of the wait. It should not become the thing that
displaces B when the block clears.
