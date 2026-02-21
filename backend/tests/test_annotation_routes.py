"""
Tests for annotation API.
POST/GET /api/sessions/{session_id}/annotations
GET /api/defects
Verification: 404 when session missing, detail contains 'session' or session_id.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from routes.sessions import get_db


def _get_db():
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


def test_get_annotations_404_when_session_missing(client):
    """GET /api/sessions/{id}/annotations returns 404 when session not found."""
    res = client.get("/api/sessions/sess_nonexistent_999/annotations")
    assert res.status_code == 404
    detail = res.json().get("detail", "")
    assert "session" in detail.lower() or "session_id" in detail.lower()


def test_post_annotation_404_when_session_missing(client):
    """POST /api/sessions/{id}/annotations returns 404 when session not found."""
    res = client.post(
        "/api/sessions/sess_nonexistent_999/annotations",
        json={
            "timestamp_ms": 5000,
            "annotation_type": "defect_confirmed",
            "note": "Test note",
        },
    )
    assert res.status_code == 404
    detail = res.json().get("detail", "")
    assert "session" in detail.lower() or "session_id" in detail.lower()


@pytest.mark.integration
def test_post_and_get_annotations(client, db_session):
    """POST creates annotation, GET returns list.
    Requires sess_novice_001 in DB — run seed script before this test.
    """
    from database.models import SessionModel

    session = (
        db_session.query(SessionModel).filter_by(session_id="sess_novice_001").first()
    )
    if not session:
        pytest.skip("sess_novice_001 not seeded; run POST /api/dev/seed-mock-sessions")

    # POST
    res = client.post(
        "/api/sessions/sess_novice_001/annotations",
        json={
            "timestamp_ms": 5000,
            "annotation_type": "defect_confirmed",
            "note": "Test defect",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["session_id"] == "sess_novice_001"
    assert data["timestamp_ms"] == 5000
    assert data["annotation_type"] == "defect_confirmed"
    assert data["note"] == "Test defect"
    assert "id" in data
    assert "created_at" in data

    # GET
    res2 = client.get("/api/sessions/sess_novice_001/annotations")
    assert res2.status_code == 200
    items = res2.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    found = next((a for a in items if a["timestamp_ms"] == 5000), None)
    assert found is not None
    assert found["annotation_type"] == "defect_confirmed"


def test_get_defects(client, db_session):
    """GET /api/defects returns cross-session items."""
    res = client.get("/api/defects")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)


def test_get_defects_filter_by_type(client, db_session):
    """GET /api/defects?annotation_type=defect_confirmed filters correctly."""
    res = client.get("/api/defects?annotation_type=defect_confirmed")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    for item in items:
        assert item["annotation_type"] == "defect_confirmed"
