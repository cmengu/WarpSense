"""
Step 17: Backend model validation rejection tests.
Tests that invalid data is rejected by Session, Frame, ThermalSnapshot, and TemperaturePoint.
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


def _base_session(frames=None, **overrides):
    if frames is None:
        frames = []
    return {
        "session_id": "sess_001",
        "operator_id": "op_01",
        "start_time": datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
        "weld_type": "mild_steel",
        "thermal_sample_interval_ms": 100,
        "thermal_directions": ["center", "north", "south", "east", "west"],
        "thermal_distance_interval_mm": 10.0,
        "sensor_sample_rate_hz": 100,
        "frames": frames,
        "frame_count": len(frames),
        **overrides,
    }


def _readings(base_temp=400.0):
    return [
        TemperaturePoint(direction="center", temp_celsius=base_temp),
        TemperaturePoint(direction="north", temp_celsius=base_temp - 20),
        TemperaturePoint(direction="south", temp_celsius=base_temp - 10),
        TemperaturePoint(direction="east", temp_celsius=base_temp - 30),
        TemperaturePoint(direction="west", temp_celsius=base_temp - 25),
    ]


def _frame(timestamp_ms=0, distances=None, **overrides):
    snapshots = []
    if distances:
        snapshots = [
            ThermalSnapshot(distance_mm=d, readings=_readings()) for d in distances
        ]
    return Frame(timestamp_ms=timestamp_ms, thermal_snapshots=snapshots, **overrides)


# ---------------------------------------------------------------------------
# Session validation
# ---------------------------------------------------------------------------


class TestSessionValidation:
    def test_rejects_negative_frame_count(self):
        with pytest.raises(ValidationError):
            Session(**_base_session(frame_count=-1))

    def test_rejects_frame_count_mismatch(self):
        frames = [_frame(0), _frame(10)]
        with pytest.raises(ValidationError):
            Session(**_base_session(frames=frames, frame_count=99))

    def test_rejects_thermal_sample_interval_ms_le_zero(self):
        with pytest.raises(ValidationError):
            Session(**_base_session(thermal_sample_interval_ms=0))
        with pytest.raises(ValidationError):
            Session(**_base_session(thermal_sample_interval_ms=-1))

    def test_rejects_thermal_distance_interval_mm_le_zero(self):
        with pytest.raises(ValidationError):
            Session(**_base_session(thermal_distance_interval_mm=0))
        with pytest.raises(ValidationError):
            Session(**_base_session(thermal_distance_interval_mm=-0.1))

    def test_rejects_sensor_sample_rate_hz_le_zero(self):
        with pytest.raises(ValidationError):
            Session(**_base_session(sensor_sample_rate_hz=0))
        with pytest.raises(ValidationError):
            Session(**_base_session(sensor_sample_rate_hz=-10))

    def test_rejects_empty_thermal_directions(self):
        with pytest.raises(ValidationError):
            Session(**_base_session(thermal_directions=[]))

    def test_rejects_missing_session_id(self):
        data = _base_session()
        data.pop("session_id")
        with pytest.raises(ValidationError):
            Session(**data)

    def test_rejects_missing_operator_id(self):
        data = _base_session()
        data.pop("operator_id")
        with pytest.raises(ValidationError):
            Session(**data)

    def test_rejects_missing_start_time(self):
        data = _base_session()
        data.pop("start_time")
        with pytest.raises(ValidationError):
            Session(**data)

    def test_rejects_missing_weld_type(self):
        data = _base_session()
        data.pop("weld_type")
        with pytest.raises(ValidationError):
            Session(**data)

    def test_rejects_complete_status_without_expected_frame_count(self):
        frames = [_frame(0), _frame(10)]
        with pytest.raises(ValidationError):
            Session(
                **_base_session(
                    frames=frames,
                    frame_count=2,
                    status=SessionStatus.COMPLETE,
                    expected_frame_count=None,
                    last_successful_frame_index=1,
                    completed_at=datetime(2026, 2, 7, 10, 0, 1, tzinfo=timezone.utc),
                )
            )

    def test_rejects_complete_status_without_completed_at(self):
        frames = [_frame(0), _frame(10)]
        with pytest.raises(ValidationError):
            Session(
                **_base_session(
                    frames=frames,
                    frame_count=2,
                    status=SessionStatus.COMPLETE,
                    expected_frame_count=2,
                    last_successful_frame_index=1,
                    completed_at=None,
                )
            )

    def test_rejects_thermal_distance_interval_mm_mismatch(self):
        frames = [
            _frame(0, distances=[10.0, 25.0, 40.0]),
            _frame(10, distances=[10.0, 25.0, 40.0]),
        ]
        with pytest.raises(ValidationError):
            Session(
                **_base_session(
                    frames=frames,
                    frame_count=2,
                    thermal_distance_interval_mm=10.0,
                    disable_sensor_continuity_checks=True,
                )
            )

    def test_rejects_duplicate_frame_timestamps(self):
        frames = [_frame(0), _frame(0), _frame(10)]
        with pytest.raises(ValidationError):
            Session(
                **_base_session(
                    frames=frames,
                    frame_count=3,
                    disable_sensor_continuity_checks=True,
                )
            )

    def test_rejects_out_of_order_frame_timestamps(self):
        frames = [_frame(20), _frame(0), _frame(10)]
        with pytest.raises(ValidationError):
            Session(
                **_base_session(
                    frames=frames,
                    frame_count=3,
                    disable_sensor_continuity_checks=True,
                )
            )


# ---------------------------------------------------------------------------
# Frame validation
# ---------------------------------------------------------------------------


class TestFrameValidation:
    def test_rejects_missing_timestamp_ms(self):
        with pytest.raises(ValidationError):
            Frame(thermal_snapshots=[])

    def test_rejects_negative_timestamp_ms(self):
        with pytest.raises(ValidationError):
            Frame(timestamp_ms=-1, thermal_snapshots=[])

    def test_rejects_negative_volts(self):
        with pytest.raises(ValidationError):
            _frame(0, volts=-1.0)

    def test_rejects_negative_amps(self):
        with pytest.raises(ValidationError):
            _frame(0, amps=-10.0)

    def test_rejects_negative_angle_degrees(self):
        with pytest.raises(ValidationError):
            _frame(0, angle_degrees=-5.0)

    def test_rejects_angle_degrees_gt_360(self):
        with pytest.raises(ValidationError):
            _frame(0, angle_degrees=361.0)

    def test_accepts_angle_degrees_360(self):
        f = _frame(0, angle_degrees=360.0)
        assert f.angle_degrees == 360.0

    def test_accepts_null_volts_amps_angle(self):
        f = Frame(timestamp_ms=0, volts=None, amps=None, angle_degrees=None)
        assert f.volts is None and f.amps is None and f.angle_degrees is None


# ---------------------------------------------------------------------------
# ThermalSnapshot validation
# ---------------------------------------------------------------------------


class TestThermalSnapshotValidation:
    def test_rejects_duplicate_directions(self):
        readings = [
            TemperaturePoint(direction="center", temp_celsius=400.0),
            TemperaturePoint(direction="north", temp_celsius=380.0),
            TemperaturePoint(direction="south", temp_celsius=390.0),
            TemperaturePoint(direction="east", temp_celsius=370.0),
            TemperaturePoint(direction="north", temp_celsius=385.0),
        ]
        with pytest.raises(ValidationError):
            ThermalSnapshot(distance_mm=10.0, readings=readings)

    def test_rejects_negative_distance_mm(self):
        with pytest.raises(ValidationError):
            ThermalSnapshot(distance_mm=-5.0, readings=_readings())

    def test_rejects_zero_distance_mm(self):
        with pytest.raises(ValidationError):
            ThermalSnapshot(distance_mm=0.0, readings=_readings())

    def test_rejects_empty_readings(self):
        with pytest.raises(ValidationError):
            ThermalSnapshot(distance_mm=10.0, readings=[])


# ---------------------------------------------------------------------------
# TemperaturePoint validation
# ---------------------------------------------------------------------------


class TestTemperaturePointValidation:
    def test_rejects_empty_direction_string(self):
        with pytest.raises(ValidationError):
            TemperaturePoint(direction="", temp_celsius=0.0)

    def test_rejects_invalid_direction(self):
        with pytest.raises(ValidationError):
            TemperaturePoint(direction="northeast", temp_celsius=0.0)

    def test_rejects_temp_below_absolute_zero(self):
        with pytest.raises(ValidationError):
            TemperaturePoint(direction="center", temp_celsius=-274.0)

    def test_accepts_temp_at_absolute_zero(self):
        p = TemperaturePoint(direction="center", temp_celsius=-273.15)
        assert p.temp_celsius == -273.15
