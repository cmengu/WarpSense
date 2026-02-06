"""
This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
SQLAlchemy ORM models for canonical time-series sessions.
This file defines SQLAlchemy ORM models, which are Python classes that map to database tables.
This is separate from Pydantic — Pydantic is for validation in Python, SQLAlchemy is for storing/querying in a database.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from .base import Base
from models.frame import Frame
from models.session import Session, SessionStatus


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    operator_id = Column(String, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    weld_type = Column(String, nullable=False, index=True)

    thermal_sample_interval_ms = Column(Integer, nullable=False)
    thermal_directions = Column(JSON, nullable=False)
    thermal_distance_interval_mm = Column(Float, nullable=False)
    sensor_sample_rate_hz = Column(Integer, nullable=False)

    status = Column(String, nullable=False, default=SessionStatus.RECORDING.value)
    frame_count = Column(Integer, nullable=False)
    expected_frame_count = Column(Integer, nullable=True)
    last_successful_frame_index = Column(Integer, nullable=True)
    validation_errors = Column(JSON, nullable=False, default=list)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    disable_sensor_continuity_checks = Column(Boolean, nullable=False, default=False)

    locked_until = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)

    frames = relationship(
        "FrameModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="FrameModel.timestamp_ms",
    )

    @staticmethod
    def _frames_to_models(frames: List[Frame]) -> List["FrameModel"]:
        return [FrameModel.from_pydantic(frame) for frame in frames]

    @staticmethod
    def _frames_from_models(frames: List["FrameModel"]) -> List[Frame]:
        return [frame.to_pydantic() for frame in frames]

    @classmethod
    def from_pydantic(cls, session: Session) -> "SessionModel":
        model = cls(
            session_id=session.session_id,
            operator_id=session.operator_id,
            start_time=session.start_time,
            weld_type=session.weld_type,
            thermal_sample_interval_ms=session.thermal_sample_interval_ms,
            thermal_directions=session.thermal_directions,
            thermal_distance_interval_mm=session.thermal_distance_interval_mm,
            sensor_sample_rate_hz=session.sensor_sample_rate_hz,
            status=session.status.value,
            frame_count=session.frame_count,
            expected_frame_count=session.expected_frame_count,
            last_successful_frame_index=session.last_successful_frame_index,
            validation_errors=session.validation_errors,
            completed_at=session.completed_at,
            disable_sensor_continuity_checks=session.disable_sensor_continuity_checks,
            version=1,
        )
        model.frames = cls._frames_to_models(session.frames)
        for frame in model.frames:
            frame.session_id = model.session_id
        return model

    def to_pydantic(self) -> Session:
        frames = self._frames_from_models(self.frames or [])
        return Session(
            session_id=self.session_id,
            operator_id=self.operator_id,
            start_time=self.start_time,
            weld_type=self.weld_type,
            thermal_sample_interval_ms=self.thermal_sample_interval_ms,
            thermal_directions=self.thermal_directions,
            thermal_distance_interval_mm=self.thermal_distance_interval_mm,
            sensor_sample_rate_hz=self.sensor_sample_rate_hz,
            frames=frames,
            status=SessionStatus(self.status),
            frame_count=self.frame_count,
            expected_frame_count=self.expected_frame_count,
            last_successful_frame_index=self.last_successful_frame_index,
            validation_errors=self.validation_errors or [],
            completed_at=self.completed_at,
            disable_sensor_continuity_checks=self.disable_sensor_continuity_checks,
        )


class FrameModel(Base):
    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    timestamp_ms = Column(Integer, nullable=False)
    frame_data = Column(JSON, nullable=False)

    session = relationship("SessionModel", back_populates="frames")

    @classmethod
    def from_pydantic(cls, frame: Frame) -> "FrameModel":
        return cls(
            timestamp_ms=frame.timestamp_ms,
            frame_data=frame.model_dump(),
        )

    def to_pydantic(self) -> Frame:
        return Frame(**self.frame_data)
