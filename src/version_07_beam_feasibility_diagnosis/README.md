# Version 07: fixed-margin beamforming feasibility diagnosis

Version này giữ cố định CSI margin và chẩn đoán tính khả thi robust SINR của ZF/RZF trên lưới beam/ngân sách đã khóa. Đây là bước phân tích tiếp theo sau calibration failure ở version 06; kết quả mang trạng thái `DIAGNOSTIC_ONLY`.

## Source và tài liệu gốc

- Gói nhập: `Beam_Feasibility_Diagnosis_Code_Guide_20261029.zip`.
- `code/beam_feasibility.py` và `docs/GUIDE_IEEE_VI.pdf`/`.tex` giữ nguyên byte từ ZIP.
- `README_UPSTREAM.md` và `UPSTREAM_FILE_SHA256.csv` lưu tài liệu gốc. Manifest gốc có tham chiếu `outputs/SMOKE` không được nhập vào thư mục source này.
- `UPSTREAM_IMPORT.json` ghi checksum ZIP; `SOURCE_SHA256.csv` ghi checksum snapshot được nhập vào Git.
- `code/run_cp01.py` đến `run_cp06.py` và `checkpoint_io.py` bổ sung chạy từng CP, kiểm tra input/provenance và chặn các trạng thái cần kiểm tra tính số.

Xem [hướng dẫn từng CP](docs/RUN_BY_CP_VI.md) và [đối chiếu PDF](docs/GUIDE_AUDIT_VI.md).

## Môi trường

Từ thư mục này:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r code/requirements.txt
```

Run đã ghi nhận dùng Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1. `requirements.txt` gốc là khoảng phiên bản; không phải lockfile tái tạo chính xác môi trường.

## Dữ liệu

NPZ cần `H` phức dạng `(N,M,K)` và `groups` dạng `(N,)`; có thể có `xyz`, `scenario`. Fixture đi kèm có **36** geometry `(36,16,4)`, không phải 12 như mô tả smoke trong README upstream. Dùng `--max-geometries 12` nếu muốn giới hạn 12 geometry.

Real dataset không nằm trong Git. Dataset của run hiện tại ở:

```text
/media/icnlab/Data/hoanganh/datasets/csi_margin_calibration/data/deepmimo.npz
```

Lineage của dataset nằm ở [`log/version_06/dataset_provenance`](../../log/version_06/dataset_provenance/deepmimo_asu35_v1/deepmimo_provenance.json). Kênh giữ nguyên thang đo DeepMIMO. Việc chương trình chạy được không xác minh chất lượng CSI thực hoặc tự xác nhận đơn vị vật lý của mọi cấu hình.

## Xác minh run đã lưu

Từ repo root, sau khi kích hoạt môi trường có NumPy/SciPy:

```bash
python src/version_07_beam_feasibility_diagnosis/code/run_cp06.py \
  --run-dir log/version_07/runs/DM_ASU35_BEAM_DIAG_20261031 \
  --verify-only
```

Lệnh này kiểm tra 11 artifact và snapshot code, không cần dataset hoặc `tasks/`. Nó kiểm tra tính toàn vẹn, không thay thế xác minh khoa học hay chữ ký số.

## Kiểm thử

```bash
python -m unittest discover -s tests -v
```

Test chạy fixture synthetic trong thư mục tạm, đối chiếu CP01–CP05 với report gốc, kiểm tra CP06 và việc phát hiện artifact bị thay đổi. Không chạy lại dữ liệu thật.
