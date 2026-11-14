# Robust SINR Cost-Aware Early Screening — V13

This is a **development-locked research code package**, not a claimed positive performance result. It is based on V12's unchanged finite-beam robust SINR model. The primary metric is **paired end-to-end wall-clock runtime relative to CARDINALITY_ONLY**; reduced full solver calls alone are not success.

## Code

`code/cost_aware_v13.py`: development-only policy selection, strict CSI-only early power lower bound, cached robust coefficient screening with LP audit, exhaustive check, checkpoint/resume, group bootstrap and test report.

Reused unchanged mathematical model and benchmark functions: `code/reference_model.py`, `code/ablation_certified.py`, `code/ablation_audit.py`. The development policy set is CARD, EARLY, CACHED and HYBRID. All beam settings are the original ZF/RZF grid.

## Start here

Install: `python -m pip install -r code/requirements.txt`.

Tests: `python -m unittest discover -s tests -v`.

Smoke (synthetic, **not** publication data):

```powershell
python code/cost_aware_v13.py --stage develop --dev-dataset data/smoke.npz --run-id T01 --smoke --limit 4 --repeats 3 --bootstrap 200
python code/cost_aware_v13.py --stage all --dev-dataset data/smoke.npz --test-dataset data/smoke_test.npz --run-id T01 --smoke --limit 4 --repeats 3 --bootstrap 200
```

Official:

```powershell
./scripts/run_v13.ps1 -Development data/development.npz -Test data/new_deepmimo_test.npz -DevelopmentProvenance data/development_provenance.json -TestProvenance data/deepmimo_test_provenance.json -RunId DEEPMIMO_V13
```

For Sionna 3GPP use a **different run-id**, exactly the **same development dataset**, source code and model parameters, and another test dataset and provenance file. The locked policy will be recalculated from unchanged development only; compare the content hash of CP02 across runs. For strict pre-registration, preserve CP02 verbatim from the first run and verify its SHA-256 before running cross-source tests.

**Important**: `groups` should use globally disjoint prefixed identifiers across development and test. Spatial grouping requires actual physical justification; a hash/group name does not prove statistical independence. The program detects exact channel overlap, not near-duplicate channel leakage. Check coordinates and provenance manually.

The dataset NPZ schema is: `H` complex `(N,16,4)` and `groups` `(N,)`, optionally `xyz`, `scenario`. Data must be separately generated and never reused from the v9-v12 development geometry pools for an independent claim. Provenance JSON must contain `source`, `scenario`, `group_definition`, `independence_basis`; the official test must also contain `prior_use: never_seen` or `sealed_before_development`. These assertions are supplied by the dataset producer and require independent verification. Validate Sionna path-delay units, normalization and path loss before interpreting that data.

## CP and resume

- CP01 development runtime and candidates
- CP02 immutable policy lock
- CP03 test preflight with dataset SHA256 and overlap audit
- CP04 repeated end-to-end runtime and call counts
- CP05 paired by geometry
- CP06 numerical GO/STOP
- CP07 SHA256 checksums
- CP08 candidate-level certificate vs exhaustive audit (105 per test geometry)

Each geometry is saved as `outputs/<run-id>/tasks/0000000.json`, written atomically with a task signature. On interruption rerun the same `--stage scan`, then `--stage report`, **without altering code/data/configuration**. The PowerShell runner supports `-SkipDevelopment` to resume without retraining after CP02 exists. Never force a failed policy on test.

## Interpreting the result

- PASS exactness requires no oracle mismatch and no false certificate in CP08.
- A benefit claim requires the selected policy to differ from CARD and the one-sided group-bootstrap lower bound on runtime savings to exceed zero **on each genuinely independent test source**.
- If development rejects all screening methods, CARD is frozen; zero claimed speedup. If test does not confirm benefit, `STOP_NO_RUNTIME_GAIN`.
- There is no statistical outage guarantee, no fully verified interval-arithmetic certificate, and no global optimality over continuously varied complex beamformers.

**Source provenance:** This package derives from the user's V12 validation code. `examples/V13_SMOKE` is synthetic verification only. Its numerical output must not be inserted into the manuscript as an independent result.
