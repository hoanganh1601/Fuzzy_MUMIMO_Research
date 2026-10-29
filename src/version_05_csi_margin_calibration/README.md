# CSI uncertainty-margin calibration for robust MU-MIMO downlink

## Status
- Self-contained program and XeLaTeX IEEE one-column Vietnamese guide.
- Preflight/development/calibration/freeze/test/transfer/report passed **synthetic smoke** only.
- NO published evidence from real DeepMIMO or Sionna 3GPP in this archive.
- Source engine is retained from Fuzzy_MUMIMO_E1R_E3R_Code_Guide.zip (`engine_original.py`).

## Key methodological safeguards
- Fixed q is selected solely on development; a single selected q is certified or rejected using a separate calibration partition.
- Calibration uses **one geometry and one error draw per group**, not many correlated Monte Carlo samples counted as independent Bernoulli events.
- One-sided Clopper-Pearson bound is conditional on independent, identically distributed groups/error events. For epsilon=alpha=0.05, >=59 independent calibration observations with zero failures are necessary.
- No unverified Gaussian fallback is declared certified.
- The locked q is assessed on disjoint DeepMIMO test groups and unchanged on a separately supplied external channel source.
- *No guarantee of 5% failure under shift from DeepMIMO to 3GPP.*
- No direct multi-candidate calibration without multiple-testing correction.

## Quick use
```bash
pip install -r code/requirements.txt
python code/create_smoke.py --output data/smoke.npz
python code/calibrate.py --stage preflight --dataset data/smoke.npz --run-id demo
python code/calibrate.py --stage develop --dataset data/smoke.npz --run-id demo
python code/calibrate.py --stage calibrate --dataset data/smoke.npz --run-id demo
python code/calibrate.py --stage freeze --dataset data/smoke.npz --run-id demo
python code/calibrate.py --stage test --dataset data/smoke.npz --run-id demo
python code/calibrate.py --stage report --dataset data/smoke.npz --run-id demo
```

For actual runs, replace smoke with a freshly prepared `data/deepmimo.npz` and add `--external-dataset data/3gpp_umi.npz` for `--stage transfer`. Both NPZs require `H: complex (N,M,K)` and `groups: (N,)`; >=12 well-defined distinct groups, but 300+ independent groups are needed for a plausible 20%-calibration split with 59 samples. Demonstrating independence of groups and correct channel propagation is a researcher responsibility.

## Cautions
- The imported fixed-beam robust power engine employs a norm-bound SINR model and is **not** a waveform/sensing system.
- Error realizations are conditionally simulated around noisy CSI; pilot estimation, measured aging, and true physical deployment are not validated.
- Mean transmit power excludes infeasible geometries, which are reported separately. Never equate lower feasible-case power with improved effective reliability.
- Test CSV includes all prespecified qs for descriptive sensitivity; policy selection must not change after test.
- The separate external 3GPP source is user-supplied, and its metadata must document Sionna configuration. Smoke uses the same synthetic source for both sides to exercise code paths only.
- Do not retain any study group already examined in previous rounds as new independent confirmatory holdout.
