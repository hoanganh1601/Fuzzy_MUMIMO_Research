# Code review R1 — Robust_Boundary_Independent_20261106

**Ngày:** 06/11/2026 · **Phạm vi:** 6 module trong `code/`, 3 file test, output smoke, hướng dẫn `.tex`.
**Kết quả kiểm tra:** 19/19 unit test PASS (8 test gốc + 11 test hồi quy mới); mọi script chạy end-to-end trên `smoke.npz`.

## 1. Lỗi đã sửa

| # | Mức | File | Lỗi | Cách sửa |
|---|---|---|---|---|
| F1 | **Nghiêm trọng (an toàn)** | `safe_pruning.py` | Ngưỡng loại 1e-10 chặt hơn dung sai 1e-9 mà `solve()` chấp nhận khả thi. Khi $P_{\max}=P_{\mathrm{req}}/(1+5\cdot10^{-10})$, certificate `NORM_NOISE_LOWER_BOUND` loại ứng viên trong khi `solve()` trả `FEASIBLE` (đã tái hiện với $\alpha=0$ và $\alpha=0.01$). Ngưỡng `TWO_CYCLE` $\ge 1-10^{-12}$ loại cả tích nhỏ hơn 1, không phải certificate. | Khai báo `POWER_REL_TOL=1e-9`, `PRUNE_REL_MARGIN=1e-8` một lần trong `reference_model.py`, mọi module import; kiểm tra `PRUNE_REL_MARGIN >= POWER_REL_TOL` khi nạp module. `TWO_CYCLE` chỉ loại khi tích $>1+10^{-8}$. |
| F2 | **Nghiêm trọng (kết luận runtime)** | `ablation_audit.py`, `ablation_certified.py` | Baseline `CARDINALITY_ONLY` vẫn gọi `screening()`; hàm này tính beam, $\mathbf g$, $\mathbf u$, $\mathbf F$ cho mọi ứng viên rồi bỏ đi. Trong smoke gốc, baseline tốn 3,4 ms screening trên 19,8 ms (≈17%), làm phép so sánh `CARDINALITY_ONLY − ALL` thiên lệch về phía `ALL`. | `screening()` trả ngay khi không bật quy tắc nào và chỉ tính đại lượng mà quy tắc đang bật cần (lazy). `selection()` bỏ qua screening khi `enabled` rỗng (`screening_ms = 0`). |
| F3 | **Cao (A1 rỗng)** | `boundary_stress.py` | (a) Họ `COUPLING` phía $\rho<1$ dùng $P_{\max}=5$ cố định, nhưng $P_{\mathrm{req}}\approx0.02/\delta \ge 20$, nên mọi trường hợp đều `POWER_BUDGET`: không thể quan sát loại nhầm. (b) Họ `POWER` có cận Neumann 4 bậc thấp hơn $P_{\mathrm{req}}$ khoảng $3.2\cdot10^{-4}$, nên không bao giờ chạm guard. (c) `PASS` chỉ yêu cầu 0 loại nhầm, không kiểm tra điều kiện "có kích hoạt fail-open" mà hướng dẫn yêu cầu. | (a) $P_{\max}=2P_{\mathrm{req}}$ ở phía $\rho<1$. (b) Giữ họ `POWER`, thêm họ `POWER_TIGHT` với $\mathbf F$ lũy linh, có cận Neumann đúng bằng $P_{\mathrm{req}}$. (c) `decide()`: PASS ⇔ 0 loại nhầm, có fail-open và có trường hợp tham chiếu khả thi; xuất thống kê theo từng họ. |
| F4 | Cao | `boundary_stress.py`, `ablation_certified.py` | `mpmath` không có trong thư viện chuẩn (môi trường kiểm tra không cài được). `power_reference` dùng trị riêng float khi $n>2$, nên không phải "tham chiếu nhiều chữ số". `mpf(str(float(x)))` lấy số thập phân ngắn nhất, không phải giá trị nhị phân chính xác. | Dùng `fractions.Fraction` (chính xác, không phụ thuộc thư viện ngoài). $\rho(\mathbf F)<1$ được quyết định chính xác qua M-matrix: mọi pivot khử Gauss của $\mathbf I-\mathbf F$ dương. Bỏ `mpmath` khỏi `requirements.txt`. Giữ tên cột `mp_*` để tương thích. |
| F5 | Trung bình | `boundary_stress.py` | Chữ ký checkpoint chỉ băm chính file này; sửa `reference_model.py`, `ablation_audit.py` hay `ablation_certified.py` (nơi chứa logic screening) không làm checkpoint mất hiệu lực. `report` dùng `assert` (bị bỏ khi chạy `python -O`). | Băm thêm 3 module phụ thuộc; thay `assert` bằng `RuntimeError`, báo rõ file thiếu. |
| F6 | Trung bình | `independent_validation.py` | Lock CP00 không gồm `repeats`, `bootstrap`, `min_groups` và seed, nên vẫn chỉnh được sau khi xem test. | Khóa trong `analysis`; seed thứ tự và seed bootstrap đọc từ lock. Đã kiểm tra: đổi `--bootstrap` sau lock → `RuntimeError`. |
| F7 | Thấp | `ablation_audit.py` | `false_certificates=0` được gán cứng. | Tính từ dữ liệu. |
| F8 | Thấp | Tất cả các `main()` | `--limit` âm làm N âm, dẫn tới `IndexError` ở `rows[0]`. | Thêm `check_count()`: kiểm tra `limit >= 0` và N ≥ 1. |
| F9 | Thấp | `independent_validation.py` | CP03 ghi `SURVIVE` cho cả trường hợp fail-open. | Ghi `FAIL_OPEN` riêng. |

