# V17 power-budget sweep of the frozen map (compiled solver, fresh natural groups)

| Deployment | Pmax | Prevalence of R (Wilson) | Median harm. gain vs threshold (K_max) | Saving K=4 (all) | Saving K_max (all) | In R, K_max | Worst outside R | X1 | X3 | X5 | X6 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| UMI | 30 dBm | 0/100 = 0.0% [0.0%, 3.7%] | -104.9 vs -123.7 dB | -1.2% [-1.3%, -1.0%] | -0.1% [-0.1%, -0.0%] | — [—, —] | CI_lo -1.3% | True | True | None | True |
| UMI | 35 dBm | 0/100 = 0.0% [0.0%, 3.7%] | -104.9 vs -128.7 dB | -0.6% [-0.7%, -0.4%] | 0.1% [0.0%, 0.1%] | — [—, —] | CI_lo -0.7% | True | True | None | True |
| UMI | 46 dBm | 0/100 = 0.0% [0.0%, 3.7%] | -104.9 vs -139.7 dB | -0.7% [-0.8%, -0.5%] | -0.0% [-0.1%, 0.0%] | — [—, —] | CI_lo -0.8% | True | True | None | True |
| UMI | 49 dBm | 0/100 = 0.0% [0.0%, 3.7%] | -104.9 vs -142.7 dB | -1.0% [-1.1%, -0.9%] | -0.0% [-0.1%, 0.0%] | — [—, —] | CI_lo -1.1% | True | True | None | True |
| UMA | 30 dBm | 100/100 = 100.0% [96.3%, 100.0%] | -143.4 vs -123.7 dB | 81.5% [76.5%, 86.2%] | 97.0% [96.0%, 97.9%] | 97.0% [96.1%, 97.9%] | CI_lo — | True | True | True | None |
| UMA | 35 dBm | 99/100 = 99.0% [94.6%, 99.8%] | -143.4 vs -128.7 dB | 72.8% [66.6%, 78.3%] | 93.0% [90.3%, 95.3%] | 94.0% [92.2%, 95.5%] | CI_lo — | True | True | True | None |
| UMA | 46 dBm | 71/100 = 71.0% [61.5%, 79.0%] | -143.4 vs -139.7 dB | 27.9% [20.5%, 35.7%] | 53.7% [46.0%, 60.9%] | 75.6% [71.6%, 79.2%] | CI_lo -1.5% | True | True | True | True |
| UMA | 49 dBm | 56/100 = 56.0% [46.2%, 65.3%] | -143.4 vs -142.7 dB | 15.7% [9.8%, 22.6%] | 39.3% [32.1%, 46.6%] | 70.1% [65.8%, 74.3%] | CI_lo -1.3% | True | True | True | True |

Verdict by level: 30 dBm: **TRANSFER_OK**, 35 dBm: **TRANSFER_OK**, 46 dBm: **TRANSFER_OK**, 49 dBm: **TRANSFER_OK**