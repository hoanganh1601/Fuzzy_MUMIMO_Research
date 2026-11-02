# Run DM_ASU35_E1R_E3R_REPLAY_20261102

## Nguồn và cấu hình

- Code version: `version_02`; source commit: `4217c9208e8ca4620045f2a65cf403b815178a6f`.
- Gói gốc: `Fuzzy_MUMIMO_E1R_E3R_R1_fixed.zip`, SHA-256 `4ee68a8c66bce982dc14eea946796dffa76ef09a79a561992943ecc03229348b`.
- Native stages: `preflight → develop → calibrate → freeze → test → report`.
- Dataset: DeepMIMO `asu_campus_3p5`, `(160,16,4)`, 160 group; SHA-256 `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`.
- Split seed 20261021: development/validation/calibration/test = 64/32/32/32. M=16, K=4, sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, Pmax=1 W, eps=0.05, 300 MC samples, 3,000 bootstrap replicates.
- Môi trường: Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1.

Dataset là dữ liệu dùng lại; đây là historical replay. Run thực thi ngoài Git trước khi đóng gói, và hai code fingerprint trong CP00 khớp source commit.

## Calibration và fail-closed

9/9 test engine và 7/7 test E1R–E3R PASS. Không phương pháp nào qua calibration gate vì effective failure 38.32–40.63%, vượt eps=5%. Do đó fuzzy_safe được khóa về Gaussian-equivalent fallback q=2.401732915. Đây là hành vi fail-closed được thiết kế trong mã.

## Kết quả test

32 checkpoint test được CP08 xác minh SHA-256; CP04 có 160 dòng = 32 geometry × 5 phương pháp. CP05 được dựng lại từ CP04 và khớp.

| Method | Feasible | Conditional outage | Effective failure | Mean feasible power W |
|---|---:|---:|---:|---:|
| gaussian | 13/32 | 0.0000% | 59.3750% | 0.395674 |
| fixed | 13/32 | 2.6667% | 60.4583% | 0.375912 |
| threshold | 13/32 | 0.0000% | 59.3750% | 0.395674 |
| fuzzy_raw | 13/32 | 2.1795% | 60.2604% | 0.376478 |
| fuzzy_safe | 13/32 | 0.0000% | 59.3750% | 0.395674 |

Fuzzy_safe bằng Gaussian về reliability và công suất do fallback; floor active trên 15.38% geometry khả thi. So với fixed trên 13 geometry khả thi chung, fuzzy_safe dùng tỷ số công suất trung bình 1.05135, tức cao hơn khoảng 5.14%. Không có power advantage.

Quyết định CP07: **`STOP_no_demonstrated_fuzzy_advantage`**. Các cờ `eligible`, `baselines_reliable`, `power_and_risk_better`, `power_and_outage_better` đều false.

## Phạm vi

Bootstrap chỉ mang tính thăm dò; dữ liệu dùng lại không tạo independent validation. Không có formal outage guarantee, 3GPP transfer hoặc chứng minh fairness/throughput. Xem [source gốc](../../../../src/version_02_e1r_e3r_r1/README.md).
