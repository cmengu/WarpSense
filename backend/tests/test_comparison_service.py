"""
Tests for comparison service.
This is really critical
it only aligns frames by timestamp and outputs structured deltas so you can see exactly how two welding sessions differ frame-by-frame, including thermal, electrical, and mechanical metrics.
but If the welding patterns differ (e.g., different weld lengths, speeds, or number of passes), the timestamps won’t match, and most frames will be skipped. Comparing only “shared timestamps” becomes meaningless because the welds are not aligned.
point to change next time
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.frame import Frame
from models.session import Session
from models.thermal import TemperaturePoint, ThermalSnapshot
from services.comparison_service import compare_sessions


def _readings(temp_celsius: float) -> list[TemperaturePoint]:
    return [
        TemperaturePoint(direction="center", temp_celsius=temp_celsius),
        TemperaturePoint(direction="north", temp_celsius=temp_celsius - 10),
        TemperaturePoint(direction="south", temp_celsius=temp_celsius - 20),
        TemperaturePoint(direction="east", temp_celsius=temp_celsius - 15),
        TemperaturePoint(direction="west", temp_celsius=temp_celsius - 25),
    ]


def _frame(timestamp_ms: int, amps: float, volts: float, temp_celsius: float) -> Frame:
    snapshot = ThermalSnapshot(distance_mm=10.0, readings=_readings(temp_celsius))
    return Frame(
        timestamp_ms=timestamp_ms,
        amps=amps,
        volts=volts,
        thermal_snapshots=[snapshot],
    )


def _session(session_id: str, frames: list[Frame]) -> Session:
    return Session(
        session_id=session_id,
        operator_id="operator-compare",
        start_time=datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="test-weld",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=frames,
        frame_count=len(frames),
    )


def test_compare_expert_vs_expert():
    session_a = _session("a", [_frame(0, 100.0, 10.0, 1000.0)])
    session_b = _session("b", [_frame(0, 98.0, 9.5, 990.0)])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 1
    assert deltas[0].amps_delta == pytest.approx(2.0)


def test_compare_novice_vs_novice():
    session_a = _session("a", [_frame(0, 110.0, 10.0, 1000.0)])
    session_b = _session("b", [_frame(0, 105.0, 10.0, 995.0)])
    deltas = compare_sessions(session_a, session_b)
    assert deltas[0].volts_delta == pytest.approx(0.0)


def test_compare_expert_vs_novice():
    session_a = _session("a", [_frame(0, 120.0, 11.0, 1000.0)])
    session_b = _session("b", [_frame(0, 100.0, 10.0, 980.0)])
    deltas = compare_sessions(session_a, session_b)
    assert deltas[0].amps_delta == pytest.approx(20.0)


def test_timestamp_alignment_handles_missing_frames():
    session_a = _session("a", [_frame(0, 100.0, 10.0, 1000.0), _frame(10, 102.0, 10.2, 990.0)])
    session_b = _session("b", [_frame(10, 100.0, 10.0, 990.0)])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 1
    assert deltas[0].timestamp_ms == 10


def test_sessions_with_different_durations():
    session_a = _session("a", [_frame(0, 100.0, 10.0, 1000.0), _frame(10, 102.0, 10.2, 990.0)])
    session_b = _session("b", [_frame(0, 100.0, 10.0, 1000.0)])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 1
    assert deltas[0].timestamp_ms == 0
