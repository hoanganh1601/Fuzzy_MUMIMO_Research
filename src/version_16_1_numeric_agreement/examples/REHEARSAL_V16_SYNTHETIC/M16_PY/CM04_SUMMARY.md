# Break-even model — M16_PY (source: python, variant: obs)

Fitted on development only: t1_ms_per_size = 0.01451, t2_ms_per_size2 = 0, t3_ms_per_size3 = 0, c_E_ms_per_subset = 0.01508, c_0_ms = 0

| Set | n | R² (ms) | MAE (pp of CARD) | Spearman (rel.) | Sign agreement (all / where abs(measured) >= 2%) | Lemma 1: rejections / noisy positive timings (rows with early_ratio <= 1) | Lemma 2 violations |
|---|---|---|---|---|---|---|---|
| FIT | 720 | 0.982 | 7.90 | 0.928 | 97.2% / 98.9% (n=549) | 0 rej. / 20 gains of 396 | 0 |
| DM | 216 | 0.984 | 10.23 | 0.902 | 95.4% / 97.7% (n=173) | 0 rej. / 9 gains of 108 | 0 |
| 3GPP | 216 | 0.982 | 8.68 | 0.905 | 97.7% / 98.7% (n=155) | 0 rej. / 3 gains of 114 | 0 |

Population curve (model, development x pool): K=4: P(gain) 77%, mean 1.62 ms; K=6: P(gain) 93%, mean 12.89 ms; K=8: P(gain) 95%, mean 77.53 ms; K=10: P(gain) 99%, mean 436.50 ms; K=12: P(gain) 100%, mean 2200.47 ms