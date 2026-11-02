# Cấu hình version 09 đã khóa trong CP00

Bản ghi hồi cứu của run `DM_ASU35_SAFE_DEV_20261102`.

```yaml
dataset_version: deepmimo_asu35_v1
dataset_role: development_reused_from_previous_versions
scenario: asu_campus_3p5
N: 160
M: 16
K: 4
groups: 160
limit: 0
q_fixed: 2.960414
sigma_rel: 0.04
sinr_db: 6
noise_w: 2e-13
pmax_w: 1
alpha_grid: [0, 0.001, 0.01, 0.05, 0.1, 0.3, 1]
candidates_per_geometry: 105
objective: maximize user count, then minimize transmit power within that count
native_stages: [preflight, scan, report]
```

Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`.
Safe pruning SHA-256: `d242114c9b45508592054ab39857ecd089816de375bf466b3dc35b35c2d29e0a`.
Reference SHA-256: `163bd7b2fb2b0a1333cf06d8b1f1df9624c2d75b3bf7b864b1fdf26e00b9bba3`.
Run signature: `5e97ac6eda78da4e0cbdb811b50ae1ad255069ff7d4be96341fb8bc2c6f66591`.

q dùng giá trị mặc định PDF version 09, khác giá trị đầy đủ của version 08. Không thay tham số sau CP00. Kênh giữ thang đo tuyệt đối, không chuẩn hóa lại. Dataset/scenario/selection NPZ nằm ngoài Git dưới `/media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/`.

Môi trường được người dùng báo cáo trước run: Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1. Manifest upstream không tự ghi thông tin môi trường; hồ sơ tái lập phân biệt thông tin người dùng cung cấp và kiểm tra tại thời điểm đóng gói.
