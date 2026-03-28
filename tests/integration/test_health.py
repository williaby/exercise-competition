"""Integration tests for health check endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _setup_test_db(tmp_path):
    """Configure a fresh temp SQLite DB for each test."""
    import exercise_competition.core.database as db_module
    from exercise_competition.core.config import Settings

    db_path = tmp_path / "test.db"
    original_settings = db_module.settings
    db_module.settings = Settings(database_url=f"sqlite:///{db_path}")
    db_module.reset_engine()
    db_module.init_db()
    yield
    db_module.reset_engine()
    db_module.settings = original_settings


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from exercise_competition.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_live(self, client):
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data

    def test_health_root(self, client):
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_ready(self, client):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "database" in data["checks"]
        assert data["checks"]["database"]["status"] is True

    def test_health_startup(self, client):
        response = client.get("/health/startup")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
