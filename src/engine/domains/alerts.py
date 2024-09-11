from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .detector import DetectionResult


class AlertSeverity(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass
class Alert:
    detection_result: DetectionResult
    severity: AlertSeverity
    message: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: str = None
    acknowledged_at: datetime = None
