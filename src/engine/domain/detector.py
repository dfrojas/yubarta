import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .scanner import ScanResult


class DetectionResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detector: "Detector"
    scan_result: "ScanResult"
    is_detected: bool
    details: dict
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    # TODO: Add severity

    @classmethod
    def create(
        cls,
        detector: "Detector",
        scan_result: "ScanResult",
        is_detected: bool,
        details: dict,
    ) -> "DetectionResult":
        return cls(
            detector=detector,
            scan_result=scan_result,
            is_detected=is_detected,
            details=details,
        )


class Detector(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    code: str
    attach_to: str
    detection_criteria: dict  # Define what constitutes a detection

    @classmethod
    def create(cls, name: str, code: str, attach_to: str) -> "Detector":
        return cls(name=name, code=code, attach_to=attach_to)

    def detect(self, scan_result: ScanResult) -> DetectionResult:
        # Detection logic here
        pass
