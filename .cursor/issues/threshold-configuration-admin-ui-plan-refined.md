# Threshold Configuration Admin UI — Implementation Plan

## Phase Breakdown

---

## Phase 1 — Data Model & Backend Foundation

**Goal:** `weld_thresholds` table exists with seed data; `process_type` column on sessions; `GET/PUT` thresholds API works; cache in place.

**Risk:** Low

**Estimate:** 6.5h (includes Step 1.8 backfill update, Step 1.9 prototype scripts)

---

## Phase 2 — Wire Thresholds into Scoring

**Goal:** `extract_features` and `score_session` use thresholds from DB for session's `process_type`; score API returns `active_threshold_spec`; no DB hit per score.

**Risk:** Medium

**Estimate:** 5h

---

## Phase 3 — Admin UI & Types

**Goal:** Admin can open `/admin/thresholds`, switch tabs, edit values, save; inline arc diagram shows target angle; validation errors display.

**Risk:** Low

**Estimate:** 6h

---

## Phase 4 — Micro-Feedback & Report Callouts

**Goal:** Replay and WelderReport use configured thresholds; micro-feedback respects them; WelderReport shows "Evaluated against MIG spec — Target 45° ±5°".

**Risk:** Medium

**Estimate:** 5.5h

---

## Steps

---

### Phase 1 — Data Model & Backend Foundation

**Step 1.1 — Add Pydantic WeldTypeThresholds model**

*What:* Define `WeldTypeThresholds` and `WeldThresholdUpdate` Pydantic models for API and service use. Use `gt=0` for `angle_target_degrees` to align model validation with PUT rejection of zero.

*File:* `backend/models/thresholds.py` (create)

*Depends on:* none

*Code:*
```python
"""
Pydantic models for weld quality thresholds.
One row per process type (mig, tig, stick, flux_core).
"""

from pydantic import BaseModel, Field


class WeldTypeThresholds(BaseModel):
    """Thresholds for one process type. Pass = actual <= threshold."""

    weld_type: str = Field(..., description="Process type: mig|tig|stick|flux_core")
    angle_target_degrees: float = Field(..., gt=0, le=90, description="Must be > 0; 0 makes scoring useless")
    angle_warning_margin: float = Field(..., ge=0, le=45)
    angle_critical_margin: float = Field(..., ge=0, le=45)
    thermal_symmetry_warning_celsius: float = Field(..., ge=0, le=200)
    thermal_symmetry_critical_celsius: float = Field(..., ge=0, le=200)
    amps_stability_warning: float = Field(..., ge=0)
    volts_stability_warning: float = Field(..., ge=0)
    heat_diss_consistency: float = Field(..., ge=0)


class WeldThresholdUpdate(BaseModel):
    """Request body for PUT /api/thresholds/:weld_type."""

    angle_target_degrees: float = Field(..., gt=0, le=90)
    angle_warning_margin: float = Field(..., ge=0, le=45)
    angle_critical_margin: float = Field(..., ge=0, le=45)
    thermal_symmetry_warning_celsius: float = Field(..., ge=0, le=200)
    thermal_symmetry_critical_celsius: float = Field(..., ge=0, le=200)
    amps_stability_warning: float = Field(..., ge=0)
    volts_stability_warning: float = Field(..., ge=0)
    heat_diss_consistency: float = Field(..., ge=0)
```

*Why this approach:* `gt=0` ensures programmatic creation of `WeldTypeThresholds(angle_target_degrees=0, ...)` fails at model level, matching PUT validation. Prevents scripts or tests passing 0 into extract_features/score_session.

*Verification:*
```
Setup: Backend venv active
Action: cd backend && python -c "from models.thresholds import WeldTypeThresholds, WeldThresholdUpdate; t = WeldTypeThresholds(weld_type='mig', angle_target_degrees=45, angle_warning_margin=5, angle_critical_margin=15, thermal_symmetry_warning_celsius=20, thermal_symmetry_critical_celsius=40, amps_stability_warning=5, volts_stability_warning=1, heat_diss_consistency=40); print(t.weld_type)"
Expected: mig
Action: python -c "WeldTypeThresholds(weld_type='mig', angle_target_degrees=0, angle_warning_margin=5, angle_critical_margin=15, thermal_symmetry_warning_celsius=20, thermal_symmetry_critical_celsius=40, amps_stability_warning=5, volts_stability_warning=1, heat_diss_consistency=40)"
Expected: ValidationError (angle_target_degrees must be > 0)
Pass criteria:
  [ ] Pydantic import succeeds
  [ ] WeldTypeThresholds instantiation succeeds with angle_target_degrees=45
  [ ] angle_target_degrees=0 raises ValidationError
  [ ] Field validation rejects negative values
If it fails: Check Python path includes backend root
```

*Estimate:* 0.5h

*Classification:* NON-CRITICAL

---

**Step 1.2 — Add SQLAlchemy WeldThresholdModel and migration**

*What:* Create `weld_thresholds` table and `process_type` column on sessions; seed 4 rows; backfill `process_type='mig'` for existing sessions.

*File:* `backend/database/models.py` (modify), `backend/alembic/versions/004_weld_thresholds_and_process_type.py` (create)

*Depends on:* Step 1.1

*Code:*
```python
# In database/models.py — add after FrameModel class:

class WeldThresholdModel(Base):
    __tablename__ = "weld_thresholds"

    weld_type = Column(String, primary_key=True, index=True)
    angle_target_degrees = Column(Float, nullable=False)
    angle_warning_margin = Column(Float, nullable=False)
    angle_critical_margin = Column(Float, nullable=False)
    thermal_symmetry_warning_celsius = Column(Float, nullable=False)
    thermal_symmetry_critical_celsius = Column(Float, nullable=False)
    amps_stability_warning = Column(Float, nullable=False)
    volts_stability_warning = Column(Float, nullable=False)
    heat_diss_consistency = Column(Float, nullable=False)
```

Migration file:
```python
"""Add weld_thresholds table and process_type to sessions.

Revision ID: 004_weld_thresholds_process_type
Revises: 003_add_score_total
Create Date: 2025-02-18

"""

from alembic import op
import sqlalchemy as sa


revision = "004_weld_thresholds_process_type"
down_revision = "003_add_score_total"
branch_labels = None
depends_on = None

SEED_DATA = [
    ("mig", 45, 5, 15, 60, 80, 5, 1, 40),
    ("tig", 75, 10, 20, 60, 80, 5, 1, 40),
    ("stick", 20, 8, 20, 60, 80, 5, 1, 40),
    ("flux_core", 45, 7, 18, 60, 80, 5, 1, 40),
]


def upgrade() -> None:
    # Add process_type to sessions
    op.add_column(
        "sessions",
        sa.Column("process_type", sa.String(), nullable=True),
    )
    # Backfill process_type: single UPDATE for typical DBs; for 100k+ rows use batched variant
    op.execute(
        sa.text("UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL")
    )
    op.alter_column(
        "sessions",
        "process_type",
        nullable=False,
        server_default="mig",
    )
    op.create_index("idx_sessions_process_type", "sessions", ["process_type"])

    # Create weld_thresholds
    op.create_table(
        "weld_thresholds",
        sa.Column("weld_type", sa.String(), primary_key=True),
        sa.Column("angle_target_degrees", sa.Float(), nullable=False),
        sa.Column("angle_warning_margin", sa.Float(), nullable=False),
        sa.Column("angle_critical_margin", sa.Float(), nullable=False),
        sa.Column("thermal_symmetry_warning_celsius", sa.Float(), nullable=False),
        sa.Column("thermal_symmetry_critical_celsius", sa.Float(), nullable=False),
        sa.Column("amps_stability_warning", sa.Float(), nullable=False),
        sa.Column("volts_stability_warning", sa.Float(), nullable=False),
        sa.Column("heat_diss_consistency", sa.Float(), nullable=False),
    )
    for row in SEED_DATA:
        op.execute(
            sa.text(
                "INSERT INTO weld_thresholds (weld_type, angle_target_degrees, "
                "angle_warning_margin, angle_critical_margin, "
                "thermal_symmetry_warning_celsius, thermal_symmetry_critical_celsius, "
                "amps_stability_warning, volts_stability_warning, heat_diss_consistency) "
                "VALUES (:w, :a, :aw, :ac, :tw, :tc, :amps, :volts, :hd)"
            ).bindparams(
                w=row[0], a=row[1], aw=row[2], ac=row[3],
                tw=row[4], tc=row[5], amps=row[6], volts=row[7], hd=row[8],
            )
        )


def downgrade() -> None:
    op.drop_table("weld_thresholds")
    op.drop_index("idx_sessions_process_type", table_name="sessions")
    op.drop_column("sessions", "process_type")
```

*Pre-migration verification (run before `alembic upgrade head`):*
```bash
# 1. Validate down_revision exists in alembic history
cd backend && alembic history | head -20
# Must show: 003_add_score_total (head) or ... -> 003_add_score_total
grep -l "revision = " alembic/versions/*.py | xargs grep "revision\|down_revision"
# Confirm 003 file has revision = "003_add_score_total"

# 2. Database writable check — fail fast if DATABASE_URL points to read replica
psql $DATABASE_URL -c "CREATE TABLE IF NOT EXISTS _migration_check (id INT); DROP TABLE IF EXISTS _migration_check"
# If fails (e.g. permission denied, read-only): DATABASE_URL may be read replica — use primary DB
# On success: proceed

# 3. Preview SQL: operator inspects what will run before applying
alembic upgrade head --sql > migration_preview.sql
# Review migration_preview.sql; confirm no unexpected DDL

# 4. Large-table guard: if sessions has >1000 rows, run manual UPDATE first
psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions"
# If count > 1000: run manual UPDATE first to avoid partial migration failure:
#   psql $DATABASE_URL -c "UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL"
#   Verify: psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions WHERE process_type IS NULL" → 0
# Then run alembic upgrade head (migration will skip UPDATE or no-op)
# If count <= 1000: proceed with alembic upgrade head directly
```

