# Threshold Configuration Admin UI — Implementation Plan

## Phase Breakdown

---

## Phase 1 — Data Model & Backend Foundation

**Goal:** `weld_thresholds` table exists with seed data; `process_type` column on sessions; `GET/PUT` thresholds API works; cache in place.

**Risk:** Low

**Estimate:** 6.25h (includes Step 1.8 backfill update)

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

**Estimate:** 5h

---

## Steps

---

### Phase 1 — Data Model & Backend Foundation

**Step 1.1 — Add Pydantic WeldTypeThresholds model**

*What:* Define `WeldTypeThresholds` and `WeldThresholdUpdate` Pydantic models for API and service use.

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
    angle_target_degrees: float = Field(..., ge=0, le=90)
    angle_warning_margin: float = Field(..., ge=0, le=45)
    angle_critical_margin: float = Field(..., ge=0, le=45)
    thermal_symmetry_warning_celsius: float = Field(..., ge=0, le=200)
    thermal_symmetry_critical_celsius: float = Field(..., ge=0, le=200)
    amps_stability_warning: float = Field(..., ge=0)
    volts_stability_warning: float = Field(..., ge=0)
    heat_diss_consistency: float = Field(..., ge=0)


class WeldThresholdUpdate(BaseModel):
    """Request body for PUT /api/thresholds/:weld_type."""

    angle_target_degrees: float = Field(..., ge=0, le=90)
    angle_warning_margin: float = Field(..., ge=0, le=45)
    angle_critical_margin: float = Field(..., ge=0, le=45)
    thermal_symmetry_warning_celsius: float = Field(..., ge=0, le=200)
    thermal_symmetry_critical_celsius: float = Field(..., ge=0, le=200)
    amps_stability_warning: float = Field(..., ge=0)
    volts_stability_warning: float = Field(..., ge=0)
    heat_diss_consistency: float = Field(..., ge=0)
