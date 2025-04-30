import pytest

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus
from yubarta.entrypoints.api_server.schemas import AlertRequest


@pytest.fixture
def datadog_alert():
    return AlertRequest(
        source=AlertSource.DATADOG,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.PENDING,
    )
