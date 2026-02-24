"""
Dev-only routes for seeding mock data.
Enabled only when ENV=development or DEBUG=1.
"""

import logging
import os
import random
import traceback

from fastapi import APIRouter, Depends, HTTPException

from database.connection import SessionLocal
from database.models import SessionModel
from sqlalchemy.orm import Session as OrmSession

router = APIRouter()
logger = logging.getLogger(__name__)


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


def _handle_seed_error(exc: BaseException) -> HTTPException:
    """Return 500 with traceback in dev for easier debugging."""
    if _is_dev_mode():
        return HTTPException(
            status_code=500,
            detail={"error": str(exc), "traceback": traceback.format_exc()},
        )
    return HTTPException(status_code=500, detail="Seed failed")


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

    try:
        from data.mock_welders import WELDER_ARCHETYPES
        from data.mock_sessions import (
            generate_session_for_welder,
            generate_expert_session,
            generate_novice_session,
        )

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

        # Also seed sess_expert_001 and sess_novice_001 (used by replay/STARTME)
        demo_ids = ["sess_expert_001", "sess_novice_001"]
        for existing in db.query(SessionModel).filter(
            SessionModel.session_id.in_(demo_ids)
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

        for sid in demo_ids:
            session = (
                generate_expert_session(sid)
                if "expert" in sid
                else generate_novice_session(sid)
            )
            model = SessionModel.from_pydantic(session)
            db.add(model)
            session_ids.append(sid)

        db.commit()

        # Seed drills and cert_standards for coaching-plan and certification-status smoke tests
        try:
            from scripts.seed_demo_data import _seed_drills, _seed_cert_standards
            _seed_drills(db)
            _seed_cert_standards(db)
        except Exception as drill_cert_err:
            logger.warning(
                "Drills/cert seed failed (non-fatal): %s. Coaching/cert endpoints may fail until manual seed.",
                drill_cert_err,
            )

        return {"seeded": session_ids}
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_seed_error(e)


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
    session_ids.extend(["sess_expert_001", "sess_novice_001"])

    deleted = db.query(SessionModel).filter(
        SessionModel.session_id.in_(session_ids)
    ).delete(synchronize_session=False)
    db.commit()

    return {"deleted": deleted, "ids": session_ids}
