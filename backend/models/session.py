"""
Session model for canonical time-series welding data.
The Session model wraps frames and enforces that the entire weld is temporally, spatially, and electrically consistent before use.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .frame import Frame


class SessionStatus(str, Enum):
    RECORDING = "recording"
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    FAILED = "failed"
    ARCHIVED = "archived"


class Session(BaseModel):
    """Complete welding session with canonical time-series frames."""

    session_id: str = Field(..., description="Unique session identifier.")
    operator_id: str = Field(..., description="Operator identifier for audit.")
    start_time: datetime = Field(..., description="Session start time (ISO 8601).")
    weld_type: str = Field(..., description="Weld type identifier.")

    thermal_sample_interval_ms: int = Field(
        ...,
        description="Thermal sampling interval in milliseconds.",
        gt=0,
    )
    thermal_directions: List[str] = Field(
        ...,
        description="Ordered thermal directions (center + cardinal).",
        min_length=1,
    )
    thermal_distance_interval_mm: float = Field(
        ...,
        description="Expected distance interval between thermal snapshots in millimeters.",
        gt=0,
    )
    sensor_sample_rate_hz: int = Field(
        ...,
        description="Sensor sampling rate in Hertz.",
        gt=0,
    )

    frames: List[Frame] = Field(default_factory=list, description="Ordered frame list.")

    status: SessionStatus = Field(default=SessionStatus.RECORDING)
    frame_count: int = Field(..., description="Total frame count ingested.")
    expected_frame_count: Optional[int] = Field(
        None,
        description="Expected total frame count for the session.",
    )
    last_successful_frame_index: Optional[int] = Field(
        None,
        description="Last successfully ingested frame index (0-based).",
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Validation errors collected during ingestion.",
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Completion time for status COMPLETE.",
    )
    disable_sensor_continuity_checks: bool = Field(
        default=False,
        description="Disable sensor continuity checks for test data.",
    )

    @staticmethod
    def is_valid_status_transition(
        previous: "SessionStatus", new: "SessionStatus"
    ) -> bool:
        # Assumption: linear progression with archive as terminal state.
        if previous == new:
            return True
        allowed = {
            SessionStatus.RECORDING: {
                SessionStatus.INCOMPLETE,
                SessionStatus.COMPLETE,
                SessionStatus.FAILED,
            },
            SessionStatus.INCOMPLETE: {
                SessionStatus.RECORDING,
                SessionStatus.FAILED,
                SessionStatus.ARCHIVED,
            },
            SessionStatus.COMPLETE: {SessionStatus.ARCHIVED},
            SessionStatus.FAILED: {SessionStatus.ARCHIVED},
            SessionStatus.ARCHIVED: set(),
        }
        return new in allowed.get(previous, set())

    @model_validator(mode="after")
    def validate_frame_count(self) -> "Session":
        if self.frame_count != len(self.frames):
            raise ValueError("frame_count must match number of frames")
        return self

    @model_validator(mode="after")
    def validate_frame_timestamps(self) -> "Session":
        if not self.frames:
            return self
        timestamps = [frame.timestamp_ms for frame in self.frames]
        if len(timestamps) != len(set(timestamps)):
            raise ValueError("Duplicate frame timestamps found")
        for i in range(1, len(timestamps)):
            interval_ms = timestamps[i] - timestamps[i - 1]
            if abs(interval_ms - 10) > 1:
                raise ValueError(
                    f"Frame interval not ~10ms: {interval_ms}ms between frames {i-1} and {i}"
                )
        return self

    @model_validator(mode="after")
    def validate_thermal_distance_consistency(self) -> "Session":
        thermal_frames = [frame for frame in self.frames if frame.has_thermal_data]
        if not thermal_frames:
            return self
        all_distances = set()
        for frame in thermal_frames:
            for snapshot in frame.thermal_snapshots:
                all_distances.add(snapshot.distance_mm)
        sorted_distances = sorted(all_distances)
        if len(sorted_distances) > 1:
            expected_interval = self.thermal_distance_interval_mm
            for i in range(1, len(sorted_distances)):
                interval = sorted_distances[i] - sorted_distances[i - 1]
                if abs(interval - expected_interval) > 0.1:
                    raise ValueError(
                        "Thermal distance interval mismatch: "
                        f"expected {expected_interval}mm, got {interval}mm"
                    )
        return self

    @model_validator(mode="after")
    def validate_complete_session(self) -> "Session":
        if self.status == SessionStatus.COMPLETE:
            if self.expected_frame_count is None:
                raise ValueError(
                    "expected_frame_count is required when status is COMPLETE"
                )
            if self.frame_count != self.expected_frame_count:
                raise ValueError(
                    "frame_count must equal expected_frame_count when status is COMPLETE"
                )
            if self.last_successful_frame_index != self.frame_count - 1:
                raise ValueError(
                    "last_successful_frame_index must match final frame index when COMPLETE"
                )
            if self.completed_at is None:
                raise ValueError("completed_at is required when status is COMPLETE")
        return self

    @model_validator(mode="after")
    def validate_sensor_continuity(self) -> "Session":
        if self.disable_sensor_continuity_checks:
            return self
        for i in range(1, len(self.frames)):
            prev = self.frames[i - 1]
            curr = self.frames[i]
            if prev.amps is not None and curr.amps is not None:
                if prev.amps == 0:
                    if curr.amps != 0:
                        raise ValueError(
                            "Amps jumped from 0 to non-zero between frames"
                        )
                else:
                    change_ratio = abs(curr.amps - prev.amps) / abs(prev.amps)
                    if change_ratio > 0.20:
                        raise ValueError(
                            "Amps jump exceeded 20% between consecutive frames"
                        )
            if prev.volts is not None and curr.volts is not None:
                if prev.volts == 0:
                    if curr.volts != 0:
                        raise ValueError(
                            "Volts jumped from 0 to non-zero between frames"
                        )
                else:
                    change_ratio = abs(curr.volts - prev.volts) / abs(prev.volts)
                    if change_ratio > 0.10:
                        raise ValueError(
                            "Volts jump exceeded 10% between consecutive frames"
                        )
        return self
