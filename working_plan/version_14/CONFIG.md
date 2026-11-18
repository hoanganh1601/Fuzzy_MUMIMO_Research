# Version 14 frozen configuration

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
- Minimum runtime gain: 0.1 ms
- Minimum test groups: 20
- Protocol seed: 217
- Frozen policy: CARD

## Development

- Source: DeepMIMO `asu_campus_3p5`
- Shape: `(160,16,4)` complex64; groups: 160
- SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`
- Fit/validation group counts: 96/64

## Test

- Source: DeepMIMO 4.0.5 `city_18_denver_3p5`, BS1
- Shape: `(92,16,4)` complex64; groups: 23 spatial cells
- 368 unique UEs; four geometries per group; 25 m cells
- 16x1 BS, 1x1 UE, 10 paths, 0.5-wavelength spacing
- Frequency domain; 10 MHz; 512 total subcarriers; subcarrier 0
- No post-generation channel normalization
- SHA-256: `7b8ca0a588db002029aa5e746e3289f5ece72291dc2ac48a4591fc73fa61aaf7`
- Selection SHA-256: `a943bd266407e7fbcc52f2ab7301b94c64e9ef75842807781985746d49872fd2`
- CP03 lock SHA-256: `19259a0cc12b86160169a46b90f8e99140171c11d7e5549305dbdd5c16020567`
