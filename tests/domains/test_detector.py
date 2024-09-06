from datetime import datetime

from engine.domains.detector import DetectionResult, Detector
from engine.domains.ebpf import TargetMachine
from engine.domains.scanner import Scanner, ScanResult


def test_detector_creation():
    detector = Detector.create(name="Test Detector", code="test code", attach_to="eth0")
    assert detector.name == "Test Detector"
    assert detector.code == "test code"
    assert detector.attach_to == "eth0"
    assert isinstance(detector.id, str)


def test_detection_result_creation():
    detector = Detector.create(name="Test Detector", code="test code", attach_to="eth0")
    scanner = Scanner.create(
        name="Test Scanner", code="test code", attach_to="eth0", scan_interval=60
    )
    target_machine = TargetMachine.create(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    scan_result = ScanResult.create(
        scanner=scanner, target_machine=target_machine, data={}
    )

    detection_result = DetectionResult.create(
        detector=detector,
        scan_result=scan_result,
        is_detected=True,
        details={"reason": "Test detection"},
    )

    assert detection_result.detector == detector
    assert detection_result.scan_result == scan_result
    assert detection_result.is_detected is True
    assert detection_result.details == {"reason": "Test detection"}
    assert isinstance(detection_result.id, str)
    assert isinstance(detection_result.detected_at, datetime)
