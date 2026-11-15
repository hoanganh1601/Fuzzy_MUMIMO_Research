# DM_ASU35_COST_V13_20261112

## Configuration

- Code: Version 13, source commit `16cc1d71409af84d90f7f93c319cd14caa7bc533`
- Development: DeepMIMO `asu_campus_3p5`, 160 geometries/160 groups,
  SHA-256 `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`
- Test: DeepMIMO `city_0_newyork_3p5`, 160 geometries/40 spatial groups,
  SHA-256 `cf3a58de6a6519921e308753858798c61c94b11bca4faafac8afb1f49248d557`
- q: 2.960414; relative CSI uncertainty: 0.04; SINR: 6 dB
- Noise: `2e-13` W; Pmax: 1 W; guard: `1e-5`
- Alpha grid: 0, 0.001, 0.01, 0.05, 0.1, 0.3, 1
- Runtime repeats: 7; group-bootstrap draws: 2,000
- Development acceptance threshold: 95% lower runtime-saving bound `> 0.1` ms

## Development decision

`EARLY` saved 0.113859 ms on average, but its lower bound was 0.010739 ms,
below the locked 0.1 ms threshold. `CACHED` and `HYBRID` had negative mean
savings. CP02 therefore froze `CARD`; its SHA-256 is
`ede58de7c0f2791327b54e929e6da4921db17b8d5c870a3dec5bdc9ef1b8b5be`.

## Test data and preflight

The New York scenario is distinct from the ASU development scenario. A fixed
seed selected 640 unique UEs in 40 cells, four geometries per cell. Selection and
channel generation occurred after CP02 was sealed. CP03 recorded zero group-label
overlap and zero exact channel overlap with development. These controls do not
prove statistical independence.

## Result

- CP06: `STOP_NO_RUNTIME_GAIN`
- Locked test policy: `SELECTED_CARD`
- Mean runtime saving: 0 ms; mean call saving: 0
- Oracle mismatch: 0; no retraining on test
- CP08: 16,800 candidate rows; 10,762 oracle-feasible candidates; 5,915
  certificate rejections; zero false rejection
- CP07 checksum table: 8/8 referenced artifacts verified

The result confirms exactness over the implemented finite candidate family but
does not establish a runtime advantage.

## Native commands

The run used the same arguments for each stage:

```bash
python code/cost_aware_v13.py --stage <develop|preflight|scan|report> \
  --dev-dataset /path/to/deepmimo-development.npz \
  --test-dataset /path/to/deepmimo-v13-test.npz \
  --dev-provenance /path/to/development-provenance.json \
  --test-provenance /path/to/test-provenance.json \
  --run-id DM_ASU35_COST_V13_20261112 \
  --repeats 7 --bootstrap 2000
```

Development is run once. After CP02 exists, run `preflight`, `scan`, and
`report` without changing source, datasets, provenance, or parameters.
