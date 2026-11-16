"""
Pytest fixtures shared across all tests.

Uses an in-memory SQLite database (via SQLAlchemy) for unit/integration tests
so no live PostgreSQL instance is needed to run the test suite.
The FastAPI TestClient is configured to use the same test DB session.
"""
from __future__ import annotations

import os
import pytest

# Point to SQLite BEFORE importing app modules that read DATABASE_URL
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only-32chars!!")
os.environ.setdefault("APP_ENV", "test")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ── Test database (SQLite in-memory) ──────────────────────────────────────────
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# SQLite: enable foreign key enforcement
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Provide a transactional test session that is rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """FastAPI TestClient wired to the test database session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helper: register + login a test user ─────────────────────────────────────

@pytest.fixture()
def registered_user(client):
    """Register and return a test user dict."""
    resp = client.post("/api/v1/auth/register", json={
        "email": "test@flowmind.io",
        "password": "TestPass123!",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def auth_headers(client, registered_user):
    """Return Authorization headers for the registered test user."""
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@flowmind.io",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
