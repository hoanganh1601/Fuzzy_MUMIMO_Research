# Version 06 working plan

## Objective

Hiệu chuẩn CSI uncertainty margin trên spatially grouped DeepMIMO với metadata, fingerprint và resumable checkpoints.

## Prespecified sequence

```text
preflight -> develop -> calibrate -> freeze -> test -> transfer -> report
```

Không chọn lại margin sau khi xem calibration/test. Nếu CP05 fail, run dừng certificate và mọi đánh giá tiếp theo chỉ mang tính mô tả.

## Current result

`DM_ASU35_V1_20261028` đã CP05 FAIL. Cải tiến scheduler/beamforming hoặc link-budget phải dùng code version, run ID và confirmatory groups mới.