*Pre-flight script (optional):* Create `backend/scripts/preflight_migration.py`:
```python
"""Run before alembic upgrade head. Exits with code 1 and clear instructions if guard fails."""
import os
import sys
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL")
if not url:
    print("ABORT: DATABASE_URL not set"); sys.exit(1)
engine = create_engine(url)
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS _migration_check (id INT)"))
        conn.execute(text("DROP TABLE IF EXISTS _migration_check"))
        conn.commit()
except Exception as e:
    print(f"ABORT: Database not writable: {e}")
    print("DATABASE_URL may point to read replica — use primary DB"); sys.exit(1)
with engine.connect() as conn:
    r = conn.execute(text("SELECT COUNT(*) FROM sessions"))
    count = r.scalar() if hasattr(r, 'scalar') else r.fetchone()[0]
if count > 1000:
    print("ABORT: sessions table has >1000 rows. Run manual UPDATE first:")
    print("  psql $DATABASE_URL -c \"UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL\"")
    print("  psql $DATABASE_URL -c \"SELECT COUNT(*) FROM sessions WHERE process_type IS NULL\"  # must be 0")
    sys.exit(1)
print("Pre-flight OK")
```

*Post-migration smoke check:*
```bash
# After alembic upgrade head succeeds:

# 1. process_type backfill
psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions WHERE process_type IS NULL"
# Expected: 0 rows. If > 0: migration UPDATE failed; manual backfill required before scoring.

# 2. Verify seed values for all four weld_types (catches SEED_DATA typos)
psql $DATABASE_URL -c "SELECT weld_type, angle_target_degrees FROM weld_thresholds ORDER BY weld_type"
# Expected exactly:
#   flux_core | 45
#   mig       | 45
#   stick     | 20
#   tig       | 75
# If any value differs: fix migration or run manual UPDATE before scoring TIG/stick/flux_core.
psql $DATABASE_URL -c "
  SELECT weld_type, angle_target_degrees FROM weld_thresholds
  WHERE (weld_type = 'tig' AND angle_target_degrees != 75)
     OR (weld_type = 'stick' AND angle_target_degrees != 20)
     OR (weld_type = 'flux_core' AND angle_target_degrees != 45)
     OR (weld_type = 'mig' AND angle_target_degrees != 45);"
# Expected: 0 rows. If any row returned: seed values incorrect — fix before proceeding.
```

*Phase 1 CI checkpoint:* Add to CI (e.g. `.github/workflows/test.yml` or equivalent):
```yaml
# Run migration against SQLite to catch syntax errors; PostgreSQL-specific issues may still occur
- name: Migration dry-run (SQLite)
  run: |
    cd backend
    export DATABASE_URL="sqlite:///./test_migration.db"
    alembic upgrade head
    rm -f test_migration.db
```
Alternatively, run `alembic upgrade head` against ephemeral PostgreSQL if available. Goal: migration is exercised in CI; first production run is not the first run ever.

*Verification:*
```
Setup: PostgreSQL running, DATABASE_URL set (primary, not read replica), alembic at 003
Action: cd backend && alembic upgrade head
Expected: Migration 004 runs without error
Action: psql $DATABASE_URL -c "SELECT weld_type, angle_target_degrees FROM weld_thresholds"
Expected: 4 rows (mig, tig, stick, flux_core)
Action: psql $DATABASE_URL -c "SELECT process_type FROM sessions LIMIT 1"
Expected: mig (or column exists)
Action: psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions WHERE process_type IS NULL"
Expected: 0
Pass criteria:
  [ ] upgrade completes
  [ ] weld_thresholds has 4 rows (mig, tig, stick, flux_core)
  [ ] tig.angle_target_degrees = 75, stick = 20, flux_core = 45, mig = 45
  [ ] sessions.process_type exists, backfilled
  [ ] Zero NULL process_type rows
  [ ] downgrade works (alembic downgrade -1)
If it fails: Check down_revision matches 003; verify DB is writable; verify sessions table
```

*Estimate:* 1h

*Classification:* CRITICAL

---

**Step 1.3 — Add process_type to Session Pydantic model**

*What:* Add optional `process_type` to `Session`; wire `SessionModel` to_pydantic/from_pydantic.

*File:* `backend/models/session.py` (modify), `backend/database/models.py` (modify)

*Depends on:* Step 1.2

*Code:*
```python
# In models/session.py — add to Session class:
process_type: str = Field(default="mig", description="Process type: mig|tig|stick|flux_core")
```

In database/models.py:
- SessionModel: add `process_type = Column(String, nullable=False, default="mig")` (after weld_type)
- from_pydantic: add `process_type=(getattr(session, "process_type", None) or "mig")` — handles process_type=None from old clients
- to_pydantic: add `process_type=(getattr(self, "process_type", None) or "mig")`

*Verification:*
```
Setup: Migration 004 applied
Action: python -c "
from database.models import SessionModel
from models.session import Session
s = Session(operator_id='op1', weld_type='mild_steel', process_type='tig')
m = SessionModel.from_pydantic(s)
p = m.to_pydantic()
assert p.process_type == 'tig', f'expected tig got {p.process_type}'
print('OK: process_type round-trip preserves tig')
"
Expected: OK: process_type round-trip preserves tig
Action: Session with process_type=None — from_pydantic uses default "mig"
Pass criteria:
  [ ] Session model has process_type
  [ ] SessionModel.from_pydantic(session).to_pydantic().process_type == session.process_type
  [ ] Session with process_type=None yields "mig" (not None)
If it fails: Ensure migration added column before model expects it
```

*Estimate:* 0.5h

*Classification:* NON-CRITICAL

---

**Step 1.4 — Create threshold_service with cache**

*What:* Implement `get_thresholds(process_type)` and `get_all_thresholds()` with in-memory cache; `invalidate_cache()` called on PUT. Handle empty table; document multi-worker limitation.

*File:* `backend/services/threshold_service.py` (create)

*Depends on:* Step 1.1, 1.2

*Code:*
```python
"""
Threshold service — cached access to weld_thresholds.
Cache invalidated on PUT; no DB hit per score request.

Threading: _load_lock protects both _load_all and invalidate_cache.
Acquire before read/write of _cache_loaded to avoid races.

LIMITATION: In-memory cache is process-local. Multi-worker deployments
(e.g. Gunicorn with multiple uvicorn workers) will serve stale thresholds
until process restart. For MVP: document and add shared cache (e.g. Redis)
to backlog. Single-worker dev/staging: works correctly.
"""

import threading
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from database.models import WeldThresholdModel
from models.thresholds import WeldTypeThresholds

# Module-level cache: weld_type -> WeldTypeThresholds
_threshold_cache: Dict[str, WeldTypeThresholds] = {}
_cache_loaded = False
_load_lock = threading.Lock()  # Prevents concurrent _load_all race


def _load_all(db: OrmSession) -> None:
    global _threshold_cache, _cache_loaded
    import logging
    log = logging.getLogger(__name__)
    with _load_lock:
        if _cache_loaded:  # Double-check after acquiring lock
            return
        rows = db.execute(select(WeldThresholdModel)).scalars().all()
        if rows:
            _threshold_cache = {}
            for r in rows:
                try:
                    t = WeldTypeThresholds(
                        weld_type=r.weld_type,
                        angle_target_degrees=r.angle_target_degrees,
                        angle_warning_margin=r.angle_warning_margin,
                        angle_critical_margin=r.angle_critical_margin,
                        thermal_symmetry_warning_celsius=r.thermal_symmetry_warning_celsius,
                        thermal_symmetry_critical_celsius=r.thermal_symmetry_critical_celsius,
                        amps_stability_warning=r.amps_stability_warning,
                        volts_stability_warning=r.volts_stability_warning,
                        heat_diss_consistency=r.heat_diss_consistency,
                    )
                    _threshold_cache[r.weld_type] = t
                except Exception as e:
                    log.warning("Skipping corrupt weld_thresholds row weld_type=%r: %s", r.weld_type, e)
            if not _threshold_cache:
                _threshold_cache = {
                    "mig": WeldTypeThresholds(
                        weld_type="mig",
                        angle_target_degrees=45,
                        angle_warning_margin=5,
                        angle_critical_margin=15,
                        thermal_symmetry_warning_celsius=60,
                        thermal_symmetry_critical_celsius=80,
                        amps_stability_warning=5,
                        volts_stability_warning=1,
                        heat_diss_consistency=40,
                    )
                }
        else:
            _threshold_cache = {
                "mig": WeldTypeThresholds(
                    weld_type="mig",
                    angle_target_degrees=45,
                    angle_warning_margin=5,
                    angle_critical_margin=15,
                    thermal_symmetry_warning_celsius=60,
                    thermal_symmetry_critical_celsius=80,
                    amps_stability_warning=5,
                    volts_stability_warning=1,
                    heat_diss_consistency=40,
                )
            }
        _cache_loaded = True


def invalidate_cache() -> None:
    """Invalidate cache so next request refetches. Threading: acquire _load_lock
    before writing _cache_loaded to avoid race with _load_all (concurrent PUT +
    GET score could interleave otherwise)."""
    global _cache_loaded
    with _load_lock:
        _cache_loaded = False


KNOWN_PROCESS_TYPES = frozenset({"mig", "tig", "stick", "flux_core"})


def get_thresholds(db: OrmSession, process_type: str) -> WeldTypeThresholds:
    """Get thresholds for a process type. For known types (mig/tig/stick/flux_core),
    fails loudly if row missing; for unknown types, falls back to mig."""
    global _cache_loaded
    if not _cache_loaded:
        _load_all(db)
    key = (process_type or "mig").lower().strip()
    if key not in _threshold_cache:
        if key in KNOWN_PROCESS_TYPES:
            import logging
            logging.getLogger(__name__).error(
                "weld_thresholds missing row for process_type=%r; scoring will use MIG. "
                "Add row or run migration seed.", key
            )
            raise ValueError(f"Thresholds for {key!r} not found in weld_thresholds. Add row or fix DB.")
        key = "mig"
    return _threshold_cache.get(key, _threshold_cache["mig"])


def get_all_thresholds(db: OrmSession) -> List[WeldTypeThresholds]:
    """Return all thresholds. Admin UI uses this for GET /api/thresholds."""
    global _cache_loaded
    if not _cache_loaded:
        _load_all(db)
    return list(_threshold_cache.values())
```

