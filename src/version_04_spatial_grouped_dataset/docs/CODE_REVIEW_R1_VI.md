# Rà soát mã, logic và toán học — Fuzzy MU-MIMO margin pilot (R1, 19/10/2026)

Phạm vi: `code/experiment.py`, `code/generate_data.py`, `code/import_3gpp.py`, `tests/test_invariants.py`, `docs/RESEARCH_AND_GUIDE_IEEE_VI.tex`. Dữ liệu smoke được sinh lại với cùng seed. `H` và `groups` trùng từng bit với bản giao; tệp `umi_smoke.npz` chỉ được thêm trường `noise_w`.

## 1. Những phần đã kiểm tra và đúng

| Hạng mục | Cách kiểm | Kết quả |
|---|---|---|
| RZF `V = Ĥ(ĤᴴĤ + αI)⁻¹`, cột chuẩn hóa | Giải tích + test | Đúng; α tỷ lệ với tr(ĤᴴĤ) nên không phụ thuộc thang đo |
| Hệ số `F`, `u` (chỉ số k = người nhận, j = luồng) | Đối chiếu từng chỉ số | Đúng |
| Nghiệm `p* = (I−F)⁻¹u` | So với `linprog` (HiGHS) trên 20 kênh | Trùng tới 10⁻⁶; là nghiệm LP nhỏ nhất (Bổ đề 1 trong `.tex`) |
| Tính SINR Monte Carlo (`einsum 'nmk,mj->nkj'` = h_kᴴv_j) | Đối chiếu công thức | Đúng; outage đồng thời theo mọi người dùng |
| Ghép cặp Monte Carlo | Cùng `SeedSequence([seed, idx, 921])` cho mọi phương án | Đúng |
| Không rò rỉ test | Đặc trưng fuzzy chỉ dùng Ĥ; chọn tham số chỉ trên validation | Đúng |
| Chia nhóm train/val/test | Test giao rỗng, phủ đủ | Đúng |
| Sugeno: tổng trọng số > 0 trên [0,1]² | Khoảng cách tới tâm ≤ 0,25 < 0,55 | Đúng; nhánh dự phòng không bao giờ được kích hoạt |
| Công thức suy hao UMi | 32,4 + 21 log₁₀d + 20 log₁₀f_c, σ_SF = 4 dB | Khớp TR 38.901 UMi-street-canyon LOS PL1 (chỉ phần large-scale) |

## 2. Lỗi logic/toán học (ảnh hưởng tới cách viết bài)

