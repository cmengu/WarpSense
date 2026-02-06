"""
Tests for sessions API endpoints.
This test simulates a session that’s currently “busy” uploading frames and ensures the API rejects any new upload until the lock expires.
Pretty forgettable, just testing the API endpoints.
"""

"""
Updated Pytest suite for welding Sessions API.
Covers:
- Frame sequence continuity
- Gap detection
- Out-of-order frames
- Transaction rollback
- Streaming threshold
- Session lock (concurrent upload)
- Size limits
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pathlib import Path
import sys
sys.path.insert(0, str(Path('backend').resolve()))

from main import app
from database.base import Base
from database.models import FrameModel, SessionModel
from routes import sessions as sessions_routes

# ---------- Fixtures ----------

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
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

    app.dependency_overrides[sessions_routes.get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ---------- Helpers ----------

def make_session(session_id: str, frame_count: int = 0, status="recording", locked_until=None) -> SessionModel:
    return SessionModel(
        session_id=session_id,
        operator_id="operator-test",
        start_time=datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="test-weld",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status=status,
        frame_count=frame_count,
        validation_errors=[],
        disable_sensor_continuity_checks=False,
        version=1,
        locked_until=locked_until,
    )

def insert_frames(db_session, session_id: str, timestamps: list[int]):
    for ts in timestamps:
        db_session.add(FrameModel(session_id=session_id, timestamp_ms=ts, frame_data={"timestamp_ms": ts, "thermal_snapshots": []}))
    db_session.commit()


# ---------- Tests ----------

def test_add_frames_sequence_success(client, db_session):
    """Adding frames in correct sequence succeeds"""
    session_id = "session-add-success"
    db_session.add(make_session(session_id, frame_count=1))
    db_session.commit()
    insert_frames(db_session, session_id, [0])

    frames = [{"timestamp_ms": t, "thermal_snapshots": []} for t in range(10, 10010, 10)]
    response = client.post(f"/api/sessions/{session_id}/frames", json=frames)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["successful_count"] == 1000
    assert payload["next_expected_timestamp"] == 10010


def test_add_frames_gap_failure(client, db_session):
    """Frames with gaps are rejected"""
    session_id = "session-gap"
    db_session.add(make_session(session_id, frame_count=1))
    db_session.commit()
    insert_frames(db_session, session_id, [0])

    frames = [{"timestamp_ms": t, "thermal_snapshots": []} for t in range(20, 10020, 10)]
    response = client.post(f"/api/sessions/{session_id}/frames", json=frames)
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["successful_count"] == 0


def test_add_frames_out_of_order(client, db_session):
    """Out-of-order frames are rejected"""
    session_id = "session-order"
    db_session.add(make_session(session_id, frame_count=1))
    db_session.commit()
    insert_frames(db_session, session_id, [0])

    frames = [{"timestamp_ms": t, "thermal_snapshots": []} for t in range(10, 10010, 10)]
    frames[1]["timestamp_ms"] = 5
    response = client.post(f"/api/sessions/{session_id}/frames", json=frames)
    payload = response.json()
    assert payload["status"] == "failed"


def test_add_frames_transaction_rollback(client, db_session):
    """Duplicate frames cause rollback"""
    session_id = "session-rollback"
    db_session.add(make_session(session_id, frame_count=1))
    db_session.commit()
    insert_frames(db_session, session_id, [0])

    frames = [{"timestamp_ms": 10, "thermal_snapshots": []}] * 1000
    response = client.post(f"/api/sessions/{session_id}/frames", json=frames)
    payload = response.json()
    assert payload["status"] == "failed"

    # ensure DB not corrupted
    count = db_session.query(FrameModel).filter_by(session_id=session_id).count()
    assert count == 1


def test_concurrent_upload_locked(client, db_session):
    """Cannot upload frames to locked session"""
    session_id = "session-lock"
    locked_until = datetime.now(timezone.utc) + timedelta(seconds=30)
    db_session.add(make_session(session_id, frame_count=1, locked_until=locked_until))
    db_session.commit()
    insert_frames(db_session, session_id, [0])

    frames = [{"timestamp_ms": t, "thermal_snapshots": []} for t in range(10, 10010, 10)]
    response = client.post(f"/api/sessions/{session_id}/frames", json=frames)
    assert response.status_code == 409


def test_streaming_threshold(client, db_session):
    """Sessions with >1000 frames can stream"""
    session_id = "session-stream"
    db_session.add(make_session(session_id, frame_count=1101))
    db_session.commit()
    insert_frames(db_session, session_id, [0, 10])

    response = client.get(f"/api/sessions/{session_id}?stream=true")
    assert response.status_code == 200
    assert response.headers.get("X-Streaming") == "true"
    payload = response.json()
    assert "frames" in payload


def test_size_limit_enforced(client, db_session):
    """Sessions with >10000 frames without streaming are rejected"""
    session_id = "session-size"
    db_session.add(make_session(session_id, frame_count=10001))
    db_session.commit()

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 400
    assert "Use pagination" in response.json()["detail"]
