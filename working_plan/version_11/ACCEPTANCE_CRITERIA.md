# Version 11 acceptance criteria

- Environment check passes, 23 tests pass, and the smoke fingerprint matches.
- Every screening variant agrees with exhaustive over the finite candidate family.
- No false prune is observed in development, boundary, or rehearsal runs.
- Boundary tests exercise fail-open behavior and return PASS.
- Locked D workflow produces CP00-CP06 with valid checksums.
- Runtime GO is asserted only when the paired bootstrap lower bound is positive.
- Synthetic rehearsal is not relabeled as real independent validation.
- Real datasets, task caches, virtual environments, and console logs are not committed.
