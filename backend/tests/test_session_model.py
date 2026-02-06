"""
Tests for Session model validations.
Critical assumptions:
Frames are at 100 Hz (10 ms interval)
All thermal_directions are present in each frame
distance_mm values must be strictly increasing from first to last in the frame
Each ThermalSnapshot must contain exactly one reading with direction="center"
amps cannot jump >20% per frame; volts cannot jump >10% but it may go to 0 and back to normal values
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.frame import Frame
from models.session import Session, SessionStatus
from models.thermal import TemperaturePoint, ThermalSnapshot


def _readings_with_center() -> list[TemperaturePoint]:
    return [
        TemperaturePoint(direction="center", temp_celsius=1000.0),
        TemperaturePoint(direction="north", temp_celsius=980.0),
        TemperaturePoint(direction="south", temp_celsius=970.0),
        TemperaturePoint(direction="east", temp_celsius=975.0),
        TemperaturePoint(direction="west", temp_celsius=965.0),
    ]


def _snapshot(distance_mm: float) -> ThermalSnapshot:
    return ThermalSnapshot(distance_mm=distance_mm, readings=_readings_with_center())


def _frame(timestamp_ms: int, distances_mm: list[float] | None = None, amps: float | None = None, volts: float | None = None) -> Frame:
    snapshots = []
    if distances_mm:
        snapshots = [_snapshot(distance) for distance in distances_mm]
    return Frame(
        timestamp_ms=timestamp_ms,
        amps=amps,
        volts=volts,
        thermal_snapshots=snapshots,
    )


def _base_session(frames: list[Frame]) -> dict:
    return {
        "session_id": "session-001",
        "operator_id": "operator-123",
        "start_time": datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc),
        "weld_type": "test-weld",
        "thermal_sample_interval_ms": 100,
        "thermal_directions": ["center", "north", "south", "east", "west"],
        "thermal_distance_interval_mm": 10.0,
        "sensor_sample_rate_hz": 100,
        "frames": frames,
        "frame_count": len(frames),
    }


def test_session_metadata_fields_required():
    data = _base_session(frames=[])
    data.pop("operator_id")
    with pytest.raises(ValidationError):
        Session(**data)


def test_frame_timestamp_validation_rejects_duplicates_and_misordered_frames():
    frames = [_frame(0), _frame(0), _frame(10)]
    data = _base_session(frames=frames)
    with pytest.raises(ValidationError):
        Session(**data)

    frames = [_frame(10), _frame(0), _frame(20)]
    data = _base_session(frames=frames)
    with pytest.raises(ValidationError):
        Session(**data)


def test_thermal_distance_consistency_validation_enforces_canonical_set():
    frames = [
        _frame(0, distances_mm=[0.0, 10.0]),
        _frame(10, distances_mm=[0.0, 12.0]),
    ]
    data = _base_session(frames=frames)
    with pytest.raises(ValidationError):
        Session(**data)


def test_status_transitions():
    assert Session.is_valid_status_transition(SessionStatus.RECORDING, SessionStatus.COMPLETE)
    assert Session.is_valid_status_transition(SessionStatus.COMPLETE, SessionStatus.ARCHIVED)
    assert not Session.is_valid_status_transition(SessionStatus.ARCHIVED, SessionStatus.RECORDING)


def test_cannot_modify_complete_session():
    frames = [_frame(0), _frame(10)]
    data = _base_session(frames=frames)
    data.update(
        {
            "status": SessionStatus.COMPLETE,
            "expected_frame_count": 1,
            "last_successful_frame_index": 1,
            "completed_at": datetime(2026, 2, 6, 12, 0, 1, tzinfo=timezone.utc),
        }
    )
    with pytest.raises(ValidationError):
        Session(**data)


def test_sensor_continuity_large_jump_rejected():
    frames = [
        _frame(0, amps=100.0, volts=10.0),
        _frame(10, amps=130.0, volts=12.0),
    ]
    data = _base_session(frames=frames)
    with pytest.raises(ValidationError):
        Session(**data)


def test_realistic_variations_accepted():
    frames = [
        _frame(0, amps=100.0, volts=10.0),
        _frame(10, amps=112.0, volts=10.5),
    ]
    data = _base_session(frames=frames)
    session = Session(**data)
    assert session.frame_count == 2
