"""
Docker startup initialisation — KB build + mock seed.
Called from main.py lifespan (not HTTP). Uses direct imports and DB session.
"""

import logging
from typing import List

from database.connection import SessionLocal
from database.models import SessionModel
from knowledge.build_welding_kb import build_knowledge_base, kb_is_ready
from models.session import SessionStatus
from routes.dev import run_seed_mock_sessions

logger = logging.getLogger(__name__)


def build_kb() -> None:
    """
    Build ChromaDB knowledge base via direct function call (no subprocess).
    Idempotent: skips rebuild if collection exists and has expected chunk count (63).
    Mirrors seed idempotency — avoids tearing down valid index on every docker-compose up.
    """
    if kb_is_ready():
        logger.info("[INIT] ChromaDB collection already valid — skipping KB rebuild.")
        return
    logger.info("[INIT] Building ChromaDB knowledge base...")
    build_knowledge_base(persist=True, verbose=True)
    logger.info("[INIT] KB ready.")


def _sessions_already_seeded() -> bool:
    """Check if ≥10 COMPLETE sessions exist (aluminum + steel demo). Uses DB directly."""
    db = SessionLocal()
    try:
        count = (
            db.query(SessionModel)
            .filter(SessionModel.status == SessionStatus.COMPLETE.value)
            .count()
        )
        return count >= 10
    finally:
        db.close()


def seed_mock() -> None:
    """
    Seed mock sessions via direct DB call (no HTTP self-call).
    Idempotent: skips if ≥10 sessions present.
    """
    if _sessions_already_seeded():
        logger.info("[INIT] Sessions already present — skipping seed.")
        return

    logger.info("[INIT] Seeding aluminum mock sessions...")
    db = SessionLocal()
    try:
        session_ids = run_seed_mock_sessions(db)
        logger.info("[INIT] Seed complete: %d sessions", len(session_ids))
    finally:
        db.close()


def run() -> None:
    """Run KB build then seed. Called from lifespan."""
    build_kb()
    seed_mock()
    logger.info("[INIT] System ready.")
