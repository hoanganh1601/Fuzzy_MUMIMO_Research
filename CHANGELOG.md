# Changelog

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
