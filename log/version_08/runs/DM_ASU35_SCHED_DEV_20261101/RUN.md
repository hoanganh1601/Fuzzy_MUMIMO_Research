# Run DM_ASU35_SCHED_DEV_20261101

## Provenance và trạng thái

- Code version: `version_08`; source commit đóng gói: `2137c3e46751e817510c2a5fcbb66e8f5b829886`.
- Vai trò dữ liệu: **development**; trạng thái **EXPLORATORY_EVALUATION**.
- CP00–CP06 hoàn tất; G1/G2 đã qua; G3 ghi số đo; **G4 chưa được xác minh**.
- Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`.
- Engine SHA-256: `163bd7b2fb2b0a1333cf06d8b1f1df9624c2d75b3bf7b864b1fdf26e00b9bba3`.
- q cố định `2.9604143746015965`, sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, Pmax=1 W.
- Codebook alpha=`0,0.001,0.01,0.05,0.1,0.3,1`; 15 tập con không rỗng; 160 geometry.

DeepMIMO `asu_campus_3p5`, dataset `deepmimo_asu35_v1`, shape `(160,16,4)`, metadata scenario/xyz. Dataset giữ nguyên thang đo tuyệt đối và đã được xem ở version 06/07; lượt này chỉ là development.

[Lineage dataset](../../../version_06/dataset_provenance/deepmimo_asu35_v1/deepmimo_provenance.json). Ma trận được dùng làm CSI ước lượng với bất định thiết kế; chưa xác minh chất lượng bộ ước lượng CSI thực tế.

Run thực thi ngoài Git trước khi nhập repo. Source commit trên là snapshot đóng gói khớp code fingerprints của run, không phải tuyên bố run đã thực thi từ một commit có sẵn. Manifest/provenance gốc giữ nguyên cả đường dẫn dataset/Python ban đầu. Ngày đóng gói: 2026-11-02; ngày trong run ID là định danh đã khóa, không đổi khi sang ngày mới.

## Kiểm tra checkpoint

- CP01: 16,800 dòng tập con–beam. Status counts: `{"COUPLING_RHO_GE_ONE": 1484, "FEASIBLE": 14222, "POWER_BUDGET": 1083, "ZERO_ROBUST_DIRECT_GAIN": 11}`. Đây là số case, không phải số geometry độc lập.
- G1: 16,800 ứng viên, 15,305 scaled LP audits, 16,800 kiểm tra ngân sách và 33,600 engine calls bổ sung. Audit không cộng vào chi phí thuật toán.
- Max relative analytic/LP gap: `1.3341767007420826e-13`; max scaled LP violation: `1.1932475635234554e-13`.
- CP02: 480 quyết định, 3 method/geometry; G2 kiểm tra lexicographic objective.
- CP03: 320 cặp, power chỉ so khi cùng số user dương.
- CP04: 3 dòng tổng hợp, mỗi method có 160 geometry.
- CP05: giữ scope upstream; không có independent improvement/certificate/global optimality claim.
- CP06: 11 artifact đã xác minh và code snapshot khớp sau khi sao chép.

## Mức phục vụ và chi phí

| Method | Mean users | Full 4 users | At least 1 | Mean calls | Mean runtime ms | Upstream positive-card match |
|---|---|---|---|---|---|---|
| exhaustive | 3.575000 | 60.625% | 100.00% | 105.00000 | 146.335950 | NA |
| forward | 3.575000 | 60.625% | 100.00% | 69.78125 | 162.330628 | 1.0 |
| backward | 3.575000 | 60.625% | 100.00% | 18.90000 | 24.608097 | 1.0 |

| Số user | Exhaustive geometries | Forward geometries | Backward geometries |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 1 | 0 | 0 | 0 |
| 2 | 5 | 5 | 5 |
| 3 | 58 | 58 | 58 |
| 4 | 97 | 97 | 97 |

## Đối sánh theo geometry

| Greedy | Card equality | Max gap | Power pairs | Mean power ratio | Max power ratio | Ratio mean calls | Ratio mean runtime |
|---|---|---|---|---|---|---|---|---|
| forward | 160/160 | 0 | 160 | 1.004788690 | 1.766190445 | 0.664583333 | 1.109301085 |
| backward | 160/160 | 0 | 160 | 1.000000000 | 1.000000000 | 0.180000000 | 0.168161663 |

Power ratio tính greedy/exhaustive trên cùng geometry và cùng số user dương. Runtime ratio là tỷ số hai thời gian trung bình, không phải trung bình tỷ số từng geometry. Metric CSV upstream `same_cardinality`/`oracle_cardinality_match_fraction` không tính both-zero là positive-card match; cardinality gap vẫn bằng 0 khi cả hai phục vụ 0.

Backward khớp cardinality và công suất exhaustive trên cả 160 geometry trong run, giảm 82% số lời gọi. Runtime trung bình quan sát giảm khoảng 83,18%, tương ứng tỷ số hai runtime trung bình khoảng 0.16816. Đây không phải bảo đảm greedy tối ưu với mọi dữ liệu.

Forward khớp cardinality nhưng runtime trung bình cao hơn khoảng 10,93% trong phép đo. Mean power ratio=1.004788690 đến từ một geometry (`54`, `asu_campus_3p5_g0054`) có tỷ số 1.766190445; 159 geometry còn lại có cùng công suất với oracle. Mean 0,48% vì vậy không mô tả penalty của case ngoại lệ.

| Method tại geometry 54 | Subset | Alpha | Power W |
|---|---|---|---|
| exhaustive | 012 | 0.01 | 0.05826583893691241 |
| forward | 023 | 0.01 | 0.1029085679859955 |
| backward | 012 | 0.01 | 0.05826583893691241 |

Subset dùng chỉ số user 0–3; ánh xạ UE gốc nằm trong selection provenance ngoài Git. Việc bỏ user để phục vụ 2/3 người thay cho 4 không phải lợi ích throughput miễn phí; fairness/latency chưa được kiểm tra.

## Giới hạn và bước tiếp

Thời gian exhaustive gồm đánh giá ứng viên CP01 cộng chọn oracle CP02; greedy đo ở CP02. G1 và artifact I/O tách riêng. Các pha không phải benchmark được kiểm soát hoàn toàn về tải/cache; không suy diễn thời gian quan sát thành cải thiện độc lập.

Full-K hoặc subset không khả thi chỉ là kết quả trong candidate family và miền bất định thiết kế, không chứng minh mọi beamforming đều thất bại. Chưa có xác nhận CSI thực, thống kê độc lập giữa geometry, fairness, throughput, latency hay outage probability. G4 cần khóa phương pháp trước khi dùng nhóm DeepMIMO mới hoặc nguồn 3GPP riêng, kèm cấu hình và bất định theo nhóm. Dữ liệu đã xem vẫn là development.

## Xác minh từ repo root

```bash
python src/version_08_robust_user_scheduling/code/run_cp06.py \
  --run-dir log/version_08/runs/DM_ASU35_SCHED_DEV_20261101 \
  --verify-only
```

Cần NumPy/SciPy; không cần channel NPZ/task cache. Xem [hướng dẫn từng CP](../../../../src/version_08_robust_user_scheduling/docs/RUN_BY_CP_VI.md), [đối chiếu PDF](../../../../src/version_08_robust_user_scheduling/docs/GUIDE_AUDIT_VI.md) và `VALIDATION.json`.
