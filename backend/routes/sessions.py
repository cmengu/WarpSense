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
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from database.connection import SessionLocal
from database.models import FrameModel, SessionModel
from models.frame import Frame
from models.session import SessionStatus
from services.thermal_service import calculate_heat_dissipation, get_previous_frame

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
            "frames": frames,
        }

    def frame_to_dict(frame_model: FrameModel) -> dict:
        frame_data = dict(frame_model.frame_data)
        if not include_thermal:
            frame_data["thermal_snapshots"] = []
        return frame_data

    if stream and total_frame_count > 1000:

        def generate():
            payload_prefix = session_payload([])
            payload_prefix.pop("frames", None)
            prefix = json.dumps(payload_prefix)
            yield prefix[:-1]
            yield ',"frames":['
            first = True
            stream_query = base_query.order_by(FrameModel.timestamp_ms.asc()).yield_per(
                1000
            )
            for frame_model in stream_query:
                if not first:
                    yield ","
                first = False
                yield json.dumps(frame_to_dict(frame_model))
            yield "]}"

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
async def get_session_score(session_id: str):
    """
    Get scoring for a session - Not implemented yet

    Args:
        session_id: Session ID

    Returns:
        SessionScore object

    Raises:
        HTTPException: 501 Not Implemented
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


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
    except Exception as exc:
        db.rollback()
        return {
            "status": "failed",
            "successful_count": 0,
            "failed_frames": [{"index": None, "timestamp_ms": None, "error": str(exc)}],
            "next_expected_timestamp": None,
            "can_resume": False,
        }
