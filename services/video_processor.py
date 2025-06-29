# services/video_processor.py
import cv2
import os
import time
import json
from datetime import datetime, timedelta
import multiprocessing
import numpy as np
from config import settings
from core.detection import Detector
from utils import redis_utils
import argparse

def process_video(video_path, camera_id):
    """
    Xử lý một file video: đọc frame, detect chuyển động (chỉ báo khi bắt đầu),
    detect object (với cooldown), chụp ảnh và publish event lên Redis.
    Hàm này sẽ chạy trong một process riêng.
    """
    print(f"[{camera_id}] Starting processing for video: {video_path}")

    # --- Khởi tạo trong process con ---
    try:
        detector = Detector(settings.YOLO_MODEL_PATH)
        if not detector.model:
            print(f"[{camera_id}] Failed to load model. Exiting process.")
            return
    except Exception as e:
        print(f"[{camera_id}] Error initializing Detector: {e}")
        return

    redis_conn = redis_utils.get_redis_connection()
    if not redis_conn:
        print(f"[{camera_id}] Failed to connect to Redis. Exiting process.")
        return

    # Đảm bảo thư mục snapshots tồn tại
    try:
        os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
    except OSError as e:
        print(f"[{camera_id}] Error creating snapshot directory {settings.SNAPSHOT_DIR}: {e}")

    # Biến state để theo dõi các track ID đã được gửi cảnh báo
    alerted_track_ids = set()

    # --- Kết thúc khởi tạo ---

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[{camera_id}] Error opening video file: {video_path}")
        if redis_conn: redis_conn.close()
        return

    frame_count = 0
    start_time = time.time()

    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                print(f"[{camera_id}] End of video or error reading frame.")
                break

            frame_count += 1
            timestamp_dt = datetime.now() # Lấy timestamp 1 lần cho frame này
            timestamp_iso = timestamp_dt.isoformat()
            timestamp_str = timestamp_dt.strftime("%Y%m%d_%H%M%S_%f")[:-3] # Format cho tên file

            # --- 2. Phát hiện đối tượng (YOLOv8) ---
            detections = detector.process_frame(frame, enable_tracking=True)

            significant_detections = []
            detected_classes_this_frame = set()
            obj_confidence_threshold = getattr(settings, 'DETECTION_CONFIDENCE_THRESHOLD', 0.4)
            interesting_classes = getattr(settings, 'INTERESTING_OBJECT_CLASSES', ['person']) # Default là person nếu không có setting
            for det in detections:
                if det['class_name'] in interesting_classes and \
                   det['confidence'] >= obj_confidence_threshold:
                    significant_detections.append(det)
                    detected_classes_this_frame.add(det['class_name'])

            # --- Vẽ bounding box lên frame hiển thị ---
            for d in significant_detections:
                bbox = d['bbox']
                # Thêm track_id vào label nếu có
                track_id_str = f"ID:{d['track_id']} " if d['track_id'] is not None else ""
                label = f"{track_id_str}{d['class_name']}:{d['confidence']:.2f}"
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                cv2.putText(frame, label, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # --- 3. Gửi cảnh báo cho các đối tượng MỚI được theo dõi ---
            newly_tracked_objects = []
            if significant_detections:
                for det in significant_detections:
                    track_id = det.get('track_id')
                    if track_id is not None and track_id not in alerted_track_ids:
                        newly_tracked_objects.append(det)
                        alerted_track_ids.add(track_id) # Thêm vào set để không báo lại

            # Nếu có đối tượng mới, tạo và gửi sự kiện
            if newly_tracked_objects:
                print(f"[{camera_id}] New objects tracked with IDs: {[d['track_id'] for d in newly_tracked_objects]}. Triggering event.")

                # Chụp ảnh của frame hiện tại khi có đối tượng mới
                snapshot_filename = f"snapshot_{camera_id}_{timestamp_str}.jpg"
                snapshot_path = os.path.join(settings.SNAPSHOT_DIR, snapshot_filename)
                frame_to_save = frame.copy()
                
                # Vẽ bounding box lên ảnh chụp (vẽ tất cả các box có trong frame, không chỉ box mới)
                for d in significant_detections:
                    bbox = d['bbox']
                    track_id_str = f"ID:{d['track_id']} " if d['track_id'] is not None else ""
                    label = f"{track_id_str}{d['class_name']}:{d['confidence']:.2f}"
                    cv2.rectangle(frame_to_save, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                    cv2.putText(frame_to_save, label, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                snapshot_path_saved = None
                try:
                    success = cv2.imwrite(snapshot_path, frame_to_save)
                    if success:
                        snapshot_path_saved = snapshot_path
                    else:
                        print(f"[{camera_id}] Failed to save snapshot: {snapshot_path}")
                except Exception as e:
                    print(f"[{camera_id}] Error saving snapshot {snapshot_path}: {e}")

                # Tạo và publish sự kiện 'object_detected' chỉ với các đối tượng mới
                event_data = {
                    'timestamp': timestamp_iso,
                    'camera_id': camera_id,
                    'event_type': 'object_detected',
                    'object_details': newly_tracked_objects,
                    'snapshot_path': snapshot_path_saved
                }
                redis_utils.publish_event(redis_conn, settings.REDIS_CHANNEL, event_data)

            # (Tùy chọn) Hiển thị frame debug - comment lại khi chạy chính thức
            cv2.imshow(f"{camera_id}_Frame", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print(f"[{camera_id}] 'q' pressed, stopping video processing.")
                break
            elif key == ord('p'): # Tạm dừng/Tiếp tục
                print(f"[{camera_id}] Paused. Press 'p' again to resume.")
                while True:
                    key2 = cv2.waitKey(0) & 0xFF
                    if key2 == ord('p'):
                        print(f"[{camera_id}] Resumed.")
                        break
                    elif key2 == ord('q'):
                         print(f"[{camera_id}] 'q' pressed during pause, stopping.")
                         ret = False # Đặt ret=False để thoát vòng lặp ngoài
                         break
                if not ret: break


            time.sleep(0.01) 

        except Exception as e:
            print(f"[{camera_id}] An error occurred during frame processing: {e}")

    # --- Dọn dẹp ---
    end_time = time.time()
    print(f"[{camera_id}] Finished processing video: {video_path}. Total frames: {frame_count}. Time: {end_time - start_time:.2f}s")
    if cap:
        cap.release()

    if redis_conn:
        try:
            redis_conn.close()
            print(f"[{camera_id}] Redis connection closed.")
        except Exception as e:
             print(f"[{camera_id}] Error closing Redis connection: {e}")
    cv2.destroyAllWindows() # Đảm bảo đóng cửa sổ imshow

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process video files for object detection.")
    parser.add_argument(
        '--video-path',
        type=str,
        help='Path to a single video file to process. Overrides the config file.'
    )
    args = parser.parse_args()

    try:
        os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
        print(f"Snapshot directory ensured at: {settings.SNAPSHOT_DIR}")
    except Exception as e:
        print(f"Warning: Could not create snapshot directory {settings.SNAPSHOT_DIR}: {e}. Snapshots might fail.")

    videos_to_process = []
    if args.video_path:
        if os.path.exists(args.video_path):
            videos_to_process.append(args.video_path)
            print(f"Processing single video from command line: {args.video_path}")
        else:
            print(f"Error: Video file not found at --video-path: {args.video_path}")
    else:
        # Nếu không, lấy danh sách từ file settings
        if not hasattr(settings, 'VIDEO_FILES') or not settings.VIDEO_FILES:
            print("Error: VIDEO_FILES not defined or empty in config/settings.py and no --video-path provided.")
        else:
            videos_to_process = settings.VIDEO_FILES
            print(f"Processing {len(videos_to_process)} video(s) from config/settings.py.")

    if videos_to_process:
        processes = []
        multiprocessing.set_start_method('spawn', force=True)

        for video_file in videos_to_process:
            if os.path.exists(video_file):
                camera_id = f"video_{os.path.splitext(os.path.basename(video_file))[0]}"
                try:
                    p = multiprocessing.Process(target=process_video, args=(video_file, camera_id))
                    processes.append(p)
                    p.start()
                    print(f"Started process PID {p.pid} for {camera_id} ({video_file})")
                except Exception as e:
                    print(f"Error starting process for {video_file}: {e}")
            else:
                print(f"Video file not found, skipping: {video_file}")

        if processes:
            print("Waiting for video processing processes to complete...")
            for p in processes:
                try:
                    p.join()
                    print(f"Process PID {p.pid} finished.")
                except Exception as e:
                    print(f"Error joining process PID {p.pid}: {e}")
            print("All video processing tasks finished.")
        else:
            print("No valid video files were found to process.")
    else:
        print("No videos to process.")