*Verification:*
```
Setup: DB with seeded thresholds, backend running
Action: In Python shell: from database.connection import SessionLocal; from services.threshold_service import get_thresholds; db = SessionLocal(); t = get_thresholds(db, "mig"); print(t.angle_target_degrees)
Expected: 45
Action: t = get_thresholds(db, "tig"); print(t.angle_target_degrees)
Expected: 75 (TIG-specific; NOT mig fallback)
Action: t = get_thresholds(db, "unknown")
Expected: Returns MIG thresholds (fallback for unknown type)
Action: Simulate empty table — truncate weld_thresholds; t = get_thresholds(db, "mig")
Expected: Returns WeldTypeThresholds (45, 5, 15, ...) — no KeyError
Action: Simulate missing tig row — DELETE FROM weld_thresholds WHERE weld_type='tig'; get_thresholds(db, 'tig')
Expected: ValueError or similar — must NOT silently return MIG thresholds
Pass criteria:
  [ ] get_thresholds("mig") returns MIG thresholds (angle_target=45)
  [ ] get_thresholds("tig") returns TIG thresholds (angle_target=75) when tig row exists
  [ ] get_thresholds("unknown") falls back to mig
  [ ] get_thresholds("tig") raises when tig row missing (no silent MIG fallback for known type)
  [ ] Empty table: get_thresholds("mig") does not raise
If it fails: Check WeldThresholdModel column names match
```

*Estimate:* 1h

*Classification:* CRITICAL

---

**Step 1.5 — Create thresholds API routes**

*What:* Add `GET /api/thresholds` and `PUT /api/thresholds/:weld_type`; validate angle_warning <= angle_critical; invalidate cache on PUT (after commit, in finally); return single updated threshold.

*File:* `backend/routes/thresholds.py` (create)

*Depends on:* Step 1.4

*Code:*
```python
"""
Thresholds API — GET all, PUT one.
"""

from fastapi import APIRouter, Depends, HTTPException

from database.connection import SessionLocal
from database.models import WeldThresholdModel
from models.thresholds import WeldTypeThresholds, WeldThresholdUpdate
from services.threshold_service import invalidate_cache, get_all_thresholds, get_thresholds

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/thresholds")
async def list_thresholds(db=Depends(get_db)):
    """Return all thresholds. Admin uses this to populate forms."""
    items = get_all_thresholds(db)
    return [t.model_dump() for t in items]


@router.put("/thresholds/{weld_type}")
async def update_threshold(
    weld_type: str,
    body: WeldThresholdUpdate,
    db=Depends(get_db),
):
    """Update thresholds for one process type. Invalidates cache."""
    weld_type = weld_type.lower()
    if weld_type not in ("mig", "tig", "stick", "flux_core"):
        raise HTTPException(status_code=422, detail=f"Unknown weld_type: {weld_type}")
    if body.angle_target_degrees == 0:
        raise HTTPException(
            status_code=422,
            detail="angle_target_degrees must be > 0",
        )
    if body.angle_warning_margin > body.angle_critical_margin:
        raise HTTPException(
            status_code=422,
            detail="angle_warning_margin must be <= angle_critical_margin",
        )
    if body.thermal_symmetry_warning_celsius > body.thermal_symmetry_critical_celsius:
        raise HTTPException(
            status_code=422,
            detail="thermal_symmetry_warning must be <= thermal_symmetry_critical",
        )
    row = db.query(WeldThresholdModel).filter_by(weld_type=weld_type).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Thresholds for {weld_type} not found")
    row.angle_target_degrees = body.angle_target_degrees
    row.angle_warning_margin = body.angle_warning_margin
    row.angle_critical_margin = body.angle_critical_margin
    row.thermal_symmetry_warning_celsius = body.thermal_symmetry_warning_celsius
    row.thermal_symmetry_critical_celsius = body.thermal_symmetry_critical_celsius
    row.amps_stability_warning = body.amps_stability_warning
    row.volts_stability_warning = body.volts_stability_warning
    row.heat_diss_consistency = body.heat_diss_consistency
    try:
        db.commit()
    finally:
        invalidate_cache()
    updated = WeldTypeThresholds(
        weld_type=row.weld_type,
        angle_target_degrees=row.angle_target_degrees,
        angle_warning_margin=row.angle_warning_margin,
        angle_critical_margin=row.angle_critical_margin,
        thermal_symmetry_warning_celsius=row.thermal_symmetry_warning_celsius,
        thermal_symmetry_critical_celsius=row.thermal_symmetry_critical_celsius,
        amps_stability_warning=row.amps_stability_warning,
        volts_stability_warning=row.volts_stability_warning,
        heat_diss_consistency=row.heat_diss_consistency,
    )
    return updated.model_dump()
```

*Verification:*
```
Setup: Backend running, migration applied
Action: curl -X PUT http://localhost:8000/api/thresholds/mig -H "Content-Type: application/json" -d '{"angle_target_degrees":0,"angle_warning_margin":5,"angle_critical_margin":15,"thermal_symmetry_warning_celsius":20,"thermal_symmetry_critical_celsius":40,"amps_stability_warning":5,"volts_stability_warning":1,"heat_diss_consistency":40}'
Expected: 422, detail "angle_target_degrees must be > 0"
Action: curl -s http://localhost:8000/api/thresholds
Expected: JSON array of 4 objects
Action: curl -X PUT ... -d '{"angle_warning_margin":20,"angle_critical_margin":10,...}' (warning > critical)
Expected: 422
Pass criteria:
  [ ] GET returns 4 items
  [ ] PUT with valid body succeeds, returns single object
  [ ] PUT with warning > critical returns 422
If it fails: Check router prefix in main.py
```

*Estimate:* 1h

*Classification:* CRITICAL

---

**Step 1.6 — Register thresholds router in main.py**

*What:* Include thresholds router under `/api` prefix.

*File:* `backend/main.py` (modify)

*Depends on:* Step 1.5

*Code:*
```python
from routes.thresholds import router as thresholds_router
# ...
app.include_router(thresholds_router, prefix="/api")
```

*Verification:*
```
Setup: Backend running
Action: curl -s http://localhost:8000/api/thresholds
Expected: 200, array of threshold objects
If it fails: Router not registered; check import and include_router
```

*Estimate:* 0.25h

*Classification:* NON-CRITICAL

---

**Step 1.7 — Add process_type to create_session and session payload**

*What:* Accept optional `process_type` in `CreateSessionRequest`; validate that `process_type` is in `(mig, tig, stick, flux_core)`; reject invalid values with 422; include `process_type` in `get_session` response; default `mig`.

*File:* `backend/routes/sessions.py` (modify)

*Depends on:* Step 1.2, 1.3

*Code:*
```python
# CreateSessionRequest: add process_type: Optional[str] = None

VALID_PROCESS_TYPES = frozenset({"mig", "tig", "stick", "flux_core"})

# In create_session, before SessionModel(...):
process_type = (body.process_type or "mig").lower().strip()
if process_type not in VALID_PROCESS_TYPES:
    raise HTTPException(
        status_code=422,
        detail=f"process_type must be one of: mig, tig, stick, flux_core (got: {body.process_type!r})",
    )

# SessionModel(... process_type=process_type ...) — add to model init
# session_payload: add "process_type": session_model.process_type or "mig"
```

*Why this approach:* Prevents typos (e.g. `t1g`, `submerged_arc`) from being stored. Invalid sessions would otherwise be scored with MIG thresholds; WelderReport would show wrong spec.

*Verification:*
```
Setup: Backend running
Action: POST /api/sessions with {"operator_id":"op1","weld_type":"mild_steel","process_type":"tig"}
Expected: 201, session created
Action: POST /api/sessions with {"operator_id":"op1","weld_type":"mild_steel","process_type":"t1g"}
Expected: 422, detail includes "process_type must be one of: mig, tig, stick, flux_core"
Action: POST /api/sessions with {"operator_id":"op1","weld_type":"mild_steel","process_type":"submerged_arc"}
Expected: 422
Action: GET /api/sessions/{id}
Expected: JSON includes "process_type": "tig" for first session (e.g. {"id":"...","process_type":"tig",...})
Pass criteria:
  [ ] POST accepts valid process_type (mig, tig, stick, flux_core)
  [ ] POST rejects invalid process_type with 422
  [ ] Omitted process_type defaults to mig
  [ ] GET returns process_type
If it fails: Ensure validation runs before SessionModel creation
```

