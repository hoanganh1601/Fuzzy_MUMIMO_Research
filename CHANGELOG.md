# Changelog

## v15.2.0 — 2026-11-20

- Nhập source, 22 unit test, three-phase runner, Vietnamese guide, paper,
  synthetic rehearsal và evidence index của V15.2.
- Development dùng 107 group ASU; mọi ô ER2 được khóa non-CARD trước khi tạo
  hoặc chọn test. Không thay đổi code, threshold hay policy sau CP03.
- Tạo pool mới sau lock: 107 group DeepMIMO Los Angeles và 120 group Sionna 3GPP
  UMi mixed-distance; cả hai ghi `prior_use=never_seen`.
- Chọn bằng frozen covariates, không dùng runtime: mỗi nguồn 15 group trong `R`
  và 15 group ngoài `R`; cả hai vượt cổng vùng 10 group.
- DeepMIMO và 3GPP đều đạt P1–P4, zero oracle mismatch và `GO_BREAK_EVEN`; tại
  K=8 trong `R`, mean saving lần lượt là 73.73% và 83.57%.
- Combined decision là `GO_PREDICTABLE_BREAK_EVEN`; kết quả hỗ trợ prototype/
  monitored pilot, không phải chứng nhận production hoặc unrestricted precoding.
- Lưu 30 checkpoint/report files, provenance và ZIP; loại real matrices,
  downloaded scenarios, task cache, console log, PID và environments.

## v15.1.0 — 2026-11-19

- Nhập source, tests, synthetic smoke workflow, official runner, Vietnamese
  guide, paper, examples và evidence index của V15.1.
- Chạy 14/14 unit test; development dùng 41 group ASU và khóa policy theo
  `(K,L,early_ratio)` trước khi mở hai nhánh test.
- Chạy test mới trên 11 group DeepMIMO Phoenix và 15 group Sionna 3GPP UMi với
  cùng frozen lock; CP04 ghi zero group/exact-channel overlap.
- Cả hai nguồn có zero oracle mismatch và E3 đạt, nhưng không geometry nào kích
  hoạt ER2; solver-call saving bằng 0 và runtime saving K=8 âm.
- E1, E2 và E4 không đạt trên cả hai nguồn; combined decision là `STOP`.
- Lưu 26 checkpoint, provenance và report ZIP; loại real channel matrices,
  downloaded scenarios, per-geometry tasks, bytecode, logs, PID và environments.

## v15.0.0 — 2026-11-18

- Nhập subset source V15 cần cho smoke workflow trong IEEE guide: unified
  entrypoint, dependency, synthetic generator/fixtures, test, guide và launcher.
- Bảo toàn byte-for-byte 29 file upstream thuộc phạm vi smoke; loại bytecode,
  per-geometry task cache, official runner/packer, evidence archive và paper.
- Chạy 4/4 unit test và pipeline synthetic với K=4,6,8, L=3, bốn geometry mỗi
  nguồn; lưu 12 checkpoint CP00--CP09.
- CP03 khóa toàn bộ cell về CARD; CP08 ghi zero oracle mismatch và `SMOKE_ONLY`.
- Lưu report ZIP và checksum curated artifact; không nhập ASU/Singapore run,
  real matrices, logs, PID hoặc environment.
- Ghi rõ smoke chỉ xác minh chương trình, không phải independent validation hay
  bằng chứng computational superiority.

## v14.0.0 — 2026-11-18

- Nhập source robust cost limits, 11 unit test, IEEE guide, smoke fixtures và
  PowerShell runner; bảo toàn 38 file upstream ngoài 40 task-cache JSON.
- Profile bốn policy trên 160 geometry ASU, fit/validation 96/64 group; rule
  `EARLY` không qua gate cận dưới 0.1 ms nên CP03 khóa `CARD`.
- Sau khi khóa rule, sinh test DeepMIMO Denver mới gồm 92 geometry, 23 spatial
  group và 368 UE không lặp; lưu selection/channel generation code và provenance.
- CP04 ghi nhận zero group/exact-channel overlap; CP06 kiểm toán 9.660 ứng viên
  với zero false certificate và CP08 có zero oracle mismatch.
- Test không kích hoạt screening, không tiết kiệm solver call và có runtime CI95
  hoàn toàn không dương; kết luận `STOP_NO_RUNTIME_GAIN`.
- Lưu CP00–CP09, report ZIP và provenance; loại real matrices, selection arrays,
  downloaded scenario, task caches, logs, PID và environment. Chưa chạy nhánh
  transfer 3GPP thứ hai.

