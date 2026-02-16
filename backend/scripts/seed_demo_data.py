#!/usr/bin/env python3
"""
Seed demo sessions (sess_expert_001, sess_novice_001) into the database.
Idempotent: skips if already seeded. Used by deploy.sh.
Run from backend/ or with PYTHONPATH including backend.
"""

import sys
from pathlib import Path

# Ensure backend is on path when run via: python scripts/seed_demo_data.py
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from data.mock_sessions import generate_expert_session, generate_novice_session
from database.connection import SessionLocal
from database.models import SessionModel


def main() -> int:
    db = SessionLocal()
    try:
        session_ids = ["sess_expert_001", "sess_novice_001"]
        existing = db.query(SessionModel).filter(
            SessionModel.session_id.in_(session_ids)
        ).count()

        if existing > 0:
            print("Demo data already exists, skipping.", file=sys.stderr)
            return 0

        expert = generate_expert_session(session_id="sess_expert_001")
        novice = generate_novice_session(session_id="sess_novice_001")

        for session in [expert, novice]:
            model = SessionModel.from_pydantic(session)
            db.add(model)

        db.commit()
        print("Demo data seeded: sess_expert_001, sess_novice_001", file=sys.stderr)
        return 0
    except Exception as e:
        import traceback
        print(f"Seeding failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
