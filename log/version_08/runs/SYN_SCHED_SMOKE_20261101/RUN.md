# Run SYN_SCHED_SMOKE_20261101

## Provenance và trạng thái

- Code version: `version_08`; source commit đóng gói: `2137c3e46751e817510c2a5fcbb66e8f5b829886`.
- Vai trò dữ liệu: **smoke**; trạng thái **EXPLORATORY_EVALUATION**.
- CP00–CP06 hoàn tất; G1/G2 đã qua; G3 ghi số đo; **G4 chưa được xác minh**.
- Dataset SHA-256: `c52e1551158a6556ad8161db560864244beb6958c7e90adac119a4708f4bd2f9`.
- Engine SHA-256: `163bd7b2fb2b0a1333cf06d8b1f1df9624c2d75b3bf7b864b1fdf26e00b9bba3`.
- q cố định `2.9604143746015965`, sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, Pmax=1 W.
- Codebook alpha=`0,0.001,0.01,0.05,0.1,0.3,1`; 15 tập con không rỗng; 12 geometry.

Synthetic fixture upstream có 24 geometry; run chọn 12 đầu bằng limit=12, shape mỗi geometry `(16,4)`. Đây chỉ là program smoke check, không phải kết quả DeepMIMO/3GPP.

Fixture lưu trong source, SHA-256 được ghi trong CP00 và source manifest.

Run thực thi ngoài Git trước khi nhập repo. Source commit trên là snapshot đóng gói khớp code fingerprints của run, không phải tuyên bố run đã thực thi từ một commit có sẵn. Manifest/provenance gốc giữ nguyên cả đường dẫn dataset/Python ban đầu. Ngày đóng gói: 2026-11-02; ngày trong run ID là định danh đã khóa, không đổi khi sang ngày mới.

## Kiểm tra checkpoint

- CP01: 1,260 dòng tập con–beam. Status counts: `{"COUPLING_RHO_GE_ONE": 112, "FEASIBLE": 1148}`. Đây là số case, không phải số geometry độc lập.
- G1: 1,260 ứng viên, 1,148 scaled LP audits, 1,260 kiểm tra ngân sách và 2,520 engine calls bổ sung. Audit không cộng vào chi phí thuật toán.
- Max relative analytic/LP gap: `3.612936901707724e-15`; max scaled LP violation: `2.0695918704955223e-14`.
- CP02: 36 quyết định, 3 method/geometry; G2 kiểm tra lexicographic objective.
- CP03: 24 cặp, power chỉ so khi cùng số user dương.
- CP04: 3 dòng tổng hợp, mỗi method có 12 geometry.
- CP05: giữ scope upstream; không có independent improvement/certificate/global optimality claim.
- CP06: 11 artifact đã xác minh và code snapshot khớp sau khi sao chép.

## Mức phục vụ và chi phí

| Method | Mean users | Full 4 users | At least 1 | Mean calls | Mean runtime ms | Upstream positive-card match |
|---|---|---|---|---|---|---|
| exhaustive | 3.666667 | 66.667% | 100.00% | 105.00000 | 156.944795 | NA |
| forward | 3.666667 | 66.667% | 100.00% | 70.00000 | 95.678299 | 1.0 |
| backward | 3.666667 | 66.667% | 100.00% | 16.33333 | 15.018979 | 1.0 |

| Số user | Exhaustive geometries | Forward geometries | Backward geometries |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 1 | 0 | 0 | 0 |
| 2 | 0 | 0 | 0 |
| 3 | 4 | 4 | 4 |
| 4 | 8 | 8 | 8 |

## Đối sánh theo geometry

| Greedy | Card equality | Max gap | Power pairs | Mean power ratio | Max power ratio | Ratio mean calls | Ratio mean runtime |
|---|---|---|---|---|---|---|---|---|
| forward | 12/12 | 0 | 12 | 1.000000000 | 1.000000000 | 0.666666667 | 0.609630279 |
| backward | 12/12 | 0 | 12 | 1.000000000 | 1.000000000 | 0.155555556 | 0.095695936 |

Power ratio tính greedy/exhaustive trên cùng geometry và cùng số user dương. Runtime ratio là tỷ số hai thời gian trung bình, không phải trung bình tỷ số từng geometry. Metric CSV upstream `same_cardinality`/`oracle_cardinality_match_fraction` không tính both-zero là positive-card match; cardinality gap vẫn bằng 0 khi cả hai phục vụ 0.

Cả hai greedy khớp exhaustive về cardinality và công suất trên smoke. Kết quả này chỉ xác nhận luồng chương trình trên fixture, không phải kiểm chứng độc lập của phương pháp.

## Giới hạn và bước tiếp

Thời gian exhaustive gồm đánh giá ứng viên CP01 cộng chọn oracle CP02; greedy đo ở CP02. G1 và artifact I/O tách riêng. Các pha không phải benchmark được kiểm soát hoàn toàn về tải/cache; không suy diễn thời gian quan sát thành cải thiện độc lập.

Full-K hoặc subset không khả thi chỉ là kết quả trong candidate family và miền bất định thiết kế, không chứng minh mọi beamforming đều thất bại. Chưa có xác nhận CSI thực, thống kê độc lập giữa geometry, fairness, throughput, latency hay outage probability. G4 cần khóa phương pháp trước khi dùng nhóm DeepMIMO mới hoặc nguồn 3GPP riêng, kèm cấu hình và bất định theo nhóm. Dữ liệu đã xem vẫn là development.

## Xác minh từ repo root

```bash
python src/version_08_robust_user_scheduling/code/run_cp06.py \
  --run-dir log/version_08/runs/SYN_SCHED_SMOKE_20261101 \
  --verify-only
```

Cần NumPy/SciPy; không cần channel NPZ/task cache. Xem [hướng dẫn từng CP](../../../../src/version_08_robust_user_scheduling/docs/RUN_BY_CP_VI.md), [đối chiếu PDF](../../../../src/version_08_robust_user_scheduling/docs/GUIDE_AUDIT_VI.md) và `VALIDATION.json`.
