# Version 09 run log

[DM_ASU35_SAFE_DEV_20261102](runs/DM_ASU35_SAFE_DEV_20261102/RUN.md): native safe pruning đối chiếu exhaustive trên 160 geometry DeepMIMO đã dùng ở các version trước. CP00–CP06 hoàn tất; 160/160 nghiệm khớp hoàn toàn, không phát hiện loại nhầm; trạng thái hồ sơ `ALGORITHM_CHECKS_PASSED_ON_DEVELOPMENT_DATA`.

Số lượt solve giảm 91.87%; mean runtime quan sát giảm 87.98%. Đây là số đo của run development, chưa phải kiểm chứng dữ liệu độc lập hoặc certificate outage/fairness.

Giữ nguyên byte cả bảy CP. CP06 gốc có sáu hash CP00–CP05; ARTIFACT_SHA256 bổ sung bao phủ cả CP06 và hồ sơ tái lập. Source commit đóng gói: `e2a3609950581a1d8e25bb5d2f7fe8f77408cfd1`. Không nhập output SMOKE ví dụ, task cache, real NPZ, scenario, môi trường, log console hoặc ZIP.