*Estimate:* 0.5h

*Classification:* CRITICAL (prevents silent wrong scoring from typos/invalid types)

---

**Step 1.8 — Update backfill_score_total.py to use thresholds**

*What:* backfill_score_total.py currently uses `extract_features(session)` (default angle_target=45) and `score_session(session, features)` (thresholds=None). Update backfill to load thresholds per session's process_type.

*File:* `backend/scripts/backfill_score_total.py` (modify)

*Depends on:* Step 1.4, 1.7

*Code:*
```python
from services.threshold_service import get_thresholds

# Inside the batch loop, for each session s:
session = s.to_pydantic()
process_type = (getattr(session, "process_type", None) or "mig").lower()
thresholds = get_thresholds(db, process_type)
features = extract_features(session, angle_target_deg=thresholds.angle_target_degrees)
score = score_session(session, features, thresholds)
```

*Verification:*
```
Setup: Session with process_type='tig', score_total=NULL, frames present
Action: Run backfill_score_total.py
Expected: Session scored with TIG thresholds (angle_target=75, etc.), not MIG
Pass criteria:
  [ ] TIG session gets score using angle_target 75
  [ ] MIG session gets score using angle_target 45
  [ ] No regression for process_type=None (defaults to mig)
If it fails: Check get_thresholds returns correct weld_type
```

*Estimate:* 0.25h

*Classification:* CRITICAL

---

**Step 1.9 — Update prototype scripts or document limitation**

*What:* `prototype_arc_scoring.py` and `prototype_aggregate_perf.py` call `extract_features(session)` and `score_session(session, features)` with no thresholds. If run with TIG/stick/flux_core sessions in DB, output uses MIG constants. Update scripts to use thresholds from DB, or document in Known Issues.

*File:* `backend/scripts/prototype_arc_scoring.py` (modify), `backend/scripts/prototype_aggregate_perf.py` (modify)

*Depends on:* Step 1.4

*Implementation (preferred):* Add threshold loading to both scripts:

```python
# prototype_arc_scoring.py — in make_session_for_arc, add process_type="mig" to Session
# In main(), before extract_features/score_session:
from database.connection import SessionLocal
from services.threshold_service import get_thresholds

db = SessionLocal()
try:
    for arc, ... in targets:
        s0 = make_session_for_arc(arc, 0, f"sess_{arc}_001")
        # Add process_type if Session supports it
        pt = getattr(s0, "process_type", None) or "mig"
        thresholds = get_thresholds(db, pt)
        f0 = extract_features(s0, angle_target_deg=thresholds.angle_target_degrees)
        sc0 = score_session(s0, f0, thresholds)
        # ... same for s4
finally:
    db.close()
```

```python
# prototype_aggregate_perf.py — in batch_score_sessions:
from services.threshold_service import get_thresholds

session = session_model.to_pydantic()
process_type = (getattr(session, "process_type", None) or "mig").lower()
thresholds = get_thresholds(db, process_type)
features = extract_features(session, angle_target_deg=thresholds.angle_target_degrees)
score = score_session(session, features, thresholds)
```

*Alternative (document only):* Add to Known Issues: "prototype_arc_scoring.py and prototype_aggregate_perf.py use legacy scoring without thresholds; will score all sessions with MIG constants. Update or run only with MIG sessions."

*Verification:*
```
Setup: DB with weld_thresholds seeded; Session with process_type='tig'
Action: Run prototype_aggregate_perf.py (or prototype_arc_scoring.py with DB sessions)
Expected: TIG sessions scored with TIG thresholds if scripts updated; or Known Issues documents limitation
Pass criteria:
  [ ] Scripts use get_thresholds when scoring, OR
  [ ] Known Issues explicitly documents prototype script limitation
If it fails: Ensure SessionModel has process_type; weld_thresholds seeded
```

*Estimate:* 0.25h

*Classification:* P1 (prevents wrong output when running dev scripts with non-MIG data)

---

### Phase 2 — Wire Thresholds into Scoring

**Order:** 2.1 → 2.2 → 2.3. Step 2.3 requires both extract_features (2.1) and score_session (2.2) to accept new params.

**Step 2.1 — Add angle_target_deg param to extract_features**

*What:* Add `angle_target_deg: float = 45` to `extract_features`; use it in `angle_max_deviation` calculation.

*File:* `backend/features/extractor.py` (modify)

*Depends on:* none

*Code:*
```python
def extract_features(session: Session, angle_target_deg: float = 45) -> Dict[str, Any]:
    # ...
    angle_max_deviation = (
        max(abs(a - angle_target_deg) for a in angles) if angles else 0.0
    )
```

*Verification:*
```
Setup: Backend tests or manual call
Action: extract_features(session, angle_target_deg=75) with angles [70, 80]
Expected: angle_max_deviation = 5 (deviation from 75)
Pass criteria:
  [ ] Default 45 yields same result as before
  [ ] 75 yields deviation from 75
If it fails: Check angles list handling for empty
```

*Estimate:* 0.25h

*Classification:* NON-CRITICAL

---

**Step 2.2 — Refactor score_session to accept thresholds**

*What:* Change `score_session(session, features)` to `score_session(session, features, thresholds: WeldTypeThresholds)`. Use thresholds for all 5 rules; keep fallback to module constants if thresholds is None for tests.

*File:* `backend/scoring/rule_based.py` (modify)

*Depends on:* Step 1.1

*Code:*
```python
# Full implementation — same as current plan
from typing import Any, Dict, Optional
from models.scoring import ScoreRule, SessionScore
from models.session import Session
from models.thresholds import WeldTypeThresholds

AMPS_STABILITY_THRESHOLD = 5.0
ANGLE_CONSISTENCY_THRESHOLD = 5.0
THERMAL_SYMMETRY_THRESHOLD = 60.0
HEAT_DISS_CONSISTENCY_THRESHOLD = 40.0
VOLTS_STABILITY_THRESHOLD = 1.0


def score_session(
    session: Session,
    features: Dict[str, Any],
    thresholds: Optional[WeldTypeThresholds] = None,
) -> SessionScore:
    t = thresholds
    rules = [
        _check_amps_stability(features, t),
        _check_angle_consistency(features, t),
        _check_thermal_symmetry(features, t),
        _check_heat_diss_consistency(features, t),
        _check_volts_stability(features, t),
    ]
    passed_count = sum(1 for r in rules if r.passed)
    total = passed_count * 20
    return SessionScore(total=total, rules=rules)


def _check_amps_stability(features: Dict[str, Any], t: Optional[WeldTypeThresholds]) -> ScoreRule:
    actual = features.get("amps_stddev", 0.0)
    th = t.amps_stability_warning if t else AMPS_STABILITY_THRESHOLD
    return ScoreRule(rule_id="amps_stability", threshold=th, passed=actual <= th, actual_value=actual)


def _check_angle_consistency(features: Dict[str, Any], t: Optional[WeldTypeThresholds]) -> ScoreRule:
    actual = features.get("angle_max_deviation", 0.0)
    th = t.angle_warning_margin if t else ANGLE_CONSISTENCY_THRESHOLD
    return ScoreRule(rule_id="angle_consistency", threshold=th, passed=actual <= th, actual_value=actual)


def _check_thermal_symmetry(features: Dict[str, Any], t: Optional[WeldTypeThresholds]) -> ScoreRule:
    actual = features.get("north_south_delta_avg", 0.0)
    th = t.thermal_symmetry_warning_celsius if t else THERMAL_SYMMETRY_THRESHOLD
    return ScoreRule(rule_id="thermal_symmetry", threshold=th, passed=actual <= th, actual_value=actual)


def _check_heat_diss_consistency(features: Dict[str, Any], t: Optional[WeldTypeThresholds]) -> ScoreRule:
    actual = features.get("heat_diss_stddev", 0.0)
    th = t.heat_diss_consistency if t else HEAT_DISS_CONSISTENCY_THRESHOLD
    return ScoreRule(rule_id="heat_diss_consistency", threshold=th, passed=actual <= th, actual_value=actual)


def _check_volts_stability(features: Dict[str, Any], t: Optional[WeldTypeThresholds]) -> ScoreRule:
    actual = features.get("volts_range", 0.0)
    th = t.volts_stability_warning if t else VOLTS_STABILITY_THRESHOLD
    return ScoreRule(rule_id="volts_stability", threshold=th, passed=actual <= th, actual_value=actual)
```

*Verification:*
```
Setup: Session with features; thresholds from get_thresholds
Action: score_session(session, features, thresholds)
Expected: SessionScore with rules using threshold values from thresholds
Action: score_session(session, features, None)
Expected: Uses module constants, same as before
Pass criteria:
  [ ] With thresholds: rules use DB values
  [ ] With None: rules use constants
  [ ] Total = passed_count * 20
If it fails: Check t is not None before accessing attributes
```

*Estimate:* 1h

*Classification:* CRITICAL

---

**Step 2.3 — Wire thresholds into get_session_score**

*What:* Load session's process_type; get thresholds; pass angle_target to extract_features and thresholds to score_session; add full active_threshold_spec to response (including thermal, amps, volts, heat_diss for micro-feedback).

