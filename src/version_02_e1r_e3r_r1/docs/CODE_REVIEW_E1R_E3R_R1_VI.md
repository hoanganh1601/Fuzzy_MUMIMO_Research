# Rà soát mã, logic và toán học — Fuzzy MU-MIMO E1-R–E3-R (R1, 21/10/2026)

Phạm vi: `code/experiment_r.py` và engine mà nó gọi (`code/experiment.py`), `tests/test_r_pipeline.py`, `docs/RESEARCH_GUIDE_E1R_E3R_IEEE_VI.tex`, `README_E1R_E3R.md`.

**Phát hiện đầu tiên.** Gói E1R–E3R được dựng trên bản R0: `experiment.py`, `generate_data.py`, `import_3gpp.py` và `test_invariants.py` trùng từng byte với bản trước lần rà soát 19/10. Vì vậy mọi lỗi R0 đã sửa (`claude/code_review_fuzzy_mumimo_R1_20261019_vi.md`) xuất hiện lại trong E1R–E3R. Bản sửa này thay engine bằng engine R1 đã kiểm chứng và viết lại `experiment_r.py` trên nền đó.

## 1. Lỗi kế thừa từ engine R0 (đã sửa bằng engine R1)

| # | Lỗi | Hệ quả trong E1R–E3R |
|---|---|---|
| 1 | q_G = √(2 ln(K/ε)) = 2,960 không có cơ sở; đúng là q_G = √(ln(K²/ε)) = 2,402 (cận hợp trên K² dải) | Baseline Gaussian bảo thủ thừa; tỷ lệ ra ngoài tập 0,25% thay vì 5%; trần luật fuzzy và fallback cũng lấy theo q sai |
| 2 | Tài liệu mô tả "biên chuẩn sai số" (hình cầu), trong khi cận chỉ hợp lệ trên tập dải \|e_kᴴv_j\| ≤ q s_k | Sai mô hình toán trong `.tex` |
| 3 | Ngưỡng tuyệt đối (1e-24, 1e-12·I) phụ thuộc thang đo kênh | Kênh UMi bị xử lý khác kênh chuẩn hóa |
| 4 | Nhiễu cố định 10⁻⁹ W | Gần như mọi geometry UMi vượt P_max |

## 2. Lỗi logic trong `experiment_r.py` (đã sửa)

