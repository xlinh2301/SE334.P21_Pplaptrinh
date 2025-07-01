# services/video_processor.py
import cv2
import os
import time
import json
from datetime import datetime
import multiprocessing
from config import settings
from core.detection import Detector
from utils import redis_utils
import argparse

# --- Refactored Functions ---

def initialize_processor(camera_id):
    """Initializes all necessary components for a video processing worker."""
    print(f"[{camera_id}] Initializing processor...")
    try:
        detector = Detector(settings.YOLO_MODEL_PATH)
        if not detector.model:
            print(f"[{camera_id}] Failed to load model.")
            return None, None
    except Exception as e:
        print(f"[{camera_id}] Error initializing Detector: {e}")
        return None, None

    redis_conn = redis_utils.get_redis_connection()
    if not redis_conn:
        print(f"[{camera_id}] Failed to connect to Redis.")
        return detector, None

    try:
        os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
    except OSError as e:
        print(f"[{camera_id}] Error creating snapshot directory {settings.SNAPSHOT_DIR}: {e}")

    return detector, redis_conn

def get_significant_detections(detections):
    """Filters raw detections for objects of interest based on settings."""
    obj_confidence_threshold = getattr(settings, 'DETECTION_CONFIDENCE_THRESHOLD', 0.4)
    interesting_classes = getattr(settings, 'INTERESTING_OBJECT_CLASSES', ['person'])
    
    significant_detections = [
        det for det in detections
        if det['class_name'] in interesting_classes and det['confidence'] >= obj_confidence_threshold
    ]
    return significant_detections

