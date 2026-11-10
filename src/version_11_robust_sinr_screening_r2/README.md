# Version 11: Robust SINR Screening R2

Version 11 packages the 2026-11-06 R2 implementation for robust SINR candidate screening. It separates beam/coefficient construction from power solving, applies deterministic tie-breaking, measures repeated randomized runtime, audits screening certificates against a finite exhaustive ZF/RZF reference, stresses numerical boundaries, and supports locked independent-validation runs.

The original source, tests, IEEE guide, Windows launcher, smoke fingerprint, and synthetic rehearsal datasets are retained byte-for-byte. `README_UPSTREAM.md` is the supplied README. `UPSTREAM_FILE_SHA256.csv` is the complete upstream manifest, including bundled rehearsal outputs and task caches that are intentionally not committed here. The two additional Vietnamese run guides in `docs/` were supplied alongside the package.

## Environment check

From this directory:

```bash
python -m pip install -r code/requirements.txt
python code/check_env.py --data /path/to/deepmimo_v10.npz
```

The recorded Linux environment used Python 3.12.3, NumPy 2.5.4, and SciPy 1.18.1. All 23 tests passed and the smoke decision fingerprint matched.

## Development A+B and boundary C

The recorded development run used the previously observed DeepMIMO v10 dataset:

```bash
python -u code/run_manuscript.py \
  --dev /media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz \
  --dev-label "DeepMIMO v10 development set" \
  --tag V11_DEV_20261110 --out-root outputs \
  --repeats 5 --bootstrap 2000 --boundary-limit 50 --skip D
```

It produced the A+B checkpoint family, boundary C, and manuscript tables. Real channel matrices and task caches remain outside Git.

## Locked independent-validation workflow

Run `independent_validation.py` in this order: `lock`, `preflight`, `scan`, then `report`, with identical parameters. Lock must occur before opening the test dataset. A dataset hash equal to the v10 development set is rejected.

The stored D run uses `rehearsal/data/synthetic_test_seed202.npz`, source `other_independent`, and its supplied provenance. It is a pipeline rehearsal only—not independent DeepMIMO/Sionna validation or a physical independence claim.

## Scope

Exactness means agreement with exhaustive search over the finite 15-subset × 7-beam candidate family. It is not global continuous-beam optimality, a statistical outage certificate, or formal interval arithmetic. Runtime bootstrap intervals are descriptive and must not be generalized beyond the recorded hardware/data. Version 11 observed fewer full solver calls but no runtime advantage over cardinality-only screening on either the DeepMIMO development run or the synthetic rehearsal.
