"""
Tests for thermal Pydantic models.
thermal.py = the gate / checker
test_thermal.py = the test that makes sure the gate stays locked
RAW SENSOR DATA
   ↓
Adapter / Normalizer
   ↓
thermal.py  (canonical contract, strict)
   ↓
test_thermal.py  (guarantees the contract stays strict)
here are just a quick set of rules enforced to ensure that a thermal snapshot must contain exactly five validated cardinal temperature readings at a single weld distance.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.thermal import TemperaturePoint, ThermalSnapshot


def _make_reading(direction: str = "center", temp_celsius: float = 1000.0) -> TemperaturePoint:
    return TemperaturePoint(direction=direction, temp_celsius=temp_celsius)


def test_temperature_point_requires_direction():
    with pytest.raises(ValidationError):
        TemperaturePoint(temp_celsius=900.0)


def test_temperature_point_requires_temp_celsius():
    with pytest.raises(ValidationError):
        TemperaturePoint(direction="center")


def test_temperature_point_rejects_invalid_direction():
    with pytest.raises(ValidationError):
        TemperaturePoint(direction="invalid", temp_celsius=900.0)


def test_thermal_snapshot_accepts_exactly_five_readings():
    readings = [
        _make_reading("center"),
        _make_reading("north"),
        _make_reading("south"),
        _make_reading("east"),
        _make_reading("west"),
    ]
    snapshot = ThermalSnapshot(distance_mm=10.0, readings=readings)
    assert len(snapshot.readings) == 5


def test_thermal_snapshot_rejects_fewer_than_five_readings():
    readings = [
        _make_reading("center"),
        _make_reading("north"),
        _make_reading("south"),
        _make_reading("east"),
    ]
    with pytest.raises(ValidationError):
        ThermalSnapshot(distance_mm=10.0, readings=readings)


def test_thermal_snapshot_rejects_more_than_five_readings():
    readings = [
        _make_reading("center"),
        _make_reading("north"),
        _make_reading("south"),
        _make_reading("east"),
        _make_reading("west"),
        _make_reading("center", 950.0),
    ]
    with pytest.raises(ValidationError):
        ThermalSnapshot(distance_mm=10.0, readings=readings)
