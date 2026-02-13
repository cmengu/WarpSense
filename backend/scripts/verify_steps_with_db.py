#!/usr/bin/env python3
"""
Run Steps 7–11 verification with a real SQLite file DB: create schema, seed,
then run validate_frame_fields script and pytest for extract_features, score_session,
get_session_score, mock_alignment.

Usage (from repo root or backend/):
  cd backend && source venv/bin/activate && python scripts/verify_steps_with_db.py

Requires: venv with dependencies installed. Uses SQLite file ./verify_steps.db (created then removed).
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BACKEND_DIR / "verify_steps.db"
DB_URL = f"sqlite:///{DB_FILE}"


def main() -> int:
    os.chdir(BACKEND_DIR)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    # Create schema and seed
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.base import Base
    from database.models import SessionModel
    from data.mock_sessions import generate_expert_session, generate_novice_session

    if DB_FILE.exists():
        DB_FILE.unlink()
    engine = create_engine(
        f"sqlite:///{DB_FILE}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()
    try:
        for session in [
            generate_expert_session(session_id="sess_expert_001"),
            generate_novice_session(session_id="sess_novice_001"),
        ]:
            db.add(SessionModel.from_pydantic(session))
        db.commit()
    finally:
        db.close()

    # Run validate_frame_fields.py against the seeded DB
    env = {**os.environ, "DATABASE_URL": DB_URL}
    r = subprocess.run(
        [sys.executable, str(BACKEND_DIR / "scripts" / "validate_frame_fields.py")],
        cwd=str(BACKEND_DIR),
        env=env,
    )
    if r.returncode != 0:
        print("validate_frame_fields.py failed", file=sys.stderr)
        return r.returncode

    # Run Step 7–11 pytest with same DB so they use real schema + data where applicable
    r2 = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_validate_frame_fields.py",
         "tests/test_extract_features.py",
         "tests/test_score_session.py",
         "tests/test_get_session_score.py",
         "tests/test_mock_alignment.py",
         "-v",
         "--tb=short"],
        cwd=str(BACKEND_DIR),
        env={**os.environ, "DATABASE_URL": DB_URL, "PYTHONPATH": str(BACKEND_DIR)},
    )
    if DB_FILE.exists():
        DB_FILE.unlink()
    return r2.returncode


if __name__ == "__main__":
    sys.exit(main())
