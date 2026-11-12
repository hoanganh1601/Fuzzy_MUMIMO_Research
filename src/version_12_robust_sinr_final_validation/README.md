# Version 12: Robust SINR final validation

Version 12 packages the final-validation workflow that follows R2.V11. It compares
`FAST` and `LITE` robust-SINR screening against the strong `CARDINALITY_ONLY`
baseline with a finite exhaustive ZF/RZF oracle. The workflow adds repeated paired
runtime measurement, channel-derived boundary stress, independent-source dataset
audits, and a read-only manuscript gate.

The supplied source, tests, IEEE guide, PowerShell launcher, provenance templates,
synthetic smoke fixture, and manuscript working files are retained byte-for-byte.
The original README is stored as `README_UPSTREAM.md`; the complete supplied
checksum table is stored as `UPSTREAM_FILE_SHA256.csv`. Bundled smoke outputs and
their task cache are intentionally excluded from the immutable source snapshot.

## Environment and tests

From this directory:

```bash
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
```

The recorded Linux run used Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1, and mpmath
1.3.0. All 12 supplied unit tests passed.

## Native workflow

Run the boundary branch with `boundary_stress.py`. For each channel source, run
`final_runtime_validation.py` in the immutable order `lock`, `preflight`, `scan`,
then `report`, keeping the same run ID and parameters. The report exports CP00–CP07.
After both DeepMIMO and Sionna/3GPP runs plus the boundary branch are complete, run
`manuscript_gate.py` to produce the cross-source decision.

The Windows orchestration example is in `scripts/run_validation.ps1`. Linux users
can invoke the same four stages directly with Python. Real channel matrices,
downloaded scenarios, per-geometry task caches, environments, and console logs must
remain outside Git.

## Recorded validation scope

The curated Version 12 runs are stored under `log/version_12`. Both new-source runs
observed zero false prunes over 16,800 candidates, while neither established a FAST
runtime advantage over `CARDINALITY_ONLY`. The final manuscript gate therefore
returned `STOP_MANUSCRIPT_NOT_LOCKED`.

Exactness applies only to the finite 15-subset by 7-beam candidate family and the
implemented floating-point robust power-control model. It is not global continuous-
beam optimality, formal interval arithmetic, an outage certificate, or proof of
statistical independence. The 3GPP protocol was locked before its own dataset was
generated and evaluated, but after the DeepMIMO result had been observed; this is
recorded in provenance rather than hidden.
