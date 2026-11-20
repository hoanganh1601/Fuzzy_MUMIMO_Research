# Version 15.2 official run log

This directory curates the official V15.2 checkpoints without real channel
matrices, downloaded scenarios, task caches, console logs or PID files.

- `runs/V152_DM`: ASU development, frozen lock, covariate preflight and the
  selected DeepMIMO Los Angeles test.
- `runs/V152_3GPP`: selected Sionna 3GPP test using the same lock.
- `runs/V152_FINAL`: combined decision and manuscript table.
- `provenance`: development, pool, selected-test and Sionna protocol records.
- `reports/KET_QUA_V152.zip`: the 30-file bundle produced by the official runner.

The report archive SHA-256 is
`8f2ae5933e59f785db2a0335524d35242cf283680017c167e26a1f30a746f7b3`.
Its compressed contents verify without errors.

Both sources pass the region gate and P1--P4 with zero oracle mismatch. The
combined status is `GO_PREDICTABLE_BREAK_EVEN`. Statistical independence is not
mathematically proven, and the result does not certify unrestricted precoding,
OTA behavior or production deployment.
