# Run card: BORDER_V12

## Identity

- Code version: Version 12 robust SINR final validation
- Program: `code/boundary_stress.py`
- Channel input: previously observed DeepMIMO ASU development dataset, used only
  for channel-derived boundary stress
- Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`
- Channel geometry limit: 50

## Outcome

- Cases: 1,020
- False prunes: 0
- Fail-open cases: 323
- Decision: `PASS`

CP03 signs CP00–CP02. This branch tests positive-`F,u` algebraic boundaries and
single-user CSI-derived power boundaries. It is not an interval-arithmetic
guarantee for the full beam-generation pipeline.
