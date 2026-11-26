# V18 — Kiểm tra tính tổng quát của LRS: hướng dẫn chạy và điểm kiểm tra

V18 là gói **tách riêng** khỏi code chung của repo:
- Tất cả nằm trong thư mục `v18/`. Gói chỉ **đọc** `code/`, không sửa file nào, nên bản đồ chính sách đã công bố vẫn dùng lại được.
- Kết quả ghi vào `outputs_v18/`.
- Khi kết quả đạt yêu cầu và đã đưa vào bài, ta mới gộp V18 vào `lrs.py`.

## 0. Bốn câu hỏi và nơi trả lời

| # | Câu hỏi | Stage | File kết quả | Endpoint / thước đo |
|---|---|---|---|---|
| 1 | Điểm hòa vốn η = 1 có còn đúng khi đổi `M`, γ, ε và điều kiện kênh không? Bản đồ được phát triển lại trên tập development riêng, rồi kiểm tra trên drop held-out | `protocol`, `develop`, `lock`, `test`, `analyze` | `G02_maps.json`, `G04_endpoints.csv`, `G07_SUMMARY.md` | G1–G4 cho mỗi cấu hình |
| 2 | So với cận cardinality (Corollary), ascending-cardinality và greedy, khi cùng giao thức, cùng phần cứng, cùng họ candidate | `test`, `analyze` | `G05_comparison.csv` | tiết kiệm, số lần giải công suất, tỉ lệ cùng quyết định/cardinality, kiểm định hoán vị LRS–CBD |
| 3 | Khoảng tin cậy có đáng tin khi drop lồng trong scene không? Có thêm drop độc lập | `analyze` (và bước 1 sinh drop mới) | `G06_stats.json`, `G06b_leave_one_scene_out.json` | bootstrap hai tầng, ICC, n_eff, kiểm định hoán vị có cặp theo drop, số drop cần thiết |
| 4 | Runtime tốn ở stage nào trong bản compiled; mô hình chi phí và cận chi phí có đúng trên nhiều phần cứng không | `stages`, `hwbundle`, `hwcompare` | `G08_stages.csv`, `G08b_stage_shares.json`, `G10_op_costs.csv`, `HW_*/`, `G09_HARDWARE.md` | tỉ trọng stage, độ khép kín, R² và độ đúng dấu khi chuyển giữa các máy, tỉ lệ cận chi phí đúng |

**Các bộ lập lịch được so sánh.** Tất cả dùng chung một bộ giải C (`v18/native/screen_v18.c`), cùng họ ZF/RZF và cùng quy tắc tie.

| Tên | Mô tả | Chính xác? |
|---|---|---|
| DCS | baseline của bài (descending-cardinality) | có |
| PBS | DCS + cận pre-beam cho từng tập con | có (Prop. 3) |
| LRS | bản đồ phát triển lại theo từng cấu hình → PBS hoặc DCS | có |
| LRSPUB | bản đồ đã công bố (30 dBm, 6 dB, ε = 0,04, M = 16), áp nguyên cho cấu hình mới: kiểm tra khả năng chuyển giao | có |
| CBD | DCS bắt đầu từ s̄ của Corollary (bỏ qua mọi tầng > s̄, không cần kiểm tra từng tập con) | có (Corollary) |
| CBPBS | CBD + PBS | có |
| ACS | duyệt cardinality tăng dần 1..s̄, đánh giá mọi tầng | có |
| ACSSTOP | duyệt tăng dần, dừng ở tầng đầu tiên không có candidate khả thi | **không** (heuristic) |
| GREEDY | thêm từng người dùng, chọn candidate khả thi có công suất nhỏ nhất | **không** (heuristic) |

**Corollary (cận cardinality), để đưa vào bài sau khi có kết quả.** Gọi tải của từng người dùng là $\ell_k=\gamma N_0/\big(P_{\max}(\|\hat{\mathbf h}_k\|_2-r_k)_+^2\big)$, sắp xếp tăng dần $\ell_{(1)}\le\dots\le\ell_{(K)}$.
- Mọi tập con cỡ $s$ có $s(\mathcal S)\ge\sum_{i\le s}\ell_{(i)}$.
- Vì vậy nếu tổng này vượt 1, Proposition 3 loại mọi tập con cỡ $s$.
- Suy ra cardinality được nhận $|\mathcal S^\star|\le\bar s=\max\{s:\sum_{i\le s}\ell_{(i)}\le1\}$.
- *Chứng minh:* dùng Lemma 1(i) và việc sắp xếp tăng dần.

