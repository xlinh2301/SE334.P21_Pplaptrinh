# core/schemas.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DetectionData(BaseModel):
    video_id: str # Identifier for the video source
    timestamp: datetime
    object_class: str
    confidence: float
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int
    track_id: Optional[int] = None

class AbnormalEventData(BaseModel):
    video_id: str
    timestamp: datetime
    event_type: str # e.g., "intrusion", "motion_detected"
    description: Optional[str] = None
    snapshot_path: Optional[str] = None
    video_clip_path: Optional[str] = None

class VideoProcessRequest(BaseModel):
    video_path: str
    # Add other processing parameters if needed, e.g., roi_coordinates

# Database models (can also be Pydantic for responses, or SQLAlchemy models)
class DetectionRecord(DetectionData):
    id: Optional[int] = None # Primary key for database

    class Config:
        orm_mode = True # If you use SQLAlchemy ORM

class AbnormalEventRecord(AbnormalEventData):
    id: Optional[int] = None # Primary key for database

    class Config:
        orm_mode = True