1. **Tập bất định được mô tả sai.** `.tex` và chú thích mã ghi `‖e_k‖ ≤ r_k`, với cận Cauchy–Schwarz. Trong mô hình sai số của mã, ‖e_k‖²/s_k² ~ Gamma(M,1) có kỳ vọng M = 8, với s_k = σ‖ĥ_k‖/√M. Với q = 2,96, hình cầu chỉ chứa sai số với xác suất 0,649 (Monte Carlo, 4·10⁵ mẫu). Để đạt 1 − ε/K, cần q = 3,95. Cận trong mã thực chất chỉ hợp lệ trên **tập dải** U(q) = {|e_kᴴv_j| ≤ q s_k, ∀j}, vì nó chỉ dùng hình chiếu của sai số lên các beam. R1 dùng đúng tập này trong mã, `.tex` và test.
2. **Bán kính "Gaussian" không có cơ sở.** R0 dùng q = √(2 ln(K/ε)) = 2,960. Với e_kᴴv_j ~ CN(0, s_k²), ta có P(|·| > q s_k) = e^{−q²}. Cận hợp trên K² dải cho q_G = √(ln(K²/ε)) = 2,402 (Mệnh đề 1). Kiểm Monte Carlo: tỷ lệ ra ngoài tập là 0,0488 với q mới và 0,0025 với q cũ. Phương án Gaussian của R0 vì vậy bảo thủ hơn mức ε = 5% mà nó tuyên bố. Trên pilot synthetic, đổi bán kính làm giảm công suất Gaussian 2,1 dB (2,458·10⁻⁸ → 1,510·10⁻⁸ W), với cùng 80/90 geometry có nghiệm. Đây là baseline mạnh mà Sugeno phải so sánh.
3. **Baseline fixed và threshold không được tinh chỉnh.** README ghi "tuned fixed and threshold baselines". Thực tế, `develop` chỉ chọn theo chỉ tiêu Sugeno; fixed và threshold nhận `qsmall` của ứng viên Sugeno được chọn. So sánh như vậy không công bằng. R1 cấp cho mỗi phương án sáu ứng viên trong cùng miền q ∈ [0,45; 1,8] và áp dụng cùng một quy tắc lựa chọn.
4. **Hướng luật Sugeno ngược với quy tắc ngưỡng.** Luật R0 tăng q theo z₂ (độ ghép kênh), còn threshold giảm q khi z₂ cao. R1 giữ cả hai họ luật và để validation chọn. Trên pilot, validation chọn họ `fall_with_coupling` (giảm q theo z₂).
5. **Tiêu chí chọn công suất bị thiên lệch.** R0 so công suất trung bình trên tập có nghiệm riêng của từng ứng viên. Ứng viên bỏ qua kênh khó (công suất cao) vì vậy có lợi. R1 so trên tập có nghiệm chung của các ứng viên đủ điều kiện; test `test_selection_uses_common_set` kiểm chứng điều này.
6. **Thang đo nhiễu làm hỏng dữ liệu UMi.** σ_n² = 10⁻⁹ W, trong khi suy hao UMi là 85–100 dB. Do đó R0 cho 0/3 geometry có nghiệm (smoke) và 0–1/30 (pilot). Nhiễu nhiệt 20 MHz với NF 9 dB là 6,3·10⁻¹³ W. Với giá trị này, cùng 90 geometry test cho 59–77 geometry có nghiệm; mọi trường hợp không có nghiệm là do ρ(F) ≥ 1, không phải do P_max. FACT{băng thông và NF phải khớp kịch bản của bài}.
7. **Ngưỡng số tuyệt đối.** Hai ngưỡng `diag ≤ 1e-24` và `+1e-12·I` trong RZF phụ thuộc thang đo kênh. Với kênh UMi (tr(ĤᴴĤ)/K ≈ 10⁻¹⁰), số hạng 10⁻¹² bằng khoảng 2,5% của tham số chính quy hóa. R1 chuyển sang ngưỡng tương đối; test `test_scale_invariance` cho thấy p* không đổi khi Ĥ → cĤ, σ² → c²σ², với c ∈ {10⁻⁶; 1; 10⁴}.

## 3. Lỗi mã đã sửa

| # | Lỗi | Sửa |
|---|---|---|
| 1 | `rzf()` trả `None` thì kênh bị bỏ qua lặng lẽ, làm effective failure bị đánh giá thấp | Ghi `feasible=0`, `reason=rzf_failed` |
| 2 | Không ghi lý do không có nghiệm | Cột `reason` (`spectral_radius_ge_1`, `power_gt_pmax`, `robust_desired_gain_zero`, …), tổng hợp trong `cp05` |
| 3 | Runtime chỉ đo bộ giải; fuzzy/threshold không bị tính thời gian tính đặc trưng | `runtime_total_s` = RZF + đặc trưng (với phương án thích nghi) + suy luận + bộ giải |
| 4 | Chữ ký chứa đường dẫn tuyệt đối của dataset và `frozen_from`; chuyển thư mục là mất hiệu lực | Dùng SHA-256 của dataset và của tệp frozen |
| 5 | Chuyển miền không kiểm tra tham số vật lý của tệp frozen | Báo lỗi nếu M, K, σ, SINR, ε khác nhau; từ chối tệp frozen R0 |
| 6 | Task checkpoint không gắn với tham số frozen | Thêm `frozen_sha`, kiểm tra khi dùng lại và khi report |
| 7 | Không có khoảng tin cậy hoặc so sánh trên tập có nghiệm chung, dù `.tex` yêu cầu | Wilson + bootstrap theo nhóm (`cp04`); `cp06_common_set_power.csv` (dB so với Gaussian) |
| 8 | Không có kiểm tra trên kênh thực | `actual_fail`: SINR trên kênh dataset |
| 9 | ε = 0,05 và ngưỡng chọn 0,10 bị gán cứng | `--eps`, `--select-target` |
| 10 | Validation tính lại kênh/MC cho từng ứng viên | Một context mỗi kênh, dùng chung cho 19 ứng viên |
| 11 | `import linprog` thừa; thông báo lỗi "need >= 5 groups" mâu thuẫn với yêu cầu ≥ 3 | Bỏ import; thống nhất thông báo |
| 12 | DeepMIMO: hàng `a` (y = a x) được dùng như `h` (y = hᴴx); tên thuộc tính `channel`/`channels` | Dùng liên hợp `h = conj(a)` (không đổi |hᴴv| nhưng đúng quy ước); đọc được cả hai tên; FACT{kiểm tra với bản DeepMIMO đã cài} |
| 13 | `__pycache__` nằm trong gói và trong bảng SHA | Bỏ |