*File:* `backend/routes/sessions.py` (modify), `backend/models/scoring.py` (modify)

*Depends on:* Step 1.3, 1.4, 2.1, 2.2

*Code:*
```python
# In get_session_score:
from fastapi import HTTPException
from services.threshold_service import get_thresholds

# Reject sessions with insufficient frames — prevents meaningless all-zero score
# Ensure session loaded with frames (e.g. options(selectinload(SessionModel.frames)))
frames = getattr(session_model, "frames", None) or []
if not frames or len(frames) < 10:
    raise HTTPException(
        status_code=400,
        detail="Session has insufficient frames for scoring (minimum 10 required)",
    )

process_type = getattr(session_model, "process_type", None) or "mig"
thresholds = get_thresholds(db, process_type)
features = extract_features(session, angle_target_deg=thresholds.angle_target_degrees)
score = score_session(session, features, thresholds)
result = score.model_dump()
result["active_threshold_spec"] = {
    "weld_type": thresholds.weld_type,
    "angle_target": thresholds.angle_target_degrees,
    "angle_warning": thresholds.angle_warning_margin,
    "angle_critical": thresholds.angle_critical_margin,
    "thermal_symmetry_warning_celsius": thresholds.thermal_symmetry_warning_celsius,
    "thermal_symmetry_critical_celsius": thresholds.thermal_symmetry_critical_celsius,
    "amps_stability_warning": thresholds.amps_stability_warning,
    "volts_stability_warning": thresholds.volts_stability_warning,
    "heat_diss_consistency": thresholds.heat_diss_consistency,
}
return result
```

*Verification:*
```
Setup: Backend running, session with process_type=tig and 10+ frames
Action: GET /api/sessions/{session_id}/score
Expected: JSON has "total", "rules", "active_threshold_spec" with all 9 fields
Action: GET /api/sessions/{empty_session_id}/score (session with 0–9 frames)
Expected: 400, detail "Session has insufficient frames for scoring (minimum 10 required)"
Pass criteria:
  [ ] active_threshold_spec present with weld_type, angle_target, angle_warning, angle_critical, thermal_symmetry_*, amps_*, volts_*, heat_diss_*
  [ ] weld_type matches session process_type
  [ ] TIG thermal_symmetry_warning_celsius = 60 (from seed)
  [ ] Session with <10 frames returns 400 (not valid-looking all-zero score)
If it fails: Check session_model has process_type; ensure frames relationship loaded
```

*Estimate:* 0.75h

*Classification:* CRITICAL

---

### Phase 3 — Admin UI & Types

**Step 3.1 — Add frontend WeldTypeThresholds type and API functions**

*What:* Define `WeldTypeThresholds` and extended `ActiveThresholdSpec` in types; add `fetchThresholds` and `updateThreshold` to api.ts; extend `SessionScore` with `active_threshold_spec`.

*File:* `my-app/src/types/thresholds.ts` (create), `my-app/src/lib/api.ts` (modify)

*Depends on:* none

*Code:*
```typescript
// types/thresholds.ts
export interface WeldTypeThresholds {
  weld_type: string;
  angle_target_degrees: number;
  angle_warning_margin: number;
  angle_critical_margin: number;
  thermal_symmetry_warning_celsius: number;
  thermal_symmetry_critical_celsius: number;
  amps_stability_warning: number;
  volts_stability_warning: number;
  heat_diss_consistency: number;
}

/** Optional thermal/amps/volts/heat_diss for legacy API callers that return old 4-field spec. */
export interface ActiveThresholdSpec {
  weld_type: string;
  angle_target: number;
  angle_warning: number;
  angle_critical: number;
  thermal_symmetry_warning_celsius?: number;
  thermal_symmetry_critical_celsius?: number;
  amps_stability_warning?: number;
  volts_stability_warning?: number;
  heat_diss_consistency?: number;
}
```

```typescript
// api.ts — extend SessionScore:
export interface SessionScore {
  total: number;
  rules: ScoreRule[];
  active_threshold_spec?: ActiveThresholdSpec;
}

export async function fetchThresholds(): Promise<WeldTypeThresholds[]> { ... }
export async function updateThreshold(weldType: string, body: Partial<WeldTypeThresholds>): Promise<WeldTypeThresholds> { ... }
```

*Verification:*
```
Setup: Backend running, my-app dev server
Action: fetch('http://localhost:8000/api/thresholds').then(r=>r.json()).then(console.log)
Expected: Array of 4 threshold objects
Pass criteria:
  [ ] fetchThresholds returns array
  [ ] updateThreshold sends PUT, returns single object
  [ ] SessionScore type includes active_threshold_spec with optional thermal/amps/volts/heat_diss
If it fails: CORS; check API_BASE_URL
```

*Estimate:* 0.5h

*Classification:* NON-CRITICAL

---

**Step 3.2 — Create AngleArcDiagram component**

*What:* Inline SVG semicircle showing target angle as an arc; ~20 lines; accept angle_target_degrees as prop. Arc spans 0° to angleTargetDegrees (always ≤90 per validation).

*File:* `my-app/src/components/admin/AngleArcDiagram.tsx` (create)

*Depends on:* none

*Code:*
```tsx
'use client';

interface AngleArcDiagramProps {
  angleTargetDegrees: number;
  className?: string;
}

export default function AngleArcDiagram({ angleTargetDegrees, className = '' }: AngleArcDiagramProps) {
  const r = 24;
  const cx = 30;
  const cy = 30;
  const startAngle = 0;
  const endAngle = (angleTargetDegrees / 180) * Math.PI;
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy - r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy - r * Math.sin(endAngle);
  const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z`;
  return (
    <svg width="60" height="40" viewBox="0 0 60 40" className={className} aria-hidden>
      <path d={d} fill="none" stroke="currentColor" strokeWidth="2" />
      <text x="30" y="38" textAnchor="middle" fontSize="10">{angleTargetDegrees}°</text>
    </svg>
  );
}
```

*Verification:*
```
Setup: Next dev server
Action: Render <AngleArcDiagram angleTargetDegrees={45} /> in a test page
Expected: Semicircle arc from 0° to 45°, "45°" label
Action: Unit test — for angleTargetDegrees=45, endAngle in radians = 45 * Math.PI/180 ≈ 0.785;
  arc path d should include A 24 24 0 0 1 with endpoint reflecting ~45° from horizontal.
  Test: (angleTargetDegrees/180)*Math.PI === endAngle used in path; 90 yields Math.PI/2.
Pass criteria:
  [ ] SVG renders
  [ ] Arc spans correct angle (45° arc, not full semicircle when target=45)
  [ ] Numeric: endAngle = (angleTargetDegrees/180)*Math.PI (not angleTargetDegrees*Math.PI)
  [ ] Accessible (aria-hidden for decorative)
If it fails: Check SVG path math; arc direction
```

*Estimate:* 0.5h

*Classification:* NON-CRITICAL

---

**Step 3.3 — Create admin layout**

*What:* Minimal layout for `/admin` route group with nav link to thresholds.

*File:* `my-app/src/app/admin/layout.tsx` (create)

*Depends on:* none

*Code:*
```tsx
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 p-6">
      <nav className="mb-6 flex gap-4">
        <a href="/admin/thresholds" className="text-blue-600 dark:text-blue-400 hover:underline">
          Thresholds
        </a>
        <a href="/" className="text-zinc-600 dark:text-zinc-400 hover:underline">← App</a>
      </nav>
      {children}
    </div>
  );
}
```

*Verification:*
```
Setup: my-app dev server
Action: Navigate to /admin/thresholds
Expected: Layout wraps page; nav links visible
Pass criteria:
  [ ] Layout renders (document.querySelector('nav a[href="/admin/thresholds"]') !== null)
  [ ] Children (thresholds page) render inside
If it fails: Route group structure
```

*Estimate:* 0.25h

*Classification:* NON-CRITICAL

---

**Step 3.4 — Create admin thresholds page with tabs and form**

*What:* Page at `/admin/thresholds` with tabs MIG|TIG|Stick|Flux Core; per-tab form with Angle (target, warning, critical), Thermal, Amps/Volts, Heat Diss; Save button; AngleArcDiagram next to angle inputs; inline validation errors. Disable Save until fetch succeeds and form is fully populated to prevent partial PUT. **On Save click: disable Save and show loading state during PUT; on PUT failure (timeout, 5xx): show error message and re-enable Save so user can retry.**

*File:* `my-app/src/app/admin/thresholds/page.tsx` (create)

*Depends on:* Step 3.1, 3.2, 3.3

*Code:* (Key pattern — same as current plan with parseFloat, isCompleteForm requiring angle_target_degrees > 0, handleSave validation)

```tsx
// State for Save UX
const [saveInProgress, setSaveInProgress] = useState(false);
const [saveError, setSaveError] = useState<string | null>(null);

async function handleSave() {
  if (!isCompleteForm()) return;
  setSaveInProgress(true);
  setSaveError(null);
  try {
    await updateThreshold(activeTab, formState);
    setSaveError(null);
    // Success: optionally show toast
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Save failed";
    setSaveError(msg);
    // Re-enable Save so user can retry
  } finally {
    setSaveInProgress(false);
  }
}

// Save button
<button
  disabled={!isCompleteForm() || saveInProgress || !thresholdsLoaded}
  onClick={handleSave}
  aria-busy={saveInProgress}
>
  {saveInProgress ? "Saving…" : "Save"}
