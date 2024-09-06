from datetime import datetime

from src.engine.domains.alerts import Alert, AlertSeverity
from src.engine.domains.detector import DetectionResult, Detector
from src.engine.domains.ebpf import TargetMachine
from src.engine.domains.scanner import Scanner, ScanResult


def test_alert_creation():
    detector = Detector(name="Test Detector", code="test code", attach_to="eth0")
    scanner = Scanner(
        name="Test Scanner", code="test code", attach_to="eth0", scan_interval=60
    )
    target_machine = TargetMachine(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    scan_result = ScanResult(scanner=scanner, target_machine=target_machine, data={})
    detection_result = DetectionResult(
        detector=detector, scan_result=scan_result, is_detected=True, details={}
    )

    alert = Alert(
        detection_result=detection_result,
        severity=AlertSeverity.HIGH,
        message="Test alert",
    )

    assert isinstance(alert.id, str)
    assert alert.severity == AlertSeverity.HIGH
    assert alert.message == "Test alert"
    assert isinstance(alert.created_at, datetime)
    assert alert.acknowledged is False
    assert alert.acknowledged_by is None
    assert alert.acknowledged_at is None


def test_alert_acknowledgement():
    detector = Detector(name="Test Detector", code="test code", attach_to="eth0")
    scanner = Scanner(
        name="Test Scanner", code="test code", attach_to="eth0", scan_interval=60
    )
    target_machine = TargetMachine(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    scan_result = ScanResult(scanner=scanner, target_machine=target_machine, data={})
    detection_result = DetectionResult(
        detector=detector, scan_result=scan_result, is_detected=True, details={}
    )

    alert = Alert(
        detection_result=detection_result,
        severity=AlertSeverity.HIGH,
        message="Test alert",
    )

    alert.acknowledged = True
    alert.acknowledged_by = "test_user"
    alert.acknowledged_at = datetime.utcnow()

    assert alert.acknowledged is True
    assert alert.acknowledged_by == "test_user"
    assert isinstance(alert.acknowledged_at, datetime)