Kiểm thử: `tests/test_invariants.py` có 9 test, tất cả PASS. Các test gồm: tối ưu LP, cận robust trên tập dải (mọi sai số trong U(q) đều thỏa SINR), độ phủ q_G, bất biến thang đo, chia nhóm, Sugeno, tiêu chí tập chung, thống kê, cùng end-to-end (khôi phục, phát hiện chữ ký lệch, chuyển miền, từ chối tham số lệch).

## 4. Pilot kiểm chứng (chỉ để kiểm mã, không đưa vào bài)

Synthetic, n = 360, 90 kênh test (3 nhóm), n_mc = 300, ε = 0,05, γ₀ = 6 dB:

| Phương án | Có nghiệm | Outage có điều kiện [bootstrap] | Effective failure [bootstrap] | dB so với Gaussian (tập chung 80) |
|---|---|---|---|---|
| Gaussian (q = 2,402) | 80/90 | 0/24.000 | 0,111 [0; 0,333] | 0 |
| Fixed (q = 1,25) | 85/90 | 4,28% [2,87; 5,66] | 0,096 [0,041; 0,191] | −0,96 [−1,56; −0,54] |
| Threshold (0,45/1,15) | 87/90 | 11,4% [7,0; 18,7] | 0,143 [0,070; 0,268] | −1,03 [−1,66; −0,58] |
| Sugeno (fall, q_s = 0,85) | 86/90 | 9,21% [6,77; 11,73] | 0,132 [0,088; 0,192] | −1,06 [−1,72; −0,61] |

Chuyển miền UMi-inspired (90 kênh, nhiễu 6,3·10⁻¹³ W, không tinh chỉnh): Gaussian có nghiệm 59/90 với 0 outage; Sugeno 73/90, outage 9,1%, −1,54 dB [−2,94; −0,96] trên tập chung 59.

Nhận xét:
- Gaussian có 0 lỗi trên 24.000 mẫu, dù bảo đảm chỉ là ≤ 5%. Cận tam giác rất bảo thủ, nên bảo đảm ε là bảo đảm dạng tập (đủ nhưng lỏng).
- Mức giảm công suất 1 dB của các phương án heuristic phải trả bằng outage 4–11%. Đây là đánh đổi, không phải lợi ích thuần.
- Chênh lệch giữa fixed, threshold và Sugeno nhỏ hơn 0,1 dB, với khoảng bootstrap chồng lấn. Pilot không phân biệt được Sugeno với baseline fixed đã tinh chỉnh.
- Không ứng viên Sugeno nào đạt ngưỡng validation 0,10 (tốt nhất 0,112), trong khi fixed đạt 0,021 tại q = 1,45. NEXT STEP{mở rộng lưới Sugeno lên vùng q lớn hơn, hoặc chọn theo outage có điều kiện ≤ ε, trước khi kết luận về fuzzy}.

## 5. Lưu ý khi dùng

- Run-id và tệp `cp02_frozen.json` của R0 không dùng được với R1. Cần chạy lại develop/freeze với run-id mới.
- PDF IEEEtran chưa được biên dịch lại, vì máy rà soát không có `IEEEtran.cls`. `docs/RESEARCH_AND_GUIDE_IEEE_VI_preview_article.pdf` là bản xem trước dùng lớp `article` từ cùng `.tex`.
