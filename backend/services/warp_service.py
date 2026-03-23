"""
WarpSense singleton service.

init_warp_components()     — called once in main.py lifespan after DB check.
analyse_session()          — non-streaming pipeline; returns persisted report model.
analyse_session_stream()   — async generator; yields SSE strings for POST /analyse.
get_graph()                — returns shared WarpSenseGraph instance.
get_classifier()           — returns shared WeldClassifier instance.

Singleton pattern: _graph and _classifier are module-level. init_warp_components()
populates them. get_graph()/get_classifier() include a lazy-init fallback so the
service works even if lifespan was not used (e.g. in tests).
"""

import asyncio
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

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


async def analyse_session_stream(session_id: str, db: OrmSession) -> AsyncGenerator[str, None]:
    """
    Async generator — yields SSE-formatted strings for the WarpSense pipeline.

    Event sequence (9 total):
      1.  {"stage": "start",          "status": "running", "message": "Pipeline initialised"}
      2.  {"stage": "thermal_agent",  "status": "running", "message": "Analysing heat profile"}
      3.  {"stage": "thermal_agent",  "status": "done",    "disposition": "..."}
      4.  {"stage": "geometry_agent", "status": "running", "message": "Checking torch angle"}
      5.  {"stage": "geometry_agent", "status": "done",    "disposition": "..."}
      6.  {"stage": "process_agent",  "status": "running", "message": "Evaluating arc stability"}
      7.  {"stage": "process_agent",  "status": "done",    "disposition": "..."}
      8.  {"stage": "summary",        "status": "running", "message": "Synthesising report"}
      9a. {"stage": "complete",       "status": "done",    "report": {...}}   — on success
      9b. {"stage": "error",          "status": "error",   "message": "..."}  — on failure

    Thread-safety contract:
      - _progress_cb runs inside run_in_executor (thread pool thread).
        It MUST use loop.call_soon_threadsafe() to put events on the queue.
      - _run_pipeline() is a coroutine on the event loop.
        It MUST use queue.put_nowait() directly (NOT call_soon_threadsafe).
    """
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _progress_cb(event: dict) -> None:
        # Called from thread executor — call_soon_threadsafe is required here.
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def _sse(event: dict) -> str:
        return f"data: {json.dumps(event)}\n\n"

    # Event 1: emit start immediately before any blocking work
    yield _sse({"stage": "start", "status": "running", "message": "Pipeline initialised"})

    async def _run_pipeline() -> None:
        # Runs on the event loop. Use queue.put_nowait() directly here.
        try:
            # 1. Load session
            session_model = db.query(SessionModel).filter_by(session_id=session_id).first()
            if session_model is None:
                raise ValueError(f"Session {session_id} not found")

            # 2. Load frames (explicit limit=1500 — default is 50)
            frames = get_session_frames_raw(session_id, db, limit=1500)
            if not frames:
                raise ValueError(f"Session {session_id} has no frames")

            # 3. Extract features
            extractor = SessionFeatureExtractor()
            features = extractor.extract(session_id, frames)

            # 4. Classify
            classifier = get_classifier()
            prediction = classifier.predict(features)

            # 5. Assess with per-stage progress — runs in thread executor; blocks until complete.
            #    Events 2–8 are emitted by _progress_cb via call_soon_threadsafe.
            graph = get_graph()
            report = await loop.run_in_executor(
                None,
                lambda: graph.assess_with_progress(prediction, features, _progress_cb),
            )

            # 6. Persist (upsert: delete existing then insert)
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
            db.flush()

            # 7. Link session -> latest report — single transaction
            session_model.quality_report_id = report_model.id
            db.add(session_model)
            db.commit()
            db.refresh(report_model)

            logger.info(
                "warp_service: analyse_session_stream OK session_id=%s disposition=%s",
                session_id,
                report.disposition,
            )

            # Event 9a: success — include full report payload
            queue.put_nowait({
                "stage":      "complete",
                "status":     "done",
                "report": {
                    "session_id":              report_model.session_id,
                    "quality_class":           report_model.quality_class,
                    "confidence":              report_model.confidence,
                    "iso_5817_level":          report_model.iso_5817_level,
                    "disposition":             report_model.disposition,
                    "disposition_rationale":   report_model.disposition_rationale,
                    "root_cause":              report_model.root_cause,
                    "corrective_actions":      report_model.corrective_actions,
                    "standards_references":    report_model.standards_references,
                    "primary_defect_categories": report_model.primary_defect_categories,
                    "threshold_violations":    report_model.threshold_violations,
                    "self_check_passed":       report_model.self_check_passed,
                    "self_check_notes":        report_model.self_check_notes,
                    "report_timestamp":        report_model.report_timestamp.isoformat(),
                    "llm_raw_response":        report_model.llm_raw_response,
                },
            })

        except Exception as e:
            logger.error(
                "warp_service: analyse_session_stream ERROR session_id=%s error=%s",
                session_id, str(e),
            )
            # Event 9b: error — frontend uses stage="error" to trigger retry UI
            queue.put_nowait({"stage": "error", "status": "error", "message": str(e)})
        finally:
            queue.put_nowait(None)  # Sentinel — signals generator to stop

    pipeline_task = asyncio.create_task(_run_pipeline())

    # Drain queue until sentinel, emitting SSE keepalive comments every 10 s.
    # Prevents Nginx proxy_read_timeout (default 60 s) from silently killing
    # the connection during long Groq LLM calls.
    _KEEPALIVE_S = 10.0
    loop = asyncio.get_running_loop()
    _deadline = loop.time() + 300.0

    try:
        while True:
            remaining = _deadline - loop.time()
            if remaining <= 0:
                break
            try:
                event = await asyncio.wait_for(
                    queue.get(), timeout=min(_KEEPALIVE_S, remaining)
                )
            except asyncio.TimeoutError:
                if loop.time() >= _deadline:
                    break
                # SSE comment — ignored by frontend parser; resets proxy idle timer.
                yield ": keepalive\n\n"
                continue
            if event is None:
                break
            yield _sse(event)
    finally:
        # If the client disconnects before the pipeline finishes, cancel the
        # background task so it does not continue DB writes on a closed session.
        if not pipeline_task.done():
            pipeline_task.cancel()
