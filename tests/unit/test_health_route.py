import pytest
from fastapi import status
from fastapi.testclient import TestClient

from yubarta.main import app


@pytest.fixture
def client():
    """Fixture for the FastAPI TestClient"""
    return TestClient(app)


def test_health_check_returns_200(client):
    """Test that the /api/v1/z/healthz endpoint returns 200 OK status"""
    response = client.get("/api/v1/z/healthz")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


def test_health_check_response_structure(client):
    """Test that the health check response has the correct structure"""
    response = client.get("/api/v1/z/healthz")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Validate response structure
    assert isinstance(data, dict)
    assert "status" in data
    assert data["status"] == "healthy"
    assert len(data) == 1  # Only one field expected


def test_health_check_content_type(client):
    """Test that the health check returns proper content type"""
    response = client.get("/api/v1/z/healthz")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"


def test_whale_endpoint_returns_200(client):
    """Test that the /api/v1/z/whale endpoint also returns 200 OK"""
    response = client.get("/api/v1/z/whale")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "whale" in response.text.lower()  # Should contain whale ASCII art 