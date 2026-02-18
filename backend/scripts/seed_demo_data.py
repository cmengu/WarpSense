#!/usr/bin/env python3
"""
Seed demo sessions from WELDER_ARCHETYPES into the database.
Idempotent: skips ONLY when existing count equals full expected count.
Used by deploy.sh.

Run from backend/ or with PYTHONPATH including backend.
"""

import random
import sys
from pathlib import Path

# Ensure backend is on path when run via: python scripts/seed_demo_data.py
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from data.mock_welders import WELDER_ARCHETYPES
from data.mock_sessions import generate_session_for_welder
from database.connection import SessionLocal
from database.models import SessionModel


def main() -> int:
    db = SessionLocal()
    try:
        session_ids = []
        for arch in WELDER_ARCHETYPES:
            welder_id = arch["welder_id"]
            n = arch["sessions"]
            for i in range(1, n + 1):
                session_ids.append(f"sess_{welder_id}_{i:03d}")

        expected_count = len(session_ids)
        existing = db.query(SessionModel).filter(
            SessionModel.session_id.in_(session_ids)
        ).count()

        if existing == expected_count:
            # Spot-check: first derived ID and first archetype operator_id
            sample_sid = session_ids[0]
            expected_operator_id = WELDER_ARCHETYPES[0]["welder_id"]
            sess = db.query(SessionModel).filter(
                SessionModel.session_id == sample_sid
            ).first()
            if sess is None or sess.operator_id != expected_operator_id:
                print(
                    f"Spot-check failed: {sample_sid} operator_id={getattr(sess, 'operator_id', None)} "
                    f"expected {expected_operator_id}. Re-seeding.",
                    file=sys.stderr,
                )
                # Fall through to re-seed
            else:
                print("Demo data already complete, skipping.", file=sys.stderr)
                return 0

        if existing > 0 and existing < expected_count:
            print(
                f"Warning: {existing}/{expected_count} sessions exist. Re-seeding all.",
                file=sys.stderr,
            )
        for s in db.query(SessionModel).filter(
            SessionModel.session_id.in_(session_ids)
        ).all():
            db.delete(s)
        db.flush()

        random.seed(42)
        for arch in WELDER_ARCHETYPES:
            welder_id = arch["welder_id"]
            arc_type = arch["arc"]
            n = arch["sessions"]
            for i in range(1, n + 1):
                sid = f"sess_{welder_id}_{i:03d}"
                session = generate_session_for_welder(welder_id, arc_type, i - 1, sid)
                model = SessionModel.from_pydantic(session)
                db.add(model)

        db.commit()
        print(f"Demo data seeded: {len(session_ids)} sessions", file=sys.stderr)
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
