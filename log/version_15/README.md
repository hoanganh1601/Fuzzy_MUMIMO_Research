# Version 15 smoke run log

This log contains only the synthetic smoke workflow required by the Version 15
IEEE guide. It does not contain the separate ASU/Singapore experiment, any real
channel matrix, or an independent 3GPP result.

The recorded run is [`V15_SMOKE`](runs/V15_SMOKE/RUN.md):

- Four supplied unit tests passed.
- Deterministic synthetic inputs contained eight users per geometry.
- Four development and four test geometries were processed for
  `(K,L) = (4,3), (6,3), (8,3)`.
- CP03 locked every observed cell to `CARD` under the deliberately small smoke
  fit/validation split.
- CP08 observed zero oracle mismatch and returned `SMOKE_ONLY`.
- The frozen policy activated no screening, so reported runtime and solver-call
  savings are zero for all three configurations.

The 12 curated top-level checkpoints are bundled in
[`Results.Robust.MUMIMO.V15.SMOKE.zip`](reports/Results.Robust.MUMIMO.V15.SMOKE.zip).
The original CP09 also signs eight per-geometry task-cache files; those caches
are deliberately not committed. `ARTIFACT_SHA256.csv` independently signs the
12 curated files present in this repository.

This run verifies software execution and finite-family agreement only. It is not
DeepMIMO/3GPP evidence, independent validation, or a runtime-advantage claim.
