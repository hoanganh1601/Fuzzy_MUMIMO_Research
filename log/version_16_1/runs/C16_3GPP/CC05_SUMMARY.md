# Compiled solver — C16_3GPP: **STOP_COMPILED**

| Zone | K | Policy | n | Rel. saving | CI95 | CARD ms (sum over L) |
|---|---|---|---|---|---|---|
| R | 4 | EARLY | 15 | 80.61% | [62.03%, 93.65%] | 0.1003 |
| R | 4 | ROUTED | 15 | 80.28% | [61.41%, 93.51%] | 0.1003 |
| R | 6 | EARLY | 15 | 90.10% | [76.56%, 97.70%] | 0.738 |
| R | 6 | ROUTED | 15 | 90.05% | [76.38%, 97.75%] | 0.738 |
| R | 8 | EARLY | 15 | 97.82% | [95.77%, 99.26%] | 4.6886 |
| R | 8 | ROUTED | 15 | 97.81% | [95.84%, 99.28%] | 4.6886 |
| outside | 4 | EARLY | 15 | -0.05% | [-0.12%, 0.04%] | 0.0212 |
| outside | 4 | ROUTED | 15 | -1.21% | [-1.32%, -1.11%] | 0.0212 |
| outside | 6 | EARLY | 15 | -0.13% | [-0.18%, -0.06%] | 0.0464 |
| outside | 6 | ROUTED | 15 | -0.72% | [-0.78%, -0.66%] | 0.0464 |
| outside | 8 | EARLY | 15 | -0.05% | [-0.16%, 0.07%] | 0.1137 |
| outside | 8 | ROUTED | 15 | -0.49% | [-0.56%, -0.42%] | 0.1137 |

C1: 810 decisions checked; 162 differ only within floating-point sensitivity ({'POWER_WITHIN_FP_SENSITIVITY': 162}); see CC06.

Median speed-up of the compiled CARD over Python CARD by K: {4: 995.7858163220073, 6: 232.25452813956792, 8: 104.33095920727166}