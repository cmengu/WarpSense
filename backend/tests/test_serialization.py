"""
Step 18: Serialization tests (Python ↔ JSON ↔ TypeScript).
Verifies Python models serialize correctly to JSON with snake_case,
preserve precision, datetime as ISO 8601, and optional null handling.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.frame import Frame
from models.session import Session, SessionStatus
from models.thermal import TemperaturePoint, ThermalSnapshot


def _readings(center_temp=400.0):
    return [
        TemperaturePoint(direction="center", temp_celsius=center_temp),
        TemperaturePoint(direction="north", temp_celsius=center_temp - 10),
        TemperaturePoint(direction="south", temp_celsius=center_temp - 20),
        TemperaturePoint(direction="east", temp_celsius=center_temp - 15),
        TemperaturePoint(direction="west", temp_celsius=center_temp - 25),
    ]


# ---------------------------------------------------------------------------
# Round-trip: Python → JSON → Python
# ---------------------------------------------------------------------------


def test_session_round_trip_preserves_all_fields():
    """Session Python → JSON → Python round-trip preserves all fields."""
    session = Session(
        session_id="sess_ser_001",
        operator_id="op_01",
        start_time=datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=[],
        frame_count=0,
        status=SessionStatus.RECORDING,
    )
    dumped = session.model_dump(mode="json")
    loaded = Session.model_validate(dumped)
    assert loaded.session_id == session.session_id
    assert loaded.operator_id == session.operator_id
    assert loaded.weld_type == session.weld_type
    assert loaded.frame_count == session.frame_count
    assert loaded.status == session.status


def test_frame_round_trip_preserves_all_fields():
    """Frame Python → JSON → Python round-trip preserves all fields."""
    frame = Frame(
        timestamp_ms=100,
        volts=22.5,
        amps=150.0,
        angle_degrees=45.0,
        thermal_snapshots=[
            ThermalSnapshot(distance_mm=10.0, readings=_readings(425.0)),
        ],
        optional_sensors=None,
        heat_dissipation_rate_celsius_per_sec=-5.2,
    )
    dumped = frame.model_dump(mode="json")
    loaded = Frame.model_validate(dumped)
    assert loaded.timestamp_ms == frame.timestamp_ms
    assert loaded.volts == frame.volts
    assert loaded.amps == frame.amps
    assert loaded.angle_degrees == frame.angle_degrees
    assert loaded.heat_dissipation_rate_celsius_per_sec == frame.heat_dissipation_rate_celsius_per_sec
    assert len(loaded.thermal_snapshots) == 1
    assert loaded.thermal_snapshots[0].distance_mm == 10.0


def test_thermal_snapshot_round_trip_preserves_all_fields():
    """ThermalSnapshot Python → JSON → Python round-trip preserves all fields."""
    snapshot = ThermalSnapshot(distance_mm=10.0, readings=_readings(425.3))
    dumped = snapshot.model_dump(mode="json")
    loaded = ThermalSnapshot.model_validate(dumped)
    assert loaded.distance_mm == snapshot.distance_mm
    assert len(loaded.readings) == 5
    center = next(r for r in loaded.readings if r.direction == "center")
    assert center.temp_celsius == 425.3


# ---------------------------------------------------------------------------
# Snake_case field names
# ---------------------------------------------------------------------------


def test_json_uses_snake_case_timestamp_ms():
    """JSON uses snake_case: timestamp_ms, not timestampMs."""
    frame = Frame(timestamp_ms=0, thermal_snapshots=[])
    dumped = frame.model_dump(mode="json")
    assert "timestamp_ms" in dumped
    assert "timestampMs" not in dumped


def test_json_uses_snake_case_thermal_fields():
    """JSON uses snake_case for thermal fields."""
    point = TemperaturePoint(direction="center", temp_celsius=400.0)
    dumped = point.model_dump(mode="json")
    assert "temp_celsius" in dumped
    assert "tempCelsius" not in dumped

    snapshot = ThermalSnapshot(distance_mm=10.0, readings=_readings())
    dumped = snapshot.model_dump(mode="json")
    assert "distance_mm" in dumped
    assert "distanceMm" not in dumped

    frame = Frame(timestamp_ms=0, heat_dissipation_rate_celsius_per_sec=100.0)
    dumped = frame.model_dump(mode="json")
    assert "heat_dissipation_rate_celsius_per_sec" in dumped


# ---------------------------------------------------------------------------
# Extreme values
# ---------------------------------------------------------------------------


def test_extreme_floating_point_values_preserved():
    """Extreme volts/amps preserved."""
    frame = Frame(
        timestamp_ms=0,
        volts=22.123456789012345,
        amps=150.987654321,
        thermal_snapshots=[],
    )
    dumped = frame.model_dump(mode="json")
    loaded = Frame.model_validate(dumped)
    assert loaded.volts == pytest.approx(22.123456789012345, rel=1e-10)
    assert loaded.amps == pytest.approx(150.987654321, rel=1e-10)


def test_extreme_temperature_preserved():
    """Extreme temp_celsius preserved."""
    point = TemperaturePoint(direction="center", temp_celsius=9999.123456789)
    dumped = point.model_dump(mode="json")
    loaded = TemperaturePoint.model_validate(dumped)
    assert loaded.temp_celsius == pytest.approx(9999.123456789, rel=1e-10)


def test_negative_heat_dissipation_preserved():
    """Negative heat_dissipation_rate preserved."""
    frame = Frame(
        timestamp_ms=0,
        heat_dissipation_rate_celsius_per_sec=-500.987654,
        thermal_snapshots=[],
    )
    dumped = frame.model_dump(mode="json")
    loaded = Frame.model_validate(dumped)
    assert loaded.heat_dissipation_rate_celsius_per_sec == pytest.approx(
        -500.987654, abs=1e-6
    )


# ---------------------------------------------------------------------------
# Optional / null handling
# ---------------------------------------------------------------------------


def test_optional_sensors_null_serializes_as_null():
    """optional_sensors: null serializes as null in JSON."""
    frame = Frame(timestamp_ms=0, optional_sensors=None, thermal_snapshots=[])
    json_str = frame.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["optional_sensors"] is None


def test_heat_dissipation_null_serializes_correctly():
    """heat_dissipation_rate_celsius_per_sec null serializes correctly."""
    frame = Frame(timestamp_ms=0, thermal_snapshots=[])
    json_str = frame.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["heat_dissipation_rate_celsius_per_sec"] is None


def test_thermal_snapshots_empty_array_serializes_as_array():
    """thermal_snapshots empty array serializes as []."""
    frame = Frame(timestamp_ms=0, thermal_snapshots=[])
    json_str = frame.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["thermal_snapshots"] == []


# ---------------------------------------------------------------------------
# Floating point precision
# ---------------------------------------------------------------------------


def test_floating_point_precision_within_tolerance():
    """Floating point precision within ±1e-10 for most fields, ±1e-6 for dissipation."""
    frame = Frame(
        timestamp_ms=0,
        volts=22.123456789012345,
        amps=150.987654321098765,
        angle_degrees=45.123456789,
        heat_dissipation_rate_celsius_per_sec=123.456789123456,
        thermal_snapshots=[],
    )
    json_str = frame.model_dump_json()
    loaded = Frame.model_validate_json(json_str)
    assert loaded.volts == pytest.approx(22.123456789012345, abs=1e-10)
    assert loaded.amps == pytest.approx(150.987654321098765, abs=1e-10)
    assert loaded.heat_dissipation_rate_celsius_per_sec == pytest.approx(
        123.456789123456, abs=1e-6
    )


# ---------------------------------------------------------------------------
# Datetime and enum
# ---------------------------------------------------------------------------


def test_datetime_fields_serialize_to_iso_8601():
    """start_time, completed_at serialize to ISO 8601 strings."""
    start = datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 2, 7, 10, 1, 30, tzinfo=timezone.utc)
    frame = Frame(timestamp_ms=0, thermal_snapshots=[])
    session = Session(
        session_id="s1",
        operator_id="o1",
        start_time=start,
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=[frame],
        frame_count=1,
        status=SessionStatus.COMPLETE,
        expected_frame_count=1,
        last_successful_frame_index=0,
        completed_at=completed,
        disable_sensor_continuity_checks=True,
    )
    dumped = session.model_dump(mode="json")
    assert "T" in dumped["start_time"]
    assert "Z" in dumped["start_time"] or "+" in dumped["start_time"]
    assert "T" in dumped["completed_at"]


def test_session_status_enum_serializes_to_string():
    """SessionStatus enum serializes to string."""
    for status in [SessionStatus.RECORDING, SessionStatus.FAILED]:
        session = Session(
            session_id="s1",
            operator_id="o1",
            start_time=datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
            weld_type="mild_steel",
            thermal_sample_interval_ms=100,
            thermal_directions=["center"],
            thermal_distance_interval_mm=10.0,
            sensor_sample_rate_hz=100,
            frames=[],
            frame_count=0,
            status=status,
        )
        dumped = session.model_dump(mode="json")
        assert isinstance(dumped["status"], str)
        assert dumped["status"] == status.value
