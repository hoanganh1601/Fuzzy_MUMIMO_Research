# Fuzzy MU-MIMO margin study — independent research pilot

**Research note + guide:** `docs/RESEARCH_AND_GUIDE_IEEE_VI.tex`, `.pdf` (IEEEtran one column, Vietnamese).

## Scope
- `code/experiment.py`: shared fixed-RZF robust power allocation on the slab uncertainty set |e_k^H v_j| <= r_k, 9-rule zero-order Sugeno, Gaussian (Bonferroni slab radius q = sqrt(ln(K^2/eps)), analytic, not tuned), fixed and threshold baselines tuned on validation with their own 6-candidate grids. Grouped train/validation/test; development on validation (train reserved for future learned policies). Frozen selection; test outputs; per-test-channel JSON checkpoints, SHA-256 manifest. Default pilot sizes are not enough to substantiate rare-outage claims.
- `code/generate_data.py`: DEMO synthetic, simplified **UMi-inspired** generator (NOT standards-compliant 3GPP), and DeepMIMO v4 loading. Download and ray tracing data are not embedded.
- `code/import_3gpp.py`: strict channel-array import for an **external genuine 3GPP TR 38.901** channel generator (Sionna UMi recommended). Source provenance and groups must be independently documented. This package DOES NOT bundle a tested Sionna 3GPP generator.
- `data/*smoke.npz`, `outputs/*`: **smoke test only**; these are not publication results.

## Setup
```bash
python -m pip install -r code/requirements.txt
python code/generate_data.py --source synthetic --n 360 --output data/smoke.npz
python code/experiment.py --stage all --dataset data/smoke.npz --run-id smoke --limit 5 --n-mc 20
python tests/test_invariants.py     # 9 correctness tests (bound validity, LP optimality, coverage, resume)
```
Noise: `--noise` [W]; if omitted, the dataset field `noise_w` is used (written by `umi_inspired`, thermal noise for 20 MHz, NF 9 dB), else 1e-9 W. Set it explicitly for DeepMIMO/3GPP (`import_3gpp.py --noise-w`).

## DeepMIMO dataset
```bash
python -m pip install deepmimo
python code/generate_data.py --source deepmimo --scenario asu_campus_3p5 --output data/deepmimo.npz
python code/experiment.py --stage preflight --dataset data/deepmimo.npz --run-id DM01
python code/experiment.py --stage develop --dataset data/deepmimo.npz --run-id DM01
python code/experiment.py --stage freeze --dataset data/deepmimo.npz --run-id DM01
python code/experiment.py --stage test --dataset data/deepmimo.npz --run-id DM01
python code/experiment.py --stage report --dataset data/deepmimo.npz --run-id DM01
```
IMPORTANT: the example DeepMIMO adapter groups *ordered user indices* rather than verified disjoint geographic regions. Confirm ordering against positions, or replace groups with spatially defined blocks before accepting any cross-region generalization conclusions. Multiuser tuples are consecutive valid users; determine actual simultaneity/spacing and exclude pathological combinations before publication.

## Genuine 3GPP external holdout
Use Sionna 3GPP TR 38.901, model UMi; export an `.npz` with complex `H[N,M,K]`, integer `groups[N]` representing independent geometry/topology blocks, preserving actual physical coefficients.
```bash
python code/import_3gpp.py --input path_to_sionna_export.npz --output data/3gpp.npz --source-note 'Sionna 3GPP TR 38.901 UMi with recorded version and parameters'
python code/experiment.py --stage test --dataset data/3gpp.npz --run-id UMI01 --frozen-from outputs/DM01/cp02_frozen.json
python code/experiment.py --stage report --dataset data/3gpp.npz --run-id UMI01 --frozen-from outputs/DM01/cp02_frozen.json
```
**No training or selection on the 3GPP test set.** If the 3GPP path is not available, DO NOT describe `umi_inspired` as a 3GPP validation.

## Outputs / checkpoints
- `cp00_manifest.json`: code/dataset/settings hashes; rejects mismatched restarts.
- `cp01_candidates.json`: validation candidate outcomes.
- `cp02_frozen.json`: frozen parameters and selection rule.
- `tasks/test/NNNNNNN.json`: independent checkpoint per test MU-MIMO channel; atomic fsync+replace, completed tasks reused.
- `cp03_test_geometry.csv`: each method/geometry: group, CSI features, margin q, feasibility and solver reason, power, MC outage, `actual_fail` (dataset channel), solver and total runtime.
- `cp04_test_summary.csv`: per-method aggregate: feasible rate, pooled conditional outage (Wilson + group bootstrap), effective failure (infeasible = 1, group bootstrap), actual-channel failure rate, mean power, mean total runtime.
- `cp05_scope.json`: dataset/sample counts, noise power, q_gauss, infeasibility reasons and limitations.
- `cp06_common_set_power.csv`: per-geometry power ratio vs gaussian (dB) on the set feasible for all methods, group-bootstrap CI.

## Scientific limitations
This is a pilot framework, not an already-validated paper result. The error perturbations of the observed estimated CSI are synthetic, not channel-estimator residuals. Mean test outage is not a certified chance constraint; confidence intervals, group-level bootstrap, a properly spatial split, accurate Sionna 3GPP export and latency profiling are necessary before journal claims. `--limit` is only for smoke tests. The Gaussian margin is an illustrative conservative parameter, not an exact joint-outage guarantee. Channel scale and receiver noise must be made physically consistent across datasets before comparing absolute watts.

## Revision R1 (2026-10-19)
See `docs/CODE_REVIEW_R1_VI.md`. Runs and frozen files from R0 are not compatible (signature and frozen format changed): use new run-ids and rerun develop/freeze.
