# Robust SINR safe-pruning: ablation and numerical audit (2026-11-04)

This package extends the earlier **Robust_Safe_Pruning_Ablation_Numerical_Audit_20261102** source. It does **not** tune the CSI uncertainty margin or expand beyond K=4.

## Primary program

`code/ablation_certified.py` — certificate ablation, independent exhaustive reference, fail-open numerical guard, 70-digit decimal diagnostic recheck close to thresholds, cluster bootstrap, resumable atomic task checkpoints, CSV/JSON outputs, SHA-256 manifest.

`code/reference_model.py` — original robust SINR / normalized ZF-RZF model and exhaustive oracle, unchanged.

`code/ablation_audit.py` — previous screening rule implementation, retained and called by the new driver.

`code/safe_pruning.py` — previous release, retained for audit/reference only.

`tests/` — original and new unit tests.

`docs/GUIDE_CERTIFIED_ABLATION_IEEE_VI.tex` and `.pdf` — 1-column IEEE Vietnamese guide.

## Reproduction

From this directory:

```powershell
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
python code/ablation_certified.py --stage preflight --dataset data/deepmimo.npz --run-id DM_CERT01
python code/ablation_certified.py --stage scan --dataset data/deepmimo.npz --run-id DM_CERT01
python code/ablation_certified.py --stage report --dataset data/deepmimo.npz --run-id DM_CERT01
```

Run `scan` again with **identical arguments** to resume. If source/data/config changes, choose a new `--run-id`. Outputs go to `outputs/<run-id>` by default. DeepMIMO and 3GPP NPZ are **not included**.

Example smoke test: 

```powershell
python code/ablation_certified.py --stage all --dataset data/smoke.npz --run-id TEST01 --limit 12 --bootstrap 300
```

## Interpretation

- `PASS_EXACTNESS` means matching exhaustive *in the finite codebook and tested scenarios*, not global beamforming optimality.
- Theoretical inequalities hold for the specified nonnegative power-control model. Floating-point checks are conservative (`--numeric-guard`, default 1e-5), but 70-digit checks from already computed coefficients are not a formal interval arithmetic certificate.
- `additional_solver_calls_saved_mean` compares ALL screening with CARDINALITY_ONLY, NOT with unpruned exhaustive.
- Reported runtime advantage requires a positive cluster-bootstrap lower bound; the 12-geometry synthetic smoke test does not show it.
- Group labels are not proof of independent samples. Prior 160-geometry DeepMIMO results must not be relabeled as unseen independent test.

### Outputs

CP00 manifest; CP01 per-geometry ablation; CP02 every candidate audit; CP03 per-ablation summary; CP04 per-rule numerical audit; CP05 paired incremental results; CP06 decision and confidence intervals; CP07 SHA-256 checks.
