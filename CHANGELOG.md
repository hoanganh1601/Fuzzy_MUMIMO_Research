# Changelog

## v2.0.0 — restored 2026-11-02; original revision 2026-10-21

- Khôi phục nguyên source/test/tài liệu từ `Fuzzy_MUMIMO_E1R_E3R_R1_fixed.zip`.
- Chạy 9 test engine và 7 test E1R–E3R; toàn bộ PASS.
- Replay native trên 160 geometry DeepMIMO với split 40/20/20/20; calibration không có phương pháp đạt effective-failure gate 5%.
- Fuzzy-safe chuyển sang Gaussian-equivalent fail-closed fallback; test kết thúc `STOP_no_demonstrated_fuzzy_advantage`.
- Lưu CP00–CP09, provenance và checksum; ghi rõ đây là dữ liệu dùng lại.

## v1.0.0 — restored 2026-11-02; original revision 2026-10-19

- Khôi phục nguyên source/test/tài liệu từ `Fuzzy_MUMIMO_Research_R1_fixed.zip`.
- Chạy 9 test gốc; toàn bộ PASS.
- Replay native trên 160 geometry DeepMIMO với split train/validation/test 96/32/32.
- Cả bốn phương pháp chỉ khả thi 15/32 geometry test; effective failure vượt xa mục tiêu 5%.
- Lưu CP00–CP06, provenance và checksum; không nhập bundled smoke output/task cache.

## v9.0.0 — 2026-11-02

- Nhập nguyên source safe pruning/reference, tests và IEEE guide từ ZIP ngày 2026-11-02; dùng native preflight/scan/report, không có runner tách CP.
- Giữ q=2.960414 đúng mặc định PDF; lưu run DeepMIMO development 160 geometry với đủ CP00–CP06.
- Khớp nghiệm exhaustive 160/160, không phát hiện loại nhầm ứng viên khả thi trong run; giảm 91.87% lượt solve và 87.98% mean runtime quan sát.
- Phân biệt 1,728 candidate bị loại bằng điều kiện sàng lọc và 13,706 candidate kích thước nhỏ hơn được bỏ theo mục tiêu từ điển.
- Kiểm tra hai test gốc, source/run hashes, provenance và byte preservation; không nhập real data, task cache, môi trường hoặc output SMOKE ví dụ.
- Ghi rõ reused development data, phạm vi finite beam family và các giới hạn về kiểm chứng độc lập, runtime, outage/fairness.

## v8.0.0 — 2026-11-02

- Đóng gói source/IEEE guide ngày 2026-11-01 cho robust user scheduling với fixed CSI margin.
- Giữ nguyên engine upstream; thêm workflow riêng từng CP và G1 independent scaled-LP/budget audit.
- Lưu smoke 12 geometry và DeepMIMO development 160 geometry, cùng hoàn tất CP00–CP06.
- Exhaustive/forward/backward cùng mean admitted users=3.575 trên DeepMIMO; backward khớp nghiệm trong run và dùng 18% số lời gọi exhaustive.
- Ghi nhận forward ít lời gọi hơn nhưng runtime cao hơn và có một power-ratio outlier; không tuyên bố cải thiện chung.
- Thêm kiểm thử workflow, provenance/checksum và hướng dẫn tái chạy; trạng thái `EXPLORATORY_EVALUATION`, G4 chưa được xác minh.

## v6.0.0 — 2026-10-29

- Thêm spatial group metadata `xyz` và `scenario`.
- Tách `preflight/develop/calibrate/freeze/test/transfer/report`.
- Thêm resumable per-geometry task checkpoints và source/dataset fingerprint.
- Thêm trình chuẩn bị DeepMIMO 4.0.5 với provenance.
- Ghi nhận run thật `DM_ASU35_V1_20261028`: CP05 FAIL, 39/80 failures.
- Tổ chức repository thành `src/`, `log/`, `working_plan/`.

## v5.0.0 — 2026-10-23

- Thêm CSI uncertainty-margin calibration pilot.
- Thêm one-sided Clopper--Pearson calibration gate.
- Thêm CP05 failure report cho smoke gate.

## v4.0.0 — 2026-10-19

- Thêm spatially grouped DeepMIMO dataset generator.

## v3.0.0 — 2026-10-19

- Thêm DeepMIMO coverage và spatial-block analysis.
