# Run DM_ASU35_SAFE_DEV_20261102

## Trạng thái và nguồn gốc

- Code version: `version_09`; source commit đóng gói: `e2a3609950581a1d8e25bb5d2f7fe8f77408cfd1`.
- Trạng thái hồ sơ: `ALGORITHM_CHECKS_PASSED_ON_DEVELOPMENT_DATA`; đây là nhãn bổ sung, không sửa CP05 upstream.
- Native `preflight → scan → report` đã hoàn tất; CP00–CP06 đủ, 160 task được kiểm toán ngoài Git.
- Source/test/PDF/TeX/fixture gốc khớp ZIP; không bổ sung code hoặc runner tách CP.
- Run được thực thi ngoài Git trước khi nhập repo. Commit trên ghi snapshot đóng gói khớp hai code fingerprints của CP00, không tuyên bố run đã thực thi từ commit có sẵn.
- Đóng gói ngày 2026-11-02. Không có smoke run mới được công bố; output SMOKE trong ZIP là ví dụ upstream.

## Dữ liệu và cấu hình

DeepMIMO `asu_campus_3p5`, dataset `deepmimo_asu35_v1`: complex64 H shape `(160,16,4)`, 160 nhóm, metadata scenario/xyz. Kênh giữ thang đo tuyệt đối, không chuẩn hóa lại. Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`.

[Lineage dữ liệu](../../../version_06/dataset_provenance/deepmimo_asu35_v1/deepmimo_provenance.json). Chọn 640 UE không lặp và có khoảng cách không đủ để chứng minh độc lập thống kê; cùng scene có thể còn tương quan. Dữ liệu đã được xem ở các version trước nên lượt này là **development**.

- q=2.960414, sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, Pmax=1 W.
- q đúng mặc định PDF version 09; khác giá trị đầy đủ của version 08.
- Alpha: 0, 0.001, 0.01, 0.05, 0.1, 0.3, 1; 15 tập con, 105 ứng viên/geometry; limit=0.
- Mục tiêu: tối đa số user, rồi tối thiểu công suất trong cùng số user; phá hòa bằng alpha và subset.
- Safe pruning SHA-256: `d242114c9b45508592054ab39857ecd089816de375bf466b3dc35b35c2d29e0a`.
- Reference SHA-256: `163bd7b2fb2b0a1333cf06d8b1f1df9624c2d75b3bf7b864b1fdf26e00b9bba3`.
- Signature: `5e97ac6eda78da4e0cbdb811b50ae1ad255069ff7d4be96341fb8bc2c6f66591`.
- Người dùng báo cáo trước run: Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1; phiên đóng gói xác nhận cùng các version này. CP00 gốc không tự ghi môi trường của scan.

## Kiểm toán checkpoint

| File | Nội dung đã xác minh |
|---|---|
| CP00_manifest.json | Signature, tham số, dữ liệu và hai file source khớp |
| CP01_candidate_screening.csv | 3,094 records; 1,728 pruned, 1,366 survivors gọi solve; không trùng candidate trong geometry |
| CP02_geometry_paired.csv | 160 geometry; cùng cardinality/subset/alpha/power, sai khác công suất quan sát bằng 0 |
| CP03_reference_exhaustive.csv | Đủ 16,800 candidate = 160 × 105; oracle tối ưu từ điển khi dựng lại từ CSV |
| CP04_screening_reasons.csv | 6 reason counts khớp CP01; tổng 3,094 gồm cả SURVIVOR |
| CP05_decision.json | all_oracle_matched=true; mean calls/runtime tính lại khớp CSV |
| CP06_SHA256.csv | Sáu hash bao phủ CP00–CP05 đều khớp; chính CP06 được bảo toàn khi sao chép |

Không có ứng viên mang cờ pruned nhưng reference FEASIBLE. Reference có 14,222 FEASIBLE, 1,083 POWER_BUDGET, 1,484 COUPLING_RHO_GE_ONE và 11 ZERO_ROBUST_DIRECT_GAIN. Đây là số candidate, không phải số geometry độc lập.

## Mức phục vụ và chi phí

| Method | Mean users | Mean solve calls | Mean runtime ms |
|---|---:|---:|---:|
| exhaustive | 3.575 | 105 | 132.712189805 |
| safe pruning | 3.575 | 8.5375 | 15.954564243 |

Cả hai có 97/160 geometry phục vụ đủ 4 user (60.625%), 58 geometry phục vụ 3, 5 geometry phục vụ 2. Toàn bộ 160 geometry khớp nghiệm cả số user, subset, alpha và công suất; max relative power gap=0.

| Nhóm công việc | Tổng candidate |
|---|---:|
| Gọi solve đầy đủ sau sàng lọc | 1,366 |
| Loại bằng điều kiện sàng lọc | 1,728 |
| Bỏ tập ít user hơn theo mục tiêu từ điển | 13,706 |
| Tổng đối chứng | 16,800 |

Số lượt solve giảm **91.8690476%**. Không diễn giải toàn bộ candidate bỏ qua là không khả thi: 13,706 candidate kích thước nhỏ hơn không thể thắng về số user, nên không cần xét sau khi tìm được nghiệm ở kích thước lớn hơn. Số lời gọi solve cũng không đồng nghĩa số LP.

| Screening reason | Count |
|---|---:|
| NEUMANN_LOWER_BOUND | 840 |
| NOISE_LOWER_BOUND | 593 |
| NORM_NOISE_LOWER_BOUND | 245 |
| TWO_CYCLE_COUPLING | 40 |
| ZERO_ROBUST_GAIN | 10 |
| SURVIVOR | 1,366 |

Mean runtime quan sát giảm **87.9780717%**, tỷ số hai thời gian trung bình **8.318133**. Pruning nhanh hơn oracle trên 160/160 geometry trong lượt này. Pruning runtime gồm screening và solve; oracle runtime gồm exhaustive và chọn oracle. Tổng hai timer tương ứng khoảng 2.55273 s và 21.23395 s. Stage scan vẫn chạy cả hai luồng để kiểm chứng; các số trên không phải giảm thời gian toàn bộ scan so với chỉ chạy oracle, và không bao gồm toàn bộ artifact I/O.

## Giới hạn kết luận

Exhaustive tối ưu trong 15 tập con và ZF/RZF codebook đã định, không phải mọi beam phức. Pruning dùng các điều kiện đủ trong mô hình robust tuyến tính hiện có. Hai luồng lựa chọn được đối chiếu sau khi chạy; cùng dùng các hàm mô hình từ reference module. Không dùng bảng reference để chọn nghiệm pruning.

Đây là phép đo một lượt trên dữ liệu development dùng lại; chưa có benchmark lặp có kiểm soát, khoảng tin cậy trên nhóm độc lập, đánh giá CSI estimator thực tế, global beamforming optimum hoặc chứng nhận outage/fairness/throughput/latency. Không so trực tiếp runtime version 08 và 09 như một benchmark có kiểm soát.

## Tái lập và xác minh

[Source và lệnh chạy gốc](../../../../src/version_09_robust_safe_pruning/README.md), [hướng dẫn PDF gốc](../../../../src/version_09_robust_safe_pruning/docs/GUIDE_IEEE_VI.pdf). Real dataset và task cache không nhập Git; tái chạy dùng run ID mới và cùng tham số.

Từ repo root, dùng Python chuẩn để kiểm tra sáu hash gốc và bảng artifact bổ sung, không cần NumPy/SciPy hoặc channel dataset:

```bash
python - <<'PY'
from pathlib import Path
import csv
import hashlib

run = Path("log/version_09/runs/DM_ASU35_SAFE_DEV_20261102")
for table in ("CP06_SHA256.csv", "ARTIFACT_SHA256.csv"):
    with (run / table).open(newline="") as file:
        entries = list(csv.DictReader(file))
    for entry in entries:
        actual = hashlib.sha256((run / entry["file"]).read_bytes()).hexdigest()
        assert actual == entry["sha256"], entry["file"]
    print(table, "PASS", len(entries), "files")
PY
```

`ARTIFACT_SHA256.csv` bao phủ bảy CP gốc cùng RUN/REPRODUCIBILITY/VALIDATION và không băm chính nó. Manifest gốc vẫn giữ đường dẫn dữ liệu tuyệt đối ban đầu để bảo toàn fingerprint.
