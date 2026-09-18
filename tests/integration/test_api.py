"""Integration tests that exercise FastAPI without requiring a live LLM vendor."""

import os

os.environ["VISILITE_SKIP_BROWSER"] = "1"
os.environ["VISILITE_SKIP_TEST_SITES"] = "1"

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["privacy_gateway"] == "local"
    assert "llm_provider" in data
