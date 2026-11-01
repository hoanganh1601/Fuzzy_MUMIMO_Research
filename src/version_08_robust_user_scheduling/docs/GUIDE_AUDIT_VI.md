# Đối chiếu implementation với GUIDE_IEEE_VI.pdf

Bản ghi này được lập khi đóng gói sau run, không phải preregistration.

- Engine `admission_beam.py`, `make_smoke.py`, requirements và PDF/TeX trùng byte với ZIP ngày 2026-11-01.
- CP00 khóa q đầy đủ `2.9604143746015965` từ version 07; PDF dùng default làm tròn `2.960414`. Các run giữ nguyên q/sigma/SINR/noise/Pmax/codebook sau khóa.
- Beam được tính lại trên từng tập con bằng hàm gốc; không dùng submatrix của beam đủ 4 user.
- CP01 chạy 15 tập con × 7 beam. Quyết định oracle/greedy được trì hoãn đến CP02 theo yêu cầu chạy từng CP.
- G1 helper bổ sung tái dựng các hệ số và kiểm tra độc lập scaled LP, kể cả stable case vượt Pmax. Kiểm tra đơn điệu dùng ngân sách dưới/trên P_req hoặc nửa/gấp đôi Pmax cho coupling/zero gain, không chọn lại cấu hình từ các phép thử này.
- G2 xác minh ưu tiên cardinality rồi power. G3 chỉ so power khi cùng số người dùng dương và giữ số lời gọi/runtime gốc của thuật toán; audit G1 tách riêng.
- CP01–CP05 của cả smoke và DeepMIMO được đối chiếu byte với `--stage report` upstream đọc bản sao task trong thư mục tạm. CP06 giữ 6 checksum upstream tương ứng và thêm 5 sidecar.
- `run_cp06.py --verify-only` xác minh 11 artifact và code snapshot, không cần channel dataset/task cache.

## Các khác biệt và giới hạn được ghi nhận

Tuyến tách CP dùng task trung gian có `cp01_complete=true`, `complete=false`; đến CP02 mới có oracle/greedy và complete=true. Source gốc không sửa, nhưng task trung gian cần tiếp tục bằng runner tương ứng thay vì trộn với scan/report upstream.

Fixture có 24 geometry; smoke chỉ chọn 12. Real run có 160 geometry DeepMIMO đã xem trước đây, nên chỉ là development. H DeepMIMO được xem như CSI ước lượng đầu vào với bất định thiết kế; chưa xác minh một bộ ước lượng CSI hoặc phân bố sai số thực.

CSV CP03/CP04 giữ semantics upstream cho cả hai cùng phục vụ 0 user: gap=0 nhưng `same_cardinality=0`; power ratio để trống. Không diễn giải cột match fraction upstream là equality kể cả zero-service nếu dataset có trường hợp đó.

Runtime exhaustive và greedy được thu ở hai CP khác nhau. Các quan sát runtime/call count không chứng minh lợi ích trên dữ liệu độc lập. G4 vẫn `NOT_ESTABLISHED`; không có certificate, global beamforming optimum, fairness/throughput hay outage probability claim.
