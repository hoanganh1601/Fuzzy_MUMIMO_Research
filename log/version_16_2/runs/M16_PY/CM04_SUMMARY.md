# Break-even model — M16_PY (source: python, variant: obs)

Fitted on development only: t1_ms_per_size = 0.03457, t2_ms_per_size2 = 0, t3_ms_per_size3 = 0, c_E_ms_per_subset = 0.05613, c_0_ms = 0

| Set | n | R² (ms) | MAE (pp of CARD) | Spearman (rel.) | Sign agreement (all / where abs(measured) >= 2%) | Lemma 1: rejections / noisy positive timings (rows with early_ratio <= 1) | Lemma 2 violations |
|---|---|---|---|---|---|---|---|
| FIT | 963 | 0.980 | 2.63 | 0.957 | 99.7% / 100.0% (n=809) | 0 rej. / 0 gains of 663 | 0 |
| DM | 270 | 0.977 | 10.24 | 0.938 | 99.6% / 100.0% (n=240) | 0 rej. / 1 gains of 147 | 0 |
| 3GPP | 270 | 0.979 | 9.14 | 0.940 | 99.3% / 100.0% (n=207) | 0 rej. / 2 gains of 144 | 0 |

Population curve (model, development x pool): K=4: P(gain) 18%, mean -0.17 ms; K=6: P(gain) 38%, mean 4.70 ms; K=8: P(gain) 50%, mean 41.57 ms; K=10: P(gain) 66%, mean 337.25 ms; K=12: P(gain) 75%, mean 2032.76 ms