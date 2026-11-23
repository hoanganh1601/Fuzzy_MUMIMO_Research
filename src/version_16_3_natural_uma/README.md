# Version 16.3 — second natural-prevalence sample

This directory preserves the 97 files listed in `UPSTREAM_FILE_SHA256.csv`.
The supplied `README.md` and `VALIDATION_REPORT.json` are preserved as
`README_UPSTREAM.md` and `VALIDATION_REPORT_UPSTREAM.json`; their upstream
manifest entries retain the original names. `SOURCE_SHA256.csv` hashes this
repository snapshot. Read `HUONG_DAN_V16_3_NAT2.md` for the intended sequence.

V16.3 adds a frozen UMa deployment specification (`NS00`), a pool validation
gate (`NS01`), and comparison of a second natural sample with the earlier UMi
run (`NP04`/`NP05`). The five V15.2 core modules and the policy lock remain
unchanged. This repository does not store generated channel matrices, native
binaries, task caches, or virtual environments.

The observed run and its limitations are documented in
`../../log/version_16_3/README.md`. Its UMa sample returned `NATURAL_GAIN`:
99/100 groups were in the predicted region R, and mean relative saving at
K=8 over all groups was 84.33% (95% CI 81.81–86.49%). The compiled run
returned `GO_COMPILED_BREAK_EVEN`, with 0 numeric events in 2,700 checked
decisions. These are results for the specified UMa simulation and finite
candidate family, not a general deployment guarantee.
