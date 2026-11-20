# Hướng dẫn chạy V15.2 — Điểm hòa vốn dự báo được của screening trước khi tạo beam

## 0. V15.2 sửa gì so với V15.1

V15.1 kết thúc ở STOP vì **dịch chuyển phân bố**: tập phát triển ASU có 54% geometry ở ô ER2 (giới hạn công suất) tại K=8, nhưng hai tập test (Phoenix, Sionna) có 0%. Vì vậy chính sách đã khóa không được dùng lần nào. V15.2 xử lý vấn đề này bằng thiết kế, không bằng việc chọn lại kết quả:

| Thay đổi | Mục đích |
|---|---|
| Endpoint chính P1–P4 tính **trong vùng dự báo R** (các geometry test có ô K=8 được lock gán chính sách khác CARD) | Kiểm định đúng nơi giả thuyết phát biểu |
| Cổng vùng: R phải có ≥ 10 nhóm, nếu không thì **INCONCLUSIVE** (không phải STOP) | Không nhầm dịch chuyển phân bố với bác bỏ giả thuyết |
| Bước `test-preflight`: chỉ đọc kênh, đếm số nhóm trong R **trước khi đo runtime**; mọi lần thử được ghi vào `TEST_SELECTION_LOG.csv` | Từ chối sớm tập test không đại diện, có dấu vết kiểm toán |
| `stratify_test_pool.py`: chọn tập test từ một kho kênh lớn theo hiệp biến (số nhóm trong R và ngoài R khai báo trước, seed cố định) | Tập test có cả hai phía của bộ dự báo |
| Chia fit/validation **phân tầng theo ô ER** tại K=8; tập phát triển ≥ 80 nhóm, trong đó ≥ 20 nhóm ở ER2 | Tránh tình trạng ô K6 ER2 bị chặn chỉ vì có 4 nhóm validation |
| `pack_deepmimo_users.py --bs-pos --min-dist --max-dist` | Tạo drop ở rìa cell cho tập phát triển và kho test |

**Endpoint chính cho mỗi nguồn test** (khóa trong chữ ký CP00):

| Tiêu chí | Điều kiện đạt |
|---|---|
| Cổng vùng | R có ≥ 10 nhóm; nếu không: `INCONCLUSIVE_REGION_TOO_SMALL` |
| P1 – hòa vốn trong R tại K=8 | Cận dưới CI95 của tiết kiệm tương đối của lock > 2% **và** cận dưới CI95 của tiết kiệm tuyệt đối > 0,1 ms |
| P2 – tăng theo K trong R | Cận dưới CI95 của (tiết kiệm tương đối của EARLY tại K=8 − tại K=4) > 0 |
| P3 – bảo toàn nghiệm | 0 sai khác so với exhaustive |
| P4 – không bỏ lỡ lợi ích ngoài R | Trượt chỉ khi có bằng chứng EARLY lẽ ra có lợi ngoài R (cận dưới CI95 ≥ 0,1 ms) |

Kết luận cuối: `GO_PREDICTABLE_BREAK_EVEN` nếu cả DeepMIMO và 3GPP đều GO với cùng lock; có nguồn nào STOP thì kết luận là `STOP`; các trường hợp còn lại là `INCONCLUSIVE`.

## 1. Chuẩn bị máy

Dùng **một máy duy nhất** cho cả ba pha. Chữ ký lần chạy ghi CPU, hệ điều hành và phiên bản thư viện; khác máy thì code từ chối chạy test. Không chạy hai việc đo cùng lúc. Giải nén gói vào thư mục mới (không đặt trong OneDrive), mở PowerShell tại thư mục gốc của gói:

```powershell
python -m pip install -r code/requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_v15_2.ps1
```
Smoke phải kết thúc bằng `SMOKE OK`.

**Không dùng lại** Phoenix và tập Sionna của V15.1 làm test, vì chúng đã được mở. Có thể dùng chúng làm một phần tập phát triển nếu cần thêm nhóm.

## 2. Chuẩn bị dữ liệu phát triển (≥ 80 nhóm, ≥ 20 nhóm ER2)

```powershell
python code/export_users.py --input raw\asu_export.npz --inspect
python code/export_users.py --input raw\asu_export.npz --output data\dev_users.npz --channel-key channel --pos-key rx_pos --layout u,rx,tx,sc --rx 0 --sc 0
python code/pack_deepmimo_users.py --input data\dev_users.npz --output data\dev.npz --scenario asu_campus_3p5 --prefix DEV --cell-m 25
python code/run_experiment.py --stage preflight --development data\dev.npz --run-id CHECK
```

