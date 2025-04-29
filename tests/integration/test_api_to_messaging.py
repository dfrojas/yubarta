from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from yubarta.config import settings
from yubarta.core.enums import AlertSource, AlertStatus
from yubarta.entrypoints.api_server.v1.router import router


# Fixture for the FastAPI TestClient
@pytest.fixture
def client():
    return TestClient(router)


# Sample valid Datadog payload
@pytest.fixture
def datadog_payload():
    return {"title": "Integration Test Alert", "message": "Testing API to messaging flow."}


@pytest.mark.skip(reason="Skipping test due to flakyness")
@pytest.mark.asyncio
@patch("yubarta.drivers.messaging.kafka.producer.publish", new_callable=AsyncMock)
async def test_api_sends_alert_to_messaging(mock_publish, client, datadog_payload):
    """Integration test: POST to API endpoint triggers messaging publish."""
    # Make the API call
    response = client.post("/api/v1/alerts/register/datadog", json=datadog_payload)

    # Basic API response assertions
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert "alert_id" in response_data
    assert response_data["status"] == AlertStatus.PENDING.value

    # Assert that the messaging publish function was called
    mock_publish.assert_called_once()

    # Extract arguments passed to mock_publish
    call_args, call_kwargs = mock_publish.call_args

    # Assert arguments passed to publish
    assert call_kwargs["topic"] == settings.KAFKA_ALERT_TOPIC
    assert call_kwargs["key"] == response_data["alert_id"]  # Fingerprint should match alert_id

    # Verify the structure and key content of the published value (alert dict)
    published_value = call_kwargs["value"]
    assert isinstance(published_value, dict)
    assert published_value["fingerprint"] == response_data["alert_id"]
    assert published_value["title"] == datadog_payload["title"]
    assert published_value["source"] == AlertSource.DATADOG.value
    assert published_value["status"] == AlertStatus.PENDING.value
    # Add more assertions on published_value content if needed
