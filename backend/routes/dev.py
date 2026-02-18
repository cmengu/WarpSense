"""
Dev-only routes for seeding mock data.
Enabled only when ENV=development or DEBUG=1.
"""

import os
import random

from fastapi import APIRouter, Depends, HTTPException

from database.connection import SessionLocal
from database.models import SessionModel
from sqlalchemy.orm import Session as OrmSession

router = APIRouter()


def _is_dev_mode() -> bool:
    """True when running in development (seed routes allowed)."""
    return (
        os.getenv("ENV", "").lower() == "development"
        or os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/seed-mock-sessions")
async def seed_mock_sessions(db: OrmSession = Depends(get_db)):
    """
    Seed mock sessions from WELDER_ARCHETYPES into the database.
    Only available when ENV=development or DEBUG=1.

    Seeds ~45 sessions (sess_{welder_id}_{001..00n}) per archetype.
    Run seed before opening /seagull dashboard or welder report.
    """
    if not _is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Seed route is only available in development (ENV=development or DEBUG=1)",
        )

    from data.mock_welders import WELDER_ARCHETYPES
    from data.mock_sessions import generate_session_for_welder

    session_ids = []
    for arch in WELDER_ARCHETYPES:
        welder_id = arch["welder_id"]
        n = arch["sessions"]
        for i in range(1, n + 1):
            session_ids.append(f"sess_{welder_id}_{i:03d}")

    if len(session_ids) == 0:
        raise HTTPException(status_code=500, detail="WELDER_ARCHETYPES is empty")

    for existing in db.query(SessionModel).filter(
        SessionModel.session_id.in_(session_ids)
    ).all():
        db.delete(existing)
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
    return {"seeded": session_ids}


@router.post("/wipe-mock-sessions")
async def wipe_mock_sessions(db: OrmSession = Depends(get_db)):
    """
    Delete mock sessions derived from WELDER_ARCHETYPES.
    Only available when ENV=development or DEBUG=1.

    Deletes sess_{welder_id}_{001..00n} for all archetypes.
    Orphan sessions (from removed archetypes) persist; manual cleanup if needed.
    """
    if not _is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Wipe route is only available in development (ENV=development or DEBUG=1)",
        )

    from data.mock_welders import WELDER_ARCHETYPES

    session_ids = []
    for arch in WELDER_ARCHETYPES:
        welder_id = arch["welder_id"]
        n = arch["sessions"]
        for i in range(1, n + 1):
            session_ids.append(f"sess_{welder_id}_{i:03d}")

    deleted = db.query(SessionModel).filter(
        SessionModel.session_id.in_(session_ids)
    ).delete(synchronize_session=False)
    db.commit()

    return {"deleted": deleted, "ids": session_ids}
