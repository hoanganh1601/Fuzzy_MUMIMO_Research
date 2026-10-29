# Version 06 acceptance criteria

## Required for a GO candidate

1. CP00 spatial and split audit passes.
2. Candidate margin is selected on development only.
3. CP05 has `upper_95_one_sided <= 0.05` under defensible independent/exchangeable episode assumptions.
4. Frozen candidate is evaluated unchanged on independent test groups.
5. Power claims use paired common-feasible geometries and confidence intervals.
6. External 3GPP results retain simulator provenance and do not inherit a DeepMIMO guarantee.

## Stop conditions

- Fewer than 59 calibration groups.
- Invalid metadata or insufficient group-center separation.
- CP05 calibration failure.
- Source, dataset or setting fingerprint mismatch.
- Missing external-source provenance.
