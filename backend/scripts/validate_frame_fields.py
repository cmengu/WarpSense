#!/usr/bin/env python3
"""
Validate that frame model uses correct field names for scoring pipeline.

Required fields (must exist): angle_degrees, amps, has_thermal_data
Prohibited fields (must NOT exist): torch_angle_degrees, frame_type

Wrong field names cause extract_features and scoring to fail silently (zeros).
Run from backend dir: python scripts/validate_frame_fields.py

Prerequisites: DATABASE_URL set; DB seeded (e.g. POST /seed-mock-sessions).
Exit code 0 = all assertions pass; 1 = validation failed or no session with frames.
"""

import sys
from pathlib import Path

# Ensure backend dir is on path when run as script
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.frame import Frame


REQUIRED_KEYS = frozenset({"angle_degrees", "amps", "has_thermal_data"})
PROHIBITED_KEYS = frozenset({"torch_angle_degrees", "frame_type"})


def validate_frame_keys(frame: Frame) -> None:
    """
    Assert frame has required keys and lacks prohibited keys.
    Raises AssertionError with clear message if validation fails.
    """
    keys = set(frame.model_dump().keys())
    print("Frame model_dump keys:", sorted(keys))

    missing = REQUIRED_KEYS - keys
    if missing:
        raise AssertionError(
            f"Frame missing required keys: {sorted(missing)}. "
            f"Fix models/frame.py to match scoring contract."
        )

    present_prohibited = PROHIBITED_KEYS & keys
    if present_prohibited:
        raise AssertionError(
            f"Frame must NOT have deprecated keys: {sorted(present_prohibited)}. "
            f"Use angle_degrees (not torch_angle_degrees); remove frame_type."
        )


def main() -> int:
    """Load first session with frames from DB; validate first frame; exit 0 if pass."""
    try:
        from database.connection import SessionLocal
        from database.models import FrameModel, SessionModel
        from sqlalchemy.orm import joinedload
    except ImportError as e:
        print(f"Import error: {e}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        # Load any session that has at least one frame
        session_model = (
            db.query(SessionModel)
            .options(joinedload(SessionModel.frames))
            .filter(SessionModel.frame_count > 0)
            .first()
        )
        if not session_model or not session_model.frames:
            print(
                "No session with frames in DB. Seed first: POST /seed-mock-sessions (with ENV=development)",
                file=sys.stderr,
            )
            return 1

        first_frame_model = session_model.frames[0]
        frame = first_frame_model.to_pydantic()

        print(f"Validating first frame from session {session_model.session_id} (ts={frame.timestamp_ms}ms)")
        validate_frame_keys(frame)
        print("OK: All frame field assertions passed.")
        return 0
    except AssertionError as e:
        print(f"Assertion failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