```

*Why this approach:* Exploration locked WeldTypeThresholds contract; heat_diss included per exploration decision.

*Verification:*
```
Setup: Backend venv active
Action: cd backend && python -c "from models.thresholds import WeldTypeThresholds, WeldThresholdUpdate; t = WeldTypeThresholds(weld_type='mig', angle_target_degrees=45, angle_warning_margin=5, angle_critical_margin=15, thermal_symmetry_warning_celsius=20, thermal_symmetry_critical_celsius=40, amps_stability_warning=5, volts_stability_warning=1, heat_diss_consistency=40); print(t.weld_type)"
Expected: mig
Pass criteria:
  [ ] Pydantic import succeeds
  [ ] WeldTypeThresholds instantiation succeeds
  [ ] Field validation rejects negative values (python -c "WeldTypeThresholds(weld_type='mig', angle_target_degrees=-1, ...)" raises)
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
    # (see Known Issues: large-table migration). Single UPDATE locks table briefly.
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
# If 003_add_score_total is missing: fix down_revision to match actual chain
grep -l "revision = " alembic/versions/*.py | xargs grep "revision\|down_revision"
# Confirm 003 file has revision = "003_add_score_total"

# 2. Preview SQL: operator inspects what will run before applying
alembic upgrade head --sql > migration_preview.sql
# Review migration_preview.sql; confirm no unexpected DDL

# 3. Large-table guard: if sessions has >1000 rows, run manual UPDATE first
psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions"
# If count > 1000: run manual UPDATE first to avoid partial migration failure:
#   psql $DATABASE_URL -c "UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL"
#   Verify: psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions WHERE process_type IS NULL" → 0
# Then run alembic upgrade head (migration will skip UPDATE or no-op)
# If count <= 1000: proceed with alembic upgrade head directly
```

*Why this approach:* Exploration chose add process_type column; TIG 75° ±10° per assumption; thermal/amps/volts/heat_diss from rule_based defaults. `sa.text()` used for raw SQL to avoid deprecation warnings.

*Verification:*
```
Setup: PostgreSQL running, DATABASE_URL set, alembic at 003
Action: cd backend && alembic upgrade head
Expected: Migration 004 runs without error
Action: psql $DATABASE_URL -c "SELECT weld_type, angle_target_degrees FROM weld_thresholds"
Expected: 4 rows (mig, tig, stick, flux_core)
Action: psql $DATABASE_URL -c "SELECT process_type FROM sessions LIMIT 1"
Expected: mig (or column exists)
Pass criteria:
  [ ] upgrade completes
  [ ] weld_thresholds has 4 rows
  [ ] sessions.process_type exists, backfilled
  [ ] downgrade works (alembic downgrade -1)
If it fails: Check down_revision matches 003 file; verify sessions table has no conflicting constraints
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

*Why this approach:* Session must carry process_type for scoring; default mig for backward compatibility.

*Verification:*
```
Setup: Migration 004 applied
Action: python -c "from database.models import SessionModel; ..." — or run existing session tests
Expected: Session.to_pydantic() includes process_type
Pass criteria:
  [ ] Session model has process_type
  [ ] SessionModel round-trip preserves process_type
  [ ] Session with process_type=None yields "mig" (not None) — test: from_pydantic(session_with_process_type_none)
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
    with _load_lock:
        if _cache_loaded:  # Double-check after acquiring lock
            return
        rows = db.execute(select(WeldThresholdModel)).scalars().all()
        if rows:
            _threshold_cache = {
                r.weld_type: WeldTypeThresholds(
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
                for r in rows
            }
        else:
            # Empty table: use hardcoded MIG defaults so scoring doesn't 500
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


def get_thresholds(db: OrmSession, process_type: str) -> WeldTypeThresholds:
    """Get thresholds for a process type. Falls back to mig if unknown."""
    global _cache_loaded
    if not _cache_loaded:
        _load_all(db)
    key = (process_type or "mig").lower()
    if key not in _threshold_cache:
        key = "mig"
    # Guard: _threshold_cache always has "mig" after _load_all (either from DB or fallback)
    return _threshold_cache.get(key, _threshold_cache["mig"])


def get_all_thresholds(db: OrmSession) -> List[WeldTypeThresholds]:
    """Return all thresholds. Admin UI uses this for GET /api/thresholds."""
    global _cache_loaded
    if not _cache_loaded:
        _load_all(db)
    return list(_threshold_cache.values())
```

*Why this approach:* Exploration: invalidate on PUT; no DB hit per score. Empty-table guard prevents KeyError when weld_thresholds has 0 rows.

*Verification:*
```
Setup: DB with seeded thresholds, backend running
Action: In Python shell: from database.connection import SessionLocal; from services.threshold_service import get_thresholds, get_all_thresholds; db = SessionLocal(); t = get_thresholds(db, "mig"); print(t.angle_target_degrees)
Expected: 45
Action: Simulate empty table — truncate weld_thresholds; t = get_thresholds(db, "mig")
Expected: Returns WeldTypeThresholds (45, 5, 15, ...) — no KeyError
Pass criteria:
  [ ] get_thresholds("mig") returns MIG thresholds
  [ ] get_thresholds("unknown") falls back to mig
  [ ] get_all_thresholds returns 4 items (or 1 if table empty)
  [ ] Empty table: get_thresholds does not raise
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
    # angle_target_degrees=0 makes scoring useless (every angle >0 triggers warning)
    if body.angle_target_degrees == 0:
        raise HTTPException(
            status_code=422,
            detail="angle_target_degrees must be > 0",
        )
    # Asymmetric validation: angle and thermal have warning <= critical ordering;
    # amps/volts/heat_diss have no ordering relationship.
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
        # Always invalidate so next request refetches; prevents stale cache if return fails
        invalidate_cache()
    # Build response from committed row — avoids 500 if get_thresholds fails (e.g. connection pool timeout)
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

*Why this approach:* Invalidate in finally so cache is cleared even if commit succeeds but return raises. Return single updated threshold (avoids refetch overhead).

*Verification:*
```
Setup: Backend running, migration applied
Action: curl -X PUT http://localhost:8000/api/thresholds/mig -H "Content-Type: application/json" -d '{"angle_target_degrees":0,"angle_warning_margin":5,"angle_critical_margin":15,"thermal_symmetry_warning_celsius":20,"thermal_symmetry_critical_celsius":40,"amps_stability_warning":5,"volts_stability_warning":1,"heat_diss_consistency":40}'
Expected: 422, detail "angle_target_degrees must be > 0"
Action: curl -s http://localhost:8000/api/thresholds
Expected: JSON array of 4 objects with weld_type, angle_target_degrees, etc.
Action: curl -X PUT http://localhost:8000/api/thresholds/mig -H "Content-Type: application/json" -d '{"angle_target_degrees":45,"angle_warning_margin":5,"angle_critical_margin":15,"thermal_symmetry_warning_celsius":20,"thermal_symmetry_critical_celsius":40,"amps_stability_warning":5,"volts_stability_warning":1,"heat_diss_consistency":40}'
Expected: 200, single object (not array)
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

*Why this approach:* Standard FastAPI pattern.

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

*What:* Accept optional `process_type` in `CreateSessionRequest`; include `process_type` in `get_session` response; default `mig`.

*File:* `backend/routes/sessions.py` (modify)

*Depends on:* Step 1.2, 1.3

*Code:*
```python
# CreateSessionRequest: add process_type: Optional[str] = None
# In create_session: process_type = body.process_type or "mig"
# SessionModel(... process_type=process_type ...) — add to model init
# session_payload: add "process_type": session_model.process_type or "mig"
```

*Why this approach:* New sessions must store process_type for scoring.

*Verification:*
```
Setup: Backend running
Action: POST /api/sessions with {"operator_id":"op1","weld_type":"mild_steel","process_type":"tig"}
Expected: 201, session created
Action: GET /api/sessions/{id}
Expected: JSON includes "process_type": "tig"
Pass criteria:
  [ ] POST accepts process_type
  [ ] GET returns process_type
  [ ] Omitted process_type defaults to mig
If it fails: SessionModel may need process_type in constructor
```

*Estimate:* 0.5h

*Classification:* NON-CRITICAL

---

**Step 1.8 — Update backfill_score_total.py to use thresholds**

*What:* backfill_score_total.py currently uses `extract_features(session)` (default angle_target=45) and `score_session(session, features)` (thresholds=None). If backfill runs after new TIG/stick/flux_core sessions exist with score_total=NULL, they are scored with MIG constants. Update backfill to load thresholds per session's process_type.

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

*Why this approach:* Without this, any backfill run after non-MIG sessions exist will score them incorrectly. Migration backfills process_type='mig' for existing rows; new sessions may have process_type='tig' etc.

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

*Classification:* CRITICAL (prevents silent corruption on future backfill runs)

---

### Phase 2 — Wire Thresholds into Scoring

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

*Why this approach:* Exploration: add optional param; backward compatible default 45.

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
# Full CRITICAL implementation:

from typing import Any, Dict, Optional
from models.scoring import ScoreRule, SessionScore
from models.session import Session
from models.thresholds import WeldTypeThresholds

# Keep as fallback for tests/callers that don't pass thresholds
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

*Why this approach:* Exploration: refactor to accept thresholds; fallback for backward compat.

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
from services.threshold_service import get_thresholds

# After session_model loaded (requires Step 1.3 — SessionModel.process_type):
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

*Why this approach:* Full spec enables Replay micro-feedback to use configured thermal/amps/volts/heat_diss instead of hardcoded values.

*Verification:*
```
Setup: Backend running, session with process_type=tig
Action: GET /api/sessions/{session_id}/score
Expected: JSON has "total", "rules", "active_threshold_spec" with weld_type, angle_target, angle_warning, angle_critical, thermal_symmetry_warning_celsius, thermal_symmetry_critical_celsius, amps_stability_warning, volts_stability_warning, heat_diss_consistency
Pass criteria:
  [ ] active_threshold_spec present with all 9 fields
  [ ] weld_type matches session process_type
  [ ] TIG thermal_symmetry_warning_celsius = 60 (from seed)
  [ ] Rules use thresholds (e.g. angle_consistency threshold = angle_warning)
If it fails: Check session_model has process_type after migration
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
// PUT now returns single object; frontend refetches all if needed
```

*Why this approach:* Full ActiveThresholdSpec mirrors backend; frontend can pass all thresholds to micro-feedback.

*Verification:*
```
Setup: Backend running, my-app dev server
Action: In browser console or test: fetch('http://localhost:8000/api/thresholds').then(r=>r.json()).then(console.log)
Expected: Array of 4 threshold objects
Pass criteria:
  [ ] fetchThresholds returns array
  [ ] updateThreshold sends PUT, returns single object (update api.ts to expect single)
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
  // Arc 0 to angleTargetDegrees; validation limits to ≤90° so largeArc always 0
  const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z`;
  return (
    <svg width="60" height="40" viewBox="0 0 60 40" className={className} aria-hidden>
      <path d={d} fill="none" stroke="currentColor" strokeWidth="2" />
      <text x="30" y="38" textAnchor="middle" fontSize="10">{angleTargetDegrees}°</text>
    </svg>
  );
}
```

*Why this approach:* Task: tiny inline arc showing target angle; validation enforces angle_target ≤90, so arc is always ≤90°.

*Verification:*
```
Setup: Next dev server
Action: Render <AngleArcDiagram angleTargetDegrees={45} /> in a test page
Expected: Semicircle arc from 0° to 45°, "45°" label
Pass criteria:
  [ ] SVG renders
  [ ] Arc spans correct angle (visual: 45° arc)
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

*Why this approach:* Exploration: standalone /admin route group.

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

*What:* Page at `/admin/thresholds` with tabs MIG|TIG|Stick|Flux Core; per-tab form with Angle (target, warning, critical), Thermal, Amps/Volts, Heat Diss; Save button; AngleArcDiagram next to angle inputs; inline validation errors. Disable Save until fetch succeeds and form is fully populated to prevent partial PUT.

*File:* `my-app/src/app/admin/thresholds/page.tsx` (create)

*Depends on:* Step 3.1, 3.2, 3.3

*Code:* (NON-CRITICAL — key pattern)
```tsx
'use client';
import { useState, useEffect } from 'react';
import { fetchThresholds, updateThreshold } from '@/lib/api';
import type { WeldTypeThresholds } from '@/types/thresholds';
import AngleArcDiagram from '@/components/admin/AngleArcDiagram';

const TABS = ['mig', 'tig', 'stick', 'flux_core'] as const;

function isCompleteForm(f: Partial<WeldTypeThresholds>): f is WeldTypeThresholds {
  const isNum = (v: unknown) => typeof v === 'number' && Number.isFinite(v);
  return (
    isNum(f.angle_target_degrees) &&
    (f.angle_target_degrees ?? 0) > 0 &&
    isNum(f.angle_warning_margin) &&
    isNum(f.angle_critical_margin) &&
    isNum(f.thermal_symmetry_warning_celsius) &&
    isNum(f.thermal_symmetry_critical_celsius) &&
    isNum(f.amps_stability_warning) &&
    isNum(f.volts_stability_warning) &&
    isNum(f.heat_diss_consistency)
  );
}

export default function AdminThresholdsPage() {
  const [all, setAll] = useState<WeldTypeThresholds[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [active, setActive] = useState<typeof TABS[number]>('mig');
  const [form, setForm] = useState<Partial<WeldTypeThresholds>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchThresholds()
      .then(setAll)
      .catch(e => setFetchError(String(e)));
  }, []);

  const current = all.find(t => t.weld_type === active);
  useEffect(() => {
    if (current) setForm({ ...current });
  }, [active, current]);

  const canSave = !fetchError && all.length > 0 && isCompleteForm(form) && !saving;
  const handleSave = async () => {
    if (!canSave || !isCompleteForm(form)) return;
    if ((form.angle_target_degrees ?? 0) <= 0) {
      setError('angle_target_degrees must be > 0');
      return;
    }
    if (form.angle_warning_margin > form.angle_critical_margin) {
      setError('angle_warning_margin must be <= angle_critical_margin');
      return;
    }
    if (form.thermal_symmetry_warning_celsius > form.thermal_symmetry_critical_celsius) {
      setError('thermal_symmetry_warning must be <= thermal_symmetry_critical');
      return;
    }
    setSaving(true); setError(null);
    try {
      await updateThreshold(active, form);
      const updated = await fetchThresholds();
      setAll(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h1>Weld Quality Thresholds</h1>
      {fetchError && <p className="text-red-600">Failed to load thresholds: {fetchError}</p>}
      <div role="tablist">
        {TABS.map(t => (
          <button key={t} role="tab" aria-selected={active===t} onClick={() => setActive(t)}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>
      <section>
        <h2>Angle</h2>
        <label>Target <input type="number" value={form.angle_target_degrees ?? ''} onChange={e=>setForm(f=>({...f, angle_target_degrees: parseFloat(e.target.value)}))} />°</label>
        <AngleArcDiagram angleTargetDegrees={Number.isFinite(form.angle_target_degrees) ? form.angle_target_degrees! : 45} />
        <label>Warning ± <input type="number" value={form.angle_warning_margin ?? ''} onChange={e=>setForm(f=>({...f, angle_warning_margin: parseFloat(e.target.value)}))} />°</label>
        <label>Critical ± <input type="number" value={form.angle_critical_margin ?? ''} onChange={e=>setForm(f=>({...f, angle_critical_margin: parseFloat(e.target.value)}))} />°</label>
      </section>
      <section>
        <h2>Thermal / Amps / Volts / Heat Diss</h2>
        <label>Thermal warning °C <input type="number" value={form.thermal_symmetry_warning_celsius ?? ''} onChange={e=>setForm(f=>({...f, thermal_symmetry_warning_celsius: parseFloat(e.target.value)}))} /></label>
        <label>Thermal critical °C <input type="number" value={form.thermal_symmetry_critical_celsius ?? ''} onChange={e=>setForm(f=>({...f, thermal_symmetry_critical_celsius: parseFloat(e.target.value)}))} /></label>
        <label>Amps stability <input type="number" value={form.amps_stability_warning ?? ''} onChange={e=>setForm(f=>({...f, amps_stability_warning: parseFloat(e.target.value)}))} /></label>
        <label>Volts stability <input type="number" value={form.volts_stability_warning ?? ''} onChange={e=>setForm(f=>({...f, volts_stability_warning: parseFloat(e.target.value)}))} /></label>
        <label>Heat diss consistency <input type="number" value={form.heat_diss_consistency ?? ''} onChange={e=>setForm(f=>({...f, heat_diss_consistency: parseFloat(e.target.value)}))} /></label>
      </section>
      <button onClick={handleSave} disabled={!canSave}>Save Changes</button>
      {error && <p className="text-red-600" data-testid="validation-error">{error}</p>}
    </div>
  );
}
```

*Why this approach:* `isCompleteForm` and `canSave` prevent saving with partial data when fetch failed or form not populated. Backend requires all fields.

*Verification:*
```
Setup: Backend running, my-app dev
Action: Open /admin/thresholds; click MIG tab; change angle target to 50; Save
Expected: Form submits; GET /api/thresholds returns mig with 50
Action: Set warning 10, critical 5
Expected: Inline error or backend 422
Action: Block network (DevTools offline); reload page; Save disabled; error shown
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
If it fails: Check fetchThresholds/updateThreshold; form state
```

*Estimate:* 2.5h

*Classification:* CRITICAL (form logic, validation, API wiring)

---

### Phase 4 — Micro-Feedback & Report Callouts

**Step 4.1 — Add optional thresholds param to generateMicroFeedback**

*What:* Extend `generateMicroFeedback(frames, thresholds?)`; use thresholds when provided (angle + thermal + amps + volts); fallback to current constants when undefined.

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
  try {
    if (!Array.isArray(frames) || frames.length === 0) return [];
    const angle = generateAngleDriftFeedback(frames, angleTarget, angleWarning, angleCritical);
    const thermal = generateThermalSymmetryFeedback(frames, thermalThresh);
    return [...angle, ...thermal].sort((a, b) => a.frameIndex - b.frameIndex);
  } catch (err) { ... }
}

function generateAngleDriftFeedback(
  frames: Frame[],
  target: number,
  warning: number,
  critical: number
): MicroFeedbackItem[] {
  // Use target, warning, critical instead of ANGLE_TARGET_DEG, etc.
  const dev = Math.abs(a - target);
  if (dev <= warning) continue;
  const severity = dev >= critical ? "critical" : "warning";
  // ...
}

function generateThermalSymmetryFeedback(frames: Frame[], thresh: number): MicroFeedbackItem[] {
  // Use thresh instead of THERMAL_VARIANCE_THRESHOLD_CELSIUS
  // ...
}
```

*Why this approach:* Exploration: optional param; fallback to consts. Thermal uses configured thermal_symmetry_warning_celsius (TIG=60) instead of hardcoded 20.

*Verification:*
```
Setup: Unit test or manual
Action: generateMicroFeedback(frames, { angle_target_degrees: 75, angle_warning_margin: 10, thermal_symmetry_warning_celsius: 60, ... })
Expected: Angle feedback uses 75° target, ±10° warning; thermal uses 60°C
Action: generateMicroFeedback(frames)
Expected: Uses 45, 5, 15, 20 as before
Pass criteria:
  [ ] With thresholds: uses provided values (including thermal)
  [ ] Without: uses defaults
  [ ] No regression for existing callers
If it fails: Refactor both generators to accept params
```

*Estimate:* 1h

*Classification:* CRITICAL

---

**Step 4.2 — Pass thresholds to generateMicroFeedback in Replay page**

*What:* Replay page receives score (with active_threshold_spec); build full thresholds from active_threshold_spec (including thermal, amps, volts, heat_diss); pass to generateMicroFeedback. **Gate micro-feedback on both sessionData and primaryScore** to avoid flicker when score loads after frames.

*File:* `my-app/src/app/replay/[sessionId]/page.tsx` (modify)

*Depends on:* Step 4.1, 2.3

*Code:*
```typescript
// Gate: wait for both sessionData AND primaryScore before computing micro-feedback.
// Avoids flicker when frames load fast and score loads slow (markers jump on re-render).
const thresholdsForMicroFeedback = useMemo(() => {
  const spec = primaryScore?.active_threshold_spec;
  if (!spec) return undefined;
  return {
    weld_type: spec.weld_type,
    angle_target_degrees: spec.angle_target,
    angle_warning_margin: spec.angle_warning,
    angle_critical_margin: spec.angle_critical,
    thermal_symmetry_warning_celsius: spec.thermal_symmetry_warning_celsius ?? 20,
    thermal_symmetry_critical_celsius: spec.thermal_symmetry_critical_celsius ?? 40,
    amps_stability_warning: spec.amps_stability_warning ?? 5,
    volts_stability_warning: spec.volts_stability_warning ?? 1,
    heat_diss_consistency: spec.heat_diss_consistency ?? 40,
  } as WeldTypeThresholds;
}, [primaryScore?.active_threshold_spec]);

const microFeedback = useMemo(() => {
  if (!sessionData?.frames || !primaryScore) return [];
  return generateMicroFeedback(sessionData.frames, thresholdsForMicroFeedback);
}, [sessionData?.frames, primaryScore, thresholdsForMicroFeedback]);
```

*Why this approach:* Uses thermal/amps/volts/heat_diss from active_threshold_spec when present (Step 2.3 now includes them). Gate on both prevents visible flicker—micro-feedback renders once with correct thresholds instead of default-then-TIG jump.

*Verification:*
```
Setup: Session with process_type=tig; backend returns active_threshold_spec with thermal_symmetry_warning_celsius: 60
Action: Open /replay/{sessionId}; ensure score loaded before micro-feedback
Expected: Micro-feedback uses TIG thresholds (75° angle, 60°C thermal)
Action: Throttle score API (DevTools Network slow 3G); load Replay; verify markers don't visibly re-render when score arrives
Pass criteria:
  [ ] TIG session: angle feedback based on 75°, thermal based on 60
  [ ] MIG session: angle based on 45°, thermal based on 60 (seed)
  [ ] Session without spec falls back to 45/5/15/20
  [ ] Micro-feedback does not re-render visibly when score loads after frames (no flicker)
If it fails: primaryScore loads after frames; ensure gate (sessionData && primaryScore) in useMemo
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
Place directly below the score display (e.g. under the `{report.score}/100` div).

*Why this approach:* Task: "Evaluated against {process} spec — Target {target}° ±{warning}°".

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

*Why this approach:* ScorePanel fetches score; callout belongs with score display on Replay.

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

*What:* Demo team welder page uses mock data; add callout. Derive from mock score's active_threshold_spec when present to avoid mismatch if demo later uses TIG session.

*File:* `my-app/src/app/demo/team/[welderId]/page.tsx` (modify)

*Depends on:* none

*Code:*
```tsx
{/* Prefer mock score's active_threshold_spec when present */}
{(mockScore?.active_threshold_spec) ? (
  <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
    Evaluated against {mockScore.active_threshold_spec.weld_type.toUpperCase()} spec — Target {mockScore.active_threshold_spec.angle_target}° ±{mockScore.active_threshold_spec.angle_warning}°
  </div>
) : (
  <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
    Evaluated against MIG spec — Target 45° ±5°
  </div>
)}
```
Place below the score in the report card. Use mock score's active_threshold_spec when available so TIG/demo sessions show correct spec.

*Note:* Hardcoded fallback "MIG spec — Target 45° ±5°" can be wrong if admin changes MIG seed via thresholds UI. Low risk for demo; prefer mock spec when present.

*Why this approach:* Exploration: "or use mock spec for demo".

*Verification:*
```
Setup: my-app dev
Action: Open /demo/team/{welderId}
Expected: Callout visible below score
Pass criteria:
  [ ] Callout displays
  [ ] Layout unchanged
