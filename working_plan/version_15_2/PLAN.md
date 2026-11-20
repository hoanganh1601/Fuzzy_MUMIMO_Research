# Version 15.2 plan record

This repository record was written after the official run on 2026-11-20. The
predeclared protocol is the supplied `HUONG_DAN_V15_2.md` together with signed
CP00/CP03 artifacts; this file does not claim to be a preregistration.

1. Validate software with unit tests and the synthetic smoke workflow.
2. Use at least 80 development groups and at least 20 K=8 ER2 groups.
3. Freeze policy cells before creating or selecting either test set.
4. Build two new pools with at least 60 groups and `prior_use=never_seen`.
5. Select test groups by frozen covariates only, with 15 in `R` and 15 outside.
6. Evaluate both sources on one lock and require P1--P4 for combined GO.
7. Curate CP artifacts, provenance and report ZIP; exclude real matrices,
   scenarios, task caches, environments, console logs and PID files.
