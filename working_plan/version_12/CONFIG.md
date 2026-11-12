# Version 12 frozen configuration

## Screening and timing

- q: 2.960414
- Relative CSI uncertainty: 0.04
- SINR target: 6 dB
- Noise: 2e-13 W
- Pmax: 1 W
- Alpha: 0, 0.001, 0.01, 0.05, 0.1, 0.3, 1
- Numerical guard: 1e-5
- Variants: CARDINALITY_ONLY, FAST, LITE
- Runtime repeats: 7
- Cluster-bootstrap draws: 2,000
- Primary runtime rule: FAST GO only when the paired 95% lower bound is positive

## DeepMIMO source

- Scenario: `city_37_seoul_3p5`, 3.5 GHz
- Dataset shape: `(160,16,4)` complex64
- Groups: 40 spatial cells
- Dataset SHA-256: `f62313a96c17c18b416929a12b6a117cfe03ee82717ad285b531bb121f6b467f`

## Sionna/3GPP source

- Model: Sionna 2.2.0 UMi, TR 38.901 V19.2, downlink
- Carrier: 3.5 GHz; static outdoor UEs; single-V arrays
- Dataset shape: `(160,16,4)` complex64
- Groups: 160 topology drops
- Dataset SHA-256: `daac3826f568b9e4cf7cf6f8858a4fe6bdb9e46ce294b73a189bfbf1c9b47f18`
