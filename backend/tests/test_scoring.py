"""Unit tests for decomposed scoring (heat input, torch angle, arc termination, defect, interpass)."""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from realtime.alert_models import AlertPayload
from scoring.components import (
    calculate_arc_termination_component,
    calculate_defect_alert_component,
    calculate_interpass_component,
    calculate_torch_angle_component,
)
from scoring.heat_input import calculate_heat_input_component
from scoring.scorer import score_session_decomposed, _build_alerts_from_frames


def test_heat_input_in_range_no_excursions():
    """200A x 24V x 60 / (250 mm/min x 1000) = 1.152 kJ/mm — clearly inside 0.9–1.5 range."""
    cfg = {"wps_heat_input_min_kj_per_mm": 0.9, "wps_heat_input_max_kj_per_mm": 1.5}
    f = MagicMock(amps=200, volts=24, travel_speed_mm_per_min=250, timestamp_ms=0)
    r = calculate_heat_input_component([f], cfg)
    assert r.passed and len(r.excursions) == 0


def test_heat_input_below_wps_flags_excursion():
    cfg = {"wps_heat_input_min_kj_per_mm": 0.9, "wps_heat_input_max_kj_per_mm": 1.5}
    f = MagicMock(amps=180, volts=22, travel_speed_mm_per_min=400, timestamp_ms=0)
    r = calculate_heat_input_component([f], cfg)
    assert not r.passed and len(r.excursions) >= 1


def test_torch_angle_drag_flags_excursion():
    cfg = {"torch_angle_max_degrees": 20.0, "interpass_min_ms": 45000}
    f = MagicMock(travel_angle_degrees=-5.0, timestamp_ms=500, amps=155)
    r = calculate_torch_angle_component([f], cfg)
    assert len(r.excursions) >= 1


def test_arc_termination_no_crater_fill_fails():
    cfg = {"torch_angle_max_degrees": 20.0, "interpass_min_ms": 45000}
    f = MagicMock(arc_termination_type="no_crater_fill", timestamp_ms=1000)
    r = calculate_arc_termination_component([f], cfg)
    assert not r.passed


def test_defect_alert_porosity_fails_component():
    cfg = {}
    a = AlertPayload(
        frame_index=0,
        rule_triggered="porosity",
        severity="critical",
        message="x",
        correction="y",
        timestamp_ms=100,
    )
    r = calculate_defect_alert_component([a], cfg)
    assert not r.passed


def test_defect_alert_oxide_inclusion_passes_component():
    """Warnings (oxide_inclusion) → score penalty only, not automatic fail."""
    cfg = {}
    a = AlertPayload(
        frame_index=0,
        rule_triggered="oxide_inclusion",
        severity="warning",
        message="x",
        correction="y",
        timestamp_ms=100,
    )
    r = calculate_defect_alert_component([a], cfg)
    assert r.passed


def test_interpass_below_minimum_flags():
    cfg = {"interpass_min_ms": 45000}
    f1 = MagicMock(amps=150, timestamp_ms=0)
    f2 = MagicMock(amps=0, timestamp_ms=10000)
    f3 = MagicMock(amps=150, timestamp_ms=20000)
    r = calculate_interpass_component([f1, f2, f3], cfg)
    assert len(r.excursions) >= 1


def test_build_alerts_from_frames_returns_list():
    """_build_alerts_from_frames returns list; does not crash on real frame-like objects."""
    f = SimpleNamespace(
        amps=200.0,
        volts=24.0,
        travel_speed_mm_per_min=250.0,
        timestamp_ms=0,
        travel_angle_degrees=12.0,
    )
    result = _build_alerts_from_frames([f])
    assert isinstance(result, list)


def test_session_score_overall_is_weighted_mean():
    cfg = {
        "heat_input_weight": 0.35,
        "torch_angle_weight": 0.25,
        "arc_termination_weight": 0.25,
        "defect_alert_weight": 0.10,
        "interpass_weight": 0.05,
        "wps_heat_input_min_kj_per_mm": 0.9,
        "wps_heat_input_max_kj_per_mm": 1.5,
        "torch_angle_max_degrees": 20.0,
        "interpass_min_ms": 45000,
    }
    frames = [
        MagicMock(
            amps=200,
            volts=24,
            travel_speed_mm_per_min=250,
            timestamp_ms=i * 10,
            travel_angle_degrees=12,
            arc_termination_type=None,
        )
        for i in range(20)
    ]
    dec = score_session_decomposed(frames, [], "s1", cfg=cfg)
    assert 0 <= dec.overall_score <= 1.0