def draw_bounding_boxes(frame, detections):
    """Draws bounding boxes and labels on a frame for visualization."""
    for d in detections:
        bbox = d['bbox']
        track_id_str = f"ID:{d['track_id']} " if d['track_id'] is not None else ""
        label = f"{track_id_str}{d['class_name']}:{d['confidence']:.2f}"
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        cv2.putText(frame, label, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame

def save_snapshot(frame, camera_id, timestamp_str):
    """Saves a snapshot of the frame to the disk."""
    snapshot_filename = f"snapshot_{camera_id}_{timestamp_str}.jpg"
    snapshot_path = os.path.join(settings.SNAPSHOT_DIR, snapshot_filename)
    try:
        success = cv2.imwrite(snapshot_path, frame)
        if success:
            # Convert WSL path to Windows path if running in WSL
            if snapshot_path.startswith('/mnt/'):
                # Convert /mnt/e/... to E:\...
                parts = snapshot_path.split('/')
                if len(parts) >= 3:
                    drive_letter = parts[2].upper()
                    windows_path = f"{drive_letter}:\\" + "\\".join(parts[3:])
                    return windows_path
            return snapshot_path
        else:
            print(f"[{camera_id}] Failed to save snapshot: {snapshot_path}")
            return None
    except Exception as e:
        print(f"[{camera_id}] Error saving snapshot {snapshot_path}: {e}")
        return None

def handle_new_objects(redis_conn, camera_id, frame, detections, alerted_track_ids, timestamp_iso, timestamp_str):
    """Identifies new objects, saves snapshots, and publishes events to Redis."""
    newly_tracked_objects = []
    for det in detections:
        track_id = det.get('track_id')
        if track_id is not None and track_id not in alerted_track_ids:
            newly_tracked_objects.append(det)
            alerted_track_ids.add(track_id)

    if not newly_tracked_objects:
        return

    print(f"[{camera_id}] New objects tracked with IDs: {[d['track_id'] for d in newly_tracked_objects]}. Triggering event.")

    # Create a clean frame for the snapshot and draw all current detections on it
    snapshot_frame = frame.copy()
    draw_bounding_boxes(snapshot_frame, detections)
    snapshot_path_saved = save_snapshot(snapshot_frame, camera_id, timestamp_str)

    # Create and publish the event for the newly detected objects
    event_data = {
        'timestamp': timestamp_iso,
        'camera_id': camera_id,
        'event_type': 'object_detected',
        'object_details': newly_tracked_objects,
        'snapshot_path': snapshot_path_saved
    }
    redis_utils.publish_event(redis_conn, settings.REDIS_CHANNEL, event_data)

def handle_keyboard_input(camera_id):
    """Handles user keyboard input for pausing or quitting."""
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print(f"[{camera_id}] 'q' pressed, stopping video processing.")
        return 'quit'
    elif key == ord('p'):
        print(f"[{camera_id}] Paused. Press 'p' again to resume or 'q' to quit.")
        while True:
            key2 = cv2.waitKey(0) & 0xFF
            if key2 == ord('p'):
                print(f"[{camera_id}] Resumed.")
                return 'continue'
            elif key2 == ord('q'):
                print(f"[{camera_id}] 'q' pressed during pause, stopping.")
                return 'quit'
    return 'continue'

def cleanup(cap, redis_conn, camera_id):
    """Releases resources like video capture and Redis connection."""
    if cap:
        cap.release()
    if redis_conn:
        try:
            redis_conn.close()
            print(f"[{camera_id}] Redis connection closed.")
        except Exception as e:
             print(f"[{camera_id}] Error closing Redis connection: {e}")
    cv2.destroyAllWindows()


def process_video(video_path, camera_id):
    """
    Main function for a single video processing worker.
    It initializes components, loops through frames, detects objects, and handles events.
    """
    detector, redis_conn = initialize_processor(camera_id)
    if not detector or not redis_conn:
        print(f"[{camera_id}] Initialization failed. Exiting.")
        if redis_conn: redis_conn.close()
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[{camera_id}] Error opening video file: {video_path}")
        cleanup(cap, redis_conn, camera_id)
        return

    alerted_track_ids = set()
    frame_count = 0
    start_time = time.time()

    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                print(f"[{camera_id}] End of video or error reading frame.")
                break

            frame_count += 1
            timestamp_dt = datetime.now()
            timestamp_iso = timestamp_dt.isoformat()
            timestamp_str = timestamp_dt.strftime("%Y%m%d_%H%M%S_%f")[:-3]

            # 1. Detect objects and filter for significant ones
            raw_detections = detector.process_frame(frame, enable_tracking=True)
            significant_detections = get_significant_detections(raw_detections)

            # 2. Handle alerts for new objects
            if significant_detections:
                handle_new_objects(redis_conn, camera_id, frame, significant_detections, alerted_track_ids, timestamp_iso, timestamp_str)

            # 3. Prepare frame for display
            display_frame = frame.copy()
            draw_bounding_boxes(display_frame, significant_detections)
            cv2.imshow(f"{camera_id}_Frame", display_frame)

            # 4. Handle user input
            user_action = handle_keyboard_input(camera_id)
            if user_action == 'quit':
                break

            time.sleep(0.01)

        except Exception as e:
            print(f"[{camera_id}] An error occurred during frame processing: {e}")
            break # Exit loop on critical error

    # --- Dọn dẹp ---
    end_time = time.time()
    print(f"[{camera_id}] Finished processing video: {video_path}. Total frames: {frame_count}. Time: {end_time - start_time:.2f}s")
    cleanup(cap, redis_conn, camera_id)


def get_video_sources_from_args():
    """Parses command-line arguments to get the list of videos to process."""
    parser = argparse.ArgumentParser(description="Process video files for object detection.")
    parser.add_argument(
        '--video-path',
        type=str,
        help='Path to a single video file to process. Overrides the config file.'
    )
    args = parser.parse_args()

    videos_to_process = []
    if args.video_path:
        if os.path.exists(args.video_path):
            videos_to_process.append(args.video_path)
            print(f"Processing single video from command line: {args.video_path}")
        else:
            print(f"Error: Video file not found at --video-path: {args.video_path}")
    else:
        if not hasattr(settings, 'VIDEO_FILES') or not settings.VIDEO_FILES:
            print("Error: VIDEO_FILES not defined or empty in config/settings.py and no --video-path provided.")
        else:
            videos_to_process = settings.VIDEO_FILES
            print(f"Processing {len(videos_to_process)} video(s) from config/settings.py.")
    return videos_to_process


def main():
    """Main entry point: gets video sources and starts processing tasks in parallel."""
    try:
        os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
        print(f"Snapshot directory ensured at: {settings.SNAPSHOT_DIR}")
    except Exception as e:
        print(f"Warning: Could not create snapshot directory {settings.SNAPSHOT_DIR}: {e}. Snapshots might fail.")

    videos_to_process = get_video_sources_from_args()

    if not videos_to_process:
        print("No videos to process.")
        return

    processes = []
    multiprocessing.set_start_method('spawn', force=True)

    for video_file in videos_to_process:
        if not os.path.exists(video_file):
            print(f"Video file not found, skipping: {video_file}")
            continue
        
        camera_id = f"video_{os.path.splitext(os.path.basename(video_file))[0]}"
        try:
            p = multiprocessing.Process(target=process_video, args=(video_file, camera_id))
            processes.append(p)
            p.start()
            print(f"Started process PID {p.pid} for {camera_id} ({video_file})")
        except Exception as e:
            print(f"Error starting process for {video_file}: {e}")

    if not processes:
        print("No valid video files were found to process.")
        return

    print("Waiting for video processing processes to complete...")
    for p in processes:
        try:
            p.join()
            print(f"Process PID {p.pid} finished.")
        except Exception as e:
            print(f"Error joining process PID {p.pid}: {e}")
    print("All video processing tasks finished.")


if __name__ == '__main__':
    main()