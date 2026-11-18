# Version 15: Unified robust MU-MIMO smoke workflow

This repository snapshot preserves the Version 15 software path required for
the PDF smoke workflow. It unifies the finite-codebook robust-SINR model,
conservative screening policies, synthetic data generator, unit tests, and the
single `run_experiment.py` entrypoint for `K = 4, 6, 8`.

The snapshot is deliberately limited to smoke reproducibility. It contains the
seven required code/requirements files, two synthetic fixtures and provenance,
the Vietnamese IEEE guide, `smoke_v15.ps1`, four unit tests, and the supplied
top-level smoke checkpoint example. Historical evidence archives, the working
paper, official-run wrapper, DeepMIMO packer, bytecode caches, per-geometry task
caches, and real-data outputs are outside this smoke-only import.

The original package README is retained as `README_UPSTREAM.md`, its validation
record as `VALIDATION_REPORT_UPSTREAM.json`, and the complete supplied manifest
as `UPSTREAM_FILE_SHA256.csv`. The import metadata lists all excluded scopes.

## Reproduce the smoke check

From this directory:

```bash
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
python code/make_synthetic.py --n 12 --prefix DEV --seed 12 --output data/smoke_dev.npz
python code/make_synthetic.py --n 8 --prefix TEST --seed 34 --output data/smoke_test.npz
python code/run_experiment.py --stage all --development data/smoke_dev.npz --test data/smoke_test.npz --ks 4,6,8 --beam-counts 3 --repeats 2 --bootstrap 100 --smoke --limit 4 --min-cell-groups 1 --run-id V15_SMOKE
```

The PowerShell equivalent is `scripts/smoke_v15.ps1`. The recorded Linux replay
used the same Python commands and is curated under `log/version_15`.

## Recorded scope

The smoke run produced CP00--CP09 for four synthetic development and four
synthetic test geometries. It evaluated `(K,L) = (4,3), (6,3), (8,3)`, observed
zero oracle mismatch, and returned `SMOKE_ONLY`. All locked cells fell back to
`CARD`, so runtime/call savings are zero by construction in the frozen-policy
summary.

This result verifies program flow, checkpoint creation, finite-family oracle
agreement, and integrity hashing only. It is not a DeepMIMO or 3GPP result, an
independent validation, evidence of runtime advantage, global beamforming
optimality, an outage certificate, or formal interval certification.
