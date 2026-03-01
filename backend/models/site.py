"""
SQLAlchemy models for Site and Team.
Sessions reference Team via nullable team_id FK.
models.site MUST import only database.base — NEVER database.models.
"""

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from database.base import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    location = Column(String(256), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    teams = relationship("Team", back_populates="site", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String(64), primary_key=True)
    site_id = Column(
        String(64), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(256), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    site = relationship("Site", back_populates="teams")
