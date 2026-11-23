# Break-even model — M16_C (source: compiled, variant: obs)

Fitted on development only: t1_ms_per_size = 0.0004688, t2_ms_per_size2 = 0, t3_ms_per_size3 = 3.397e-06, c_E_ms_per_subset = 3.193e-05, c_0_ms = 0.004928

| Set | n | R² (ms) | MAE (pp of CARD) | Spearman (rel.) | Sign agreement (all / where abs(measured) >= 2%) | Lemma 1: rejections / noisy positive timings (rows with early_ratio <= 1) | Lemma 2 violations |
|---|---|---|---|---|---|---|---|
| FIT | 963 | 0.919 | 12.60 | 0.708 | 88.5% / 100.0% (n=298) | 0 rej. / 111 gains of 663 | 0 |
| DM | 270 | 0.917 | 20.70 | 0.802 | 84.8% / 99.2% (n=124) | 0 rej. / 41 gains of 147 | 0 |
| 3GPP | 270 | 0.884 | 38.11 | 0.772 | 87.0% / 100.0% (n=126) | 0 rej. / 35 gains of 144 | 0 |

Population curve (model, development x pool): K=4: P(gain) 18%, mean 0.00 ms; K=6: P(gain) 40%, mean 0.12 ms; K=8: P(gain) 52%, mean 0.90 ms; K=10: P(gain) 70%, mean 6.83 ms; K=12: P(gain) 78%, mean 42.32 ms