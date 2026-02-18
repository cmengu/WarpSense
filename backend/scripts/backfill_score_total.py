#!/usr/bin/env python3
"""
Backfill score_total for COMPLETE sessions that have frames but no score.
Run from backend/: python scripts/backfill_score_total.py

Batches in groups of 10 to avoid memory spike when many sessions need backfill.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import joinedload

from database.connection import SessionLocal
from database.models import SessionModel
from features.extractor import extract_features
from scoring.rule_based import score_session
from services.threshold_service import get_thresholds

BATCH_SIZE = 10


def main():
    db = SessionLocal()
    try:
        base_query = db.query(SessionModel).filter(
            SessionModel.status == "complete",
            SessionModel.frame_count > 0,
            SessionModel.score_total.is_(None),
        )
        total = base_query.count()
        print(f"Found {total} sessions to backfill")
        processed = 0
        while True:
            batch = (
                db.query(SessionModel)
                .options(joinedload(SessionModel.frames))
                .filter(
                    SessionModel.status == "complete",
                    SessionModel.frame_count > 0,
                    SessionModel.score_total.is_(None),
                )
                .order_by(SessionModel.session_id)
                .limit(BATCH_SIZE)
                .all()
            )
            if not batch:
                break
            for s in batch:
                try:
                    session = s.to_pydantic()
                    process_type = (
                        getattr(session, "process_type", None) or "mig"
                    ).lower()
                    thresholds = get_thresholds(db, process_type)
                    features = extract_features(
                        session, angle_target_deg=thresholds.angle_target_degrees
                    )
                    score = score_session(session, features, thresholds)
                    s.score_total = score.total
                    print(f"  {s.session_id}: score_total={score.total}")
                except Exception as e:
                    print(f"  {s.session_id}: ERROR {e}")
                    continue
            db.commit()
            processed += len(batch)
        print(f"Done ({processed} sessions)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
