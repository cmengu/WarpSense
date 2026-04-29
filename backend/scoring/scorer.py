"""
Orchestrator: AWS D1.2 decomposed scoring.
Single source for _build_alerts_from_frames used by routes, rescore endpoint, and backfill script.
"""

import os
import time
from typing import List, Optional

from realtime.alert_engine import AlertEngine
from realtime.alert_models import AlertPayload, FrameInput

from scoring.components import (
    calculate_arc_termination_component,
    calculate_defect_alert_component,
    calculate_interpass_component,
    calculate_torch_angle_component,
)
from scoring.config import load_scoring_config
from scoring.heat_input import calculate_heat_input_component
from scoring.models import DecomposedSessionScore, ScoreComponent

ALERT_CONFIG_PATH = "config/alert_thresholds.json"


def _ns_asymmetry_from_frame(frame) -> float:
    """North minus south temp_celsius at first thermal snapshot. Returns 0.0 if no thermal data."""
    snapshots = getattr(frame, "thermal_snapshots", None) or []
    if not snapshots:
        return 0.0
    readings = snapshots[0].readings
    north = next((r.temp_celsius for r in readings if r.direction == "north"), None)
    south = next((r.temp_celsius for r in readings if r.direction == "south"), None)
    if north is None or south is None:
        return 0.0
    return float(north) - float(south)


def _build_alerts_from_frames(
    frames: list,
    config_path: str = ALERT_CONFIG_PATH,
) -> List[AlertPayload]:
    """Build FrameInput list, run through AlertEngine, return alerts. Single source for routes + script."""
    engine = AlertEngine(config_path=config_path)
    alerts: List[AlertPayload] = []
    for i, f in enumerate(frames):
        fi = FrameInput(
            frame_index=i,
            timestamp_ms=getattr(f, "timestamp_ms", None),
            travel_angle_degrees=getattr(f, "travel_angle_degrees", None),
            travel_speed_mm_per_min=getattr(f, "travel_speed_mm_per_min", None),
            ns_asymmetry=_ns_asymmetry_from_frame(f),
            volts=getattr(f, "volts", None),
            amps=getattr(f, "amps", None),
        )
        out = engine.push_frame(fi)
        if out:
            alerts.append(out)
    return alerts


def score_session_decomposed(
    frames: list,
    alerts: list,
    session_id: str,
    cfg: Optional[dict] = None,
    config_path: str = "config/scoring_config.json",
) -> DecomposedSessionScore:
    """Compute decomposed AWS D1.2 score. Critical = heat_input, arc_termination, defect_alerts."""
    if cfg is None:
        cfg = load_scoring_config(config_path)
    arc_on = sum(
        1
        for f in frames
        if getattr(f, "amps", None) is not None and getattr(f, "amps", 0) > 1.0
    )
    heat = calculate_heat_input_component(frames, cfg)
    torch = calculate_torch_angle_component(frames, cfg)
    arc_term = calculate_arc_termination_component(frames, cfg)
    defect = calculate_defect_alert_component(alerts, cfg)
    interpass = calculate_interpass_component(frames, cfg)
    components = {
        "heat_input": heat,
        "torch_angle": torch,
        "arc_termination": arc_term,
        "defect_alerts": defect,
        "interpass": interpass,
    }
    critical = [heat, arc_term, defect]
    passed = all(c.passed for c in critical)
    weights = {
        "heat_input": cfg["heat_input_weight"],
        "torch_angle": cfg["torch_angle_weight"],
        "arc_termination": cfg["arc_termination_weight"],
        "defect_alerts": cfg["defect_alert_weight"],
        "interpass": cfg["interpass_weight"],
    }
    overall = sum(c.score * weights[c.name] for c in components.values())
    wps_range = (
        cfg["wps_heat_input_min_kj_per_mm"],
        cfg["wps_heat_input_max_kj_per_mm"],
    )
    return DecomposedSessionScore(
        session_id=session_id,
        overall_score=round(overall, 3),
        passed=passed,
        components=components,
        frame_count=len(frames),
        arc_on_frame_count=arc_on,
        computed_at_ms=time.time() * 1000,
        wps_range_kj_per_mm=wps_range,
    )
