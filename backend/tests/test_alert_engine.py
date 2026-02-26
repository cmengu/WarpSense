"""
Tests for realtime alert engine.
"""

from __future__ import annotations

import time
import pytest

from realtime.alert_engine import AlertEngine, load_thresholds
from realtime.alert_models import FrameInput
from realtime.frame_buffer import SpeedFrameBuffer


def test_load_thresholds_missing_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_thresholds("nonexistent/path.json")


def test_rule1_positive_ns_tilt_back() -> None:
    """ns positive and above threshold → correction contains 'tilt back'."""
    engine = AlertEngine("config/alert_thresholds.json")
    frame = FrameInput(
        frame_index=0,
        travel_angle_degrees=12.0,
        travel_speed_mm_per_min=450.0,
        ns_asymmetry=25.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "rule1"
    assert "tilt back" in alert.correction


def test_rule1_negative_ns_tilt_forward() -> None:
    """ns negative and above threshold → correction contains 'tilt forward'."""
    engine = AlertEngine("config/alert_thresholds.json")
    frame = FrameInput(
        frame_index=0,
        travel_angle_degrees=12.0,
        travel_speed_mm_per_min=450.0,
        ns_asymmetry=-25.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "rule1"
    assert "tilt forward" in alert.correction


def test_frame_buffer_speed_change_pct() -> None:
    """speed_change_pct = (current - speed_10_ago) / speed_10_ago * 100."""
    buf = SpeedFrameBuffer()
    for i in range(10):
        buf.push(100.0)  # 10 frames at 100
    buf.push(90.0)  # frame 11: dropped 10%
    pct = buf.speed_change_pct()
    assert pct is not None
    assert abs(pct - (-10.0)) < 0.01
    buf.push(110.0)  # frame 12: +10% vs frame 2 (100)
    pct = buf.speed_change_pct()
    assert pct is not None
    assert abs(pct - 10.0) < 0.01


def test_benchmark_push_frame_p99_under_50ms() -> None:
    """Benchmark 1000 push_frame calls. Use fresh AlertEngine per call; frame_index=i."""
    config_path = "config/alert_thresholds.json"
    latencies: list[float] = []
    for i in range(1000):
        engine = AlertEngine(config_path)
        frame = FrameInput(
            frame_index=i,
            travel_angle_degrees=18.0,
            travel_speed_mm_per_min=300.0,
            ns_asymmetry=20.0,
        )
        t0 = time.perf_counter()
        engine.push_frame(frame)
        latencies.append(time.perf_counter() - t0)
    latencies.sort()
    p99_idx = int(0.99 * len(latencies)) - 1
    p99 = latencies[max(0, p99_idx)]
    assert p99 < 0.05, f"p99 latency {p99*1000:.2f}ms exceeds 50ms"


# --- Defect rule tests (Step 15) ---
# Use config/alert_thresholds_defect_test.json for defect-only tests to avoid rule 1–2
# firing on negative angles (angle_deviation_critical=90 keeps -5° within range).

DEFECT_CONFIG = "config/alert_thresholds_defect_test.json"
DEFAULT_CONFIG = "config/alert_thresholds.json"


def test_porosity_fires_when_drag_and_low_speed() -> None:
    """Porosity fires when travel_angle < 0 and speed < porosity_speed_max."""
    engine = AlertEngine(DEFECT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        travel_angle_degrees=-5.0,
        travel_speed_mm_per_min=200.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "porosity"


def test_porosity_does_not_fire_when_angle_positive() -> None:
    """Porosity does not fire when travel_angle >= 0."""
    engine = AlertEngine(DEFECT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        travel_angle_degrees=5.0,
        travel_speed_mm_per_min=200.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    # May fire other rules; must not fire porosity
    assert alert is None or alert.rule_triggered != "porosity"


def test_arc_instability_skips_when_volts_none(caplog: pytest.LogCaptureFixture) -> None:
    """When volts is None, arc_instability logs exactly one warning and skips."""
    import logging

    caplog.set_level(logging.WARNING)
    engine = AlertEngine(DEFECT_CONFIG)
    for i in range(5):
        frame = FrameInput(
            frame_index=i,
            volts=None,
            ns_asymmetry=0.0,
            travel_angle_degrees=12.0,
            travel_speed_mm_per_min=450.0,
            timestamp_ms=float(i * 10),
        )
        engine.push_frame(frame)
    warns = [m for m in caplog.messages if "arc_instability" in m and "volts" in m]
    assert len(warns) == 1, f"Expected exactly one volts-missing warning, got {len(warns)}"


def test_crater_crack_fires_on_abrupt_drop() -> None:
    """Crater crack fires when amps drops abruptly to 0 after 60 frames at 150A (arc on >= 500ms)."""
    engine = AlertEngine(DEFAULT_CONFIG)
    for i in range(60):
        engine.push_frame(
            FrameInput(
                frame_index=i,
                amps=150.0,
                ns_asymmetry=0.0,
                travel_angle_degrees=12.0,
                travel_speed_mm_per_min=450.0,
                timestamp_ms=float(i * 10),
            )
        )
    alert = engine.push_frame(
        FrameInput(
            frame_index=60,
            amps=0.0,
            ns_asymmetry=0.0,
            travel_angle_degrees=12.0,
            travel_speed_mm_per_min=450.0,
            timestamp_ms=600.0,
        )
    )
    assert alert is not None
    assert alert.rule_triggered == "crater_crack"


def test_crater_crack_does_not_fire_after_amps_dropout() -> None:
    """Crater crack does not fire when amps=None resets buffer between arc-on and amps=0."""
    engine = AlertEngine(DEFAULT_CONFIG)
    for i in range(60):
        engine.push_frame(
            FrameInput(
                frame_index=i,
                amps=150.0,
                ns_asymmetry=0.0,
                travel_angle_degrees=12.0,
                travel_speed_mm_per_min=450.0,
                timestamp_ms=float(i * 10),
            )
        )
    # Dropout: amps=None resets crater buffer, clearing arc history
    for i in range(5):
        engine.push_frame(
            FrameInput(
                frame_index=60 + i,
                amps=None,
                ns_asymmetry=0.0,
                travel_angle_degrees=12.0,
                travel_speed_mm_per_min=450.0,
                timestamp_ms=600.0 + i * 10,
            )
        )
    alert = engine.push_frame(
        FrameInput(
            frame_index=65,
            amps=0.0,
            ns_asymmetry=0.0,
            travel_angle_degrees=12.0,
            travel_speed_mm_per_min=450.0,
            timestamp_ms=650.0,
        )
    )
    assert alert is None or alert.rule_triggered != "crater_crack"


def test_crater_crack_does_not_fire_when_not_armed() -> None:
    """Crater crack does not fire when arc on < 500ms (5 frames at 10ms = 50ms)."""
    engine = AlertEngine(DEFAULT_CONFIG)
    for i in range(5):
        engine.push_frame(
            FrameInput(
                frame_index=i,
                amps=150.0,
                ns_asymmetry=0.0,
                travel_angle_degrees=12.0,
                travel_speed_mm_per_min=450.0,
                timestamp_ms=float(i * 10),
            )
        )
    alert = engine.push_frame(
        FrameInput(
            frame_index=5,
            amps=0.0,
            ns_asymmetry=0.0,
            travel_angle_degrees=12.0,
            travel_speed_mm_per_min=450.0,
            timestamp_ms=50.0,
        )
    )
    # abrupt is None when not armed
    assert alert is None or alert.rule_triggered != "crater_crack"


def test_oxide_inclusion_fires_when_angle_negative() -> None:
    """Oxide inclusion fires when travel_angle < 0 (argon trailing)."""
    engine = AlertEngine(DEFECT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        travel_angle_degrees=-3.0,
        travel_speed_mm_per_min=300.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "oxide_inclusion"


def test_oxide_suppressed_when_porosity_fires() -> None:
    """When angle<0 and speed<250, porosity fires; oxide must not fire same frame (suppressed)."""
    engine = AlertEngine(DEFECT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        travel_angle_degrees=-5.0,
        travel_speed_mm_per_min=200.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "porosity"
    # Oxide would also match angle<0, but porosity sets _suppress_oxide_until, so we get porosity


def test_undercut_fires_when_high_amps_and_speed() -> None:
    """Undercut fires when amps > 210 and speed > 500."""
    engine = AlertEngine(DEFAULT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        amps=220.0,
        travel_speed_mm_per_min=550.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "undercut"


def test_lack_of_fusion_fires_on_low_amps() -> None:
    """Lack of fusion (amps) fires when amps < 140."""
    engine = AlertEngine(DEFAULT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        amps=120.0,
        travel_speed_mm_per_min=300.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "lack_of_fusion_amps"


def test_lack_of_fusion_fires_on_high_speed() -> None:
    """Lack of fusion (speed) fires when speed > 520."""
    engine = AlertEngine(DEFAULT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        amps=150.0,
        travel_speed_mm_per_min=550.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "lack_of_fusion_speed"


def test_burn_through_fires_when_high_amps_low_speed() -> None:
    """Burn-through fires when amps > 220 and speed < 200."""
    engine = AlertEngine(DEFAULT_CONFIG)
    frame = FrameInput(
        frame_index=0,
        amps=230.0,
        travel_speed_mm_per_min=150.0,
        ns_asymmetry=0.0,
        timestamp_ms=0.0,
    )
    alert = engine.push_frame(frame)
    assert alert is not None
    assert alert.rule_triggered == "burn_through"
