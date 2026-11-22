# Version 16.1 compiled run — C1 gate not met

The run reused the V15.2 lock after 31/31 unit tests passed. `compiled` completed on all three datasets. Curated top-level checkpoints are under `runs/C16_DEV`, `runs/C16_DM` and `runs/C16_3GPP`. `V16_1_compiled.log` is the console log. `reports/V16_1_compiled_C1_report_20261121.zip` contains six files selected for review.

| Run | Numeric events / decisions | Fraction | C1 | C2–C4 | Decision |
|---|---:|---:|---|---|---|
| C16_DEV | 1005 / 2889 | 34.79% | FAIL | PASS | `STOP_COMPILED` |
| C16_DM | 0 / 810 | 0% | PASS | PASS | `GO_COMPILED_BREAK_EVEN` |
| C16_3GPP | 162 / 810 | 20% | FAIL | PASS | `STOP_COMPILED` |

The C1 threshold in `HUONG_DAN_V16.md` is at most 1% **per dataset**. `CC06_numeric_events.csv` is absent for C16_DM because it had no events. Each event type is `POWER_WITHIN_FP_SENSITIVITY`; these are accepted by the V16.1 comparator but still counted against C1. Per-geometry task caches and PID files are omitted.

Read-only spot checks found that all logged event values have `rho(F) <= 0.6291` on development and `<= 0.1688` on 3GPP, far from 1. For one event in each dataset, the Python oracle on the stored `complex64` input reproduces the logged reference power, while computing on the same values promoted to `complex128` reproduces the compiled power. `native_search.Prepared` passes channel components as `float64` to C. This suggests a precision mismatch for at least those cases; it does not establish the cause of every event. The near-singular explanation in the supplied V16.1 changelog should be reviewed against these observed data before publication.

No official V16.1 overall conclusion has been established. The `model` and `natural` phases have not been run. Keep the frozen V15.2 source, lock and results unchanged; review C1 before deciding on another run or an amended protocol.