If it fails: Check placement in JSX
```

*Estimate:* 0.25h

*Classification:* NON-CRITICAL

---

**Step 4.6 — Add automated tests**

*What:* Tests for GET/PUT thresholds API; scoring with different thresholds; cache invalidation (PUT then GET score asserts active_threshold_spec); WelderReport/ScorePanel callout when spec present.

*File:* `backend/tests/test_thresholds_api.py` (create), `backend/tests/test_scoring_thresholds.py` (create), `my-app/src/__tests__/components/welding/ScorePanel.test.tsx` (modify), `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` (modify)

*Depends on:* Steps 1.5, 2.3, 4.3, 4.4

*Code:* (Key patterns)
```python
# test_thresholds_api.py
# Fixtures: db (in-memory SQLite, Base.metadata.create_all — ensure WeldThresholdModel imported
# before create_all so weld_thresholds table exists), client (override get_db for routes.thresholds
# and routes.sessions)

@pytest.fixture
def session_factory(db, seeded_weld_thresholds):
    """Creates SessionModel with frames and process_type for score endpoint tests.
    Requires Step 1.3 (Session has process_type). Uses generate_expert_session.
    """
    from data.mock_sessions import generate_expert_session
    from database.models import SessionModel

    def _create(process_type: str = "mig", session_id: str = "sess_test_001"):
        session = generate_expert_session(session_id=session_id)
        session = session.model_copy(update={"process_type": process_type})
        model = SessionModel.from_pydantic(session)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    return _create