## v13.0.0 — 2026-11-15

- Nhập nguyên source cost-aware screening, 5 unit test, IEEE guide, smoke fixtures,
  PowerShell runner và manuscript examples; bảo toàn 28/28 file upstream.
- Chạy development trên 160 geometry ASU với bảy lần lặp và 2.000 bootstrap draws;
  không policy screening nào vượt cận dưới 0.1 ms nên CP02 khóa `CARD`.
- Niêm phong CP02 trước khi chọn/sinh test DeepMIMO New York mới gồm 160 geometry,
  40 spatial group và 640 UE không lặp; lưu generation code và provenance hash.
- CP03 xác nhận zero group/exact-channel overlap với development; CP08 kiểm toán
  16.800 ứng viên với zero false rejection và zero oracle mismatch.
- CP06 trả `STOP_NO_RUNTIME_GAIN`; không tuyên bố tăng tốc khi baseline CARD được
  chọn. Giữ kết luận exactness của finite candidate family và các giới hạn khoa học.
- Lưu CP01–CP08, report ZIP, provenance và checksum; loại real channel matrices,
  selection arrays, downloaded scenario, per-geometry tasks, logs, PID và environment.

## v12.0.0 — 2026-11-12

- Nhập source final-validation, 12 unit test, IEEE guide, PowerShell launcher và provenance templates; bảo toàn 24 file upstream ngoài bundled smoke output/task cache.
- Chạy boundary stress trên 1.020 ca: 0 false prune, 323 fail-open, kết quả PASS.
- Chạy DeepMIMO mới `city_37_seoul_3p5` trên 160 geometry/40 spatial group: zero false prune nhưng FAST chậm hơn cardinality-only 0.803 ms, CI95 hoàn toàn âm.
- Sinh nguồn Sionna 2.2.0 UMi theo 3GPP TR 38.901 V19.2 và chạy 160 geometry: zero false prune nhưng FAST chậm hơn 0.727 ms, CI95 hoàn toàn âm.
- Final gate trả `STOP_MANUSCRIPT_NOT_LOCKED`; giữ kết luận exactness của finite candidate family nhưng không tuyên bố runtime superiority.
- Lưu 21 checkpoint, provenance và report ZIP; loại real matrices, downloaded scenarios, per-geometry tasks, logs, PID và environments.
- Ghi rõ protocol 3GPP được khóa trước chính GPP generation/evaluation nhưng sau khi đã thấy kết quả DeepMIMO.

## v11.0.0 — 2026-11-10

- Nhập source R2 ngày 2026-11-06, IEEE boundary/independent guide, Windows launcher, five-test-module suite và smoke decision fingerprint.
- Chạy 23/23 test PASS và fingerprint MATCH trên Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1.
- Chạy A+B trên 160 geometry DeepMIMO development với năm runtime repeats: 160/160 exact, 0 false prune, giảm 55.85% full solves so với cardinality-only.
- Ghi nhận ALL chậm hơn cardinality-only 5.27%; không xác nhận runtime advantage. Boundary C PASS trên 1.030 ca với 324 fail-open.
- Hoàn tất locked synthetic D rehearsal: AUDIT_PASS, 0 false prune, giảm solver calls nhưng runtime chậm hơn 5.47%; không gọi đây là independent DeepMIMO/3GPP validation.
- Lưu CP chọn lọc, manuscript tables, ENV check, provenance và checksum; loại task cache, console log và real channel matrices.

## v10.0.0 — 2026-11-04

- Nhập source, tests và IEEE guide của certified safe-pruning ablation audit; giữ nguyên các chương trình reference/version trước để kiểm toán.
- Thêm bảy cấu hình ablation, exhaustive reference độc lập với quyết định pruning, fail-open sát ngưỡng, chẩn đoán 70 chữ số và checkpoint nguyên tử có chữ ký.
- Chạy 5/5 unit test và native preflight/scan/report trên 160 geometry DeepMIMO development; lưu CP00–CP07.
- Kiểm toán 16.800 ứng viên, khớp exhaustive trên 160/160 geometry và không phát hiện false prune.
- So với CARDINALITY_ONLY, ALL tiết kiệm trung bình 10.8 full solver calls và 1.486 ms/geometry; descriptive bootstrap runtime 95% `[1.0599, 1.9279]` ms.
- Ghi rõ dữ liệu đã được quan sát trước đó, finite candidate scope, high-precision diagnostic không phải interval proof và chưa có independent 3GPP validation.

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
