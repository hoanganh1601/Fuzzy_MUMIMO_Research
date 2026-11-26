# V18 — hardware comparison of the cost model and the cost bound

| Machine | CPU | t1 (ms) | c_E (ms) | dev R2 | held-out R2 | sign acc (|saving|>2%) | bound validity | eta* [CI] | acc(eta>=1) |
|---|---|---|---|---|---|---|---|---|---|
| HW_icnlab-Pro-E500-G6-WS720T_f60f0f | Intel(R) Core(TM) i9-10900K CPU @ 3.70GHz | 6.817e-05 | 2.189e-05 | 0.999 | 0.980 | 0.998 | 0.945 | 1.000 [0.006, 1.000] | 0.999 |

## Transfer: coefficients of machine A applied to machine B with one speed factor (ratio of median DCS times on development drops)

| A -> B | speed factor | R2 on B held-out | sign acc on B (|saving|>2%) |
|---|---|---|---|
