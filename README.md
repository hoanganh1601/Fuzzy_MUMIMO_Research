# Fuzzy MU-MIMO Research

Kho nghiên cứu được tổ chức theo ba lớp độc lập:

- `src/`: mã nguồn bất biến theo từng code version.
- `log/`: kết quả chạy đã chọn lọc, trạng thái PASS/FAIL và provenance; không chứa task checkpoint lớn.
- `working_plan/`: mục tiêu, cấu hình và tiêu chí chấp nhận; mỗi bản ghi nêu rõ được lập trước hay sau run.

## Version index

| Version | Nội dung | Mốc gốc | Trạng thái |
|---|---|---|---|
| `version_03` | DeepMIMO spatial analysis | `089ab5a` | Historical |
| `version_04` | Spatially grouped DeepMIMO generator | `2aa366f` | Historical |
| `version_05` | CSI margin calibration pilot | `b51505e` | CP05 failure documented |
| `version_06` | Spatial CSI calibration with `xyz/scenario` metadata | `0642020` | Real DeepMIMO CP05 FAIL |
| `version_07` | Fixed-margin ZF/RZF feasibility diagnosis, từng CP | `6439c5e` | CP00–CP06 complete; DIAGNOSTIC_ONLY |
| `version_08` | Robust user scheduling + finite ZF/RZF codebook, từng CP | `2137c3e` | Smoke + DeepMIMO CP00–CP06 complete; EXPLORATORY_EVALUATION |
| `version_09` | Safe pruning đối chiếu exhaustive, native stages | `e2a3609` | DeepMIMO CP00–CP06 complete; algorithm checks passed on development |

Version mới nhất là [`src/version_09_robust_safe_pruning`](src/version_09_robust_safe_pruning).

## Kết quả hiện tại

Run `DM_ASU35_SAFE_DEV_20261102` dùng nguyên `safe_pruning.py`/`reference_model.py` từ ZIP ngày 2026-11-02, theo ba stage gốc `preflight → scan → report`:

- 160/160 geometry khớp nghiệm exhaustive về số user, subset, alpha và công suất; không phát hiện loại nhầm ứng viên khả thi.
- Số lượt solve giảm từ 16,800 xuống 1,366 (91.87%); 1,728 ứng viên loại bằng điều kiện sàng lọc, 13,706 ứng viên kích thước nhỏ hơn được bỏ theo mục tiêu từ điển.
- Mean runtime quan sát: pruning 15.954564 ms, exhaustive 132.712190 ms; giảm 87.98%, tỷ số hai thời gian trung bình khoảng 8.32.
- Mean users=3.575; 97/160 geometry phục vụ đủ 4 user, 58 phục vụ 3 và 5 phục vụ 2.
- q=2.960414 đúng mặc định PDF version 09. Bảy CP gốc và sáu checksum CP06 được giữ nguyên; không thêm runner tách CP.
- Trạng thái hồ sơ: **ALGORITHM_CHECKS_PASSED_ON_DEVELOPMENT_DATA**. Dữ liệu dùng lại từ các version trước; chưa có kiểm chứng dữ liệu độc lập, global beamforming optimum hoặc chứng nhận outage/fairness.

Xem [run card version 09](log/version_09/runs/DM_ASU35_SAFE_DEV_20261102/RUN.md) và [source/lệnh chạy gốc](src/version_09_robust_safe_pruning/README.md).

## Kết quả trước đó (version 08)

Run `DM_ASU35_SCHED_DEV_20261101` dùng lại 160 geometry DeepMIMO, giữ q cố định và so exhaustive 15 tập con × 7 beam với forward/backward:

- Cả ba phục vụ trung bình 3.575 người dùng; 97/160 geometry phục vụ đủ 4, mọi geometry phục vụ ít nhất một người.
- Backward khớp số user/công suất exhaustive trên run, giảm 82% số lời gọi; runtime trung bình quan sát 24.608 ms so với 146.336 ms.
- Forward khớp số user; tỷ số công suất trung bình 1.00479. Một geometry có tỷ số 1.76619; runtime trung bình cao hơn exhaustive trong phép đo.
- Smoke và DeepMIMO đều hoàn tất CP00–CP06, 11 artifact/run được xác minh. Đây là **development/exploratory**; G4 độc lập chưa được xác minh.

Xem [run card version 08](log/version_08/runs/DM_ASU35_SCHED_DEV_20261101/RUN.md) và [hướng dẫn từng CP](src/version_08_robust_user_scheduling/docs/RUN_BY_CP_VI.md).

## Chẩn đoán trước đó (version 07)

Run chẩn đoán `DM_ASU35_BEAM_DIAG_20261031` trên DeepMIMO `asu_campus_3p5`:

- 160 geometry/160 nhóm, M=16, K=4; giữ q cố định `2.9604143746015965`.
- Lưới 7 beam × 5 ngân sách; 5.600 dòng chi tiết và 4.800 cặp ZF/RZF.
- Tại 1 W: 97/160 geometry có ít nhất một beam khả thi, 63 thất bại trên cả lưới.
- Trong 63: 44 có ít nhất một budget failure; 19 chỉ coupling/zero gain, gồm 14 coupling ở mọi beam.
- CP00–CP06 hoàn tất; 11 artifact được xác minh checksum. Trạng thái nghiên cứu: `DIAGNOSTIC_ONLY`.

Xem [`log/version_07/runs/DM_ASU35_BEAM_DIAG_20261031/RUN.md`](log/version_07/runs/DM_ASU35_BEAM_DIAG_20261031/RUN.md) và [hướng dẫn từng CP](src/version_07_beam_feasibility_diagnosis/docs/RUN_BY_CP_VI.md).

## Calibration trước đó (version 06)

Run `DM_ASU35_V1_20261028` trên cùng nguồn dữ liệu:

- 160 spatial groups: 40 development / 80 calibration / 40 test.
- Candidate khóa: `q = 2.9604143746015965`.
- Calibration: 39/80 failures (`48.75%`).
- Clopper--Pearson upper 95%: `58.4805%` > `5%`.
- Quyết định: `CP05_FAIL`; chưa được phép tuyên bố certificate.

Xem [`log/version_06/runs/DM_ASU35_V1_20261028/RUN.md`](log/version_06/runs/DM_ASU35_V1_20261028/RUN.md).

Version 07 tái phân tích dataset này; không tạo holdout độc lập và không thay đổi kết luận certificate failure ở version 06.

## Quy tắc sử dụng

1. Không sửa source của version lịch sử; tạo version mới.
2. Không dùng `version` để đặt tên dataset hoặc run. Xem [`VERSIONING.md`](VERSIONING.md).
3. Không commit DeepMIMO scenarios, real dataset, virtual environment hoặc `outputs/**/tasks`.
4. Mỗi run công bố phải có manifest, dataset SHA-256, code commit và trạng thái PASS/FAIL.
5. Sau khi calibration/test đã được xem, không retune rồi tái sử dụng holdout đó để chứng nhận.

## Data policy

Real datasets được lưu ngoài Git. Version 6–9 sử dụng kho cục bộ:

```text
/media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/
```

Git chỉ lưu provenance, group audit và checksum cần thiết để kiểm toán.
