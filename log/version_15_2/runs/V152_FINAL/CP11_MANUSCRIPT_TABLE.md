# V15.2 combined decision: **GO_PREDICTABLE_BREAK_EVEN**

Predicted region R = test geometries whose K_max early_ratio cell is locked to a non-CARD policy.

| Run | Source | Status | R groups | K | Frozen map rel. saving in R | CI95 | EARLY rel. saving in R | CI95 | Frozen abs. saving in R (ms) |
|---|---|---|---|---|---|---|---|---|---|
| V152_DM | DeepMIMO 4.0.5 external extraction | GO_BREAK_EVEN | 15 | 4 | 54.57% | [34.67, 74.89]% | 54.02% | [32.16, 73.53]% | 7.00 |
| V152_DM | DeepMIMO 4.0.5 external extraction | GO_BREAK_EVEN | 15 | 6 | 66.07% | [47.96, 81.27]% | 65.77% | [47.41, 82.27]% | 32.38 |
| V152_DM | DeepMIMO 4.0.5 external extraction | GO_BREAK_EVEN | 15 | 8 | 73.73% | [57.10, 86.45]% | 73.83% | [58.04, 87.15]% | 138.69 |
| V152_3GPP | Sionna_3GPP | GO_BREAK_EVEN | 15 | 4 | 41.99% | [30.86, 52.92]% | 41.87% | [30.19, 52.98]% | 7.06 |
| V152_3GPP | Sionna_3GPP | GO_BREAK_EVEN | 15 | 6 | 65.22% | [52.88, 74.36]% | 65.23% | [54.52, 74.46]% | 31.24 |
| V152_3GPP | Sionna_3GPP | GO_BREAK_EVEN | 15 | 8 | 83.57% | [75.90, 89.31]% | 83.63% | [76.32, 89.32]% | 126.69 |

- **V152_DM**: {'P1_break_even_in_region': True, 'P2_trend_in_region': True, 'P3_exactness': True, 'P4_no_missed_gain_outside_region': True}; EARLY trend K4→K8 in R: 19.81 pp, CI [9.66, 31.04] pp; outside R (15 groups) EARLY abs. saving -5.88 ms, CI [-7.95, -3.75]; reasons: none
- **V152_3GPP**: {'P1_break_even_in_region': True, 'P2_trend_in_region': True, 'P3_exactness': True, 'P4_no_missed_gain_outside_region': True}; EARLY trend K4→K8 in R: 41.76 pp, CI [34.50, 48.11] pp; outside R (15 groups) EARLY abs. saving -0.14 ms, CI [-0.19, -0.11]; reasons: none