def test_get_thresholds_returns_four(client, seeded_weld_thresholds):
    r = client.get("/api/thresholds")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    types = [t["weld_type"] for t in data]
    assert "mig" in types and "tig" in types

@pytest.fixture
def seeded_weld_thresholds(db):
    """Seed weld_thresholds so GET/PUT tests work. In-memory SQLite creates empty table."""
    from database.models import WeldThresholdModel
    for weld_type, a, aw, ac, tw, tc, amps, volts, hd in [
        ("mig", 45.0, 5.0, 15.0, 60.0, 80.0, 5.0, 1.0, 40.0),
        ("tig", 75.0, 10.0, 20.0, 60.0, 80.0, 5.0, 1.0, 40.0),
        ("stick", 20.0, 8.0, 20.0, 60.0, 80.0, 5.0, 1.0, 40.0),
        ("flux_core", 45.0, 7.0, 18.0, 60.0, 80.0, 5.0, 1.0, 40.0),
    ]:
        db.add(WeldThresholdModel(weld_type=weld_type, angle_target_degrees=a,
            angle_warning_margin=aw, angle_critical_margin=ac,
            thermal_symmetry_warning_celsius=tw, thermal_symmetry_critical_celsius=tc,
            amps_stability_warning=amps, volts_stability_warning=volts, heat_diss_consistency=hd))
    db.commit()


