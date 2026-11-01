# Các gate đã áp dụng

Bản ghi sau run về tiêu chí đã kiểm tra trong phiên hướng dẫn:

- CP00: dữ liệu hữu hạn/phức `(N,M,4)`, M>=4, group/metadata và fingerprint nhất quán.
- CP01: đủ 15 tập con × 7 beam/geometry, không trùng/thiếu, chưa chạy quyết định CP02; chặn status numerical/rank cần xem xét.
- G1 trước quyết định CP02: unit-norm beam, direct gain, rho, analytic power/residual, scaled LP objective/residual và budget monotonicity.
- G2 trong CP02: oracle tối ưu theo cardinality rồi power trong candidate family; greedy choice phải tương ứng candidate khả thi.
- CP03: 2 cặp/geometry; gap không âm; power chỉ trên cặp cùng số user dương; lưu call counts.
- CP04: 3 dòng summary, đủ geometry cho từng method, chi phí và mức phục vụ hợp lệ.
- CP05: scope upstream `EXPLORATORY_EVALUATION`, không có independent improvement/certificate/global optimum claim. G3 chỉ ghi số đo; không tuyên bố forward nhanh hơn khi runtime quan sát cao hơn exhaustive.
- CP06: 11 artifact và snapshot code khớp; task cache/real dataset không nhập Git.

G4 chưa qua. Hoàn tất CP00–CP06 không đồng nghĩa hoàn tất independent validation hoặc đạt certificate.
