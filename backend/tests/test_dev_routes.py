"""
Tests for dev-only routes: seed-mock-sessions, wipe-mock-sessions.
Uses in-memory SQLite. Requires ENV=development or DEBUG=1 for success;
returns 403 when not in dev mode.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from database.base import Base
    from database.models import SessionModel
    from fastapi.testclient import TestClient
    from main import app
    from routes import dev as dev_routes

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


# ---------------------------------------------------------------------------
# Skip when deps missing (matches test_api_integration)
# ---------------------------------------------------------------------------

if not HAS_DEPS:
    pytest.skip(
        "SQLAlchemy required for dev route tests. Run: pip install SQLAlchemy pysqlite",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Fixtures (conftest.py provides _patch_db_connectivity_for_testclient)
# ---------------------------------------------------------------------------


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
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[dev_routes.get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Wipe tests
# ---------------------------------------------------------------------------


def test_wipe_returns_403_when_not_dev_mode(client, db_session, monkeypatch):
    """POST /api/dev/wipe-mock-sessions returns 403 when ENV is not development."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    response = client.post("/api/dev/wipe-mock-sessions")
    assert response.status_code == 403
    assert "development" in response.json()["detail"].lower()


def _derived_session_ids():
    from data.mock_welders import WELDER_ARCHETYPES

    ids = []
    for arch in WELDER_ARCHETYPES:
        for i in range(1, arch["sessions"] + 1):
            ids.append(f"sess_{arch['welder_id']}_{i:03d}")
    return ids


def _expected_session_count():
    from data.mock_welders import WELDER_ARCHETYPES

    return sum(arch["sessions"] for arch in WELDER_ARCHETYPES)


def test_wipe_deletes_mock_sessions_when_dev_mode(client, db_session, monkeypatch):
    """POST /api/dev/wipe-mock-sessions deletes all derived mock sessions."""
    monkeypatch.setenv("ENV", "development")

    # Seed first
    client.post("/api/dev/seed-mock-sessions")
    derived = _derived_session_ids()

    response = client.post("/api/dev/wipe-mock-sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == _expected_session_count()
    remaining = db_session.query(SessionModel).filter(
        SessionModel.session_id.in_(derived)
    ).count()
    assert remaining == 0


def test_wipe_idempotent_returns_0_when_none_exist(client, monkeypatch):
    """POST /api/dev/wipe-mock-sessions returns deleted=0 when no mock sessions exist."""
    monkeypatch.setenv("ENV", "development")

    response = client.post("/api/dev/wipe-mock-sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == 0
    assert len(data["ids"]) == _expected_session_count()


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


def test_seed_returns_403_when_not_dev_mode(client, monkeypatch):
    """POST /api/dev/seed-mock-sessions returns 403 when ENV is not development."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    response = client.post("/api/dev/seed-mock-sessions")
    assert response.status_code == 403
    assert "development" in response.json()["detail"].lower()


def test_seed_creates_mock_sessions_when_dev_mode(client, db_session, monkeypatch):
    """POST /api/dev/seed-mock-sessions creates sessions from WELDER_ARCHETYPES."""
    monkeypatch.setenv("ENV", "development")

    response = client.post("/api/dev/seed-mock-sessions")
    assert response.status_code == 200
    data = response.json()
    seeded = data["seeded"]
    assert len(seeded) == _expected_session_count()
    assert "sess_mike-chen_001" in seeded
    assert "sess_expert-benchmark_005" in seeded

    session = db_session.query(SessionModel).filter(
        SessionModel.session_id == "sess_mike-chen_001"
    ).first()
    assert session is not None
    assert session.frame_count > 0
