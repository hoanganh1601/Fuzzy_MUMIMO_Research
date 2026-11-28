# V18.3: hướng dẫn đo lại hai cấu hình M = 32 không ổn định thời gian

## 1. Mục đích và quy tắc đã khóa

Ở lần chạy M = 32 đầu tiên (`outputs_v18_m32`), hai cấu hình **M32_G10_E0.02** và **M32_G10_E0.04** có nhiều cặp đo thời gian bất thường.

**Cặp "cùng đường tìm kiếm" (identical-path pair).** Khi LRS định tuyến sang DCS, nó thực hiện đúng phép tìm kiếm của DCS; khi định tuyến sang PBS, nó thực hiện đúng phép tìm kiếm của PBS. Chỉ có thêm phép tính tải η. Vì vậy hai thời gian của một cặp như thế chỉ được khác nhau ở chi phí định tuyến (khoảng 1–2%) cộng nhiễu đo.

**Tiêu chí kiểm soát chất lượng (timing QC):**
- Một cặp là *bất thường* (discordant) nếu hai thời gian lệch nhau quá 1,5 lần.
- Cấu hình đạt QC nếu tỉ lệ cặp bất thường **≤ 1%**.

**Áp dụng hồi cứu cho toàn bộ kết quả đã có** (`results/RESULTS_V18/QC_TIMING_RETROSPECTIVE.csv`):

| Nhóm | Số cấu hình | Tỉ lệ cặp bất thường |
|---|---|---|
| V18, M = 8 và 16 | 18, tất cả đạt | 0,02–0,38% |
| M = 32, bảy cấu hình còn lại | 7, tất cả đạt | 0,04–0,11% |
| M32_G10_E0.02 | trượt | 9,19% (248/2700 cặp) |
| M32_G10_E0.04 | trượt | 5,93% (160/2700 cặp) |

Ngưỡng 1% nằm giữa hai nhóm này với khoảng cách rộng; nó được ghi vào tệp khai báo **trước** khi đo lại.

**Quy tắc báo cáo**, được ghi vào `G00c_retime.json` trước khi đo:
1. Kết quả đo lại **thay thế** các đầu ra runtime (G2, G3) của lần đầu chỉ khi đủ cả hai điều kiện:
   - lần đo lại đạt QC;
   - **mọi quyết định** trùng với lần đầu (cardinality, công suất, số lần gọi, định tuyến).
2. Nếu không đủ, báo cáo **cả hai** lần và đánh dấu cấu hình là *timing-unresolved*.
3. Mỗi cấu hình chỉ được đo lại **một lần**. Chương trình từ chối khai báo lần thứ hai có nội dung khác.
4. Giao thức, phép chia tập, bản đồ G02 và các drop được giữ nguyên. Không chạy lại `develop` hay `lock`.

QC chỉ là đầu ra phụ (auxiliary endpoint): nó không làm thay đổi verdict G1–G4.

## 2. Chuẩn bị máy

1. Dùng **đúng máy** đã chạy `outputs_v18_m32`.
2. Chép đè các tệp của gói V18.3 vào repo, gồm:
   - `v18/run_v18.py`, `v18/run_m32.py`
   - `v18/tests/test_qc.py`
   - `v18/HUONG_DAN_V18_M32_RETIME.md`
   - `results/RESULTS_V18/QC_TIMING_RETROSPECTIVE.csv`

   Không sửa thư mục `code/`.
3. Thư mục `outputs_v18_m32` của lần đầu phải còn nguyên.
4. Tệp `results/RESULTS_V15_2/V152_DM/...CP03...` (bản đồ đã công bố) phải còn. Thiếu tệp này, bước test sẽ dừng.
5. **Trước khi đo, tắt mọi tác vụ khác:**
   - trình duyệt, IDE, đồng bộ đám mây (OneDrive/Dropbox);
   - Windows Update, chống virus quét toàn bộ, lập chỉ mục tìm kiếm;
   - tác vụ GPU hoặc các lần chạy mô phỏng khác.

   Cắm sạc nếu dùng laptop và chọn chế độ năng lượng *High performance / Best performance*. Không để máy ngủ.

## 3. Các lệnh, theo thứ tự

Tất cả lệnh chạy từ thư mục gốc repo, trong môi trường Python đã dùng cho V18.2.

