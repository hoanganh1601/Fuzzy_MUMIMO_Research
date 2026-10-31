# Run DM_ASU35_BEAM_DIAG_20261031

## Trạng thái và provenance

- Code version: `version_07`.
- Source commit: `6439c5e07bb090c22eb528673c26bd211227ac68`.
- Source: `src/version_07_beam_feasibility_diagnosis`.
- Kết quả: **CP00–CP06 hoàn tất; DIAGNOSTIC_ONLY**.
- Dataset: `deepmimo_asu35_v1`, scenario `asu_campus_3p5`, shape `(160,16,4)`, 160 nhóm.
- Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`.
- Engine SHA-256: `36a0ee286a5650c1adedd50c36bdd6fab5a6b46fc7911f2636310c2cfa071726`.
- q cố định: `2.9604143746015965`; sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, baseline Pmax=1 W.
- Alpha: `0,0.001,0.01,0.05,0.1,0.3,1`; budget factors: `0.3,0.6,1,2,5`.

Run được thực thi ngoài Git trước khi nhập source. Source commit trên là snapshot đóng gói; code khớp từng byte với fingerprints của run, không phải tuyên bố run đã thực thi từ commit có sẵn vào thời điểm đó. Manifest và provenance gốc được giữ nguyên, kể cả các đường dẫn tuyệt đối của môi trường ban đầu.

Dataset được tái sử dụng từ version 06; xem [lineage](../../../version_06/dataset_provenance/deepmimo_asu35_v1/deepmimo_provenance.json). Kết quả không tạo holdout độc lập và không thay đổi kết luận certificate failure trước đó.

## Kết quả checkpoint

- CP01: 5.600 dòng. FEASIBLE=2.628; COUPLING_RHO_GE_ONE=1.950; POWER_BUDGET=997; ZERO_ROBUST_DIRECT_GAIN=25. Đây là số case qua cả lưới, không phải số geometry độc lập.
- CP02: 35 dòng, 160 geometry mỗi dòng, `n_other=0`.
- CP03: 4.800 cặp đối sánh cùng geometry/ngân sách.
- CP04 tại 1 W: 97 geometry có ít nhất một candidate beam khả thi; 63 thất bại ở mọi candidate. Trong 63: 44 có ít nhất một POWER_BUDGET case; 19 chỉ coupling/zero gain, gồm 14 coupling ở mọi beam.
- CP05: `DIAGNOSTIC_ONLY`; không có statistical certificate/global optimality/post-test selection claim.
- CP06: 11 artifact khớp checksum; snapshot code khớp sau khi nhập vào repo.

## Theo beam tại 1 W

| Beam | Khả thi/N | Tỷ lệ | Coupling | Zero gain | Budget |
|---|---|---|---|---|---|
| ZF | 96/160 | 60.00% | 14 | 5 | 45 |
| RZF_0.001 | 97/160 | 60.62% | 21 | 0 | 42 |
| RZF_0.01 | 92/160 | 57.50% | 34 | 0 | 34 |
| RZF_0.05 | 81/160 | 50.62% | 57 | 0 | 22 |
| RZF_0.1 | 68/160 | 42.50% | 70 | 0 | 22 |
| RZF_0.3 | 53/160 | 33.12% | 92 | 0 | 15 |
| RZF_1 | 48/160 | 30.00% | 102 | 0 | 10 |

## Đối sánh với ZF tại 1 W

| RZF alpha | Both | ZF only | RZF only | Neither | Mean RZF/ZF trên Both |
|---|---|---|---|---|---|
| 0.001 | 96 | 0 | 1 | 63 | 0.993857 |
| 0.01 | 91 | 5 | 1 | 63 | 0.991111 |
| 0.05 | 81 | 15 | 0 | 64 | 1.093924 |
| 0.1 | 68 | 28 | 0 | 64 | 1.091445 |
| 0.3 | 53 | 43 | 0 | 64 | 1.168505 |
| 1 | 48 | 48 | 0 | 64 | 1.295214 |

RZF_0.001 giữ cả 96 geometry khả thi của ZF và thêm 1 geometry. Mean ratio khoảng 0.993857 trên 96 geometry chung, tương ứng giảm khoảng 0,61%. Mỗi alpha có tập Both khác nhau; không coi các mean này là đối sánh trên cùng tập giữa mọi alpha. Đây là kết quả mô tả; không xác nhận một alpha được chọn sau test.

## Độ nhạy ngân sách trong lưới đã khóa

| Pmax (W) | ZF khả thi | RZF_0.001 khả thi | Có ít nhất một candidate khả thi |
|---|---|---|---|
| 0.3 | 54 | 55 | 55 |
| 0.6 | 76 | 76 | 76 |
| 1 | 96 | 97 | 97 |
| 2 | 118 | 119 | 120 |
| 5 | 135 | 135 | 135 |

Cột cuối là hợp của các candidate trên từng geometry, không phải hiệu năng của một luật beam cố định đã được xác nhận.

## Kiểm chứng và giới hạn

CP01–CP05 khớp từng byte khi source gốc chạy `--stage report` trên bản sao task của run. Sáu checksum gốc trong CP06 khớp; năm checksum thêm bao phủ các sidecar. Bốn test workflow synthetic đã qua; xem `VALIDATION.json` và [đối chiếu PDF](../../../../src/version_07_beam_feasibility_diagnosis/docs/GUIDE_AUDIT_VI.md).

Source gốc chỉ chạy LP sau khi nghiệm giải tích vượt qua kiểm tra ngân sách; dòng POWER_BUDGET không có kiểm tra LP. Không có numerical/solver status được ghi trong run này, nhưng điều đó không xác nhận CSI thực tế, đơn vị vật lý hoặc sự độc lập của geometry.

Hướng tiếp: kiểm tra thang đo kênh/nhiễu và budget sensitivity cho 44 geometry có budget case; xem scheduling/grouping/beam space cho 19 geometry chỉ coupling/zero gain. Luật mới cần được khóa trên development và kiểm tra trên dữ liệu độc lập.

## Xác minh từ repo root

```bash
python src/version_07_beam_feasibility_diagnosis/code/run_cp06.py \
  --run-dir log/version_07/runs/DM_ASU35_BEAM_DIAG_20261031 \
  --verify-only
```

Cần NumPy/SciPy; không cần real dataset hoặc task caches. Không commit NPZ thật, virtual environment hoặc `tasks/`.
