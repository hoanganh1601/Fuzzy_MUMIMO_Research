# Hướng dẫn chạy V17 — Vòng cuối: quét ngân sách công suất Pmax (cho nghiên cứu sinh)

## 0. Mục tiêu và thiết kế (đã khóa trong code)

Bài v1.3 có hai mẫu tự nhiên đo ở Pmax = 30 dBm (mức của lock). Phản biện sẽ hỏi kết quả còn đúng không khi công suất trạm gốc thực tế cao hơn. V17 đo lại ở **35, 46 và 49 dBm**, kèm **30 dBm làm mức tham chiếu** đo trên cùng các nhóm.

- **Bản đồ chính sách không học lại.** Bản đồ khóa ở V15.2 được giữ nguyên và chỉ được áp dụng (chuyển giao) sang mức Pmax mới. Điều này hợp lệ về mặt định nghĩa: ρE đã chia cho Pmax, và Bổ đề "ρE ≤ 1 thì không loại tập con nào" đúng với mọi Pmax. Mọi tham số khác (γ = 6 dB, N0, q_c, σ, α, K, L, ngưỡng ô ρE) giữ như lock.
- **Dữ liệu là 100 nhóm chưa từng được lấy mẫu** của mỗi kho tự nhiên đã có (UMi ISD 200 m và UMa ISD 500 m). Các nhóm này chưa bao giờ bị đo hay xem. Cách chọn là phần bù tất định của mẫu V16, không dùng ngẫu nhiên, không dùng covariate.
- **Bộ giải:** bản biên dịch (C). Mọi quyết định được đối chiếu với oracle Python ở **cùng mức Pmax**. Python V15.2 không chạy lại.
- **Tổng cộng 8 lần chạy:** 2 triển khai × 4 mức Pmax.

**Endpoint** (tính cho từng triển khai và từng mức Pmax; "tiết kiệm" là tiết kiệm của ROUTED so với CARD biên dịch):

| Mã | Nội dung |
|---|---|
| X1 | Không sai khác quyết định; sự kiện số học ≤ 1%; quyết định độ chính xác đơn và kép không đổi |
| X2 | Tỷ lệ R kèm khoảng tin cậy Wilson (chỉ ước lượng, không có ngưỡng đạt/trượt) |
| X3 | Tiết kiệm toàn cell: cận dưới CI > −2% ở mọi K (không gây hại) |
| X4 | Tiết kiệm toàn cell tại K = 8: cận dưới CI > 0 (chỉ báo cáo) |
| X5 | Nếu R ≥ 5 nhóm: tiết kiệm trong R tại K = 8 có cận dưới CI > 0 |
| X6 | Nếu ngoài R ≥ 5 nhóm: tiết kiệm ngoài R có cận dưới CI > −2% ở mọi K |

**Kết luận theo từng mức Pmax:** `TRANSFER_OK` nếu X1, X3, X5 (khi tính được) và X6 (khi tính được) đều đạt ở **cả hai** triển khai.

**Rủi ro đã biết trước:** khi Pmax lớn, nhiều người dùng được phục vụ hơn, nên CARD biên dịch kết thúc rất nhanh (vài chục µs). Khi đó chi phí định tuyến chiếm tỷ trọng lớn hơn, và X3/X6 có thể sát ngưỡng −2%. Nếu trượt, đó là một **kết quả cần báo cáo**, không phải lỗi. Không được đổi ngưỡng sau khi đã thấy kết quả.

## 1. Chuẩn bị — **CK0**

Dùng **cùng máy** đã chạy V16. Giải nén V17 vào thư mục mới, rồi chép sang:
- `outputs/V152_DM/` (manifest và lock V15.2);
- kho UMi của NP16 và provenance của nó (đường dẫn như lần chạy V16);
- `data/V16_natural_sample.npz` (mẫu UMi của V16);
- `data/nat2_pool.npz` cùng `data/nat2_pool.npz.provenance.json`;
- `data/V16_natural2_sample.npz` (mẫu UMa của V16).

```bash
A="-Development data/dev.npz -DevProvenance data/dev.npz.provenance.json -Python <python của venv>"
pwsh -File scripts/run_v16.ps1 -Phase check $A
```
**CK0 đạt khi:** selftest 216/216 và **38/38 test** OK.

