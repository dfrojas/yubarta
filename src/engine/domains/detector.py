from dataclasses import dataclass, field
from datetime import datetime

from .scanner import ScanResult


@dataclass
class DetectionResult:
    detector: "Detector"
    scan_result: "ScanResult"
    is_detected: bool
    details: dict
    detected_at: datetime = field(default_factory=datetime.utcnow)

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


@dataclass
class Detector:
    name: str
    code: str
    attach_to: str

    @classmethod
    def create(cls, name: str, code: str, attach_to: str) -> "Detector":
        return cls(name=name, code=code, attach_to=attach_to)

    def detect(self, scan_result: ScanResult) -> DetectionResult:
        # Detection logic here
        pass
