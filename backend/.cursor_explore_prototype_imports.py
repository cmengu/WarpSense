#!/usr/bin/env python3
"""Prototype: validate models/site.py + database.models import chain and create_all."""
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent
sys.path.insert(0, str(backend))

# Simulate what tests do: Base.metadata.create_all
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from database.base import Base
# Must import models that define tables - database.models has SessionModel, FrameModel, WeldThresholdModel
# Task: add Site, Team in models/site.py; SessionModel.team_id in database.models
# For create_all to create sites/teams, we need Site/Team imported.
# Option: database.models imports "from models.site import Site, Team" 
# Prototype: create models/site.py and add team_id to SessionModel, then import chain

# Step 1: Can we define Site/Team in models/site.py with from database.base import Base?
# (We don't actually create the file - we inline it to test)
from database.base import Base as _Base
from sqlalchemy import Column, String, DateTime, ForeignKey, func

class _Site(_Base):
    __tablename__ = "sites"
    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    location = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class _Team(_Base):
    __tablename__ = "teams"
    id = Column(String(64), primary_key=True)
    site_id = Column(String(64), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# Now import database.models - which has SessionModel. If we add team_id there,
# we need teams table to exist for FK. SQLite may allow deferred FK check.
from database.models import SessionModel, FrameModel, WeldThresholdModel

# Create engine and create_all - do we have sites, teams?
engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)

# Verify tables
from sqlalchemy import inspect
insp = inspect(engine)
tables = insp.get_table_names()
assert "sites" in tables, f"Missing sites: {tables}"
assert "teams" in tables, f"Missing teams: {tables}"
assert "sessions" in tables, f"Missing sessions: {tables}"

# Sessions: does it have team_id? (We haven't added it in prototype - just checking sites/teams register)
cols = [c["name"] for c in insp.get_columns("sessions")]
print(f"Sessions columns: {cols}")
print("create_all with Site/Team + Base: OK")
