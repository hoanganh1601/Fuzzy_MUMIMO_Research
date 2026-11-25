# Version 17 — frozen-policy Pmax transfer

This directory preserves the 100 files listed by the supplied
`UPSTREAM_FILE_SHA256.csv`. The upstream `README.md` and
`VALIDATION_REPORT.json` are retained as `README_UPSTREAM.md` and
`VALIDATION_REPORT_UPSTREAM.json`; their manifest entries keep the original
names. `SOURCE_SHA256.csv` hashes this repository snapshot.

Read `HUONG_DAN_V17_PMAX.md` before running. V17 keeps the V15.2 policy map
and physical settings fixed, then evaluates the compiled solver on held-out
complements of the earlier UMi and UMa natural pools at 30, 35, 46 and
49 dBm. `code/pmax_sweep.py` freezes the protocol, verifies inputs and power
levels after every run, and evaluates endpoints X1–X6. The five V15.2 core
modules and policy thresholds are not retrained.

The observed run is documented in `../../log/version_17/README.md`. All four
power levels returned `TRANSFER_OK`. Across eight runs, 21,600 decisions were
checked with zero numeric events and zero single/double decision changes. UMa
showed strong positive runtime savings; UMi had no groups in R and primarily
established bounded overhead rather than positive gain.

Generated channel matrices, complement NPZ files, task checkpoints, native
binaries, PID files and environments are intentionally excluded from Git.
