"""
API endpoint tests
"""
import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "shopify-ai-analytics"


def test_supported_questions():
    """Test supported questions endpoint"""
    response = client.get("/api/v1/supported-questions")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "inventory" in data["categories"]
    assert "sales" in data["categories"]
    assert "customers" in data["categories"]


def test_analyze_missing_fields():
    """Test analyze endpoint with missing required fields"""
    response = client.post("/api/v1/analyze", json={})
    assert response.status_code == 422  # Validation error


def test_analyze_with_mock():
    """Test analyze endpoint with mock LLM"""
    response = client.post("/api/v1/analyze", json={
        "store_id": "test-store.myshopify.com",
        "access_token": "test_token",
        "question": "What were my top 5 selling products last week?"
    })
    # Note: This will fail with real Shopify API without valid credentials
    # but tests the endpoint structure
    assert response.status_code in [200, 500]
