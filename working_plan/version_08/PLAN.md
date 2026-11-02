# Version 08: bản ghi mục tiêu và quy trình

Tài liệu được lập sau khi hoàn tất run để đóng gói. Đây là bản ghi hồi cứu yêu cầu/cấu hình đã áp dụng, không phải kế hoạch được commit trước khi chạy.

Mục tiêu: đánh giá lựa chọn tập người dùng kết hợp ZF/RZF khi giữ CSI margin cố định. Exhaustive duyệt 15 tập con × 7 beam; forward/backward là baseline. Ưu tiên số người dùng trước công suất.

Thứ tự đã thực hiện theo phiên hướng dẫn: kiểm tra gói → môi trường → smoke CP00–CP06 → kiểm tra dữ liệu ngoài Git → DeepMIMO development CP00–CP06. Mỗi CP được đọc và kiểm tra trước bước tiếp theo. Smoke và DeepMIMO là hai run của cùng source version.

Dataset hiện có được dùng lại từ version 06/07, nên chỉ là development. G1/G2 đã qua; G3 đã ghi số đo; G4 độc lập chưa được thực hiện. Nếu mở rộng, khóa thuật toán trước khi sinh/chạy các nhóm mới hoặc kênh 3GPP riêng, lưu cấu hình và báo cáo bất định theo nhóm.
