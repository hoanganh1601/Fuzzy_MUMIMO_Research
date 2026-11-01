# Version 08: robust user scheduling and beam selection

Version này kiểm tra chọn tập người dùng kết hợp beam ZF/RZF khi giữ cố định CSI margin. Với K=4, exhaustive reference duyệt 15 tập con không rỗng × 7 beam. Hai baseline là forward admission và backward deletion. Mục tiêu theo thứ tự: tối đa số người dùng phục vụ, sau đó tối thiểu công suất trong cùng số người dùng.

## Source và hướng dẫn

- Nhập từ `Robust_User_Scheduling_Beam_Code_Guide_20261101.zip`.
- `code/admission_beam.py`, `code/make_smoke.py`, requirements và PDF/TeX giữ nguyên byte từ ZIP.
- `README_UPSTREAM.md`, `UPSTREAM_FILE_SHA256.csv` giữ tài liệu/checksum upstream; manifest upstream có tham chiếu smoke outputs không được nhập vào source này.
- `UPSTREAM_IMPORT.json` ghi fingerprint ZIP, `SOURCE_SHA256.csv` ghi snapshot source đã đóng gói.
- Các runner `run_cp01.py`–`run_cp06.py` và ba helper bổ sung chạy từng CP, G1 audit và xác minh provenance. Chúng gọi hàm toán học gốc; không retune q hoặc sửa engine.

Xem [hướng dẫn từng CP](docs/RUN_BY_CP_VI.md) và [đối chiếu PDF](docs/GUIDE_AUDIT_VI.md).

## Môi trường và dữ liệu

Từ thư mục version này:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r code/requirements.txt
```

Hai run đã ghi nhận dùng Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1. Requirements upstream là các cận dưới, không phải lockfile môi trường.

Input cần `H` phức hữu hạn `(N,M,4)`, M>=4, và `groups` vector N phần tử; metadata `scenario`, `xyz` nếu có. Fixture `data/smoke.npz` có **24** geometry; smoke run chọn 12 geometry bằng `--limit 12`. Synthetic chỉ kiểm tra chương trình.

Real dataset nằm ngoài Git:

```text
/media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz
```

Dataset có `(160,16,4)`, 160 nhóm, metadata `scenario/xyz`, checksum khớp [lineage version 06](../../log/version_06/dataset_provenance/deepmimo_asu35_v1/deepmimo_provenance.json). Kênh giữ thang đo tuyệt đối DeepMIMO, được dùng làm CSI ước lượng đầu vào với bất định thiết kế norm-bounded. Run này không xác minh chất lượng bộ ước lượng CSI thực tế.

## Kết quả DeepMIMO development

Run [`DM_ASU35_SCHED_DEV_20261101`](../../log/version_08/runs/DM_ASU35_SCHED_DEV_20261101/RUN.md):

- CP01: 16.800 ứng viên; G1 đối chiếu 15.305 LP và 16.800 kiểm tra đơn điệu ngân sách.
- CP02: 480 quyết định; CP03: 320 cặp; CP04: 3 phương pháp.
- Cả ba phương pháp phục vụ trung bình 3.575 người dùng; 97/160 geometry phục vụ đủ 4, mọi geometry phục vụ ít nhất một người.
- Backward khớp số người dùng/công suất của exhaustive trên run, giảm 82% số lời gọi; thời gian trung bình quan sát được khoảng 24.608 ms so với 146.336 ms.
- Forward khớp số người dùng, tỷ số công suất trung bình khoảng 1.00479; số lời gọi thấp hơn nhưng thời gian trung bình cao hơn exhaustive trong phép đo này.
- Trạng thái: **EXPLORATORY_EVALUATION; G4 NOT_ESTABLISHED**. Dataset đã xem ở version 06/07 là development, không phải test độc lập mới.

## Xác minh artifact đã lưu

Từ repo root, với môi trường có NumPy/SciPy:

```bash
python src/version_08_robust_user_scheduling/code/run_cp06.py \
  --run-dir log/version_08/runs/DM_ASU35_SCHED_DEV_20261101 \
  --verify-only
```

Thay run ID bằng `SYN_SCHED_SMOKE_20261101` để kiểm tra smoke. Chế độ này không cần dataset/task cache; nó kiểm tra 11 artifact và snapshot code, không phải xác nhận khoa học hay chữ ký số.

## Kiểm thử

Từ thư mục version:

```bash
python -m unittest discover -s tests -v
```

Workflow synthetic chạy trong thư mục tạm, kiểm tra thứ tự CP, G1/G2, tương đương report upstream và phát hiện artifact bị thay đổi. Real data không được chạy lại bởi test.
