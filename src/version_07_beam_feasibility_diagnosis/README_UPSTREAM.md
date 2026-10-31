# Beamforming Feasibility Diagnosis (fixed CSI margin)

This package replaces CSI-margin tuning with fixed-margin communication-only robust SINR feasibility diagnostics. Source code: `code/beam_feasibility.py`. Vietnamese one-column IEEE guide: `docs/GUIDE_IEEE_VI.pdf` and `.tex`.

## Requirements
`python -m pip install -r code/requirements.txt`

## Run
`python code/beam_feasibility.py --stage preflight --dataset data/deepmimo.npz --run-id DM_BEAM01`
`python code/beam_feasibility.py --stage scan --dataset data/deepmimo.npz --run-id DM_BEAM01`
`python code/beam_feasibility.py --stage report --dataset data/deepmimo.npz --run-id DM_BEAM01`

Input NPZ must include complex `H` with shape (N,M,K) and `groups` length N; optional `xyz`, `scenario`. Change `--q`, `--sigma-rel`, `--sinr-db`, `--noise`, `--pmax` only as physically justified and lock them across ZF/RZF. Code uses a conservative norm-bounded CSI error model, not a statistical outage guarantee.

Tested on `data/synthetic_diagnostic.npz` with 12 geometries, 7 beam cases, 5 power budgets. The included `outputs/SMOKE` is only a program check, not DeepMIMO or 3GPP results. For 3GPP evaluation, export channel tensor separately, use a new run-id, and retain metadata of simulator configuration.

## Checkpoints
CP00 manifest; per-geometry atomic JSON under tasks; CP01 geometry-level detailed CSV; CP02 beam/budget summary; CP03 ZF/RZF paired CSV; CP04 geometry diagnosis; CP05 scope and stop conditions; CP06 SHA-256 of output tables. Repeating same command skips completed geometries; changing code or configuration with same run-id fails closed.

## Caveats
ZF only if full rank. The condition rho(F)<1 concerns the robust fixed-beam power-control model, not global beamforming feasibility. High noise or channel units may create power-budget failure. Analyzed beam regularization factors are a predefined grid; no post hoc test-set best-alpha claims.
