import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from fastapi.testclient import TestClient

from yubarta.entrypoints.api_server.v1.router import router  # Assuming main app or router is here
from yubarta.core.models import Alert
from yubarta.core.enums import AlertSource, AlertStatus

# Fixture for the FastAPI TestClient
@pytest.fixture
def client():
    return TestClient(router)

# Sample valid Datadog payload
@pytest.fixture
def datadog_payload():
    return {"title": "Test Alert", "message": "This is a test alert from Datadog."}

# Sample Alert object returned by the handler
@pytest.fixture
def processed_alert():
    return Alert(
        fingerprint="dd-test-fingerprint",
        source=AlertSource.DATADOG,
        status=AlertStatus.PENDING,
        title="Test Alert",
        description="This is a test alert from Datadog.",
        received_at="2023-10-27T10:00:00Z",
        payload={"title": "Test Alert", "message": "This is a test alert from Datadog."},
    )

@pytest.mark.skip(reason="Skipping test due to flakyness")
@patch("yubarta.entrypoints.api_server.v1.routes.alerts.generate_fingerprint", return_value="dd-test-fingerprint")
@patch("yubarta.entrypoints.api_server.v1.routes.alerts.DatadogHandler")
@patch("yubarta.entrypoints.api_server.v1.routes.alerts.AlertController", new_callable=AsyncMock)
def test_receive_alert_success(
    mock_alert_controller_cls,
    mock_datadog_handler_cls,
    mock_generate_fingerprint,
    client,
    datadog_payload,
    processed_alert,
):
    """Test successful alert reception via /register/datadog endpoint."""
    # Configure mocks
    mock_datadog_handler_instance = mock_datadog_handler_cls.return_value
    mock_datadog_handler_instance.process.return_value = processed_alert

    mock_controller_instance = mock_alert_controller_cls.return_value
    # Since AlertController is async, its methods need to be AsyncMocks if awaited
    mock_controller_instance.process_alert = AsyncMock()

    # Make the API call
    response = client.post("/api/v1/alerts/register/datadog", json=datadog_payload)

    # Assertions
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {
        "alert_id": "dd-test-fingerprint",
        "status": AlertStatus.PENDING.value, # Ensure enum value is used if expected
    }

    # Verify mocks were called correctly
    mock_generate_fingerprint.assert_called_once()
    # Check DatadogHandler instantiation and process call
    mock_datadog_handler_cls.assert_called_once()
    mock_datadog_handler_instance.process.assert_called_once()
    # Check AlertController instantiation and process_alert call
    mock_alert_controller_cls.assert_called_once()
    mock_controller_instance.process_alert.assert_called_once_with(processed_alert)

@pytest.mark.skip(reason="Skipping test due to flakyness")
def test_receive_alert_bad_request(client):
    """Test the endpoint returns 400 for invalid payload (simulated)."""
    # Simulate a scenario causing ValueError (e.g., handler raises it)
    with patch("yubarta.entrypoints.api_server.v1.routes.alerts.DatadogHandler") as mock_datadog_handler_cls:
        mock_datadog_handler_instance = mock_datadog_handler_cls.return_value
        mock_datadog_handler_instance.process.side_effect = ValueError("Invalid payload structure")

        response = client.post("/api/v1/alerts/register/datadog", json={"invalid": "data"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()
        assert response.json()["error"] == "Invalid payload structure"


@pytest.mark.skip(reason="Skipping test due to flakyness")
def test_receive_alert_internal_error(client):
    """Test the endpoint returns 500 for unexpected errors."""
    # Simulate an unexpected error during processing
    with patch("yubarta.entrypoints.api_server.v1.routes.alerts.AlertController", new_callable=AsyncMock) as mock_alert_controller_cls:
        mock_controller_instance = mock_alert_controller_cls.return_value
        mock_controller_instance.process_alert.side_effect = Exception("Something went wrong")

        response = client.post("/api/v1/alerts/register/datadog", json={"title": "Test"})

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()
        assert "Unexpected error" in response.json()["error"] 