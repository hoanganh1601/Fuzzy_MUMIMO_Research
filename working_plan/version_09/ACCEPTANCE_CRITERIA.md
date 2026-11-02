# Tiêu chí đã kiểm tra cho version 09

Bản ghi hồi cứu sau run; không phải tiêu chí được preregister trước khi xem dữ liệu.

- Source/test/guide/fixture nguyên byte so ZIP và bảng hash upstream.
- Hai test gốc đạt: random no-false-pruning và high-noise norm certificate.
- CP00: signature, dữ liệu, hai file code, tham số và 160 nhóm nhất quán; bộ đọc gốc chấp nhận H complex hữu hạn `(160,16,4)`.
- Scan: 160 task hoàn tất, đúng geometry/signature, mỗi reference đủ 105 ứng viên không trùng; hai luồng khớp cardinality/subset/alpha và power trong tolerance 1e-7.
- CP01: record sàng lọc duy nhất; không có ứng viên mang cờ pruned nhưng reference FEASIBLE.
- CP02: đúng 160 quyết định và nghiệm oracle tối ưu theo thứ tự từ điển trên reference; các count tách evaluated/certificate/cardinality cộng thành 105.
- CP03: đủ 16,800 ứng viên, status và công suất nhất quán với candidate records và task đã lưu.
- CP04: tổng count theo reason khớp CP01; cardinality-skipped không bị gọi nhầm là physically infeasible.
- CP05: các mean được tính lại từ CSV và khớp; số lần gọi solve được phân biệt với LP calls; runtime chỉ là số đo cùng lượt chạy.
- CP06: sáu hash CP00–CP05 khớp, giữ nguyên CP06 gốc; bảy CP được sao chép nguyên byte vào log.
- SOURCE_SHA256/ARTIFACT_SHA256 bổ sung được kiểm tra cả trên disk và Git blobs để phát hiện đổi line ending.

Đạt kiểm chứng thuật toán trên development; không suy ra kiểm chứng dữ liệu độc lập, tối ưu beamforming liên tục, outage probability, fairness, throughput hoặc latency. Có ưu thế tính toán quan sát trên run này; benchmark lặp/độc lập chưa được thiết lập.
