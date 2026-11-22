# Compiled solver — C16_DM: **GO_COMPILED_BREAK_EVEN**

| Zone | K | Policy | n | Rel. saving | CI95 | CARD ms (sum over L) |
|---|---|---|---|---|---|---|
| R | 4 | EARLY | 15 | 72.13% | [52.52%, 89.08%] | 0.1109 |
| R | 4 | ROUTED | 15 | 71.96% | [50.66%, 90.61%] | 0.1109 |
| R | 6 | EARLY | 15 | 80.99% | [65.28%, 93.80%] | 0.8583 |
| R | 6 | ROUTED | 15 | 80.95% | [66.39%, 94.08%] | 0.8583 |
| R | 8 | EARLY | 15 | 85.71% | [73.00%, 96.42%] | 5.6595 |
| R | 8 | ROUTED | 15 | 85.72% | [72.63%, 96.20%] | 5.6595 |
| outside | 4 | EARLY | 15 | -0.25% | [-0.33%, -0.16%] | 0.0596 |
| outside | 4 | ROUTED | 15 | -0.92% | [-1.19%, -0.65%] | 0.0596 |
| outside | 6 | EARLY | 15 | -0.37% | [-0.43%, -0.30%] | 0.455 |
| outside | 6 | ROUTED | 15 | -0.37% | [-0.55%, -0.19%] | 0.455 |
| outside | 8 | EARLY | 15 | -0.30% | [-0.40%, -0.20%] | 3.4899 |
| outside | 8 | ROUTED | 15 | -0.13% | [-0.22%, -0.03%] | 3.4899 |

C1: 810 decisions checked; 0 differ only within floating-point sensitivity ({}); see CC06.

Median speed-up of the compiled CARD over Python CARD by K: {4: 539.5615584950922, 6: 192.78582809967295, 8: 103.25768194757578}