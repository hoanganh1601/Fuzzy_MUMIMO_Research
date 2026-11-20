# Version 15.2 — predictable break-even in a frozen prediction region

Version 15.2 evaluates pre-beam screening only inside a region `R` defined by
the policy frozen on development data. Test pools are created after the lock,
selected by covariates without runtime measurements, and evaluated with the
same lock on DeepMIMO and Sionna 3GPP sources.

The supplied Vietnamese procedure is
[`HUONG_DAN_V15_2.md`](HUONG_DAN_V15_2.md). The original package README and
validation report are retained as `README_UPSTREAM.md` and
`VALIDATION_REPORT_UPSTREAM.json`; upstream hashes are recorded in
`UPSTREAM_FILE_SHA256.csv`.

## Reproduction outline

```powershell
python -m pip install -r code/requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_v15_2.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase develop `
  -Development <dev.npz> -DevProvenance <dev.provenance.json> -Tag V152
powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase select `
  -Development <dev.npz> -DevProvenance <dev.provenance.json> -Tag V152 `
  -PoolDM <dm_pool.npz> -PoolDMProvenance <dm_pool.provenance.json> `
  -Pool3GPP <gpp_pool.npz> -Pool3GPPProvenance <gpp_pool.provenance.json>
powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase test `
  -Development <dev.npz> -DevProvenance <dev.provenance.json> -Tag V152
```

Real channel matrices and downloaded scenarios are intentionally not tracked.
See [`../../log/version_15_2`](../../log/version_15_2) for the curated official
checkpoints, provenance and report bundle.

## Recorded official outcome

The official run used 107 ASU development groups, then selected 15 groups in
`R` and 15 outside `R` from each new test pool. DeepMIMO Los Angeles and Sionna
3GPP both returned `GO_BREAK_EVEN`; P1--P4 passed and oracle mismatch was zero.
The combined decision is `GO_PREDICTABLE_BREAK_EVEN`.

This result supports prototype and monitored-pilot evaluation. It is limited to
the finite ZF/RZF candidate family and the recorded runtime environment. It is
not a proof of unrestricted beamforming optimality, mathematical statistical
independence, OTA performance or production readiness.
