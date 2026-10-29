# Fuzzy MU-MIMO Research

Kho nghiên cứu được tổ chức theo ba lớp độc lập:

- `src/`: mã nguồn bất biến theo từng code version.
- `log/`: kết quả chạy đã chọn lọc, trạng thái PASS/FAIL và provenance; không chứa task checkpoint lớn.
- `working_plan/`: mục tiêu, cấu hình và tiêu chí chấp nhận được viết trước khi chạy.

## Version index

| Version | Nội dung | Mốc gốc | Trạng thái |
|---|---|---|---|
| `version_03` | DeepMIMO spatial analysis | `089ab5a` | Historical |
| `version_04` | Spatially grouped DeepMIMO generator | `2aa366f` | Historical |
| `version_05` | CSI margin calibration pilot | `b51505e` | CP05 failure documented |
| `version_06` | Spatial CSI calibration with `xyz/scenario` metadata | branch này | Real DeepMIMO CP05 FAIL |

Version mới nhất là [`src/version_06_csi_spatial_calibration`](src/version_06_csi_spatial_calibration).

## Kết quả hiện tại

Run `DM_ASU35_V1_20261028` trên DeepMIMO `asu_campus_3p5`:

- 160 spatial groups: 40 development / 80 calibration / 40 test.
- Candidate khóa: `q = 2.9604143746015965`.
- Calibration: 39/80 failures (`48.75%`).
- Clopper--Pearson upper 95%: `58.4805%` > `5%`.
- Quyết định: `CP05_FAIL`; chưa được phép tuyên bố certificate.

Xem [`log/version_06/runs/DM_ASU35_V1_20261028/RUN.md`](log/version_06/runs/DM_ASU35_V1_20261028/RUN.md).

## Quy tắc sử dụng

1. Không sửa source của version lịch sử; tạo version mới.
2. Không dùng `version` để đặt tên dataset hoặc run. Xem [`VERSIONING.md`](VERSIONING.md).
3. Không commit DeepMIMO scenarios, real dataset, virtual environment hoặc `outputs/**/tasks`.
4. Mỗi run công bố phải có manifest, dataset SHA-256, code commit và trạng thái PASS/FAIL.
5. Sau khi calibration/test đã được xem, không retune rồi tái sử dụng holdout đó để chứng nhận.

## Data policy

Real datasets được lưu ngoài Git. Version 6 sử dụng kho cục bộ:

```text
/media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/
```

Git chỉ lưu provenance, group audit và checksum cần thiết để kiểm toán.
