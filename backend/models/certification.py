"""
SQLAlchemy models for certification standards and welder certification tracking.
Used for operator credentialing evaluation against cert standards.
"""
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)

from database.base import Base


class CertStandard(Base):
    """
    Certification standard definition (e.g. AWS D1.1, ISO 9606).
    Defines required score and session count for certification.
    """

    __tablename__ = "cert_standards"

    id = Column(String(32), primary_key=True)
    name = Column(String(256), nullable=False)
    required_score = Column(Float, nullable=False)
    sessions_required = Column(Integer, nullable=False)
    weld_type = Column(String(32), nullable=True)


class WelderCertification(Base):
    """
    Per-welder, per-standard certification status.
    One row per (welder_id, cert_standard_id); updated by cert_service.
    """

    __tablename__ = "welder_certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    welder_id = Column(String(128), nullable=False)
    cert_standard_id = Column(
        String(32), ForeignKey("cert_standards.id"), nullable=False
    )
    status = Column(String(32), nullable=False, default="not_started")
    evaluated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    qualifying_session_ids = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("welder_id", "cert_standard_id", name="uq_welder_cert"),
    )
