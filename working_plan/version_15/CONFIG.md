# Version 15 smoke configuration

- Scope: synthetic software smoke only
- Development seed/prefix: 12 / `DEV`
- Test seed/prefix: 34 / `TEST`
- Generated development/test geometries: 12 / 8
- Run limit: 4 geometries from each source
- Input shape: `(N,16,8)` complex
- K: 4, 6, 8
- Beam count L: 3
- Alpha prefix: 0, 0.001, 0.01
- q: 2.960414
- Relative CSI uncertainty: 0.04
- SINR target: 6 dB
- Noise: 2e-13 W
- Pmax: 1 W
- Runtime repeats: 2
- Bootstrap draws: 100
- Minimum gain: 0.1 ms
- Minimum cell groups: 1
- Protocol seed: 20261117
- Run ID: `V15_SMOKE`

Development NPZ SHA-256:
`3f71fab89857553bb0961c1ff32b3d00f71663e7c31278f891b302446537694b`.

Test NPZ SHA-256:
`99e75f4825a901af5db7e288a57faf814cd7c4e4256f6ec335c02a0a4de50a6e`.
