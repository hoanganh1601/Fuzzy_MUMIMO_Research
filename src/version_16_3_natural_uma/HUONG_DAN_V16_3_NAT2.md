# Hướng dẫn chạy V16.3 — Mẫu tự nhiên thứ hai trong kịch bản giới hạn công suất (cho nghiên cứu sinh)

## 0. Mục tiêu và các quyết định đã khóa trong code

Ở lần NP16 (Sionna UMi, ISD 200 m, toàn bộ người dùng ngoài trời), vùng có lợi R chỉ chiếm **1/100 nhóm**. Lần này kiểm tra xem trong một triển khai giới hạn công suất, R xuất hiện thường xuyên đến đâu và lợi ích trên toàn cell lớn tới mức nào. Lock V15.2 và mọi tham số vật lý (γ = 6 dB, Pmax = 1 W, N0, q_c, σ, M = 16) **giữ nguyên**.

**Kịch bản mặc định `UMA500_TR38901`:** bố trí UMa chuẩn của 3GPP TR 38.901: ISD 500 m, BS cao 25 m, UT cao 1,5 m, khoảng cách BS–UT tối thiểu 35 m, **80% người dùng trong nhà** (mô hình xuyên tường O2I "low"), 3,5 GHz, 16 anten (cùng mảng với bộ sinh UMi), 8 người dùng mỗi drop, không chuẩn hóa kênh, không lọc theo khoảng cách hay theo kênh, lưu ở complex64 như NP16. Kho gồm 200 drop (seed 20261124); mẫu gồm 100 nhóm (seed 20261125).

**Vì sao không làm kịch bản URLLC (γ cao) ở lần này:** đổi γ là đổi chính bài toán (tập khả thi, thời gian chạy). Bản đồ chính sách của lock V15.2 được khóa ở γ = 6 dB, nên không thể đem dùng nguyên cho γ khác. Muốn làm URLLC phải chạy lại toàn bộ quy trình phát triển và khóa ở γ mới (mất vài ngày). Bản đánh giá V16 đã có phép chiếu covariate cho trường hợp này: tăng γ/Pmax thêm 10 dB thì tỷ lệ R tại K = 8 lên 10%.

**Lưu ý khi diễn giải:** so với NP16 có **hai yếu tố thay đổi cùng lúc** (bố trí macro và người dùng trong nhà), nên đây là so sánh giữa hai triển khai, không phải phân tích tách riêng từng yếu tố. Nếu muốn chỉ đổi bố trí, phải quyết định **ngay ở bước 2** bằng `--set indoor_probability=0.0`, và chỉ được khóa một lần. Bộ sinh giữ UT trong nhà ở độ cao 1,5 m; TR 38.901 cho UT trong nhà ở các tầng cao hơn, nên đây là một điểm đơn giản hóa cần ghi trong bài. FACT{đối chiếu Bảng 7.2-1 của phiên bản TR 38.901 đang dùng: ISD, chiều cao BS, tỷ lệ trong nhà, mô hình O2I}.

**Thứ tự chống "chọn kịch bản theo kết quả":**
1. Khóa kịch bản **trước** khi sinh bất kỳ kênh nào (`NS00`).
2. Sinh kho từ đúng file đó. Provenance phải chứa mã băm của `NS00`.
3. Kiểm tra kho (`NS01`). Chỉ xem độ lợi kênh và khoảng cách; **không tính early ratio trên kho**.
4. Khóa protocol mẫu tự nhiên (`NP00`). Cỡ mẫu và seed lấy từ `NS00`.
5. Lấy mẫu ngẫu nhiên → V15.2 test → bản biên dịch → các endpoint N1–N4 → so sánh với NP16.

Endpoint giữ nguyên như NP16. N1: tỷ lệ R (khoảng tin cậy Wilson). N2: cận dưới CI của tiết kiệm toàn cell tại K = 8 > 0. N3: cận dưới CI > −2% ở mọi K. N4: nếu R có ≥ 5 nhóm, cận dưới CI của tiết kiệm trong R tại K = 8 > 0. Phân tích phụ (`NP05`): chênh lệch tỷ lệ R giữa UMa và UMi, kèm khoảng tin cậy Newcombe 95%.

## 1. Chuẩn bị

1. Giải nén **V16.3** vào một thư mục mới, trên **cùng máy** đã chạy V16. Chép sang thư mục mới: `outputs/V152_DM` (lock), `outputs/NP16` (để so sánh) và hai tập dữ liệu phát triển, rồi chạy:
   ```bash
   pwsh -File scripts/run_v16.ps1 -Phase check -Development data/dev.npz -DevProvenance data/dev.npz.provenance.json -Python <python của venv>
   ```
   Phải đạt: selftest 216/216 và 36/36 test.
2. Môi trường Sionna: dùng đúng môi trường đã sinh kho UMi cho NP16 (Sionna 2.2.0, torch). Nếu môi trường này khác venv chạy thí nghiệm, truyền nó qua `-SionnaPython`.

