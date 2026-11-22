# Hướng dẫn chạy V16.1 — Mở rộng nghiên cứu điểm hòa vốn (cho nghiên cứu sinh)

> **V16.1 (21/11/2026)** sửa lỗi `COMPILED MISMATCH geometry=8 K=6 L=3 CARD` ở pha `compiled`. Xem mục 3a. Lock V15.2 và 5 module lõi **không đổi**; chỉ cần chạy lại `check` rồi `compiled` (script tự cất thư mục `C16_*` cũ sang `C16_*_old_V16-compiled_<thời gian>`).

## 0. V16 làm gì

V16 mở rộng kết quả V15.2 (đã khóa bài) bằng ba phần, phục vụ bản full paper:

| Phần | Câu hỏi | Script |
|---|---|---|
| A. Tỷ lệ R tự nhiên | Trong một cell lấy mẫu ngẫu nhiên (không phân tầng 50/50), bao nhiêu phần trăm drop thuộc vùng dự báo R, và lợi ích kỳ vọng trên toàn cell là bao nhiêu? | `natural_prevalence.py` |
| B. Mô hình giải tích | Có dự báo được mức tiết kiệm từ chuẩn kênh (không tạo beam) bằng một mô hình chi phí đơn giản không? | `breakeven_model.py` |
| C. Bộ giải biên dịch | Điểm hòa vốn còn đúng không khi bộ giải nhanh hơn khoảng 60–800 lần (C thay cho Python; diễn tập đo được 64–782 lần)? | `native/screen_core.c`, `compiled_benchmark.py` |

**Nguyên tắc quan trọng:** V16 **không sửa** 5 module lõi của V15.2 (`run_experiment.py`, `robust_model.py`, `screening_policy.py`, `certified_screening.py`, `screening_bounds.py`); mã băm của chúng phải giữ nguyên. Nhờ đó lock V15.2 (`outputs\V152_DM\CP03_locked_cells.json`) được dùng lại nguyên vẹn, không huấn luyện lại.

**Cơ sở lý thuyết của phần B** (có chứng minh trong `breakeven_model.py`):
- *Bổ đề 1:* nếu `early_ratio` ≤ 1 thì EARLY không loại tập con nào, nên tiết kiệm luôn âm và đúng bằng chi phí kiểm tra. Đây là lý do ngưỡng hòa vốn nằm đúng tại `early_ratio` = 1 trong Hình 2 của bài.
- *Bổ đề 2:* họ tập con bị loại là một up-set, nên tỷ lệ tập con bị loại không giảm theo kích thước tập con. Đây là lý do tiết kiệm tăng theo K.
- *Mô hình:* $\Delta T = L\sum_{s=s^*}^{K} n_{\mathrm{rej}}(s)\,c(s) - N_{\mathrm{vis}}\,c_E - c_0$, với $c(s)=t_1 s+t_2 s^2+t_3 s^3$. Số tập con bị loại $n_{\mathrm{rej}}(s)$ tính chính xác từ chuẩn kênh; các hệ số được hiệu chỉnh bằng NNLS **chỉ trên tập phát triển**, rồi kiểm tra trên hai tập test.

## 1. Chuẩn bị (một lần)

1. **Dùng đúng máy đã chạy V15.2** và giữ nguyên thư mục `outputs\` của V15.2 (cần `V152_DM`, `V152_3GPP` và các file `data\V152_dm_test.npz`, `data\V152_3gpp_test.npz`).
2. Giải nén gói V16 vào **cùng thư mục gốc** với V15.2 (ghi đè `code\`, `scripts\`, `tests\`). Các file lõi giống hệt nên không làm mất hiệu lực lock.
3. **Cài trình biên dịch C** cho phần C:
   - Linux: `sudo apt install gcc`.
   - Windows (chọn một): MSYS2 + MinGW-w64 (`pacman -S mingw-w64-ucrt-x86_64-gcc`, rồi thêm thư mục `bin` vào PATH), hoặc Visual Studio Build Tools (chạy từ "Developer PowerShell" để có lệnh `cl`).
4. Không chạy việc nặng nào khác trong lúc đo; **không cập nhật hệ điều hành hay thư viện** cho đến khi xong.

## 2. Pha `check` (bắt buộc)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase check -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json
```
Pha này làm bốn việc: biên dịch thư viện C, chạy selftest (216 quyết định của bản C phải trùng với Python), chạy unit test, và kiểm tra xem lock V15.2 có dùng lại được trên máy hiện tại không.

