# Hướng dẫn chạy V15.1 — Điểm hòa vốn dự báo được của screening trước khi tạo beam

## 0. Mục tiêu và giả thuyết (đã khóa trong code, không sửa)

V15.1 kiểm chứng giả thuyết sau: **khi chia ô theo `early_ratio`, screening trước khi tạo beam (EARLY) tiết kiệm runtime so với CARD, mức tiết kiệm tăng theo K, và vùng có lợi dự báo được từ dữ liệu phát triển; điều này đúng trên cả DeepMIMO mới và 3GPP.**

`early_ratio` $=\sum_k \gamma N_0/(\|\widehat{\mathbf h}_k\|-r_k)^2/P_{\max}$ là đúng đại lượng mà EARLY kiểm tra. Giá trị lớn hơn 1 nghĩa là toàn bộ tập người dùng đã bị loại trước khi tạo beam. Các ô được chia theo ngưỡng `--er-bins 0.1,1.0`:

| Ô | `early_ratio` | Ý nghĩa |
|---|---|---|
| ER0 | < 0,1 | Giới hạn giao thoa; EARLY hầu như không kích hoạt |
| ER1 | [0,1; 1) | Trung gian |
| ER2 | ≥ 1 | Giới hạn công suất; EARLY tránh được L lần tạo beam cho mỗi tập con bị loại |

**Cổng quyết định cho mỗi nguồn test** (khai báo trước, nằm trong chữ ký CP00):

| Tiêu chí | Điều kiện đạt |
|---|---|
| E1 – hòa vốn tại K = 8 | Cận dưới CI95 của tiết kiệm tương đối > 2% **và** cận dưới CI95 của tiết kiệm tuyệt đối > 0,1 ms |
| E2 – tăng theo K | Cận dưới CI95 của hiệu ghép cặp (tiết kiệm tương đối tại K=8) − (tại K=4) > 0 |
| E3 – bảo toàn nghiệm | 0 sai khác so với exhaustive (một certificate sai sẽ làm chương trình dừng) |
| E4 – dự báo được | Trên các geometry được lock kích hoạt tại K=8, cận dưới CI95 của tiết kiệm > 0 |

Kết luận cuối `GO_PREDICTABLE_BREAK_EVEN` chỉ đạt khi **cả DeepMIMO và 3GPP** đều `GO_BREAK_EVEN` với **cùng một lock**. Cổng cũ của V15 (mọi cặp (K,L) phải vượt 0,1 ms) vẫn được báo cáo như kết quả phụ (`secondary_strict_all_KL_gate`).

## 1. Chuẩn bị máy (một lần)

1. Dùng **một máy duy nhất** cho toàn bộ: phát triển, DeepMIMO test, 3GPP test. Chữ ký lần chạy có ghi CPU, hệ điều hành, phiên bản Python/NumPy/SciPy; nếu khác máy, code sẽ từ chối chạy test.
2. Không chạy hai lần chạy song song, và không dùng máy cho việc nặng khác trong lúc đo runtime.
3. Giải nén gói vào một thư mục mới (không đặt trong OneDrive), mở PowerShell tại thư mục gốc của gói:
   ```powershell
   python -m pip install -r code/requirements.txt
   powershell -ExecutionPolicy Bypass -File .\scripts\smoke_v15_1.ps1
   ```
   Smoke chạy khoảng 1 phút và phải kết thúc bằng `SMOKE OK`.

## 2. Chuẩn bị dữ liệu (8 người dùng mỗi drop)

Tập v10 (4 người dùng) **không dùng được**. Cần ba tập: phát triển (≥ 20 nhóm), DeepMIMO test mới (≥ 10 nhóm, chưa từng mở), 3GPP test (≥ 10 nhóm, chưa từng mở). Định dạng: `H` phức kích thước (N, M, 8) với M ≥ 8, và `groups` dài N.

**DeepMIMO** (ví dụ cho tập test; làm tương tự cho tập phát triển với một scenario hoặc vùng không gian khác):
```powershell
# 2a. Xem cấu trúc file đã xuất từ DeepMIMO
python code/export_users.py --input raw\deepmimo_export.npz --inspect
# 2b. Khai báo đúng thứ tự trục (ví dụ u,rx,tx,sc), giữ một anten thu và một subcarrier
python code/export_users.py --input raw\deepmimo_export.npz --output data\dm_users.npz --channel-key channel --pos-key rx_pos --layout u,rx,tx,sc --rx 0 --sc 0
# 2c. Đóng gói thành drop 8 người dùng, mỗi ô không gian một drop
python code/pack_deepmimo_users.py --input data\dm_users.npz --output data\dm_test.npz --scenario <ten_scenario> --prefix DMT --cell-m 50
```
Mở `data\dm_test.npz.provenance.json` và sửa `prior_use` thành `never_seen` cho tập test (hoặc `development` cho tập phát triển). Ghi thêm phiên bản DeepMIMO, scenario, tần số sóng mang, anten và subcarrier đã chọn. **Không chuẩn hóa kênh**: giữ path loss tuyệt đối, vì $N_0=2\cdot10^{-13}$ W tham chiếu đến độ lợi tuyệt đối này.

