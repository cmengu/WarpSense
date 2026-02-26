"""
Alert service — runs AlertEngine over session frames.

Used by get_session_alerts and get_report_summary. Returns AlertPayload objects
directly; callers call model_dump() when building HTTP responses.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from realtime.alert_engine import AlertEngine
from realtime.alert_models import AlertPayload, FrameInput

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as OrmSession


def _ns_asymmetry_from_frame_data(frame_data: dict) -> float:
    """North minus south at 10mm. 0 if no thermal. Matches sessions._ns_asymmetry_from_frame_data."""
    snapshots = frame_data.get("thermal_snapshots") or []
    if not snapshots:
        return 0.0
    snap = snapshots[0]
    readings = snap.get("readings") or []
    north = next(
        (r["temp_celsius"] for r in readings if r.get("direction") == "north"),
        None,
    )
    south = next(
        (r["temp_celsius"] for r in readings if r.get("direction") == "south"),
        None,
    )
    if north is None or south is None:
        return 0.0
    return float(north) - float(south)


async def run_session_alerts(session_id: str, db: "OrmSession") -> list[AlertPayload]:
    """
    Run session frames through AlertEngine, return AlertPayload objects.

    Does NOT call model_dump(). Callers (e.g. get_session_alerts) dump when
    building the HTTP response. compute_report_summary needs .rule_triggered
    and .message on objects.
    """
    from database.models import FrameModel

    frames_query = (
        db.query(FrameModel)
        .filter_by(session_id=session_id)
        .order_by(FrameModel.timestamp_ms.asc())
        .limit(2000)
    )
    frame_models = frames_query.all()

    config_path = (
        Path(__file__).resolve().parent.parent
        / "config"
        / "alert_thresholds.json"
    )
    engine = AlertEngine(str(config_path))

    alerts: list[AlertPayload] = []
    for i, fm in enumerate(frame_models):
        fd = dict(fm.frame_data)
        ns = _ns_asymmetry_from_frame_data(fd)
        ts_ms = fd.get("timestamp_ms")
        if ts_ms is None:
            ts_ms = fm.timestamp_ms
        fin = FrameInput(
            frame_index=i,
            timestamp_ms=float(ts_ms),
            travel_angle_degrees=fd.get("travel_angle_degrees"),
            travel_speed_mm_per_min=fd.get("travel_speed_mm_per_min"),
            ns_asymmetry=ns,
            volts=fd.get("volts"),
            amps=fd.get("amps"),
        )
        alert = engine.push_frame(fin)
        if alert:
            alerts.append(alert)

    return alerts