- `OK: the V15.2 lock is reusable as is` → chuyển sang bước 3.
- Nếu báo khác biệt **chỉ ở `machine`** (thường do cập nhật kernel hoặc hệ điều hành), chạy:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase transfer -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json
  ```
  Bước này tạo lock chuyển giao `outputs\V16_T\CP03T_transferred_lock.json`: bản đồ chính sách giữ nguyên (có kiểm tra mã băm), kèm bản ghi máy trước và sau. **Phải nêu việc chuyển lock trong bài.** Các pha sau tự dùng lock này.
- Nếu khác ở `code_hashes`, `dev_hash` hay tham số: **dừng lại và báo**, không tự sửa.

## 3. Pha `compiled` (phần C, khoảng 30–40 phút)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase compiled -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json
```
Pha này chạy CARD, EARLY và ROUTED (định tuyến theo lock, chạy hoàn toàn trong C) trên tập phát triển và hai tập test V15.2. Mỗi phép đo lặp 7 lần với thứ tự xáo trộn. Mọi quyết định của bản C đều được đối chiếu với oracle Python, bên ngoài vùng đo thời gian.

Đọc kết quả ở `outputs\C16_DM\CC05_SUMMARY.md` và `CC04_compiled_decision.json` (tương tự cho `C16_3GPP`). Bốn endpoint đã khai báo trước:
- C1: mọi quyết định trùng oracle, hoặc chỉ lệch trong phạm vi độ nhạy dấu phẩy động của ứng viên (mục 3a), và các trường hợp này không quá 1% số quyết định được kiểm tra;
- C2: trong R, tại K=8, cận dưới CI tiết kiệm tương đối của ROUTED > 2%;
- C3: trong R, tiết kiệm của EARLY tăng từ K=4 lên K=8;
- C4: ngoài R, cận dưới CI tiết kiệm của ROUTED > −2% ở mọi K.

File `CC03_python_vs_compiled.csv` cho biết bản C nhanh hơn bao nhiêu lần, và mức tiết kiệm tương đối của EARLY thay đổi thế nào khi chuyển sang bản biên dịch.

**Lưu ý đo thời gian:** ở K=4, CARD biên dịch chỉ mất khoảng 15 µs mỗi cấu hình, nên dao động hệ thống có thể lấn át các chênh lệch dưới 1%. Mặc định mỗi phép đo kéo dài ≥ 20 ms (`--min-ms 20`; vòng lặp chạy bên trong C) và lặp 7 lần. Trong diễn tập, cấu hình 5 ms và 3 lần lặp đã làm C4 trượt vì nhiễu, còn cấu hình mặc định cho mức lỗ ngoài R khoảng −0,5% với CI hẹp. Không giảm các tham số này để chạy nhanh hơn.

## 3a. Lỗi `COMPILED MISMATCH` của V16 và cách V16.1 xử lý

**Hiện tượng:** tại geometry 8, K=6, L=3, bản C và oracle Python chọn **cùng** tập con `24`, cùng α = 0,01, cùng 2 người dùng; chỉ tổng công suất lệch nhau 1,2·10⁻⁷ (tương đối), vượt ngưỡng cứng 10⁻⁷ của V16.

**Nguyên nhân:** khi bán kính phổ ρ(F) rất gần 1, hệ (I − F)p = u gần suy biến, nên p khuếch đại sai số làm tròn khoảng 1/(1 − ρ) lần. Bản C và NumPy cộng theo thứ tự khác nhau nên lệch nhau ở các bit cuối. Diễn tập tái hiện đúng hiện tượng: với 1 − ρ = 10⁻⁷, 10⁻⁸, 10⁻⁹, độ lệch tương đối lần lượt là 6·10⁻⁷, 3·10⁻⁵, 8·10⁻⁵. Cả hai bản đều đúng tới độ chính xác máy; ngưỡng cứng 10⁻⁷ mới là chỗ sai.

**V16.1 (`code/numeric_agreement.py`):** khi phép so sánh chặt thất bại, chương trình tính độ nhạy của ứng viên bằng cách nhiễu mỗi phần tử kênh khoảng 9 ulp (16 lần, seed cố định). Trường hợp được chấp nhận chỉ khi:
- cùng quyết định và |Δp| ≤ max(10⁻⁷·p, 4 × độ nhạy) → `POWER_WITHIN_FP_SENSITIVITY`;
- khác quyết định nhưng là hòa trong phạm vi độ nhạy (`TIE_…`) hoặc ứng viên nằm đúng biên khả thi (`BOUNDARY_…`).

Mọi trường hợp khác vẫn dừng chương trình. Một lỗi thật (lệch 10⁻⁵ trên ứng viên điều kiện tốt) vẫn bị bắt (đã có unit test). Mọi trường hợp được chấp nhận ghi vào `CC06_numeric_events.csv` (kèm ρ và độ nhạy), đếm trong `CC04` (`numeric_events`, `numeric_event_fraction`). Nếu quá 1% số quyết định, C1 = sai.