Mã dùng đúng quy tắc fail-open của PBS. Self-test kiểm tra: (a) PBS loại toàn bộ $\binom{K}{s}$ tập con ở mọi $s>\bar s$; (b) $\bar s\ge|\mathcal S^\star|$.

## 1. Chuẩn bị

- Repo `lrs-mumimo`, đã đặt thư mục `v18/` ở gốc repo.
- Dữ liệu trong `data/`: đã qua `python lrs.py data-check`.
- `gcc`.
- Môi trường Sionna 2.2.0 (chỉ cần cho bước 2).
- Đặt một luồng trước mọi lệnh có đo thời gian:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1          # Linux/macOS
# pwsh:  $env:OMP_NUM_THREADS=1; $env:OPENBLAS_NUM_THREADS=1; $env:MKL_NUM_THREADS=1
```

Trong khi chạy không chạy việc nặng nào khác trên máy, và không đổi chế độ nguồn hay tần số CPU.

**CK0 — kiểm tra phần mềm (khoảng 1 phút)**
```bash
python v18/run_v18.py selftest
python -m unittest discover -s v18/tests
```
Đạt khi thấy:
- `selftest V18: 576 configurations x 7 schedulers, 96 oracle checks, 0 failures`
- `Ran 8 tests ... OK`

Nếu có `FAIL`, dừng lại và gửi toàn bộ log về.

## 2. Sinh drop độc lập mới (câu 3, và M = 32 cho câu 1)

Sinh ba tập mới, **chưa ai mở**, mỗi tập 150 drop với seed mới và mảng 1×32. Các tập này chỉ dùng làm held-out. Các giá trị UMi/RMa dưới đây là giá trị bố trí thường dùng: **FACT{đối chiếu Table 7.2-1 / 7.8-1 của TR 38.901 đang dùng}** trước khi chạy.

```bash
O=outputs_v18
python code/scenario_spec.py --stage freeze --run-id NS18_UMI --out-root $O --set name=UMI_V18 --set sionna_scenario=umi \
  --set scenario=3GPP_TR_38.901_UMi_single_sector_ISD200 --set inter_site_distance_m=200 --set bs_height_m=10 \
  --set minimum_bs_ut_distance_m=10 --set indoor_probability=0.8 --set bs_antennas=32 --set pool_drops=150 --set pool_seed=20261201
python code/scenario_spec.py --stage freeze --run-id NS18_UMA --out-root $O --set name=UMA_V18 --set sionna_scenario=uma \
  --set bs_antennas=32 --set pool_drops=150 --set pool_seed=20261202
python code/scenario_spec.py --stage freeze --run-id NS18_RMA --out-root $O --set name=RMA_V18 --set sionna_scenario=rma \
  --set scenario=3GPP_TR_38.901_RMa_single_sector_ISD1732 --set inter_site_distance_m=1732 --set bs_height_m=35 \
  --set minimum_bs_ut_distance_m=35 --set indoor_probability=0.5 --set bs_antennas=32 --set pool_drops=150 --set pool_seed=20261203
for s in UMI UMA RMA; do
  l=$(echo $s | tr A-Z a-z)
  <python-sionna> v18/gen_sionna_3gpp.py --spec $O/NS18_$s/NS00_scenario_spec.json --output data/v18_${l}_fresh.npz --bs-rows 1 --bs-cols 32
  python code/scenario_spec.py --stage validate --run-id NS18_$s --out-root $O --pool data/v18_${l}_fresh.npz --provenance data/v18_${l}_fresh.npz.provenance.json