1. **Bốn "finalist" là cùng một cấu hình fuzzy.** `development_grid` lồng vòng `qfixed` (5 giá trị) với lưới fuzzy (9 cấu hình), tạo 45 ứng viên nhưng chỉ 9 cấu hình fuzzy khác nhau. Do `qfixed` không ảnh hưởng `fuzzy_safe`, bốn ứng viên đầu bảng có chỉ tiêu giống hệt nhau. Smoke `smoke_v2/cp02` xác nhận điều này: id 0, 9, 18, 27 có cùng luật, cùng sàn 1,2, chỉ khác `qfixed`. Bước calibration vì vậy chỉ sàng lọc một cấu hình. Sửa: lưới riêng cho từng phương án; test kiểm finalist khác nhau.
2. **Bộ lọc an toàn suy biến thành margin hằng.** Luật nằm trong [1,15; 1,65], còn sàn ∈ {1,2; 1,7; 2,2}. Với sàn 1,7 và 2,2 (6/9 cấu hình), q_safe = sàn ở mọi geometry, nên `fuzzy_safe` thực chất là fixed margin. Lưới fixed {1,0; 1,4; 1,8; 2,2; q_G} lại không có 1,7, nên "fuzzy" có thể thắng chỉ vì baseline thiếu điểm lưới. Sửa: chỉ giữ sàn có hiệu lực với một phần luật (min c_ℓ < sàn < max c_ℓ); lưới fixed chứa mọi giá trị sàn và phủ miền đầu ra fuzzy; báo cáo `floor_active_rate`.
3. **Tập development (40% nhóm) không được dùng.** Lưới được quét trên validation; calibration vừa chọn trong bốn finalist vừa kiểm cổng trên cùng dữ liệu, nên cổng bị lạc quan (winner's curse). Sửa: quét lưới trên development → chọn trên validation → calibration chỉ kiểm đạt/không đạt.
4. **Baseline và fuzzy không cùng quy trình.** Fixed/threshold chỉ có 5 ứng viên, chọn trên validation và không qua calibration; fuzzy được chọn qua hai tập. Sửa: cả bốn phương án tinh chỉnh (fixed, threshold, fuzzy_raw, fuzzy_safe) đi qua cùng quy trình.
5. **So công suất trên tập có nghiệm riêng.** Cách này có lợi cho ứng viên bỏ qua kênh khó. Sửa: so trên tập có nghiệm chung của các ứng viên đạt cổng; test `test_rank_common_set` kiểm chứng.
6. **Quy trình chuyển miền trong README không chạy được.** `--frozen-from` nằm trong chữ ký, nên bước `test` (không kèm `--frozen-from`, đúng như README) báo "Code/data/settings changed". Lỗi đã tái hiện trên bản giao. Sửa: `--frozen-from` chỉ dùng ở bước freeze và nằm ngoài chữ ký; checkpoint task gắn `frozen_sha`; kiểm M, K, σ, SINR, ε khớp nguồn; mọi nhóm của tập chuyển miền là test (bản giao chỉ test 20% nhóm, dù không tinh chỉnh gì trên tập đó).
7. **RZF thất bại làm dừng cả lượt chạy** (`raise RuntimeError`). Sửa: ghi là không có nghiệm, lý do `rzf_failed`.
8. **Bootstrap theo geometry** bỏ qua tương quan trong nhóm, nên khoảng tin cậy quá hẹp. Sửa: bootstrap theo nhóm; thêm Wilson, dB, `actual_fail`, runtime tổng.
9. `--bootstrap` nằm trong chữ ký, nên đổi số lần bootstrap ở bước report buộc phải chạy lại toàn bộ. Sửa: loại khỏi chữ ký.
10. Sắp xếp với NaN power (ứng viên không có nghiệm nào) cho thứ tự không xác định. Sửa: khóa sắp xếp có xử lý NaN.

Kiểm thử: 9 test engine (`test_invariants.py`) và 7 test pipeline (`test_r_pipeline.py`), tất cả PASS. Các test pipeline gồm: split rời nhau; lưới không trùng và không suy biến; sàn thuộc lưới fixed; q_safe ≥ q_raw; xếp hạng trên tập chung; bootstrap ghép cặp; end-to-end gồm khôi phục, đổi bootstrap ở report, phát hiện chữ ký lệch, quy trình chuyển miền đúng README, từ chối tham số lệch.

## 3. Pilot kiểm chứng (chỉ để kiểm mã, không đưa vào bài)

Synthetic M = 16, K = 4, 480 kênh, 12 nhóm (160/120/80/120), n_mc = 300, γ₀ = 6 dB, ε = 0,05. Tập test gồm 120 geometry:

| Phương án | Có nghiệm | Conditional outage [bootstrap nhóm] | Effective failure | Tỷ số công suất so với Gaussian [CI] |
|---|---|---|---|---|
| Gaussian (q_G = 2,402) | 119/120 | 0,00% [0; 0,01] | 0,008 | 1 |
| Fixed (q = 1,4) | 120/120 | 2,33% [0,99; 3,58] | 0,023 | 0,920 [0,866; 0,961] (−0,37 dB) |
| Threshold (1,0/1,4) | 120/120 | 2,36% | 0,024 | 0,920 (−0,37 dB) |
| Fuzzy_raw | 120/120 | 2,73% | 0,027 | 0,918 (−0,38 dB) |
| Fuzzy_safe (sàn 1,4) | 120/120 | 2,33% | 0,023 | 0,920 (−0,37 dB) |

So với fixed, fuzzy_safe có tỷ số công suất 1,001 [1,000; 1,004]. Quyết định: `STOP_no_demonstrated_fuzzy_advantage`.

Chuyển miền UMi-inspired (480 geometry, nhiễu 6,3·10⁻¹³ W, không tinh chỉnh): kết luận giống trên. Fuzzy_safe so với fixed: 1,001 [1,000; 1,003]. Fuzzy_raw không đạt effective failure ≤ ε (0,058). Quyết định: STOP.

Giải thích: sàn của fuzzy_safe có hiệu lực ở 99,2% (synthetic) và 98,9% (UMi) geometry, nên fuzzy_safe thực chất là fixed q = 1,4. Nguyên nhân nằm ở phân bố đặc trưng đầu vào. z₂ = ρ(F(q_G))/2 có trung vị 0,05–0,06, và P(z₂ > 0,5) chỉ là 0,8–3,3%. z₁ = log₁₀κ/8 nằm trong [0,08; 0,35] (phân vị 5–95%). Do đó chỉ góc "thấp–thấp" của bảng 3×3 được kích hoạt, và đầu ra fuzzy chỉ dao động 1,31–1,61. Đây là vấn đề thiết kế, không phải lỗi mã. NEXT STEP{chuẩn hóa z₁, z₂ theo phân vị trên tập development (tâm tập mờ đặt tại phân vị 10/50/90%), rồi chạy lại quy trình trước khi kết luận về fuzzy}.

Mức giảm 0,37 dB của các phương án heuristic so với Gaussian phải trả bằng conditional outage khoảng 2,3%, so với 0% của Gaussian. Đây là đánh đổi, không phải lợi ích thuần.

## 4. Lưu ý khi dùng

- Run-id và `cp03_frozen.json` của bản giao không dùng được (chữ ký và định dạng frozen đã đổi).
- Hai PDF IEEEtran chưa được biên dịch lại, vì máy rà soát không có `IEEEtran.cls` và gói T5/vietnamese. `docs/*_preview_article.pdf` là bản xem trước biên dịch bằng XeLaTeX từ cùng nội dung `.tex`.
- Adapter DeepMIMO chưa chạy được do môi trường không có mạng. FACT{kiểm tra tên thuộc tính `channels`/`channel` và cấu hình anten với phiên bản DeepMIMO đã cài}.
