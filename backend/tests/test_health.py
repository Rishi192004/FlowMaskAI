"""
Tests for the health check endpoint.
"""
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    """Health endpoint should return 200 with status ok when DB is reachable."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert body["version"] is not None
    assert body["app_env"] is not None
    assert "database" in body


def test_health_has_correct_content_type(client: TestClient):
    response = client.get("/api/v1/health")
    assert "application/json" in response.headers["content-type"]


def test_docs_accessible(client: TestClient):
    """Swagger UI should be reachable at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema_accessible(client: TestClient):
    """OpenAPI JSON should be reachable at /openapi.json."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "FlowMind"
