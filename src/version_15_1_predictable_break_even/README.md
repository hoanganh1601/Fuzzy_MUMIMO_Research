# Version 15.1: Predictable computational break-even

This snapshot preserves the static V15.1 workflow used to test whether
an `early_ratio`-conditioned policy can predict a runtime break-even point as
the number of users grows from `K=4` to `K=8`. It includes the source, unit
tests, synthetic smoke workflow, official runner, Vietnamese guide, paper,
rehearsal examples, and evidence index supplied with the package. Historical
source ZIP archives duplicated by earlier repository versions are excluded.

Real DeepMIMO/Sionna channel matrices, downloaded scenarios, virtual
environments, per-geometry task caches, console logs, and PID files are not
stored in Git. Their provenance is curated under `log/version_15_1`.

## Reproduce

Follow `HUONG_DAN_V15_1.md`. The official wrapper is:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_1.ps1 `
  -Development <dev.npz> -DevProvenance <dev.provenance.json> `
  -TestDM <dm_test.npz> -TestDMProvenance <dm.provenance.json> `
  -Test3GPP <gpp_test.npz> -Test3GPPProvenance <gpp.provenance.json> `
  -Tag V151
```

The wrapper runs unit tests, development profiling, frozen-policy selection,
DeepMIMO test, 3GPP test with the same lock, combined decision, and report ZIP.

## Recorded official outcome

The recorded run used 41 ASU development groups, 11 new Phoenix DeepMIMO test
groups, and 15 newly generated Sionna UMi groups. The frozen lock selected
`HYBRID/EARLY` only for `K=8, ER2`; neither test source contained an ER2
geometry, so the activated fraction and solver-call saving were both zero.

Both sources achieved zero oracle mismatch (`E3=true`) but failed E1, E2, and
E4. At K=8, mean runtime saving was -0.0606 ms on DeepMIMO and -0.0705 ms on
3GPP. The combined decision is `STOP`, not a computational-superiority claim.

