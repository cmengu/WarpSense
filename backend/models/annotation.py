"""
SQLAlchemy model for session annotations.
Stores defect/near-miss/technique annotations keyed by session and timestamp.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func

from database.base import Base


class SessionAnnotation(Base):
    """Annotation on a welding session (defect, near miss, technique error, equipment issue)."""

    __tablename__ = "session_annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(64),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp_ms = Column(BigInteger, nullable=False)
    annotation_type = Column(String(32), nullable=False)
    note = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
