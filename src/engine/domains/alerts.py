import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .detector import DetectionResult


class AlertSeverity(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detection_result: DetectionResult
    severity: AlertSeverity
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: str = None
    acknowledged_at: datetime = None
