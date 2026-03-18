"""
WarpSense singleton service.

init_warp_components() — called once in main.py lifespan after DB check.
analyse_session()      — called by POST /sessions/{session_id}/analyse route.
get_graph()            — returns shared WarpSenseGraph instance.
get_classifier()       — returns shared WeldClassifier instance.

Singleton pattern: _graph and _classifier are module-level. init_warp_components()
populates them. get_graph()/get_classifier() include a lazy-init fallback so the
service works even if lifespan was not used (e.g. in tests).
"""

import asyncio
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session as OrmSession

from database.models import SessionModel, WeldQualityReportModel
from routes.sessions import get_session_frames_raw
from agent.warpsense_graph import WarpSenseGraph
from features.session_feature_extractor import (
    SessionFeatureExtractor,
    generate_feature_dataset,
)
from features.weld_classifier import WeldClassifier

logger = logging.getLogger(__name__)

_graph: Optional[WarpSenseGraph] = None
_classifier: Optional[WeldClassifier] = None


def init_warp_components() -> None:
    """
    Initialise WarpSenseGraph and WeldClassifier once at startup.
    Called from main.py lifespan after check_db_connectivity().
    Safe to call multiple times — no-op if already initialised.
    """
    global _graph, _classifier
    if _graph is not None and _classifier is not None:
        return

    # Fail fast on missing LLM credentials (prevents first-request 500)
    if not (os.getenv("GROQ_API_KEY") or "").strip():
        raise RuntimeError("GROQ_API_KEY is not set (required for WarpSense analysis)")

    logger.info("warp_service: initialising WarpSenseGraph...")
    _graph = WarpSenseGraph(verbose=False)

    logger.info("warp_service: training WeldClassifier...")
    dataset = generate_feature_dataset()
    clf = WeldClassifier()
    clf.train(dataset)
    _classifier = clf

    logger.info(
        "warp_service: ready — graph=%s classifier=%s",
        type(_graph).__name__,
        type(_classifier).__name__,
    )


def get_graph() -> WarpSenseGraph:
    if _graph is None:
        init_warp_components()
    return _graph


def get_classifier() -> WeldClassifier:
    if _classifier is None:
        init_warp_components()
    return _classifier


# IMPORTANT: Do NOT re-implement frame queries here.
# Use `routes.sessions.get_session_frames_raw(session_id, db, limit=1500)` which already:
# - Returns dicts in ascending timestamp_ms order
# - Uses copy.deepcopy to avoid JSON ref aliasing
# - Mirrors the contract expected by SessionFeatureExtractor.extract()


async def analyse_session(session_id: str, db: OrmSession) -> WeldQualityReportModel:
    """
    Run full WarpSense pipeline for a session and persist the result.

    Steps:
      1. Load frames from DB (last 1500, ascending)
      2. Extract SessionFeatures via SessionFeatureExtractor
      3. Predict quality_class via WeldClassifier
      4. Assess via WarpSenseGraph → WeldQualityReport
      5. Persist WeldQualityReportModel (upsert by session_id)
      6. Return persisted model row

    Raises:
      ValueError: session not found, no frames, or feature extractor rejects session (e.g. < 100 arc-on frames)
      RuntimeError: WarpSenseGraph or classifier not initialised
    """
    # 1. Load frames
    session_model = db.query(SessionModel).filter_by(session_id=session_id).first()
    if session_model is None:
        raise ValueError(f"Session {session_id} not found")

    # Load frames using the existing proven helper (do NOT re-implement the query)
    frames = get_session_frames_raw(session_id, db, limit=1500)
    if not frames:
        raise ValueError(f"Session {session_id} has no frames")
    # NOTE: Do NOT pre-check raw frame count here. `SessionFeatureExtractor.extract()`
    # enforces the real minimum (>= 100 arc-on frames after filtering volts/amps),
    # and raw frame count is not a reliable proxy.

    # 2. Extract features
    extractor = SessionFeatureExtractor()
    features = extractor.extract(session_id, frames)

    # 3. Classify
    classifier = get_classifier()
    prediction = classifier.predict(features)

    # 4. Assess (CF5)
    # WarpSenseGraph.assess() is synchronous and includes blocking network I/O (Groq).
    # In an async FastAPI server, this MUST NOT run on the event loop thread.
    graph = get_graph()
    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(None, lambda: graph.assess(prediction, features))

    # 5. Persist (upsert: delete existing then insert)
    existing = db.query(WeldQualityReportModel).filter_by(session_id=session_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    report_model = WeldQualityReportModel(
        session_id=session_id,
        operator_id=session_model.operator_id,
        report_timestamp=datetime.now(timezone.utc),
        quality_class=report.quality_class,
        confidence=report.confidence,
        iso_5817_level=report.iso_5817_level,
        disposition=report.disposition,
        disposition_rationale=report.disposition_rationale,
        root_cause=report.root_cause,
        corrective_actions=report.corrective_actions,
        standards_references=report.standards_references,
        retrieved_chunks_used=getattr(report, "retrieved_chunks_used", []),
        primary_defect_categories=report.primary_defect_categories,
        threshold_violations=[asdict(v) for v in report.threshold_violations],
        self_check_passed=report.self_check_passed,
        self_check_notes=report.self_check_notes,
        llm_raw_response=getattr(report, "llm_raw_response", None),
        agent_type="langgraph",
        created_at=datetime.now(timezone.utc),
    )
    db.add(report_model)
    db.flush()  # Get report_model.id without committing

    # Link session -> latest report (CF7) — single transaction
    session_model.quality_report_id = report_model.id
    db.add(session_model)
    db.commit()
    db.refresh(report_model)

    logger.info(
        "warp_service: analyse_session OK session_id=%s disposition=%s",
        session_id,
        report.disposition,
    )
    return report_model
