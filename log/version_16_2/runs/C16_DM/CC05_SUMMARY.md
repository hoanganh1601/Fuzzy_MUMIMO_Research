# Compiled solver — C16_DM: **GO_COMPILED_BREAK_EVEN**

| Zone | K | Policy | n | Rel. saving | CI95 | CARD ms (sum over L) |
|---|---|---|---|---|---|---|
| R | 4 | EARLY | 15 | 72.23% | [52.66%, 89.11%] | 0.1614 |
| R | 4 | ROUTED | 15 | 72.03% | [50.79%, 90.67%] | 0.1614 |
| R | 6 | EARLY | 15 | 81.04% | [65.31%, 93.83%] | 1.2696 |
| R | 6 | ROUTED | 15 | 81.03% | [66.42%, 94.11%] | 1.2696 |
| R | 8 | EARLY | 15 | 85.75% | [73.19%, 96.42%] | 8.3581 |
| R | 8 | ROUTED | 15 | 85.76% | [72.71%, 96.20%] | 8.3581 |
| outside | 4 | EARLY | 15 | -0.22% | [-0.31%, -0.13%] | 0.1018 |
| outside | 4 | ROUTED | 15 | -0.68% | [-0.94%, -0.43%] | 0.1018 |
| outside | 6 | EARLY | 15 | -0.22% | [-0.35%, -0.04%] | 0.7681 |
| outside | 6 | ROUTED | 15 | -0.24% | [-0.37%, -0.11%] | 0.7681 |
| outside | 8 | EARLY | 15 | -0.15% | [-0.26%, -0.05%] | 5.7978 |
| outside | 8 | ROUTED | 15 | -0.03% | [-0.16%, 0.10%] | 5.7978 |

C1: 810 decisions checked; 0 differ only within floating-point sensitivity ({}); see CC06.
Input dtype complex128

Median speed-up of the compiled CARD over Python CARD by K: {4: 348.673142343059, 6: 146.21083577617242, 8: 67.06138535608565}