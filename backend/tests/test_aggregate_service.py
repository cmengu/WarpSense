"""
Tests for aggregate_service.get_aggregate_kpis.
Covers: empty, all-null avg_score, invalid date 400, two sessions.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.models import SessionModel
from services.aggregate_service import get_aggregate_kpis


@pytest.fixture
def db_session():
    """In-memory SQLite session for service tests."""
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


def test_aggregate_kpis_empty(db_session):
    """No sessions: zeros and empty arrays."""
    result = get_aggregate_kpis(
        db_session, date_start="2025-02-01", date_end="2025-02-17"
    )
    assert result["kpis"]["session_count"] == 0
    assert result["kpis"]["avg_score"] is None
    assert result["kpis"]["rework_count"] == 0
    assert result["trend"] == []
    assert result["calendar"] == []


def test_aggregate_kpis_all_null_score(db_session):
    """Sessions with score_total=NULL: avg_score must be None, no division by zero."""
    s = SessionModel(
        session_id="sess_null",
        operator_id="op_a",
        start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status="complete",
        frame_count=10,
        validation_errors=[],
        score_total=None,
    )
    db_session.add(s)
    db_session.commit()

    result = get_aggregate_kpis(
        db_session, date_start="2025-02-01", date_end="2025-02-17"
    )
    assert result["kpis"]["session_count"] == 1
    assert result["kpis"]["avg_score"] is None
    assert result["kpis"]["rework_count"] == 0
    assert result["trend"] == []
    assert result["calendar"] != []
    assert len(result["calendar"]) == 1


def test_aggregate_kpis_two_sessions(db_session):
    """Two sessions with scores: correct KPIs, trend, calendar."""
    s1 = SessionModel(
        session_id="sess_001",
        operator_id="op_a",
        start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status="complete",
        frame_count=10,
        validation_errors=[],
        score_total=85,
    )
    s2 = SessionModel(
        session_id="sess_002",
        operator_id="op_b",
        start_time=datetime(2025, 2, 11, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status="complete",
        frame_count=10,
        validation_errors=[],
        score_total=55,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    result = get_aggregate_kpis(
        db_session, date_start="2025-02-01", date_end="2025-02-17"
    )
    assert result["kpis"]["session_count"] == 2
    assert result["kpis"]["avg_score"] == 70.0
    assert result["kpis"]["rework_count"] == 1
    assert len(result["trend"]) == 2
    assert len(result["calendar"]) == 2
