"""
Frame query helpers — the one home for raw frame data access.

Moved from api/sessions.py so that services/ no longer imports upward from
api/. Both layers now import downward from db/.
"""

import copy

from sqlalchemy.orm import Session as OrmSession

from warpsense.db.models import FrameModel, SessionModel


def get_session_frames_raw(
    session_id: str, db: OrmSession, limit: int = 50
) -> list[dict] | None:
    """
    Returns the last `limit` frames of a session as raw dicts (ascending by timestamp_ms).
    Each dict has same shape as Frame.model_dump() — required for extract_features.
    Returns None if session not found.
    Uses copy.deepcopy to avoid shared nested references (SQLAlchemy JSONB may share refs).
    """
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        return None
    frames = (
        db.query(FrameModel)
        .filter_by(session_id=session_id)
        .order_by(FrameModel.timestamp_ms.desc())
        .limit(limit)
        .all()
    )
    return [copy.deepcopy(dict(f.frame_data)) for f in reversed(frames)]
