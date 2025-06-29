import redis
import json
from config import settings

def get_redis_connection():
    """Tạo kết nối đến Redis server."""
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True # Tự động decode bytes sang string khi nhận
        )
        r.ping() # Kiểm tra kết nối
        print("Connected to Redis successfully.")
        return r
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
        return None

def publish_event(redis_conn, channel, event_data):
    """Publish một sự kiện (dictionary) lên Redis channel dưới dạng JSON string."""
    if not redis_conn:
        print("Cannot publish event: No Redis connection.")
        return False
    try:
        message = json.dumps(event_data)
        redis_conn.publish(channel, message)
        # print(f"Published event to {channel}: {message[:100]}...") # Bỏ comment để debug
        return True
    except TypeError as e:
        print(f"Error serializing event data to JSON: {e}")
        return False
    except redis.exceptions.RedisError as e:
        print(f"Redis error during publish: {e}")
        return False

# --- Các hàm cho Consumer ---
def subscribe(redis_conn, channel):
    """Tạo đối tượng PubSub và subscribe vào channel."""
    if not redis_conn:
        print("Cannot subscribe: No Redis connection.")
        return None
    try:
        p = redis_conn.pubsub(ignore_subscribe_messages=True) # Bỏ qua các message thông báo subscribe thành công
        p.subscribe(channel)
        print(f"Subscribed to Redis channel: {channel}")
        return p
    except redis.exceptions.RedisError as e:
        print(f"Redis error during subscribe: {e}")
        return None

def listen_for_messages(pubsub_obj, process_func):
    """Lắng nghe message từ đối tượng PubSub và gọi hàm xử lý."""
    if not pubsub_obj:
        print("Cannot listen: No PubSub object.")
        return

    print("Started listening for messages...")
    while True:
        try:
            message = pubsub_obj.get_message() # Non-blocking
            if message:
                try:
                    event_data = json.loads(message['data'])
                    process_func(event_data) # Gọi hàm xử lý được truyền vào
                except json.JSONDecodeError:
                    print(f"Error decoding JSON: {message['data']}")
                except Exception as e:
                    print(f"Error processing message: {e}")
            # Thêm sleep nhỏ để tránh CPU usage cao khi không có message
            import time
            time.sleep(0.01)
        except redis.exceptions.ConnectionError:
             print("Redis connection lost. Attempting to reconnect...")
             # Cần thêm logic reconnect phức tạp hơn ở đây nếu muốn tự động kết nối lại
             time.sleep(5)
             break # Thoát vòng lặp hiện tại để thử kết nối lại ở tầng cao hơn (nếu có)
        except KeyboardInterrupt:
            print("Listener interrupted.")
            break
        except Exception as e:
            print(f"Unexpected error in listener loop: {e}")
            time.sleep(1) # Chờ 1 giây trước khi thử lại