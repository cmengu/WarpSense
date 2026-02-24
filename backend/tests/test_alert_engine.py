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
