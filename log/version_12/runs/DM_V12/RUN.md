# Run card: DM_V12

## Identity

- Code version: Version 12 robust SINR final validation
- Source: DeepMIMO 4.0.5, `city_37_seoul_3p5`
- Dataset SHA-256: `f62313a96c17c18b416929a12b6a117cfe03ee82717ad285b531bb121f6b467f`
- Shape: 160 geometries, 16 BS antennas, 4 users
- Spatial groups: 40 fixed 35 m cells, four geometries per cell
- Development overlap check: zero group-ID overlap with 160 ASU development groups

## Locked configuration

`q=2.960414`, relative CSI uncertainty `0.04`, SINR `6 dB`, noise
`2e-13 W`, `Pmax=1 W`, alpha=`0,0.001,0.01,0.05,0.1,0.3,1`, numerical
guard `1e-5`, runtime repeats `7`, cluster bootstrap `2000`.

## Outcome

- Candidates audited: 16,800
- False prunes: 0
- Fail-open events: 0
- FAST mean full-solver calls saved: 32.7375 per geometry
- FAST mean runtime saved: `-0.802617 ms`
- FAST descriptive 95% interval: `[-0.943106, -0.662912] ms`
- Decision: `STOP_NO_FAST_RUNTIME_ADVANTAGE`

CP07 signs CP00–CP06. FAST preserved the finite exhaustive reference but its
screening overhead exceeded the saved solver time. A different ray-tracing scene
and non-overlapping labels support separation; they do not prove statistical
independence.