Trong kết quả preflight, tại K=8 cần `groups_per_cell` có ER2 ≥ 20 và tổng số nhóm ≥ 80. Nếu thiếu:
- giảm `--cell-m` (ví dụ 25 m) để có nhiều tile hơn;
- thêm một scenario DeepMIMO khác vào tập phát triển;
- tạo drop ở rìa cell bằng `--bs-pos x,y,z --min-dist <m>` (lấy vị trí trạm từ dữ liệu DeepMIMO).

Sửa `prior_use` trong provenance thành `development`. Không chuẩn hóa kênh (giữ path loss tuyệt đối).

## 3. Pha `develop` (phát triển và khóa)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase develop -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -Tag V152
```
Kết quả là `outputs\V152_DM\CP03_locked_cells.json`. Mở `CP03_cell_validation.csv` để xem các ô được kích hoạt. Nếu không có ô nào khác CARD, dừng tại đây: giả thuyết không có vùng để kiểm chứng.

## 4. Pha `select` (tạo tập test sau khi khóa)

1. Tạo **hai kho kênh mới, chưa từng đo**, mỗi kho ≥ 60 nhóm và có người dùng ở rìa cell:
   - DeepMIMO: một scenario chưa dùng ở V11–V15.1, đóng gói bằng `pack_deepmimo_users.py` (có thể kết hợp tile gần trạm và tile xa trạm với `--min-dist`);
   - 3GPP (Sionna): UMa/UMi với ISD lớn hoặc khoảng cách UT lớn, giữ path loss tuyệt đối, xuất ra `H` (N, 16, 8) cùng `groups`.

   Ghi provenance với `prior_use: never_seen`.
2. Chạy:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase select -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -Tag V152 `
     -PoolDM data\dm_pool.npz -PoolDMProvenance data\dm_pool.npz.provenance.json `
     -Pool3GPP data\gpp_pool.npz -Pool3GPPProvenance data\gpp_pool.npz.provenance.json
   ```
   Script chọn 15 nhóm trong R và 15 nhóm ngoài R cho mỗi nguồn (đổi bằng `-RegionGroups`, `-OutsideGroups`), rồi chạy `test-preflight`. Bước này **chưa đo runtime**.
3. Nếu một nguồn báo `REJECTED` hoặc `Pool too small`: tạo kho mới có nhiều drop ở rìa cell hơn, rồi chạy lại pha `select`. Mọi lần thử đều nằm trong `TEST_SELECTION_LOG.csv`; báo cáo cả các lần bị loại. Không hạ ngưỡng 10 nhóm.

Nếu đã có sẵn tập test thay vì kho, dùng `-TestDM ... -TestDMProvenance ...` (và `-Test3GPP ...`).

## 5. Pha `test` (đo runtime và tổng hợp)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase test -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -Tag V152
```
Script chạy test DeepMIMO, test 3GPP (cùng lock), report, combine, rồi đóng gói `KET_QUA_V152.zip`. Nếu bị gián đoạn, chạy lại đúng lệnh. Thời gian đo trên máy kiểm tra: 10–17 giây/geometry (pha `develop` với 80 nhóm mất khoảng 20 phút; pha `test` với 30 + 30 geometry mất khoảng 15 phút).

## 6. Đọc kết quả

| File | Nội dung |
|---|---|
| `outputs/V152_FINAL/CP11_combined_decision.json` | `GO_PREDICTABLE_BREAK_EVEN`, `STOP` hoặc `INCONCLUSIVE` |
| `outputs/V152_FINAL/CP11_MANUSCRIPT_TABLE.md` | Theo K, trong R: tiết kiệm tương đối của lock và của EARLY, kèm CI95; xu hướng theo K; kết quả ngoài R |
| `outputs/V152_DM/CP08_decision.json` | P1–P4, cổng vùng, lý do; `secondary_all_geometry_V15_1` là endpoint cũ của V15.1 |
| `outputs/*/TEST_SELECTION_LOG.csv` | Mọi tập test đã thử, được nhận hoặc bị loại |
| `CP02_development_breakeven_curve.csv`, `CP06_test_breakeven_curve.csv` | Đường hòa vốn theo (K, L, ô ER), dùng vẽ hình chính |

## 7. Quy tắc bắt buộc

1. Không sửa code, ngưỡng hay tham số sau pha `develop`; muốn sửa thì dùng `-Tag` mới.
2. Tập test chỉ được tạo hoặc chọn **sau** khi khóa, và chỉ bằng hiệp biến (`stratify_test_pool.py`, `test-preflight`); không bao giờ dựa vào runtime.
3. Không develop/lock trên 3GPP; 3GPP chỉ dùng lock của DeepMIMO.
4. Báo cáo đúng kết luận theo P1–P4, kể cả INCONCLUSIVE hoặc STOP; không chọn lại K, L hay ô sau khi đã xem test.
