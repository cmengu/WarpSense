"""
Scoring service — rule-based session score computation.
Used by sessions route and narrative service.
"""

import statistics
from typing import Optional, TYPE_CHECKING

from sqlalchemy.orm import Session as DBSession, joinedload

from database.models import SessionModel
from features.extractor import extract_features
from models.scoring import SessionScore
from scoring.rule_based import score_frames_windowed, score_session
from services.threshold_service import get_thresholds

if TYPE_CHECKING:
    from models.session import Session


def get_session_score(
    session_id: str,
    db: DBSession,
    *,
    include_windowed: bool = False,
    session_model: Optional["SessionModel"] = None,
    session: Optional["Session"] = None,
) -> SessionScore:
    """
    Compute rule-based score for a welding session.

    Args:
        session_id: Session identifier.
        db: Database session.
        include_windowed: When True, compute windowed WQI timeline and aggregates.
        session_model: Optional pre-loaded SessionModel (avoids duplicate query).
        session: Optional pre-converted Session (avoids double to_pydantic when route passes).

    Returns:
        SessionScore with total (0–100), rules, and optionally wqi_timeline, mean_wqi, etc.

    Raises:
        ValueError: Session not found or has insufficient frames (< 10).
    """
    if session_model is None:
        session_model = (
            db.query(SessionModel)
            .options(joinedload(SessionModel.frames))
            .filter_by(session_id=session_id)
            .first()
        )
    if not session_model:
        raise ValueError(f"Session {session_id} not found")

    frames = getattr(session_model, "frames", None) or []
    if not frames or len(frames) < 10:
        raise ValueError(
            "Session has insufficient frames for scoring (minimum 10 required)"
        )

    if session is None:
        session = session_model.to_pydantic()

    process_type = getattr(session_model, "process_type", None) or "mig"
    thresholds = get_thresholds(db, process_type)
    angle_target_deg = (
        thresholds.angle_target_degrees if thresholds else 45
    )
    features = extract_features(session, angle_target_deg=angle_target_deg)
    score = score_session(session, features, thresholds)

    if include_windowed and len(frames) >= 10:
        session_metadata = {
            "weld_type": session.weld_type,
            "thermal_sample_interval_ms": session.thermal_sample_interval_ms,
            "thermal_directions": session.thermal_directions,
            "thermal_distance_interval_mm": session.thermal_distance_interval_mm,
            "sensor_sample_rate_hz": session.sensor_sample_rate_hz,
        }
        frame_list = [f.to_pydantic() for f in frames]
        timeline = score_frames_windowed(
            frame_list,
            thresholds,
            session_metadata,
            angle_target_deg=angle_target_deg,
            window_size=50,
        )
        if timeline:
            wqis = [e["wqi"] for e in timeline]
            mean_wqi = statistics.mean(wqis)
            median_wqi = statistics.median(wqis)
            min_wqi = min(wqis)
            max_wqi = max(wqis)
            wqi_trend = None
            if len(timeline) >= 4:
                n = len(wqis)
                first_half = wqis[: n // 2]
                second_half = wqis[n // 2 :]
                diff = statistics.mean(second_half) - statistics.mean(first_half)
                if diff > 5:
                    wqi_trend = "improving"
                elif diff < -5:
                    wqi_trend = "degrading"
                else:
                    wqi_trend = "stable"
            score = score.model_copy(
                update={
                    "wqi_timeline": timeline,
                    "mean_wqi": round(mean_wqi, 2),
                    "median_wqi": round(median_wqi, 2),
                    "min_wqi": min_wqi,
                    "max_wqi": max_wqi,
                    "wqi_trend": wqi_trend,
                }
            )

    return score
