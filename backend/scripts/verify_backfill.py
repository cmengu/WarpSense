#!/usr/bin/env python3
"""
Verify all COMPLETE sessions with frames have score_total.
Exit 1 if any null. Use after backfill or in CI to ensure data integrity.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from database.connection import SessionLocal


def main():
    db = SessionLocal()
    try:
        r = db.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE status = 'complete' "
                "AND frame_count > 0 AND score_total IS NULL"
            )
        ).scalar()
        if r and r > 0:
            print(f"❌ {r} COMPLETE session(s) with frames have null score_total")
            sys.exit(1)
        print("✅ All COMPLETE sessions with frames have score_total")
    finally:
        db.close()


if __name__ == "__main__":
    main()
