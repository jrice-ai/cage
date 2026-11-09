# cage, the instrument behind "What a CAGE 4 Score Measures"

This repository is the harness, the patches, the analysis tools and the ledger behind the paper *What a CAGE 4 Score Measures: An Audit of a Learned Cyber-Defense Benchmark, Its Reference Defenders, and the Tables Built on Them* (James M. Rice and advisors, Rochester Institute of Technology, 2026). The arXiv identifier is added here in the first commit after posting. The tag `arxiv-v1` is the state every number in the posted paper was computed from.

The traces and checkpoints the paper's numbers are computed from are deposited separately, at https://doi.org/10.5281/zenodo.23681828, in four archives.

| Archive | Contents | Unpack into | sha256 |
|---|---|---|---|
| `traces_arms_arxiv-v1.tar.zst` | the step records of every evaluation arm of the main audit, the 123 that Appendix B of the paper lists and the diagnostic arms `ARMS.md` names, one directory per arm, one JSON-lines file per episode | `data/traces/` | `db2c3d17684180e5d4ca7fb9a7f1f739b5414e62da0e8c4b9b792cd31568f456` |
| `traces_pilot_arxiv-v1.tar.zst` | the step records of the busy-check pilot and its continuation (arms named `kbf_*`) | `data/traces/` | `ece72ca24d17bf688144b2d0276ae9f0209aa8a50f95ecdd0aab9a6f8a9c0fc0` |
| `checkpoints_pilot_arxiv-v1.tar.zst` | the kept checkpoints and resume state of the pilot and continuation training runs | `repos/cage-4-submission/checkpoints/` | `dc2c8219e12a0c2931263be0003c8858039931b04b019e1bfa60c0ba6856c07e` |
| `checkpoints_continuation_arxiv-v1.tar.zst` | the checkpoints of the Wrecker continuation runs of Section 5 | `repos/cage-4-submission/checkpoints/` | in `SHA256SUMS` |
| `run_logs_arxiv-v1.tar.zst` | the training and evaluation logs of the pilot and continuation runs from both machines, with `pilot_runs.log`, which records each run's host, thread count, worker count, code digest and image | `data/` | in `SHA256SUMS` |

`SHA256SUMS` in the deposit lists all four. Check an archive with `sha256sum -c SHA256SUMS` before unpacking.

## What is where

