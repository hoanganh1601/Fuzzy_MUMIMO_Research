# Version 11 run log

Version 11 records the R2 re-run of manuscript Sections A–C on the previously observed DeepMIMO v10 development set and a locked synthetic D rehearsal.

- [`V11_DEV_20261110_AB`](runs/V11_DEV_20261110_AB/RUN.md): 160 geometries, 16,800 candidates, five runtime repeats, exact agreement with exhaustive, zero false prunes.
- [`V11_DEV_20261110_C`](runs/V11_DEV_20261110_C/RUN.md): 1,030 boundary cases, zero false prunes, 324 fail-open cases.
- [`SYN_REHEARSAL_D_20261110`](runs/SYN_REHEARSAL_D_20261110/RUN.md): locked synthetic independent-workflow rehearsal, 160 geometries in 32 groups, zero false prunes, no observed runtime GO.
- [`BOUNDARY01`](runs/BOUNDARY01/RUN.md): direct boundary command retained because it was part of the delivered report; it duplicates the integrated C configuration/result.

The curated report files are in [`reports/`](reports/). Task caches and console logs are excluded. No real independent DeepMIMO-new or Sionna 3GPP run was available.
