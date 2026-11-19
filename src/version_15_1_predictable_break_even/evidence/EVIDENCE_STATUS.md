# Evidence scope and freeze status

- **V9–V10:** On 160 development geometries, 160/160 solutions matched finite-codebook exhaustive. V10 showed 19.3375 vs 8.5375 full solver calls per geometry; 20.4568 vs 18.9708 ms in that specific run. These runtime figures did not reproduce consistently.
- **V11:** Repeated runtime measurements: CARD 15.5838 ms, ALL 16.4046 ms, and 1,030 constructed boundary stress cases (0 false pruning, 324 fail-open). Retain the negative runtime finding.
- **V12:** On DeepMIMO holdout of 160 geometries, FAST saved -0.8026 ms vs CARD. On Sionna UMi of 160 topologies, FAST saved -0.7271 ms. In both, no false pruning in candidate audits; the external-source provenance and delay units still require verification against raw simulator output.
- **V13:** Development chose CARD. The test ran CARD vs CARD; the resulting zero/near-zero runtime difference cannot estimate EARLY/CACHED performance on test.
- **V14:** Development candidate rule did not pass its validation gate; frozen rule CARD. Denver test had 92 geometries in 23 spatial groups. No claimed V14 acceleration. Per-candidate profiling showed feasible candidates often cost more to solve than cheaply rejected infeasible candidates.
- **V15:** Program and synthetic smoke tests only. No real DeepMIMO or independent 3GPP V15 result available in this package; leave headline results and final conclusions pending.

Do not call the above statistical intervals certified probability guarantees: grouping assumptions and channel provenance require validation. This package retains the original result archives for independent recalculation and avoids merging different benchmark runs as though measured on the same hardware/session.
