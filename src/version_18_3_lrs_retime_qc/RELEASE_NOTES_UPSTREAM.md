# Robust MU-MIMO V18.3: kiểm soát chất lượng thời gian và đo lại (27/11/2026)

## Gói giao
`LRS_V18_3_retime_QC_20261127.zip` là bản vá đè lên repo `lrs-mumimo` V18.2. Thư mục `code/` không đổi.

| Tệp | Nội dung |
|---|---|
| `v18/run_v18.py` | Phiên bản V18.3 |
| `v18/run_m32.py` | Thêm các wrapper đo lại |
| `v18/tests/test_qc.py` | 3 test mới |
| `v18/HUONG_DAN_V18_M32_RETIME.md` | Hướng dẫn chạy |
| `results/RESULTS_V18/QC_TIMING_RETROSPECTIVE.csv` | QC hồi cứu |

## Tiêu chí QC (endpoint phụ, không đổi verdict G1–G4)
- **Cặp cùng đường tìm kiếm:** LRS định tuyến DCS so với DCS; LRS định tuyến PBS so với PBS.
- **Cặp bất thường:** hai thời gian lệch nhau quá 1,5 lần.
- **Đạt QC:** tỉ lệ cặp bất thường ≤ 1%.
- **Vị trí trong đầu ra:** các cột QC_pairs, QC_discordant, QC_rate, QC_pass trong G04; cột "timing QC" trong G07.
- **Cảnh báo khi chạy:** in ra nếu có hơn 5 trong 100 cặp gần nhất là bất thường.

## QC hồi cứu
- V18, M = 8 và 16: 18/18 cấu hình đạt, 0,02–0,38%.
- M = 32: 7/9 cấu hình đạt, 0,04–0,11%.
- Trượt: M32_G10_E0.02 (9,19%, 248/2700 cặp) và M32_G10_E0.04 (5,93%, 160/2700 cặp). Đây đúng là hai cấu hình đã nghi ngờ.
- Phân tích lại từ dữ liệu thô: không trường G04 gốc nào thay đổi.

## Các stage mới
- **`probe`:**
  - đo cùng phép tìm kiếm DCS hai lần, mỗi cặp là trung vị của các lần lặp xen kẽ;
  - ít nhất 200 cặp;
  - ổn định khi tỉ lệ ≤ 1% và trung vị |log tỉ số| ≤ 0,03;
  - ghi tệp G11_probe_*.json.
- **`retime-setup`:**
  - thư mục mới, chép G00, G00b, G02 và G01;
  - ghi G00c_retime.json gồm sha256 của G03 gốc, QC gốc, quy tắc báo cáo;
  - chỉ được khai báo một lần.
- **`retime-compare`:** ghi G12_retime_report.json và G12_RETIME.md, gồm quyết định trùng hay không, QC trước và sau, G2/G3 trước và sau, lần chạy được báo cáo.
- **Quy tắc báo cáo:** dùng lần đo lại chỉ khi QC đạt **và** quyết định trùng hoàn toàn; nếu không, báo cáo cả hai và đánh dấu timing-unresolved.

## Diễn tập (mock Sionna)
- 11/11 test đạt.
- Chuỗi setup → probe → retime-run → compare chạy được.
- Quyết định trùng: True.
- Khai báo lại với nội dung khác: bị từ chối.
- Sửa một quyết định: chuyển sang "both (timing-unresolved)".

## Bước tiếp
1. Nghiên cứu sinh chạy và gửi `KET_QUA_V18_M32_RETIME_<ngày>.zip`.
2. Sau đó cập nhật bài: các dòng M = 32 và cột timing QC trong bảng tổng quát hóa; Sec. V-I; Limitations (chi phí định tuyến tăng theo M); Conclusion.
3. Đưa RESULTS_V18_M32 vào repo.
