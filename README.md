# Hệ Thống Giám Sát Video

Đây là một hệ thống giám sát video sử dụng YOLOv8 để phát hiện đối tượng trong các luồng video, gửi cảnh báo qua Redis và cung cấp một API để truy vấn các sự kiện.

## Tính năng chính

- **Phát hiện đối tượng**: Sử dụng YOLOv8 để phát hiện người và các đối tượng khác
- **Tracking đối tượng**: Theo dõi đối tượng qua các frame với ByteTrack
- **Cảnh báo email**: Tự động gửi email cảnh báo khi phát hiện đối tượng
- **Giao diện web**: Dashboard để xem và quản lý các sự kiện
- **Lưu trữ dữ liệu**: Database SQLite để lưu trữ sự kiện và ảnh chụp
- **Xử lý đa luồng**: Hỗ trợ xử lý nhiều video đồng thời
- **API RESTful**: API để truy vấn và quản lý sự kiện

## Cấu trúc thư mục

- **/config**: Chứa file cấu hình `settings.py`.
- **/core**: Chứa các logic cốt lõi (phát hiện đối tượng, schema dữ liệu, database).
- **/data**: Chứa video đầu vào và các ảnh chụp (snapshot) được tạo ra.
- **/services**: Chứa các kịch bản chạy các thành phần của hệ thống (API, Alerter, Consumer, Processor).
- **/utils**: Chứa các module tiện ích (email, Redis).
- **/static, /templates**: Cho giao diện web của API.
- **/database**: Chứa file database SQLite.

## Cài đặt

Hướng dẫn này giả định bạn đã cài đặt Python 3.8+ và pip.

### 1. Cài đặt Redis (Yêu cầu bắt buộc)

Hệ thống sử dụng Redis làm message broker. Bạn cần phải cài đặt và khởi động Redis server trước khi chạy các dịch vụ.

- **Trên Windows:** Cách tốt nhất là sử dụng WSL (Windows Subsystem for Linux).
  1. Cài đặt WSL và Ubuntu bằng lệnh `wsl --install` trong PowerShell (với quyền admin).
  2. Mở Ubuntu, chạy `sudo apt update && sudo apt install redis-server`.
  3. Khởi động Redis bằng `sudo service redis-server start`.
  4. Kiểm tra với `redis-cli ping` (phải trả về `PONG`).

- **Trên macOS:** Sử dụng Homebrew: `brew install redis` và sau đó `brew services start redis`.

- **Trên Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install redis-server` và `sudo systemctl start redis-server`.

### 2. Tạo và kích hoạt môi trường ảo

```bash
# Tạo môi trường ảo
python -m venv myvenv

# Kích hoạt môi trường ảo
# Trên Windows
myvenv\\Scripts\\activate

# Trên macOS/Linux
source myvenv/bin/activate
```

### 3. Cài đặt các gói phụ thuộc

Đảm bảo rằng bạn đã kích hoạt môi trường ảo, sau đó chạy lệnh sau:

```bash
pip install -r requirements.txt
```

### 4. Cấu hình Email (Tùy chọn)

Để sử dụng tính năng gửi email cảnh báo, bạn cần cấu hình thông tin SMTP trong file `config/settings.py`:

```python
# Cấu hình Gmail
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Sử dụng App Password cho Gmail
EMAIL_USE_TLS = True
EMAIL_RECEIVER = 'receiver-email@gmail.com'
```

**Lưu ý**: Nếu sử dụng Gmail, bạn cần tạo "App Password" thay vì sử dụng mật khẩu thông thường.

## Chạy hệ thống

Hệ thống bao gồm 4 thành phần chính cần được chạy song song:
- `event_consumer.py`: Lắng nghe sự kiện từ Redis và ghi vào database.
- `alerter.py`: Lắng nghe sự kiện và gửi cảnh báo email.
- `api.py`: Cung cấp giao diện API và web để xem các sự kiện.
- `video_processor.py`: Xử lý video và phát hiện đối tượng.

### Khởi động các dịch vụ nền

Sử dụng kịch bản `start_system.sh` để khởi động tất cả các dịch vụ cần thiết ở chế độ nền.

```bash
# Cấp quyền thực thi cho file script (chỉ cần làm một lần)
chmod +x start_system.sh