**Khi viết bài:** báo cáo số trường hợp này, ví dụ "x trong N quyết định chỉ lệch về công suất trong phạm vi độ nhạy dấu phẩy động, do 1 − ρ(F) < 10⁻⁷".

## 4. Pha `model` (phần B, vài phút)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase model -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json
```
Pha này chạy hai mô hình: `M16_PY` (thời gian Python, từ V15.2) và `M16_C` (thời gian C, từ pha `compiled`). Mỗi mô hình được hiệu chỉnh trên tập phát triển và kiểm tra trên DM và 3GPP. Kết quả nằm ở `CM04_SUMMARY.md`:
- R², MAE (điểm phần trăm, pp), Spearman, tỷ lệ đoán đúng dấu trên **tập test**;
- số lần vi phạm Bổ đề 1 và 2 (phải bằng 0);
- hình `CM03_pred_vs_measured.png`;
- đường dân số theo K (K = 10, 12 là **ngoại suy của mô hình**, phải ghi rõ như vậy).

## 5. Phần A — tỷ lệ R tự nhiên

**5.1 Chuẩn bị kho kênh tự nhiên (trước khi khóa protocol).** Kho phải đại diện cho một cell thực và **chưa từng được đo**:
- DeepMIMO: một scenario **mới** (không dùng ASU, Seoul, Phoenix, Los Angeles); người dùng phủ đều toàn scenario; đóng gói bằng `pack_deepmimo_users.py` **không dùng** `--min-dist`/`--max-dist`, với `--cell-m` bằng tập phát triển (25 m); khoảng ≥ 150 nhóm.
- Hoặc Sionna 3GPP UMi với cấu hình chuẩn (một ISD duy nhất, ví dụ 200 m), người dùng rải đều, không phân tầng gần/xa.

Ghi provenance (`prior_use: never_seen`, scenario, cách rải người dùng).

**5.2 Khóa protocol** (chưa lấy mẫu, chưa đo):
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase natural-protocol -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -NaturalPool data\nat_pool.npz -NaturalGroups 100
```
**5.3 Lấy mẫu, đo và phân tích:**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase natural -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -NaturalPool data\nat_pool.npz -NaturalPoolProvenance data\nat_pool.npz.provenance.json
```
Pha này lấy mẫu ngẫu nhiên đơn giản 100 nhóm (không dùng hiệp biến), chạy test V15.2 với lock đã khóa (`--allow-small-region`, vì R có thể nhỏ), chạy bản biên dịch trên cùng mẫu, tính các endpoint, và đóng gói `KET_QUA_V16.zip`.

Các endpoint (`outputs\NP16\NP03_SUMMARY.md`):

| Endpoint | Nội dung |
|---|---|
| N1 | Tỷ lệ R kèm CI Wilson (ước lượng, không có ngưỡng) |
| N2 | Cận dưới CI tiết kiệm tương đối trung bình trên **toàn cell** tại K=8 > 0 |
| N3 | Ở mọi K, cận dưới CI > −2% (định tuyến không gây hại) |
| N4 | Nếu R có ≥ 5 nhóm: tiết kiệm trong R dương |

Kết luận là `NATURAL_GAIN`, `NATURAL_NO_HARM` hoặc `NATURAL_HARM`. **Cả ba đều là kết quả hợp lệ** để báo cáo: một cell gần trạm cho tỷ lệ R thấp, và khi đó kết luận đúng là "định tuyến không gây hại, lợi ích tập trung ở rìa cell".

## 6. Gửi lại

Gửi file `KET_QUA_V16.zip`, kèm `outputs\V16_T\` nếu có chuyển lock.

## 7. Quy tắc

1. Không sửa 5 module lõi; không sửa ngưỡng sau khi đã khóa protocol tự nhiên.
2. Mỗi kho chỉ được lấy mẫu **một lần** theo protocol đã khóa; không lấy mẫu lại vì kết quả không như mong muốn.
3. Bản C bỏ qua bước kiểm toán LP (bước này không đổi quyết định), và chạy HYBRID như EARLY; hai điểm này phải ghi rõ trong bài.
4. Nếu selftest C báo `MISMATCH`, hoặc benchmark báo `COMPILED MISMATCH`: dừng lại và gửi log.

## 8. Thời gian ước tính

| Pha | Thời gian |
|---|---|
| `check` | khoảng 1 phút |
| `compiled` | khoảng 30–40 phút (phần lớn là đối chiếu oracle Python tại K=8) |
| `model` | khoảng 1–3 phút |
| `natural` (100 nhóm) | khoảng 25–30 phút cho Python, cộng 10–15 phút cho bản biên dịch |
