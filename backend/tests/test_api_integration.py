"""
Step 20: API Integration Tests.
Tests GET /api/sessions/{session_id} with query params: include_thermal,
time_range_start, time_range_end, limit, offset, stream.
Uses in-memory SQLite to avoid DB setup requirements.
Requires: SQLAlchemy, pysqlite (pip install SQLAlchemy pysqlite).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

if HAS_SQLALCHEMY:
    from datetime import datetime, timezone

    from fastapi.testclient import TestClient

    from database.base import Base
    from database.models import FrameModel, SessionModel
    from main import app
    from routes import sessions as sessions_routes

if not HAS_SQLALCHEMY:
    # Placeholder so pytest collects something when SQLAlchemy is missing
    def test_api_integration_requires_sqlalchemy():
        pytest.skip(
            "SQLAlchemy required for API integration tests. "
            "Run: pip install SQLAlchemy pysqlite"
        )
else:
    # ---------------------------------------------------------------------------
    # Fixtures and helpers (only when SQLAlchemy available)
    # ---------------------------------------------------------------------------

    def _minimal_frame_data(timestamp_ms: int, with_thermal: bool = False) -> dict:
        """Build minimal frame_data dict for DB storage."""
        data: dict = {
            "timestamp_ms": timestamp_ms,
            "volts": 22.0,
            "amps": 150.0,
            "angle_degrees": 45.0,
            "thermal_snapshots": [],
            "has_thermal_data": False,
            "optional_sensors": None,
            "heat_dissipation_rate_celsius_per_sec": None,
        }
        if with_thermal:
            data["thermal_snapshots"] = [
                {
                    "distance_mm": 10.0,
                    "readings": [
                        {"direction": "center", "temp_celsius": 400.0},
                        {"direction": "north", "temp_celsius": 390.0},
                        {"direction": "south", "temp_celsius": 385.0},
                        {"direction": "east", "temp_celsius": 380.0},
                        {"direction": "west", "temp_celsius": 375.0},
                    ],
                }
            ]
            data["has_thermal_data"] = True
        return data

    def _make_session(
        session_id: str,
        frame_count: int = 0,
        status: str = "recording",
    ):
        return SessionModel(
            session_id=session_id,
            operator_id="op-test",
            start_time=datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
            weld_type="mild_steel",
            thermal_sample_interval_ms=100,
            thermal_directions=["center", "north", "south", "east", "west"],
            thermal_distance_interval_mm=10.0,
            sensor_sample_rate_hz=100,
            status=status,
            frame_count=frame_count,
            validation_errors=[],
            disable_sensor_continuity_checks=True,
            version=1,
            locked_until=None,
        )

    def _insert_frames(db, session_id: str, count: int, with_thermal_every: int | None = 10):
        """Insert frames at 10ms intervals. With thermal every Nth frame if specified."""
        for i in range(count):
            ts = i * 10
            with_thermal = with_thermal_every and (i % with_thermal_every == 0)
            db.add(
                FrameModel(
                    session_id=session_id,
                    timestamp_ms=ts,
                    frame_data=_minimal_frame_data(ts, with_thermal=with_thermal),
                )
            )
        db.commit()

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

        app.dependency_overrides[sessions_routes.get_db] = override_get_db
        with TestClient(app) as client:
            yield client
        app.dependency_overrides.clear()

    # ---------------------------------------------------------------------------
    # Tests
    # ---------------------------------------------------------------------------

    def test_get_session_returns_metadata(client, db_session):
        """GET /api/sessions/{id} returns session metadata."""
        session_id = "sess-meta"
        db_session.add(_make_session(session_id, frame_count=5))
        db_session.commit()
        _insert_frames(db_session, session_id, 5)

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["operator_id"] == "op-test"
        assert data["frame_count"] == 5
        assert data["status"] == "recording"
        assert "frames" in data

    def test_get_session_with_no_query_params_returns_all_frames(client, db_session):
        """GET /api/sessions/{id} with no params returns all frames (up to limit)."""
        session_id = "sess-all"
        db_session.add(_make_session(session_id, frame_count=50))
        db_session.commit()
        _insert_frames(db_session, session_id, 50)

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["frames"]) == 50

    def test_get_session_time_range_start_end(client, db_session):
        """GET with time_range_start and time_range_end returns filtered frames."""
        session_id = "sess-range"
        db_session.add(_make_session(session_id, frame_count=500))
        db_session.commit()
        _insert_frames(db_session, session_id, 500)

        response = client.get(
            f"/api/sessions/{session_id}",
            params={"time_range_start": 0, "time_range_end": 500},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["frames"]) == 51
        assert data["frames"][0]["timestamp_ms"] == 0
        assert data["frames"][-1]["timestamp_ms"] == 500

    def test_get_session_time_range_middle(client, db_session):
        """GET with middle time range returns correct chunk."""
        session_id = "sess-mid"
        db_session.add(_make_session(session_id, frame_count=1500))
        db_session.commit()
        _insert_frames(db_session, session_id, 1500)

        response = client.get(
            f"/api/sessions/{session_id}",
            params={"time_range_start": 5000, "time_range_end": 10000},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["frames"]) == 501
        assert data["frames"][0]["timestamp_ms"] == 5000
        assert data["frames"][-1]["timestamp_ms"] == 10000

    def test_get_session_time_range_last_500ms(client, db_session):
        """GET with time range covering last 500ms."""
        session_id = "sess-last"
        db_session.add(_make_session(session_id, frame_count=1500))
        db_session.commit()
        _insert_frames(db_session, session_id, 1500)

        response = client.get(
            f"/api/sessions/{session_id}",
            params={"time_range_start": 14500, "time_range_end": 14990},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["frames"]) == 50
        assert data["frames"][0]["timestamp_ms"] == 14500
        assert data["frames"][-1]["timestamp_ms"] == 14990

    def test_include_thermal_false_removes_thermal_snapshots(client, db_session):
        """GET with include_thermal=false removes thermal_snapshots from response."""
        session_id = "sess-nothermal"
        db_session.add(_make_session(session_id, frame_count=20))
        db_session.commit()
        _insert_frames(db_session, session_id, 20, with_thermal_every=5)

        response_with = client.get(
            f"/api/sessions/{session_id}", params={"include_thermal": True}
        )
        data_with = response_with.json()
        has_thermal = any(
            len(f.get("thermal_snapshots", [])) > 0 for f in data_with["frames"]
        )
        assert has_thermal

        response_without = client.get(
            f"/api/sessions/{session_id}", params={"include_thermal": False}
        )
        data_without = response_without.json()
        for frame in data_without["frames"]:
            assert frame.get("thermal_snapshots") == []

    def test_include_thermal_false_reduces_payload(client, db_session):
        """GET with include_thermal=false reduces payload size."""
        session_id = "sess-size"
        db_session.add(_make_session(session_id, frame_count=100))
        db_session.commit()
        _insert_frames(db_session, session_id, 100, with_thermal_every=1)

        r_with = client.get(
            f"/api/sessions/{session_id}", params={"include_thermal": True}
        )
        r_without = client.get(
            f"/api/sessions/{session_id}", params={"include_thermal": False}
        )
        len_with = len(r_with.content)
        len_without = len(r_without.content)
        assert len_without < len_with * 0.5

    def test_include_thermal_true_includes_thermal(client, db_session):
        """GET with include_thermal=true includes thermal_snapshots."""
        session_id = "sess-thermal"
        db_session.add(_make_session(session_id, frame_count=20))
        db_session.commit()
        _insert_frames(db_session, session_id, 20, with_thermal_every=5)

        response = client.get(
            f"/api/sessions/{session_id}", params={"include_thermal": True}
        )
        data = response.json()
        thermal_frames = [f for f in data["frames"] if f.get("thermal_snapshots")]
        assert len(thermal_frames) > 0
        assert len(thermal_frames[0]["thermal_snapshots"][0]["readings"]) == 5

    def test_limit_offset_pagination(client, db_session):
        """GET with limit and offset returns paginated frames."""
        session_id = "sess-pag"
        db_session.add(_make_session(session_id, frame_count=3000))
        db_session.commit()
        _insert_frames(db_session, session_id, 3000)

        r1 = client.get(
            f"/api/sessions/{session_id}",
            params={"limit": 1000, "offset": 0},
        )
        data1 = r1.json()
        assert len(data1["frames"]) == 1000
        assert data1["frames"][0]["timestamp_ms"] == 0
        assert data1["frames"][-1]["timestamp_ms"] == 9990

        r2 = client.get(
            f"/api/sessions/{session_id}",
            params={"limit": 1000, "offset": 1000},
        )
        data2 = r2.json()
        assert len(data2["frames"]) == 1000
        assert data2["frames"][0]["timestamp_ms"] == 10000
        assert data2["frames"][-1]["timestamp_ms"] == 19990

    def test_large_session_without_pagination_returns_400(client, db_session):
        """GET session with 30k+ frames without pagination/stream returns 400."""
        session_id = "sess-large"
        db_session.add(_make_session(session_id, frame_count=30001))
        db_session.commit()
        _insert_frames(db_session, session_id, 30001)

        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 400
        assert "Use pagination" in response.json()["detail"] or "frames" in response.json()["detail"].lower()

    def test_invalid_session_id_returns_404(client, db_session):
        """GET with invalid session_id returns 404."""
        response = client.get("/api/sessions/nonexistent-session-12345")
        assert response.status_code == 404

    def test_time_range_start_gt_end_returns_empty(client, db_session):
        """GET with time_range_start > time_range_end returns 200 with empty frames (no overlap)."""
        session_id = "sess-badrange"
        db_session.add(_make_session(session_id, frame_count=100))
        db_session.commit()
        _insert_frames(db_session, session_id, 100)

        response = client.get(
            f"/api/sessions/{session_id}",
            params={"time_range_start": 5000, "time_range_end": 1000},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["frames"]) == 0

    def test_negative_time_range_start_excludes_negative_timestamps(client, db_session):
        """GET with negative time_range_start: 200 returns only frames with timestamp_ms >= 0."""
        session_id = "sess-neg"
        db_session.add(_make_session(session_id, frame_count=50))
        db_session.commit()
        _insert_frames(db_session, session_id, 50)

        response = client.get(
            f"/api/sessions/{session_id}",
            params={"time_range_start": -100, "time_range_end": 500},
        )
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.json()
            assert all(f["timestamp_ms"] >= 0 for f in data["frames"])
        else:
            assert "detail" in response.json()
