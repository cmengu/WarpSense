"""
Torch angle, arc termination, defect alert, interpass score components.
"""

import logging
from typing import Dict, List, Optional

from realtime.alert_models import AlertPayload
from scoring.models import ExcursionEvent, ScoreComponent

_logger = logging.getLogger(__name__)


def calculate_torch_angle_component(frames: list, cfg: dict) -> ScoreComponent:
    """Check travel_angle_degrees vs torch_angle_max_degrees. Excursion = >20 or <0 (drag)."""
    max_deg = cfg["torch_angle_max_degrees"]
    excursions: List[ExcursionEvent] = []
    excursion_start_ms: Optional[float] = None
    excursion_start_value: Optional[float] = None
    excursion_threshold: Optional[float] = None
    last_valid_ms: Optional[float] = None

    for frame in frames:
        angle = getattr(frame, "travel_angle_degrees", None)
        ts = getattr(frame, "timestamp_ms", 0)
        if angle is None:
            if (
                excursion_start_ms is not None
                and last_valid_ms is not None
                and excursion_threshold is not None
                and excursion_start_value is not None
            ):
                excursions.append(
                    ExcursionEvent(
                        timestamp_ms=excursion_start_ms,
                        parameter="travel_angle_degrees",
                        value=excursion_start_value,
                        threshold=excursion_threshold,
                        duration_ms=last_valid_ms - excursion_start_ms,
                    )
                )
                excursion_start_ms = None
            continue
        last_valid_ms = ts
        threshold = max_deg if angle > max_deg else 0.0
        is_violation = angle > max_deg or angle < 0
        if is_violation:
            if excursion_start_ms is None:
                excursion_start_ms = ts
                excursion_start_value = angle
                excursion_threshold = threshold
        else:
            if excursion_start_ms is not None:
                excursions.append(
                    ExcursionEvent(
                        timestamp_ms=excursion_start_ms,
                        parameter="travel_angle_degrees",
                        value=excursion_start_value,
                        threshold=excursion_threshold,
                        duration_ms=ts - excursion_start_ms,
                    )
                )
                excursion_start_ms = None

    if (
        excursion_start_ms is not None
        and last_valid_ms is not None
        and excursion_threshold is not None
        and excursion_start_value is not None
    ):
        excursions.append(
            ExcursionEvent(
                timestamp_ms=excursion_start_ms,
                parameter="travel_angle_degrees",
                value=excursion_start_value,
                threshold=excursion_threshold,
                duration_ms=last_valid_ms - excursion_start_ms,
            )
        )

    score_val = 1.0 - min(1.0, len(excursions) * 0.2)
    return ScoreComponent(
        name="torch_angle",
        passed=len(excursions) == 0,
        score=round(score_val, 3),
        excursions=excursions,
        summary=f"{len(excursions)} torch angle excursions (max {max_deg}°, no drag)",
    )


def calculate_arc_termination_component(frames: list, cfg: dict) -> ScoreComponent:
    """Excursion = frame with arc_termination_type == 'no_crater_fill'. duration_ms=0."""
    excursions: List[ExcursionEvent] = []
    for frame in frames:
        at = getattr(frame, "arc_termination_type", None)
        ts = getattr(frame, "timestamp_ms", 0)
        if at == "no_crater_fill":
            excursions.append(
                ExcursionEvent(
                    timestamp_ms=ts,
                    parameter="arc_termination_type",
                    value=0.0,
                    threshold=0.0,
                    duration_ms=0.0,
                )
            )
    count = len(excursions)
    return ScoreComponent(
        name="arc_termination",
        passed=count == 0,
        score=1.0 if count == 0 else round(max(0.0, 1.0 - count * 0.25), 3),
        excursions=excursions,
        summary=f"{count} abrupt arc terminations without crater fill",
    )


def calculate_defect_alert_component(
    alerts: List[AlertPayload], cfg: dict
) -> ScoreComponent:
    """
    Group alerts by rule_triggered.
    Critical (porosity, crater_crack, burn_through, arc_instability) → fail.
    Warnings (oxide_inclusion) → score penalty only, not automatic fail.
    """
    CRITICAL = {"porosity", "crater_crack", "burn_through", "arc_instability"}
    excursions: List[ExcursionEvent] = []
    by_rule: Dict[str, int] = {}
    dropped = [a for a in alerts if not isinstance(a, AlertPayload)]
    if dropped:
        _logger.warning(
            "calculate_defect_alert_component: %d non-AlertPayload items dropped",
            len(dropped),
        )
    for a in alerts:
        if not isinstance(a, AlertPayload):
            continue
        rule = a.rule_triggered
        ts = a.timestamp_ms
        excursions.append(
            ExcursionEvent(
                timestamp_ms=ts, parameter=rule, value=1.0, threshold=0.0, duration_ms=0.0
            )
        )
        by_rule[rule] = by_rule.get(rule, 0) + 1
    has_critical = any(r in CRITICAL for r in by_rule)
    score_val = 0.0 if has_critical else (1.0 - min(1.0, len(alerts) * 0.1))
    return ScoreComponent(
        name="defect_alerts",
        passed=not has_critical,
        score=round(score_val, 3),
        excursions=excursions,
        summary=f"defects: {dict(by_rule)}" if by_rule else "no defect alerts",
    )


def calculate_interpass_component(frames: list, cfg: dict) -> ScoreComponent:
    """
    Timer model only. No plate temperature sensor.
    Gap < interpass_min_ms → violation (proxy for >60°C interpass).
    """
    min_ms = cfg["interpass_min_ms"]
    excursions: List[ExcursionEvent] = []
    prev_arc_on_ms: Optional[float] = None
    prev_arc_off_ms: Optional[float] = None

    for frame in frames:
        amps = getattr(frame, "amps", None)
        ts = getattr(frame, "timestamp_ms", 0)
        arc_on = amps is not None and amps > 1.0
        if arc_on:
            if prev_arc_off_ms is not None and prev_arc_on_ms is not None:
                gap = ts - prev_arc_off_ms
                if gap < min_ms and gap > 0:
                    excursions.append(
                        ExcursionEvent(
                            timestamp_ms=prev_arc_off_ms,
                            parameter="interpass_gap_ms",
                            value=gap,
                            threshold=min_ms,
                            duration_ms=gap,
                        )
                    )
            prev_arc_on_ms = ts
            prev_arc_off_ms = None
        else:
            if prev_arc_on_ms is not None:
                prev_arc_off_ms = ts
            else:
                prev_arc_off_ms = None

    score_val = 1.0 - min(1.0, len(excursions) * 0.3)
    return ScoreComponent(
        name="interpass",
        passed=len(excursions) == 0,
        score=round(score_val, 3),
        excursions=excursions,
        summary=f"{len(excursions)} interpass violations (< {min_ms}ms gap). Timer proxy only.",
    )
