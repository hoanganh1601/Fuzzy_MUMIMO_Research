# Version 13 frozen configuration

## Robust-SINR and timing

- q: 2.960414
- Relative CSI uncertainty: 0.04
- SINR target: 6 dB
- Noise: 2e-13 W
- Pmax: 1 W
- Alpha: 0, 0.001, 0.01, 0.05, 0.1, 0.3, 1
- Numerical guard: 1e-5
- Policies: CARD, EARLY, CACHED, HYBRID
- Runtime repeats: 7
- Group-bootstrap draws: 2,000
- Development minimum lower-bound improvement: 0.1 ms
- Frozen policy: CARD

## Development

- Source: DeepMIMO `asu_campus_3p5`
- Shape: `(160,16,4)` complex64; groups: 160
- SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`

## Test

- Source: DeepMIMO 4.0.5 `city_0_newyork_3p5`, BS1
- Shape: `(160,16,4)` complex64; groups: 40 spatial cells
- 640 unique UEs; selection seed: 20261113; spatial cell: 15 m
- 16x1 BS ULA, 1x1 UE, 10 paths, 0.5-wavelength spacing
- Frequency domain; 10 MHz; 512 total subcarriers; subcarrier 0
- No post-generation channel normalization
- SHA-256: `cf3a58de6a6519921e308753858798c61c94b11bca4faafac8afb1f49248d557`
