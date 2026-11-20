# V15.2 combined decision: **GO_PREDICTABLE_BREAK_EVEN**

Predicted region R = test geometries whose K_max early_ratio cell is locked to a non-CARD policy.

| Run | Source | Status | R groups | K | Frozen map rel. saving in R | CI95 | EARLY rel. saving in R | CI95 | Frozen abs. saving in R (ms) |
|---|---|---|---|---|---|---|---|---|---|
| V152_DM | synthetic_dmp | GO_BREAK_EVEN | 12 | 4 | 58.17% | [41.49, 74.97]% | 58.17% | [42.01, 76.54]% | 3.94 |
| V152_DM | synthetic_dmp | GO_BREAK_EVEN | 12 | 6 | 74.25% | [65.85, 83.27]% | 74.36% | [65.57, 83.42]% | 16.85 |
| V152_DM | synthetic_dmp | GO_BREAK_EVEN | 12 | 8 | 85.31% | [80.44, 89.94]% | 85.31% | [80.29, 90.09]% | 69.91 |
| V152_3GPP | synthetic_gpp | GO_BREAK_EVEN | 12 | 4 | 46.01% | [26.74, 67.00]% | 44.86% | [25.22, 66.46]% | 3.34 |
| V152_3GPP | synthetic_gpp | GO_BREAK_EVEN | 12 | 6 | 56.69% | [39.66, 71.95]% | 56.95% | [39.57, 73.45]% | 14.70 |
| V152_3GPP | synthetic_gpp | GO_BREAK_EVEN | 12 | 8 | 70.04% | [52.21, 83.11]% | 70.04% | [51.32, 83.34]% | 62.01 |

- **V152_DM**: {'P1_break_even_in_region': True, 'P2_trend_in_region': True, 'P3_exactness': True, 'P4_no_missed_gain_outside_region': True}; EARLY trend K4→K8 in R: 27.13 pp, CI [12.60, 39.33] pp; outside R (12 groups) EARLY abs. saving -1.71 ms, CI [-2.82, -0.56]; reasons: none
- **V152_3GPP**: {'P1_break_even_in_region': True, 'P2_trend_in_region': True, 'P3_exactness': True, 'P4_no_missed_gain_outside_region': True}; EARLY trend K4→K8 in R: 25.19 pp, CI [8.92, 42.22] pp; outside R (12 groups) EARLY abs. saving -3.01 ms, CI [-5.15, -1.31]; reasons: none