**3GPP (Sionna)**: xuất trực tiếp ra `H` (N, M, 8) cùng `groups`, hoặc xuất kênh từng người dùng kèm vị trí rồi dùng `pack_deepmimo_users.py` như trên. Provenance phải ghi scenario (ví dụ UMi), tần số sóng mang, seed và đơn vị.

Mỗi tập cần một file provenance có đủ các trường `source`, `scenario`, `group_definition`, `independence_basis`, `prior_use`.

## 3. Kiểm tra trước (bắt buộc, khoảng 1 phút, chỉ đọc dữ liệu phát triển)

```powershell
python code/run_experiment.py --stage preflight --development data\dev.npz --run-id CHECK
```
Đọc `fraction_er_ge_1` và `groups_per_cell` tại K = 8:

| Quan sát | Dự báo |
|---|---|
| `fraction_er_ge_1` < 0,1 hoặc ô ER2 có ít hơn khoảng 13 nhóm | Không đủ geometry giới hạn công suất; lock sẽ chọn CARD và kết quả gần như chắc chắn là STOP. Chọn scenario hoặc vùng có nhiều người dùng ở rìa cell hơn **trước khi** chạy develop. |
| `fraction_er_ge_1` từ 0,2 đến 0,8 và mỗi ô có ≥ 13 nhóm | Có khả năng đạt GO; tiếp tục bước 4. |

Thay đổi scenario hoặc vùng dữ liệu phát triển ở bước này là hợp lệ, vì chưa có dữ liệu test nào được mở. Ghi lại lý do trong provenance.

## 4. Chạy chính thức (một lệnh)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_1.ps1 `
  -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json `
  -TestDM data\dm_test.npz -TestDMProvenance data\dm_test.npz.provenance.json `
  -Test3GPP data\gpp_test.npz -Test3GPPProvenance data\gpp_test.npz.provenance.json -Tag V151
```

Script tự chạy: unit test → preflight → develop → lock → DeepMIMO test → 3GPP test (dùng cùng lock) → combine → đóng gói `KET_QUA_V151.zip`.

- Muốn khóa trước rồi mới chuẩn bị tập test: thêm `-StopAfterLock`, sau đó chạy lại cùng lệnh khi đã có tập test.
- Bị gián đoạn: chạy lại **đúng lệnh cũ**; các geometry đã xong được dùng lại.
- Thời gian ước tính: khoảng 10 giây/geometry trên máy kiểm tra (gần 20 phút cho 30 + 15 + 15 geometry; khoảng 1 giờ cho 100 + 50 + 50).

## 5. Đọc kết quả

| File | Nội dung |
|---|---|
| `outputs/V151_FINAL/CP11_combined_decision.json` | Kết luận cuối: `GO_PREDICTABLE_BREAK_EVEN` hoặc `STOP` |
| `outputs/V151_FINAL/CP11_MANUSCRIPT_TABLE.md` | Bảng tiết kiệm tương đối và tuyệt đối theo K cho từng nguồn, kèm CI95 |
| `outputs/V151_DM/CP08_decision.json` | E1–E4 và lý do STOP (nếu có) cho DeepMIMO; tương tự `V151_3GPP` |
| `CP02_development_breakeven_curve.csv`, `CP06_test_breakeven_curve.csv` | Đường hòa vốn: tiết kiệm của từng chính sách theo (K, L, ô ER), dùng vẽ hình chính của bài |
| `CP03_locked_cells.json` | Chính sách đã khóa cho từng ô |

## 6. Quy tắc bắt buộc

1. Không sửa code, ngưỡng (`--er-bins`, `--min-rel-gain`, `--min-gain-ms`) hay tham số vật lý sau khi đã chạy develop. Nếu phải sửa: dùng `-Tag` mới, ghi lý do, và **không** dùng lại tập test đã mở.
2. Không bao giờ chạy develop/lock trên tập 3GPP; 3GPP chỉ được đánh giá bằng lock của DeepMIMO.
3. Nếu kết quả là STOP, báo cáo trung thực theo E1–E4; không chọn lại ô hay K có lợi sau khi đã xem kết quả test.
4. Lỗi `Different machine/software stack`: đang chạy test trên máy khác, hoặc đã nâng cấp thư viện. Quay lại đúng máy và môi trường ban đầu.
