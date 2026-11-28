# V18 re-timing report

Reason: timing QC of the first run failed (identical-path discordance above 1%); decisions are not re-run

QC rule: identical-path pairs (LRS vs the DCS or PBS search it executes) differing by more than 1.5x must be <= 1%

Reporting rule: the re-timed run replaces the original runtime endpoints only if its timing QC passes and every decision equals the original run; otherwise both runs are reported and the configuration is marked timing-unresolved. Decisions (G1, G4 inputs) of the original run are kept.

| Config | decisions identical | QC original | QC re-timed | G2 lo orig -> new | G3 worst lo orig -> new | verdict orig -> new | reported run |
|---|---|---|---|---|---|---|---|
| M32_G10_E0.02 | True | 9.19% | 0.11% | 93.1% -> 94.2% | -31.9% -> -1.3% | FAIL -> PASS | re-timed |
| M32_G10_E0.04 | True | 5.93% | 0.04% | 93.9% -> 94.0% | -17.1% -> -1.5% | FAIL -> PASS | re-timed |
