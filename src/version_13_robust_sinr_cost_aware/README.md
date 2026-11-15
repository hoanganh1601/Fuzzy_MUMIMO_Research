# Version 13: Robust SINR cost-aware screening

Version 13 keeps the finite ZF/RZF robust-SINR model from Version 12 and tests
whether early channel-norm screening or reuse of cached robust coefficients can
improve end-to-end runtime over the strong cardinality-only baseline.

The four development policies are `CARD`, `EARLY`, `CACHED`, and `HYBRID`.
Policy selection is locked on development data using paired group bootstrap and
a minimum lower-bound improvement of 0.1 ms. The locked policy is then evaluated
without retraining on a separate test source, with all 105 finite candidates per
geometry audited against the exhaustive oracle.

The supplied source, tests, IEEE guide, PowerShell launcher, smoke fixtures, smoke
example results, and manuscript examples are retained byte-for-byte. The original
README is stored as `README_UPSTREAM.md`; the supplied checksum table is stored as
`UPSTREAM_FILE_SHA256.csv`. Generated outputs, task caches, environments, console
logs, and downloaded scenarios are excluded from the immutable source snapshot.

## Environment and tests

From this directory:

```bash
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
```

The recorded Linux run used Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, and
mpmath 1.4.1. All five supplied unit tests passed.

## Native workflow

Run the stages in the immutable order `develop`, `preflight`, `scan`, then
`report`, keeping the same run ID, source, datasets, and parameters. Development
exports CP01 and the immutable CP02 policy lock. Test evaluation exports CP03--CP08.
Per-geometry task files support resume but are not publication artifacts.

The PowerShell orchestration example is `scripts/run_v13.ps1`. Linux users can
invoke the same stages directly with Python. Real channel matrices, selection
arrays, downloaded ray-tracing scenarios, per-geometry tasks, environments, and
console logs must remain outside Git.

## Recorded result and scope

The curated run is stored under `log/version_13`. Development selected `CARD`:
`EARLY` saved 0.1139 ms on average, but its 95% lower bound was only 0.0107 ms,
below the locked 0.1 ms threshold; `CACHED` and `HYBRID` were slower. The new
DeepMIMO New York test therefore retained the baseline and returned
`STOP_NO_RUNTIME_GAIN` with zero oracle mismatch.

The CP08 audit covered 16,800 candidates and observed zero false rejection.
Exactness applies only to the finite 15-subset by 7-beam family and the implemented
floating-point robust power-control model. It is not global continuous-beam
optimality, formal interval certification, an outage certificate, verified
statistical independence, or evidence of computational superiority.