done
```

Ghi chú:
- `gen_sionna_3gpp.py` dùng lại các hàm của `code/gen_sionna_uma.py`, bản đã chạy được với Sionna 2.2.0. Nó chỉ thêm phần chọn mô hình UMi/UMa/RMa.
- Nếu Sionna báo lỗi tham số `RMa`, sửa đúng dòng có ghi `# ADAPT`.

**CK1:** mỗi tập in ra `POOL ACCEPTED`. File `outputs_v18/NS18_*/NS01_pool_validation.json` có `ok: true`, và `H` có dạng `(150, 32, 8)`.

**Không** sinh lại hay bỏ một tập sau khi đã nhìn kết quả. Nếu một tập lỗi kỹ thuật, ghi lý do vào `NOTES.txt` rồi sinh lại với **seed mới**.

## 3. Cố định protocol (trước mọi phép đo)

```bash
python v18/run_v18.py protocol \
  --set ASU=data/dev.npz --set LA=data/dm_pool.npz --set UMI_NE=data/gpp_pool.npz \
  --set UMI=data/natural_umi_pool.npz --set UMA=data/nat2_pool.npz \
  --set UMI_F=data/v18_umi_fresh.npz:hold --set UMA_F=data/v18_uma_fresh.npz:hold --set RMA_F=data/v18_rma_fresh.npz:hold \
  --grid-M 8,16,32 --grid-gamma-db 0,6,10 --grid-eps 0.02,0.04,0.08 \
  --min-ms 5 --repeats 3 --max-drops-per-set 150
```

Ý nghĩa:
- **Năm tập cũ** (`split`): chia 50/50 theo hash của nhãn drop thành development và held-out. Việc chia không phụ thuộc kênh, η hay runtime.
- **Ba tập mới**: chỉ là held-out.
- **Lưới tham số**: 27 cấu hình.
  - Cấu hình `M = 8` và `M = 16` dùng **mảng con** (M anten đầu tiên) của mọi tập.
  - Cấu hình `M = 32` chỉ dùng các tập 32 anten. Các tập này đều là held-out, nên các cấu hình `M32_*` sẽ ghi `NOT_EVALUABLE`. Nếu muốn có kết quả cho M = 32, sinh thêm một tập 32 anten với vai trò `dev` (ví dụ `--set UMA_D32=data/v18_uma_dev32.npz:dev`, seed khác) **trước** khi chạy `protocol`.
- **Khi đã có `G00_protocol.json`, không được đổi tham số nào.** Muốn đổi thì chuyển thư mục `outputs_v18` sang tên khác và bắt đầu protocol mới.

**CK2:** lệnh in số cấu hình và số drop development/held-out. Kiểm tra `G00b_split.csv`: mỗi tập `split` có cả `dev` lẫn `hold`. Dòng `NOTE: held-out set ... prior_use=...` cho biết tập đó đã từng được dùng; phải ghi điều này trong bài.

Muốn **ước lượng thời gian** trước, chạy `test --decisions-only` trên một thư mục protocol thử (`--out outputs_v18_try`), hoặc đo một cấu hình bằng `--configs M16_G6_E0.04`.

## 4. Development và cố định bản đồ

```bash
python v18/run_v18.py develop          # có thể giới hạn: --configs M16_G6_E0.04,M8_G10_E0.04
python v18/run_v18.py lock
```
- `develop` đo DCS và PBS trên các drop development. Nếu bị ngắt, chạy lại đúng lệnh đó để tiếp tục.
- `lock` phát triển một bản đồ cho mỗi cấu hình và ghi `G02_maps.json`. Quy tắc giống V15.2, nhưng ngưỡng là tương đối (2%), vì runtime compiled ở mức micro giây:
  - mỗi ô (K, L, bin η) chia fit/valid theo tỉ lệ 60/40;
  - ô được chọn PBS khi cận dưới CI95 trên phần valid lớn hơn 2%.

**CK3/CK4:**
- `lock` in `LOCKED` cho mọi cấu hình có drop development.
- `only_top_bin_active: true` nghĩa là bản đồ trùng đúng với quy tắc "PBS khi và chỉ khi η ≥ 1". Đây là dấu hiệu tổng quát đầu tiên.
- Nếu `lock` báo PBS khác DCS trên development, **dừng lại** và gửi log về.
- Sau bước `lock` không chạy `develop` lại.

