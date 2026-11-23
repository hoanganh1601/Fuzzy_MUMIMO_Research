# Compiled solver — C16_NAT2: **GO_COMPILED_BREAK_EVEN**

| Zone | K | Policy | n | Rel. saving | CI95 | CARD ms (sum over L) |
|---|---|---|---|---|---|---|
| R | 4 | EARLY | 99 | 83.22% | [77.79%, 87.75%] | 0.0771 |
| R | 4 | ROUTED | 99 | 82.96% | [77.65%, 87.52%] | 0.0771 |
| R | 6 | EARLY | 99 | 93.20% | [90.58%, 95.18%] | 0.5709 |
| R | 6 | ROUTED | 99 | 93.17% | [90.37%, 95.23%] | 0.5709 |
| R | 8 | EARLY | 99 | 96.85% | [96.01%, 97.69%] | 3.9879 |
| R | 8 | ROUTED | 99 | 96.85% | [95.87%, 97.70%] | 3.9879 |
| outside | 4 | EARLY | 1 | -0.27% | [—, —] | 0.0544 |
| outside | 4 | ROUTED | 1 | -0.30% | [—, —] | 0.0544 |
| outside | 6 | EARLY | 1 | -0.32% | [—, —] | 0.4145 |
| outside | 6 | ROUTED | 1 | 0.12% | [—, —] | 0.4145 |
| outside | 8 | EARLY | 1 | 0.31% | [—, —] | 2.7408 |
| outside | 8 | ROUTED | 1 | 0.52% | [—, —] | 2.7408 |

C1: 2700 decisions checked; 0 differ only within floating-point sensitivity ({}); see CC06.
Input dtype complex64; V15.2 single-precision Python decisions vs double: 0 changes in 900 configurations, max relative power difference 1.2505292111317812e-05

Median speed-up of the compiled CARD over Python CARD by K: {4: 459.1706341133158, 6: 159.745948037745, 8: 94.03960586751148}