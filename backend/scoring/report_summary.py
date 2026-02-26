"""
Report summary aggregator for session compliance.

Computes heat input aggregates, travel angle excursions (run-length collapsed),
arc termination quality, and defect counts from frames + alerts.
Owns the full process_type → config_key mapping. Does not touch scoring or extract_features.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from models.frame import Frame
from realtime.alert_models import AlertPayload

# process_type → config key. compute_report_summary owns this mapping.
# Route passes raw process_type; we resolve to a key in report_thresholds.json.
PROCESS_TYPE_TO_CONFIG_KEY: dict[str, str] = {
    "aluminum": "aluminum_spray",
    "mig": "aluminum_spray",
    "tig": "aluminum_spray",
    "stick": "aluminum_spray",
    "flux_core": "aluminum_spray",
}
DEFAULT_CONFIG_KEY = "aluminum_spray"


def _load_report_thresholds() -> dict:
    """Load report_thresholds.json. Raises FileNotFoundError if missing."""
    backend = Path(__file__).resolve().parent.parent
    path = backend / "config" / "report_thresholds.json"
    return json.loads(path.read_text())


def _get_config_key(process_type: Optional[str]) -> str:
    """Resolve process_type to config key. Fallback: aluminum_spray."""
    if not process_type or not process_type.strip():
        return DEFAULT_CONFIG_KEY
    key = PROCESS_TYPE_TO_CONFIG_KEY.get(process_type.strip().lower(), DEFAULT_CONFIG_KEY)
    return key


def _get_thresholds(process_type: Optional[str]) -> dict:
    """Load thresholds for process_type. Raises ValueError if aluminum_spray missing."""
    config = _load_report_thresholds()
    key = _get_config_key(process_type)
    if key not in config:
        raise ValueError(
            f"report_thresholds.json missing key {key!r} for process_type {process_type!r}. "
            "Add entry or ensure fallback aluminum_spray exists."
        )
    return config[key]


class ExcursionEntry(BaseModel):
    """Single excursion (alert or frame-derived, run-length collapsed)."""

    timestamp_ms: int
    defect_type: str
    parameter_value: Optional[float] = None
    threshold_value: Optional[float] = None
    duration_ms: Optional[int] = None
    source: Literal["alert", "frame_derived"]
    notes: Optional[str] = None


class ReportSummary(BaseModel):
    """Session-level compliance summary for report UI and PDF."""

    session_id: str
    generated_at: datetime

    heat_input_min_kj_per_mm: Optional[float] = None
    heat_input_max_kj_per_mm: Optional[float] = None
    heat_input_mean_kj_per_mm: Optional[float] = None
    heat_input_wps_min: float = 0.5
    heat_input_wps_max: float = 0.9
    heat_input_compliant: bool = False

    travel_angle_excursion_count: int = 0
    travel_angle_worst_case_deg: Optional[float] = None
    travel_angle_threshold_deg: float = 25.0

    total_arc_terminations: int = 0
    no_crater_fill_count: int = 0
    crater_fill_rate_pct: float = 0.0

    defect_counts_by_type: dict[str, int] = Field(default_factory=dict)
    total_defect_alerts: int = 0

    excursions: List[ExcursionEntry] = Field(default_factory=list)


def _collapse_travel_angle_runs(
    frames: List[Frame],
    nominal_deg: float,
    threshold_deg: float,
) -> List[ExcursionEntry]:
    """
    Run-length collapse: consecutive frames in excursion → one ExcursionEntry per run.
    duration_ms = last_ts - first_ts (last excursion frame in run).
    Single-frame runs are valid — emit with duration_ms=0. Do not skip.
    """
    entries: List[ExcursionEntry] = []
    in_run = False
    run_start_ms: Optional[int] = None
    run_end_ms: Optional[int] = None
    run_max_deviation = 0.0

    for f in frames:
        angle = f.travel_angle_degrees
        if angle is None:
            if in_run and run_start_ms is not None:
                duration = (run_end_ms - run_start_ms) if run_end_ms is not None else 0
                entries.append(
                    ExcursionEntry(
                        timestamp_ms=run_start_ms,
                        defect_type="travel_angle_excursion",
                        parameter_value=run_max_deviation,
                        threshold_value=threshold_deg,
                        duration_ms=duration,
                        source="frame_derived",
                    )
                )
                in_run = False
            continue

        dev = abs(angle - nominal_deg)
        is_excursion = dev > threshold_deg

        if is_excursion:
            if not in_run:
                in_run = True
                run_start_ms = f.timestamp_ms
                run_end_ms = f.timestamp_ms
                run_max_deviation = dev
            else:
                run_end_ms = f.timestamp_ms
                run_max_deviation = max(run_max_deviation, dev)
        else:
            if in_run and run_start_ms is not None:
                duration = (run_end_ms - run_start_ms) if run_end_ms is not None else 0
                entries.append(
                    ExcursionEntry(
                        timestamp_ms=run_start_ms,
                        defect_type="travel_angle_excursion",
                        parameter_value=run_max_deviation,
                        threshold_value=threshold_deg,
                        duration_ms=duration,
                        source="frame_derived",
                    )
                )
                in_run = False

    if in_run and run_start_ms is not None:
        duration = (run_end_ms - run_start_ms) if run_end_ms is not None else 0
        entries.append(
            ExcursionEntry(
                timestamp_ms=run_start_ms,
                defect_type="travel_angle_excursion",
                parameter_value=run_max_deviation,
                threshold_value=threshold_deg,
                duration_ms=duration,
                source="frame_derived",
            )
        )

    return entries


def compute_report_summary(
    session_id: str,
    frames: List[Frame],
    alerts: List[AlertPayload],
    process_type: Optional[str] = None,
) -> ReportSummary:
    """
    Aggregate session compliance from frames and alerts.

    process_type: Raw value from session (e.g. "aluminum", "mig"). This module
    owns the mapping to config keys. Pass through; do not map in the route.
    """
    thresholds = _get_thresholds(process_type)
    wps_min = float(thresholds.get("heat_input_min", 0.5))
    wps_max = float(thresholds.get("heat_input_max", 0.9))
    travel_threshold = float(thresholds.get("travel_angle_threshold", 25.0))
    travel_nominal = float(thresholds.get("travel_angle_nominal", 12.0))

    heat_vals = [f.heat_input_kj_per_mm for f in frames if f.heat_input_kj_per_mm is not None]
    heat_min = min(heat_vals) if heat_vals else None
    heat_max = max(heat_vals) if heat_vals else None
    heat_mean = sum(heat_vals) / len(heat_vals) if heat_vals else None
    heat_compliant = heat_mean is not None and wps_min <= heat_mean <= wps_max

    travel_frames_in_excursion = 0
    travel_worst: Optional[float] = None
    for f in frames:
        if f.travel_angle_degrees is not None:
            dev = abs(f.travel_angle_degrees - travel_nominal)
            if dev > travel_threshold:
                travel_frames_in_excursion += 1
                travel_worst = dev if travel_worst is None else max(travel_worst, dev)

    frame_derived = _collapse_travel_angle_runs(frames, travel_nominal, travel_threshold)

    terminations = [f for f in frames if f.arc_termination_type is not None]
    total_term = len(terminations)
    no_crater = sum(1 for f in terminations if f.arc_termination_type == "no_crater_fill")
    crater_fill_rate = (
        100.0 * (total_term - no_crater) / total_term if total_term else 0.0
    )

    defect_counts = Counter(a.rule_triggered for a in alerts)
    total_alerts = len(alerts)

    alert_entries = [
        ExcursionEntry(
            timestamp_ms=int(a.timestamp_ms),
            defect_type=a.rule_triggered,
            parameter_value=None,
            threshold_value=None,
            duration_ms=None,
            source="alert",
            notes=a.message,
        )
        for a in alerts
    ]

    all_excursions = frame_derived + alert_entries
    all_excursions.sort(key=lambda e: e.timestamp_ms)

    return ReportSummary(
        session_id=session_id,
        generated_at=datetime.now(timezone.utc),
        heat_input_min_kj_per_mm=heat_min,
        heat_input_max_kj_per_mm=heat_max,
        heat_input_mean_kj_per_mm=heat_mean,
        heat_input_wps_min=wps_min,
        heat_input_wps_max=wps_max,
        heat_input_compliant=heat_compliant,
        travel_angle_excursion_count=travel_frames_in_excursion,
        travel_angle_worst_case_deg=travel_worst,
        travel_angle_threshold_deg=travel_threshold,
        total_arc_terminations=total_term,
        no_crater_fill_count=no_crater,
        crater_fill_rate_pct=round(crater_fill_rate, 2),
        defect_counts_by_type=dict(defect_counts),
        total_defect_alerts=total_alerts,
        excursions=all_excursions,
    )
