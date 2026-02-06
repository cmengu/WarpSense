"""
This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
Tests for SQLAlchemy ORM models.
Ensure your ORM and connection actually work.
Catches schema or conversion issues before your app runs in production.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.base import Base
from database.models import SessionModel
from models.frame import Frame
from models.session import Session
from models.thermal import TemperaturePoint, ThermalSnapshot


def _readings_with_center() -> list[TemperaturePoint]:
    return [
        TemperaturePoint(direction="center", temp_celsius=1000.0),
        TemperaturePoint(direction="north", temp_celsius=980.0),
        TemperaturePoint(direction="south", temp_celsius=970.0),
        TemperaturePoint(direction="east", temp_celsius=975.0),
        TemperaturePoint(direction="west", temp_celsius=965.0),
    ]


def _frame(timestamp_ms: int) -> Frame:
    snapshot = ThermalSnapshot(distance_mm=10.0, readings=_readings_with_center())
    return Frame(timestamp_ms=timestamp_ms, amps=100.0, volts=10.0, thermal_snapshots=[snapshot])


def _session(frames: list[Frame]) -> Session:
    return Session(
        session_id="session-orm-001",
        operator_id="operator-001",
        start_time=datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="test-weld",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=frames,
        frame_count=len(frames),
    )


def test_orm_create_and_query():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    frames = [_frame(0), _frame(10)]
    session = _session(frames)
    model = SessionModel.from_pydantic(session)

    db = SessionLocal()
    db.add(model)
    db.commit()

    stored = db.query(SessionModel).filter_by(session_id="session-orm-001").one()
    restored = stored.to_pydantic()

    assert restored.session_id == session.session_id
    assert restored.frame_count == 2
    assert restored.frames[0].timestamp_ms == 0
    assert restored.frames[1].timestamp_ms == 10
    db.close()


def test_pydantic_to_orm_conversion():
    frames = [_frame(0)]
    session = _session(frames)
    model = SessionModel.from_pydantic(session)

    assert model.session_id == session.session_id
    assert model.operator_id == session.operator_id
    assert model.frame_count == 1
    assert isinstance(model.frames, list)
    assert model.frames[0].frame_data["timestamp_ms"] == 0