## 5. Kiểm tra trên drop held-out

```bash
python v18/run_v18.py test
python v18/run_v18.py analyze
```
- `test` đo 9 bộ lập lịch trên các drop held-out.
- Khoảng 2% số (drop, K, L) được đối chiếu thêm với oracle Python.
- Nếu một bộ lập lịch chính xác cho kết quả khác DCS, dòng `WARNING exactness` hiện ra. Lệnh vẫn ghi lại và chạy tiếp, nhưng endpoint G1 sẽ thất bại.

**CK5/CK6:** đọc `G07_SUMMARY.md`.

| Endpoint | Đạt khi | Ý nghĩa |
|---|---|---|
| G1 | `True` ở mọi cấu hình | điều kiện bắt buộc |
| G2 | cận dưới CI của LRS trong R tại K_max > 2% và p hoán vị < 0,05 | đánh giá khi R ≥ 10 drop |
| G3 | cận dưới CI xấu nhất ngoài R > −2% | không gây thiệt hại |
| G4 | ≥ 95% | quy tắc η ≥ 1 đoán đúng dấu tiết kiệm |

Thêm vào đó:
- **η\*** là ngưỡng thực nghiệm, kèm CI. Nếu CI chứa 1 ở mọi cấu hình, có thể khẳng định "điểm hòa vốn nằm tại η = 1 trong miền đã thử".
- **`LRSPUB`**: nếu tiết kiệm của nó xấp xỉ `LRS`, bản đồ đã công bố chuyển được sang cấu hình mới mà không cần phát triển lại.
- **Bảng so sánh** (`G05_comparison.csv`), xem tại K_max:
  - tách được bao nhiêu phần tiết kiệm đến từ việc bỏ tầng (CBD) và bao nhiêu đến từ loại từng tập con (PBS);
  - GREEDY và ACSSTOP nhanh hơn bao nhiêu, và phải trả giá bằng tỉ lệ khác quyết định hay mất cardinality là bao nhiêu.
  - Cột `perm_p_LRS_vs_CBD_two_sided` là kiểm định hoán vị có cặp theo drop.

## 6. Thống kê phân tầng (câu 3)

`G06_stats.json`, cho mỗi cấu hình:
- **CI phân tầng theo scene**: suy diễn trên các scene đã có.
- **CI bootstrap hai tầng** (lấy lại scene trước, rồi đến drop): suy diễn sang scene mới. Khi có ít hơn 5 scene, kết quả này được đánh dấu là chưa tin cậy.
- **ICC giữa các scene, hệ số thiết kế, n_eff.**
- **Số drop cần** để CI có nửa độ rộng ±2 điểm phần trăm.

Nếu ICC lớn, độ chính xác bị giới hạn bởi **số scene**: phải thêm scene (bước 2 với kịch bản hoặc ISD khác), thêm drop trong cùng scene không đủ.

`G06b_leave_one_scene_out.json` (phân tích phụ): phát triển bản đồ khi bỏ ra một scene, rồi áp lên scene đó. Thời gian LRS trong phân tích này được suy từ DCS/PBS đã đo cộng với chi phí định tuyến đo được, nên phải ghi đúng là "inferred".

## 7. Runtime theo stage và chi phí từng phép toán (câu 4)

```bash
python v18/run_v18.py stages --max-drops 40          # cấu hình tham chiếu M16_G6_E0.04
python v18/run_v18.py hwbundle
```

**`stages`** chạy song song bản thư viện có bộ đếm thời gian theo stage và bản không đếm, trên cùng các bước xử lý. Kết quả:
- **Tỉ trọng**: load, bound, beam, coefficients, coupling, power, select, other.
- **`median_closure`**: tổng các stage chia cho thời gian ngoài. Cần ≥ 0,9.
- **`inflation_timed_over_untimed`**: chi phí của chính bộ đếm. Mọi endpoint runtime đều dùng bản **không** đếm.

