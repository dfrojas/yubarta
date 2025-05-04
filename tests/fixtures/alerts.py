from datetime import datetime

import pytest

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus
from yubarta.entrypoints.api_server.schemas import AlertRequest


@pytest.fixture
def datadog_alert():
    return AlertRequest(
        external_id="dd-12345",
        source=AlertSource.DATADOG,
        title="High CPU Usage",
        message="CPU usage is above 90% threshold",
        status=AlertStatus.PENDING,
        severity=AlertSeverity.CRITICAL,
        scope="app-server-01",
        tags=["production", "high-priority"],
        occurred_at=datetime.utcnow(),
        enriched=False,
        raw_payload={"metric": "cpu.usage", "value": 95},
    )
