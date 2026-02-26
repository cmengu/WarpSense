"""
Real-time alert engine. Three rules, time-based suppression, zero I/O in push_frame.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from realtime.alert_models import AlertPayload, FrameInput
from realtime.frame_buffer import (
    CurrentRampDownBuffer,
    SpeedFrameBuffer,
    VoltageSustainBuffer,
)

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
        # Defect rules (4–11)
        self._suppress_porosity_until = 0.0
        self._suppress_oxide_until = 0.0
        self._voltage_buffer = VoltageSustainBuffer(
            float(self._cfg["voltage_lo_V"]),
            float(self._cfg["voltage_sustain_ms"]),
        )
        self._suppress_arc_instability_until = 0.0
        self._warned_volts_missing = False
        self._crater_buffer = CurrentRampDownBuffer(
            float(self._cfg["crater_ramp_pct"]),
            float(self._cfg["crater_ramp_min_ms"]),
            float(self._cfg["crater_arc_on_min_ms"]),
        )
        self._suppress_crater_until = 0.0
        self._warned_amps_missing_crater = False
        self._suppress_undercut_until = 0.0
        self._warned_amps_missing_undercut = False
        self._suppress_lof_amps_until = 0.0
        self._suppress_lof_speed_until = 0.0
        self._suppress_burn_through_until = 0.0
        self._warned_amps_missing_burn_through = False

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

        # Rule 4: Porosity (spike)
        if now_ms >= self._suppress_porosity_until:
            if frame.travel_angle_degrees is not None and frame.travel_speed_mm_per_min is not None:
                if frame.travel_angle_degrees < 0 and frame.travel_speed_mm_per_min < self._cfg["porosity_speed_max_mm_per_min"]:
                    candidates.append((4, "critical", AlertPayload(
                        frame_index=frame.frame_index,
                        rule_triggered="porosity",
                        severity="critical",
                        message="Porosity risk: drag angle and low speed",
                        correction="Increase travel angle to push and speed to 250+ mm/min",
                        timestamp_ms=now_ms,
                    )))
                    self._suppress_porosity_until = now_ms + self._suppression_ms
                    self._suppress_oxide_until = now_ms + self._suppression_ms

        # Rule 5: Arc instability (sustained) — push every frame (buffer handles None); warn when None
        sustained = self._voltage_buffer.push(now_ms, frame.volts)
        if frame.volts is None:
            if not self._warned_volts_missing:
                logger.warning("arc_instability requires volts; skipping (frame_index=%d)", frame.frame_index)
                self._warned_volts_missing = True
        elif sustained and now_ms >= self._suppress_arc_instability_until:
            candidates.append((5, "critical", AlertPayload(
                frame_index=frame.frame_index,
                rule_triggered="arc_instability",
                severity="critical",
                message="Arc instability: voltage < 19.5V sustained",
                correction="Check shielding gas and wire feed",
                timestamp_ms=now_ms,
            )))
            self._suppress_arc_instability_until = now_ms + self._cfg["sustained_repeat_ms"]

        # Rule 6: Crater crack (spike) — push every frame to maintain buffer history
        if frame.amps is None:
            if not self._warned_amps_missing_crater:
                logger.warning("crater_crack requires amps; skipping (frame_index=%d)", frame.frame_index)
                self._warned_amps_missing_crater = True
        else:
            abrupt = self._crater_buffer.push(now_ms, frame.amps)
            if abrupt is True and now_ms >= self._suppress_crater_until:
                candidates.append((6, "critical", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="crater_crack",
                    severity="critical",
                    message="Crater crack risk: abrupt arc termination",
                    correction="Use controlled ramp-down at bead end",
                    timestamp_ms=now_ms,
                )))
                self._suppress_crater_until = now_ms + self._suppression_ms

        # Rule 7: Oxide inclusion (spike) — standalone negative angle
        if now_ms >= self._suppress_oxide_until:
            if frame.travel_angle_degrees is not None and frame.travel_angle_degrees < 0:
                candidates.append((7, "warning", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="oxide_inclusion",
                    severity="warning",
                    message="Oxide inclusion risk: argon trailing (negative travel angle)",
                    correction="Maintain push angle; avoid dragging torch",
                    timestamp_ms=now_ms,
                )))
                self._suppress_oxide_until = now_ms + self._suppression_ms

        # Rule 8: Undercut (spike)
        if frame.amps is None:
            if not self._warned_amps_missing_undercut:
                logger.warning("undercut requires amps; skipping (frame_index=%d)", frame.frame_index)
                self._warned_amps_missing_undercut = True
        elif now_ms >= self._suppress_undercut_until and frame.travel_speed_mm_per_min is not None:
            if frame.amps > self._cfg["undercut_amps_min"] and frame.travel_speed_mm_per_min > self._cfg["undercut_speed_min_mm_per_min"]:
                candidates.append((8, "critical", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="undercut",
                    severity="critical",
                    message="Undercut risk: high current and high speed",
                    correction="Reduce travel speed or current",
                    timestamp_ms=now_ms,
                )))
                self._suppress_undercut_until = now_ms + self._suppression_ms

        # Rule 9: Lack of fusion — low amps (sustained). Priority 9.
        if frame.amps is not None and frame.amps < self._cfg["lack_of_fusion_amps_max"]:
            if now_ms >= self._suppress_lof_amps_until:
                candidates.append((9, "critical", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="lack_of_fusion_amps",
                    severity="critical",
                    message="Lack of fusion risk: low current",
                    correction="Increase current to 140+ A",
                    timestamp_ms=now_ms,
                )))
                self._suppress_lof_amps_until = now_ms + self._cfg["sustained_repeat_ms"]
        # Rule 10: Lack of fusion — high speed (spike). Priority 10.
        if frame.travel_speed_mm_per_min is not None and frame.travel_speed_mm_per_min > self._cfg["lack_of_fusion_speed_max_mm_per_min"]:
            if now_ms >= self._suppress_lof_speed_until:
                candidates.append((10, "critical", AlertPayload(
                    frame_index=frame.frame_index,
                    rule_triggered="lack_of_fusion_speed",
                    severity="critical",
                    message="Lack of fusion risk: travel speed too high",
                    correction="Reduce speed below 520 mm/min",
                    timestamp_ms=now_ms,
                )))
                self._suppress_lof_speed_until = now_ms + self._suppression_ms

        # Rule 11: Burn-through (spike)
        if frame.amps is None:
            if not self._warned_amps_missing_burn_through:
                logger.warning("burn_through requires amps; skipping (frame_index=%d)", frame.frame_index)
                self._warned_amps_missing_burn_through = True
        elif frame.travel_speed_mm_per_min is not None:
            if now_ms >= self._suppress_burn_through_until:
                if frame.amps > self._cfg["burn_through_amps_min"] and frame.travel_speed_mm_per_min < self._cfg["burn_through_speed_max_mm_per_min"]:
                    candidates.append((11, "critical", AlertPayload(
                        frame_index=frame.frame_index,
                        rule_triggered="burn_through",
                        severity="critical",
                        message="Burn-through risk: high current and low speed",
                        correction="Reduce current or increase travel speed",
                        timestamp_ms=now_ms,
                    )))
                    self._suppress_burn_through_until = now_ms + self._suppression_ms

        if not candidates:
            return None
        # Highest severity wins; tiebreak: lower rule number (critical > warning, then rule 1 < 2 < 3)
        severity_rank = {"critical": 1, "warning": 0}
        candidates.sort(key=lambda x: (-severity_rank[x[1]], x[0]))
        return candidates[0][2]
