# Hướng dẫn chạy R2 trên máy đã chạy v10 (Windows)

**Mục tiêu:** chạy lại Section V (A–D) của manuscript bằng code R2 trên tập DeepMIMO v10 (160 geometry) và sinh sẵn bảng kết quả. Thời gian khoảng 5 phút cho A–C.

## 1. Chuẩn bị (một lần)

1. Giải nén gói vào một **thư mục mới**, ví dụ `D:\NCS\R2`. Không ghi đè thư mục v10 cũ và không đặt trong OneDrive.
2. Mở PowerShell tại thư mục đó (Shift + chuột phải → *Open PowerShell window here*).
3. Máy đã chạy v10 thường đã có đủ thư viện. Nếu bước kiểm tra ở mục 2 báo thiếu, chạy:
   `python -m pip install -r code/requirements.txt`
   Yêu cầu: Python ≥ 3.8, NumPy ≥ 1.24, SciPy ≥ 1.10. Không cần `mpmath` nữa.

## 2. Kiểm tra máy (bắt buộc, khoảng 30 giây)

```powershell
python code/check_env.py --data "D:\data\deepmimo_v10.npz"
```

Kết quả phải là `RESULT: PASS`, đồng thời dòng `v10 development set (sha matches): True` xác nhận đúng file v10. Nếu báo FAIL, **dừng lại** và gửi file `ENV_CHECK.json`.

## 3. Chạy toàn bộ (một lệnh)

```powershell
powershell -ExecutionPolicy Bypass -File .\CHAY_TOAN_BO.ps1 -Dev "D:\data\deepmimo_v10.npz" -Tag V11
```

- Nếu máy dùng lệnh `py` thay cho `python`, thêm `-Python py`.
- Nếu đã có tập test độc lập, thêm `-TestDM "<file.npz>" -TestDMProv "<provenance.json>"` (và/hoặc `-Test3GPP ... -Test3GPPProv ...`). Script tự khóa protocol trước khi đọc dữ liệu test.
- Bị mất điện hoặc tắt máy giữa chừng: chạy lại **đúng lệnh cũ, cùng `-Tag`**, chương trình sẽ chạy tiếp từ chỗ dừng.

## 4. Gửi lại kết quả

Khi chạy xong, gửi file `KET_QUA_V11.zip`. File này gồm bảng `V11_MANUSCRIPT_TABLES.md`, `V11_manuscript_results.json`, `ENV_CHECK.json` và các file CP của từng phần.

## 5. Quy tắc (không được vi phạm)

1. Không sửa code và không đổi tham số (`q`, `sigma`, SINR, `pmax`, danh sách `alpha`, `repeats`, `bootstrap`). Nếu thật sự phải đổi, dùng `-Tag` mới và ghi lý do.
2. Không dùng tập v10 làm tập test độc lập; code sẽ từ chối.
3. Không xóa thư mục `outputs\`: đó là checkpoint dùng để chạy tiếp và để kiểm toán.

## 6. Lỗi thường gặp

| Thông báo | Cách xử lý |
|---|---|
| `running scripts is disabled` | Dùng đúng lệnh ở mục 3 (có `-ExecutionPolicy Bypass`). |
| `python is not recognized` | Thêm `-Python py`, hoặc dùng đường dẫn đầy đủ tới `python.exe`. |
| `signature mismatch` / `new run-id required` | Code, dữ liệu hoặc tham số đã thay đổi so với lần chạy trước có cùng Tag. Dùng `-Tag` mới. |
| `Code or parameters changed after lock` | Tập test đã được khóa với tham số khác. Dùng `-Tag` mới. |
| `MISMATCH` hoặc `FALSE_PRUNE` | Lỗi khoa học thật. Dừng lại, gửi ngay thư mục `outputs\V11_AB` cùng `ENV_CHECK.json`. |
| `PermissionError` | Thư mục nằm trong OneDrive hoặc đang bị antivirus quét; chuyển sang `D:\NCS\...`. |
