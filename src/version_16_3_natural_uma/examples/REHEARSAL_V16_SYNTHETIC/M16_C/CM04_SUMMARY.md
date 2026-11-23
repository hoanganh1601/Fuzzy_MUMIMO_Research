# Break-even model — M16_C (source: compiled, variant: obs)

Fitted on development only: t1_ms_per_size = 6.105e-05, t2_ms_per_size2 = 4.618e-05, t3_ms_per_size3 = 0, c_E_ms_per_subset = 6.128e-05, c_0_ms = 0

| Set | n | R² (ms) | MAE (pp of CARD) | Spearman (rel.) | Sign agreement (all / where abs(measured) >= 2%) | Lemma 1: rejections / noisy positive timings (rows with early_ratio <= 1) | Lemma 2 violations |
|---|---|---|---|---|---|---|---|
| FIT | 720 | 0.991 | 2.92 | 0.828 | 82.1% / 95.8% (n=361) | 0 rej. / 129 gains of 396 | 0 |
| DM | 216 | 0.952 | 3.75 | 0.840 | 87.5% / 95.9% (n=123) | 0 rej. / 27 gains of 108 | 0 |
| 3GPP | 216 | 0.980 | 3.76 | 0.837 | 77.3% / 90.6% (n=127) | 0 rej. / 49 gains of 114 | 0 |

Population curve (model, development x pool): K=4: P(gain) 77%, mean 0.02 ms; K=6: P(gain) 93%, mean 0.22 ms; K=8: P(gain) 95%, mean 1.54 ms; K=10: P(gain) 99%, mean 9.97 ms; K=12: P(gain) 100%, mean 56.94 ms