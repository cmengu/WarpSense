"""
Backfill score_total using decomposed scoring. Run after scoring logic changes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import joinedload

from database.connection import SessionLocal
from database.models import SessionModel
from scoring.scorer import score_session_decomposed, _build_alerts_from_frames


def main():
    db = SessionLocal()
    try:
        models = (
            db.query(SessionModel)
            .options(joinedload(SessionModel.frames))
            .filter(SessionModel.status == "complete")
            .all()
        )
        for m in models:
            frames = getattr(m, "frames", None) or []
            if len(frames) < 10:
                continue
            session = m.to_pydantic()
            alerts = _build_alerts_from_frames(list(session.frames))
            dec = score_session_decomposed(list(session.frames), alerts, m.session_id)
            m.score_total = int(round(dec.overall_score * 100))
            print(f"{m.session_id}: {dec.overall_score:.3f} -> {m.score_total}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
