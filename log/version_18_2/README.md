# Version 18.2 M32 observed results

This is a retrospective record of the M32 run completed on 2026-11-27. The
frozen protocol is `runs/V18_M32/G00_protocol.json`; the official handover
archive is `reports/KET_QUA_V18_M32_20261127.zip`. The ZIP includes all nine
G01 and nine G03 raw JSONL measurement files, scenario validations, hardware
bundle and `NOTES.txt`. It contains no log, PID, native binary or channel NPZ.

| Checkpoint | Observed result |
|---|---|
| CK0 | Native self-test: 576 configurations × 7 schedulers, 96 oracle checks, 0 failures; 8/8 unit tests pass |
| Development | Three new Sionna UMi/UMa/RMa M32 pools accepted, 150 drops each |
| Protocol | 9 configurations, 450 development and 450 held-out drops; no M16 control |
| Lock | Nine maps locked; only the top load bin is active in each |
| Test | G1 exactness, G2 gain in R and G4 load-rule accuracy pass in all nine; G3 passes in four |
| Extras | 36 stage-timed drops; minimum median closure 0.9638; one hardware bundle |

The four complete passes are `M32_G0_E0.04`, `M32_G6_E0.02`,
`M32_G6_E0.08` and `M32_G10_E0.08`. The other five fail only G3: their
worst outside-region CI lower bounds are −3.5%, −4.9%, −6.5%, −31.9% and
−17.1%, respectively, against the predeclared >−2% gate. The measured LRS
gain inside R at K=8 is 92.7–94.6%. Do not report a universal PASS.

The 450 held-out drops per configuration belong to only three scenes.
Scene-level bootstrap intervals are wide and marked unreliable with fewer
than five scenes. The held-out channel sets had been measured at M=8/M=16
in V18, but had not been timed at M32 or used for M32 development. Hardware
evidence comes from one machine only. G1 exactness is limited to the finite
candidate family and the recorded numerical oracle.

The first `run` attempt stopped because the published V15.2 policy map was
missing from the expected `results/` path. The map was restored with the
recorded SHA-256, and the same protocol resumed; see `NOTES.txt`. Real NPZ
files and expanded G01/G03 measurements are not committed. The latter are
preserved in the ZIP. `ARTIFACT_SHA256.csv` hashes the curated files in this
directory.