def test_put_threshold_invalidates_cache(client, db, session_factory, seeded_weld_thresholds):
    # seeded_weld_thresholds ensures weld_thresholds has mig row; PUT returns 200 not 404
    # Create session for score endpoint
    session = session_factory(process_type="mig")
    # Get initial score
    r0 = client.get(f"/api/sessions/{session.session_id}/score")
    assert r0.status_code == 200
    spec0 = r0.json().get("active_threshold_spec", {})
    assert spec0.get("angle_target") == 45

    # PUT new threshold
    r1 = client.put("/api/thresholds/mig", json={
        "angle_target_degrees": 50,
        "angle_warning_margin": 6,
        "angle_critical_margin": 16,
        "thermal_symmetry_warning_celsius": 60,
        "thermal_symmetry_critical_celsius": 80,
        "amps_stability_warning": 5,
        "volts_stability_warning": 1,
        "heat_diss_consistency": 40,
    })
    assert r1.status_code == 200

    # Next score must use new value
    r2 = client.get(f"/api/sessions/{session.session_id}/score")
    assert r2.status_code == 200
    spec2 = r2.json().get("active_threshold_spec", {})
    assert spec2.get("angle_target") == 50, "Cache must be invalidated; score should reflect new threshold"
```

```python
# test_scoring_thresholds.py
def test_score_uses_thresholds_for_process_type():
    session = create_session_with_process_type("tig")
    thresholds = get_thresholds(db, "tig")
    features = extract_features(session, angle_target_deg=75)
    score = score_session(session, features, thresholds)
    assert score.rules[1].threshold == 10  # angle_warning for TIG
