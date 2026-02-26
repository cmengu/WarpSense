"""
Heat input component: per-frame kJ/mm vs WPS range.
Formula: (amps × volts × 60) / (travel_speed_mm_per_min × 1000).
"""

from typing import List, Optional

from scoring.models import ExcursionEvent, ScoreComponent


def _close_excursion(
    excursions: List[ExcursionEvent],
    start_ms: Optional[float],
    end_ms: float,
    parameter: str,
    value: float,
    threshold: float,
) -> None:
    """Append excursion if one is open. Call on arc-off or loop end."""
    if start_ms is not None:
        excursions.append(
            ExcursionEvent(
                timestamp_ms=start_ms,
                parameter=parameter,
                value=value,
                threshold=threshold,
                duration_ms=end_ms - start_ms,
            )
        )


def calculate_heat_input_component(frames: list, cfg: dict) -> ScoreComponent:
    """Compute heat input component. Excursion = frame outside WPS range."""
    wps_min = cfg["wps_heat_input_min_kj_per_mm"]
    wps_max = cfg["wps_heat_input_max_kj_per_mm"]
    excursions: List[ExcursionEvent] = []
    excursion_start_ms: Optional[float] = None
    excursion_start_value: Optional[float] = None
    excursion_threshold: Optional[float] = None
    arc_on_count = 0
    last_arc_on_ms: Optional[float] = None

    for frame in frames:
        amps = getattr(frame, "amps", None)
        volts = getattr(frame, "volts", None)
        speed = getattr(frame, "travel_speed_mm_per_min", None)
        ts = getattr(frame, "timestamp_ms", 0)

        if amps is None or volts is None or speed is None or speed <= 0:
            # last_arc_on_ms is correct here — excursion ends at last arc-on frame, not current arc-off frame
            if (
                excursion_start_ms is not None
                and last_arc_on_ms is not None
                and excursion_threshold is not None
            ):
                _close_excursion(
                    excursions,
                    excursion_start_ms,
                    last_arc_on_ms,
                    "heat_input_kj_per_mm",
                    excursion_start_value or 0.0,
                    excursion_threshold,
                )
                excursion_start_ms = None
            continue

        hi = (amps * volts * 60) / (speed * 1000)
        arc_on_count += 1
        last_arc_on_ms = ts

        threshold = wps_min if hi < wps_min else wps_max
        if hi < wps_min or hi > wps_max:
            if excursion_start_ms is None:
                excursion_start_ms = ts
                excursion_start_value = hi
                excursion_threshold = threshold
        else:
            if (
                excursion_start_ms is not None
                and excursion_start_value is not None
                and excursion_threshold is not None
            ):
                excursions.append(
                    ExcursionEvent(
                        timestamp_ms=excursion_start_ms,
                        parameter="heat_input_kj_per_mm",
                        value=excursion_start_value,
                        threshold=excursion_threshold,
                        duration_ms=ts - excursion_start_ms,
                    )
                )
                excursion_start_ms = None

    if (
        excursion_start_ms is not None
        and last_arc_on_ms is not None
        and excursion_threshold is not None
        and excursion_start_value is not None
    ):
        _close_excursion(
            excursions,
            excursion_start_ms,
            last_arc_on_ms,
            "heat_input_kj_per_mm",
            excursion_start_value,
            excursion_threshold,
        )

    # Penalty: ~10% score drop per excursion per 10% of arc-on frames; collapses to 0 when excursions >= 10% of arc-on count
    score_val = 1.0 - min(1.0, len(excursions) / max(arc_on_count, 1) * 10)
    return ScoreComponent(
        name="heat_input",
        passed=len(excursions) == 0,
        score=round(score_val, 3),
        excursions=excursions,
        summary=f"{len(excursions)} heat input excursions vs WPS range {wps_min}–{wps_max} kJ/mm",
    )