```bash
# 0. Kiểm tra mã (11 test, khoảng 2 giây)
python -m unittest v18/tests/test_qc.py v18/tests/test_v18.py

# 1. Khai báo đo lại: tạo outputs_v18_m32_retime, chép G00/G00b/G02 và G01 của hai cấu hình,
#    ghi G00c_retime.json (sha256 của G03 gốc, QC gốc, quy tắc báo cáo)
python v18/run_m32.py retime-setup

# 2. Kiểm tra độ ổn định của máy (khoảng 1–3 phút); lặp lại đến khi in STABLE
python v18/run_m32.py probe

# 3. Đo lại test và analyze cho hai cấu hình (ước tính 30–90 phút, tùy máy)
python v18/run_m32.py retime-run

# 4. So sánh với lần đầu: quyết định, QC, G2/G3, lần chạy được báo cáo
python v18/run_m32.py retime-compare

# 5. Ghi chú rồi đóng gói
python v18/run_m32.py retime-pack
```

**Bước 2 (probe).**
- Probe đo cùng một phép tìm kiếm DCS hai lần trên khoảng 20 drop, với K = 4 và 8.
- Mỗi cặp dùng đúng thống kê của bước test: trung vị của các lần lặp xen kẽ, thứ tự ngẫu nhiên.
- Probe gom ít nhất 200 cặp. Máy được coi là ổn định khi tỉ lệ cặp lệch quá 1,5 lần ≤ 1% **và** trung vị |log tỉ số| ≤ 0,03.
- Nếu in `NOT STABLE` (mã thoát 2): tắt thêm tác vụ, chờ vài phút, rồi chạy lại probe.
- Mỗi lần probe sinh một tệp `G11_probe_*.json`. **Giữ lại tất cả**, kể cả các lần không đạt.
- Chỉ sang bước 3 khi probe in `STABLE`.

**Bước 3 (retime-run).**
- Trong lúc chạy, nếu ≥ 6 trong 100 cặp gần nhất là bất thường, chương trình in `TIMING UNSTABLE`.
- Gặp cảnh báo này **không dừng chương trình**: chỉ cần tắt tác vụ gây nhiễu và ghi giờ xuất hiện vào NOTES.
- Nếu máy bị tắt giữa chừng, chạy lại đúng lệnh `retime-run`: bước test tiếp tục từ các realization chưa đo.

## 4. Điểm kiểm tra

| Sau bước | Phải thấy |
|---|---|
| 0 | `Ran 11 tests ... OK` |
| 1 | `Re-timing declared`; QC gốc in ra: khoảng 9,19% và 5,93%, `"pass": false` |
| 2 | `STABLE: timing may start.` |
| 3 | `outputs_v18_m32_retime/G07_SUMMARY.md` có cột `timing QC`; mỗi cấu hình có 2700 cặp |
| 4 | `G12_RETIME.md`: cột `decisions identical` = `True` ở cả hai dòng |
| 5 | `KET_QUA_V18_M32_RETIME_<ngày>.zip` |

**Xử lý sự cố:**
- **`decisions identical` = `False`:** đây là lỗi nghiêm trọng vì quyết định không phụ thuộc thời gian. Gửi ngay thư mục, **không** chạy lại.
- **QC đo lại vẫn > 1%:** cấu hình được báo cáo là *timing-unresolved*. Không đo lần thứ ba.

## 5. Ghi chú gửi kèm (`outputs_v18_m32_retime/NOTES.txt`)

Ghi các thông tin sau:
- ngày và giờ bắt đầu, kết thúc;
- máy (giống lần đầu?);
- các tác vụ đã tắt;
- số lần probe và kết quả từng lần;
- các lần cảnh báo `TIMING UNSTABLE` (nếu có);
- mọi sự kiện bất thường (máy ngủ, cập nhật hệ điều hành, mất điện).

Sau đó chạy lại `retime-pack` và gửi tệp zip.

## 6. Sau khi nhận kết quả

Bài báo được cập nhật theo `G12_retime_report.json` và đúng quy tắc ở mục 1:
- thêm các dòng M = 32 vào Bảng tổng quát hóa;
- thêm cột timing QC;
- cập nhật Sec. V-I, phần Limitations (chi phí định tuyến tăng theo M) và Conclusion.

Không có số liệu nào của lần đo lại được đưa vào bài trước khi kết quả về.
