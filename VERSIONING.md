# Versioning policy

Repository này phân biệt bốn định danh; không dùng lẫn nhau.

| Loại | Ví dụ | Ý nghĩa |
|---|---|---|
| Code version | `version_06` / tag `v6.0.0` | Thuật toán và source bất biến |
| Dataset version | `deepmimo_asu35_v1` | Quy tắc chọn và chuyển đổi dữ liệu |
| Run ID | `DM_ASU35_V1_20261028` | Một lần chạy với cấu hình khóa |
| Git commit | SHA đầy đủ | Snapshot tái lập chính xác |

## Code versions

- Major (`v6`): thay đổi phương pháp, schema dữ liệu hoặc protocol checkpoint.
- Minor (`v6.1`): tính năng tương thích ngược, không làm thay đổi ý nghĩa run cũ.
- Patch (`v6.1.1`): sửa lỗi không đổi protocol khoa học.

Source của version đã công bố không được sửa tại chỗ. Mọi thay đổi có thể làm kết quả khác phải tạo version mới và run ID mới.

## Run IDs

Định dạng khuyến nghị:

```text
<SOURCE>_<SCENARIO>_<DATASET-VERSION>_<YYYYMMDD>[_RNN]
```

Mỗi run card phải ghi code version/Git SHA, dataset version/SHA-256, cấu hình, checkpoint cuối, trạng thái và checksum artifact.

## Data and output policy

- Không commit real channel matrices hoặc downloaded scenarios.
- Smoke fixture nhỏ được phép nằm trong `src/<version>/data/`.
- `outputs/<run>/tasks/` là cache tái chạy, không phải artifact công bố.
- Chỉ artifact được chọn lọc nằm trong `log/<version>/runs/<run-id>/`.
- Calibration/test đã xem không được dùng lại làm holdout mới sau khi chỉnh luật.

## Historical tags

| Tag | Commit | Nội dung |
|---|---|---|
| `v3.0.0` | `089ab5a` | DeepMIMO spatial analysis |
| `v4.0.0` | `2aa366f` | Spatially grouped generator |
| `v5.0.0` | `b51505e` | CSI margin calibration pilot |
| `v6.0.0` | restructuring commit | Spatial CSI calibration and real-run audit |
