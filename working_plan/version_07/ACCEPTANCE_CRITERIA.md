# Kiểm tra checkpoint đã áp dụng

Bản ghi sau run về các gate đã áp dụng trong phiên hướng dẫn:

- CP00: input hữu hạn, dạng phức, shape/group nhất quán; checksum và tham số được khóa.
- CP01: đủ 160 geometry × 7 beam × 5 budget = 5.600 dòng; geometry/group và signature đúng; không có solver/numerical status cần dừng.
- CP02: 35 dòng tổng hợp, mỗi dòng có 160 geometry; `n_other=0`.
- CP03: 4.800 cặp, tỷ số công suất chỉ trên cặp cùng khả thi; số đếm marginal khớp CP02.
- CP04: 160 dòng tại budget factor 1; nhóm failure phân hoạch đầy đủ.
- CP05: scope `DIAGNOSTIC_ONLY`, không có certificate/global optimality/post-test beam selection claim.
- CP06: 11 artifact khớp checksum; provenance ghi snapshot code.

PASS của checkpoint không có nghĩa đạt statistical certificate. Các status vật lý bao gồm ZERO_ROBUST_DIRECT_GAIN, COUPLING_RHO_GE_ONE và POWER_BUDGET được giữ lại để chẩn đoán.
