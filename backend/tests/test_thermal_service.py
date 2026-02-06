"""
Tests for thermal service functions.
Not really any critical assumptions here, just that the service works as expected.
Heat dissipation calculation is null-safe, DB-aware, numerically correct, and performant under real-world frame loads.
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.base import Base
from database.models import SessionModel
from models.frame import Frame
from models.session import Session
from models.thermal import TemperaturePoint, ThermalSnapshot
from services.thermal_service import calculate_heat_dissipation, get_previous_frame


def _readings_with_center(temp_celsius: float) -> list[TemperaturePoint]:
    return [
        TemperaturePoint(direction="center", temp_celsius=temp_celsius),
        TemperaturePoint(direction="north", temp_celsius=temp_celsius - 10),
        TemperaturePoint(direction="south", temp_celsius=temp_celsius - 20),
        TemperaturePoint(direction="east", temp_celsius=temp_celsius - 15),
        TemperaturePoint(direction="west", temp_celsius=temp_celsius - 25),
    ]


def _frame(timestamp_ms: int, temp_celsius: float, with_thermal: bool = True) -> Frame:
    snapshots = []
    if with_thermal:
        snapshots = [ThermalSnapshot(distance_mm=10.0, readings=_readings_with_center(temp_celsius))]
    return Frame(timestamp_ms=timestamp_ms, thermal_snapshots=snapshots)


def _session(frames: list[Frame]) -> Session:
    return Session(
        session_id="session-thermal-001",
        operator_id="operator-thermal",
        start_time=datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="test-weld",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=frames,
        frame_count=len(frames),
    )


def test_first_frame_returns_none():
    curr = _frame(0, 1000.0)
    assert calculate_heat_dissipation(None, curr) is None


def test_missing_thermal_frames_returns_none():
    prev = _frame(0, 1000.0, with_thermal=False)
    curr = _frame(10, 990.0)
    assert calculate_heat_dissipation(prev, curr) is None

    prev = _frame(0, 1000.0)
    curr = _frame(10, 990.0, with_thermal=False)
    assert calculate_heat_dissipation(prev, curr) is None


def test_empty_readings_returns_none():
    prev = Frame.model_construct(
        timestamp_ms=0,
        thermal_snapshots=[
            ThermalSnapshot.model_construct(
                distance_mm=10.0,
                readings=[],
            )
        ],
    )
    curr = _frame(10, 990.0)
    assert calculate_heat_dissipation(prev, curr) is None


def test_normal_calculation():
    prev = _frame(0, 1000.0)
    curr = _frame(10, 990.0)
    assert calculate_heat_dissipation(prev, curr) == pytest.approx(100.0)


def test_negative_dissipation():
    prev = _frame(0, 980.0)
    curr = _frame(10, 1000.0)
    assert calculate_heat_dissipation(prev, curr) == pytest.approx(-200.0)


def test_db_lookup():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    frames = [_frame(0, 1000.0), _frame(10, 990.0)]
    session = _session(frames)
    session_model = SessionModel.from_pydantic(session)

    db = SessionLocal()
    db.add(session_model)
    db.commit()

    prev = get_previous_frame("session-thermal-001", 10, db)
    assert prev is not None
    assert prev.timestamp_ms == 0
    db.close()


def test_no_prev_frame():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    db = SessionLocal()
    prev = get_previous_frame("missing-session", 10, db)
    assert prev is None
    db.close()


def test_performance_1000_frames_under_100ms():
    frames = [_frame(i * 10, 1000.0 - i) for i in range(1000)]
    start = time.perf_counter()
    prev = None
    for frame in frames:
        _ = calculate_heat_dissipation(prev, frame)
        prev = frame
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 100
