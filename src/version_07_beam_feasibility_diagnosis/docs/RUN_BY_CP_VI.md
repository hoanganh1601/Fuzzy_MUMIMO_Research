# Chạy lần lượt CP00–CP06

Từ `src/version_07_beam_feasibility_diagnosis`, kích hoạt `.venv` và cài `code/requirements.txt`. Real data được lưu dưới `/media/icnlab/Data/hoanganh/datasets`. Mọi run mới phải có run ID mới; không đổi manifest hay source để tiếp tục một run đã khóa.

## CP00: khóa dữ liệu và tham số

Ví dụ tạo run mới trên dataset hiện có, chỉ với mục đích phân tích mô tả:

```bash
python code/beam_feasibility.py \
  --stage preflight \
  --dataset /media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz \
  --run-id DM_ASU35_BEAM_DIAG_REPLAY_R01 \
  --q 2.9604143746015965 \
  --sigma-rel 0.04 --sinr-db 6 --noise 2e-13 --pmax 1 \
  --alpha-list 0,0.001,0.01,0.05,0.1,0.3,1 \
  --budget-list 0.3,0.6,1,2,5
```

Kiểm tra `PREFLIGHT PASS` và `outputs/<run-id>/CP00_manifest.json`. Với synthetic, thay đường dẫn bằng `data/synthetic_diagnostic.npz` và dùng run ID riêng.

## CP01–CP06: mỗi lệnh chỉ xuất CP tương ứng

Chạy **từng lệnh**, đọc kết quả trước khi sang lệnh tiếp theo:

```bash
python code/run_cp01.py --run-dir outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01
```

```bash
python code/run_cp02.py --run-dir outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01
```

```bash
python code/run_cp03.py --run-dir outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01
```

```bash
python code/run_cp04.py --run-dir outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01
```

```bash
python code/run_cp05.py --run-dir outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01
```

```bash
python code/run_cp06.py --run-dir outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01
```

- CP01 gọi `--stage scan` của source gốc và xuất bảng geometry–beam–budget. Chạy lại cùng lệnh sẽ tái sử dụng task hợp lệ.
- CP02 tổng hợp theo beam/ngân sách.
- CP03 đối sánh cùng geometry/ngân sách; tỷ số công suất chỉ trên tập cùng khả thi.
- CP04 chẩn đoán geometry tại `budget_factor=1`; `best_alpha` là kết quả mô tả trên lưới, không phải luật chọn beam đã xác nhận.
- CP05 giữ scope JSON gốc, thêm bằng chứng vào sidecar provenance. PASS là thành công của checkpoint; trạng thái khoa học là `DIAGNOSTIC_ONLY`.
- CP06 băm 6 file CP00–CP05 và 5 sidecar; provenance CP06 ghi hash bảng checksum và toàn bộ code. Chế độ `--verify-only` chỉ xác minh bộ đã lưu, không tái chạy solver hoặc truy cập channel data.

Các runner CP02–CP06 yêu cầu chuỗi trước đó hợp lệ, source/dataset đúng checksum, môi trường khớp CP01. Khi chuyển máy hoặc tạo môi trường mới, dùng run ID mới để tính lại; dùng `--verify-only` để đọc bộ kết quả lịch sử.

## Khi nào dùng nohup

Với dataset 160 geometry, dùng lệnh thường cho mọi CP. Smoke 36 geometry ghi nhận khoảng 1,2 giây tổng thời gian case; con số này không gồm mọi chi phí khởi động/đọc ghi và không bảo đảm thời gian trên máy khác.

Với scan lớn dự kiến kéo dài nhiều phút/giờ, chỉ CP01 cần chuyển sang chạy nền, sau khi CP00 đã đạt:

```bash
nohup python -u code/run_cp01.py \
  --run-dir outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01 \
  > outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01/CP01_console.log 2>&1 &
```

```bash
tail -f outputs/DM_ASU35_BEAM_DIAG_REPLAY_R01/CP01_console.log
```

Đợi tiến trình kết thúc và đọc dòng PASS/lỗi trước CP02. `Ctrl+C` khi đang `tail -f` chỉ dừng theo dõi log. Không chạy đồng thời hai tiến trình ghi cùng run ID.

## Giới hạn được kế thừa từ engine gốc

Đây là bài toán power control bảo thủ cho beam cố định. Trạng thái coupling hoặc zero gain không chứng minh mọi beamforming khả dĩ đều thất bại. Source gốc trả `POWER_BUDGET` ngay sau nghiệm giải tích vượt ngân sách; LP chỉ được gọi cho case vượt qua kiểm tra ngân sách. Phần dư LP vì vậy không có cho mọi dòng CP01.

Không chọn alpha từ kết quả test rồi tuyên bố đã kiểm chứng cải thiện trên cùng dữ liệu. Holdout đã xem ở version 06 không trở thành holdout mới khi tạo run ID khác.
