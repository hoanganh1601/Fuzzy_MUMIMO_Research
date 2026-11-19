# Version 15.1 official run log

This directory curates the official V15.1 checkpoints without real channel
matrices or resumable task caches.

- `runs/V151_DM`: development, frozen lock, and Phoenix DeepMIMO test.
- `runs/V151_3GPP`: Sionna 3GPP UMi test using the same frozen lock.
- `runs/V151_FINAL`: combined cross-source decision and manuscript table.
- `provenance`: development/test provenance and the locked Sionna protocol.
- `reports/KET_QUA_V151.zip`: the 26-file report produced by the official runner.

The archive SHA-256 is
`6749797a6c5966c40cf7dace93bbedfb5fa9e060e4e9954c0519fc34ada4ed50`.
Its compressed data verifies without errors.

The combined status is `STOP`. Both sources preserve oracle agreement, but
neither verifies a predictable runtime break-even. No test geometry activated
the K=8 ER2 policy cells selected during development.