| Path | What it is |
|---|---|
| `bin/run` | runs a command in one of the two images with this directory mounted at `/work`, passing the `KEEP_*` and `HMARL_*` switches through. It expects the clone at `~/cage`. |
| `build/` | the two Dockerfiles (`Dockerfile.keep`, `Dockerfile.marl`) and the patches applied to the upstream repositories before the images are built |
| `scripts/capture.py` | runs KEEP's released policy on paired environment seeds and writes the step record with the agents' raw observations and the simulator's true state |
| `scripts/capture_hmarl.py` | the same for H-MARL Expert, through the authors' evaluation path (`--compat`) or through the supervisory harness |
| `scripts/oracle.py`, `scripts/oracle_rules.py` | the supervisory harness on KEEP, the rules O1 to O15 and the rule defenders, with the delivery switches (`--wait-busy`, `--queue`, `--min-gap`) |
| `red_agents/` | the adversaries the paper runs beyond the stock `FiniteStateRedAgent`. Wrecker and its Pn and Qn ladders are the paper's own (Section 2), and `bin/run` copies every file here into the image's `SimpleAgents` directory at launch |
| `tools_*.py` | the analysis tools. `tools_paired.py` (paired difference, bootstrap interval, wins, sign test), `tools_charge.py` and `tools_busy_charge.py` (the Restore charge and the rest), `tools_dropped.py` (executed against asserted interventions), `tools_cont.py`, `tools_ceiling.py`, `tools_fraction_ci.py`, `tools_latch_sum.py`, `tools_drawspread.py`, `tools_lagcorr.py`, `tools_busy_restores.py`, `tools_pilot_decisions.py` and the rest. Each prints what it computes from a trace directory under `data/traces/` |
| `tools_patch_*.py` | the patch stack on the released code. `tools_patch_keep_busy.py`, `tools_patch_keep_seedmode.py` and `tools_patch_keep_readall.py`, in that order, give KEEP's trainer the switches of Section 6. `tools_patch_hmarl_busy.py` gives H-MARL's wrapper the `HMARL_BUSY=none` switch. `tools_patch_oracle_truth.py` adds `--log-truth` to the harness. Each is idempotent and refuses to run on code it does not recognize |
| `run_keep_pilot.sh`, `eval_keep_pilot.sh`, `pilot_status.sh`, `test_keep_*.sh` | the pilot and continuation of Section 6, their evaluation and their tests |
| `run_busy_reds.sh` | the released KEEP policy with its busy check on and off at the stock adversary and nine others (Section 6.1) |
| `queue_*.sh`, `read_*.sh`, `run_*.sh`, `rerun_F.sh`, `gate_O15.sh`, `pilot_O15.sh`, `svy_O15.sh` | the campaign launchers and readers. Every arm in the paper was launched by one of these, so they are the record of each arm's exact invocation |
| `ARMS.md` | every arm, by name, with its command, its mean and the file that holds it |
| `RESULTS.md` | the dated log of the work, newest first |
| `papers/` | the artifact copy of the paper's analysis layer, without the paper's text. `papers/paper1/ledger.csv` is the ledger, one row per number printed in the paper, with the command that recomputes it. `papers/paper1/fig/` holds the figure and table scripts. `papers/paper1/check_identities.py` tests the arithmetic identities every build must satisfy. The `recompute_*.py` and `means.py` scripts at `papers/` are the criterion, variance and share computations the ledger calls |

Everything under `data/` and `repos/` is ignored by git. The traces go under `data/traces/`, the upstream repositories and the checkpoints under `repos/`.

## Three levels of reproduction

The paper's Appendix A names three levels. They need increasingly more of the environment.

### Level 1, every printed number from the released traces, no container

Clone, unpack the two trace archives into `data/traces/`, and run the recompute from the repository root. It runs every distinct command in the ledger from this directory and checks that each row's stored value appears in that command's output.

```
git clone https://github.com/jrice-ai/cage ~/cage && cd ~/cage && git checkout arxiv-v1
mkdir -p data/traces && tar -I zstd -xf traces_arms_arxiv-v1.tar.zst -C data/traces && tar -I zstd -xf traces_pilot_arxiv-v1.tar.zst -C data/traces
./recompute.sh
python3 papers/paper1/check_identities.py papers/paper1/ledger.csv
```

