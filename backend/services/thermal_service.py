"""
Thermal service utilities for heat dissipation calculations.
Heat dissipation is only calculated when both current and previous frames have valid center temperature data; otherwise it safely returns None.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from database.models import FrameModel
from models.frame import Frame


def get_previous_frame(
    session_id: str, timestamp_ms: int, db: OrmSession
) -> Optional[Frame]:
    """Fetch the most recent frame before timestamp_ms for a session."""
    stmt = (
        select(FrameModel)
        .where(FrameModel.session_id == session_id)
        .where(FrameModel.timestamp_ms < timestamp_ms)
        .order_by(FrameModel.timestamp_ms.desc())
        .limit(1)
    )
    result = db.execute(stmt).scalars().first()
    if result is None:
        return None
    return result.to_pydantic()


def _extract_center_temperature_celsius(frame: Frame) -> Optional[float]:
    if not frame.has_thermal_data:
        return None
    if not frame.thermal_snapshots:
        return None
    first_snapshot = frame.thermal_snapshots[0]
    if not first_snapshot.readings:
        return None
    center = next(
        (
            reading
            for reading in first_snapshot.readings
            if reading.direction == "center"
        ),
        None,
    )
    if center is None:
        return None
    return center.temp_celsius


def calculate_heat_dissipation(
    prev_frame: Optional[Frame],
    curr_frame: Frame,
    db: Optional[OrmSession] = None,
    session_id: Optional[str] = None,
    sample_interval_seconds: float = 0.1,
) -> Optional[float]:
    """Calculate heat dissipation rate with null-safe checks.

    Formula: (prev_center_temp - curr_center_temp) / sample_interval_seconds
    Default: thermal snapshots every 100ms (0.1s). Can override for testing.
    Raises ZeroDivisionError if sample_interval_seconds == 0.
    """
    if sample_interval_seconds == 0:
        raise ZeroDivisionError("sample_interval_seconds must be non-zero")

    if prev_frame is None and db is not None and session_id is not None:
        prev_frame = get_previous_frame(
            session_id=session_id, timestamp_ms=curr_frame.timestamp_ms, db=db
        )

    if prev_frame is None:
        return None
    if not prev_frame.has_thermal_data:
        return None
    if not curr_frame.has_thermal_data:
        return None
    if not prev_frame.thermal_snapshots or not curr_frame.thermal_snapshots:
        return None

    prev_center = _extract_center_temperature_celsius(prev_frame)
    curr_center = _extract_center_temperature_celsius(curr_frame)
    if prev_center is None or curr_center is None:
        return None

    return (prev_center - curr_center) / sample_interval_seconds
