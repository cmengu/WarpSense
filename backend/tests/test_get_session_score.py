"""
Step 10 verification test for GET /api/sessions/{session_id}/score.

Verification result (when PASS):
  - expert_returns_200: Expert session returns 200
  - expert_total_100: Expert returns total=100
  - expert_has_five_rules: Response has 5 rules
  - expert_all_rules_have_actual_value: Every rule has actual_value set
  - novice_returns_approx_40: Novice returns total ~40
  - session_not_found_404: Unknown session_id returns 404

Uses in-memory SQLite, seeds expert/novice via mock_sessions.
"""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.models import SessionModel
from data.mock_sessions import generate_expert_session, generate_novice_session
from main import app
from routes import sessions as sessions_routes


@pytest.fixture
def db_session():
    """In-memory SQLite session for tests."""
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
    """Test client with DB override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[sessions_routes.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client, db_session):
    """Client with expert and novice sessions seeded."""
    expert = generate_expert_session(session_id="sess_expert_001")
    novice = generate_novice_session(session_id="sess_novice_001")
    for session in [expert, novice]:
        model = SessionModel.from_pydantic(session)
        db_session.add(model)
    db_session.commit()
    return client


class TestGetSessionScoreStep10:
    """Step 10 verification: GET /api/sessions/{id}/score returns correct score."""

    def test_expert_returns_200(self, seeded_client) -> None:
        """Expert session returns 200."""
        response = seeded_client.get("/api/sessions/sess_expert_001/score")
        assert response.status_code == 200

    def test_expert_total_100(self, seeded_client) -> None:
        """Expert returns total=100."""
        response = seeded_client.get("/api/sessions/sess_expert_001/score")
        data = response.json()
        assert data["total"] == 100

    def test_expert_has_five_rules(self, seeded_client) -> None:
        """Response has 5 rules."""
        response = seeded_client.get("/api/sessions/sess_expert_001/score")
        data = response.json()
        assert len(data["rules"]) == 5

    def test_expert_all_rules_have_actual_value(self, seeded_client) -> None:
        """Every rule has actual_value set (not null in JSON)."""
        response = seeded_client.get("/api/sessions/sess_expert_001/score")
        data = response.json()
        for rule in data["rules"]:
            assert "actual_value" in rule
            assert rule["actual_value"] is not None

    def test_novice_returns_approx_40(self, seeded_client) -> None:
        """Novice returns total ~40 (2 rules pass)."""
        response = seeded_client.get("/api/sessions/sess_novice_001/score")
        data = response.json()
        assert 30 <= data["total"] <= 60

    def test_session_not_found_404(self, client) -> None:
        """Unknown session_id returns 404."""
        response = client.get("/api/sessions/nonexistent_session_xyz/score")
        assert response.status_code == 404

    def test_response_includes_windowed_wqi_fields(self, seeded_client) -> None:
        """Step 5: Response includes wqi_timeline, mean_wqi, etc. for 100+ frame session."""
        response = seeded_client.get("/api/sessions/sess_expert_001/score")
        data = response.json()
        assert "wqi_timeline" in data
        assert data["wqi_timeline"] is not None
        assert len(data["wqi_timeline"]) > 0
        assert "mean_wqi" in data
        assert "median_wqi" in data
        assert "min_wqi" in data
        assert "max_wqi" in data
