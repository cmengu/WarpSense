#!/usr/bin/env python3
"""Prototype: validate migration 005 SQL. Run from backend/ with DATABASE_URL set."""
# Uses PostgreSQL - 001 has postgresql.JSONB so SQLite would fail for full chain
import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent
sys.path.insert(0, str(backend))

# Need Postgres - skip if not available
db_url = os.getenv("DATABASE_URL", "")
if "sqlite" in db_url:
    print("SKIP: Migration 001 uses postgresql.JSONB; use PostgreSQL for full chain")
    sys.exit(0)

from alembic import command
from alembic.config import Config

cfg = Config(str(backend / "alembic.ini"))
cfg.set_main_option("script_location", str(backend / "alembic"))

# Down to 004, then up to 005
command.downgrade(cfg, "004")
command.upgrade(cfg, "005")
print("UPGRADE 005: OK")
command.downgrade(cfg, "004")
print("DOWNGRADE 004: OK")
