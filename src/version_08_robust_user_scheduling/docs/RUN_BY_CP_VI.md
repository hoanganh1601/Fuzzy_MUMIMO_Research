# Chạy riêng từng CP của version 08

Từ `src/version_08_robust_user_scheduling`, kích hoạt môi trường và cài `code/requirements.txt`. Real datasets lưu ngoài Git dưới `/media/icnlab/Data/hoanganh/datasets`.

Mỗi lượt chạy/dataset có bộ CP00–CP06 riêng. Hai lượt đã lưu là smoke 12 geometry và DeepMIMO development 160 geometry, cùng dùng source version 08. Không đổi code, dữ liệu hoặc tham số giữa một run; thay đổi cần run ID mới.

## CP00: khóa cấu hình

Ví dụ tạo smoke mới:

```bash
python code/admission_beam.py --stage preflight \
  --dataset data/smoke.npz --run-id SYN_SCHED_REPLAY_R01 \
  --q 2.9604143746015965 --sigma-rel 0.04 --sinr-db 6 \
  --noise 2e-13 --pmax 1 --alpha-list 0,0.001,0.01,0.05,0.1,0.3,1 \
  --limit 12
```

Kiểm tra `PASS 12 geometries, 12 groups` và manifest trước CP01.

Để chạy DeepMIMO development mới, dùng CP00 riêng:

```bash
python code/admission_beam.py --stage preflight \
  --dataset /media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz \
  --run-id DM_ASU35_SCHED_DEV_REPLAY_R01 \
  --q 2.9604143746015965 --sigma-rel 0.04 --sinr-db 6 \
  --noise 2e-13 --pmax 1 --alpha-list 0,0.001,0.01,0.05,0.1,0.3,1 \
  --limit 0
```

`--limit 0` dùng mọi geometry. Với dataset hiện có, kỳ vọng 160 geometry/160 nhóm. Kiểm tra checksum, shape, metadata và provenance trước khi chạy.

## CP01 đến CP06: dừng sau mỗi CP để đọc kết quả

Ví dụ tiếp tục smoke mới, chạy từng lệnh dưới đây. Với DeepMIMO, thay run directory bằng `outputs/DM_ASU35_SCHED_DEV_REPLAY_R01`.

```bash
python code/run_cp01.py --run-dir outputs/SYN_SCHED_REPLAY_R01
```

CP01 chỉ tính 15 tập con × các beam và ghi `CP01_all_subset_beam.csv`. Task có `cp01_complete=true`, `complete=false`; oracle/greedy chưa chạy. Lệnh có thể tiếp tục từ candidate checkpoint hợp lệ khi bị gián đoạn.

```bash
python code/run_cp02.py --run-dir outputs/SYN_SCHED_REPLAY_R01
```

CP02 xác minh CP01, kiểm tra G1 độc lập trước khi gọi oracle và hai greedy. G1 tái dựng F/u, kiểm tra unit-norm beam, direct gain, rho, nghiệm giải tích, scaled LP/residual và tính đơn điệu theo ngân sách. LP audit bao gồm cả case ổn định nhưng vượt ngân sách gốc. Các ngân sách dưới/trên P_req chỉ phục vụ kiểm tra toán học, không dùng tune chính sách. G1 audit được ghi riêng, không cộng vào chi phí thuật toán. CP02 đánh dấu task đầy đủ và xuất 3 quyết định/geometry.

```bash
python code/run_cp03.py --run-dir outputs/SYN_SCHED_REPLAY_R01
```

CP03 xuất 2 cặp/geometry: cardinality gap, công suất khi bằng số user dương và số lời gọi solver. Khi cả hai phục vụ 0 người dùng, gap=0 nhưng upstream `same_cardinality=0` và tỷ số công suất để trống. `CARD_MATCH` trên Terminal dùng gap=0; số cặp công suất được ghi riêng.

```bash
python code/run_cp04.py --run-dir outputs/SYN_SCHED_REPLAY_R01
```

CP04 tổng hợp số user phục vụ, full-service fraction, ít nhất một user, số lời gọi và runtime. Giữ nguyên schema upstream; cột `oracle_cardinality_match_fraction` dùng cờ cùng cardinality dương, do đó không tính cả hai cùng 0 là match. Ghi nhận này quan trọng nếu một dataset có geometry không phục vụ được ai.

```bash
python code/run_cp05.py --run-dir outputs/SYN_SCHED_REPLAY_R01
```

CP05 giữ nguyên scope JSON upstream, ghi thêm bằng chứng vào provenance. Trạng thái `EXPLORATORY_EVALUATION`, G4 chưa được xác minh; PASS của checkpoint không phải certificate.

```bash
python code/run_cp06.py --run-dir outputs/SYN_SCHED_REPLAY_R01
```

CP06 kiểm tra chuỗi và băm 6 file CP00–CP05 cùng 5 sidecar provenance. Receipt CP06 ghi hash bảng checksum và snapshot mọi code file. Console log không nằm trong bộ 11 file được niêm phong.

Lệnh `scan/report/all` trong PDF là tuyến upstream gộp nhiều CP. Khi chọn workflow tách CP, tiếp tục bằng các runner trên: task CP01 còn chưa có quyết định nên không trộn với `--stage scan/report/all` trong cùng run.

## Runtime và nohup

Smoke dùng lệnh thường cho mọi CP. Run 160 geometry dùng lệnh thường cho CP01 và CP03–CP06. CP02 có G1 audit bổ sung và scheduling, nên đã chạy nền bằng nohup:

```bash
nohup python -u code/run_cp02.py \
  --run-dir outputs/DM_ASU35_SCHED_DEV_REPLAY_R01 \
  > outputs/DM_ASU35_SCHED_DEV_REPLAY_R01/CP02_console.log 2>&1 &
```

```bash
tail -f outputs/DM_ASU35_SCHED_DEV_REPLAY_R01/CP02_console.log
```

Đợi PASS hoặc xem lỗi trước bước sau. Ctrl+C khi đang tail chỉ dừng theo dõi log. Chỉ có một tiến trình ghi cùng run directory tại một thời điểm.

Exhaustive runtime gồm thời gian đánh giá ứng viên ở CP01 và chọn oracle ở CP02; greedy runtime đo ở CP02. Không cộng G1 audit hay artifact I/O. Đo ở hai CP khác nhau và không kiểm soát đầy đủ tải/cache, nên runtime chỉ là quan sát trên run, không phải benchmark độc lập được kiểm soát.

## Dữ liệu và giới hạn

Dataset DeepMIMO hiện có đủ cho lượt development và đã khớp checksum/selection provenance. Mọi geometry từng được xem ở các vòng trước là development. G4 cần phương pháp được khóa trước khi dùng các nhóm mới chưa quan sát hoặc nguồn 3GPP riêng, kèm cấu hình và báo cáo bất định theo nhóm. Lượt hiện có không xác minh fairness, throughput, latency hoặc outage xác suất.