</button>
{saveError && <p data-testid="save-error" className="text-red-600">{saveError}</p>}
```

*Verification:*
```
Setup: Backend running, my-app dev
Action: Open /admin/thresholds; click MIG tab; change angle target to 50; Save
Expected: Form submits; GET /api/thresholds returns mig with 50
Action: Set warning 10, critical 5
Expected: Inline error or backend 422
Action: Block network (DevTools offline); reload page; Save disabled; error shown
Action: Load page, edit, click Save; block /api/thresholds/mig in DevTools and return 500; Save shows "Saving…" then error message; Save re-enabled for retry
Action: Clear angle target field (empty string → parseFloat yields NaN); isCompleteForm must be false; Save disabled
Action: Set angle target to 0; handleSave or backend must reject with error
Pass criteria:
  [ ] Tabs switch
  [ ] Form populated from fetch; Save disabled until loaded
  [ ] Save calls PUT with full body
  [ ] Validation errors display (data-testid="validation-error")
  [ ] Arc diagram visible
  [ ] NaN/invalid numbers (cleared fields) do not pass isCompleteForm — Save stays disabled
  [ ] angle_target_degrees=0 rejected (frontend or backend 422)
  [ ] Failed PUT: Save shows loading then error; button re-enabled; user can retry (data-testid="save-error" visible)
If it fails: Check fetchThresholds/updateThreshold; form state
```

*Estimate:* 2.5h

*Classification:* CRITICAL

---

### Phase 4 — Micro-Feedback & Report Callouts

**Step 4.1 — Add optional thresholds param to generateMicroFeedback**

*What:* Extend `generateMicroFeedback(frames, thresholds?)`; use thresholds when provided (angle + thermal + amps + volts); fallback to current constants when undefined. Add defensive handling: validate frames before processing; on exception in a sub-generator, log error and return partial results (e.g. angle feedback only) rather than swallowing entirely with empty array—unless frames are fundamentally malformed.

*File:* `my-app/src/lib/micro-feedback.ts` (modify)

*Depends on:* Step 3.1

*Code:*
```typescript
import type { WeldTypeThresholds } from "@/types/thresholds";

export function generateMicroFeedback(
  frames: Frame[],
  thresholds?: WeldTypeThresholds | null
): MicroFeedbackItem[] {
  const angleTarget = thresholds?.angle_target_degrees ?? ANGLE_TARGET_DEG;
  const angleWarning = thresholds?.angle_warning_margin ?? ANGLE_WARNING_THRESHOLD_DEG;
  const angleCritical = thresholds?.angle_critical_margin ?? ANGLE_CRITICAL_THRESHOLD_DEG;
  const thermalThresh = thresholds?.thermal_symmetry_warning_celsius ?? THERMAL_VARIANCE_THRESHOLD_CELSIUS;

  if (!Array.isArray(frames) || frames.length === 0) return [];

  let angle: MicroFeedbackItem[] = [];
  let thermal: MicroFeedbackItem[] = [];

  try {
    angle = generateAngleDriftFeedback(frames, angleTarget, angleWarning, angleCritical);
  } catch (err) {
    logWarn("micro-feedback", "Angle feedback generation failed", { error: err });
    // Continue to thermal; do not return empty for angle failure alone
  }

  try {
    thermal = generateThermalSymmetryFeedback(frames, thermalThresh);
  } catch (err) {
    logWarn("micro-feedback", "Thermal feedback generation failed", { error: err });
  }

  try {
    return [...angle, ...thermal].sort((a, b) => a.frameIndex - b.frameIndex);
  } catch (err) {
    logWarn("micro-feedback", "Micro-feedback sort/merge failed", { error: err });
    return [...angle, ...thermal]; // Return unsorted if sort fails
  }
}

function generateAngleDriftFeedback(
  frames: Frame[],
  target: number,
  warning: number,
  critical: number
): MicroFeedbackItem[] {
  const items: MicroFeedbackItem[] = [];
  for (let i = 0; i < frames.length && items.length < CAP_PER_TYPE; i++) {
    const frame = frames[i];
    if (!frame) continue;
    const a = frame.angle_degrees;
    if (a == null || typeof a !== "number" || Number.isNaN(a)) continue;
    const dev = Math.abs(a - target);
    if (dev <= warning) continue;
    const severity: MicroFeedbackSeverity =
      dev >= critical ? "critical" : "warning";
    items.push({
      frameIndex: i,
      severity,
      message: `Torch angle drifted ${dev.toFixed(1)}° at frame ${i} — keep within ±${warning}°`,
      suggestion: "Maintain consistent work angle for uniform penetration.",
      type: "angle",
    });
  }
  return items;
}

function generateThermalSymmetryFeedback(frames: Frame[], thresh: number): MicroFeedbackItem[] {
  // Use thresh instead of THERMAL_VARIANCE_THRESHOLD_CELSIUS; same structure as before
  // ... (existing logic with thresh param)
}
```

*Why this approach:* Catch returns [] on any exception causes user to see no feedback with no indication of error. Per-frame try-catch in generators is heavy; per-generator try-catch allows partial feedback (e.g. angle works, thermal fails due to malformed thermal_snapshots). Logging remains; user gets at least angle feedback when thermal fails.

*Verification:*
```
Setup: Unit test or manual
Action: generateMicroFeedback(frames, { angle_target_degrees: 75, angle_warning_margin: 10, thermal_symmetry_warning_celsius: 60, ... })
Expected: Angle feedback uses 75° target, ±10° warning; thermal uses 60°C
Action: generateMicroFeedback(frames)
Expected: Uses 45, 5, 15, 20 as before
Action: generateMicroFeedback([{ angle_degrees: 50 }, { thermal_snapshots: null }]) — mixed valid/invalid
Expected: No throw; returns angle feedback for frame 0; thermal skipped or partial
Pass criteria:
  [ ] With thresholds: uses provided values (including thermal)
  [ ] Without: uses defaults
  [ ] Malformed frame structure does not cause empty return for all feedback
  [ ] No regression for existing callers
If it fails: Refactor both generators to accept params
```

*Estimate:* 1h

*Classification:* CRITICAL

---

**Step 4.2 — Pass thresholds to generateMicroFeedback in Replay page**

*What:* Replay page receives score (with active_threshold_spec); build full thresholds from active_threshold_spec (including thermal, amps, volts, heat_diss); pass to generateMicroFeedback. **Gate micro-feedback on both sessionData and primaryScore** to avoid flicker when score loads after frames. **Add error UI when score fetch fails** — show "Score unavailable" or similar so user knows feedback is limited, not that session has no issues.

*File:* `my-app/src/app/replay/[sessionId]/page.tsx` (modify)

*Depends on:* Step 4.1, 2.3

*Code:*
```typescript
// Add score fetch error state
const [scoreFetchError, setScoreFetchError] = useState<string | null>(null);

// In fetchScore .catch:
.catch((err) => {
  if (!cancelled) {
    logWarn("ReplayPage", `Failed to fetch score for ${sessionId}`, {
      error: err instanceof Error ? err.message : String(err),
    });
    setPrimaryScore(null);
    setScoreFetchError(err instanceof Error ? err.message : "Score unavailable");
  }
});

// Clear scoreFetchError when score succeeds
.then((data) => {
  if (!cancelled) {
    setPrimaryScore(data);
    setScoreFetchError(null);
  }
});

// Gate: wait for both sessionData AND primaryScore (or scoreFetchError) before deciding micro-feedback
const thresholdsForMicroFeedback = useMemo(() => {
  const spec = primaryScore?.active_threshold_spec;
  if (!spec) return undefined;
  return {
    weld_type: spec.weld_type,
    angle_target_degrees: spec.angle_target,
    angle_warning_margin: spec.angle_warning,
    angle_critical_margin: spec.angle_critical,
    thermal_symmetry_warning_celsius: spec.thermal_symmetry_warning_celsius ?? 60,
    thermal_symmetry_critical_celsius: spec.thermal_symmetry_critical_celsius ?? 80,
    amps_stability_warning: spec.amps_stability_warning ?? 5,
    volts_stability_warning: spec.volts_stability_warning ?? 1,
    heat_diss_consistency: spec.heat_diss_consistency ?? 40,
  } as WeldTypeThresholds;
}, [primaryScore?.active_threshold_spec]);

const microFeedback = useMemo(() => {
  if (!sessionData?.frames) return [];
  // If score never loaded (fetch failed): use fallback thresholds but show error state
  if (!primaryScore && !scoreFetchError) return []; // Still loading
  return generateMicroFeedback(sessionData.frames, thresholdsForMicroFeedback);
}, [sessionData?.frames, primaryScore, scoreFetchError, thresholdsForMicroFeedback]);
```

In JSX, near ScorePanel or FeedbackPanel:
```tsx
{scoreFetchError && (
  <p className="text-amber-600 dark:text-amber-400 text-sm" data-testid="score-fetch-error">
    Score unavailable: {scoreFetchError}. Micro-feedback may use default thresholds.
  </p>
)}
```

*Why this approach:* When score API returns 500 or times out, primaryScore stays null. Without scoreFetchError, microFeedback stays [] with no explanation. User may assume "no issues" when actually score fetch failed. Showing scoreFetchError surfaces the failure; micro-feedback can still render with fallback thresholds (once we know fetch completed, even if failed) so user gets some feedback.

*Verification:*
```
Setup: Session with process_type=tig; backend returns active_threshold_spec with thermal_symmetry_warning_celsius: 60
Action: Open /replay/{sessionId}; ensure score loaded before micro-feedback
Expected: Micro-feedback uses TIG thresholds (75° angle, 60°C thermal)
Action: Simulate score fetch failure (e.g. block /api/sessions/{id}/score in DevTools, return 500)
Expected: "Score unavailable" message visible; micro-feedback shows with default thresholds (or empty with message)
Action: Throttle score API (DevTools Network slow 3G); load Replay; verify markers don't visibly re-render when score arrives
Pass criteria:
  [ ] TIG session: angle feedback based on 75°, thermal based on 60
  [ ] MIG session: angle based on 45°, thermal based on 60 (seed)
  [ ] Score fetch failure: scoreFetchError displayed; user informed
  [ ] Micro-feedback does not re-render visibly when score loads after frames (no flicker)
