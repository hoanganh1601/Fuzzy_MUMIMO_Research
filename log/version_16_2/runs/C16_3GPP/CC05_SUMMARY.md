# Compiled solver — C16_3GPP: **GO_COMPILED_BREAK_EVEN**

| Zone | K | Policy | n | Rel. saving | CI95 | CARD ms (sum over L) |
|---|---|---|---|---|---|---|
| R | 4 | EARLY | 15 | 80.56% | [61.89%, 93.63%] | 0.1029 |
| R | 4 | ROUTED | 15 | 80.23% | [61.32%, 93.50%] | 0.1029 |
| R | 6 | EARLY | 15 | 90.10% | [76.58%, 97.69%] | 0.7519 |
| R | 6 | ROUTED | 15 | 90.00% | [76.21%, 97.74%] | 0.7519 |
| R | 8 | EARLY | 15 | 97.83% | [95.80%, 99.25%] | 4.7884 |
| R | 8 | ROUTED | 15 | 97.82% | [95.87%, 99.28%] | 4.7884 |
| outside | 4 | EARLY | 15 | -0.27% | [-0.40%, -0.12%] | 0.0324 |
| outside | 4 | ROUTED | 15 | -1.19% | [-1.30%, -1.09%] | 0.0324 |
| outside | 6 | EARLY | 15 | -0.22% | [-0.31%, -0.13%] | 0.0701 |
| outside | 6 | ROUTED | 15 | -0.87% | [-0.96%, -0.79%] | 0.0701 |
| outside | 8 | EARLY | 15 | -0.09% | [-0.17%, -0.00%] | 0.1527 |
| outside | 8 | ROUTED | 15 | -0.48% | [-0.57%, -0.40%] | 0.1527 |

C1: 810 decisions checked; 0 differ only within floating-point sensitivity ({}); see CC06.
Input dtype complex64; V15.2 single-precision Python decisions vs double: 0 changes in 270 configurations, max relative power difference 7.747536833958508e-06

Median speed-up of the compiled CARD over Python CARD by K: {4: 606.5174547831768, 6: 218.86350294412674, 8: 87.19471412159238}