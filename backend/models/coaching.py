"""
SQLAlchemy models for coaching drills and assignments.
Drills target specific weld metrics; assignments track welder progress.
"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from database.base import Base


class Drill(Base):
    """A coaching drill targeting a specific weld metric."""

    __tablename__ = "drills"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_metric = Column(String(64), nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    sessions_required = Column(Integer, nullable=False, default=3)
    success_threshold = Column(Float, nullable=False, default=70.0)


class CoachingAssignment(Base):
    """Assignment of a drill to a welder. Tracks sessions completed and completion status."""

    __tablename__ = "coaching_assignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    welder_id = Column(String(128), nullable=False)
    drill_id = Column(Integer, ForeignKey("drills.id"), nullable=False)
    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status = Column(String(32), nullable=False, default="active")
    sessions_completed = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