If it fails: primaryScore loads after frames; ensure gate; add scoreFetchError to fetch catch
```

*Estimate:* 0.75h

*Classification:* NON-CRITICAL

---

**Step 4.3 — Add threshold callout to Seagull WelderReport**

*What:* Below the score (e.g. under "100/100"), display "Evaluated against MIG spec — Target 45° ±5°" when `score.active_threshold_spec` is present.

*File:* `my-app/src/app/seagull/welder/[id]/page.tsx` (modify)

*Depends on:* Step 2.3, 3.1

*Code:*
```tsx
{score?.active_threshold_spec && (
  <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
    Evaluated against {score.active_threshold_spec.weld_type.toUpperCase()} spec — Target {score.active_threshold_spec.angle_target}° ±{score.active_threshold_spec.angle_warning}°
  </div>
)}
```

*Verification:*
```
Setup: Backend with session; fetchScore returns active_threshold_spec
Action: Open /seagull/welder/mike-chen (or expert-benchmark)
Expected: Below score: "Evaluated against MIG spec — Target 45° ±5°"
Pass criteria:
  [ ] Callout visible when spec present
  [ ] Callout hidden when spec absent
  [ ] Values match score response
If it fails: Check score type; ensure fetchScore returns spec
```

*Estimate:* 0.5h

*Classification:* NON-CRITICAL

---

**Step 4.4 — Add threshold callout to ScorePanel (Replay)**

*What:* ScorePanel displays threshold callout when `active_threshold_spec` is in the score response.

*File:* `my-app/src/components/welding/ScorePanel.tsx` (modify)

*Depends on:* Step 2.3

*Code:*
```tsx
{score?.active_threshold_spec && (
  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2">
    Evaluated against {score.active_threshold_spec.weld_type.toUpperCase()} spec — Target {score.active_threshold_spec.angle_target}° ±{score.active_threshold_spec.angle_warning}°
  </p>
)}
```

*Verification:*
```
Setup: Replay page with session that has process_type
Action: Open /replay/{sessionId}
Expected: ScorePanel shows score and callout
Pass criteria:
  [ ] Callout below rules list
  [ ] Correct spec values
If it fails: ScorePanel receives full score from API
```

*Estimate:* 0.25h

*Classification:* NON-CRITICAL

---

**Step 4.5 — Add mock threshold callout to demo WelderReport**

*What:* Demo team welder page uses mock data; add callout. **Prefer mock score's active_threshold_spec when present.** When absent, fetch GET /api/thresholds and use mig row so callout reflects admin-configured values (not hardcoded 45° ±5°). If fetch fails (offline/demo-only), show "Evaluated against configured spec" or omit callout.

*File:* `my-app/src/app/demo/team/[welderId]/page.tsx` (modify)

*Depends on:* none

*Code:*
```tsx
// Add state and fetch on mount
const [fetchedThresholds, setFetchedThresholds] = useState<WeldTypeThresholds[] | null>(null);
useEffect(() => {
  fetchThresholds().then(setFetchedThresholds).catch(() => setFetchedThresholds(null));
}, []);

// Callout — prefer mock spec, else use fetched MIG (reflects admin config)
{(mockScore?.active_threshold_spec) ? (
  <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
    Evaluated against {mockScore.active_threshold_spec.weld_type.toUpperCase()} spec — Target {mockScore.active_threshold_spec.angle_target}° ±{mockScore.active_threshold_spec.angle_warning}°
  </div>
) : (() => {
  const mig = fetchedThresholds?.find(t => t.weld_type === 'mig');
  return mig ? (
    <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
      Evaluated against MIG spec — Target {mig.angle_target_degrees}° ±{mig.angle_warning_margin}°
    </div>
  ) : null;
})()}
```
Place below the score in the report card.

*Verification:*
```
Setup: my-app dev
Action: Open /demo/team/{welderId}
Expected: Callout visible below score
Pass criteria:
  [ ] Callout displays
  [ ] Layout unchanged
  [ ] When mock lacks spec: callout uses fetched MIG thresholds (admin-configured values)
If it fails: Check placement in JSX
```

*Estimate:* 0.25h

*Classification:* NON-CRITICAL

---

**Step 4.6 — Add automated tests**

*What:* Tests for GET/PUT thresholds API; scoring with different thresholds; cache invalidation (PUT then GET score asserts active_threshold_spec); WelderReport/ScorePanel callout when spec present. **Specify exact FastAPI dependency override keys**; **assert session has frames** for score endpoint tests.

*File:* `backend/tests/conftest.py` (modify), `backend/tests/test_thresholds_api.py` (create), `backend/tests/test_scoring_thresholds.py` (create), `my-app/src/__tests__/components/welding/ScorePanel.test.tsx` (modify), `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` (modify)

*Depends on:* Steps 1.5, 2.3, 4.3, 4.4

*Code:*
```python
# conftest.py — in fixture that creates engine/tables (e.g. db or app fixture):
# MUST import WeldThresholdModel BEFORE Base.metadata.create_all so weld_thresholds
# table is created. Test order is non-deterministic; test_thresholds_api may run
# before any test that imported WeldThresholdModel. Without this import, create_all
# omits weld_thresholds and tests fail with "no such table weld_thresholds".
from database.models import Base, SessionModel, FrameModel, WeldThresholdModel  # WeldThresholdModel required
# ... then Base.metadata.create_all(engine)
```

```python
# test_thresholds_api.py

