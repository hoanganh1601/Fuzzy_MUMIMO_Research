# Version 16.1 — numeric agreement audit

This directory preserves the supplied V16.1 package. Read `HUONG_DAN_V16.md` and `CHANGELOG_V16_1.md` for its procedure and changes. The package README and validation report are retained as `README_UPSTREAM.md` and `VALIDATION_REPORT_UPSTREAM.json`; `UPSTREAM_FILE_SHA256.csv` records the supplied hashes (using the original names for those two renamed files).

V16.1 adds `code/numeric_agreement.py` and updates the compiled benchmark, selftest, regression test and runner. The five frozen V15.2 core modules and `code/native/screen_core.c` are byte identical to V16. Real development and test channel matrices remain outside Git. The included `examples/REHEARSAL_V16_SYNTHETIC` files are synthetic rehearsal only.

## Observed run status

The `check` phase passed 31/31 tests and reused the frozen V15.2 lock. The `compiled` phase completed all three datasets, but its C1 gate allows at most 1% numeric events per dataset. DeepMIMO test had 0/810 and returned `GO_COMPILED_BREAK_EVEN`; development had 1005/2889 (34.79%) and 3GPP had 162/810 (20%), both returning `STOP_COMPILED`. C2–C4 passed on each dataset. No V16.1 overall GO or release tag is claimed. See `../../log/version_16_1/README.md` for the curated results.
