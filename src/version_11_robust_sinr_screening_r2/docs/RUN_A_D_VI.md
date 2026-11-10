# R2 — Hợp nhất code và chạy lại toàn bộ Section V (A–D)

**Ngày:** 06/11/2026 · **Cơ sở:** gói 01/11, 02/11, 04/11, 06/11 và bản sửa R1 (`CHANGELOG_R1_20261106.md`).
**Kiểm tra:** 23/23 unit test PASS; `solve()` mới trùng bit với bản cũ trên 7.560 lần đánh giá ứng viên (3 mức $P_{\max}$ × 24 geometry × 105 ứng viên).

## 1. Thay đổi code so với R1

| # | File | Thay đổi | Lý do theo manuscript |
|---|---|---|---|
| R2-1 | `reference_model.py` | Tách `solve()` thành `coefficients()` (beam, $\mathbf g$, $\mathbf a$, $\mathbf F$, $\mathbf u$) và `power_solve()` ($\rho$, $\mathbf p^*$, kiểm toán LP); thứ tự phép tính giữ nguyên. | Fig. 2: subset → beam → screening → power allocation. Mỗi ứng viên chỉ tạo beam một lần; bản cũ tạo lại beam trong bộ giải cho mọi ứng viên sống sót. |
| R2-2 | `reference_model.py` | `select_best()`: (1) nhiều người dùng nhất; (2) công suất nhỏ nhất, coi bằng nhau nếu lệch tương đối ≤ 1e-9; (3) $\alpha$ nhỏ hơn (ZF trước RZF); (4) nhãn tập con nhỏ nhất. Mọi thuật toán chọn nghiệm qua hàm này. | Section III: quy tắc tie-breaking xác định. |
| R2-3 | `ablation_audit.py`, `ablation_certified.py` | Screening hai giai đoạn: `NORM_NOISE_LOWER_BOUND` chạy trước khi tạo beam; các quy tắc còn lại dùng chung hệ số với bộ giải qua `cache`. Tách thời gian `beam_ms`, `screening_ms` (không gồm beam), `solver_ms`. | Đo đúng chi phí từng khối của pipeline. |
| R2-4 | `ablation_certified.py` | Mỗi geometry chạy EXHAUSTIVE và 7 biến thể `--repeats` lần (mặc định 5); thứ tự xáo trộn theo seed; báo cáo median. Thêm CP01b (từng lần lặp), CP08 (chi phí beam và power solve theo trạng thái tham chiếu), phân bố số người dùng, CI so với exhaustive. | Section V-B: so sánh exhaustive / cardinality-only / all certificates, runtime ghép cặp có lặp. |
| R2-5 | `run_manuscript.py` (mới) | Một lệnh chạy A+B → C → D (lock → preflight → scan → report cho từng tập test) rồi sinh `*_MANUSCRIPT_TABLES.md` và `*_manuscript_results.json` từ checkpoint. Có thể chạy tiếp khi bị gián đoạn. | Bảng A, B, B2, C, D theo khung bài báo. |
| R2-6 | `make_synthetic.py` (mới) | Kênh đa đường ULA tổng hợp theo khối không gian (32 nhóm × 5 drop), suy hao 35 dB/decade, shadowing 4 dB. **Không phải DeepMIMO hay 3GPP.** | Diễn tập pipeline khi chưa có dữ liệu ray-tracing. |

## 2. Kết quả diễn tập (DỮ LIỆU TỔNG HỢP — không được đưa vào manuscript)

Cấu hình: $M=16$, $K=4$, $q_c=2.960414$, $\sigma=0.04$, SINR 6 dB, $N_0=2\cdot10^{-13}$ W, $P_{\max}=1$ W, 7 lựa chọn beam, 105 ứng viên/geometry, 5 lần lặp, 2.000 mẫu bootstrap. Bảng đầy đủ: `rehearsal/outputs/REH_MANUSCRIPT_TABLES.md`.

| Chỉ số | Exhaustive | Cardinality-only | All certificates |
|---|---|---|---|
| Nghiệm khớp exhaustive | 160/160 | 160/160 | 160/160 |
| Lời gọi giải đầy đủ / geometry | 105,000 | 28,875 | 11,375 (−60,61% so với cardinality-only) |
| Beam được tạo / geometry | 105,000 | 28,875 | 28,875 |
| Runtime / geometry (ms) | 91,54 | 13,43 | 14,14 (+5,24%; CI95 của mức tiết kiệm [−0,85; −0,57] ms) |

- A: 53/160 geometry phục vụ 4 người dùng, 95/160 phục vụ 3, 12/160 phục vụ 2; 0 loại nhầm trên 16.800 lần kiểm toán ứng viên.
- C: PASS — 430 trường hợp, 215 trường hợp tham chiếu khả thi, 0 loại nhầm, 50 lần fail-open.
- D (tập tổng hợp seed 202, khóa trước khi sinh dữ liệu): 160/160 khớp exhaustive, 0 loại nhầm, giảm 17,63 lời gọi/geometry, runtime +4,32%, GO = False.

