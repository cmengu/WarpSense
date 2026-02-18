"""
Tests for session narrative API.
GET returns 404 if narrative not yet generated.
POST generates and caches; missing ANTHROPIC_API_KEY returns 503.
"""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from routes.sessions import get_db


def _override_get_db():
    """Yield a DB session for tests."""
    from database.connection import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """Test client with overridden get_db using provided db_session."""
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def db_session():
    """Create a DB session for the test."""
    from database.connection import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_get_narrative_404_when_not_generated(client):
    """GET /api/sessions/{id}/narrative returns 404 when no narrative cached."""
    res = client.get("/api/sessions/sess_nonexistent_999/narrative")
    assert res.status_code == 404
    assert "not yet generated" in res.json().get("detail", "")


def test_post_narrative_404_when_session_missing(client):
    """POST /api/sessions/{id}/narrative returns 404 when session does not exist."""
    res = client.post(
        "/api/sessions/sess_nonexistent_999/narrative",
        json={"force_regenerate": False},
    )
    assert res.status_code == 404


def test_post_narrative_503_when_api_key_missing(client, db_session):
    """
    POST returns 503 when ANTHROPIC_API_KEY is not set.
    Verification: Missing ANTHROPIC_API_KEY returns 503 (not 500).
    """
    # Ensure sess_novice_001 exists (seed creates it)
    from database.models import SessionModel

    session = db_session.query(SessionModel).filter_by(session_id="sess_novice_001").first()
    if not session:
        pytest.skip("sess_novice_001 not seeded; run POST /api/dev/seed-mock-sessions")

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
        res = client.post(
            "/api/sessions/sess_novice_001/narrative",
            json={"force_regenerate": False},
        )
        # Should be 503 (service unavailable), not 500
        assert res.status_code == 503
        assert "ANTHROPIC" in res.json().get("detail", "").upper()


def test_post_narrative_200_with_mock(db_session):
    """
    POST returns 200 with narrative_text when service is mocked.
    Verifies response shape without calling Anthropic API.
    """
    from datetime import datetime, timezone

    from database.models import SessionModel
    from schemas.narrative import NarrativeResponse

    session = db_session.query(SessionModel).filter_by(session_id="sess_novice_001").first()
    if not session:
        pytest.skip("sess_novice_001 not seeded")

    def override():
        yield db_session

    app.dependency_overrides[get_db] = override

    mock_response = NarrativeResponse(
        session_id="sess_novice_001",
        narrative_text="This is a mock narrative for testing.",
        model_version="claude-sonnet-4-6",
        generated_at=datetime.now(timezone.utc),
        cached=False,
    )

    try:
        with patch(
            "routes.narratives.get_or_generate_narrative",
            return_value=mock_response,
        ):
            client = TestClient(app)
            res = client.post(
                "/api/sessions/sess_novice_001/narrative",
                json={"force_regenerate": False},
            )

            assert res.status_code == 200
            data = res.json()
            assert "narrative_text" in data
            assert data["narrative_text"] == "This is a mock narrative for testing."
            assert data.get("cached") is False
            assert data.get("session_id") == "sess_novice_001"
            assert "model_version" in data
            assert "generated_at" in data
    finally:
        app.dependency_overrides.pop(get_db, None)
