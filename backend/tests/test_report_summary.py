"""
Unit tests for report summary aggregator.

Tests compute_report_summary with synthetic frames and alerts:
- Run-length collapse (one entry per travel angle excursion run)
- Heat input, arc termination, defect counts
- AlertPayload.message maps to ExcursionEntry.notes
- process_type mapping: aluminum, mig, None → aluminum_spray thresholds
"""

import pytest

from models.frame import Frame
from realtime.alert_models import AlertPayload
from scoring.report_summary import (
    ExcursionEntry,
    ReportSummary,
    compute_report_summary,
)


# ---------------------------------------------------------------------------
# Run-length collapse
# ---------------------------------------------------------------------------


def test_single_run_collapses_to_one_entry():
    """5 consecutive excursion frames → 1 ExcursionEntry, duration_ms=40."""
    frames = [
        Frame(
            timestamp_ms=i * 10,
            travel_angle_degrees=40.0,
            heat_input_kj_per_mm=0.7,
            arc_termination_type="crater_fill_present",
        )
        for i in range(5)
    ]
    r = compute_report_summary("s1", frames, [], "aluminum")
    assert r.session_id == "s1"
    assert r.heat_input_mean_kj_per_mm == 0.7
    assert len(r.excursions) == 1
    assert r.excursions[0].duration_ms == 40  # last 40 - first 0
    assert r.excursions[0].parameter_value == 28.0  # |40 - 12| = 28
    assert r.travel_angle_excursion_count == 5


def test_two_runs_split_by_in_range_frame():
    """In-range frame (angle=15) splits run; single-frame run has duration_ms=0."""
    frames = [
        Frame(
            timestamp_ms=0,
            travel_angle_degrees=40.0,
            heat_input_kj_per_mm=0.7,
            arc_termination_type="crater_fill_present",
        ),
        Frame(
            timestamp_ms=10,
            travel_angle_degrees=41.0,
            heat_input_kj_per_mm=0.7,
            arc_termination_type="crater_fill_present",
        ),
        Frame(
            timestamp_ms=20,
            travel_angle_degrees=15.0,
            heat_input_kj_per_mm=0.7,
            arc_termination_type="crater_fill_present",
        ),
        Frame(
            timestamp_ms=30,
            travel_angle_degrees=50.0,
            heat_input_kj_per_mm=0.7,
            arc_termination_type="crater_fill_present",
        ),
    ]
    r = compute_report_summary("s2", frames, [], "aluminum")
    assert len(r.excursions) == 2
    assert r.excursions[0].timestamp_ms == 0
    assert r.excursions[0].duration_ms == 10
    assert r.excursions[1].timestamp_ms == 30
    assert r.excursions[1].duration_ms == 0
    assert r.travel_angle_excursion_count == 3


# ---------------------------------------------------------------------------
# Empty frames, no arc terminations, config load
# ---------------------------------------------------------------------------


def test_empty_frames_returns_valid_summary():
    """Empty frames → no heat/travel, zero counts, empty excursions."""
    r = compute_report_summary("s_empty", [], [], "mig")
    assert r.session_id == "s_empty"
    assert r.heat_input_mean_kj_per_mm is None
    assert r.heat_input_compliant is False
    assert r.travel_angle_excursion_count == 0
    assert r.total_arc_terminations == 0
    assert r.crater_fill_rate_pct == 0.0
    assert r.excursions == []
    assert r.heat_input_wps_min == 0.5
    assert r.heat_input_wps_max == 0.9


def test_no_arc_terminations():
    """Frames without arc_termination_type → total=0, rate=0."""
    frames = [
        Frame(timestamp_ms=0, heat_input_kj_per_mm=0.7),
    ]
    r = compute_report_summary("s_no_term", frames, [], "aluminum")
    assert r.total_arc_terminations == 0
    assert r.no_crater_fill_count == 0
    assert r.crater_fill_rate_pct == 0.0


def test_config_load_aluminum_spray():
    """report_thresholds.json aluminum_spray entry is used."""
    frames = [
        Frame(timestamp_ms=0, heat_input_kj_per_mm=0.7),
    ]
    r = compute_report_summary("s", frames, [], "aluminum")
    assert r.heat_input_wps_min == 0.5
    assert r.heat_input_wps_max == 0.9
    assert r.heat_input_compliant is True
    assert r.travel_angle_threshold_deg == 25.0


# ---------------------------------------------------------------------------
# AlertPayload.message → ExcursionEntry.notes
# ---------------------------------------------------------------------------


def test_alert_message_maps_to_excursion_notes():
    """AlertPayload.message appears in ExcursionEntry.notes."""
    alert = AlertPayload(
        frame_index=0,
        rule_triggered="travel_angle_excursion",
        severity="warning",
        message="Travel angle 45° exceeds threshold",
        correction="Return to nominal 12°",
        timestamp_ms=100.0,
    )
    r = compute_report_summary("s", [], [alert], "aluminum")
    assert len(r.excursions) == 1
    assert r.excursions[0].source == "alert"
    assert r.excursions[0].notes == "Travel angle 45° exceeds threshold"
    assert r.excursions[0].parameter_value is None
    assert r.excursions[0].threshold_value is None
    assert r.defect_counts_by_type == {"travel_angle_excursion": 1}
    assert r.total_defect_alerts == 1


