# V18.2 — Mở rộng nghiên cứu tổng quát sang M = 32 anten: hướng dẫn chạy

## Vì sao cần lần chạy này
Trong V18, 9 cấu hình `M32_*` có kết quả `NOT_EVALUABLE`. Lý do là cả ba tập 32 anten đều là held-out, nên không có drop development nào để phát triển bản đồ ở M = 32. V18.2 chạy một **protocol riêng**, ghi vào `outputs_v18_m32/`, và không đụng tới `outputs_v18/` hay `results/RESULTS_V18`.

| Thành phần | Nội dung |
|---|---|
| Development | **3 tập Sionna mới**: UMi, UMa, RMa; 32 anten; 150 drop mỗi tập; seed 20261211, 20261212, 20261213. Spec **sao chép mọi trường triển khai** từ spec của tập held-out V18 (`results/RESULTS_V18/NS18_*`); chỉ đổi tên và seed |
| Held-out | **3 tập mới của V18**: `data/v18_{umi,uma,rma}_fresh.npz` (đã kiểm hash). Ở V18 các tập này chỉ được đo qua 8 hoặc 16 anten đầu; chưa từng đo ở M = 32 và chưa từng dùng để phát triển. Lịch sử này được ghi trong protocol (`prior_use`) và **phải nêu trong bài** |
| Lưới tham số | M = 32 × γ ∈ {0, 6, 10} dB × ε ∈ {0,02; 0,04; 0,08}: 9 cấu hình. Nếu thêm `--control`, protocol đánh giá thêm M = 16 trên **cùng các drop**, để so trực tiếp ảnh hưởng của M; thời gian chạy tăng gấp đôi |
| Phần giữ nguyên so với V18 | quy tắc phát triển bản đồ, các endpoint G1–G4, 9 bộ lập lịch, cách đo thời gian (5 ms × 3 lần), seed |
| Cấu hình tham chiếu | `M32_G6_E0.04`, dùng cho `stages` và `hwbundle` |

**Chi tiết kỹ thuật cần biết khi đọc kết quả.** η chuẩn hóa theo độ lợi trên mỗi anten và dùng toàn bộ độ lợi mảng. Vì vậy với cùng một drop, η ở M = 32 nhỏ hơn ở M = 16 khoảng 2 lần (3 dB), nên vùng R ở M = 32 sẽ nhỏ hơn. Đây là hiệu ứng vật lý, không phải lỗi.