Trong các lệnh dưới đây, đặt sẵn `A="-Development data/dev.npz -DevProvenance data/dev.npz.provenance.json -Python <python của venv>"`.

## 2. Khóa kịch bản (trước khi sinh kênh)
```bash
pwsh -File scripts/run_v16.ps1 -Phase natural2-spec $A
```
Kết quả là `outputs/NS2/NS00_scenario_spec.json` và dòng `scenario_spec_sha256 = …`. **Không** sửa file này. Nếu buộc phải đổi kịch bản, dùng run-id mới và ghi lý do vào nhật ký.

## 3. Sinh kho UMa

**Cách A — dùng template của gói:**
```bash
pwsh -File scripts/run_v16.ps1 -Phase natural2-generate $A -SionnaPython <python có Sionna> -BsRows 1 -BsCols 16
```
`-BsRows` và `-BsCols` phải **giống hệt** mảng anten của bộ sinh UMi (ví dụ 4×4 hoặc 1×16). File `code/gen_sionna_uma.py` viết theo API công khai của Sionna nhưng **chưa được chạy với Sionna thật** (môi trường soạn code không có Sionna; chỉ thử với một module giả lập). Nếu lỗi, sửa đúng 5 dòng đánh dấu `ADAPT` cho khớp phiên bản Sionna của bạn.

**Cách B — sửa bộ sinh UMi đã dùng cho NP16 (khuyến nghị nếu cách A lỗi):** đổi kịch bản sang UMa và đặt các giá trị lấy từ `NS00`: ISD 500, chiều cao BS 25, khoảng cách tối thiểu 35, tỷ lệ trong nhà 0,8, O2I "low", seed 20261124, 200 drop. Ghi ra `data/nat2_pool.npz` (H dạng (200, 16, 8) complex64, `groups` không trùng nhau, nên có thêm `ut_distance_m`). Provenance `data/nat2_pool.npz.provenance.json` phải có:
- `scenario_spec_sha256` = mã băm in ra ở bước 2;
- `scenario`, `inter_site_distance_m`, `bs_height_m`, `ut_height_m`, `minimum_bs_ut_distance_m`, `indoor_probability`, `o2i_model`, `carrier_frequency_hz`, `bs_antennas`, `users_per_geometry`, `channel_normalization`, `dataset_dtype` **đúng như `NS00`**;
- `seed` = 20261124, `prior_use` = `never_seen`, cùng `source`, `group_definition`, `independence_basis`.

## 4. Kiểm tra kho
```bash
pwsh -File scripts/run_v16.ps1 -Phase natural2-validate $A
```
Phải ra `POOL ACCEPTED`. `NS01_pool_validation.json` ghi phân bố độ lợi kênh trên mỗi anten và khoảng cách. Không tính thêm gì khác trên kho.

## 5. Khóa protocol
```bash
pwsh -File scripts/run_v16.ps1 -Phase natural2-protocol $A
```
Kết quả là `outputs/NP16B/NP00_natural_protocol.json`. Protocol ghi lại mã băm của kho, của `NS00` và của `NS01`. Chương trình từ chối chạy nếu kho chưa được chấp nhận ở bước 4, hoặc nếu cỡ mẫu và seed khác `NS00`.

## 6. Chạy và gửi lại
```bash
pwsh -File scripts/run_v16.ps1 -Phase natural2 $A
```
Pha này chạy lấy mẫu, V15.2 test (lock giữ nguyên), bản biên dịch, phân tích N1–N4, và so sánh với `outputs/NP16`. Thời gian tương đương lần NP16. Gửi lại `KET_QUA_V16_NAT2.zip`, gồm NS2, NP16B, V16_NAT2, C16_NAT2 và provenance của kho.

Nếu V15.2 test báo `INCONCLUSIVE_REGION_TOO_SMALL`, đó là cổng 10 nhóm của V15.2, không phải lỗi; các endpoint tự nhiên N1–N3 vẫn tính được.

## 7. Quy tắc
- Không mở hay phân tích kho ngoài bước 4. Không sinh lại kho với tham số khác.
- Nếu bước sinh bị gián đoạn: sinh lại với **cùng** `NS00` và cùng seed. Nếu kho ra khác, phải ghi lại trong nhật ký.
- Không chạy song song; không dùng máy cho việc nặng khác trong lúc đo; không cập nhật hệ điều hành.
- Mọi lỗi: gửi nguyên file log, không tự sửa code.

## 8. Đọc kết quả
- `NP16B/NP03_SUMMARY.md`: N1–N4 và kết luận (`NATURAL_GAIN` / `NATURAL_NO_HARM` / `NATURAL_HARM`).
- `NP16B/NP05_COMPARISON.md`: tỷ lệ R của UMa so với UMi, kèm khoảng tin cậy Newcombe.
- `C16_NAT2/CC04_compiled_decision.json`: C1 (số sai khác phải bằng 0) và mục kiểm tra độ chính xác đơn/kép (số quyết định thay đổi phải bằng 0).