**Cơ chế (CP08).** Certificate chỉ loại các ứng viên mà bộ giải đầy đủ vốn bác bỏ rất nhanh: bác bỏ do coupling tốn 0,0149 ms, do vượt ngân sách công suất 0,0311 ms. Ứng viên khả thi tốn 1,0045 ms (chủ yếu là kiểm toán LP) nhưng không bao giờ bị loại. Tính trên mỗi geometry, screening tốn 1,215 ms trong khi thời gian power solve tránh được chỉ khoảng 0,385 ms. Phần runtime giảm so với exhaustive (−84,56%) đến từ thứ tự duyệt theo số người dùng, không đến từ certificate.

## 3. Hệ quả cho manuscript (cần quyết định)

1. **Bảng B của v10 phải được tạo lại.** Các số 19,3375 → 8,5375 lời gọi và −7,26% runtime được đo khi baseline cardinality-only vẫn chạy screening và tạo beam hai lần. Trên dữ liệu diễn tập, chiều runtime đảo ngược. NEXT STEP{chạy `run_manuscript.py` trên tập DeepMIMO v10 160 geometry}.
2. **C3 nên định vị là giảm số lời gọi bộ giải có chứng nhận**, không phải giảm wall-clock. Lợi ích runtime chỉ xuất hiện khi việc phát hiện infeasibility của bộ giải theo từng ứng viên tốn kém (ví dụ bộ giải robust SDP/SOCP). NEXT STEP{thử nghiệm với bộ giải đắt hơn trước khi khẳng định tăng tốc}.
3. `NOISE_LOWER_BOUND` là trường hợp $L_0$ của Proposition 2 và luôn bị bao bởi $L_N$ với $N\ge1$: bỏ quy tắc này không làm thay đổi số lời gọi (Δ = 0). Nên gộp vào Proposition 2 thay vì trình bày như certificate riêng.
4. `NORM_NOISE_LOWER_BOUND` không kích hoạt lần nào trên dữ liệu diễn tập. Vai trò duy nhất của nó là tránh tạo beam khi hệ thống bị giới hạn công suất; chỉ nên giữ trong bảng ablation nếu nó kích hoạt trên DeepMIMO.
5. Proposition 3 viết $F_{ij}F_{ji}\ge1$; code chỉ loại khi tích $>1+10^{-8}$ (numerical guard). Cách này nhất quán với đoạn "Numerical safeguards", cần ghi rõ trong bài.
6. Section V-C: số liệu "80 trường hợp, 7 fail-open" đã lỗi thời. Với `--limit 20`, mã R2 cho 430 trường hợp, 50 fail-open, chia thành 3 họ đại số và họ kênh.

## 4. Cách chạy trên dữ liệu thật

```bash
python -m unittest discover -s tests -v
# Bước 1 — khóa protocol D TRƯỚC khi mở bất kỳ tập test nào
python code/independent_validation.py --stage lock --run-id DM_NEW01 --repeats 5 --bootstrap 2000
python code/independent_validation.py --stage lock --run-id S3GPP01 --repeats 5 --bootstrap 2000
# Bước 2 — chạy toàn bộ A–D và sinh bảng
python code/run_manuscript.py --tag V11 --dev data/deepmimo_v10.npz --dev-label "DeepMIMO v10 development set" \
  --test DM_NEW01 data/deepmimo_new.npz data/deepmimo_new_provenance.json \
  --test S3GPP01 data/sionna_3gpp.npz data/sionna_provenance.json
```

Trên Windows nên dùng `CHAY_TOAN_BO.ps1` (xem `HUONG_DAN_NCS.md`). Nếu gõ lệnh trực tiếp trong PowerShell, viết trên một dòng hoặc thay `\` bằng dấu backtick. Có thể chạy A–C trước bằng `--skip D` khi chưa có tập test. Ước lượng thời gian: khoảng 1,1 s/geometry cho A+B (với 5 lần lặp) và 0,3 s/geometry cho D.

## 5. Bản R2.1 — tương thích máy Windows đã chạy v10

- Mọi file JSON được đọc/ghi bằng UTF-8; console được chuyển sang UTF-8 (`utf8_console()`), tránh lỗi cp1252 và tránh mismatch chữ ký khi đường dẫn có tiếng Việt.
- `run_manuscript.py --test RUNID DATA PROV` nhận 3 tham số tách rời (bản cũ tách theo `:`, nên hỏng với `C:\...`).
- `jwrite`/`cwrite` thử lại `os.replace` khi gặp `PermissionError` (OneDrive, antivirus).
- `code/check_env.py`: kiểm tra phiên bản, chạy 23 test, so dấu vân tay quyết định trên `smoke.npz` với `code/expected_smoke_fingerprint.json`, kiểm tra định dạng và SHA-256 của tập dữ liệu (nhận diện tập v10).
- `CHAY_TOAN_BO.ps1`: một lệnh chạy check → lock → A–D → đóng gói `KET_QUA_<Tag>.zip`.
- Cú pháp tương thích Python ≥ 3.8 (đã kiểm tra bằng `ast`, `feature_version=(3,8)`).
- Code tính toán không đổi: 23/23 test PASS; dấu vân tay smoke MATCH.
