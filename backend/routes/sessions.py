"""
Sessions API routes
Exposes endpoints for welding session data
This API is the bridge between your sensors (frontend or ESP32) and the backend models, validating and storing high-frequency welding data while calculating thermal metrics for later comparison.
Key points of failure:
the frame data must be between 1000 and 5000 frames per request
Frame Timestamps must be strictly increasing, 10ms apart.
Session status: Cannot add frames if status == COMPLETE.
Concurrency: Session cannot be uploaded to if currently locked (locked_until).
Streaming threshold: Total frames > 1000 triggers streaming; otherwise uses paginated JSON.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession, joinedload

from database.connection import SessionLocal
from database.models import FrameModel, SessionModel
from features.extractor import extract_features
from models.frame import Frame
from models.session import Session, SessionStatus
from scoring.rule_based import score_session
from services.benchmark_service import get_welder_benchmarks
from services.coaching_service import assign_coaching_plan, evaluate_progress
from services.thermal_service import calculate_heat_dissipation
from services.threshold_service import get_thresholds
from realtime.alert_engine import AlertEngine
from realtime.alert_models import AlertPayload, FrameInput

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /sessions request body
# ---------------------------------------------------------------------------


VALID_PROCESS_TYPES = frozenset({"mig", "tig", "stick", "flux_core", "aluminum"})


class CreateSessionRequest(BaseModel):
    """Request body for creating a new recording session."""

    operator_id: str = Field(..., description="Operator identifier for audit.")
    weld_type: str = Field(..., description="Weld type identifier.")
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID. If omitted, a UUID is generated.",
    )
    process_type: Optional[str] = Field(
        None,
        description="Process type: mig|tig|stick|flux_core|aluminum. Default mig.",
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ns_asymmetry_from_frame_data(frame_data: dict) -> float:
    """North minus south at 10mm. 0 if no thermal. Mirrors simulate_realtime._ns_asymmetry_from_frame."""
    snapshots = frame_data.get("thermal_snapshots") or []
    if not snapshots:
        return 0.0
    snap = snapshots[0]
    readings = snap.get("readings") or []
    north = next(
        (r["temp_celsius"] for r in readings if r.get("direction") == "north"),
        None,
    )
    south = next(
        (r["temp_celsius"] for r in readings if r.get("direction") == "south"),
        None,
    )
    if north is None or south is None:
        return 0.0
    return float(north) - float(south)


def get_session_frames_raw(
    session_id: str, db: OrmSession, limit: int = 50
) -> list[dict] | None:
    """
    Returns the last `limit` frames of a session as raw dicts (ascending by timestamp_ms).
    Each dict has same shape as Frame.model_dump() — required for extract_features.
    Returns None if session not found.
    Uses copy.deepcopy to avoid shared nested references (SQLAlchemy JSONB may share refs).
    """
    import copy

    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        return None
    frames = (
        db.query(FrameModel)
        .filter_by(session_id=session_id)
        .order_by(FrameModel.timestamp_ms.desc())
        .limit(limit)
        .all()
    )
    return [copy.deepcopy(dict(f.frame_data)) for f in reversed(frames)]


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    db: OrmSession = Depends(get_db),
):
    """
    Create a new welding session in RECORDING status.
    Use the returned session_id when calling POST /sessions/{session_id}/frames.
    """
    session_id = body.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    existing = db.query(SessionModel).filter_by(session_id=session_id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Session {session_id} already exists",
        )

    process_type = (body.process_type or "mig").lower().strip()
    if process_type not in VALID_PROCESS_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"process_type must be one of: mig, tig, stick, flux_core, aluminum (got: {body.process_type!r})",
        )

    model = SessionModel(
        session_id=session_id,
        operator_id=body.operator_id,
        start_time=datetime.now(timezone.utc),
        weld_type=body.weld_type,
        thermal_sample_interval_ms=100,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status=SessionStatus.RECORDING.value,
        frame_count=0,
        expected_frame_count=None,
        last_successful_frame_index=None,
        validation_errors=[],
        completed_at=None,
        disable_sensor_continuity_checks=False,
        locked_until=None,
        version=1,
        process_type=process_type,
    )
    db.add(model)
    db.commit()
    return {"session_id": session_id}


@router.get("/sessions")
async def list_sessions():
    """
    List all welding sessions - Not implemented yet

    Returns:
        List of welding sessions

    Raises:
        HTTPException: 501 Not Implemented
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    include_thermal: bool = Query(True, description="Include thermal snapshot data"),
    time_range_start: Optional[int] = Query(None, description="Start time in ms"),
    time_range_end: Optional[int] = Query(None, description="End time in ms"),
    limit: int = Query(1000, ge=1, le=10000, description="Max frames to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    stream: bool = Query(False, description="Stream response for large sessions"),
    db: OrmSession = Depends(get_db),
):
    """
    Get a specific welding session - Not implemented yet

    Args:
        session_id: Session ID to retrieve

    Returns:
        Session object

    Raises:
        HTTPException: 501 Not Implemented
    """
    session_model = db.query(SessionModel).filter_by(session_id=session_id).first()
    if session_model is None:
        raise HTTPException(status_code=404, detail="Session not found")

    base_query = db.query(FrameModel).filter(FrameModel.session_id == session_id)
    if time_range_start is not None:
        base_query = base_query.filter(FrameModel.timestamp_ms >= time_range_start)
    if time_range_end is not None:
        base_query = base_query.filter(FrameModel.timestamp_ms <= time_range_end)

    total_frame_count = session_model.frame_count
    if total_frame_count > 10000 and not stream and offset == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Session has {total_frame_count} frames. "
                "Use pagination (limit/offset) or streaming (stream=true) to fetch in chunks."
            ),
        )

    def session_payload(frames: List[dict]) -> dict:
        completed_at = session_model.completed_at
        return {
            "session_id": session_model.session_id,
            "operator_id": session_model.operator_id,
            "start_time": session_model.start_time.isoformat(),
            "weld_type": session_model.weld_type,
            "thermal_sample_interval_ms": session_model.thermal_sample_interval_ms,
            "thermal_directions": session_model.thermal_directions,
            "thermal_distance_interval_mm": session_model.thermal_distance_interval_mm,
            "sensor_sample_rate_hz": session_model.sensor_sample_rate_hz,
            "status": session_model.status,
            "frame_count": session_model.frame_count,
            "expected_frame_count": session_model.expected_frame_count,
            "last_successful_frame_index": session_model.last_successful_frame_index,
            "validation_errors": session_model.validation_errors,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "disable_sensor_continuity_checks": session_model.disable_sensor_continuity_checks,
            "score_total": getattr(session_model, "score_total", None),
            "process_type": getattr(session_model, "process_type", None) or "mig",
            "frames": frames,
        }

    def frame_to_dict(frame_model: FrameModel) -> dict:
        frame_data = dict(frame_model.frame_data)
        if not include_thermal:
            frame_data["thermal_snapshots"] = []
        return frame_data

    if stream and total_frame_count > 1000:

        def generate():
            # Use a dedicated session so stream lifecycle is independent of
            # request-scoped db (avoids "session closed" if teardown runs early).
            stream_db = SessionLocal()
            try:
                payload_prefix = session_payload([])
                payload_prefix.pop("frames", None)
                prefix = json.dumps(payload_prefix)
                yield prefix[:-1]
                yield ',"frames":['
                first = True
                stream_query = stream_db.query(FrameModel).filter(
                    FrameModel.session_id == session_id
                )
                if time_range_start is not None:
                    stream_query = stream_query.filter(
                        FrameModel.timestamp_ms >= time_range_start
                    )
                if time_range_end is not None:
                    stream_query = stream_query.filter(
                        FrameModel.timestamp_ms <= time_range_end
                    )
                stream_query = stream_query.order_by(
                    FrameModel.timestamp_ms.asc()
                ).yield_per(1000)
                for frame_model in stream_query:
                    if not first:
                        yield ","
                    first = False
                    yield json.dumps(frame_to_dict(frame_model))
                yield "]}"
            finally:
                stream_db.close()

        return StreamingResponse(
            generate(),
            media_type="application/json",
            headers={"X-Streaming": "true"},
        )

    paginated = (
        base_query.order_by(FrameModel.timestamp_ms.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    frames = [frame_to_dict(frame_model) for frame_model in paginated]
    return session_payload(frames)


@router.get("/sessions/{session_id}/features")
async def get_session_features(session_id: str):
    """
    Get extracted features for a session - Not implemented yet

    Args:
        session_id: Session ID

    Returns:
        Dictionary of extracted features

    Raises:
        HTTPException: 501 Not Implemented
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/sessions/{session_id}/score")
async def get_session_score(
    session_id: str,
    db: OrmSession = Depends(get_db),
):
    """
    Get rule-based score for a welding session.
    Persists score_total when computed (lazy write-through) for COMPLETE sessions.

    Loads session with frames (joinedload), extracts 5 features, runs 5 rules,
    returns { total, rules } with actual_value per rule for "actual vs threshold" display.

    Returns:
        200: { total: 0-100, rules: [{ rule_id, threshold, passed, actual_value }] }
        404: Session not found
    """
    session_model = (
        db.query(SessionModel)
        .options(joinedload(SessionModel.frames))
        .filter_by(session_id=session_id)
        .first()
    )
    if not session_model:
        raise HTTPException(status_code=404, detail="Session not found")

    frames = getattr(session_model, "frames", None) or []
    if not frames or len(frames) < 10:
        raise HTTPException(
            status_code=400,
            detail="Session has insufficient frames for scoring (minimum 10 required)",
        )

    session = session_model.to_pydantic()
    process_type = getattr(session_model, "process_type", None) or "mig"
    thresholds = get_thresholds(db, process_type)
    features = extract_features(
        session, angle_target_deg=thresholds.angle_target_degrees
    )
    score = score_session(session, features, thresholds)

    # Lazy persistence: if COMPLETE and score_total is null, persist
    if (
        session_model.status == SessionStatus.COMPLETE.value
        and session_model.score_total is None
        and session_model.frame_count > 0
    ):
        session_model.score_total = score.total
        db.commit()
        # Non-critical: evaluate coaching progress; auto-assign drills when score < 60
        if session_model.operator_id:
            try:
                evaluate_progress(session_model.operator_id, db)
                if score.total < 60:
                    benchmark_data = get_welder_benchmarks(
                        session_model.operator_id, db
                    )
                    assign_coaching_plan(
                        session_model.operator_id, benchmark_data, db
                    )
            except Exception as e:
                logger.warning(
                    "Post-score coaching hook failed for %s: %s",
                    session_model.operator_id,
                    e,
                )
                # Never fail the score request due to coaching errors

    result = score.model_dump()
    try:
        from scoring.scorer import score_session_decomposed, _build_alerts_from_frames

        alerts = _build_alerts_from_frames(list(session.frames))
        decomposed = score_session_decomposed(list(session.frames), alerts, session_id)
        result["session_score"] = decomposed.model_dump()
    except Exception:
        logger.exception("Decomposed score failed")
        # Only suppress and return null in production; re-raise in dev/staging so failures are visible
        if os.environ.get("ENV") != "production":
            raise
        result["session_score"] = None
    # TODO Session 4: remove legacy total/rules, use session_score only.
    # TODO Before Session 4: add mock WPS config (0.4–1.0) for test sessions or explicit annotation when expert mock (0.5–0.9) flags below WPS (0.9 floor); QA will otherwise see every expert failing heat_input.
    result["active_threshold_spec"] = {
        "weld_type": thresholds.weld_type,
        "angle_target": thresholds.angle_target_degrees,
        "angle_warning": thresholds.angle_warning_margin,
        "angle_critical": thresholds.angle_critical_margin,
        "thermal_symmetry_warning_celsius": thresholds.thermal_symmetry_warning_celsius,
        "thermal_symmetry_critical_celsius": thresholds.thermal_symmetry_critical_celsius,
        "amps_stability_warning": thresholds.amps_stability_warning,
        "volts_stability_warning": thresholds.volts_stability_warning,
        "heat_diss_consistency": thresholds.heat_diss_consistency,
    }
    return result


@router.post("/sessions/{session_id}/rescore")
async def rescore_session(
    session_id: str,
    db: OrmSession = Depends(get_db),
):
    """Recompute decomposed score, persist score_total. For backfill after scoring changes."""
    # TODO: add auth guard before exposing to QA environment
    session_model = (
        db.query(SessionModel)
        .options(joinedload(SessionModel.frames))
        .filter_by(session_id=session_id)
        .first()
    )
    if not session_model:
        raise HTTPException(status_code=404, detail="Session not found")
    frames = getattr(session_model, "frames", None) or []
    if len(frames) < 10:
        raise HTTPException(status_code=400, detail="Insufficient frames for scoring")
    session = session_model.to_pydantic()
    from scoring.scorer import score_session_decomposed, _build_alerts_from_frames

    alerts = _build_alerts_from_frames(list(session.frames))
    decomposed = score_session_decomposed(list(session.frames), alerts, session_id)
    session_model.score_total = int(round(decomposed.overall_score * 100))
    db.commit()
    return decomposed.model_dump()


@router.get("/sessions/{session_id}/alerts")
async def get_session_alerts(
    session_id: str,
    db: OrmSession = Depends(get_db),
):
    """
    Run session frames through AlertEngine, return pre-computed alerts.
    Caps at 2000 frames (same as compare page).
    """
    session_model = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session_model:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        frames_query = (
            db.query(FrameModel)
            .filter_by(session_id=session_id)
            .order_by(FrameModel.timestamp_ms.asc())
            .limit(2000)
        )
        frame_models = frames_query.all()

        config_path = (
            Path(__file__).resolve().parent.parent
            / "config"
            / "alert_thresholds.json"
        )
        engine = AlertEngine(str(config_path))
        alerts: list[dict] = []

        for i, fm in enumerate(frame_models):
            fd = dict(fm.frame_data)
            ns = _ns_asymmetry_from_frame_data(fd)
            ts_ms = fd.get("timestamp_ms")
            if ts_ms is None:
                ts_ms = fm.timestamp_ms
            fin = FrameInput(
                frame_index=i,
                timestamp_ms=float(ts_ms),
                travel_angle_degrees=fd.get("travel_angle_degrees"),
                travel_speed_mm_per_min=fd.get("travel_speed_mm_per_min"),
                ns_asymmetry=ns,
                volts=fd.get("volts"),
                amps=fd.get("amps"),
            )
            alert = engine.push_frame(fin)
            if alert:
                alerts.append(alert.model_dump())

        logger.info(
            "get_session_alerts OK session_id=%s alerts=%d",
            session_id,
            len(alerts),
        )
        return {"alerts": alerts}
    except FileNotFoundError as e:
        logger.warning("get_session_alerts config missing: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Alert thresholds config not found",
        ) from e
    except Exception as e:
        logger.warning("get_session_alerts failed session_id=%s: %s", session_id, e)
        raise HTTPException(
            status_code=500,
            detail="Failed to compute alerts",
        ) from e


@router.post("/sessions/{session_id}/frames")
async def add_frames(
    session_id: str,
    frames: List[Frame],
    db: OrmSession = Depends(get_db),
):
    if not frames:
        raise HTTPException(status_code=400, detail="No frames provided")
    if len(frames) < 1000 or len(frames) > 5000:
        raise HTTPException(
            status_code=400, detail="Frames per request must be between 1000 and 5000"
        )

    now = datetime.now(timezone.utc)
    errors = []

    try:
        with db.begin():
            session_row = (
                db.execute(
                    select(SessionModel)
                    .where(SessionModel.session_id == session_id)
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            if session_row is None:
                raise HTTPException(status_code=404, detail="Session not found")
            if session_row.status == SessionStatus.COMPLETE.value:
                raise HTTPException(
                    status_code=400, detail="Cannot add frames to a complete session"
                )
            if session_row.locked_until:
                locked_until = session_row.locked_until
                compare_now = now
                if locked_until.tzinfo is None:
                    compare_now = now.replace(tzinfo=None)
                if locked_until > compare_now:
                    raise HTTPException(
                        status_code=409,
                        detail="Session is locked for concurrent upload",
                    )

            session_row.locked_until = now + timedelta(seconds=30)

            last_frame = (
                db.execute(
                    select(FrameModel)
                    .where(FrameModel.session_id == session_id)
                    .order_by(FrameModel.timestamp_ms.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            last_timestamp = last_frame.timestamp_ms if last_frame else None

            timestamps = [frame.timestamp_ms for frame in frames]
            if timestamps != sorted(timestamps):
                errors.append(
                    {
                        "index": None,
                        "timestamp_ms": None,
                        "error": "Frames must be sorted by timestamp",
                    }
                )
            if len(timestamps) != len(set(timestamps)):
                errors.append(
                    {
                        "index": None,
                        "timestamp_ms": None,
                        "error": "Duplicate frame timestamps in request",
                    }
                )

            if last_timestamp is not None:
                expected_first = last_timestamp + 10
                if timestamps[0] != expected_first:
                    errors.append(
                        {
                            "index": 0,
                            "timestamp_ms": timestamps[0],
                            "error": f"First frame must start at {expected_first}ms",
                        }
                    )

            for i in range(1, len(timestamps)):
                if timestamps[i] - timestamps[i - 1] != 10:
                    errors.append(
                        {
                            "index": i,
                            "timestamp_ms": timestamps[i],
                            "error": "Frames must be continuous at 10ms intervals",
                        }
                    )

            if errors:
                session_row.locked_until = None
                return {
                    "status": "failed",
                    "successful_count": 0,
                    "failed_frames": errors,
                    "next_expected_timestamp": (
                        (last_timestamp + 10) if last_timestamp is not None else None
                    ),
                    "can_resume": False,
                }

            prev_frame = last_frame.to_pydantic() if last_frame else None
            frame_models: List[FrameModel] = []
            for frame in frames:
                dissipation = calculate_heat_dissipation(prev_frame, frame, db=None)
                updated_frame = frame.model_copy(
                    update={"heat_dissipation_rate_celsius_per_sec": dissipation}
                )
                frame_models.append(
                    FrameModel(
                        session_id=session_id,
                        timestamp_ms=updated_frame.timestamp_ms,
                        frame_data=updated_frame.model_dump(),
                    )
                )
                prev_frame = updated_frame

            db.add_all(frame_models)

            session_row.frame_count += len(frames)
            session_row.last_successful_frame_index = session_row.frame_count - 1
            session_row.locked_until = None

        next_expected = timestamps[-1] + 10
        return {
            "status": "success",
            "successful_count": len(frames),
            "failed_frames": [],
            "next_expected_timestamp": next_expected,
            "can_resume": True,
        }
    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        return {
            "status": "failed",
            "successful_count": 0,
            "failed_frames": [
                {
                    "index": None,
                    "timestamp_ms": None,
                    "error": "Database constraint violated",
                }
            ],
            "next_expected_timestamp": None,
            "can_resume": False,
        }
    except Exception:
        db.rollback()
        # Sanitize: do not expose internal exception details to client
        return {
            "status": "failed",
            "successful_count": 0,
            "failed_frames": [
                {"index": None, "timestamp_ms": None, "error": "Internal error during frame ingestion"}
            ],
            "next_expected_timestamp": None,
            "can_resume": False,
        }
