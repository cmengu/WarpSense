"""
Step 17: Comparison service edge case tests.
Tests compare_sessions with no overlap, partial overlap, different thermal distances,
no thermal data, identical sessions, and sparse thermal data.
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


def _readings(temp_celsius=400.0):
    return [
        TemperaturePoint(direction="center", temp_celsius=temp_celsius),
        TemperaturePoint(direction="north", temp_celsius=temp_celsius - 10),
        TemperaturePoint(direction="south", temp_celsius=temp_celsius - 20),
        TemperaturePoint(direction="east", temp_celsius=temp_celsius - 15),
        TemperaturePoint(direction="west", temp_celsius=temp_celsius - 25),
    ]


def _frame(timestamp_ms, amps=150.0, volts=22.0, angle_degrees=45.0, distances=None):
    snapshots = []
    if distances:
        snapshots = [
            ThermalSnapshot(distance_mm=d, readings=_readings(400 - d))
            for d in distances
        ]
    return Frame(
        timestamp_ms=timestamp_ms,
        amps=amps,
        volts=volts,
        angle_degrees=angle_degrees,
        thermal_snapshots=snapshots,
    )


def _session(session_id, frames):
    return Session(
        session_id=session_id,
        operator_id="op_01",
        start_time=datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=frames,
        frame_count=len(frames),
        disable_sensor_continuity_checks=True,
    )


# ---------------------------------------------------------------------------
# No shared timestamps
# ---------------------------------------------------------------------------


def test_no_shared_timestamps_returns_empty():
    """compare_sessions with offset sessions → shared_count=0, deltas=[]."""
    session_a = _session("a", [_frame(0), _frame(10), _frame(20)])
    session_b = _session("b", [_frame(1000), _frame(1010), _frame(1020)])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 0


# ---------------------------------------------------------------------------
# Partial timestamp overlap
# ---------------------------------------------------------------------------


def test_partial_timestamp_overlap():
    """Partial overlap → shared_count = overlap size."""
    session_a = _session("a", [_frame(0), _frame(10), _frame(20), _frame(30)])
    session_b = _session("b", [_frame(10), _frame(20), _frame(30), _frame(40)])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 3
    assert [d.timestamp_ms for d in deltas] == [10, 20, 30]


# ---------------------------------------------------------------------------
# Different thermal distances
# ---------------------------------------------------------------------------


def test_different_thermal_distances_thermal_deltas_empty():
    """Expert [10,20,30], novice [15,25,35] → thermal_deltas empty (no matching distance)."""
    dist_a = [10.0, 20.0, 30.0]
    dist_b = [15.0, 25.0, 35.0]
    session_a = _session(
        "a",
        [_frame(0, distances=dist_a), _frame(10, distances=dist_a)],
    )
    session_b = _session(
        "b",
        [_frame(0, distances=dist_b), _frame(10, distances=dist_b)],
    )
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 2
    for d in deltas:
        assert len(d.thermal_deltas) == 0


# ---------------------------------------------------------------------------
# One session has no thermal data
# ---------------------------------------------------------------------------


def test_one_session_no_thermal_data():
    """One session has no thermal data → thermal_deltas empty for all frames."""
    session_a = _session("a", [_frame(0, distances=[10]), _frame(10, distances=[10])])
    session_b = _session("b", [_frame(0), _frame(10)])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 2
    for d in deltas:
        assert len(d.thermal_deltas) == 0


# ---------------------------------------------------------------------------
# Both sessions have no thermal data
# ---------------------------------------------------------------------------


def test_both_sessions_no_thermal_data_no_crash():
    """Both sessions have no thermal data → no crash, thermal_deltas empty."""
    session_a = _session("a", [_frame(0), _frame(10)])
    session_b = _session("b", [_frame(0), _frame(10)])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 2
    for d in deltas:
        assert len(d.thermal_deltas) == 0
        assert d.amps_delta is not None or d.volts_delta is not None


# ---------------------------------------------------------------------------
# Identical sessions
# ---------------------------------------------------------------------------


def test_identical_sessions_all_deltas_zero():
    """Identical sessions → all deltas exactly 0."""
    frames = [_frame(0, distances=[10]), _frame(10, distances=[10])]
    session_a = _session("a", frames)
    session_b = _session("b", [  # same data, different session_id
        _frame(0, distances=[10]),
        _frame(10, distances=[10]),
    ])
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 2
    for d in deltas:
        assert d.amps_delta == 0.0
        assert d.volts_delta == 0.0
        assert d.angle_degrees_delta == 0.0
        for td in d.thermal_deltas:
            for r in td.readings:
                assert r.delta_temp_celsius == 0.0


# ---------------------------------------------------------------------------
# Different frame counts
# ---------------------------------------------------------------------------


def test_different_frame_counts_shared_count_min():
    """Expert 1500 frames, novice 500 frames → shared_count = 500."""
    frames_a = [_frame(t) for t in range(0, 15000, 10)]
    frames_b = [_frame(t) for t in range(0, 5000, 10)]
    session_a = _session("a", frames_a)
    session_b = _session("b", frames_b)
    deltas = compare_sessions(session_a, session_b)
    assert len(deltas) == 500
    assert deltas[-1].timestamp_ms == 4990


# ---------------------------------------------------------------------------
# Sparse thermal data
# ---------------------------------------------------------------------------


def test_sparse_thermal_data_thermal_deltas_only_at_matching_frames():
    """Novice thermal every 500ms vs expert every 100ms → thermal_deltas only at matching frames."""
    def make_expert():
        return _session(
            "expert",
            [_frame(t, distances=[10]) for t in range(0, 600, 10)],
        )

    def make_novice_sparse():
        frames = []
        for t in range(0, 600, 10):
            distances = [10] if t % 500 == 0 else None
            frames.append(_frame(t, distances=distances))
        return _session("novice", frames)

    session_a = make_expert()
    session_b = make_novice_sparse()
    deltas = compare_sessions(session_a, session_b)

    thermal_delta_count = sum(1 for d in deltas if len(d.thermal_deltas) > 0)
    assert thermal_delta_count == 2
    timestamps_with_thermal = [d.timestamp_ms for d in deltas if len(d.thermal_deltas) > 0]
    assert 0 in timestamps_with_thermal
    assert 500 in timestamps_with_thermal