The ledger's commands name the analysis layer by its path on the authors' machine, `~/papers`, so `recompute.sh` runs the check with `HOME` pointed at a scratch directory that links `papers/` there. Nothing is written outside the repository. On a laptop the full recompute takes tens of minutes, most of it the pilot arms. Ten rows, the hyperparameters read from the released checkpoints (keys `keep*` and `trident*`, which run through `bin/run`), need the level-2 image and report as not found without it. `check_identities.py` reports the arithmetic identities (cost equals charge plus rest for every split, the four-draw and four-seed intervals against their means and sds, the H-MARL mask-off pair's zero rest). The figure and table scripts under `papers/paper1/fig/` regenerate the paper's figures and tables from the same traces with `CAGE=~/cage python3 papers/paper1/fig/fig_curves.py` and likewise for `fig_drop.py`, `fig_noise.py`, `make_tables.py`, `make_busyreds.py` and `make_arms.py`.

### Level 2, a fresh evaluation of any arm

This needs the two images, the upstream repositories at their pinned revisions, and the released checkpoints.

Clone the three upstream repositories into `repos/` at the revisions the paper was computed from, which are the revisions Table 12 of the paper prints.

| Repository | Revision |
|---|---|
| `cage-challenge/cage-challenge-4` | `8c3c50ca54b1` |
| `cybermonic/cage-4-submission` (KEEP, with its five released checkpoints under `weights/`) | `2afd652d80ce` |
| `adityavs14/Hierarchical-MARL` (H-MARL Expert, with its released checkpoint) | `6fe960f5931f` |

Apply the patches in `build/` to the repositories they name (`git apply` from inside each clone), then build the two images from the repository root. The two defenders' dependency sets do not coexist, which is why there are two.

```
docker build -f build/Dockerfile.keep -t cage-keep:dev .
docker build -f build/Dockerfile.marl -t cage-hmarl:dev .
```

The checkpoint digests the paper reports are an md5 over the sorted per-file md5s, `55fb3e7f46540eeea63230b149e1744e` for KEEP's five files and `fd9e9172fd56b723fedca72ce0e78a16` for H-MARL's fifteen policy files and `algorithm_state.pkl`. Check them before running anything.

Then an arm is one command through `bin/run`. The released KEEP policy on the hundred paired environment seeds at the stock adversary, with the true state recorded, which is the `corpus_v1` arm,

```
bin/run cage-keep:dev python3 /work/scripts/capture.py --episodes 100 --base-seed 0 --red FiniteStateRedAgent --out /work/data/traces/corpus_v1 --workers 4
```

H-MARL Expert through the authors' evaluation path, which is the reproduction interval's arm,

```
bin/run cage-hmarl:dev python3 /work/scripts/capture_hmarl.py --rule none --episodes 100 --base-seed 0 --compat --out /work/data/traces/hmarl_s0
```

and a supervised arm, O1 held until the agent is idle with a gap of 32 steps on KEEP,

```
bin/run cage-keep:dev python3 /work/scripts/oracle.py --rule O1 --min-gap 32 --wait-busy --episodes 100 --out /work/data/traces/so_O1_g32_wb
```

The exact invocation of every arm in the paper is in the `queue_*.sh` and `run_*.sh` scripts and recorded in `ARMS.md`, and a rerun on the same seeds reproduces a released arm to the digit, as the H-MARL arm of Section 6.1, captured on a second machine from a copy of the image, reproduces its control. The busy-check ablations of Section 6.1 are `run_busy_reds.sh` for KEEP and, for H-MARL, `tools_patch_hmarl_busy.py` followed by `capture_hmarl.py` with `HMARL_BUSY=none` and `--log-policy`.

### Level 3, retraining

This needs the patched trainer and days of CPU per seed. Apply the three KEEP trainer patches in order and run their tests, which take a few minutes each and exercise every switch,

```
python3 tools_patch_keep_busy.py && python3 tools_patch_keep_seedmode.py && python3 tools_patch_keep_readall.py
./test_keep_busy.sh && ./test_keep_seedmode.sh && ./test_keep_readall.sh
```

then launch a pilot arm. `F` trains with the busy check as shipped, `N` without it, `S` is the fixed-layout seeded control and `R` the read-all control. An update is five episodes (twenty-five for `R`), kept checkpoints land every hundred updates under `repos/cage-4-submission/checkpoints/`, and the `resume` argument continues a run from its state file.

```
nohup ./run_keep_pilot.sh F 4101 400 0-17 > /dev/null 2>&1 &
./pilot_status.sh
./eval_keep_pilot.sh kbf_F_s4101 400 shipped 6
```

`eval_keep_pilot.sh <tag> <update> [busy] [workers] [policy seed]` scores a kept checkpoint on the hundred paired seeds, with the check as trained or crossed, and with a policy seed for the reseeded draws of the four-draw estimates. A pilot run is reproducible from its seed up to the learner's thread count, which moves the weights in their seventh decimal, so a rerun with a different `cpus` argument matches the released checkpoints closely and not bit for bit. The run configurations, thread counts, hosts and code digests of every run in the paper are in `pilot_runs.log` in the deposit's run-logs archive and in `ARMS.md`.

## Citing

Until the arXiv identifier is in, cite the paper by title and the artifact by its tag and the deposit's DOI. The paper's own bibliography lists the upstream repositories and checkpoints it depends on with their revisions.
