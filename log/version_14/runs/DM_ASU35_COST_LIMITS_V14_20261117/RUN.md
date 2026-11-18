# Run: DM_ASU35_COST_LIMITS_V14_20261117

## Identity

- Code version: 14
- Source commit: `187c9053f55ab8f8e526383b829315be02ecfb5c`
- Source tag: `v14.0.0`
- Final checkpoint: CP09
- Decision: `STOP_NO_RUNTIME_GAIN`

## Development and lock

- Dataset: DeepMIMO ASU Campus, `(160,16,4)`, 160 development groups
- Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`
- Fit/validation groups: 96/64
- Candidate rule: `EARLY` if `early_ratio >= 0.4690403640270233`
- Validation mean saving: 0.084034 ms
- Validation CI95: `[-0.036903, 0.255293]` ms
- Required lower-bound gain: 0.1 ms
- Locked policy: `CARD`
- CP03 SHA-256: `19259a0cc12b86160169a46b90f8e99140171c11d7e5549305dbdd5c16020567`

## Post-lock test

- Source: DeepMIMO 4.0.5 `city_18_denver_3p5`, BS1
- Dataset: `(92,16,4)` complex64, 23 spatial groups, 368 unique UEs
- Dataset SHA-256: `7b8ca0a588db002029aa5e746e3289f5ece72291dc2ac48a4591fc73fa61aaf7`
- Selection SHA-256: `a943bd266407e7fbcc52f2ab7301b94c64e9ef75842807781985746d49872fd2`
- Selection protocol SHA-256: `41a887fd41fd5c9ea28d62a69a446beee362a22609b2b13f7729dadc046941b2`
- Development/test group overlap: 0
- Exact-channel overlap: 0
- Candidate audit rows: 9,660
- Oracle mismatch: 0
- False certificate: 0

## Runtime outcome

- Activated geometries: 0/92
- Mean calls saved: 0
- Mean runtime saving: -0.014485 ms
- Median runtime saving: -0.003620 ms
- Group-bootstrap CI95: `[-0.031906, -0.000037]` ms
- Final status: `STOP_NO_RUNTIME_GAIN`

The result preserves the exhaustive outcome over the implemented finite
candidate family but does not demonstrate acceleration. A second-source 3GPP
transfer was not executed. Different scenarios, post-lock generation, and
overlap checks do not mathematically prove statistical independence.