# IMPORTANT: Override get_db for BOTH routes.thresholds and routes.sessions.
# FastAPI matches dependency overrides by callable reference. Each route module
# defines its own get_db(). Both must be overridden or test_put_threshold_invalidates_cache
# will hit real DB and pass for wrong reasons.
# Override keys (exact): routes.thresholds.get_db, routes.sessions.get_db
# Example:
from routes import thresholds as thresholds_routes
from routes import sessions as sessions_routes

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[thresholds_routes.get_db] = override_get_db
    app.dependency_overrides[sessions_routes.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

```python
# session_factory must produce session with 10+ frames for valid score
# generate_expert_session produces ~1500 frames — valid
# Assert in test: len(session.frames) >= 10 or equivalent

@pytest.fixture
def session_factory(db, seeded_weld_thresholds):
    """Creates SessionModel with frames and process_type for score endpoint tests.
    Uses generate_expert_session (has 10+ frames). REQUIRED: WeldThresholdModel must be
    imported before Base.metadata.create_all (in conftest engine/session fixture) so
    weld_thresholds table exists. Fixture order: seeded_weld_thresholds depends on
    table creation; conftest must ensure WeldThresholdModel is imported before create_all.
    """
    from data.mock_sessions import generate_expert_session
    from database.models import SessionModel

    def _create(process_type: str = "mig", session_id: str = "sess_test_001"):
        session = generate_expert_session(session_id=session_id)
        assert len(session.frames) >= 10, "Session must have 10+ frames for valid score"
        session = session.model_copy(update={"process_type": process_type})
        model = SessionModel.from_pydantic(session)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    return _create
```

**Test run requirements:** Run from project root with backend on PYTHONPATH, or `cd backend && pytest tests/test_thresholds_api.py -v`. If importing `data.mock_sessions` fails, ensure `cd backend` or `PYTHONPATH=backend`.

```python
def test_put_threshold_invalidates_cache(client, db, session_factory, seeded_weld_thresholds):
    session = session_factory(process_type="mig")
    assert len(session.frames) >= 10, "Fixture must provide session with frames"
    # ... rest of test
```

*Verification:*
```
Setup: pytest, jest configured. Run from backend: cd backend && pytest tests/test_thresholds_api.py tests/test_scoring_thresholds.py -v
Expected: All pass, including test_put_threshold_invalidates_cache
Action: cd my-app && npm test -- ScorePanel.test
Expected: Callout test passes
Pass criteria:
  [ ] GET/PUT tests pass
  [ ] test_put_threshold_invalidates_cache: PUT then GET score, assert active_threshold_spec.angle_target changed
  [ ] session_factory produces session with len(frames) >= 10
  [ ] Dependency overrides applied to both thresholds and sessions get_db
  [ ] ScorePanel callout test passes
If it fails: Verify routes.thresholds.get_db and routes.sessions.get_db are overridden; check PYTHONPATH
```

*Estimate:* 2h

*Classification:* CRITICAL

---

## Risk Heatmap

| Phase.Step | Risk Description | Probability | Impact | Early Warning | Mitigation |
|------------|------------------|-------------|--------|---------------|------------|
| 1.2 | Migration fails; partial migration (UPDATE succeeds, ALTER fails) | Med | High | alembic upgrade error; revision partially applied | Pre-flight: row count (>1000 → manual UPDATE first), migration_preview.sql, DB writable check; test on copy of prod DB |
| 1.2 | DATABASE_URL is read replica; UPDATE fails | Low | High | Permission error on UPDATE | Pre-flight writable check (CREATE/DROP test table) |
| 1.2 | Migration never run in CI; first prod run fails | Med | High | Production deploy failure | Add alembic upgrade head to CI (SQLite or ephemeral Postgres) |
| 1.4 | Cache not invalidated on PUT → stale scores | Low | Med | Admin saves, score unchanged | invalidate_cache in finally; test_put_threshold_invalidates_cache |
| 1.4 | invalidate_cache race with _load_all | Low | Med | Redundant _load_all; potential stale read | invalidate_cache acquires _load_lock |
| 1.4 | Multi-worker: stale thresholds on other workers | Med | High | Admin saves, worker B serves old | Document; backlog shared cache (Redis) |
| 1.7 | Invalid process_type stored; scoring uses wrong thresholds | Med | High | WelderReport shows wrong spec | process_type validation in create_session (mig,tig,stick,flux_core) |
| 4.1 | Malformed frames cause empty feedback; no error surface | Low | Med | User sees no feedback; logs show error | Per-generator try-catch; partial results; logWarn |
| 4.2 | Score fetch fails; user sees no feedback with no explanation | Med | Low | Blank micro-feedback; user confused | scoreFetchError state; "Score unavailable" UI |
| 4.6 | Dependency override key wrong; test hits real DB | Low | High | test_put_threshold_invalidates_cache flaky | Override routes.thresholds.get_db and routes.sessions.get_db explicitly |
| 4.6 | session_factory creates session without frames | Med | High | test passes for wrong reason | Assert len(session.frames) >= 10 in fixture |
| 2.3 | Session with 0–9 frames returns valid-looking score | Med | High | WelderReport shows 100/100 for empty session | Explicit len(frames) < 10 check; return 400 |
| 1.4 | tig/stick/flux_core row missing; silent MIG fallback | Low | High | TIG scored with MIG thresholds | Fail loudly (ValueError) when known type missing |

---

## Pre-Flight Checklist

### Phase 1 Prerequisites
- [ ] PostgreSQL running, DATABASE_URL set — `psql $DATABASE_URL -c "SELECT 1"` — Fix: start Postgres, set env
- [ ] DATABASE_URL points to primary (writable) DB, not read replica — `psql $DATABASE_URL -c "CREATE TABLE _x(id INT); DROP TABLE _x"` — Fix: use primary
- [ ] Alembic at revision 003 — `cd backend && alembic current` — Fix: `alembic upgrade 003`
- [ ] down_revision matches 003 — `grep "revision\|down_revision" alembic/versions/003*.py` — Fix: ensure 004 down_revision = "003_add_score_total"
- [ ] Backend venv active, deps installed — `cd backend && python -c "import fastapi"` — Fix: `pip install -r requirements.txt`
- [ ] No uncommitted migration conflicts — `alembic history` — Fix: resolve branches
- [ ] Migration SQL preview — `alembic upgrade head --sql > migration_preview.sql`; inspect before applying
- [ ] **If sessions >1000 rows (staging/prod):** Run manual `UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL`; verify `SELECT COUNT(*) FROM sessions WHERE process_type IS NULL` = 0 — Fix: run UPDATE; retry upgrade

### Phase 2 Prerequisites
- [ ] Phase 1 complete — weld_thresholds table exists
- [ ] Step 1.3 complete — SessionModel has process_type
- [ ] Sessions have process_type — `SELECT process_type FROM sessions LIMIT 1`
- [ ] Post-migration smoke check — `SELECT COUNT(*) FROM sessions WHERE process_type IS NULL` = 0
- [ ] threshold_service returns data — `get_thresholds(db,"mig")`, `get_all_thresholds(db)`
- [ ] extract_features and score_session accept new params
- [ ] test_put_threshold_invalidates_cache passes (run early to verify cache invalidation)

### Phase 3 Prerequisites
- [ ] Backend /api/thresholds returns 200 — `curl /api/thresholds`
- [ ] NEXT_PUBLIC_API_URL or localhost:8000 — Env check
- [ ] my-app builds — `npm run build`
- [ ] No existing /admin route conflicts

### Phase 4 Prerequisites
- [ ] Score API returns active_threshold_spec with thermal/amps/volts/heat_diss
- [ ] SessionScore type has active_threshold_spec
- [ ] generateMicroFeedback accepts optional param
- [ ] Replay fetches score before micro-feedback

---

## Success Criteria

1. **Admin tabs** — User can open `/admin/thresholds` and see MIG|TIG|Stick|Flux Core tabs. P0.
2. **Edit and save** — User can edit angle/thermal/amps/volts/heat_diss and save; changes persist. P0.
3. **Arc diagram** — Small inline arc next to angle inputs shows target angle. P1.
4. **Validation** — warning > critical shows inline error or 422; angle_target_degrees=0 rejected; process_type invalid rejected at create_session. P0.
5. **GET thresholds** — Returns array keyed by weld_type. P0.
6. **Scoring uses thresholds** — Session with process_type=tig scores with TIG thresholds. P0.
7. **angle_max_deviation** — Uses configured target. P0.
8. **Micro-feedback thresholds** — Replay uses configured thresholds (angle + thermal); no visible flicker when score loads after frames; score fetch failure shows error UI. P1.
9. **WelderReport callout** — "Evaluated against MIG spec — Target 45° ±5°". P0.
10. **Score API active_threshold_spec** — Response includes weld_type, angle_target, angle_warning, thermal/amps/volts/heat_diss. P0.
11. **Cache** — No DB hit per score. P1.
12. **Automated tests** — GET/PUT, cache invalidation, scoring, callout covered; session with <10 frames returns 400. P0.
13. **Migration in CI** — alembic upgrade head runs in CI (SQLite or ephemeral Postgres). P1.

---

## Progress Tracker

```
| Phase   | Steps | Done | In Progress | Blocked | %   |
|---------|-------|------|-------------|---------|-----|
| Phase 1 | 9     | 0    | 0           | 0       | 0%  |
| Phase 2 | 3     | 0    | 0           | 0       | 0%  |
| Phase 3 | 4     | 0    | 0           | 0       | 0%  |
| Phase 4 | 6     | 0    | 0           | 0       | 0%  |
| TOTAL   | 22    | 0    | 0           | 0       | 0%  |
```

---

## Notes

- **Pre-flight script:** `backend/scripts/preflight_migration.py` runs DB writability check and row-count guard; exits with clear instructions if sessions >1000. Optional before `alembic upgrade head`.
- **Post-migration seed verification:** Assert tig=75, stick=20, flux_core=45, mig=45 in weld_thresholds after migration.
- **Health check (optional):** Add startup log or `/health` that confirms weld_thresholds has 4 rows after migration.
- **WeldTypeThresholds/WeldThresholdUpdate:** `angle_target_degrees` uses `gt=0` to match PUT validation; programmatic creation with 0 fails at model level.
- **create_session:** process_type validated against (mig, tig, stick, flux_core); invalid values return 422.
- **Pre-flight:** DB writable check prevents read-replica failures; post-migration smoke check ensures zero NULL process_type.
- **Phase 1 CI:** Add alembic upgrade head to CI to catch migration syntax errors before production.
- **Prototype scripts:** prototype_arc_scoring.py and prototype_aggregate_perf.py updated to use get_thresholds; or document in Known Issues.
- **generateMicroFeedback:** Per-generator try-catch; partial results on sub-generator failure; no silent empty return for angle+thermal both failing.
- **Replay score fetch error:** scoreFetchError state and UI when fetch fails; user informed, not silently degraded.
- **test_thresholds_api:** Override `routes.thresholds.get_db` and `routes.sessions.get_db`; session_factory asserts len(frames) >= 10; conftest imports WeldThresholdModel before create_all; run from backend or with PYTHONPATH.
- **Thermal fallback:** Step 4.2 uses 60/80 for thermal_symmetry_* when spec omits them (matches seed); legacy 4-field spec would otherwise use wrong threshold.

---

## Known Issues & Limitations

- **Multi-worker cache**: Single-process cache invalidates only in the worker that handled the PUT. Other workers retain stale thresholds until restart. For MVP: document; use single worker or add Redis to backlog.
- **Migration compatibility**: Assumes vanilla PostgreSQL. DBs with extensions, read replicas, or custom triggers may need migration adjustments.
- **Large-table migration**: Step 1.2 uses single `UPDATE sessions SET process_type = 'mig'`. On DBs with 100k+ sessions, consider batched UPDATE or run during maintenance window.
- **AngleArcDiagram**: Validation limits angle_target to ≤90°; arc path assumes ≤90°.
- **Prototype scripts (if not updated):** prototype_arc_scoring.py and prototype_aggregate_perf.py use legacy scoring without thresholds; will score all sessions with MIG constants. Update per Step 1.9 or run only with MIG sessions.
- **Flicker verification (Step 4.2):** "Verify markers don't visibly re-render" is subjective; throttle test is manual. No automatable DOM assertion for CI.

---

## Rollback Procedure

**Code reverted but migration not reverted:** If code is reverted (e.g. feature flag off) but `alembic downgrade -1` was not run, DB schema is ahead of code. SessionModel.from_pydantic may fail if code expects process_type but column was dropped. Fix: run `alembic downgrade -1` to revert schema, or redeploy code to match schema.

**Partial rollback (after Phase 1 or 2):**
```bash
cd backend && alembic downgrade -1
# Drops weld_thresholds table and process_type column
```

**Full rollback:** Revert code changes; run downgrade above. Restore SessionModel, routes, frontend from git.