# Chạy script
bash start_system.sh
```

Sau khi chạy, các dịch vụ API, Alerter, và Event Consumer sẽ chạy ngầm. Log của chúng sẽ được ghi vào các file `api_server.log`, `alerter.log`, và `event_consumer.log`.

Để dừng các dịch vụ, bạn có thể dùng lệnh `pkill -f services` hoặc `pkill -f uvicorn` trên Linux/macOS, hoặc tìm và dừng các tiến trình Python trên Windows Task Manager.

### Truy cập giao diện web

Sau khi khởi động API server, bạn có thể truy cập giao diện web tại:
- **Dashboard**: http://127.0.0.1:8008/
- **API Status**: http://127.0.0.1:8008/api/status
- **Events API**: http://127.0.0.1:8008/api/events

## Xử lý Video

Sau khi hệ thống đã chạy, bạn có thể bắt đầu xử lý video để phát hiện đối tượng.

### Cách 1: Xử lý một file video cụ thể

Bạn có thể xử lý một file video duy nhất bằng cách truyền đường dẫn của nó qua tham số `--video-path`.

```bash
python -m services.video_processor --video-path data/videos/video1.mp4
```

Thay `data/videos/video1.mp4` bằng đường dẫn tới file video của bạn. Một cửa sổ sẽ hiện lên để hiển thị quá trình xử lý. Nhấn `q` để dừng, `p` để tạm dừng/tiếp tục.

### Cách 2: Xử lý hàng loạt video từ file cấu hình

Bạn có thể định cấu hình một danh sách các video để xử lý cùng lúc.

1. **Mở file `config/settings.py`.**
2. **Chỉnh sửa biến `VIDEO_FILES`**:
   ```python
   # config/settings.py
   VIDEO_FILES = [
       "data/videos/video1.mp4",
       "data/videos/video2.mp4",
       # Thêm các đường dẫn video khác tại đây
   ]
   ```
3. **Chạy kịch bản xử lý:**
   ```bash
   python -m services.video_processor
   ```
   Kịch bản sẽ tạo một tiến trình riêng cho mỗi video trong danh sách và xử lý chúng đồng thời.

## Tính năng chi tiết

### Phát hiện và Tracking đối tượng

- **Model**: Sử dụng YOLOv8 với model `yolo12x.pt`
- **Tracking**: ByteTrack để theo dõi đối tượng qua các frame
- **Đối tượng quan tâm**: Mặc định phát hiện người (`person`)
- **Ngưỡng tin cậy**: Có thể điều chỉnh trong `config/settings.py`
- **Cooldown**: Tránh spam cảnh báo cho cùng một đối tượng

### Cảnh báo Email

- **Điều kiện**: Phát hiện người với confidence > 0.6
- **Nội dung**: Thông tin chi tiết về đối tượng, camera, thời gian
- **Cấu hình**: SMTP settings trong `config/settings.py`
- **Test**: Sử dụng `python test_email.py` để kiểm tra

### Giao diện Web

- **Dashboard**: Hiển thị danh sách sự kiện theo thời gian thực
- **Ảnh chụp**: Xem ảnh snapshot khi có sự kiện
- **Quản lý**: Xóa sự kiện đơn lẻ hoặc hàng loạt
- **Auto-refresh**: Cập nhật dữ liệu mỗi 5 giây

### API Endpoints

- `GET /api/events`: Lấy danh sách sự kiện (limit mặc định: 50)
- `GET /api/snapshots/{filename}`: Lấy ảnh snapshot
- `DELETE /api/events/{event_id}`: Xóa sự kiện
- `POST /api/events/delete-bulk`: Xóa nhiều sự kiện
- `GET /api/status`: Kiểm tra trạng thái API

### Database Schema

Bảng `events` chứa:
- `id`: ID tự động tăng
- `timestamp`: Thời gian sự kiện
- `camera_id`: ID camera
- `event_type`: Loại sự kiện
- `object_details`: Chi tiết đối tượng (JSON)
- `confidence`: Độ tin cậy
- `zone`: Khu vực (nếu có)
- `snapshot_path`: Đường dẫn ảnh chụp

## Cấu hình nâng cao

### Điều chỉnh tham số phát hiện

Trong `config/settings.py`:

```python
# Ngưỡng tin cậy cho phát hiện
DETECTION_CONFIDENCE_THRESHOLD = 0.8

# Đối tượng quan tâm
INTERESTING_OBJECT_CLASSES = ['person']

# Thời gian cooldown giữa các cảnh báo (giây)
ALERT_COOLDOWN_SECONDS = 30

# Ngưỡng diện tích pixel tối thiểu cho chuyển động
MIN_MOTION_CONTOUR_AREA = 700
```

### Cấu hình Redis

```python
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_CHANNEL = 'surveillance_events'
```

### Cấu hình API

```python
API_HOST = "127.0.0.1"
API_PORT = 8008
```

## Troubleshooting

### Lỗi kết nối Redis
- Đảm bảo Redis server đang chạy
- Kiểm tra cấu hình host/port trong `settings.py`
- Chạy `redis-cli ping` để kiểm tra kết nối

### Lỗi Email
- Kiểm tra cấu hình SMTP trong `settings.py`
- Đảm bảo sử dụng App Password cho Gmail
- Chạy `python test_email.py` để test

### Lỗi Model YOLO
- Đảm bảo file model `yolo12x.pt` tồn tại
- Kiểm tra quyền truy cập file
- Cài đặt lại ultralytics: `pip install ultralytics --upgrade`

### Lỗi Video Processing
- Kiểm tra đường dẫn video trong `VIDEO_FILES`
- Đảm bảo format video được hỗ trợ (MP4, AVI, etc.)
- Kiểm tra quyền truy cập file video

## Dependencies

Các thư viện chính được sử dụng:
- `fastapi`: Web framework cho API
- `uvicorn`: ASGI server
- `opencv-python`: Xử lý video
- `ultralytics`: YOLOv8 model
- `redis`: Message broker
- `sqlite3`: Database (built-in)
- `smtplib`: Gửi email (built-in)

## Đóng góp

Để đóng góp vào dự án:
1. Fork repository
2. Tạo branch mới cho tính năng
3. Commit changes
4. Push và tạo Pull Request

## License

Dự án này được phát hành dưới MIT License. 