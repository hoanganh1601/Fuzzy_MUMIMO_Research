# Version 09: bản ghi mục tiêu và quy trình

Lập hồi cứu ngày 2026-11-02 sau khi run hoàn tất để đóng gói repo; không phải kế hoạch đã commit hoặc preregistration trước run.

Mục tiêu: kiểm tra safe pruning có giữ nghiệm exhaustive trong 15 tập con × 7 beam, tránh loại nhầm ứng viên khả thi và giảm số lượt giải đầy đủ/thời gian quan sát hay không. Giữ cố định mô hình bất định CSI; ưu tiên số user trước công suất.

Quy trình thực tế: kiểm tra ZIP/checksum → cài môi trường → chạy hai test gốc → kiểm tra dữ liệu thật → native preflight → native scan → native report → kiểm toán CP00–CP06 và đóng gói. Người dùng chọn chạy DeepMIMO trực tiếp. Không có smoke run mới; `outputs/SMOKE` trong ZIP là ví dụ upstream và không nhập như bằng chứng của phiên chạy này.

Dùng nguyên `safe_pruning.py` và `reference_model.py`; không có runner tách CP. Preflight xuất CP00, scan lưu task và đối chiếu hai luồng, report xuất CP01–CP06 cùng lúc. Source/run thực thi ngoài Git trước khi tạo commit đóng gói; các fingerprints được đối chiếu khi nhập repo.

Dữ liệu 160 geometry đã được xem ở các version trước, nên kết quả được ghi là development. Giai đoạn sau cần khóa quy tắc trước dữ liệu mới, kiểm tra tính độc lập và báo cáo bất định theo nhóm. Việc kiểm tra hai luồng chọn nghiệm không thay thế kiểm chứng trên dữ liệu độc lập.