## 2. Tác động đến kết quả (smoke, SYNTHETIC — không phải bằng chứng khoa học)

| Chỉ số (4 geometry, 2 lần lặp) | Bản gốc | Sau sửa |
|---|---|---|
| Lời gọi bộ giải tiết kiệm trung bình | 10,5 | 10,5 (không đổi) |
| Runtime tiết kiệm `CARDINALITY_ONLY − ALL` | +0,46 ms (+3,1%) | −1,16 ms (−9,4%) |
| Screening trong baseline | 3,4 ms/geometry | 0 ms |
| A1: trường hợp tham chiếu khả thi trong họ đại số | 5/20 (chỉ họ `POWER`) | 15/30 (cả ba họ) |
| A1: fail-open ở họ đại số | 1 | 2 |

**Diễn giải.** Khi baseline không còn phải tính beam thừa, biến thể `ALL` chậm hơn trên dữ liệu smoke, kể cả ở geometry tiết kiệm được 21 lời gọi. Nguyên nhân: các ứng viên bị certificate loại thường cũng bị `solve()` loại sớm (trước LP) với chi phí thấp, trong khi screening phải tính một beam cho mọi ứng viên. Do đó **không nên khẳng định tăng tốc runtime** dựa trên các lần chạy trước bản R1. Kết luận an toàn hiện có là mức giảm số lời gọi bộ giải.

## 3. Ghi nhận chưa sửa (thiết kế, cần quyết định)

1. **NEXT STEP{dùng chung beam/F giữa screening và solve}:** khi ứng viên sống sót, `solve()` tính lại beam. Truyền kết quả `build_Fu` vào bộ giải sẽ loại bỏ phần lớn chi phí của `ALL`; cần đổi giao diện `solve()` và chạy lại toàn bộ A2.
2. `robust_screen` dừng ở quy tắc đầu tiên kích hoạt; nếu quy tắc đó nằm trong guard thì fail-open mà không thử các quy tắc sau. Cách này an toàn nhưng có thể bỏ lỡ một certificate khác có biên rộng.
3. δ = guard (1e-5) là điểm sát mép: kết quả PRUNE hay FAIL_OPEN phụ thuộc làm tròn. Nên chọn danh sách δ không chứa đúng giá trị guard.
4. Kiểm tra trùng dữ liệu phát triển chỉ so SHA-256 của file; lưu lại file là vượt qua được. Có thể bổ sung băm nội dung mảng `H`.
5. `CP01_dataset_audit.json` lưu đường dẫn tuyệt đối, nên di chuyển thư mục làm checkpoint mất hiệu lực (hành vi chủ ý theo README).

## 4. Hiệu lực của các lần chạy cũ

Mã nguồn đã đổi nên mọi `run-id` và lock CP00 cũ đều mất hiệu lực (chữ ký khác). Cần chạy lại `lock → preflight → scan → report` với `run-id` mới. `smoke_outputs/` đã được tạo lại bằng code R1. `docs/GUIDE_…pdf` **chưa được build lại** (môi trường không có `IEEEtran.cls`); file `.tex` đã cập nhật và cần biên dịch lại bằng XeLaTeX.
