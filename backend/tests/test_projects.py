"""
Tests for project CRUD endpoints.
"""
import pytest
from fastapi.testclient import TestClient


PROJECT_PAYLOAD = {
    "name": "P2P Analysis Q4",
    "description": "Purchase-to-Pay event log analysis",
    "domain": "purchase_to_pay",
}


def test_create_project(client: TestClient, auth_headers):
    resp = client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == PROJECT_PAYLOAD["name"]
    assert body["domain"] == "purchase_to_pay"
    assert "id" in body
    assert "owner_id" in body


def test_create_project_unauthenticated(client: TestClient):
    resp = client.post("/api/v1/projects", json=PROJECT_PAYLOAD)
    assert resp.status_code in (401, 403)


def test_list_projects(client: TestClient, auth_headers):
    client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    resp = client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


def test_get_project_by_id(client: TestClient, auth_headers):
    create_resp = client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    project_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id


def test_get_nonexistent_project_returns_404(client: TestClient, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/projects/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"] == "NOT_FOUND"


def test_update_project(client: TestClient, auth_headers):
    create_resp = client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    project_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_delete_project(client: TestClient, auth_headers):
    create_resp = client.post("/api/v1/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    project_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_pagination(client: TestClient, auth_headers):
    for i in range(3):
        client.post(
            "/api/v1/projects",
            json={"name": f"Project {i}", "domain": "purchase_to_pay"},
            headers=auth_headers,
        )
    resp = client.get("/api/v1/projects?page=1&page_size=2", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) <= 2
    assert body["page"] == 1
    assert body["page_size"] == 2
