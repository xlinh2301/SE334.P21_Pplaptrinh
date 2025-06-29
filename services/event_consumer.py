# services/event_consumer.py
import json
import logging
import time
from datetime import datetime
from utils import redis_utils
from core import database
from config import settings
import redis

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_event(event_data):
    """Xử lý sự kiện nhận được từ Redis và lưu vào database."""
    try:
        # Chuyển đổi timestamp nếu cần
        if isinstance(event_data.get('timestamp'), str):
            event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
            
        # Lưu vào database
        database.save_event(event_data)
        logger.info(f"Saved event to database: {event_data.get('event_type')} from {event_data.get('camera_id')}")
        
    except Exception as e:
        logger.error(f"Error saving event to database: {e}")
        logger.error(f"Event data: {json.dumps(event_data, default=str)}")

def main():
    """Khởi động consumer để lắng nghe sự kiện từ Redis."""
    logger.info("Starting event consumer...")
    
    redis_conn = None
    while True:  # Vòng lặp để thử kết nối lại nếu Redis mất kết nối
        try:
            if not redis_conn or not redis_conn.ping():
                logger.info("Attempting to connect to Redis...")
                redis_conn = redis_utils.get_redis_connection()

            if redis_conn:
                pubsub = redis_utils.subscribe(redis_conn, settings.REDIS_CHANNEL)
                if pubsub:
                    logger.info(f"Subscribed to Redis channel: {settings.REDIS_CHANNEL}")
                    logger.info("Started listening for messages...")
                    # Bắt đầu lắng nghe
                    redis_utils.listen_for_messages(pubsub, process_event)
                else:
                    logger.error("Failed to subscribe to Redis channel. Retrying in 5 seconds...")
            else:
                logger.error("Failed to connect to Redis. Retrying in 5 seconds...")

        except redis.exceptions.ConnectionError:
            logger.error("Redis connection lost. Retrying in 5 seconds...")
            redis_conn = None  # Đặt lại để thử kết nối ở lần lặp sau
        except KeyboardInterrupt:
            logger.info("\nConsumer stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(5)  # Chờ 5 giây trước khi thử lại nếu có lỗi

        time.sleep(5)  # Chờ 5 giây trước khi thử lại nếu có lỗi hoặc mất kết nối

    if redis_conn:
        redis_conn.close()
        logger.info("Redis connection closed.")

if __name__ == '__main__':
    main()