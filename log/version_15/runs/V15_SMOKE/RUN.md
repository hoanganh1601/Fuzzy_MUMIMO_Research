# Run: V15_SMOKE

## Identity

- Code version: 15
- Source commit: `7632acc77b77966b967a0d7b2af40853858eb0f6`
- Source tag: `v15.0.0`
- Final checkpoint: CP09
- Decision: `SMOKE_ONLY`

## Inputs and configuration

- Development: synthetic seed 12, SHA-256
  `3f71fab89857553bb0961c1ff32b3d00f71663e7c31278f891b302446537694b`
- Test: synthetic seed 34, SHA-256
  `99e75f4825a901af5db7e288a57faf814cd7c4e4256f6ec335c02a0a4de50a6e`
- Four geometries per source after `--limit 4`
- K: 4, 6, 8
- L: 3
- Runtime repeats: 2
- Bootstrap draws: 100
- Minimum cell groups: 1
- Smoke flag: enabled

## Outcome

- CP01 development rows: 96
- CP02 paired rows: 36
- CP03 validation cells: 8
- Locked policy: `CARD` in every observed cell
- CP05 test rows: 96
- CP06 paired rows: 36
- CP07 frozen-policy rows: 12; summary rows: 3
- Oracle mismatch: 0
- Final status: `SMOKE_ONLY`

All three configurations report zero frozen-policy savings because no non-CARD
cell was activated. This outcome is a software-flow check and must not be cited
as independent channel validation or computational superiority.
