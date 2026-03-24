"""
WarpSense AI analysis routes.

POST /api/sessions/{session_id}/analyse  — stream WarpSense pipeline as SSE
GET  /api/sessions/{session_id}/reports  — retrieve persisted quality report
GET  /api/health/warp                    — WarpSense component health check
GET  /api/mock-sessions                  — 10 aluminium demo sessions (in-memory)

All session routes use the same get_db pattern as routes/sessions.py.
Do NOT add these routes to sessions.py — AI analysis is a separate domain.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as OrmSession

from data.mock_welders import WELDER_ARCHETYPES
from database.models import SessionModel, WeldQualityReportModel
from routes.sessions import get_db
from services.warp_service import analyse_session_stream, get_graph, get_classifier

logger = logging.getLogger(__name__)
router = APIRouter(tags=["warp-analysis"])

# Aluminium archetype welder IDs — match WELDER_ARCHETYPES entries for the demo surface.
_MOCK_SESSION_WELDER_IDS = {"expert_aluminium_001", "novice_aluminium_001"}

# Anchor timestamp for deterministic session ordering in the demo.
# Sessions are numbered oldest-first from this point, 1 day apart.
_MOCK_BASE_TIMESTAMP = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)


@router.post("/api/sessions/{session_id}/analyse")
async def run_analysis(
    session_id: str,
    db: OrmSession = Depends(get_db),
):
    """
    Stream WarpSense AI quality analysis as Server-Sent Events (text/event-stream).

    Streams 9 SSE events covering pipeline stages: start → thermal_agent →
    geometry_agent → process_agent → summary → complete (with full report payload).

    Errors are emitted as SSE stage="error" events rather than HTTP error codes.
    The stream always returns HTTP 200; the client must inspect each event's stage.
    Re-analysing a session overwrites the previous report.

    Phase UI-4 must use fetch() + ReadableStream to consume this stream;
    the browser EventSource API is GET-only and is incompatible with this POST route.
    """
    return StreamingResponse(
        analyse_session_stream(session_id, db),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control":     "no-cache",
            # Prevents GZipMiddleware from buffering SSE events until minimum_size
            # (1 KB) is reached — without this header, all events arrive at the client
            # in one dump when the pipeline completes rather than streaming live.
            "Content-Encoding":  "identity",
        },
    )


@router.get("/api/sessions/{session_id}/reports")
async def get_report(
    session_id: str,
    db: OrmSession = Depends(get_db),
):
    """
    Retrieve the most recent WarpSense quality report for a session.

    Returns:
      200: quality report
      404: no report found (session not yet analysed)
    """
    report_model = (
        db.query(WeldQualityReportModel)
        .filter_by(session_id=session_id)
        .first()
    )
    if report_model is None:
        raise HTTPException(
            status_code=404,
            detail=f"No quality report found for session {session_id}. "
                   "Call POST /api/sessions/{session_id}/analyse first.",
        )

    return {
        "session_id": report_model.session_id,
        "report_id": report_model.id,
        "disposition": report_model.disposition,
        "disposition_rationale": report_model.disposition_rationale,
        "quality_class": report_model.quality_class,
        "confidence": report_model.confidence,
        "iso_5817_level": report_model.iso_5817_level,
        "primary_defect_categories": report_model.primary_defect_categories,
        "root_cause": report_model.root_cause,
        "corrective_actions": report_model.corrective_actions,
        "standards_references": report_model.standards_references,
        "retrieved_chunks_used": report_model.retrieved_chunks_used,
        "threshold_violations": report_model.threshold_violations,
        "self_check_passed": report_model.self_check_passed,
        "self_check_notes": report_model.self_check_notes,
        "agent_type": report_model.agent_type,
        "report_timestamp": report_model.report_timestamp.isoformat(),
        "llm_raw_response": report_model.llm_raw_response,
        "rework_cost_usd": report_model.rework_cost_usd,
    }


@router.get("/api/health/warp")
async def warp_health():
    """
    WarpSense component health check.
    Distinct from /api/ai/health which checks Cactus/Gemini.

    Returns:
      200: component statuses (graph_initialised, classifier_initialised)
    """
    status = {
        "graph_initialised": False,
        "classifier_initialised": False,
    }

    try:
        graph = get_graph()
        status["graph_initialised"] = graph is not None
    except Exception as e:
        logger.warning("warp_health graph check failed: %s", e)

    try:
        clf = get_classifier()
        status["classifier_initialised"] = clf is not None and getattr(clf, "_model", None) is not None
    except Exception as e:
        logger.warning("warp_health classifier check failed: %s", e)

    return status


@router.get("/api/mock-sessions")
async def get_mock_sessions():
    """
    Return session metadata for the 10 aluminium demo sessions, generated in-memory.

    No DB required — uses WELDER_ARCHETYPES to determine session count per welder.
    arc_on_ratio and disposition are null (sessions are in pre-analysis state).
    Sessions are ordered chronologically: expert_aluminium_001 first, then novice.
    Timestamps are deterministic (no randomness) for exact replay in tests.
    """
    sessions = []
    session_index = 0

    for archetype in WELDER_ARCHETYPES:
        if archetype["welder_id"] not in _MOCK_SESSION_WELDER_IDS:
            continue

        for i in range(archetype["sessions"]):
            # Must match scripts/seed_demo_data.py: sess_{welder_id}_{n:03d} for n in 1..sessions
            session_id = f"sess_{archetype['welder_id']}_{i + 1:03d}"

            # 1 day apart, oldest first — deterministic, no randomness
            started_at = _MOCK_BASE_TIMESTAMP + timedelta(days=session_index)

            sessions.append({
                "session_id":     session_id,
                "welder_id":      archetype["welder_id"],
                "welder_name":    archetype["name"],
                "arc_type":       archetype["arc"],
                # null until POST /analyse has been called for this session
                "arc_on_ratio":   None,
                "disposition":    None,
                "started_at":     started_at.isoformat(),
            })
            session_index += 1

    return sessions


# Disposition → numeric quality score.
# Single source of truth: backend computes score; frontend uses it verbatim.
_DISPOSITION_SCORE: dict[str, float] = {
    "PASS":             1.0,
    "CONDITIONAL":      0.5,
    "REWORK_REQUIRED":  0.0,
}


@router.get("/api/welders/{welder_id}/quality-trend")
async def get_quality_trend(
    welder_id: str,
    db: OrmSession = Depends(get_db),
):
    """
    Return last 10 quality reports for a welder, ordered oldest-first.

    Each item:
      session_id      — report's session
      report_timestamp — ISO-8601 UTC string
      weld_type       — from sessions table (null if session row absent)
      disposition     — PASS / CONDITIONAL / REWORK_REQUIRED
      quality_score   — 1.0 / 0.5 / 0.0 (deterministic from disposition)

    Filters by operator_id = welder_id.
    In the demo context welder_id == operator_id (e.g. expert_aluminium_001).
    """
    rows = (
        db.query(WeldQualityReportModel, SessionModel.weld_type)
        .outerjoin(SessionModel, WeldQualityReportModel.session_id == SessionModel.session_id)
        .filter(WeldQualityReportModel.operator_id == welder_id)
        .order_by(WeldQualityReportModel.report_timestamp.asc())
        .limit(10)
        .all()
    )

    result = []
    for report, weld_type in rows:
        score = _DISPOSITION_SCORE.get(report.disposition)
        if score is None:
            logger.warning(
                "get_quality_trend: unknown disposition %r for session %s — skipping row",
                report.disposition,
                report.session_id,
            )
            continue
        result.append({
            "session_id":        report.session_id,
            "report_timestamp":  report.report_timestamp.isoformat(),
            "weld_type":         weld_type,
            "disposition":       report.disposition,
            "quality_score":     score,
        })
    return result
