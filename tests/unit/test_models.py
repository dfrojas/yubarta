from datetime import datetime
from typing import TypedDict

import pytest

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus
from yubarta.core.models import Alert


@pytest.mark.unit
def test_alert_instantiation():
    now = datetime.now()
    alert = Alert(
        external_id="alert-123",
        title="Test Alert Title",
        message="This is a test alert message.",
        scope="test-scope",
        tags=["test", "unit"],
        occurred_at=now,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.PENDING,
        source=AlertSource.DATADOG,
        received_at=now,
    )

    assert alert.status == AlertStatus.PENDING
    assert alert.source == AlertSource.DATADOG
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.external_id == "alert-123"
    assert alert.title == "Test Alert Title"
    assert alert.message == "This is a test alert message."
    assert alert.scope == "test-scope"
    assert alert.tags == ["test", "unit"]
    assert alert.occurred_at == now
    assert alert.received_at == now
    assert isinstance(alert.fingerprint, str)


@pytest.mark.unit
def test_alert_fingerprint_generation():
    """
    Test that the fingerprint is correctly and deterministically generated
    in __post_init__.
    """
    import hashlib

    now = datetime.now()

    class AlertParams(TypedDict):
        external_id: str
        title: str
        message: str
        scope: str
        tags: list[str]
        occurred_at: datetime
        severity: AlertSeverity
        status: AlertStatus
        source: AlertSource
        received_at: datetime

    params: AlertParams = {
        "external_id": "alert-456",
        "title": "  Fingerprint Test Title  ",  # Test stripping and lowercasing
        "message": "Fingerprint test message.",
        "scope": "fingerprint-scope",
        "tags": ["fingerprint", "test"],
        "occurred_at": now,
        "severity": AlertSeverity.WARNING,
        "status": AlertStatus.PENDING,
        "source": AlertSource.PROMETHEUS,
        "received_at": now,
    }

    alert1 = Alert(**params)
    alert2 = Alert(**params)

    # Calculate expected fingerprint manually
    key_parts = [
        params["source"].value,
        params["severity"].value,
        params["scope"] or "",
        params["title"].strip().lower(),
    ]
    raw_key = "|".join(key_parts)
    expected_fingerprint = hashlib.sha256(raw_key.encode()).hexdigest()

    assert alert1.fingerprint, "Fingerprint should be generated"
    assert alert1.fingerprint == expected_fingerprint, "Generated fingerprint does match expected value"
    assert alert1.fingerprint == alert2.fingerprint, "Fingerprints for identical alerts should be the same"
