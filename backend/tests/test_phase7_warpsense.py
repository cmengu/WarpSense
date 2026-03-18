"""
Tests for Phase 7 WarpSense integration.

Covers:
- warp_analysis routes: POST /analyse, GET /reports, GET /api/health/warp
- welders quality-trend: GET /{welder_id}/quality-trend
- days parameter bounding (negative -> 1, >90 -> 90)

Requires httpx<0.27 for TestClient compatibility (see requirements.txt).
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend is on path
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_backend))

from database.base import Base
from database.models import SessionModel, WeldQualityReportModel
from main import app
from routes import sessions


# ---------- Unit tests (no TestClient) ----------


def test_clamp_quality_trend_days():
    """_clamp_quality_trend_days bounds negative/zero to 1, >90 to 90."""
    from routes.welders import _clamp_quality_trend_days

    assert _clamp_quality_trend_days(-5) == 1
    assert _clamp_quality_trend_days(0) == 1
    assert _clamp_quality_trend_days(1) == 1
    assert _clamp_quality_trend_days(30) == 30
    assert _clamp_quality_trend_days(90) == 90
    assert _clamp_quality_trend_days(999) == 90


def test_warp_analysis_routes_registered():
    """WarpSense routes are registered in main."""
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    source = main_path.read_text()
    assert "warp_analysis_router" in source
    assert "include_router(warp_analysis_router)" in source
    warp_routes = Path(__file__).resolve().parent.parent / "routes" / "warp_analysis.py"
    wr = warp_routes.read_text()
    assert "/api/sessions/{session_id}/analyse" in wr
    assert "/api/health/warp" in wr


def test_quality_trend_route_registered():
    """Quality-trend route exists in welders."""
    welders_path = Path(__file__).resolve().parent.parent / "routes" / "welders.py"
    source = welders_path.read_text()
    assert "quality-trend" in source
    assert "_clamp_quality_trend_days" in source


# ---------- Fixtures ----------


@pytest.fixture
def db_engine():
    """In-memory SQLite with all Phase 7 tables."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    sm = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)
    db = sm()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """TestClient with get_db overridden for in-memory SQLite."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[sessions.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_session(session_id: str, operator_id: str = "op-001", frame_count: int = 0) -> SessionModel:
    return SessionModel(
        session_id=session_id,
        operator_id=operator_id,
        start_time=datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="test-weld",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status="recording",
        frame_count=frame_count,
        validation_errors=[],
        disable_sensor_continuity_checks=False,
        version=1,
        process_type="mig",
    )


# ---------- Integration tests ----------


def test_warp_health_returns_status(client):
    """GET /api/health/warp returns graph_initialised and classifier_initialised."""
    r = client.get("/api/health/warp")
    assert r.status_code == 200
    data = r.json()
    assert "graph_initialised" in data
    assert "classifier_initialised" in data


# ---------- GET reports ----------


def test_get_reports_404_when_no_report(client, db_session):
    """GET /api/sessions/{id}/reports returns 404 when no report exists."""
    db_session.add(_make_session("sess-no-report"))
    db_session.commit()

    r = client.get("/api/sessions/sess-no-report/reports")
    assert r.status_code == 404
    assert "No quality report found" in r.json()["detail"]


def test_get_reports_200_when_report_exists(client, db_session):
    """GET /api/sessions/{id}/reports returns 200 with report when one exists."""
    db_session.add(_make_session("sess-with-report"))
    db_session.commit()

    report = WeldQualityReportModel(
        session_id="sess-with-report",
        operator_id="op-001",
        report_timestamp=datetime.now(timezone.utc),
        quality_class="B",
        confidence=0.92,
        iso_5817_level="B",
        disposition="PASS",
        disposition_rationale="Within tolerance",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(report)
    db_session.commit()

    r = client.get("/api/sessions/sess-with-report/reports")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "sess-with-report"
    assert data["disposition"] == "PASS"
    assert data["report_id"] == report.id


# ---------- POST analyse (mocked) ----------


def test_post_analyse_404_when_session_not_found(client, db_session):
    """POST /api/sessions/{id}/analyse returns 404 when session does not exist."""
    r = client.post("/api/sessions/nonexistent-session/analyse")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


@patch("routes.warp_analysis.analyse_session", new_callable=AsyncMock)
def test_post_analyse_200_when_mocked(mock_analyse, client, db_session):
    """POST /api/sessions/{id}/analyse returns 200 with report when mocked."""
    db_session.add(_make_session("sess-analysed"))
    db_session.commit()

    fake_report = WeldQualityReportModel(
        session_id="sess-analysed",
        operator_id="op-001",
        report_timestamp=datetime.now(timezone.utc),
        quality_class="B",
        confidence=0.88,
        iso_5817_level="B",
        disposition="CONDITIONAL",
        disposition_rationale="Minor deviation",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(fake_report)
    db_session.commit()
    db_session.refresh(fake_report)

    mock_analyse.return_value = fake_report

    r = client.post("/api/sessions/sess-analysed/analyse")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "sess-analysed"
    assert data["disposition"] == "CONDITIONAL"
    mock_analyse.assert_awaited_once()


@patch("routes.warp_analysis.analyse_session", new_callable=AsyncMock)
def test_post_analyse_400_when_value_error(mock_analyse, client):
    """POST /api/sessions/{id}/analyse returns 400 when analyse_session raises ValueError (e.g. no frames)."""
    mock_analyse.side_effect = ValueError("Session sess-bad has no frames")

    r = client.post("/api/sessions/sess-bad/analyse")
    assert r.status_code == 400
    assert "no frames" in r.json()["detail"].lower()


# ---------- Quality trend ----------


def test_quality_trend_empty(client, db_session):
    """GET /api/welders/{id}/quality-trend returns empty reports when none exist."""
    r = client.get("/api/welders/welder-xyz/quality-trend")
    assert r.status_code == 200
    data = r.json()
    assert data["welder_id"] == "welder-xyz"
    assert data["days"] == 30
    assert data["total_sessions_analysed"] == 0
    assert data["disposition_counts"] == {"PASS": 0, "CONDITIONAL": 0, "REWORK_REQUIRED": 0}
    assert data["reports"] == []


def test_quality_trend_days_bounded_negative(client):
    """days=-5 is clamped to 1 (H2 fix)."""
    r = client.get("/api/welders/welder-xyz/quality-trend?days=-5")
    assert r.status_code == 200
    data = r.json()
    assert data["days"] == 1


def test_quality_trend_days_bounded_over_90(client):
    """days=999 is clamped to 90."""
    r = client.get("/api/welders/welder-xyz/quality-trend?days=999")
    assert r.status_code == 200
    data = r.json()
    assert data["days"] == 90


def test_quality_trend_with_reports(client, db_session):
    """GET /api/welders/{id}/quality-trend returns reports when they exist."""
    db_session.add(_make_session("s1", operator_id="welder-trend"))
    db_session.add(_make_session("s2", operator_id="welder-trend"))
    db_session.commit()

    now = datetime.now(timezone.utc)
    for sid, disp in [("s1", "PASS"), ("s2", "REWORK_REQUIRED")]:
        db_session.add(
            WeldQualityReportModel(
                session_id=sid,
                operator_id="welder-trend",
                report_timestamp=now - timedelta(days=1),
                quality_class="B",
                confidence=0.9,
                iso_5817_level="B",
                disposition=disp,
                created_at=now,
            )
        )
    db_session.commit()

    r = client.get("/api/welders/welder-trend/quality-trend?days=7")
    assert r.status_code == 200
    data = r.json()
    assert data["welder_id"] == "welder-trend"
    assert data["total_sessions_analysed"] == 2
    assert data["disposition_counts"]["PASS"] == 1
    assert data["disposition_counts"]["REWORK_REQUIRED"] == 1
    assert len(data["reports"]) == 2
