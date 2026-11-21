# Version 16 — computational break-even extension

This directory preserves the supplied V16 source package. The Vietnamese procedure is in `HUONG_DAN_V16.md`; the original README and validation report are retained as `README_UPSTREAM.md` and `VALIDATION_REPORT_UPSTREAM.json`. `UPSTREAM_FILE_SHA256.csv` lists the supplied package hashes; its `README.md` and `VALIDATION_REPORT.json` entries correspond to the renamed files above.

V16 extends the frozen V15.2 study with a C implementation, an analytical cost model and a natural prevalence experiment. The five V15.2 core modules are byte identical to the frozen source. Real development and test channel matrices are stored outside Git.

## Current run status

- The `check` phase passed 30/30 unit tests and confirmed that the V15.2 lock is reusable on the current machine.
- The `compiled` phase stopped during `C16_DEV` at geometry 8, K=6, L=3, CARD. The C and Python results selected the same subset, alpha and cardinality, but their power values failed the comparison tolerance.
- The guide instructs the operator to stop and send the log on `COMPILED MISMATCH`. See `../../log/version_16/V16_compiled.log` and its run status note.
- No official V16 conclusion or release tag exists. The `examples/REHEARSAL_V16_SYNTHETIC` files are synthetic rehearsal output only.
