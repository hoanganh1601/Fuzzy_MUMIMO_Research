# Version 01: Fuzzy MU-MIMO R1

Đây là snapshot source của gói gốc `Fuzzy_MUMIMO_Research_R1_fixed.zip`, được khôi phục ngày 2026-11-02. Mã, test, fixture và tài liệu được giữ nguyên byte; không chỉnh thuật toán.

- Engine chính: `code/experiment.py`.
- Bốn phương pháp: Gaussian, fixed margin, threshold margin và Sugeno.
- Quy trình native: `preflight → develop → freeze → test → report`.
- Mục tiêu: đánh giá robust RZF power allocation trên slab uncertainty set, chọn tham số trên validation rồi khóa trước test.

[README gốc](README_UPSTREAM.md), [tài liệu nghiên cứu](docs/RESEARCH_AND_GUIDE_IEEE_VI_preview_article.pdf), [code review R1](docs/CODE_REVIEW_R1_VI.md), [thông tin nhập gói](UPSTREAM_IMPORT.json).

`UPSTREAM_FILE_SHA256.csv` là bảng hash nguyên gốc của ZIP. Bảng đó còn liệt kê bundled smoke outputs; các output mẫu và task cache không được nhập vào `src/`. `SOURCE_SHA256.csv` bao phủ snapshot source thực tế trong repo.

Replay DeepMIMO 160 geometry được lưu tại [`log/version_01`](../../log/version_01/README.md). Dữ liệu này đã được dùng ở các version sau, nên replay là tái dựng lịch sử trên development data, không phải holdout độc lập.
