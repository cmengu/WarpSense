"""
Tests for GET/PUT thresholds API and cache invalidation.
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
from database.models import SessionModel, FrameModel, WeldThresholdModel
from data.mock_sessions import generate_expert_session
from main import app
from routes import thresholds as thresholds_routes
from routes import sessions as sessions_routes


@pytest.fixture
def db_session():
    """In-memory SQLite. WeldThresholdModel must be imported so create_all creates weld_thresholds."""
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
    """Override get_db for BOTH routes.thresholds and routes.sessions."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[thresholds_routes.get_db] = override_get_db
    app.dependency_overrides[sessions_routes.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_weld_thresholds(db_session):
    """Seed weld_thresholds so GET/PUT tests work."""
    for weld_type, a, aw, ac, tw, tc, amps, volts, hd in [
        ("mig", 45.0, 5.0, 15.0, 60.0, 80.0, 5.0, 1.0, 80.0),
        ("tig", 75.0, 10.0, 20.0, 60.0, 80.0, 5.0, 1.0, 80.0),
        ("stick", 20.0, 8.0, 20.0, 60.0, 80.0, 5.0, 1.0, 80.0),
        ("flux_core", 45.0, 7.0, 18.0, 60.0, 80.0, 5.0, 1.0, 80.0),
    ]:
        db_session.add(
            WeldThresholdModel(
                weld_type=weld_type,
                angle_target_degrees=a,
                angle_warning_margin=aw,
                angle_critical_margin=ac,
                thermal_symmetry_warning_celsius=tw,
                thermal_symmetry_critical_celsius=tc,
                amps_stability_warning=amps,
                volts_stability_warning=volts,
                heat_diss_consistency=hd,
            )
        )
    db_session.commit()


@pytest.fixture
def session_factory(db_session, seeded_weld_thresholds):
    """Creates SessionModel with 10+ frames for score endpoint tests."""

    def _create(process_type: str = "mig", session_id: str = "sess_test_001"):
        session = generate_expert_session(session_id=session_id)
        assert len(session.frames) >= 10
        session = session.model_copy(update={"process_type": process_type})
        model = SessionModel.from_pydantic(session)
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)
        return model

    return _create


def test_get_thresholds_returns_four(client, seeded_weld_thresholds):
    """GET /api/thresholds returns 4 items."""
    r = client.get("/api/thresholds")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    types = [t["weld_type"] for t in data]
    assert "mig" in types and "tig" in types


def test_put_threshold_succeeds(client, seeded_weld_thresholds):
    """PUT with valid body succeeds, returns single object."""
    r = client.put(
        "/api/thresholds/mig",
        json={
            "angle_target_degrees": 50,
            "angle_warning_margin": 6,
            "angle_critical_margin": 16,
            "thermal_symmetry_warning_celsius": 60,
            "thermal_symmetry_critical_celsius": 80,
            "amps_stability_warning": 5,
            "volts_stability_warning": 1,
            "heat_diss_consistency": 80,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["weld_type"] == "mig"
    assert data["angle_target_degrees"] == 50


def test_put_threshold_angle_zero_returns_422(client, seeded_weld_thresholds):
    """PUT with angle_target_degrees=0 returns 422."""
    r = client.put(
        "/api/thresholds/mig",
        json={
            "angle_target_degrees": 0,
            "angle_warning_margin": 5,
            "angle_critical_margin": 15,
            "thermal_symmetry_warning_celsius": 60,
            "thermal_symmetry_critical_celsius": 80,
            "amps_stability_warning": 5,
            "volts_stability_warning": 1,
            "heat_diss_consistency": 80,
        },
    )
    assert r.status_code == 422


def test_put_threshold_warning_gt_critical_returns_422(
    client, seeded_weld_thresholds
):
    """PUT with warning > critical returns 422."""
    r = client.put(
        "/api/thresholds/mig",
        json={
            "angle_target_degrees": 45,
            "angle_warning_margin": 20,
            "angle_critical_margin": 10,
            "thermal_symmetry_warning_celsius": 60,
            "thermal_symmetry_critical_celsius": 80,
            "amps_stability_warning": 5,
            "volts_stability_warning": 1,
            "heat_diss_consistency": 80,
        },
    )
    assert r.status_code == 422


def test_put_threshold_invalidates_cache(
    client, db_session, session_factory, seeded_weld_thresholds
):
    """PUT then GET score must reflect new threshold (cache invalidated)."""
    session = session_factory(process_type="mig")
    assert len(session.frames) >= 10

    r0 = client.get(f"/api/sessions/{session.session_id}/score")
    assert r0.status_code == 200
    spec0 = r0.json().get("active_threshold_spec", {})
    assert spec0.get("angle_target") == 45

    r1 = client.put(
        "/api/thresholds/mig",
        json={
            "angle_target_degrees": 50,
            "angle_warning_margin": 6,
            "angle_critical_margin": 16,
            "thermal_symmetry_warning_celsius": 60,
            "thermal_symmetry_critical_celsius": 80,
            "amps_stability_warning": 5,
            "volts_stability_warning": 1,
            "heat_diss_consistency": 80,
        },
    )
    assert r1.status_code == 200

    r2 = client.get(f"/api/sessions/{session.session_id}/score")
    assert r2.status_code == 200
    spec2 = r2.json().get("active_threshold_spec", {})
    assert spec2.get("angle_target") == 50


def test_score_insufficient_frames_returns_400(
    client, db_session, seeded_weld_thresholds
):
    """GET score for session with <10 frames returns 400."""
    session = generate_expert_session(session_id="sess_few_001")
    frames_5 = session.frames[:5]
    session = session.model_copy(
        update={
            "frames": frames_5,
            "frame_count": 5,
            "expected_frame_count": 5,
            "last_successful_frame_index": 4,
        }
    )
    model = SessionModel.from_pydantic(session)
    db_session.add(model)
    db_session.commit()

    r = client.get("/api/sessions/sess_few_001/score")
    assert r.status_code == 400
    assert "insufficient frames" in r.json()["detail"].lower()
