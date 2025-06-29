from ultralytics import YOLO
import torch
from config import settings

# Thêm cấu hình cho PyTorch
torch.serialization.add_safe_globals(['ultralytics.nn.tasks.DetectionModel'])

class Detector:
    """Quản lý việc tải model và thực hiện phát hiện đối tượng."""
    def __init__(self, model_path=settings.YOLO_MODEL_PATH):
        print(f"Loading YOLO model from: {model_path}")
        try:
            self.model = YOLO(model_path)
            self.class_names = self.model.names
            print("YOLO model loaded successfully.")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None
            self.class_names = {}

    def process_frame(self, frame, enable_tracking=False, confidence_threshold=settings.DETECTION_CONFIDENCE_THRESHOLD):
        """
        Thực hiện phát hiện hoặc theo dõi đối tượng trên một khung hình.

        Args:
            frame: Khung hình đầu vào (NumPy array).
            enable_tracking (bool): Bật/tắt chế độ theo dõi.
            confidence_threshold: Ngưỡng tin cậy tối thiểu.

        Returns:
            List các dictionary, mỗi dict chứa thông tin một đối tượng.
            Nếu tracking bật, sẽ có thêm 'track_id'.
        """
        detections = []
        if not self.model:
            return detections

        try:
            if enable_tracking:
                results = self.model.track(frame, persist=True, verbose=False, tracker='bytetrack.yaml')
            else:
                results = self.model(frame, verbose=False)

            if results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf >= confidence_threshold:
                        class_id = int(box.cls[0])
                        class_name = self.class_names.get(class_id, 'Unknown')
                        coords = box.xyxy[0].tolist()
                        
                        track_id = None
                        # Lấy track_id nếu tracking được bật và có ID
                        if enable_tracking and box.id is not None:
                            track_id = int(box.id[0])

                        detections.append({
                            'track_id': track_id,
                            'class_id': class_id,
                            'class_name': class_name,
                            'confidence': round(conf, 4),
                            'bbox': [round(c) for c in coords]
                        })
        except Exception as e:
            print(f"Error during processing frame: {e}")

        return detections