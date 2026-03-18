"""
WarpSense AI analysis routes.

POST /api/sessions/{session_id}/analyse  — run WarpSense pipeline, persist report
GET  /api/sessions/{session_id}/reports  — retrieve persisted quality report
GET  /api/health/warp                    — WarpSense component health check

All session routes use the same get_db pattern as routes/sessions.py.
Do NOT add these routes to sessions.py — AI analysis is a separate domain.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from database.models import WeldQualityReportModel
from routes.sessions import get_db
from services.warp_service import analyse_session, get_graph, get_classifier

logger = logging.getLogger(__name__)
router = APIRouter(tags=["warp-analysis"])


@router.post("/api/sessions/{session_id}/analyse")
async def run_analysis(
    session_id: str,
    db: OrmSession = Depends(get_db),
):
    """
    Run WarpSense AI quality analysis for a completed welding session.

    Loads frames from DB, extracts 11 LOF/LOP features, classifies quality,
    runs LangGraph multi-agent assessment, persists result.
    Re-analysing a session overwrites the previous report.

    Returns:
      200: quality report (disposition, root_cause, corrective_actions, ...)
      400: insufficient frames or session not in analysable state
      404: session not found
      500: WarpSense pipeline error
    """
    try:
        report_model = await analyse_session(session_id, db)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        logger.exception("run_analysis failed session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail="WarpSense analysis failed")

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
    }


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
