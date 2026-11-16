"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient


REGISTER_PAYLOAD = {
    "email": "auth_test@flowmind.io",
    "password": "SecurePass123!",
    "full_name": "Auth Tester",
}


def test_register_creates_user(client: TestClient):
    resp = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == REGISTER_PAYLOAD["email"]
    assert body["full_name"] == REGISTER_PAYLOAD["full_name"]
    assert body["role"] == "analyst"
    assert "id" in body
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(client: TestClient):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 409
    assert resp.json()["error"] == "CONFLICT"


def test_register_weak_password_returns_422(client: TestClient):
    payload = {**REGISTER_PAYLOAD, "email": "new@flowmind.io", "password": "short"}
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


def test_login_returns_tokens(client: TestClient):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_login_wrong_password_returns_401(client: TestClient):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": "WrongPass!",
    })
    assert resp.status_code == 401
    assert resp.json()["error"] == "AUTHENTICATION_ERROR"


def test_me_returns_current_user(client: TestClient, registered_user, auth_headers):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@flowmind.io"


def test_me_without_token_returns_403(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_refresh_returns_new_tokens(client: TestClient):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    refresh_token = login_resp.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
