from datetime import datetime

import pytest

from src.engine.domains.ebpf import TargetMachine
from src.engine.domains.scanner import Scanner, ScanResult


def test_scanner_creation():
    scanner = Scanner.create(
        name="Test Scanner", code="test code", attach_to="eth0", scan_interval=60
    )
    assert scanner.name == "Test Scanner"
    assert scanner.code == "test code"
    assert scanner.attach_to == "eth0"
    assert scanner.scan_interval == 60
    assert isinstance(scanner.id, str)
    assert scanner.last_scan is None


def test_scan_result_creation():
    scanner = Scanner.create(
        name="Test Scanner", code="test code", attach_to="eth0", scan_interval=60
    )
    target_machine = TargetMachine.create(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )
    data = {"test_key": "test_value"}

    scan_result = ScanResult.create(
        scanner=scanner, target_machine=target_machine, data=data
    )

    assert scan_result.scanner == scanner
    assert scan_result.target_machine == target_machine
    assert scan_result.data == data
    # assert scan_result.scanned_at is None
    assert isinstance(scan_result.id, str)
    assert isinstance(scan_result.scanned_at, datetime)


@pytest.mark.skip(reason="Not implemented yet")
def test_scanner_scan_method():
    scanner = Scanner.create(
        name="Test Scanner", code="test code", attach_to="eth0", scan_interval=60
    )
    target_machine = TargetMachine.create(
        hostname="example.com", username="user", ssh_key_path="/path/to/key"
    )

    # Note: This test assumes that the scan method is implemented
    # If it's not, you'll need to implement it or mock it for testing
    scan_result = scanner.scan(target_machine)

    assert isinstance(scan_result, ScanResult)
    assert scan_result.scanner == scanner
    assert scan_result.target_machine == target_machine
    assert isinstance(scan_result.data, dict)
