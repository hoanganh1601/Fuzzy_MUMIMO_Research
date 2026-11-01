# Cấu hình được khóa trong CP00

Hai run: `SYN_SCHED_SMOKE_20261101` và `DM_ASU35_SCHED_DEV_20261101`.

```yaml
K: 4
M: 16
q_fixed: 2.9604143746015965
sigma_rel: 0.04
sinr_db: 6
noise_w: 2e-13
pmax_w: 1
alpha_grid: [0, 0.001, 0.01, 0.05, 0.1, 0.3, 1]
subsets_per_geometry: 15
objective: maximize user count, then minimize power within that count
methods: [exhaustive, forward, backward]
engine_sha256: 163bd7b2fb2b0a1333cf06d8b1f1df9624c2d75b3bf7b864b1fdf26e00b9bba3
```

Smoke: fixture có 24 geometry, limit=12; sha_data=`c52e1551158a6556ad8161db560864244beb6958c7e90adac119a4708f4bd2f9`.

DeepMIMO: scenario `asu_campus_3p5`, shape `(160,16,4)`, groups=160, limit=0; sha_data=`1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`. Không chuẩn hóa lại kênh; provenance giữ thang đo tuyệt đối. Nguồn nằm dưới `/media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/`.

q lấy từ run trước và không tune lại từ kết quả scheduling. G1 thử ngân sách khác để kiểm tra toán học, không thay Pmax=1 W của bài toán lựa chọn.
