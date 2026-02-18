"""
Scoring service — rule-based session score computation.
Used by sessions route and narrative service.
"""

from sqlalchemy.orm import Session as DBSession, joinedload

from database.models import SessionModel
from features.extractor import extract_features
from models.scoring import SessionScore
from scoring.rule_based import score_session
from services.threshold_service import get_thresholds


def get_session_score(session_id: str, db: DBSession) -> SessionScore:
    """
    Compute rule-based score for a welding session.

    Args:
        session_id: Session identifier.
        db: Database session.

    Returns:
        SessionScore with total (0–100) and rules (rule_id, threshold, passed, actual_value).

    Raises:
        ValueError: Session not found or has insufficient frames (< 10).
    """
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

    session = session_model.to_pydantic()
    process_type = getattr(session_model, "process_type", None) or "mig"
    thresholds = get_thresholds(db, process_type)
    features = extract_features(
        session, angle_target_deg=thresholds.angle_target_degrees
    )
    return score_session(session, features, thresholds)