# ---------------------------------------------------------------------------
# process_type mapping
# ---------------------------------------------------------------------------


def test_process_type_aluminum_resolves_to_aluminum_spray():
    """process_type='aluminum' uses aluminum_spray thresholds."""
    frames = [Frame(timestamp_ms=0, heat_input_kj_per_mm=0.7)]
    r = compute_report_summary("s", frames, [], "aluminum")
    assert r.heat_input_wps_min == 0.5
    assert r.heat_input_wps_max == 0.9


def test_process_type_mig_resolves_to_aluminum_spray():
    """process_type='mig' falls back to aluminum_spray (MVP)."""
    frames = [Frame(timestamp_ms=0, heat_input_kj_per_mm=0.7)]
    r = compute_report_summary("s", frames, [], "mig")
    assert r.heat_input_wps_min == 0.5
    assert r.heat_input_wps_max == 0.9


def test_process_type_none_resolves_to_aluminum_spray():
    """process_type=None falls back to aluminum_spray."""
    frames = [Frame(timestamp_ms=0, heat_input_kj_per_mm=0.7)]
    r = compute_report_summary("s", frames, [], None)
    assert r.heat_input_wps_min == 0.5
    assert r.heat_input_wps_max == 0.9


def test_process_type_unknown_resolves_to_aluminum_spray():
    """Unknown process_type (e.g. 'flux_core') falls back to aluminum_spray."""
    frames = [Frame(timestamp_ms=0, heat_input_kj_per_mm=0.7)]
    r = compute_report_summary("s", frames, [], "flux_core")
    assert r.heat_input_wps_min == 0.5
    assert r.heat_input_wps_max == 0.9


# ---------------------------------------------------------------------------
# Heat input compliance
# ---------------------------------------------------------------------------


def test_heat_input_compliant_in_range():
    """Mean 0.7 in [0.5, 0.9] → compliant."""
    frames = [
        Frame(timestamp_ms=i * 10, heat_input_kj_per_mm=0.7)
        for i in range(5)
    ]
    r = compute_report_summary("s", frames, [], "aluminum")
    assert r.heat_input_compliant is True
    assert r.heat_input_mean_kj_per_mm == 0.7


def test_heat_input_non_compliant_below_min():
    """Mean 0.4 < 0.5 → not compliant."""
    frames = [
        Frame(timestamp_ms=i * 10, heat_input_kj_per_mm=0.4)
        for i in range(5)
    ]
    r = compute_report_summary("s", frames, [], "aluminum")
    assert r.heat_input_compliant is False


def test_heat_input_non_compliant_above_max():
    """Mean 1.0 > 0.9 → not compliant."""
    frames = [
        Frame(timestamp_ms=i * 10, heat_input_kj_per_mm=1.0)
        for i in range(5)
    ]
    r = compute_report_summary("s", frames, [], "aluminum")
    assert r.heat_input_compliant is False


# ---------------------------------------------------------------------------
# Arc termination counts
# ---------------------------------------------------------------------------


def test_arc_termination_crater_fill_rate():
    """3 crater_fill, 1 no_crater_fill → 75% rate."""
    frames = [
        Frame(timestamp_ms=0, arc_termination_type="crater_fill_present"),
        Frame(timestamp_ms=10, arc_termination_type="crater_fill_present"),
        Frame(timestamp_ms=20, arc_termination_type="crater_fill_present"),
        Frame(timestamp_ms=30, arc_termination_type="no_crater_fill"),
    ]
    r = compute_report_summary("s", frames, [], "aluminum")
    assert r.total_arc_terminations == 4
    assert r.no_crater_fill_count == 1
    assert r.crater_fill_rate_pct == 75.0


# ---------------------------------------------------------------------------
# Merged excursions: frame-derived + alerts, sorted by timestamp
# ---------------------------------------------------------------------------


def test_excursions_merged_and_sorted():
    """Frame-derived and alert entries merged, sorted by timestamp_ms."""
    frames = [
        Frame(
            timestamp_ms=50,
            travel_angle_degrees=50.0,
            heat_input_kj_per_mm=0.7,
            arc_termination_type="crater_fill_present",
        ),
    ]
    alert = AlertPayload(
        frame_index=0,
        rule_triggered="travel_speed",
        severity="warning",
        message="Slow travel",
        correction="Speed up",
        timestamp_ms=10.0,
    )
    r = compute_report_summary("s", frames, [alert], "aluminum")
    assert len(r.excursions) == 2
    # Alert at 10ms, frame-derived at 50ms
    assert r.excursions[0].timestamp_ms == 10
    assert r.excursions[0].source == "alert"
    assert r.excursions[1].timestamp_ms == 50
    assert r.excursions[1].source == "frame_derived"
