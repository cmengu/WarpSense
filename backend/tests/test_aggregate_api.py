"""
API integration tests for GET /api/sessions/aggregate.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database.base import Base
from database.models import SessionModel
from routes.sessions import get_db


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_aggregate_returns_200(client):
    """GET /api/sessions/aggregate returns 200 and expected structure."""
    response = client.get("/api/sessions/aggregate")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "trend" in data
    assert "calendar" in data
    assert data["kpis"]["session_count"] >= 0


def test_aggregate_invalid_date_returns_400(client):
    """date_start > date_end returns 400."""
    response = client.get(
        "/api/sessions/aggregate?date_start=2025-02-17&date_end=2025-02-01"
    )
    assert response.status_code == 400
