"""
Step 17: Heat dissipation calculator unit tests.
Tests calculate_heat_dissipation edge cases: null inputs, cooling/heating, zero rate,
variable interval, and integration with mock sessions.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.frame import Frame
from models.thermal import TemperaturePoint, ThermalSnapshot
from services.thermal_service import calculate_heat_dissipation


def _readings(center_temp: float):
    return [
        TemperaturePoint(direction="center", temp_celsius=center_temp),
        TemperaturePoint(direction="north", temp_celsius=center_temp - 10),
        TemperaturePoint(direction="south", temp_celsius=center_temp - 20),
        TemperaturePoint(direction="east", temp_celsius=center_temp - 15),
        TemperaturePoint(direction="west", temp_celsius=center_temp - 25),
    ]


def _frame(timestamp_ms: int, center_temp: float, with_thermal: bool = True) -> Frame:
    snapshots = []
    if with_thermal:
        snapshots = [ThermalSnapshot(distance_mm=10.0, readings=_readings(center_temp))]
    return Frame(timestamp_ms=timestamp_ms, thermal_snapshots=snapshots)


# ---------------------------------------------------------------------------
# None when center temp missing
# ---------------------------------------------------------------------------


def test_returns_none_when_prev_center_temp_none():
    prev = _frame(0, 500.0, with_thermal=False)
    curr = _frame(10, 480.0)
    assert calculate_heat_dissipation(prev, curr) is None


def test_returns_none_when_curr_center_temp_none():
    prev = _frame(0, 500.0)
    curr = _frame(10, 480.0, with_thermal=False)
    assert calculate_heat_dissipation(prev, curr) is None


def test_returns_none_when_both_temps_none():
    prev = _frame(0, 500.0, with_thermal=False)
    curr = _frame(10, 480.0, with_thermal=False)
    assert calculate_heat_dissipation(prev, curr) is None


def test_returns_none_when_prev_frame_none():
    curr = _frame(10, 480.0)
    assert calculate_heat_dissipation(None, curr) is None


# ---------------------------------------------------------------------------
# Cooling (positive rate)
# ---------------------------------------------------------------------------


def test_returns_positive_rate_when_cooling():
    """prev=500, curr=480, interval=0.1 → 200°C/sec."""
    prev = _frame(0, 500.0)
    curr = _frame(10, 480.0)
    result = calculate_heat_dissipation(prev, curr)
    assert result == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# Heating (negative rate)
# ---------------------------------------------------------------------------


def test_returns_negative_rate_when_heating():
    """prev=480, curr=520, interval=0.1 → -400°C/sec."""
    prev = _frame(0, 480.0)
    curr = _frame(10, 520.0)
    result = calculate_heat_dissipation(prev, curr)
    assert result == pytest.approx(-400.0)


# ---------------------------------------------------------------------------
# Zero rate
# ---------------------------------------------------------------------------


def test_returns_zero_rate_when_unchanged():
    """prev=500, curr=500 → 0°C/sec."""
    prev = _frame(0, 500.0)
    curr = _frame(10, 500.0)
    result = calculate_heat_dissipation(prev, curr)
    assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Large and small temperature change
# ---------------------------------------------------------------------------


def test_large_cooling_rate():
    """prev=600, curr=200 → 4000°C/sec."""
    prev = _frame(0, 600.0)
    curr = _frame(10, 200.0)
    result = calculate_heat_dissipation(prev, curr)
    assert result == pytest.approx(4000.0)


def test_small_temperature_change():
    """prev=500.0, curr=499.5 → 5°C/sec."""
    prev = _frame(0, 500.0)
    curr = _frame(10, 499.5)
    result = calculate_heat_dissipation(prev, curr)
    assert result == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Variable interval
# ---------------------------------------------------------------------------


def test_50ms_interval():
    """prev=500, curr=490, interval=0.05 → 200°C/sec."""
    prev = _frame(0, 500.0)
    curr = _frame(10, 490.0)
    result = calculate_heat_dissipation(
        prev, curr, sample_interval_seconds=0.05
    )
    assert result == pytest.approx(200.0)


def test_200ms_interval():
    """prev=500, curr=460, interval=0.2 → 200°C/sec."""
    prev = _frame(0, 500.0)
    curr = _frame(10, 460.0)
    result = calculate_heat_dissipation(
        prev, curr, sample_interval_seconds=0.2
    )
    assert result == pytest.approx(200.0)


def test_raises_zero_division_error_when_interval_zero():
    prev = _frame(0, 500.0)
    curr = _frame(10, 490.0)
    with pytest.raises(ZeroDivisionError):
        calculate_heat_dissipation(
            prev, curr, sample_interval_seconds=0.0
        )


def test_negative_interval_produces_inverted_sign():
    """Negative interval inverts sign (documents behavior)."""
    prev = _frame(0, 500.0)
    curr = _frame(10, 490.0)
    result = calculate_heat_dissipation(
        prev, curr, sample_interval_seconds=-0.1
    )
    assert result == pytest.approx(-100.0)


# ---------------------------------------------------------------------------
# Integration tests with mock sessions
# ---------------------------------------------------------------------------


def test_first_thermal_frame_has_none_dissipation():
    """First thermal frame in session has None heat_dissipation."""
    from data.mock_sessions import generate_expert_session

    session = generate_expert_session()
    first_frame = session.frames[0]
    assert first_frame.has_thermal_data
    assert first_frame.heat_dissipation_rate_celsius_per_sec is None


def test_second_thermal_frame_has_non_none_dissipation():
    """Second thermal frame in session has non-None heat_dissipation."""
    from data.mock_sessions import generate_expert_session

    session = generate_expert_session()
    thermal_frames = [f for f in session.frames if f.has_thermal_data]
    assert len(thermal_frames) >= 2
    assert thermal_frames[1].heat_dissipation_rate_celsius_per_sec is not None


def test_thermal_frame_after_gap_has_none_dissipation():
    """Thermal frame after gap (novice session) has None heat_dissipation."""
    from data.mock_sessions import generate_novice_session

    session = generate_novice_session()
    thermal_frames = [f for f in session.frames if f.has_thermal_data]
    for i in range(1, len(thermal_frames)):
        interval = thermal_frames[i].timestamp_ms - thermal_frames[i - 1].timestamp_ms
        if interval > 100:
            assert thermal_frames[i].heat_dissipation_rate_celsius_per_sec is None
            return
    pytest.fail("Novice session should have a thermal gap")


def test_non_thermal_frames_have_none_dissipation():
    """Non-thermal frames have None heat_dissipation."""
    from data.mock_sessions import generate_expert_session

    session = generate_expert_session()
    non_thermal = [f for f in session.frames if not f.has_thermal_data]
    assert len(non_thermal) > 0
    for f in non_thermal:
        assert f.heat_dissipation_rate_celsius_per_sec is None


def test_expert_session_dissipation_mostly_positive():
    """Expert session dissipation is mostly positive (cooling)."""
    from data.mock_sessions import generate_expert_session

    session = generate_expert_session()
    thermal_frames = [f for f in session.frames if f.has_thermal_data]
    dissipations = [
        f.heat_dissipation_rate_celsius_per_sec
        for f in thermal_frames[50:100]
        if f.heat_dissipation_rate_celsius_per_sec is not None
    ]
    assert len(dissipations) > 0
    positive_ratio = sum(1 for d in dissipations if d > 0) / len(dissipations)
    # Expert is predominantly cooling, but small stable power oscillations can yield
    # brief heating intervals (negative values). We only require "more positive than negative".
    assert positive_ratio > 0.5


def test_novice_session_dissipation_higher_variance():
    """Novice session dissipation has higher variance than expert."""
    from data.mock_sessions import generate_expert_session, generate_novice_session

    expert = generate_expert_session()
    novice = generate_novice_session()

    def variance(dissipations):
        if len(dissipations) < 2:
            return 0.0
        mean = sum(dissipations) / len(dissipations)
        return sum((d - mean) ** 2 for d in dissipations) / len(dissipations)

    expert_diss = [
        f.heat_dissipation_rate_celsius_per_sec
        for f in expert.frames
        if f.heat_dissipation_rate_celsius_per_sec is not None
    ]
    novice_diss = [
        f.heat_dissipation_rate_celsius_per_sec
        for f in novice.frames
        if f.heat_dissipation_rate_celsius_per_sec is not None
    ]
    assert len(expert_diss) > 0 and len(novice_diss) > 0
    assert variance(novice_diss) > variance(expert_diss)