```

```tsx
// ScorePanel.test.tsx - add test
it('displays threshold callout when active_threshold_spec present', async () => {
  mockFetchScore.mockResolvedValue({
    total: 100,
    rules: [],
    active_threshold_spec: { weld_type: 'mig', angle_target: 45, angle_warning: 5, angle_critical: 15 },
  });
  render(<ScorePanel sessionId="sess_1" />);
  await waitFor(() => expect(screen.getByText(/Evaluated against MIG spec/)).toBeInTheDocument());
});
```

*Why this approach:* Explicit cache invalidation assertion prevents regression. Acceptance criteria 12: automated tests verify API, scoring, callout.

*Verification:*
```
Setup: pytest, jest configured
Action: cd backend && pytest tests/test_thresholds_api.py tests/test_scoring_thresholds.py -v
Expected: All pass, including test_put_threshold_invalidates_cache
Action: cd my-app && npm test -- ScorePanel.test
Expected: Callout test passes
Pass criteria:
  [ ] GET/PUT tests pass
  [ ] test_put_threshold_invalidates_cache: PUT then GET score, assert active_threshold_spec.angle_target changed
  [ ] ScorePanel callout test passes
If it fails: Fixtures for db, client; mock setup
```

*Estimate:* 2h

*Classification:* CRITICAL (test coverage for new behavior)

---

## Risk Heatmap

| Phase.Step | Risk Description | Probability | Impact | Early Warning | Mitigation |
|------------|------------------|-------------|--------|---------------|------------|
| 1.2 | Migration fails; partial migration (UPDATE succeeds, ALTER fails) | Med | High | alembic upgrade error; revision partially applied | Pre-flight: row count (>1000 → manual UPDATE first), migration_preview.sql; test on copy of prod DB |
| 1.4 | Cache not invalidated on PUT → stale scores | Low | Med | Admin saves, score unchanged | invalidate_cache in finally; test_put_threshold_invalidates_cache |
| 1.4 | invalidate_cache race with _load_all (concurrent PUT+GET) | Low | Med | Redundant _load_all; potential stale read | invalidate_cache acquires _load_lock (Step 1.4 fix) |
| 1.4 | Multi-worker: stale thresholds on other workers | Med | High | Admin saves, worker B serves old | Document; backlog shared cache (Redis) |
| 1.4 | Empty weld_thresholds → KeyError | Low | High | 500 on every score | Fallback to hardcoded MIG in _load_all |
| 2.2 | score_session signature change breaks other callers | Low | Med | Import errors, test failures | Optional thresholds; fallback; grep for score_session usages |
| 2.3 | Session missing process_type before backfill | Med | High | KeyError or wrong thresholds | Backfill in same migration; default "mig" in code |
| 3.4 | Form validation bypass (warning > critical) | Low | Low | Invalid DB values | Backend validation mandatory; frontend mirrors |
| 4.1 | generateMicroFeedback regresses for undefined thresholds | Med | Low | Wrong feedback for legacy callers | Fallback to consts when undefined; add unit test |
| 4.2 | Replay passes partial thresholds (thermal hardcoded) | Low | Low | TIG thermal wrong | active_threshold_spec now full; Step 4.2 uses spec |
| 4.2 | Micro-feedback flicker when score loads after frames | Med | Low | Markers jump on timeline | Gate on sessionData && primaryScore; single paint |
| 4.6 | session_factory creates session without frames → test passes for wrong reason | Med | High | test_put_threshold_invalidates_cache 404 or false pass | Explicit fixture: generate_expert_session (has frames) |

---

## Pre-Flight Checklist

### Phase 1 Prerequisites
- [ ] PostgreSQL running, DATABASE_URL set — `psql $DATABASE_URL -c "SELECT 1"` — Fix: start Postgres, set env
- [ ] Alembic at revision 003 — `cd backend && alembic current` — Fix: `alembic upgrade 003`
- [ ] down_revision matches 003 — `grep "revision\|down_revision" alembic/versions/003*.py` — Fix: ensure 004 down_revision = "003_add_score_total"
- [ ] Backend venv active, deps installed — `cd backend && python -c "import fastapi"` — Fix: `pip install -r requirements.txt`
- [ ] No uncommitted migration conflicts — `alembic history` — Fix: resolve branches
- [ ] Migration SQL preview — `alembic upgrade head --sql > migration_preview.sql`; inspect before applying — Fix: review migration_preview.sql
- [ ] **If sessions >1000 rows (staging/prod):** Run manual `UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL`; verify `SELECT COUNT(*) FROM sessions WHERE process_type IS NULL` = 0 — Fix: run UPDATE; retry upgrade

### Phase 2 Prerequisites
- [ ] Phase 1 complete — weld_thresholds table exists — Fix: run Phase 1
- [ ] Step 1.3 complete — SessionModel has process_type — Fix: complete 1.3
- [ ] Sessions have process_type — `SELECT process_type FROM sessions LIMIT 1` — Fix: re-run migration
- [ ] threshold_service returns data — `get_thresholds(db,"mig")`, `get_all_thresholds(db)` — Fix: check seed data
- [ ] extract_features and score_session accept new params — Import check — Fix: complete Steps 2.1, 2.2
- [ ] test_put_threshold_invalidates_cache passes (Step 4.6; run early to verify cache invalidation before Phase 2)

### Phase 3 Prerequisites
- [ ] Backend /api/thresholds returns 200 — `curl /api/thresholds` — Fix: complete Phase 1
- [ ] NEXT_PUBLIC_API_URL or localhost:8000 — Env check — Fix: set for dev
- [ ] my-app builds — `npm run build` — Fix: resolve TypeScript errors
- [ ] No existing /admin route conflicts — Navigate to /admin — Fix: remove conflicting route

### Phase 4 Prerequisites
- [ ] Score API returns active_threshold_spec with thermal/amps/volts/heat_diss — `GET /sessions/{id}/score` — Fix: complete Step 2.3
- [ ] SessionScore type has active_threshold_spec — Type check — Fix: Step 3.1
- [ ] generateMicroFeedback accepts optional param — Signature check — Fix: Step 4.1
- [ ] Replay fetches score before micro-feedback — Code review — Fix: ensure fetch order

---

## Success Criteria

1. **Admin tabs** — User can open `/admin/thresholds` and see MIG|TIG|Stick|Flux Core tabs. Verify: Navigate, inspect DOM. P0.
2. **Edit and save** — User can edit angle/thermal/amps/volts/heat_diss and save; changes persist. Verify: Edit, Save, GET /api/thresholds. P0.
3. **Arc diagram** — Small inline arc next to angle inputs shows target angle. Verify: Visual check. P1.
4. **Validation** — warning > critical shows inline error or 422; angle_target_degrees=0 rejected. Verify: Submit invalid; see error. P0.
5. **GET thresholds** — Returns array keyed by weld_type. Verify: curl /api/thresholds. P0.
6. **Scoring uses thresholds** — Session with process_type=tig scores with TIG thresholds. Verify: Create tig session, score, check rule thresholds. P0.
7. **angle_max_deviation** — Uses configured target. Verify: TIG session with angles; deviation from 75. P0.
8. **Micro-feedback thresholds** — Replay uses configured thresholds (angle + thermal); no visible flicker when score loads after frames. Verify: TIG session replay; angle 75°, thermal 60°C; throttle score API, confirm single paint. P1.
9. **WelderReport callout** — "Evaluated against MIG spec — Target 45° ±5°". Verify: Open WelderReport, see text. P0.
10. **Score API active_threshold_spec** — Response includes weld_type, angle_target, angle_warning, thermal/amps/volts/heat_diss. Verify: GET score, inspect JSON. P0.
11. **Cache** — No DB hit per score. Verify: Log or profile; single threshold fetch per process_type. P1.
12. **Automated tests** — GET/PUT, cache invalidation, scoring, callout covered. Verify: pytest, jest pass. P0.

---

## Progress Tracker

```
| Phase   | Steps | Done | In Progress | Blocked | %   |
|---------|-------|------|-------------|---------|-----|
| Phase 1 | 8     | 0    | 0           | 0       | 0%  |
| Phase 2 | 3     | 0    | 0           | 0       | 0%  |
| Phase 3 | 4     | 0    | 0           | 0       | 0%  |
| Phase 4 | 6     | 0    | 0           | 0       | 0%  |
| TOTAL   | 20    | 0    | 0           | 0       | 0%  |
```

---

## Notes

- **Critique fixes applied (plan-critique-fixes issue):** Step 1.2 pre-flight adds row-count check and migration_preview.sql; Step 1.4 invalidate_cache acquires _load_lock; Step 1.5 rejects angle_target_degrees=0; Step 3.4 form uses parseFloat() without ||0 fallback, isCompleteForm requires angle_target_degrees>0; Step 4.2 gates micro-feedback on sessionData && primaryScore; Step 4.6 includes explicit session_factory fixture.
- **create_session**: Add `process_type` to CreateSessionRequest; default "mig". SessionModel constructor must include it (add in Step 1.2 model update).
- **WeldThresholdModel**: Ensure it is imported in `database/connection` or models __init__ if needed for migration; Alembic autogenerate may require the model to be in scope.
- **PUT response**: Step 1.5 returns single updated threshold; frontend refetches all after save.
- **backfill_score_total.py**: Step 1.8 updates backfill to use get_thresholds and pass angle_target_deg + thresholds. Required because backfill may run after new TIG/stick/flux_core sessions exist; without update, those get scored with MIG constants.
- **Multi-worker**: In-memory cache is process-local. Gunicorn with multiple uvicorn workers will serve stale thresholds until restart. Add shared cache (Redis) to backlog for production.
- **Total estimate**: ~22.25h (Phase 1: 6.25h, Phase 2: 5h, Phase 3: 6h, Phase 4: 5h).

---

## Known Issues & Limitations

- **Multi-worker cache**: Single-process cache invalidates only in the worker that handled the PUT. Other workers retain stale thresholds until restart. For MVP: document; use single worker or add Redis to backlog.
- **Migration compatibility**: Assumes vanilla PostgreSQL. DBs with extensions, read replicas, or custom triggers may need migration adjustments.
- **Large-table migration**: Step 1.2 uses single `UPDATE sessions SET process_type = 'mig'`. On DBs with 100k+ sessions, this may lock the table and cause migration timeout or connection pool exhaustion. For large staging/prod: consider batched UPDATE (e.g. 5k rows per batch) or run during maintenance window.
- **AngleArcDiagram**: Validation limits angle_target to ≤90°; arc path assumes ≤90°.
- **SQLAlchemy 2.0**: Step 1.5 uses `db.query(WeldThresholdModel)`. Consider migrating to `db.execute(select(...))` style when updating SQLAlchemy.

---

## Rollback Procedure

**Partial rollback (after Phase 1 or 2):**
```bash
cd backend && alembic downgrade -1
# Drops weld_thresholds table and process_type column
```

**Full rollback:** Revert code changes; run downgrade above. Restore SessionModel, routes, frontend from git.
