"""
Real-time alert engine. Three rules, time-based suppression, zero I/O in push_frame.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from realtime.alert_models import AlertPayload, FrameInput
from realtime.frame_buffer import SpeedFrameBuffer

logger = logging.getLogger(__name__)


def load_thresholds(config_path: str) -> dict:
    """Load and validate alert_thresholds.json. Raises FileNotFoundError or ValueError if invalid."""
    path = Path(config_path)
    if not path.is_absolute():
        # Resolve relative to backend/
        backend = Path(__file__).resolve().parent.parent
        path = backend / config_path
    if not path.exists():
        raise FileNotFoundError(f"alert_thresholds.json not found: {path}")
    data = json.loads(path.read_text())
    required = (
        "thermal_ns_warning",
        "thermal_ns_critical",
        "angle_deviation_warning",
        "angle_deviation_critical",
        "speed_drop_warning_pct",
        "speed_drop_critical_pct",
        "nominal_travel_angle",
        "suppression_ms",
        "voltage_lo_V",
        "voltage_sustain_ms",
        "crater_ramp_pct",
        "crater_ramp_min_ms",
        "crater_arc_on_min_ms",
        "porosity_speed_max_mm_per_min",
        "undercut_amps_min",
        "undercut_speed_min_mm_per_min",
        "lack_of_fusion_amps_max",
        "lack_of_fusion_speed_max_mm_per_min",
        "burn_through_amps_min",
        "burn_through_speed_max_mm_per_min",
        "sustained_repeat_ms",
    )
    for key in required:
        if data.get(key) is None:
            raise ValueError(f"threshold {key!r} is null in {path}")
    return data


class AlertEngine:
    """Evaluates three rules per frame. Time-based suppression per rule."""

    def __init__(
        self,
        config_path: str = "config/alert_thresholds.json",
        suppression_ms_override: int | None = None,
    ) -> None:
        self._cfg = load_thresholds(config_path)
        self._nominal_angle = float(self._cfg["nominal_travel_angle"])
        self._suppression_ms = (
            suppression_ms_override
            if suppression_ms_override is not None
            else int(self._cfg["suppression_ms"])
        )
        self._suppress_rule1_until = 0.0
        self._suppress_rule2_until = 0.0
        self._suppress_rule3_until = 0.0
        self._buffer = SpeedFrameBuffer()

    def push_frame(self, frame: FrameInput) -> AlertPayload | None:
        """Evaluate rules, return at most one alert per frame. Highest severity wins; tiebreak: lower rule number."""
        now_ms = (
            frame.timestamp_ms
            if frame.timestamp_ms is not None
            else time.time() * 1000.0
        )
        candidates: list[tuple[int, str, AlertPayload]] = []

        # Rule 1: NS thermal
        if now_ms >= self._suppress_rule1_until:
            abs_ns = abs(frame.ns_asymmetry)
            if abs_ns >= self._cfg["thermal_ns_critical"]:
                correction = (
                    "Reduce push angle — tilt back 3°" if frame.ns_asymmetry > 0 else "Increase push angle — tilt forward 3°"
                )
                candidates.append((1, "critical", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="rule1",
                    severity="critical",
                    message=f"Thermal asymmetry {frame.ns_asymmetry:+.1f}°C (critical)",
                    correction=correction,
                    timestamp_ms=now_ms,
                )))
                self._suppress_rule1_until = now_ms + self._suppression_ms
            elif abs_ns >= self._cfg["thermal_ns_warning"]:
                correction = (
                    "Reduce push angle — tilt back 3°" if frame.ns_asymmetry > 0 else "Increase push angle — tilt forward 3°"
                )
                candidates.append((1, "warning", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="rule1",
                    severity="warning",
                    message=f"Thermal asymmetry {frame.ns_asymmetry:+.1f}°C (warning)",
                    correction=correction,
                    timestamp_ms=now_ms,
                )))
                self._suppress_rule1_until = now_ms + self._suppression_ms

        # Rule 2: Travel angle
        if frame.travel_angle_degrees is not None and now_ms >= self._suppress_rule2_until:
            dev = abs(frame.travel_angle_degrees - self._nominal_angle)
            if dev >= self._cfg["angle_deviation_critical"]:
                correction = "Travel angle too steep — reduce to 12°" if frame.travel_angle_degrees > self._nominal_angle else "Travel angle too shallow — increase to 12°"
                candidates.append((2, "critical", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="rule2",
                    severity="critical",
                    message=f"Torch angle {frame.travel_angle_degrees:.1f}° vs {self._nominal_angle}° nominal (critical)",
                    correction=correction,
                    timestamp_ms=now_ms,
                )))
                self._suppress_rule2_until = now_ms + self._suppression_ms
            elif dev >= self._cfg["angle_deviation_warning"]:
                correction = "Travel angle too steep — reduce to 12°" if frame.travel_angle_degrees > self._nominal_angle else "Travel angle too shallow — increase to 12°"
                candidates.append((2, "warning", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="rule2",
                    severity="warning",
                    message=f"Torch angle {frame.travel_angle_degrees:.1f}° vs {self._nominal_angle}° nominal (warning)",
                    correction=correction,
                    timestamp_ms=now_ms,
                )))
                self._suppress_rule2_until = now_ms + self._suppression_ms

        # Rule 3: Speed drop
        if frame.travel_speed_mm_per_min is not None and now_ms >= self._suppress_rule3_until:
            self._buffer.push(frame.travel_speed_mm_per_min)
            pct = self._buffer.speed_change_pct()
            if pct is not None and pct < 0:
                drop = abs(pct)
                if drop >= self._cfg["speed_drop_critical_pct"]:
                    candidates.append((3, "critical", AlertPayload(
                        frame_index=frame.frame_index,
                        rule_triggered="rule3",
                        severity="critical",
                        message=f"Speed {frame.travel_speed_mm_per_min:.0f} mm/min — {drop:.1f}% drop (critical)",
                        correction="Speed critical — increase to 420mm/min",
                        timestamp_ms=now_ms,
                    )))
                    self._suppress_rule3_until = now_ms + self._suppression_ms
                elif drop >= self._cfg["speed_drop_warning_pct"]:
                    candidates.append((3, "warning", AlertPayload(
                        frame_index=frame.frame_index,
                        rule_triggered="rule3",
                        severity="warning",
                        message=f"Speed {frame.travel_speed_mm_per_min:.0f} mm/min — {drop:.1f}% drop (warning)",
                        correction="Slowing down — maintain pace",
                        timestamp_ms=now_ms,
                    )))
                    self._suppress_rule3_until = now_ms + self._suppression_ms

        if not candidates:
            return None
        # Highest severity wins; tiebreak: lower rule number (critical > warning, then rule 1 < 2 < 3)
        severity_rank = {"critical": 1, "warning": 0}
        candidates.sort(key=lambda x: (-severity_rank[x[1]], x[0]))
        return candidates[0][2]
