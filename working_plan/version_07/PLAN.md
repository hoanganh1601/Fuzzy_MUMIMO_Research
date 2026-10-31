# Version 07: mục tiêu và bản ghi quy trình

Tài liệu này được lập khi đóng gói sau run. Nó tổng hợp yêu cầu và cấu hình đã dùng trong phiên hướng dẫn; không phải preregistration hay bằng chứng kế hoạch được commit trước khi chạy.

Mục tiêu: chẩn đoán failure của MU-MIMO bằng ZF/RZF với CSI margin cố định. Chạy từng CP theo PDF; dừng để xem kết quả trước khi sang CP sau. Real data lưu dưới `/media/icnlab/Data/hoanganh/datasets`.

Trình tự đã thực hiện: CP00 khóa manifest → CP01 scan → CP02 summary → CP03 paired comparison → CP04 geometry diagnosis → CP05 scope → CP06 integrity.

Dataset được tái sử dụng từ version 06, bao gồm các nhóm đã được xem. Mọi so sánh là exploratory/descriptive. Quy trình này không làm thay đổi kết luận CP05_FAIL của version 06.

Phân tích tiếp: kiểm tra thang đo kênh/nhiễu và lưới ngân sách cho 44 geometry có budget failure; xem scheduling/grouping/beam space cho 19 geometry chỉ có coupling/zero gain. Mọi luật beam mới cần được khóa trên development và đánh giá trên dữ liệu độc lập.
