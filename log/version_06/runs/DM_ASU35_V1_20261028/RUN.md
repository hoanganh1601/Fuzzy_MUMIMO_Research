# Run DM_ASU35_V1_20261028

## Identity

```yaml
code_version: version_06
dataset_version: deepmimo_asu35_v1
scenario: asu_campus_3p5
run_id: DM_ASU35_V1_20261028
dataset_sha256: 1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50
status: CP05_FAIL
```

## Locked configuration

```yaml
M: 16
K: 4
seed: 20261028
sigma_rel: 0.04
sinr_db: 6
noise_w: 2.0e-13
pmax_w: 1
epsilon: 0.05
alpha: 0.05
mc: 100
min_center_distance_m: 10
```

## Split and result

```yaml
development_groups: 40
calibration_groups: 80
test_groups: 40
locked_q: 2.9604143746015965
calibration_feasible: 41
calibration_failures: 39
calibration_failure_rate: 0.4875
upper_95_one_sided: 0.5848050192029324
eligible: false
```

Trong 39 calibration failures, 32 geometry có coupling spectral radius `rho >= 1`; 7 geometry có `rho < 1` nhưng yêu cầu tổng công suất lớn hơn `1 W`. Không có conditional SINR outage trong 41 geometry khả thi.

## Interpretation

Run không đạt certificate 5%. Không retune bằng chính calibration split này. Test/transfer, nếu chạy, chỉ được mô tả là exploratory sau failure.
