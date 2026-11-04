# Version 10: certified safe-pruning ablation audit

Version 10 audits the robust SINR safe-pruning rules introduced in Version 09. It adds seven ablation configurations, an exhaustive reference that does not participate in pruning decisions, conservative fail-open handling near numerical thresholds, 70-digit diagnostic rechecks, paired solver/runtime comparisons, cluster bootstrap intervals, and resumable per-geometry checkpoints.

The original package is preserved in `code/`, `data/`, `docs/`, and `tests/`. `README_UPSTREAM.md`, `RELEASE_NOTES.md`, and `UPSTREAM_FILE_SHA256.csv` retain the supplied documentation and checksums. Generated task checkpoints, virtual environments, the real DeepMIMO matrix, and console logs are intentionally excluded from Git.

## Reproduction

Install dependencies and run the supplied tests:

```bash
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
```

The recorded development run used the same arguments at every stage:

```bash
python -u code/ablation_certified.py --stage preflight \
  --dataset /media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz \
  --run-id DM_ASU35_CERT_AUDIT_20261104 --limit 0 \
  --q 2.960414 --sigma-rel 0.04 --sinr-db 6 --noise 2e-13 --pmax 1 \
  --alpha-list 0,0.001,0.01,0.05,0.1,0.3,1 \
  --numeric-guard 1e-5 --bootstrap 2000
```

Repeat the command with `--stage scan`, then `--stage report`. Re-running `scan` with the identical configuration resumes completed geometry checkpoints. A changed source, dataset, or parameter set requires a new run ID.

## Recorded result and scope

Run [`DM_ASU35_CERT_AUDIT_20261104`](../../log/version_10/runs/DM_ASU35_CERT_AUDIT_20261104/RUN.md) evaluated 16,800 candidates over 160 DeepMIMO geometries. It returned `PASS_EXACTNESS`: all ablation solutions matched the finite exhaustive reference and no false prune was observed. ALL saved 10.8 full solver calls per geometry relative to CARDINALITY_ONLY. Mean paired runtime saving was 1.486 ms with descriptive cluster-bootstrap 95% interval `[1.060, 1.928]` ms.

These geometries were already observed in prior development work. The result is therefore a development audit, not independent 3GPP validation, a global beamforming certificate, a statistical outage guarantee, or formal interval arithmetic proof. High-precision checks only re-evaluate coefficients already derived in floating point.

