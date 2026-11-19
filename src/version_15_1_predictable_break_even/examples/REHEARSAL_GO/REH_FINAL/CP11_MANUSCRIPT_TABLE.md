# V15.1 combined decision: **GO_PREDICTABLE_BREAK_EVEN**

| Run | Source | K | Rel. saving (mean) | Rel. CI95 | Abs. saving ms | Abs. CI95 | Activated |
|---|---|---|---|---|---|---|---|
| REH_DM | synthetic_dmt | 4 | 26.10% | [8.1941, 45.1452]% | 1.6424 | [0.7567, 2.7820] | 40.0% |
| REH_DM | synthetic_dmt | 6 | 30.58% | [12.2988, 50.1771]% | 7.0970 | [3.3141, 11.6420] | 40.0% |
| REH_DM | synthetic_dmt | 8 | 34.37% | [12.1214, 57.1865]% | 27.4220 | [9.5914, 45.4939] | 40.0% |

REH_DM: endpoints {'E1_break_even_Kmax': True, 'E2_trend_in_K': True, 'E3_exactness': True, 'E4_predictability': True}; trend K4→K8 mean 8.27 pp, CI [0.0773, 18.0790] pp; status GO_BREAK_EVEN

| REH_3G | synthetic_gpt | 4 | 10.28% | [2.6874, 18.8122]% | 1.2940 | [0.3430, 2.3111] | 40.0% |
| REH_3G | synthetic_gpt | 6 | 21.21% | [8.3475, 36.4080]% | 5.6120 | [2.2205, 10.0574] | 46.7% |
| REH_3G | synthetic_gpt | 8 | 29.99% | [13.8451, 49.5196]% | 24.9994 | [9.1385, 42.0436] | 46.7% |

REH_3G: endpoints {'E1_break_even_Kmax': True, 'E2_trend_in_K': True, 'E3_exactness': True, 'E4_predictability': True}; trend K4→K8 mean 19.72 pp, CI [8.4811, 30.8282] pp; status GO_BREAK_EVEN
