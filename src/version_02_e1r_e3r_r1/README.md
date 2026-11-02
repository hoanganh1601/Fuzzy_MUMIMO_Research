# Version 02: E1R–E3R reliability-screened Sugeno

Đây là snapshot source của gói gốc `Fuzzy_MUMIMO_E1R_E3R_R1_fixed.zip`, được khôi phục ngày 2026-11-02. Gói kế thừa engine version 01 và bổ sung `code/experiment_r.py`, test pipeline cùng hướng dẫn E1R–E3R. Mã gốc không bị chỉnh sửa.

- Năm phương pháp: Gaussian, fixed, threshold, fuzzy_raw và fuzzy_safe.
- Split theo group: 40/20/20/20 cho development/validation/calibration/test.
- Quy trình native: `preflight → develop → calibrate → freeze → test → report`.
- Quy tắc fail-closed: nếu fuzzy_safe không qua calibration thì khóa về Gaussian-equivalent fallback.

[README E1R–E3R gốc](README_E1R_E3R_UPSTREAM.md), [README engine nền](README_BASE_UPSTREAM.md), [tài liệu E1R–E3R](docs/RESEARCH_GUIDE_E1R_E3R_IEEE_VI_preview_article.pdf), [code review R1](docs/CODE_REVIEW_E1R_E3R_R1_VI.md), [thông tin nhập gói](UPSTREAM_IMPORT.json).

`UPSTREAM_FILE_SHA256.csv` là bảng hash nguyên gốc của ZIP và còn liệt kê bundled smoke outputs. Các output mẫu/task cache không được nhập vào `src/`; `SOURCE_SHA256.csv` bao phủ source thực tế trong repo.

Replay DeepMIMO 160 geometry được lưu tại [`log/version_02`](../../log/version_02/README.md). Đây là dữ liệu dùng lại, nên quyết định chỉ là tái dựng lịch sử trên development data.
