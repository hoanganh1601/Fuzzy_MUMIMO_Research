# Version 09: robust SINR safe pruning

Version 09 loại sớm ứng viên tập user–beam bằng các điều kiện đủ và dừng xét các tập ít user hơn sau khi tìm được nghiệm ở số user lớn hơn. Mục tiêu giữ nguyên: tối đa số user, rồi tối thiểu công suất trong cùng số user. Exhaustive xét đủ 15 tập con × 7 beam làm đối chứng.

Source nhập nguyên byte từ `Robust_Safe_Pruning_Code_Guide_20261102.zip`. Hai file `code/safe_pruning.py` và `code/reference_model.py` cùng bộ test gốc được giữ nguyên. Safe pruning chọn nghiệm trước, rồi reference exhaustive được tính riêng để đối chiếu; các hàm mô hình `get_beam`/`solve` được dùng chung từ reference module. Không bổ sung runner riêng từng CP.

[PDF hướng dẫn gốc](docs/GUIDE_IEEE_VI.pdf), [TeX gốc](docs/GUIDE_IEEE_VI.tex), [README upstream](README_UPSTREAM.md), [thông tin nhập gói](UPSTREAM_IMPORT.json). `UPSTREAM_FILE_SHA256.csv` giữ nguyên bảng hash gốc; mục `README.md` trong bảng này ứng với `README_UPSTREAM.md`. `SOURCE_SHA256.csv` bao phủ snapshot source đã đóng gói, trừ chính bảng đó.

## Dữ liệu và phạm vi

Run đã lưu: [`DM_ASU35_SAFE_DEV_20261102`](../../log/version_09/runs/DM_ASU35_SAFE_DEV_20261102/RUN.md), DeepMIMO `asu_campus_3p5`, shape `(160,16,4)`, 160 nhóm. Dữ liệu dùng lại từ các version trước nên là **development**. Tách hai luồng chọn nghiệm để đối chiếu không tạo ra một tập kiểm chứng dữ liệu độc lập.

Channel NPZ/scenario/selection cache nằm ngoài Git dưới `/media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/`. Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`. Giữ thang đo kênh tuyệt đối, không chuẩn hóa lại. Fixture `data/smoke.npz` là synthetic từ ZIP, chỉ phục vụ kiểm tra chương trình; không có lượt smoke mới được lưu như kết quả người dùng.

q=`2.960414` đúng mặc định PDF version 09; không dùng giá trị đầy đủ `2.9604143746015965` của version 08. sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, Pmax=1 W; alpha=`0,0.001,0.01,0.05,0.1,0.3,1`. Thay dữ liệu/source/tham số phải dùng run ID mới.

## Chạy theo ba stage gốc

Từ thư mục version này, dùng Python >=3.10 và cài `code/requirements.txt`. Bộ kiểm thử có sẵn trong ZIP:

```bash
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
```

Ví dụ tái chạy development với run ID mới; chạy xong mỗi stage rồi mới sang stage tiếp theo. Dataset giữ ở đường dẫn ngoài repo:

```bash
python code/safe_pruning.py --stage preflight \
  --dataset /media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz \
  --run-id DM_ASU35_SAFE_DEV_REPLAY_R01 --limit 0 \
  --q 2.960414 --sigma-rel 0.04 --sinr-db 6 --noise 2e-13 --pmax 1 \
  --alpha-list 0,0.001,0.01,0.05,0.1,0.3,1
```

`preflight` tạo CP00. `--limit 0` sử dụng toàn bộ 160 geometry. Tiếp theo:

```bash
python -u code/safe_pruning.py --stage scan \
  --dataset /media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz \
  --run-id DM_ASU35_SAFE_DEV_REPLAY_R01 --limit 0 \
  --q 2.960414 --sigma-rel 0.04 --sinr-db 6 --noise 2e-13 --pmax 1 \
  --alpha-list 0,0.001,0.01,0.05,0.1,0.3,1
```

`scan` chạy pruning và exhaustive, đối chiếu nghiệm/ứng viên bị loại rồi lưu checkpoint từng geometry. Cần cùng cardinality/subset/alpha và sai khác công suất tương đối <=1e-7; trường hợp loại nhầm hoặc nghiệm khác sẽ gây `AssertionError`. Có thể chạy lại cùng lệnh để tiếp tục checkpoint hợp lệ. Tiến độ in mỗi 25 geometry; đợi chương trình kết thúc sau dòng 150/160. Run đã báo cáo dùng lệnh thường.

```bash
python code/safe_pruning.py --stage report \
  --dataset /media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz \
  --run-id DM_ASU35_SAFE_DEV_REPLAY_R01 --limit 0 \
  --q 2.960414 --sigma-rel 0.04 --sinr-db 6 --noise 2e-13 --pmax 1 \
  --alpha-list 0,0.001,0.01,0.05,0.1,0.3,1
```

`report` đọc checkpoint đã hoàn chỉnh và xuất CP01–CP06 cùng lúc. Chạy report tái tạo hash dựa trên file CP hiện có; dùng thư mục run sạch và giữ console log ngoài các tên `CP0*`. Task cache ở `outputs/` không được đưa vào Git.

## Kết quả và giới hạn

Trên 160 geometry development: 160/160 khớp hoàn toàn nghiệm exhaustive, không phát hiện loại nhầm; 97 geometry phục vụ 4 user, 58 phục vụ 3, 5 phục vụ 2. Số gọi `solve` giảm từ 16,800 xuống 1,366 (91.87%). Trong đó 1,728 ứng viên được loại bằng điều kiện sàng lọc, 13,706 ứng viên kích thước nhỏ hơn được bỏ qua theo mục tiêu từ điển.

Mean runtime oracle=132.712190 ms, pruning=15.954564 ms; giảm quan sát 87.98%, tỷ số hai thời gian trung bình=8.31813. Thời gian pruning bao gồm sàng lọc; stage scan vẫn thực thi thêm oracle để kiểm tra, nên đây là so sánh hai luồng, không phải thời gian toàn bộ scan so với việc chỉ chạy oracle. Số lượt `solve` không đồng nghĩa số LP. Không so trực tiếp runtime với version 08 vì khác lượt chạy/cách tổ chức phép đo.

Trạng thái đóng gói: `ALGORITHM_CHECKS_PASSED_ON_DEVELOPMENT_DATA`. Đây là nhãn trong hồ sơ bổ sung; CP05 gốc được giữ nguyên và không có trường status này. Chưa có kiểm chứng dữ liệu độc lập, benchmark lặp có kiểm soát, global beamforming optimum, outage probability hoặc fairness/throughput/latency certificate. Nghiệm exhaustive chỉ tối ưu trong candidate family và mô hình robust tuyến tính đang dùng.

Các CP00–CP06 lưu trong `log/` giữ nguyên byte. Xem [run card](../../log/version_09/runs/DM_ASU35_SAFE_DEV_20261102/RUN.md) để xác minh checksum bằng Python chuẩn mà không cần `rg`, dữ liệu kênh hoặc task cache.
