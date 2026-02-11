"""
Dev-only routes for seeding mock data.
Enabled only when ENV=development or DEBUG=1.
"""

import os

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
    Seed expert and novice mock sessions into the database.
    Only available when ENV=development or DEBUG=1.

    Seeds:
      - sess_expert_001 (expert welder, 15s, stable signals)
      - sess_novice_001 (novice welder, 15s, erratic + thermal gap)

    Visit /replay/sess_expert_001 or /replay/sess_novice_001 after seeding.
    """
    if not _is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Seed route is only available in development (ENV=development or DEBUG=1)",
        )

    from data.mock_sessions import generate_expert_session, generate_novice_session

    session_ids = ["sess_expert_001", "sess_novice_001"]

    for existing in db.query(SessionModel).filter(
        SessionModel.session_id.in_(session_ids)
    ).all():
        db.delete(existing)
    db.flush()

    expert = generate_expert_session(session_id="sess_expert_001")
    novice = generate_novice_session(session_id="sess_novice_001")

    for session in [expert, novice]:
        model = SessionModel.from_pydantic(session)
        db.add(model)

    db.commit()

    return {"seeded": session_ids}
