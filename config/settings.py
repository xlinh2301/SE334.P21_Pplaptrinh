# config/settings.py
import os

# --- Đường dẫn ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_SOURCE_DIR = os.path.join(BASE_DIR, 'data', 'videos')
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'surveillance.db')
SNAPSHOT_DIR = os.path.join(BASE_DIR, 'data', 'snapshots') # <<< THÊM DÒNG NÀY

# --- Cấu hình Redis ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_CHANNEL = 'surveillance_events'

# --- Cấu hình YOLOv8 ---
YOLO_MODEL_PATH = 'yolo12x.pt'
DETECTION_CONFIDENCE_THRESHOLD = 0.8

# --- Cấu hình Logic Sự kiện ---
INTERESTING_OBJECT_CLASSES = ['person']
MIN_MOTION_CONTOUR_AREA = 700  # <<< THÊM DÒNG NÀY (Ngưỡng diện tích pixel tối thiểu để coi là chuyển động)
ALERT_COOLDOWN_SECONDS = 30  # <<< THÊM DÒNG NÀY: Thời gian chờ (giây) trước khi gửi lại cảnh báo cho cùng loại đối tượng trên cùng camera


# --- Cấu hình Video Processor ---
VIDEO_FILES = [
    # os.path.join(VIDEO_SOURCE_DIR, 'video3.mp4'),
    os.path.join(VIDEO_SOURCE_DIR, 'video2.mp4'),
]

# --- Cấu hình API ---
API_HOST = "127.0.0.1"
API_PORT = 8008

# --- Cấu hình Gmail ---
EMAIL_HOST = 'smtp.gmail.com'  # hoặc host của bạn
EMAIL_PORT = 587
EMAIL_HOST_USER = 'khanh2003dakdoa@gmail.com'
EMAIL_HOST_PASSWORD = 'dgck nbii ribp wtly'  # dùng App Password nếu là Gmail
EMAIL_USE_TLS = True
EMAIL_RECEIVER = 'superkklot2001@gmail.com'