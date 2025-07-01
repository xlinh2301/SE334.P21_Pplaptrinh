import time
import json
import logging
import redis
from config import settings
from utils import redis_utils
from utils.email_utils import send_email_alert


# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cache để tránh gửi email trùng lặp
sent_alerts_cache = set()

def handle_event_for_alert(event_data):
    """Hàm callback để xử lý message và quyết định có gửi cảnh báo không."""
    # DEBUG: Log toàn bộ event data
    logger.info(f"Received event data: {event_data}")
    
    event_type = event_data.get('event_type')
    camera_id = event_data.get('camera_id')
    timestamp = event_data.get('timestamp')
    details = event_data.get('object_details', [])
    snapshot_path = event_data.get('snapshot_path')  # Lấy đường dẫn ảnh
    
    # DEBUG: Log snapshot path
    logger.info(f"Snapshot path from event: {snapshot_path}")
    
    alert_triggered = False
    message = ""

    for obj in details:
        if obj.get('class_name') == 'person' and obj.get('confidence', 0) > 0.8: # Confidence cao hơn cho cảnh báo person
            alert_triggered = True
            message = (
                    f"⚠️ Security Alert Detected!\n\n"
                    f"🔍 Object: Person\n"
                    f"📷 Camera ID: {camera_id}\n"
                    f"🕒 Time: {timestamp}\n"
                    f"✅ Confidence Level: {obj['confidence']:.2f}\n\n"
                    f"Please check the camera feed immediately."
                        )

            break

    if alert_triggered:
        # Tạo unique key để tránh gửi email trùng lặp
        alert_key = f"{camera_id}_{timestamp}_{details[0].get('track_id', 'no_id')}"
        
        if alert_key in sent_alerts_cache:
            logger.info(f"Alert already sent for key: {alert_key}, skipping...")
            return
        
        # Thêm vào cache (giới hạn cache size)
        sent_alerts_cache.add(alert_key)
        if len(sent_alerts_cache) > 1000:  # Giới hạn 1000 items
            sent_alerts_cache.clear()
            logger.info("Cleared alert cache")
        
        logger.info("="*20 + " ALERT " + "="*20)
        logger.info(f"Alert key: {alert_key}")
        logger.info(message)

        # Chuyển đổi đường dẫn để phù hợp với hệ điều hành hiện tại
        converted_snapshot_path = snapshot_path
        if snapshot_path:
            if snapshot_path.startswith('/mnt/'):
                # WSL path → Windows path (nếu chạy trên Windows)
                parts = snapshot_path.split('/')
                if len(parts) >= 3:
                    drive_letter = parts[2].upper()
                    converted_snapshot_path = f"{drive_letter}:\\" + "\\".join(parts[3:])
                    logger.info(f"Converted WSL path {snapshot_path} to Windows path {converted_snapshot_path}")
            elif snapshot_path[1:3] == ':\\' and len(snapshot_path) > 3:
                # Windows path → WSL path (nếu chạy trên Ubuntu/WSL)
                drive_letter = snapshot_path[0].lower()
                wsl_path = f"/mnt/{drive_letter}/" + snapshot_path[3:].replace('\\', '/')
                converted_snapshot_path = wsl_path
                logger.info(f"Converted Windows path {snapshot_path} to WSL path {converted_snapshot_path}")

        # Gửi email cảnh báo với ảnh đính kèm
        send_email_alert('WARNING: Security Alert', message, converted_snapshot_path)
        logger.info("="*47)


if __name__ == '__main__':
    logger.info("Starting Alerter Service...")

    redis_conn = None
    while True: # Vòng lặp để thử kết nối lại
        try:
            if not redis_conn or not redis_conn.ping():
                 logger.info("Attempting to connect to Redis...")
                 redis_conn = redis_utils.get_redis_connection()

            if redis_conn:
                pubsub = redis_utils.subscribe(redis_conn, settings.REDIS_CHANNEL)
                if pubsub:
                    redis_utils.listen_for_messages(pubsub, handle_event_for_alert)
            else:
                 logger.error("Failed to connect to Redis. Retrying in 5 seconds...")

        except redis.exceptions.ConnectionError:
            logger.error("Redis connection lost. Retrying in 5 seconds...")
            redis_conn = None
        except KeyboardInterrupt:
             logger.info("Alerter service stopped by user.")
             break
        except Exception as e:
            logger.error(f"An unexpected error occurred in Alerter: {e}")

        time.sleep(5)

    if redis_conn:
        redis_conn.close()
    logger.info("Alerter Service finished.")