**`hwbundle`** tạo thư mục `outputs_v18/HW_<máy>_<mã CPU>/`, gồm:
- chi phí từng phép toán theo cỡ tập con;
- hệ số mô hình chi phí, fit trên development và kiểm tra trên held-out;
- **độ đúng của cận chi phí**: tỉ lệ realization có tiết kiệm đo được ≥ cận dưới, tính từ phân vị 5%/95% của chi phí từng phép toán.

**CK7:** `median_closure` ≥ 0,9; R² held-out và độ đúng dấu được in ra.

**Trên các máy khác** (càng khác kiến trúc càng tốt, ví dụ Intel desktop, AMD server, Apple M, ARM):
1. Chép repo, `v18/`, dữ liệu, và **hai file** `outputs_v18/G00_protocol.json` và `outputs_v18/G00b_split.csv`.
2. Chạy:
```bash
python v18/run_v18.py selftest
python v18/run_v18.py hwbundle --quick --max-drops 60
```
3. Mang các thư mục `HW_*` về máy chính, rồi chạy:
```bash
python v18/run_v18.py hwcompare --bundles outputs_v18/HW_*
```

**CK8** (`G09_HARDWARE.md`), cho mỗi máy:
- R² và độ đúng dấu;
- độ đúng của cận chi phí;
- η\* và độ chính xác của quy tắc η ≥ 1;
- bảng chuyển hệ số giữa các máy, chỉ dùng một hệ số tốc độ.

**Diễn giải**: nếu độ đúng dấu khi chuyển máy ≥ 0,95 và CI của η\* chứa 1 trên mọi máy, thì điểm hòa vốn **không phụ thuộc phần cứng** trong số máy đã thử. Hệ số tuyệt đối thì đương nhiên khác nhau giữa các máy.

## 8. Gửi kết quả về

Nén toàn bộ `outputs_v18/` (bỏ `native/build` nếu có), gồm:
- `G00`–`G10`;
- các thư mục `HW_*`;
- `NS18_*`;
- `NOTES.txt`: những gì đã xảy ra trong lúc chạy.

File `G01_*.jsonl` và `G03_*.jsonl` là số đo gốc, **phải gửi kèm**.

## 9. Thời gian dự kiến (ước lượng trên máy đơn luồng của lần chạy đã công bố, cần xác nhận khi chạy)

| Bước | Ước lượng |
|---|---|
| Development | 18 cấu hình × khoảng 350 drop × 6 ô × 2 chính sách × 3 lần × ≥ 5 ms → khoảng 1–2 giờ |
| Test | 27 cấu hình × khoảng 650 drop held-out × 9 chính sách → khoảng 6–10 giờ. ACS và DCS ở K = 8 vùng power-limited chậm nhất |
| `stages` + `hwbundle` | khoảng 15 phút cho mỗi máy |

Mọi stage đều chạy tiếp được sau khi bị ngắt. Nếu thời gian không cho phép, chạy trước các cấu hình quan trọng bằng `--configs`, sau đó chạy các cấu hình còn lại **với cùng protocol**:
- `M16_G6_E0.04` (tham chiếu)
- `M16_G10_E0.04`
- `M16_G0_E0.04`
- `M8_G6_E0.04`
- `M16_G6_E0.08`

## 10. Điều được và không được khẳng định sau V18

- **Được**, nếu G1–G4 đạt ở mọi cấu hình có thể đánh giá: "trong miền M ∈ {8, 16, 32}, γ ∈ {0, 6, 10} dB, ε ∈ {0,02; 0,04; 0,08} và các kịch bản ASU, LA, UMi, UMa, RMa đã thử, điểm hòa vốn nằm tại η = 1 và LRS bảo toàn quyết định".
- **Không được** mở rộng ra ngoài miền này, sang bộ tiền mã hóa liên tục, hay sang triển khai song song.
- Nếu GREEDY hoặc ACSSTOP nhanh hơn LRS, bài phải nói rõ hai cách này **không** bảo toàn quyết định, và nêu tỉ lệ sai lệch đo được.
- Nếu CBD đạt gần mức tiết kiệm của LRS, phần đóng góp phải nêu rõ rằng phần lớn lợi ích đến từ việc **bỏ tầng** theo Corollary.
