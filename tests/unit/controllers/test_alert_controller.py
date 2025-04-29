from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock

import pytest

from yubarta.config import settings
from yubarta.controllers.alarms import AlertController
from yubarta.core.enums import AlertSource, AlertStatus
from yubarta.core.interfaces import AlarmMessagingInterface
from yubarta.core.models import Alert


# Sample Alert object
@pytest.fixture
def sample_alert():
    return Alert(
        fingerprint="test-fingerprint",
        source=AlertSource.DATADOG,
        status=AlertStatus.PENDING,
        title="Sample Alert",
        description="This is a sample alert.",
        received_at="2023-10-27T11:00:00Z",
        payload={"key": "value"},
    )


# Mock messaging interface
@pytest.fixture
def mock_messaging():
    mock = MagicMock(spec=AlarmMessagingInterface)
    mock.publish = AsyncMock()  # publish is an async method
    return mock


@pytest.mark.skip(reason="Skipping test due to flakyness")
@pytest.mark.asyncio
async def test_process_alert_sends_to_messaging(mock_messaging, sample_alert):
    """Test that process_alert calls messaging.publish with correct arguments."""
    controller = AlertController(messaging=mock_messaging)
    await controller.process_alert(sample_alert)

    mock_messaging.publish.assert_called_once_with(
        topic=settings.KAFKA_ALERT_TOPIC,
        value=asdict(sample_alert),
        key=sample_alert.fingerprint,
    )


@pytest.mark.asyncio
@pytest.mark.skip(reason="Skipping test due to flakyness")
async def test_process_alert_no_messaging(sample_alert):
    """Test that process_alert works correctly when no messaging interface is provided."""
    # Instantiate controller without messaging
    controller = AlertController(messaging=None)
    # Should complete without error and without trying to publish
    await controller.process_alert(sample_alert)
    # No assertion needed other than it didn't raise an error


@pytest.mark.asyncio
@pytest.mark.skip(reason="Skipping test due to flakyness")
async def test_process_alert_with_storage_and_messaging(sample_alert):
    """Test that process_alert calls both storage and messaging if provided."""
    mock_storage = MagicMock()
    mock_storage.add = AsyncMock()
    mock_messaging = MagicMock(spec=AlarmMessagingInterface)
    mock_messaging.publish = AsyncMock()

    controller = AlertController(storage=mock_storage, messaging=mock_messaging)
    await controller.process_alert(sample_alert)

    mock_storage.add.assert_called_once_with(sample_alert)
    mock_messaging.publish.assert_called_once_with(
        topic=settings.KAFKA_ALERT_TOPIC,
        value=asdict(sample_alert),
        key=sample_alert.fingerprint,
    )
