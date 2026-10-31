# Đối chiếu run với GUIDE_IEEE_VI.pdf

Run: `DM_ASU35_BEAM_DIAG_20261031`. Bản ghi này được lập sau khi hoàn tất run; không phải đăng ký trước thí nghiệm.

## Kiểm tra đã thực hiện

1. So sánh byte của `code/beam_feasibility.py` và `docs/GUIDE_IEEE_VI.pdf` với ZIP gốc: trùng khớp.
2. CP00 khóa dataset SHA-256, source SHA-256, q và các tham số. Dataset có `(160,16,4)`, 160 nhóm, metadata `xyz/scenario`.
3. CP01 có 5.600 dòng; các trạng thái là FEASIBLE 2.628, COUPLING_RHO_GE_ONE 1.950, POWER_BUDGET 997, ZERO_ROBUST_DIRECT_GAIN 25. Không có trạng thái solver/numerical khác trong run này.
4. Chạy `--stage report` của engine gốc trong thư mục tạm, đọc bản sao 160 task đã hoàn thành với đúng cấu hình CP00. Cả năm file CP01–CP05 khớp từng byte với các runner chạy riêng từng CP.
5. Sáu checksum CP00–CP05 do report gốc sinh khớp sáu checksum tương ứng của CP06 hiện tại. CP06 bổ sung năm sidecar provenance nên có 11 dòng.
6. Chạy lại `run_cp06.py --verify-only`: xác minh đủ 11 artifact và snapshot code.

## Khác biệt có chủ đích

- Dùng các runner riêng để dừng/kiểm tra từng CP theo yêu cầu người dùng; engine toán học gốc không bị sửa.
- Dùng đường dẫn dataset tuyệt đối bên ngoài repo và run ID riêng.
- Giữ q đầy đủ `2.9604143746015965` từ run calibration trước, thay vì default đã làm tròn `2.960414` của CLI; q giữ cố định trong toàn bộ đối sánh.
- Thêm provenance và kiểm tra dữ liệu/source/môi trường trước khi tổng hợp.
- Fixture gốc thực tế có 36 geometry; mô tả 12 trong README upstream tương ứng quy mô demo nhỏ hơn. Run smoke không đặt giới hạn nên tạo 1.260 dòng.

## Phạm vi xác minh

Các kiểm tra trên chứng minh tính nhất quán của luồng thực thi và artifact với source/PDF được cung cấp. Chúng không xác nhận sai số CSI thực tế, tính độc lập của geometry hoặc hiệu chuẩn đơn vị vật lý. LP vẫn tuân theo các nhánh xử lý của source gốc; các dòng `POWER_BUDGET` được trả về trước bước LP. Kết luận run là `DIAGNOSTIC_ONLY`.
