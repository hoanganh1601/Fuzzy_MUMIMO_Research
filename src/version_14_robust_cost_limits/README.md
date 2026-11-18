# Version 14: Robust cost limits

Version 14 follows Version 13 without changing the robust-SINR model. It asks
whether a development-locked, cost-aware switch can improve end-to-end runtime
over the cardinality-only (`CARD`) baseline while preserving the exhaustive
answer over the finite 15-subset by 7-beam ZF/RZF family.

The development workflow profiles `CARD`, `EARLY`, `CACHED`, and `HYBRID`, fits
simple rules on 60% of the development groups, validates the selected rule on
the remaining 40%, and freezes `CARD` unless the group-bootstrap lower bound is
greater than 0.1 ms. Test data cannot be used to change the rule or threshold.

The supplied code, tests, IEEE guide, PowerShell runner, smoke fixtures, and
smoke checkpoint examples are retained byte-for-byte. The original README is
stored as `README_UPSTREAM.md`; the supplied checksum table is stored as
`UPSTREAM_FILE_SHA256.csv`. Forty per-geometry JSON files under the supplied
`profile_tasks/` and `tasks/` directories are excluded because they are
generated resume caches, not immutable source or publication artifacts.

## Environment and tests

From this directory:

```bash
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
```

The recorded Linux run used Python 3.12.3, NumPy 2.5.5, SciPy 1.18.1, and
mpmath 1.4.1. All 11 supplied unit tests passed.

## Native workflow

Run the stages in the immutable order `profile`, `select`, `preflight`, `scan`,
then `report`, retaining the same code, datasets, parameters, and run ID.
`profile` and `scan` produce resumable task caches; only CP00--CP09 are curated
as report artifacts. A second source must reuse CP03 through `--lock-from` and a
new run ID.

The PowerShell orchestration example is `scripts/run_v14.ps1`. Linux users may
invoke the same stages directly with Python. Real channel matrices, selection
arrays, downloaded scenarios, task caches, environments, console logs, and PID
files must remain outside Git.

## Recorded result and scope

The curated run is stored under `log/version_14`. Development used 160 ASU
geometries and selected an `EARLY` candidate rule, but its validation saving was
0.0840 ms with 95% CI `[-0.0369, 0.2553]` ms. The locked fallback was therefore
`CARD`.

After CP03 was sealed, a new DeepMIMO 4.0.5 Denver test was generated with 92
geometries in 23 spatial groups and 368 unique UEs. The test audited 9,660
candidates and observed zero oracle mismatch and zero false certificate. Because
`CARD` activated no adaptive screening, the mean runtime saving was -0.0145 ms
with 95% CI `[-0.0319, -0.00004]` ms, and CP08 returned
`STOP_NO_RUNTIME_GAIN`.

This is a valid negative result. It does not establish acceleration, statistical
independence, global continuous-beam optimality, formal interval certification,
or an outage guarantee. The planned second-source 3GPP transfer was not run for
this recorded V14 result.
