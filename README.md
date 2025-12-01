# VietOCR-labeling

Công cụ đánh nhãn để training nhận diện ký tự VietOCR, PPOCR

![](doc/context_menu.png)

Link: https://thigiacmaytinh.com/huong-dan-su-dung-tool-danh-nhan-vietocr-labeling/

## Chạy WinForms (desktop)
- Yêu cầu: Windows + .NET Framework 4.6.1 + Visual Studio (workload .NET desktop) hoặc Developer Command Prompt với MSBuild.
- Mở `Labeling.sln`, chọn `Release|x86` (hoặc `Debug|x86`), Build, chạy `bin/Labeling.exe`.

## FastAPI (tùy chọn, dùng HTTP thay vì UI)
- Chuẩn bị Python 3.10+ và pip; trong thư mục repo:
  - `python3 -m venv .venv`
  - Linux/macOS: `source .venv/bin/activate` | Windows: `.venv\Scripts\activate`
  - `python3 -m pip install --upgrade pip`
  - `python3 -m pip install -r requirements-api.txt`
- Đặt biến môi trường `DATA_DIR` trỏ tới thư mục chứa ảnh + `label.txt` (các file `.txt` theo ảnh cũng nằm trong đó).
- Chạy: `uvicorn api.main:app --reload --port 8000`
- Kiểm tra nhanh bằng Postman/curl:
  - `GET http://localhost:8000/health` (trạng thái)
  - `GET http://localhost:8000/labels?size=20` (liệt kê nhãn, có phân trang)
  - `POST http://localhost:8000/labels/foo.jpg` với JSON `{"label":"abc"}` để lưu nhãn; ảnh `foo.jpg` phải có trong `DATA_DIR`
  - Ảnh tĩnh: `http://localhost:8000/files/foo.jpg`