## Yêu cầu
- Repo `lrs-mumimo` v1.7: phải có `results/RESULTS_V18/NS18_*`.
- Ghi đè thư mục `v18/` bằng bản trong gói này. Gói gồm `run_v18.py` V18.2, `run_m32.py` và hướng dẫn này.
- `data/v18_{umi,uma,rma}_fresh.npz` kèm file provenance của chúng: đúng các file của V18.
- `gcc`.
- Môi trường Sionna 2.2.0, chính là môi trường đã sinh các tập fresh của V18.
- Đặt một luồng:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
```

Khi đang đo không chạy việc nặng khác trên máy. Dùng **đúng máy của V18** (i9-10900K), để có thể so sánh với kết quả M = 8/16.

## Các bước và điểm kiểm tra

**CK0 — phần mềm**
```bash
python v18/run_v18.py selftest
python -m unittest discover -s v18/tests
```
Phải thấy: `576 configurations x 7 schedulers, 96 oracle checks, 0 failures` và `OK`.

**Bước 1 — cố định spec của các tập development (trước khi sinh)**
```bash
python v18/run_m32.py specs
```
Lệnh tạo `outputs_v18_m32/NS32_{UMI,UMA,RMA}/NS00_scenario_spec.json`. Kiểm tra trong mỗi file:
- `bs_antennas = 32`, `pool_drops = 150`;
- seed là 20261211 / 20261212 / 20261213;
- ISD, chiều cao BS, khoảng cách tối thiểu và tỉ lệ người dùng trong nhà **giống hệt** `results/RESULTS_V18/NS18_*`.

**Bước 2 — sinh tập development**, chạy bằng Python có Sionna:
```bash
<python-sionna> v18/run_m32.py generate --bs-rows 1 --bs-cols 32
# hoặc: python v18/run_m32.py generate --sionna-python <python-sionna>
```
Kết quả là `data/v18_{umi,uma,rma}_dev32.npz`, mỗi file có dạng `(150, 32, 8)`. Tập nào đã có thì được giữ nguyên. **Không sinh lại sau khi đã nhìn kết quả.** Nếu lỗi kỹ thuật, ghi vào `NOTES.txt`, xóa file lỗi, rồi chạy lại đúng lệnh (seed giữ nguyên).

**Bước 3 — kiểm tra**
```bash
python v18/run_m32.py validate
```
Đạt khi thấy:
- `POOL ACCEPTED` cho cả 3 tập development;
- `held-out ...: SHA-256 matches V18` cho cả 3 tập held-out.

Lệnh cũng ghi `outputs_v18_m32/DATASETS_M32.csv` (hash của 6 file). Nếu hash held-out không khớp thì **dừng lại**: đó không phải tập của V18.

**Bước 4 — cố định protocol** (trước mọi phép đo thời gian)
```bash
python v18/run_m32.py protocol              # thêm --control nếu muốn có M = 16 trên cùng drop
```
Lệnh phải in `9 configurations, 450 development / 450 held-out drops`, hoặc 18 cấu hình nếu có `--control`. Ba dòng `NOTE: held-out set ... prior_use=...` là bình thường. Sau bước này **không đổi tham số nào**.

**Bước 5 — development → lock → test → analyze**
```bash
python v18/run_m32.py run
```
Mọi bước đều chạy tiếp được sau khi bị ngắt: chỉ cần chạy lại đúng lệnh.

- **CK5a:** `lock` in `LOCKED` cho 9 cấu hình. Ghi lại giá trị `only_top_bin_active`: nếu là `true` thì bản đồ trùng quy tắc η ≥ 1. Nếu có cấu hình không như vậy, **không sửa gì**; ghi vào `NOTES.txt`, vì đó là kết quả.
- **CK5b:** `test` không được in `WARNING exactness`. Nếu có, vẫn để lệnh chạy hết, nhưng ghi lại.
- **CK5c:** đọc `outputs_v18_m32/G07_SUMMARY.md`:
  - các cột G1–G4 và verdict;
  - số drop trong R. Nếu R có dưới 10 drop, G2 được ghi "không đánh giá được"; đây là kết quả hợp lệ;
  - **LRSPUB** (bản đồ đã công bố) phải có số lần giải công suất bằng LRS trong vùng η ≥ 1. Nếu bằng DCS thì bản đồ không được nạp: V18.2 sẽ dừng với thông báo `Published policy map not found`.

**Bước 6 — stage và phần cứng ở M = 32**
```bash
python v18/run_m32.py extras
```
Đạt khi `median_closure` ≥ 0,9. Bundle `HW_*` được ghi trong `outputs_v18_m32/`.

**Bước 7 — đóng gói**
Viết `outputs_v18_m32/NOTES.txt` gồm: ngày chạy, máy, phiên bản, các CK và mọi điều bất thường. Sau đó chạy:
```bash
python v18/run_m32.py pack
```
Gửi file `KET_QUA_V18_M32_<ngày>.zip` về. Gói đã có sẵn toàn bộ G01/G03, NS32_*, HW và NOTES.

## Thời gian dự kiến
Ước lượng trên i9-10900K, cần xác nhận khi chạy:

| Bước | Ước lượng |
|---|---|
| Development | 9 cấu hình × 450 drop × 6 ô × 2 chính sách → khoảng 1,5–2 giờ |
| Test | 9 cấu hình × 450 drop × 9 bộ lập lịch → khoảng 5–7 giờ; ACS và DCS ở K = 8 chậm nhất. Với `--control`, cộng thêm khoảng 4–5 giờ |
| `extras` | khoảng 15 phút |

## Sau khi có kết quả
Tôi sẽ thêm 9 dòng M = 32 vào Bảng IX (hoặc làm một bảng riêng) và cập nhật mục V-I, Limitations và Conclusion.

Bài sẽ nêu rõ ba điều:
- tập development của M = 32 khác với V18, nhưng cùng kịch bản;
- tập held-out đã từng được đo ở M = 8/16;
- R nhỏ hơn ở M = 32 là do độ lợi mảng.