## 2. Khóa protocol — **CK1**
```bash
pwsh -File scripts/run_v16.ps1 -Phase pmax-protocol $A -NaturalPool <kho UMi> -NaturalPoolProvenance <provenance kho UMi>
```
Lệnh này tạo `outputs/PX17/PX00_protocol.json` cùng hai tập phần bù `data/V17_umi_complement.npz` và `data/V17_uma_complement.npz`. Nếu mỗi kho có 200 nhóm thì mỗi tập phần bù có 100 nhóm. Protocol ghi lại mã băm của lock, manifest, các kho, mẫu V16, tập phần bù và code.

**Không sửa** file nào sau bước này. Nếu protocol đã tồn tại, chương trình sẽ từ chối khóa lại.

**CK1 chạy tự động ở đầu bước 3** (`PX01_CK1_check.json`, phải có `"ok": true`). Nếu lock, dữ liệu hoặc code đã đổi, CK1 trượt và chương trình dừng.

## 3. Chạy 8 lần — **CK2 sau mỗi lần**
```bash
pwsh -File scripts/run_v16.ps1 -Phase pmax-run $A
```
Thứ tự chạy: UMi ở 30 → 35 → 46 → 49 dBm, rồi UMa ở 30 → 35 → 46 → 49 dBm. Thư mục kết quả có dạng `outputs/C17_UMI_P30`, …, `outputs/C17_UMA_P49`.

Sau mỗi lần chạy, chương trình ghi CK2 vào `outputs/PX17/PX01b_CK2_progress.json`. Mỗi lần chạy xong phải ở trạng thái `DONE`, với `data_ok`, `pmax_ok` và `X1` cùng bằng `true`. Nếu một lần chạy báo `PROBLEM`, chương trình dừng; khi đó gửi log, **không tự sửa**.

- **Thời gian:** mỗi lần khoảng 15–40 phút (gồm cả oracle Python); tổng khoảng 2–5 giờ.
- **Bị gián đoạn:** chạy lại đúng lệnh trên. Các geometry đã xong được giữ nguyên trong checkpoint, chương trình chạy tiếp phần còn lại.
- **Muốn xem tiến độ bất cứ lúc nào:**
  ```bash
  <python của venv> code/pmax_sweep.py --stage progress --out-root outputs
  ```

## 4. Phân tích và đóng gói — **CK3**
```bash
pwsh -File scripts/run_v16.ps1 -Phase pmax-analyze $A
```
Lệnh này tạo `outputs/PX17/PX02_results.json` và `PX03_SUMMARY.md` (bảng X1–X6 cho từng triển khai và từng mức Pmax, kèm kết luận theo mức Pmax).

**CK3 đạt khi:** không có lần chạy nào bị thiếu, và mọi lần chạy đều dùng đúng tập phần bù và đúng mức Pmax (chương trình tự kiểm tra hai điều này).

Gửi lại **`KET_QUA_V17_PMAX.zip`**, gồm `PX17` và 8 thư mục `C17_*` (chỉ các file CC*/PX*).

## 5. Bảng checkpoint

| CK | Khi nào | File | Điều kiện đạt |
|---|---|---|---|
| CK0 | Trước mọi thứ | màn hình | 216/216 selftest, 38/38 test |
| CK1 | Đầu `pmax-run` | `PX17/PX01_CK1_check.json` | `ok: true` |
| CK2 | Sau mỗi lần chạy | `PX17/PX01b_CK2_progress.json` | mỗi lần chạy xong: DONE, X1 true |
| CK3 | `pmax-analyze` | `PX17/PX02_results.json` | không thiếu lần chạy; đúng dữ liệu, đúng Pmax |

## 6. Quy tắc
- Một máy, không chạy song song, không dùng máy cho việc nặng khác, không cập nhật hệ điều hành trong lúc chạy.
- Không đổi tham số (`--repeats`, `--min-ms`, ngưỡng). Không xem hay phân tích các tập phần bù trước khi chạy.
- Gặp lỗi: gửi nguyên log và thư mục `outputs/PX17`.
