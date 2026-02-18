"""
SQLAlchemy model for session narrative cache.
Stores AI-generated narrative text keyed by session_id.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from database.base import Base


class SessionNarrative(Base):
    """Cached AI narrative for a welding session."""

    __tablename__ = "session_narratives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(64),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    narrative_text = Column(Text, nullable=False)
    score_snapshot = Column(Float, nullable=True)
    model_version = Column(String(64), nullable=False, default="claude-sonnet-4-6")
    generated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
