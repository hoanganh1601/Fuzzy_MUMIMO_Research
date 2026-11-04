# Run card: DM_ASU35_CERT_AUDIT_20261104

## Identity

- Code version: Version 10 certified safe-pruning ablation audit
- Dataset: DeepMIMO `asu_campus_3p5`, reused development data
- Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`
- Shape: 160 geometries, 16 antennas, 4 candidate users
- Groups: 160 labels; labels alone do not establish statistical independence
- Manifest signature: `8bd06734144be054cc6165bac94c2b13fbb68a7b1505a8e847f3c907455dec6d`

## Locked configuration

`q=2.960414`, `sigma_rel=0.04`, `SINR=6 dB`, `noise=2e-13 W`, `Pmax=1 W`, alpha=`0,0.001,0.01,0.05,0.1,0.3,1`, `numeric_guard=1e-5`, bootstrap=`2000`, limit=`0`.

Environment recorded by CP00: NumPy 2.5.4. Execution environment check used Python 3.12.3, SciPy 1.18.1, and mpmath 1.4.1. The supplied unit suite passed 5/5 tests.

## Outcome

- Status: `PASS_EXACTNESS`
- Candidates audited: 16,800
- Exact matches: 160/160 for every ablation variant
- False prunes: 0
- Near-threshold fail-open events: 0
- ALL mean full solves: 8.5375
- CARDINALITY_ONLY mean full solves: 19.3375
- Additional solver calls saved: 10.8 per geometry; descriptive 95% interval `[8.8622, 12.8125]`
- Mean paired runtime saved: 1.486 ms; descriptive 95% interval `[1.0599, 1.9279]` ms
- Runtime advantage flag in CP06: true

CP07 signs CP00-CP06. `ARTIFACT_SHA256.csv` additionally signs all eight checkpoint artifacts CP00-CP07.

## Interpretation limits

Exactness applies only to the finite 15-subset by 7-beam candidate family and the implemented robust power-control model. The DeepMIMO geometries were observed in earlier development, so the positive runtime interval is not independent 3GPP validation. The numerical audit is conservative but is not formal interval arithmetic from the original CSI.

