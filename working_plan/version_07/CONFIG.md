# Cấu hình đã khóa trong CP00

Run ID: `DM_ASU35_BEAM_DIAG_20261031`.

```yaml
dataset_version: deepmimo_asu35_v1
scenario: asu_campus_3p5
shape: [160, 16, 4]
unique_groups: 160
dataset_sha256: 1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50
engine_sha256: 36a0ee286a5650c1adedd50c36bdd6fab5a6b46fc7911f2636310c2cfa071726
q_fixed: 2.9604143746015965
sigma_rel: 0.04
sinr_db: 6
noise_w: 2e-13
pmax_w: 1
alpha_grid: [0, 0.001, 0.01, 0.05, 0.1, 0.3, 1]
budget_factors: [0.3, 0.6, 1, 2, 5]
max_geometries: 0
```

Mọi beam dùng chung q, sigma, SINR, noise. Dãy alpha/ngân sách có trong manifest trước scan. q lấy từ run version 06 và không được tune lại trong diagnosis.
