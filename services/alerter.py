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

def handle_event_for_alert(event_data):
    """Hàm callback để xử lý message và quyết định có gửi cảnh báo không."""
    event_type = event_data.get('event_type')
    camera_id = event_data.get('camera_id')
    timestamp = event_data.get('timestamp')
    details = event_data.get('object_details', [])
    alert_triggered = False
    message = ""

    # Ví dụ: Cảnh báo nếu phát hiện 'person'
    for obj in details:
        if obj.get('class_name') == 'person' and obj.get('confidence', 0) > 0.6: # Confidence cao hơn cho cảnh báo person
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
        logger.info("="*20 + " ALERT " + "="*20)
        logger.info(message)

        # Gửi email cảnh báo
        send_email_alert('WARNING: ',message)
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