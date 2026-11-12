# Run card: GPP_V12

## Identity

- Code version: Version 12 robust SINR final validation
- Source: Sionna 2.2.0 official UMi model, 3GPP TR 38.901 V19.2
- Dataset SHA-256: `daac3826f568b9e4cf7cf6f8858a4fe6bdb9e46ce294b73a189bfbf1c9b47f18`
- Shape: 160 geometries, 16 BS antennas, 4 users
- Groups: 160 fresh topology-drop identifiers
- Carrier: 3.5 GHz; static outdoor UEs; pathloss and shadow fading enabled;
  frequency response not normalized

## Locked configuration

The screening configuration is identical to `DM_V12`: `q=2.960414`, relative
CSI uncertainty `0.04`, SINR `6 dB`, noise `2e-13 W`, `Pmax=1 W`, seven
ZF/RZF settings, guard `1e-5`, seven runtime repeats, and 2,000 bootstrap draws.
The channel-generation seed is `20261112`.

## Outcome

- Candidates audited: 16,800
- False prunes: 0
- Fail-open events: 0
- FAST mean full-solver calls saved: 1.7 per geometry
- FAST mean runtime saved: `-0.727140 ms`
- FAST descriptive 95% interval: `[-0.769253, -0.681935] ms`
- Decision: `STOP_NO_FAST_RUNTIME_ADVANTAGE`

CP07 signs CP00–CP06. The Sionna protocol was locked before this dataset was
generated and evaluated, but after the DeepMIMO result had been observed. No GPP
outcome was used for tuning; nevertheless this is not complete cross-source
preregistration or proof of statistical independence.
