# V18 generality study — summary

Protocol V18.3; held-out drops only. Machine: Intel(R) Core(TM) i9-10900K CPU @ 3.70GHz.

## Endpoints per configuration

| Config | drops | in R | G1 exact | G2 LRS in R, K_max [CI] p | G3 worst CI lo outside R | G4 acc(eta>=1) | eta* [CI] | verdict | timing QC (discordant pairs) |
|---|---|---|---|---|---|---|---|---|---|
| M32_G10_E0.02 | 450 | 399 | True | 94.8% [94.2%, 95.4%] p=1e-05 | -1.3% | 99.5% (n=805) | 0.28 [0.28, 1.00] | PASS | PASS 0.11% (3/2700) |
| M32_G10_E0.04 | 450 | 400 | True | 94.7% [94.0%, 95.3%] p=1e-05 | -1.5% | 99.3% (n=816) | 1.00 [0.24, 1.00] | PASS | PASS 0.04% (1/2700) |

## Schedulers at K_max (all held-out drops, relative saving vs DCS, drop-level mean [CI95])

| Config | policy | saving | same decision | same cardinality | power solves (DCS) |
|---|---|---|---|---|---|
| M32_G10_E0.02 | PBS | 84.0% [81.5%, 86.3%] | 100.0% | 100.0% | 11.1 (415.0) |
| M32_G10_E0.02 | LRS | 84.0% [81.5%, 86.3%] | 100.0% | 100.0% | 11.1 (415.0) |
| M32_G10_E0.02 | LRSPUB | 84.0% [81.5%, 86.3%] | 100.0% | 100.0% | 11.1 (415.0) |
| M32_G10_E0.02 | CBD | 38.1% [36.2%, 40.0%] | 100.0% | 100.0% | 203.1 (415.0) |
| M32_G10_E0.02 | CBPBS | 84.1% [81.6%, 86.4%] | 100.0% | 100.0% | 11.1 (415.0) |
| M32_G10_E0.02 | ACS | -932.5% [-1122.3%, -760.8%] | 100.0% | 100.0% | 1063.1 (415.0) |
| M32_G10_E0.02 | ACSSTOP | -920.6% [-1089.6%, -760.0%] | 100.0% | 100.0% | 1163.4 (415.0) |
| M32_G10_E0.02 | GREEDY | -19.6% [-39.8%, -0.2%] | 100.0% | 100.0% | 163.7 (415.0) |
| M32_G10_E0.04 | PBS | 83.6% [80.7%, 86.3%] | 100.0% | 100.0% | 11.9 (421.8) |
| M32_G10_E0.04 | LRS | 84.1% [81.6%, 86.4%] | 100.0% | 100.0% | 11.9 (421.8) |
| M32_G10_E0.04 | LRSPUB | 84.1% [81.6%, 86.4%] | 100.0% | 100.0% | 11.9 (421.8) |
| M32_G10_E0.04 | CBD | 38.4% [36.5%, 40.3%] | 100.0% | 100.0% | 206.2 (421.8) |
| M32_G10_E0.04 | CBPBS | 84.1% [81.7%, 86.5%] | 100.0% | 100.0% | 11.9 (421.8) |
| M32_G10_E0.04 | ACS | -865.4% [-1034.7%, -704.3%] | 100.0% | 100.0% | 1059.4 (421.8) |
| M32_G10_E0.04 | ACSSTOP | -882.7% [-1051.7%, -722.7%] | 100.0% | 100.0% | 1161.1 (421.8) |
| M32_G10_E0.04 | GREEDY | -14.9% [-35.0%, 4.3%] | 100.0% | 100.0% | 163.4 (421.8) |

## Hierarchical statistics (LRS saving at K_max, all held-out drops)

| Config | stratified CI | two-level CI (scenes) | ICC | n_eff | drops for ±2 pp |
|---|---|---|---|---|---|
| M32_G10_E0.02 | 84.0% [81.5%, 86.5%] | [62.5%, 98.4%] (fewer than 5 scenes) | 0.348 | 8.5 | 48650 |
| M32_G10_E0.04 | 84.1% [81.6%, 86.5%] | [62.9%, 98.4%] (fewer than 5 scenes) | 0.343 | 8.6 | 47392 |

## Leave-one-scene-out (secondary, inferred LRS time)

- M32_G10_E0.02: RMA_F: map [2], mean 91.8%, min -4.3%; UMA_F: map [2], mean 98.5%, min 78.3%; UMI_F: map [2], mean 61.8%, min -3.9%
- M32_G10_E0.04: RMA_F: map [2], mean 91.7%, min -0.5%; UMA_F: map [2], mean 98.4%, min 78.3%; UMI_F: map [2], mean 62.2%, min -3.8%
