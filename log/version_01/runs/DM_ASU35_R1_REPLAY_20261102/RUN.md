# Run DM_ASU35_R1_REPLAY_20261102

## Nguồn và cấu hình

- Code version: `version_01`; source commit: `c74dec97e6068d1ba6b642c1a365b7ef5d2d417d`.
- Gói gốc: `Fuzzy_MUMIMO_Research_R1_fixed.zip`, SHA-256 `7e1e3eabca0da0eea93983ad9831d56b2834067ece2d47c587568d5ca0ee8b5c`.
- Native stages: `preflight → develop → freeze → test → report`; không có wrapper bổ sung.
- Dataset: DeepMIMO `asu_campus_3p5`, `(160,16,4)`, 160 group; SHA-256 `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`.
- Split seed 20261019: train/validation/test = 96/32/32. M=16, K=4, sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, Pmax=1 W, eps=0.05, 300 MC samples/feasible geometry, 2,000 bootstrap replicates.
- Môi trường: Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1.

Dataset đã được xem ở các version sau; replay này là tái dựng lịch sử, không phải test độc lập mới. Run thực thi ngoài Git trước khi source được nhập; code fingerprint trong CP00 khớp source commit trên.

## Kiểm tra và kết quả

9/9 test gốc PASS. 32 checkpoint test hoàn chỉnh; CP03 có 128 dòng = 32 geometry × 4 phương pháp. Summary được tính lại từ CP03 và khớp CP04.

| Method | Feasible | Conditional outage | Effective failure | Mean feasible power W |
|---|---:|---:|---:|---:|
| gaussian | 15/32 | 0.0222% | 53.1354% | 0.269666 |
| fixed | 15/32 | 3.8000% | 54.9063% | 0.253993 |
| threshold | 15/32 | 2.2667% | 54.1875% | 0.255461 |
| sugeno | 15/32 | 16.8000% | 61.0000% | 0.249227 |

Tất cả phương pháp có 17/32 geometry không khả thi theo fixed-RZF robust model. Conditional outage chỉ tính trên 15 geometry khả thi; effective failure tính geometry không khả thi là 1. Vì vậy không được dùng mức công suất thấp hơn của Sugeno để tuyên bố tốt hơn: Sugeno có reliability kém nhất trong replay.

CP06 so công suất trên 15 geometry khả thi chung: fixed −0.231 dB, threshold −0.209 dB, Sugeno −0.306 dB so với Gaussian. Lợi ích nhỏ này đi cùng effective failure/outage cao hơn và không thỏa reliability target 5%.

## Phạm vi

Kết quả là pilot với sai số CSI mô phỏng quanh estimated channel, không phải residual của bộ ước lượng thật. Không có xác nhận 3GPP độc lập, outage certificate hay power advantage có kiểm soát. Xem [source gốc](../../../../src/version_01_fuzzy_mumimo_r1/README.md).
