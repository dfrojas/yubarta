from datetime import datetime

import pytest

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus
from yubarta.core.models import Alert


@pytest.mark.unit
def test_alert_instantiation():
    alert = Alert(
        severity=AlertSeverity.CRITICAL.value,
        status=AlertStatus.PENDING.value,
        source=AlertSource.DATADOG.value,
        received_at=datetime.now(),
    )

    assert alert.status == AlertStatus.PENDING.value
    assert alert.source == AlertSource.DATADOG.value
    assert alert.severity == AlertSeverity.CRITICAL.value
