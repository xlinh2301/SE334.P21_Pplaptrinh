# Hệ Thống Giám Sát Video

Đây là một hệ thống giám sát video sử dụng YOLOv8 để phát hiện đối tượng trong các luồng video, gửi cảnh báo qua Redis và cung cấp một API để truy vấn các sự kiện.

## Cấu trúc thư mục

- **/config**: Chứa file cấu hình `settings.py`.
- **/core**: Chứa các logic cốt lõi (phát hiện đối tượng, schema dữ liệu).
- **/data**: Chứa video đầu vào và các ảnh chụp (snapshot) được tạo ra.
- **/services**: Chứa các kịch bản chạy các thành phần của hệ thống (API, Alerter, Consumer, Processor).
- **/utils**: Chứa các module tiện ích (ví dụ: kết nối Redis).
- **/static, /templates**: Cho giao diện web của API.

## Cài đặt

Hướng dẫn này giả định bạn đã cài đặt Python 3.8+ và pip.

1.  **Cài đặt Redis (Yêu cầu bắt buộc):**

    Hệ thống sử dụng Redis làm message broker. Bạn cần phải cài đặt và khởi động Redis server trước khi chạy các dịch vụ.

    -   **Trên Windows:** Cách tốt nhất là sử dụng WSL (Windows Subsystem for Linux).
        1.  Cài đặt WSL và Ubuntu bằng lệnh `wsl --install` trong PowerShell (với quyền admin).
        2.  Mở Ubuntu, chạy `sudo apt update && sudo apt install redis-server`.
        3.  Khởi động Redis bằng `sudo service redis-server start`.
        4.  Kiểm tra với `redis-cli ping` (phải trả về `PONG`).

    -   **Trên macOS:** Sử dụng Homebrew: `brew install redis` và sau đó `brew services start redis`.

    -   **Trên Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install redis-server` và `sudo systemctl start redis-server`.

2.  **Tạo và kích hoạt môi trường ảo:**

    ```bash
    # Tạo môi trường ảo
    python -m venv myvenv

    # Kích hoạt môi trường ảo
    # Trên Windows
    myvenv\\Scripts\\activate

    # Trên macOS/Linux
    source myvenv/bin/activate
    ```

3.  **Cài đặt các gói phụ thuộc:**

    Đảm bảo rằng bạn đã kích hoạt môi trường ảo, sau đó chạy lệnh sau:

    ```bash
    pip install -r requirements.txt
    ```

## Chạy hệ thống

Hệ thống bao gồm 3 thành phần chính cần được chạy song song:
- `event_consumer.py`: Lắng nghe sự kiện từ Redis và ghi vào database/log.
- `alerter.py`: Lắng nghe sự kiện và gửi cảnh báo (hiện tại chỉ in ra console).
- `api.py`: Cung cấp giao diện API để xem các sự kiện.

1.  **Khởi động các dịch vụ nền:**

    Sử dụng kịch bản `start_system.sh` để khởi động tất cả các dịch vụ cần thiết ở chế độ nền.

    ```bash
    # Cấp quyền thực thi cho file script (chỉ cần làm một lần)
    chmod +x start_system.sh

    # Chạy script
    bash start_system.sh
    ```
    Sau khi chạy, các dịch vụ API, Alerter, và Event Consumer sẽ chạy ngầm. Log của chúng sẽ được ghi vào các file `api_server.log`, `alerter.log`, và `event_consumer.log`.

    Để dừng các dịch vụ, bạn có thể dùng lệnh `pkill -f services` hoặc `pkill -f uvicorn` trên Linux/macOS, hoặc tìm và dừng các tiến trình Python trên Windows Task Manager.

## Xử lý Video

Sau khi hệ thống đã chạy, bạn có thể bắt đầu xử lý video để phát hiện đối tượng.

Có hai cách để thực hiện:

### Cách 1: Xử lý một file video cụ thể

Bạn có thể xử lý một file video duy nhất bằng cách truyền đường dẫn của nó qua tham số `--video-path`.

```bash
python -m services.video_processor --video-path data/videos/video1.mp4
```
Thay `data/videos/video1.mp4` bằng đường dẫn tới file video của bạn. Một cửa sổ sẽ hiện lên để hiển thị quá trình xử lý. Nhấn `q` để dừng.

### Cách 2: Xử lý hàng loạt video từ file cấu hình

Bạn có thể định cấu hình một danh sách các video để xử lý cùng lúc.

1.  **Mở file `config/settings.py`.**
2.  **Chỉnh sửa biến `VIDEO_FILES`**:
    ```python
    # config/settings.py
    VIDEO_FILES = [
        "data/videos/video1.mp4",
        "data/videos/video2.mp4",
        # Thêm các đường dẫn video khác tại đây
    ]
    ```
3.  **Chạy kịch bản xử lý:**
    ```bash
    python -m services.video_processor
    ```
    Kịch bản sẽ tạo một tiến trình riêng cho mỗi video trong danh sách và xử lý chúng đồng thời. 