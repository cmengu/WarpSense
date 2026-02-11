"""
Tests for Frame model validations.
Key assumptions that need to change in the future:
No two ThermalSnapshots in a Frame may have the same distance_mm
The distance_mm values of snapshots must be strictly increasing from first to last in the frame.
Each ThermalSnapshot must contain exactly one reading with direction="center".
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.frame import Frame
from models.thermal import TemperaturePoint, ThermalSnapshot


def _readings_with_center() -> list[TemperaturePoint]:
    return [
        TemperaturePoint(direction="center", temp_celsius=1000.0),
        TemperaturePoint(direction="north", temp_celsius=980.0),
        TemperaturePoint(direction="south", temp_celsius=970.0),
        TemperaturePoint(direction="east", temp_celsius=975.0),
        TemperaturePoint(direction="west", temp_celsius=965.0),
    ]


def _readings_without_center() -> list[TemperaturePoint]:
    return [
        TemperaturePoint(direction="north", temp_celsius=980.0),
        TemperaturePoint(direction="south", temp_celsius=970.0),
        TemperaturePoint(direction="east", temp_celsius=975.0),
        TemperaturePoint(direction="west", temp_celsius=965.0),
        TemperaturePoint(direction="north", temp_celsius=990.0),
    ]


def test_has_thermal_data_true_when_snapshots_present():
    snapshot = ThermalSnapshot(distance_mm=10.0, readings=_readings_with_center())
    frame = Frame(timestamp_ms=0, thermal_snapshots=[snapshot])
    assert frame.has_thermal_data is True


def test_has_thermal_data_false_when_no_snapshots():
    frame = Frame(timestamp_ms=0, thermal_snapshots=[])
    assert frame.has_thermal_data is False


def test_thermal_snapshot_distance_duplicates_rejected():
    snapshots = [
        ThermalSnapshot(distance_mm=10.0, readings=_readings_with_center()),
        ThermalSnapshot(distance_mm=10.0, readings=_readings_with_center()),
    ]
    with pytest.raises(ValidationError):
        Frame(timestamp_ms=0, thermal_snapshots=snapshots)


def test_thermal_snapshot_distance_out_of_order_rejected():
    snapshots = [
        ThermalSnapshot(distance_mm=20.0, readings=_readings_with_center()),
        ThermalSnapshot(distance_mm=10.0, readings=_readings_with_center()),
    ]
    with pytest.raises(ValidationError):
        Frame(timestamp_ms=0, thermal_snapshots=snapshots)


def test_thermal_missing_center_rejected():
    """ThermalSnapshot rejects readings without exactly one center direction."""
    with pytest.raises(ValidationError):
        ThermalSnapshot(distance_mm=10.0, readings=_readings_without_center())
