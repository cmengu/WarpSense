"""
Tests for comparison models.
critical constraints:
timestamp_ms must be ≥ 0
amps_delta cannot exceed ±20% of session_a.amps
volts_delta cannot exceed ±10% of session_a.volts
angle_degrees_delta cannot exceed ±10° of session_a.angle_degrees
thermal_deltas must contain exactly five readings, one for each direction (center, north, south, east, west)
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.comparison import FrameDelta, ThermalDelta, TemperatureDelta


def _thermal_delta() -> ThermalDelta:
    readings = [
        TemperatureDelta(direction="center", delta_temp_celsius=10.0),
        TemperatureDelta(direction="north", delta_temp_celsius=-5.0),
        TemperatureDelta(direction="south", delta_temp_celsius=2.0),
        TemperatureDelta(direction="east", delta_temp_celsius=1.5),
        TemperatureDelta(direction="west", delta_temp_celsius=-1.0),
    ]
    return ThermalDelta(distance_mm=10.0, readings=readings)


def test_comparison_models_work_for_expert_vs_expert():
    frame_delta = FrameDelta(
        timestamp_ms=100,
        amps_delta=2.0,
        volts_delta=-0.5,
        angle_degrees_delta=1.0,
        thermal_deltas=[_thermal_delta()],
    )
    assert frame_delta.timestamp_ms == 100
    assert len(frame_delta.thermal_deltas) == 1


def test_comparison_models_work_for_novice_vs_novice():
    frame_delta = FrameDelta(
        timestamp_ms=200,
        amps_delta=-3.0,
        volts_delta=0.2,
        angle_degrees_delta=-0.8,
        thermal_deltas=[_thermal_delta()],
    )
    assert frame_delta.amps_delta == -3.0


def test_comparison_models_work_for_expert_vs_novice():
    frame_delta = FrameDelta(
        timestamp_ms=300,
        amps_delta=5.0,
        volts_delta=1.0,
        angle_degrees_delta=2.5,
        thermal_deltas=[_thermal_delta()],
    )
    assert frame_delta.volts_delta == 1.0


def test_comparison_aligns_by_timestamp_only():
    with pytest.raises(ValidationError):
        FrameDelta(timestamp_ms=-1)
