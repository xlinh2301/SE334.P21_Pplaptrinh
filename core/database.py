import sqlite3
import json
from typing import List
from config import settings
import os

def init_db(db_path=settings.DATABASE_PATH):
    """Khởi tạo database và bảng events nếu chưa tồn tại."""
    try:
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            camera_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            object_details TEXT, -- Lưu danh sách object dưới dạng JSON string
            confidence REAL,     -- Có thể lưu confidence cao nhất hoặc trung bình của sự kiện
            zone TEXT,           -- Khu vực nếu có
            snapshot_path TEXT   -- Đường dẫn ảnh chụp (nếu có)
            -- video_clip_path TEXT -- Đường dẫn video clip (nếu có)
        )
        ''')
        conn.commit()
        print(f"Database initialized at {db_path}")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()

def save_event(event_data, db_path=settings.DATABASE_PATH):
    """Lưu một sự kiện vào database."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Chuyển object_details thành JSON string để lưu
        obj_details_json = None
        if event_data.get('object_details'):
             try:
                 obj_details_json = json.dumps(event_data['object_details'])
             except TypeError as e:
                 print(f"Error converting object_details to JSON: {e}")
                 obj_details_json = json.dumps(str(event_data['object_details'])) # Lưu dạng string nếu lỗi

        # Lấy confidence (ví dụ lấy confidence của object đầu tiên nếu có)
        confidence = None
        if event_data.get('object_details') and len(event_data['object_details']) > 0:
            confidence = event_data['object_details'][0].get('confidence')

        cursor.execute('''
        INSERT INTO events (timestamp, camera_id, event_type, object_details, confidence, zone, snapshot_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_data.get('timestamp'),
            event_data.get('camera_id'),
            event_data.get('event_type'),
            obj_details_json,
            confidence,
            event_data.get('zone'),
            event_data.get('snapshot_path')
        ))
        conn.commit()
        # print(f"Event from {event_data.get('camera_id')} saved to DB.") # Bỏ comment nếu muốn log chi tiết
    except sqlite3.Error as e:
        print(f"Database error while saving event: {e}")
    finally:
        if conn:
            conn.close()

def get_events(limit=20, db_path=settings.DATABASE_PATH):
    """Lấy các sự kiện gần nhất từ database."""
    conn = None
    events = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Trả về kết quả dạng dictionary-like
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        for row in rows:
            event_dict = dict(row)
            # Parse lại object_details từ JSON string
            if event_dict.get('object_details'):
                try:
                    event_dict['object_details'] = json.loads(event_dict['object_details'])
                except (json.JSONDecodeError, TypeError):
                     # Giữ nguyên string nếu không parse được
                     pass
            events.append(event_dict)

    except sqlite3.Error as e:
        print(f"Database error while fetching events: {e}")
    finally:
        if conn:
            conn.close()
    return events


def delete_event(event_id: int, db_path=settings.DATABASE_PATH) -> bool:
    """Xóa một sự kiện khỏi database dựa vào ID. Trả về True nếu xóa thành công, False nếu không tìm thấy hoặc lỗi."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        # cursor.rowcount sẽ > 0 nếu có hàng bị xóa
        if cursor.rowcount > 0:
            print(f"Successfully deleted event with id: {event_id}")
            return True
        else:
            print(f"Event with id {event_id} not found for deletion.")
            return False
    except sqlite3.Error as e:
        print(f"Database error deleting event {event_id}: {e}")
        return False # Trả về False nếu có lỗi
    finally:
        if conn:
            conn.close()

def delete_multiple_events(event_ids: List[int], db_path=settings.DATABASE_PATH) -> int:
    """
    Xóa nhiều sự kiện khỏi database dựa vào danh sách các ID.
    Trả về số lượng hàng đã xóa thành công.
    """
    if not event_ids: # Nếu danh sách ID rỗng thì không làm gì cả
        return 0

    conn = None
    deleted_count = 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Tạo chuỗi placeholder (?,?,?) dựa vào số lượng ID
        placeholders = ','.join('?' * len(event_ids))
        sql = f"DELETE FROM events WHERE id IN ({placeholders})"
        cursor.execute(sql, event_ids)
        conn.commit()
        deleted_count = cursor.rowcount # Lấy số hàng thực sự đã bị xóa
        print(f"Successfully deleted {deleted_count} event(s) with IDs: {event_ids}")
    except sqlite3.Error as e:
        print(f"Database error deleting multiple events: {e}")
        # Có thể raise lỗi ở đây hoặc trả về 0 tùy cách xử lý ở API
    finally:
        if conn:
            conn.close()
    return deleted_count