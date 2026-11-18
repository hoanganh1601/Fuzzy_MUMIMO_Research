# V14 — Computational limits and cost-aware screening

**Goal:** Evaluate whether a pre-registered cost-aware ON/OFF decision reduces **end-to-end runtime** against CARDINALITY_ONLY on genuinely untouched MU-MIMO channels. This is a follow-up to V13, not a new SINR model. No improvement is assumed.

## Structure

- `code/cost_limits_v14.py`: V14 protocol and checkpointed runs.
- `code/cost_aware_v13.py`, `reference_model.py`, `ablation_certified.py`, `ablation_audit.py`: retained V13 algorithms and independent finite-codebook oracle.
- `docs/GUIDE_COST_LIMITS_IEEE_VI.tex` and `.pdf`: IEEE one-column Vietnamese guide.
- `scripts/run_v14.ps1`: PowerShell full-stage runner, with reuse of frozen CP03 for the second channel source.
- `data/*_TEMPLATE.json`: provenance templates. `smoke.npz` and `smoke_test.npz` are **synthetic only**.
- `examples/V14_SMOKE*`: smoke-test outputs. **Do not cite as DeepMIMO or 3GPP results.**
- `tests/`: unit tests.

## Required data

`.npz` contains complex `H` with shape `(N,M,4)` and `groups` length N. `groups` must reflect genuinely distinct spatial areas or topology drops. Metadata must justify independence; separate group IDs alone are insufficient. Avoid every dataset previously inspected in V9–V13 if claiming *independent* validation. For 3GPP additionally preserve the generator configuration, Sionna version, channel normalization, delay units, path loss and drop seeds.

## Install, test

```powershell
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
```

## DeepMIMO run — commands from package root

```powershell
$dev = 'data/development.npz'
$test = 'data/new_deepmimo_test.npz'
$run = 'DM_V14'
python code/cost_limits_v14.py --stage profile --development $dev --run-id $run
python code/cost_limits_v14.py --stage select --development $dev --run-id $run
python code/cost_limits_v14.py --stage preflight --development $dev --test $test --test-provenance data/deepmimo_provenance.json --run-id $run
python code/cost_limits_v14.py --stage scan --development $dev --test $test --test-provenance data/deepmimo_provenance.json --run-id $run
python code/cost_limits_v14.py --stage report --development $dev --test $test --test-provenance data/deepmimo_provenance.json --run-id $run
```

The `development-provenance` argument is available for recording data source in the PowerShell wrapper; the test provenance is mandatory for official evaluation. Set `prior_use` on untouched test to `never_seen` or `sealed_before_development`; this is an auditable declaration, not a mathematical proof. Do not fake provenance.

## 3GPP independent run — *reuse* DeepMIMO lock

```powershell
$dev='data/development.npz'
$gpp='data/3gpp_independent.npz'
$lock='outputs/DM_V14/CP03_locked_rule.json'
$run='GPP_V14'
python code/cost_limits_v14.py --stage preflight --development $dev --test $gpp --test-provenance data/3gpp_provenance.json --run-id $run --lock-from $lock
python code/cost_limits_v14.py --stage scan --development $dev --test $gpp --test-provenance data/3gpp_provenance.json --run-id $run --lock-from $lock
python code/cost_limits_v14.py --stage report --development $dev --test $gpp --test-provenance data/3gpp_provenance.json --run-id $run --lock-from $lock
```

The complete PowerShell script automates these stages. To reuse the lock call with `-LockFrom` and a **new run-id**. You must use the same model settings and code hashes for both runs.

## Outputs

| Checkpoint | Content |
|---|---|
| CP00 | `CP00_manifest.json`: code/data/parameter fingerprint |
| CP01 | `CP01_development_profile.csv`: profiled runtime for CARD, EARLY, CACHED, HYBRID; `CP01_candidate_cost.csv`: full per-candidate power-solve cost and rejection cost |
| CP02 | `CP02_rule_search.csv`: simple cost/feature threshold rules evaluated on development-fit groups |
| CP03 | `CP03_locked_rule.json`: fit-selected rule, holdout gate, final fallback |
| CP04 | `CP04_preflight.json`: test hash, provenance, overlap checks |
| CP05 | `CP05_runtime_repetitions.csv`: end-to-end repeated runtime, switching decisions, substage times |
| CP06 | `CP06_oracle_audit.csv`, `CP06_candidate_certificates.csv`: 105 finite candidates per geometry, false rejection count |
| CP07 | `CP07_paired_geometry.csv`: CARD vs adaptive decision per geometry |
| CP08 | `CP08_decision.json`: GO/STOP with group bootstrap 95% CI |
| CP09 | `CP09_SHA256.csv`: output integrity |

`profile_tasks/` and `tasks/` contain individually committed per-geometry JSON checkpoints. Every write is atomic with fsync. Restart the interrupted stage with unchanged code, input, flags and `run-id`. A mismatch fails instead of silently reusing data. If files or settings change, use a new run ID.

## Method and decision

A fixed CSI radius and the **same 105 ZF/RZF subset candidates** are used in each mode. The learned switch uses only cheap pre-beam statistics of **estimated CSI** (`early_ratio` and `norm_spread`). It decides CARD or EARLY/CACHED/HYBRID. All feature selection overhead is charged to the adaptive strategy at test. Candidate profiling includes all power solvers, including fast infeasible cases; it is diagnostic and **never used as test-time information**.

Development groups are divided into fit (60%) and validation (40%). The single best rule from fit is screened once on validation using a group-level bootstrap lower confidence bound `> min_gain_ms=0.1`. On failure, lock CARD. The test is not used to tune thresholds or rule classes. A claim of runtime benefit additionally requires positive independent test group-bootstrap bound above the same margin, preserved exhaustive outcomes and no false certificate. Both new DeepMIMO and new 3GPP should separately pass.

**Scientific caveats:** A performance model selected from the same finite development family can still overfit. Bootstrap group CIs assume groups constitute meaningful resampling units; provenance must support that. End-to-end timing depends on BLAS threading, CPU clocks, warm-up, OS activity and solver versions; log all of these externally with the run. A rule which locks to CARD is a valid negative result but not acceleration. The finite-codebook oracle is not globally optimal continuous beamforming.

## Smoke test (not for manuscript)

```powershell
python code/cost_limits_v14.py --stage all --development data/smoke.npz --test data/smoke_test.npz --run-id V14_SMOKE --out examples --smoke --limit 8 --repeats 3 --bootstrap 150 --min-groups 3
```

Smoke test outputs are not stable benchmarking evidence; short timings vary between runs.
