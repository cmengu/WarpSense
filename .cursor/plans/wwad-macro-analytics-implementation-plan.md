# WWAD Macro-Level Analytics Dashboard — Implementation Plan

**Time Budget:** 180+ minutes for plan creation  
**Status:** Draft  
**Created:** 2025-02-17  
**Issue Reference:** `.cursor/issues/wwad-macro-analytics-dashboard.md`  
**Exploration Reference:** `.cursor/explore/wwad-macro-analytics-exploration.md`

---

## Critical vs Non-Critical Step Classification

| Step | Type | Critical? | Reason |
|------|------|-----------|--------|
| 1.1 | Prototype | No | Validation only |
| 1.2 | Schema | Yes | Migration affects DB |
| 1.3 | Model | No | Simple column add |
| 1.4 | Backend | Yes | Persistence logic |
| 1.5 | Script | Yes | Backfill correctness |
| 1.6 | Ops | No | Run script |
| 1.7 | Backend | No | Add field to payload |
| 2.1 | Types | No | Pydantic model |
| 2.2 | Service | Yes | Core aggregation logic |
| 2.3 | Route | Yes | API contract, security |
| 2.4 | Config | No | Router registration |
| 2.5 | Validation | No | Query validation |
| 2.6 | Index | No | Verification |
| 2.7 | Test | No | Unit test |
| 2.8 | Test | No | API test |
| 2.9 | Docs | No | OpenAPI |
| 3.1 | Types | No | TypeScript types |
| 3.2 | API | No | Fetch function |
| 3.3 | Component | Yes | New UX component |
| 3.4 | Transform | Yes | Data shape mapping |
| 3.5 | Page | Yes | Main user entry |
| 3.6 | Review | No | Grep check |
| 3.7 | CSS | No | Responsive |
| 3.8 | CI | No | Lint rule |
| 3.9 | Test | No | Component test |
| 4.1 | Util | No | CSV helpers |
| 4.2 | UI | No | Date filter |
| 4.3 | Feature | Yes | Export flow |
| 4.4 | Nav | No | Link |
| 4.5 | UX | No | Error handling |
| 4.6 | UX | No | Empty state |
| 4.7 | A11y | No | Keyboard |

**Summary:** Critical steps needing code review: 1.2, 1.4, 1.5, 2.2, 2.3, 3.3, 3.4, 3.5, 4.3 (9 steps).

---

## Phase 0: MANDATORY PRE-PLANNING THINKING SESSION

### A. Exploration Review and Synthesis (10 minutes)

#### 1. Core approach

**In one sentence:** Persist `score_total` on sessions, add `GET /api/sessions/aggregate` that queries metadata + score_total only (no frames), and build a supervisor dashboard at `/supervisor` with KPI tiles, trend chart, calendar heatmap, and CSV export — all orthogonal to TorchViz3D, HeatmapPlate3D, and micro-feedback.

**Key decisions:**
- Add `score_total INTEGER NULL` column; persist via lazy write-through in `GET /sessions/{id}/score` when computed, plus backfill script for existing sessions.
- Aggregate endpoint queries sessions by date range (COMPLETE only); uses metadata + score_total; never loads frames.
- Route: `/supervisor`. Filter: COMPLETE sessions. KPIs: avg_score, session_count, top_performer, rework_count (score < 60).
- Calendar heatmap: sessions per day (activity view).
- Orthogonality: zero imports from 3D or micro-feedback in supervisor module.

**Why this approach:** Batch scoring 500 sessions with frames takes ~25–100s (prototype confirmed). Persisting scores makes aggregate queries fast (< 3s). Metadata-only aggregation avoids OOM and keeps WWAD decoupled from frame-heavy paths.

#### 2. Major components

| Component | Purpose |
|-----------|---------|
| **score_total persistence** | Avoid loading frames for aggregation; enable avg_score, rework_count KPIs |
| **Aggregate service** | Business logic: date filter, group by operator/weld_type, compute KPIs from metadata + score_total |
| **Aggregate route** | HTTP API: `GET /api/sessions/aggregate?date_start=&date_end=` |
| **Supervisor page** | Frontend dashboard: fetch aggregate API, render KPIs, charts, calendar, export |
| **CalendarHeatmap** | Custom GitHub-style grid: sessions per day; 7 cols × weeks |
| **export.ts** | generateCSV, downloadCSV for session summary export |
| **Types (aggregate.ts)** | AggregateKPIResponse, SessionSummary, etc. |

#### 3. Data flow

```
Input: date_start, date_end (query params)
  ↓
Transform: Backend queries SessionModel (metadata + score_total) WHERE status='complete' AND start_time IN range
  ↓
Process: aggregate_service computes kpis (avg_score, session_count, top_performer, rework_count), trend (date→value), calendar (date→sessions_count)
  ↓
Output: { kpis, trend, calendar, sessions? } → Frontend renders MetricCard, LineChart, CalendarHeatmap, Export CSV
```

#### 4. Biggest risks

1. **Batch scoring perf** — If we don't persist, aggregate would load 500×1500 frames; exploration says persist.
2. **Orthogonality break** — Accidentally importing 3D/micro-feedback; mitigate with code review and no-import rule.
3. **Migration/backfill failure** — New column or backfill script errors; mitigate with dev testing, batched backfill.
4. **Wrong KPIs** — Supervisors want different metrics; mitigate by validating with stakeholder; document assumptions.
5. **Empty calendar UX** — Sparse data looks confusing; mitigate with tooltip, "No activity" label.

#### 5. What exploration did NOT answer

- **Gap 1:** Where exactly does session transition to COMPLETE? (Dev seed creates COMPLETE; no PATCH endpoint. Plan: lazy persistence in get_session_score + backfill.)
- **Gap 2:** Exact timezone for date_start/date_end — UTC vs user local. (Assumption: **UTC for API**; frontend passes YYYY-MM-DD strings; backend interprets as UTC midnight; date_end is **inclusive**. Frontend displays local.)
- **Gap 3:** Export row limit — exploration says 90 days or 1000 sessions; need to implement and document.

---

### B. Dependency Brainstorm (10 minutes)

#### Major work items (before ordering)

1. Add `score_total` column (migration)
2. Update SessionModel to include score_total
3. Add lazy persistence in get_session_score (compute + UPDATE when null)
4. Create backfill_score_total.py script
5. Create aggregate_service.py
6. Create aggregate route
7. Add AggregateKPIResponse Pydantic model
8. Register aggregate router in main.py
9. Create types/aggregate.ts
10. Add fetchAggregateKPIs to api.ts
11. Create CalendarHeatmap component
12. Create export.ts (generateCSV, downloadCSV)
13. Create supervisor page
14. Add date range filter UI
15. Add Export CSV button
16. Add nav link to /supervisor
17. Run prototype_aggregate_perf.py (verify before impl)
18. Unit tests for aggregate_service
19. API integration test for aggregate endpoint
20. Frontend E2E or component tests
21. Orthogonality grep / lint check

#### Dependency graph

```
Migration (1) ──→ SessionModel update (2)
                        ↓
get_session_score persistence (3) ←── extract_features, score_session
                        ↓
Backfill script (4)
                        ↓
aggregate_service (5) ──→ aggregate route (6) ──→ Pydantic model (7)
                        ↓                              ↓
                        └──────────────────────────────┴──→ main.py (8)

Frontend:
types/aggregate.ts (9) ──→ api.ts fetchAggregateKPIs (10)
CalendarHeatmap (11) ──┐
export.ts (12) ────────┼──→ supervisor page (13) ──→ date filter (14), Export (15)
MetricCard/LineChart ──┘
```

**Critical path:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 13 → 14 → 15

**Bottlenecks:** Migration (blocks backend), aggregate_service (blocks route), supervisor page (blocks frontend value)

**Parallelizable:** (11) CalendarHeatmap, (12) export.ts can be done in parallel with (10) api.ts after types exist.

---

### C. Risk-Based Planning (10 minutes)

| Risk | Probability | Impact | Mitigation in plan |
|------|-------------|--------|--------------------|
| Batch scoring slow | 70% | High | Persist score_total; never compute on aggregate |
| Orthogonality break | 30% | High | Step: Grep for forbidden imports; no TorchViz3D/HeatmapPlate3D |
| Migration failure | 20% | Medium | Test migration on dev; rollback script |
| Backfill OOM | 25% | Medium | Batch backfill (e.g. 10 at a time); profile |
| Wrong KPIs | 30% | Medium | Validate with stakeholder; document in plan |
| Empty calendar UX | 40% | Low | Empty state, tooltip, "No activity" |
| Export timeout | 25% | Medium | Limit 90 days or 1000 sessions |
| Date range validation | 15% | Low | Backend validation; 400 on invalid |
| Aggregate query slow | 20% | High | Index on start_time (exists); limit range |
| Timezone confusion | 25% | Low | Document UTC; frontend local display |

**Failure modes:**

1. **If migration fails:** Detection: `alembic upgrade head` errors. Response: Check PostgreSQL version, constraints. Recovery: Downgrade, fix, retry.
2. **If backfill fails:** Detection: Script exits non-zero or partial update. Response: Check frames exist, extract_features doesn't error. Recovery: Re-run with --dry-run, fix data.
3. **If aggregate returns 500:** Detection: Frontend shows error. Response: Check backend logs for traceback. Recovery: Fix route; add try/except.
4. **If CalendarHeatmap breaks layout:** Detection: Overflow on small screen. Response: Responsive grid, min-width. Recovery: Adjust CSS.
5. **If CSV export fails:** Detection: No download or empty file. Response: Check generateCSV logic, blob creation. Recovery: Add logging, test with small dataset.
6. **If get_session_score doesn't persist:** Detection: score_total stays null after /score call. Response: Verify UPDATE in route. Recovery: Add persistence logic.
7. **If date_start > date_end:** Detection: Empty or wrong data. Response: Swap or 400. Recovery: Backend validation.
8. **If no sessions in range:** Detection: Empty KPIs. Response: Empty state UI. Recovery: "No sessions in date range" message.
9. **If forbidden import added:** Detection: Grep/lint. Response: Remove import. Recovery: Enforce in CI.
10. **If aggregate timeout:** Detection: Request > 10s. Response: Add limit, optimize query. Recovery: Add index, reduce scope.

---

## 1. Phase Breakdown Strategy

### A. Natural breaking points

| Boundary | User can | Ship alone? | User value? | Independently testable? | Logical stop? |
|----------|----------|-------------|-------------|------------------------|--------------|
| After migration + persistence | Backend has score_total; future scores persisted | Yes | No (internal) | Yes | Yes |
| After aggregate API | API returns KPIs, trend, calendar | Yes | No (API only) | Yes | Yes |
| After supervisor page | User sees dashboard with real data | Yes | Yes | Yes | Yes |
| After date filter | User can change date range | Yes | Yes | Yes | Yes |
| After CSV export | User can download report | Yes | Yes | Yes | Yes |

**Valid phase boundaries:** Migration+persistence (foundation), Aggregate API (backend complete), Supervisor page (MVP), Date filter + Export (full feature).

### B. Phase design

**Phase 1: Foundation — Score persistence and backfill**  
- **Goal:** Sessions have score_total; get_session_score persists when computed; backfill existing.  
- **User value:** None directly (enables Phase 2).  
- **Why first:** Aggregate API cannot return score-based KPIs without this.  
- **Estimated effort:** 6–8 hours  
- **Risk level:** 🟡 Medium (migration, backfill)  
- **Major steps:** Migration, SessionModel update, lazy persistence in get_session_score, backfill script, run backfill  

**Phase 2: Backend — Aggregate API**  
- **Goal:** GET /api/sessions/aggregate returns KPIs, trend, calendar for date range.  
- **User value:** API consumers can build supervisor views.  
- **Why second:** Frontend needs this API.  
- **Estimated effort:** 8–10 hours  
- **Risk level:** 🟢 Low  
- **Major steps:** aggregate_service, aggregate route, Pydantic models, register router, tests  

**Phase 3: Frontend — Supervisor dashboard**  
- **Goal:** User sees /supervisor with KPI tiles, trend chart, calendar heatmap.  
- **User value:** At-a-glance team performance.  
- **Why third:** Depends on Phase 2.  
- **Estimated effort:** 8–10 hours  
- **Risk level:** 🟢 Low  
- **Major steps:** types, api client, CalendarHeatmap, supervisor page, DashboardLayout reuse  

**Phase 4: Extensions — Date filter and CSV export**  
- **Goal:** User can filter date range and export CSV.  
- **User value:** Flexible analysis, reporting for meetings.  
- **Why fourth:** Builds on Phase 3.  
- **Estimated effort:** 4–6 hours  
- **Risk level:** 🟢 Low  
- **Major steps:** date filter UI, export.ts, Export button, nav link  

### C. Phase dependency graph

```
Phase 1 (Foundation)
  ↓
Phase 2 (Aggregate API)
  ↓
Phase 3 (Supervisor dashboard)
  ↓
Phase 4 (Date filter + Export)
```

**Critical path:** Phase 1 → 2 → 3 → 4 ≈ 26–34 hours total.

### D. Phase success criteria

**Phase 1 done when:**
- [ ] Migration applied; score_total column exists
- [ ] get_session_score persists score_total when computed for COMPLETE session
- [ ] Backfill script runs without error; existing COMPLETE sessions have score_total
- [ ] All Phase 1 verification tests pass

**Phase 2 done when:**
- [ ] GET /api/sessions/aggregate returns 200 with kpis, trend, calendar
- [ ] Response time < 3s for 500 sessions
- [ ] No frames loaded in aggregate code path
- [ ] All Phase 2 verification tests pass

**Phase 3 done when:**
- [ ] /supervisor renders without error
- [ ] KPI tiles, trend chart, calendar visible with real data
- [ ] No imports from TorchViz3D, HeatmapPlate3D, HeatMap (thermal)
- [ ] SupervisorPage component test passes (automated verification)
- [ ] All Phase 3 verification tests pass

**Phase 4 done when:**
- [ ] Date range filter updates data
- [ ] Export CSV downloads valid file
- [ ] Nav link to /supervisor exists
- [ ] Truncation alert shown when sessions_truncated
- [ ] E2E test (date filter + export) passes
- [ ] All Phase 4 verification tests pass

---

## 2. Step Definition

---

## Phase 1 — Foundation: Score Persistence and Backfill

**Goal:** Sessions have score_total; scores persist when computed; existing sessions backfilled.

**Time estimate:** 6–8 hours  
**Risk level:** 🟡 Medium

---

### Step 1.1: Run prototype_aggregate_perf.py to baseline performance — *Critical: Validates persistence decision*

**Why critical:** Confirms we must persist score_total; prevents implementing batch-on-request by mistake.

**Context:** The exploration concluded that batch scoring 500 sessions would take 25–100s. This step runs the existing prototype to get real numbers on the current DB. If metadata-only is fast and batch scoring is slow, we proceed with persistence.

**Subtasks:**
- [ ] cd backend && python scripts/prototype_aggregate_perf.py
- [ ] Record metadata-only query time (expect < 100 ms)
- [ ] Record batch score time for 2, 5, 10 sessions
- [ ] Confirm extrapolation shows 500 sessions would exceed 3s

**✓ Verification test:**
- Setup: DB seeded (`curl -X POST http://localhost:8000/api/dev/seed-mock-sessions`), backend not required for script
- Action: Run prototype script from backend/
- Expected: Output shows "RECOMMENDATION: Persist score_total column" or similar
- Pass: Script completes; metadata query < 100ms; batch scoring time increases with session count

**Time estimate:** 0.5 hours

---

### Step 1.2: Create Alembic migration for score_total column — *Critical: Schema change*

**Why critical:** Adds new column; affects SessionModel and all session queries.

**Context:** Sessions table needs `score_total INTEGER NULL` to store precomputed scores. Nullable because existing sessions and future sessions before first score computation will have NULL. Aggregate will exclude NULL from avg_score but include in session_count.

**Full code example:**

```python
"""Add score_total to sessions for WWAD aggregate performance.

Revision ID: 003_add_score_total
Revises: 002_add_disable_sensor_continuity_checks
Create Date: 2025-02-17

"""

from alembic import op
import sqlalchemy as sa

revision = "003_add_score_total"
down_revision = "002_disable_sensor_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("score_total", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "score_total")
```

**Files:** Create `backend/alembic/versions/003_add_score_total.py`

**Note:** down_revision must match latest migration (`002_disable_sensor_checks` from `002_add_disable_sensor_continuity_checks.py`).

**Pre-production: Create pre-migration backup**

Before running migration on production, substitute the actual database name from `DATABASE_URL` (e.g. `shipyard_welding` or `postgres`). Do not use a literal `production_db` placeholder.

```bash
mkdir -p ./backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
# Extract DB name from DATABASE_URL (e.g. postgresql://user:pass@host:5432/DBNAME)
DB_NAME=$(echo $DATABASE_URL | sed -n 's|.*/\([^/?]*\).*|\1|p' || echo "postgres")
pg_dump -h localhost -U postgres -d "$DB_NAME" > ./backups/backup_${TIMESTAMP}.sql
if [ $? -eq 0 ]; then
  echo "✅ Backup: backup_${TIMESTAMP}.sql ($(du -h ./backups/backup_${TIMESTAMP}.sql | cut -f1))"
else
  echo "❌ Backup failed - ABORT MIGRATION"
  exit 1
fi
```

**Verification on staging:** Run `alembic downgrade -1` then `alembic upgrade head` on a staging copy before prod.

**✓ Verification test:**
- Setup: PostgreSQL running, alembic configured
- Action: `cd backend && alembic upgrade head`
- Expected: Migration applies; no errors
- Action: `alembic downgrade -1` then `alembic upgrade head`
- Pass: Round-trip succeeds; `\d sessions` in psql shows score_total integer nullable

**Time estimate:** 1 hour

---

### Step 1.3: Add score_total to SessionModel and Session Pydantic model

**What:** Add `score_total` column to SQLAlchemy SessionModel and `score_total` field to Pydantic Session model.

**Why:** ORM and API must know about the new field.

**Explicit edits:**

**a) `backend/models/session.py`** — add field to Session Pydantic model:

```python
# Add after line with disable_sensor_continuity_checks (around line 75):
    score_total: Optional[int] = Field(
        None,
        description="Precomputed total score (persisted on first score computation).",
    )
```

**b) `backend/database/models.py`** — add column and round-trip:

- **SessionModel class:** Add column (after `version`):
```python
    score_total = Column(Integer, nullable=True)
```

- **from_pydantic:** Add to cls() call:
```python
    score_total=getattr(session, "score_total", None),
```

- **to_pydantic:** Add to Session() call:
```python
    score_total=self.score_total,
```

**Subtasks:**
- [ ] Add score_total to Session (Pydantic) in backend/models/session.py
- [ ] Add score_total column to SessionModel in backend/database/models.py
- [ ] Add score_total to from_pydantic and to_pydantic
- [ ] Ensure get_session response includes score_total

**✓ Verification test:**
- Setup: Migration applied
- Action: Query a session via API or test; check response has score_total (null for now)
- Pass: No AttributeError; score_total present in session dict/model

**Time estimate:** 0.5 hours

---

### Step 1.4: Implement lazy persistence in get_session_score — *Critical: Score write-through*

**Why critical:** Ensures scores are persisted when computed; enables fast aggregation without loading frames.

**Context:** When `GET /api/sessions/{id}/score` is called, we load session with frames, compute score. If session is COMPLETE and has frames and score_total is NULL, we UPDATE the session row with the computed score. Subsequent aggregate queries can use score_total without recomputing.

**Full code example:**

```python
# In backend/routes/sessions.py, modify get_session_score:

@router.get("/sessions/{session_id}/score")
async def get_session_score(
    session_id: str,
    db: OrmSession = Depends(get_db),
):
    """
    Get rule-based score for a welding session.
    Persists score_total when computed (lazy write-through) for COMPLETE sessions.
    """
    session_model = (
        db.query(SessionModel)
        .options(joinedload(SessionModel.frames))
        .filter_by(session_id=session_id)
        .first()
    )
    if not session_model:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_model.to_pydantic()
    features = extract_features(session)
    score = score_session(session, features)

    # Lazy persistence: if COMPLETE and score_total is null, persist
    if (
        session_model.status == SessionStatus.COMPLETE.value
        and session_model.score_total is None
        and session_model.frame_count > 0
    ):
        session_model.score_total = score.total
        db.commit()

    return score.model_dump()
```

**Assumptions:** SessionModel has score_total; db.commit() is valid (route uses get_db which yields session with auto-close). If sessions router uses a different pattern (e.g. no explicit commit), ensure the session is committed.

**✓ Verification test:**
- Setup: Seeded DB with sess_expert_001, sess_novice_001 (COMPLETE, have frames)
- Action: `GET /api/sessions/sess_expert_001/score`
- Expected: 200, { total: N, rules: [...] }; DB shows score_total updated for sess_expert_001
- Action: Call again
- Expected: score_total unchanged (idempotent)
- Pass: First call persists; second call doesn't overwrite

**Time estimate:** 1.5 hours

---

### Step 1.5: Create backfill_score_total.py script — *Critical: Populates existing data*

**Why critical:** Existing COMPLETE sessions have no score_total; backfill is required for aggregate to return score-based KPIs.

**Context:** Script queries sessions with status='complete' and frame_count > 0 and score_total IS NULL. Processes in batches of 10 (limit/offset) to avoid OOM when hundreds of sessions exist. For each batch, loads with frames, extract_features, score_session, UPDATE score_total.

**Full code example:**

```python
#!/usr/bin/env python3
"""
Backfill score_total for COMPLETE sessions that have frames but no score.
Run from backend/: python scripts/backfill_score_total.py

Batches in groups of 10 to avoid memory spike when many sessions need backfill.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import joinedload
from database.connection import SessionLocal
from database.models import SessionModel
from features.extractor import extract_features
from scoring.rule_based import score_session

BATCH_SIZE = 10


def main():
    db = SessionLocal()
    try:
        base_query = (
            db.query(SessionModel)
            .filter(
                SessionModel.status == "complete",
                SessionModel.frame_count > 0,
                SessionModel.score_total.is_(None),
            )
        )
        total = base_query.count()
        print(f"Found {total} sessions to backfill")
        processed = 0
        while True:
            batch = (
                db.query(SessionModel)
                .options(joinedload(SessionModel.frames))
                .filter(
                    SessionModel.status == "complete",
                    SessionModel.frame_count > 0,
                    SessionModel.score_total.is_(None),
                )
                .order_by(SessionModel.session_id)
                .limit(BATCH_SIZE)
                .all()
            )
            if not batch:
                break
            for s in batch:
                session = s.to_pydantic()
                features = extract_features(session)
                score = score_session(session, features)
                s.score_total = score.total
                print(f"  {s.session_id}: score_total={score.total}")
            db.commit()
            processed += len(batch)
        print(f"Done ({processed} sessions)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

**Files:** Create `backend/scripts/backfill_score_total.py`

**✓ Verification test:**
- Setup: Migration applied; seeded DB with sessions that have score_total=NULL
- Action: Run `python scripts/backfill_score_total.py`
- Expected: Sessions updated; no errors
- Pass: SELECT session_id, score_total FROM sessions WHERE status='complete' shows non-null score_total

**Time estimate:** 1.5 hours

---

### Step 1.6: Run backfill on dev database

**What:** Execute backfill script against dev DB.

**Why:** Ensures aggregate API will have data to aggregate.

**Subtasks:**
- [ ] Run backfill_score_total.py
- [ ] Run automated verification (see below)
- [ ] Document in README or SETUP how to run backfill for new envs

**Automated backfill verification:** Add `--verify` mode to backfill script or create `backend/scripts/verify_backfill.py`:

```python
#!/usr/bin/env python3
"""Verify all COMPLETE sessions with frames have score_total. Exit 1 if any null."""
import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))
from sqlalchemy import text
from database.connection import SessionLocal

def main():
    db = SessionLocal()
    try:
        r = db.execute(text(
            "SELECT COUNT(*) FROM sessions WHERE status='complete' AND frame_count > 0 AND score_total IS NULL"
        )).scalar()
        if r and r > 0:
            print(f"❌ {r} COMPLETE session(s) with frames have null score_total")
            sys.exit(1)
        print("✅ All COMPLETE sessions with frames have score_total")
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

**CI integration:** Add `python scripts/verify_backfill.py` to post-backfill check (e.g. in deploy or manual run); exit 1 blocks success criterion.

**✓ Verification test:**
- Action: Run backfill; run `python scripts/verify_backfill.py`
- Pass: Exit 0; "All COMPLETE sessions with frames have score_total"

**Time estimate:** 0.5 hours

---

### Step 1.7: Verify get_session response includes score_total

**What:** Ensure GET /api/sessions/{id} returns score_total in session payload.

**Why:** Consistency; clients may need it.

**Files:** Modify session_payload in get_session (sessions.py) to include score_total.

**Exact edit:** In the session_payload construction (or Session model serialization), add:
```python
"score_total": getattr(session_model, 'score_total', None),
```
Insert after any existing fields such as `disable_sensor_continuity_checks`. Ensure this appears in the dict returned by GET /api/sessions/{id}.

**✓ Verification test:**
- Action: GET /api/sessions/sess_expert_001
- Expected: Response includes "score_total": N (or null)
- Pass: Field present

**Time estimate:** 0.25 hours

---

**Phase 1 total:** ~6.5 hours

**Phase 1 completion criteria:**
- [ ] All steps 1.1–1.7 completed
- [ ] All verification tests pass
- [ ] Ready for Phase 2

---

## Phase 2 — Backend: Aggregate API

**Goal:** GET /api/sessions/aggregate returns KPIs, trend, calendar.

**Time estimate:** 8–10 hours  
**Risk level:** 🟢 Low

---

### Step 2.1: Create AggregateKPIResponse Pydantic model — *Critical: API contract*

**Why critical:** Defines response shape; frontend types will mirror this.

**Context:** Response has kpis (avg_score, session_count, top_performer, rework_count), trend (list of {date, value}), calendar (list of {date, value}), optional sessions for export.

**Full code example:**

```python
# backend/models/aggregate.py (or in routes/aggregate.py)

from pydantic import BaseModel
from typing import Optional


class AggregateKPIs(BaseModel):
    avg_score: Optional[float]  # None if no scored sessions
    session_count: int
    top_performer: Optional[str]  # operator_id with best avg
    rework_count: int  # sessions with score_total < 60


class TrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    value: float


class CalendarDay(BaseModel):
    date: str  # YYYY-MM-DD
    value: int  # sessions count


class SessionSummary(BaseModel):
    session_id: str
    operator_id: str
    weld_type: str
    start_time: str  # ISO
    score_total: Optional[int]
    frame_count: int


class AggregateKPIResponse(BaseModel):
    kpis: AggregateKPIs
    trend: list[TrendPoint]
    calendar: list[CalendarDay]
    sessions: Optional[list[SessionSummary]] = None  # for export
    sessions_truncated: bool = False  # true when include_sessions and >1000 sessions; frontend shows alert
```

**Files:** Create `backend/models/aggregate.py` or add to existing models.

**✓ Verification test:**
- Action: Import and instantiate AggregateKPIResponse with sample data
- Pass: Pydantic validates; model_dump() produces expected JSON

**Time estimate:** 0.5 hours

---

### Step 2.2: Create aggregate_service.py with get_aggregate_kpis — *Critical: Business logic*

**Why critical:** Core aggregation logic; must be correct and fast.

**Context:** Query sessions in date range, status=complete. Use metadata + score_total only. Compute: avg_score (exclude null), session_count, top_performer (operator with best avg score among those with score), rework_count (score_total < 60). Trend: group by date, avg score per day. Calendar: group by date, count sessions per day.

**Full code example:**

```python
# backend/services/aggregate_service.py

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as OrmSession

from database.models import SessionModel


def get_aggregate_kpis(
    db: OrmSession,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    include_sessions: bool = False,
) -> dict:
    """
    Aggregate sessions by date range. COMPLETE only.
    Returns kpis, trend, calendar; optionally sessions for export.
    """
    # PostgreSQL coerces YYYY-MM-DD to midnight UTC for timestamp comparison.
    # date_end inclusive: start_time <= date_end would exclude sessions later that day;
    # use start_time < (date_end + 1 day).
    q = db.query(SessionModel).filter(SessionModel.status == "complete")
    if date_start:
        q = q.filter(SessionModel.start_time >= date_start)
    if date_end:
        de = datetime.fromisoformat(date_end).date() if isinstance(date_end, str) else date_end
        end_exclusive = datetime.combine(de + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
        q = q.filter(SessionModel.start_time < end_exclusive)
    sessions = q.all()

    # KPIs — defensive: never divide by zero; avg_score only when scored list non-empty
    scored = [s for s in sessions if s.score_total is not None]
    if len(scored) == 0:
        avg_score = None
    else:
        total_score = sum(s.score_total for s in scored)
        avg_score = total_score / len(scored)  # Safe: len(scored) > 0
    session_count = len(sessions)
    by_operator = defaultdict(list)
    for s in scored:
        by_operator[s.operator_id].append(s.score_total)
    top_performer = None
    if by_operator:
        # Tie-break: when two operators have same avg score, pick lexicographically smallest operator_id (deterministic)
        best_avg = max(sum(v) / len(v) for v in by_operator.values())
        candidates = [op for op, scores in by_operator.items() if sum(scores) / len(scores) == best_avg]
        top_performer = min(candidates) if candidates else None
    rework_count = sum(1 for s in scored if s.score_total < 60)

    # Trend: avg score by date (YYYY-MM-DD)
    by_date_score = defaultdict(list)
    for s in scored:
        dt = s.start_time.date() if hasattr(s.start_time, 'date') else s.start_time
        key = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)[:10]
        by_date_score[key].append(s.score_total)
    trend = [
        {"date": d, "value": sum(v) / len(v)}
        for d, v in sorted(by_date_score.items())
    ]

    # Calendar: sessions per day
    by_date_count = defaultdict(int)
    for s in sessions:
        dt = s.start_time.date() if hasattr(s.start_time, 'date') else s.start_time
        key = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)[:10]
        by_date_count[key] += 1
    calendar = [{"date": d, "value": c} for d, c in sorted(by_date_count.items())]

    result = {
        "kpis": {
            "avg_score": round(avg_score, 1) if avg_score is not None else None,
            "session_count": session_count,
            "top_performer": top_performer,
            "rework_count": rework_count,
        },
        "trend": trend,
        "calendar": calendar,
        "sessions_truncated": False,
    }
    if include_sessions:
        # Cap at 1000 sessions to avoid OOM on backend and client; prevents memory issues on export
        sessions_list = sessions[:1000]
        result["sessions"] = [
            {
                "session_id": s.session_id,
                "operator_id": s.operator_id,
                "weld_type": s.weld_type,
                "start_time": s.start_time.isoformat() if s.start_time else "",
                "score_total": s.score_total,
                "frame_count": s.frame_count,
            }
            for s in sessions_list
        ]
        # Include truncated flag so frontend can show prominent alert
        result["sessions_truncated"] = len(sessions) > 1000
    return result
```

**Timezone:** `s.start_time.date()` returns the date in the session's timezone. **Assumption:** All `start_time` values are stored in UTC. If your DB stores local time, add explicit `s.start_time.astimezone(timezone.utc).date()` before grouping. Document in backend README or aggregate_service docstring.

**✓ Verification test:**
- Setup: DB with 2+ COMPLETE sessions with score_total, different dates
- Action: Call get_aggregate_kpis with date range covering them
- Expected: kpis.avg_score correct, session_count=2, trend and calendar have entries
- Pass: Numbers match manual calculation

**Time estimate:** 2 hours

---

### Step 2.3: Create aggregate route GET /api/sessions/aggregate — *Critical: API endpoint*

**Why critical:** Public API; security and contract matter.

**Context:** Parse date_start, date_end from query params (ISO date). Validate: date_start <= date_end; limit to 90 days if needed. Call aggregate_service. Return AggregateKPIResponse. Handle empty range.

**Full code example:**

```python
# backend/routes/aggregate.py

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models.aggregate import AggregateKPIResponse
from routes.sessions import get_db
from services.aggregate_service import get_aggregate_kpis


router = APIRouter()


@router.get("/sessions/aggregate", response_model=AggregateKPIResponse)
async def get_sessions_aggregate(
    date_start: Optional[str] = Query(None, description="Start date YYYY-MM-DD (UTC); inclusive"),
    date_end: Optional[str] = Query(None, description="End date YYYY-MM-DD (UTC); inclusive"),
    include_sessions: bool = Query(False, description="Include session list for export"),
    db=Depends(get_db),
):
    """
    Aggregate session KPIs for supervisor dashboard.
    COMPLETE sessions only. Uses metadata + score_total; no frame loading.

    Timezone: All dates (date_start, date_end) are interpreted as UTC. date_end is inclusive:
    sessions with start_time on date_end (any time that day) are included. Backend uses
    start_time < (date_end + 1 day) for the upper bound.
    """
    # Default: last 7 days
    now = datetime.now(timezone.utc)
    if not date_end:
        date_end = now.date().isoformat()
    if not date_start:
        date_start = (now - timedelta(days=7)).date().isoformat()

    # Validate
    try:
        ds = datetime.fromisoformat(date_start).date()
        de = datetime.fromisoformat(date_end).date()
    except ValueError:
        raise HTTPException(400, "Invalid date format; use YYYY-MM-DD")
    if ds > de:
        raise HTTPException(400, "date_start must be <= date_end")

    # Limit 90 days
    if (de - ds).days > 90:
        raise HTTPException(400, "Date range must be <= 90 days")

    data = get_aggregate_kpis(db, date_start=ds.isoformat(), date_end=de.isoformat(), include_sessions=include_sessions)
    return AggregateKPIResponse(**data)
```

**Note:** Use the same get_db pattern as sessions.py (SessionLocal, yield, close). HTTPException from fastapi.

**✓ Verification test:**
- Setup: Backend running, seeded DB
- Action: GET /api/sessions/aggregate?date_start=2025-02-01&date_end=2025-02-17
- Expected: 200, JSON with kpis, trend, calendar
- Action: GET with date_start > date_end
- Expected: 400
- Pass: Valid range returns data; invalid returns 400

**Time estimate:** 1.5 hours

---

### Step 2.4: Register aggregate router in main.py

**What:** Include aggregate router with /api prefix. **CRITICAL: Register aggregate_router BEFORE sessions_router** so that `/api/sessions/aggregate` matches the aggregate route rather than `/api/sessions/{session_id}` with session_id="aggregate" (which would return 404).

**Why:** Exposes the endpoint. Route order matters: FastAPI matches first-registered route; if sessions_router is first, `/api/sessions/aggregate` is interpreted as session_id="aggregate".

**Files:** Modify `backend/main.py`

```python
from routes.aggregate import router as aggregate_router
from routes.sessions import router as sessions_router
# ...
# Aggregate BEFORE sessions (so /api/sessions/aggregate matches)
app.include_router(aggregate_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
```

**✓ Verification test:**
- Action: GET http://localhost:8000/api/sessions/aggregate
- Pass: 200 (or 404 if route not found before — after fix, 200)

**Time estimate:** 0.25 hours

---

### Step 2.5: Add date range validation and limit (90 days)

**What:** Ensure backend rejects invalid ranges and limits to 90 days.

**Why:** Prevent unbounded queries and export.

**Note:** Already included in Step 2.3. If not, add validation.

**✓ Verification test:**
- Action: GET with range > 90 days
- Expected: 400
- Pass: Rejected

**Time estimate:** 0.25 hours (if not in 2.3)

---

### Step 2.6: Add start_time index check (already exists per 001_initial_schema)

**What:** Verify idx_sessions_start_time exists.

**Why:** Aggregate query filters by start_time; index required for performance.

**Subtasks:**
- [ ] Grep alembic for idx_sessions_start_time
- [ ] If missing, add in migration

**✓ Verification test:**
- Action: EXPLAIN SELECT ... WHERE start_time BETWEEN ... 
- Pass: Uses index

**Time estimate:** 0.25 hours

---

### Step 2.7: Write unit test for aggregate_service

**What:** Test get_aggregate_kpis with mocked DB or test DB.

**Why:** Regression protection.

**Files:** Create `backend/tests/test_aggregate_service.py`

**Minimal fixture/arrange pattern:**

```python
# backend/tests/test_aggregate_service.py

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.models import SessionModel
from services.aggregate_service import get_aggregate_kpis


@pytest.fixture
def db_session():
    """In-memory SQLite session for service tests (no PostgreSQL required)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()  # Prevent state bleed between tests
        db.close()


def test_aggregate_kpis_empty(db_session):
    """Arrange: no sessions. Act: get_aggregate_kpis. Assert: zeros/empty."""
    result = get_aggregate_kpis(db_session, date_start="2025-02-01", date_end="2025-02-17")
    assert result["kpis"]["session_count"] == 0
    assert result["kpis"]["avg_score"] is None
    assert result["trend"] == []
    assert result["calendar"] == []


def test_aggregate_kpis_zero_sessions_all_null_score(db_session):
    """Edge: sessions with score_total=NULL — avg_score must be None, no division by zero."""
    s = SessionModel(
        session_id="sess_null",
        operator_id="op_a",
        start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status="complete",
        frame_count=10,
        score_total=None,  # Not yet scored
    )
    db_session.add(s)
    db_session.commit()
    result = get_aggregate_kpis(db_session, date_start="2025-02-01", date_end="2025-02-17")
    assert result["kpis"]["session_count"] == 1
    assert result["kpis"]["avg_score"] is None
    assert result["kpis"]["rework_count"] == 0
    assert result["trend"] == []
    assert result["calendar"] != []


def test_aggregate_kpis_two_sessions(db_session):
    """Arrange: 2 sessions (different operators, dates, score_total). Act: get_aggregate_kpis. Assert: correct kpis."""
    # Create sessions (minimal required fields)
    s1 = SessionModel(
        session_id="sess_001",
        operator_id="op_a",
        start_time=datetime(2025, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status="complete",
        frame_count=10,
        score_total=85,
    )
    s2 = SessionModel(
        session_id="sess_002",
        operator_id="op_b",
        start_time=datetime(2025, 2, 11, 12, 0, 0, tzinfo=timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=100,
        thermal_directions=["center"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        status="complete",
        frame_count=10,
        score_total=55,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    result = get_aggregate_kpis(db_session, date_start="2025-02-01", date_end="2025-02-17")
    assert result["kpis"]["session_count"] == 2
    assert result["kpis"]["avg_score"] == 70.0
    assert result["kpis"]["rework_count"] == 1
    assert len(result["trend"]) == 2
    assert len(result["calendar"]) == 2
```

**Subtasks:**
- [ ] Create test_aggregate_service.py with db_session fixture
- [ ] Insert 2 sessions (different operators, dates, scores)
- [ ] Assert kpis, trend, calendar shape and values

**✓ Verification test:**
- Action: Run from project root: `cd backend && pytest tests/test_aggregate_service.py` (or ensure `PYTHONPATH` includes `backend/` before running pytest)
- Pass: All tests pass

**Time estimate:** 1.5 hours

---

### Step 2.8: Write API integration test for aggregate endpoint

**What:** Test GET /api/sessions/aggregate via TestClient.

**Why:** Ensures route works end-to-end.

**Files:** Create `backend/tests/test_aggregate_api.py`

**Minimal fixture/arrange pattern:**

```python
# backend/tests/test_aggregate_api.py

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from database.base import Base
from database.models import SessionModel

# Override get_db to use in-memory SQLite (see test_sessions_api.py pattern)
from routes import aggregate as aggregate_routes  # or wherever get_db is imported from


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    """Test client with get_db override. Clears override in finally to avoid bleed with pytest-xdist."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from routes.sessions import get_db
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()  # Always clear; prevents mid-test reset if parallel


def test_aggregate_returns_200(client):
    """Arrange: client with override. Act: GET /api/sessions/aggregate. Assert: 200, structure."""
    response = client.get("/api/sessions/aggregate")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "trend" in data
    assert "calendar" in data
    assert data["kpis"]["session_count"] >= 0


def test_aggregate_invalid_date_returns_400(client):
    """Edge: date_start > date_end returns 400."""
    response = client.get("/api/sessions/aggregate?date_start=2025-02-17&date_end=2025-02-01")
    assert response.status_code == 400
```

**Note:** Adjust `get_db` import to match your project (e.g. `from routes.sessions import get_db` if aggregate route uses sessions' get_db).

**Optional enhancement:** Add integration test with seeded PostgreSQL (or testcontainers) to catch AggregateKPIResponse shape drift that mocks miss. Lower priority than unit/API tests.

**Subtasks:**
- [ ] Create test_aggregate_api.py with client fixture
- [ ] test_aggregate_returns_200: assert 200, kpis/trend/calendar present
- [ ] test_aggregate_invalid_date_returns_400: date_start > date_end → 400

**✓ Verification test:**
- Action: Run from project root: `cd backend && pytest tests/test_aggregate_api.py` (or ensure `PYTHONPATH` includes `backend/` before running pytest)
- Pass: 200, kpis.session_count >= 0

**Time estimate:** 1 hour

---

### Step 2.9: Add OpenAPI documentation for aggregate endpoint

**What:** Ensure docstring and response_model are clear for API consumers.

**Why:** Discoverability; correct OpenAPI schema.

**Subtasks:**
- [ ] Add description to Query params
- [ ] Add example responses in docstring
- [ ] Verify /docs shows correct schema

**✓ Verification test:**
- Action: Open http://localhost:8000/docs; find GET /api/sessions/aggregate
- Pass: Schema shows date_start, date_end, include_sessions; response has kpis, trend, calendar

**Time estimate:** 0.25 hours

---

**Phase 2 total:** ~8.5 hours

---

## Phase 3 — Frontend: Supervisor Dashboard

**Goal:** User sees /supervisor with KPI tiles, trend chart, calendar heatmap.

**Time estimate:** 8–10 hours  
**Risk level:** 🟢 Low

---

### Step 3.1: Create types/aggregate.ts

**What:** Mirror backend AggregateKPIResponse in TypeScript.

**Why:** Type safety for API client and components.

**Full code example:**

```typescript
// my-app/src/types/aggregate.ts

export interface AggregateKPIs {
  avg_score: number | null;
  session_count: number;
  top_performer: string | null;
  rework_count: number;
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface CalendarDay {
  date: string;
  value: number;
}

export interface SessionSummary {
  session_id: string;
  operator_id: string;
  weld_type: string;
  start_time: string;
  score_total: number | null;
  frame_count: number;
}

export interface AggregateKPIResponse {
  kpis: AggregateKPIs;
  trend: TrendPoint[];
  calendar: CalendarDay[];
  sessions?: SessionSummary[];
  sessions_truncated?: boolean;  // true when include_sessions and >1000 sessions; for export alert
}
```

Display "—" for null avg_score and null top_performer (consistent with dashboard metrics).

**✓ Verification test:**
- Action: Import in a file; use as type
- Pass: No TS errors

**Time estimate:** 0.5 hours

---

### Step 3.2: Add fetchAggregateKPIs to api.ts

**What:** fetch function for GET /api/sessions/aggregate.

**Why:** Supervisor page needs to fetch data.

**Full code example:**

```typescript
// In my-app/src/lib/api.ts

import type { AggregateKPIResponse } from "@/types/aggregate";

export interface FetchAggregateParams {
  date_start?: string;
  date_end?: string;
  include_sessions?: boolean;
}

export async function fetchAggregateKPIs(
  params: FetchAggregateParams = {},
  signal?: AbortSignal
): Promise<AggregateKPIResponse> {
  const url = buildUrl("/api/sessions/aggregate", {
    date_start: params.date_start,
    date_end: params.date_end,
    include_sessions: params.include_sessions,
  } as Record<string, string | boolean | undefined>);
  return apiFetch<AggregateKPIResponse>(url, { signal });
}
```

**Note:** Uses buildUrl for consistency with fetchSession(), fetchSessionScore(), fetchDashboardData(); omits undefined params automatically. apiFetch(url, { signal }) forwards the signal to native fetch().

**Environment switching for API_BASE_URL (NEXT_PUBLIC_API_URL):**

| Environment | NEXT_PUBLIC_API_URL | When to use |
|-------------|---------------------|-------------|
| Local | Unset (fallback: `http://localhost:8000`) | `npm run dev` on same machine as backend |
| Dev/staging | `http://dev-server:8000` or `https://api-dev.example.com` | Frontend built and served from dev server; browser reaches backend |
| Production | `https://api.example.com` or full backend URL | Set before `npm run build`; baked into bundle |

**Implementation:** `my-app/src/lib/api.ts` uses `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`. Next.js bakes `NEXT_PUBLIC_*` at build time. For deployment:
- Local dev: No `.env` needed.
- Remote: Create `my-app/.env.local` (or Docker env) with `NEXT_PUBLIC_API_URL=http://<host>:8000` before `npm run build`. Rebuild required when backend URL changes.
- CORS: Backend `CORS_ORIGINS` must include frontend origin (e.g. `http://localhost:3000`, `https://app.example.com`). See `DEPLOY.md`.

**✓ Verification test:**
- Setup: Backend running
- Action: Call fetchAggregateKPIs() from browser console or test
- Pass: Returns AggregateKPIResponse; no CORS error

**Time estimate:** 0.5 hours

---

### Step 3.3: Create CalendarHeatmap component — *Critical: New UX component*

**Why critical:** GitHub-style calendar is central to supervisor view; different from existing HeatMap (thermal).

**Context:** 7 columns (Sun–Sat), rows = weeks. Each cell = day. Color intensity by value (sessions per day). Tooltip on hover. Empty state when no data.

**Full code example:**

```tsx
// my-app/src/components/dashboard/CalendarHeatmap.tsx

'use client';

interface DayValue {
  date: string;
  value: number;
}

interface CalendarHeatmapProps {
  data: DayValue[];
  title?: string;
  emptyMessage?: string;
  weeksToShow?: number;  // Configurable; default 12
}

export function CalendarHeatmap({ data, title = "Activity", emptyMessage = "No activity", weeksToShow = 12 }: CalendarHeatmapProps) {
  if (!data || data.length === 0) {
    return (
      <div className="p-6 text-center text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
        {emptyMessage}
      </div>
    );
  }

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const byDate = new Map(data.map((d) => [d.date, d.value]));

  // Build grid: last N weeks, Sun–Sat. Use UTC to avoid timezone off-by-one across DST/month boundaries.
  const now = new Date();
  const todayUtc = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
  const cells: { date: string; value: number }[] = [];
  for (let w = weeksToShow - 1; w >= 0; w--) {
    for (let d = 0; d < 7; d++) {
      const daysBack = w * 7 + (6 - d);
      const dte = new Date(todayUtc);
      dte.setUTCDate(dte.getUTCDate() - daysBack);
      const key = dte.toISOString().slice(0, 10);  // YYYY-MM-DD in UTC
      cells.push({ date: key, value: byDate.get(key) ?? 0 });
    }
  }

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
      {title && <h3 className="text-sm font-medium mb-2 text-zinc-700 dark:text-zinc-300">{title}</h3>}
      <div className="grid grid-cols-7 gap-0.5" style={{ width: "fit-content" }}>
        {cells.map((c, i) => {
          const intensity = maxVal > 0 ? c.value / maxVal : 0;
          const bg = intensity === 0
            ? "bg-zinc-100 dark:bg-zinc-800"
            : `bg-blue-${Math.min(5, Math.max(1, Math.ceil(intensity * 5)))}`;
          return (
            <div
              key={i}
              title={`${c.date}: ${c.value} sessions`}
              role="img"
              aria-label={`${c.date}: ${c.value} session${c.value === 1 ? '' : 's'}`}
              className={`w-3 h-3 rounded-sm ${intensity === 0 ? "bg-zinc-100 dark:bg-zinc-800" : "bg-blue-500/50"}`}
              style={{
                backgroundColor: intensity === 0
                  ? "var(--zinc-200)"
                  : `rgba(59, 130, 246, ${0.2 + 0.8 * intensity})`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
```

**Note:** Tailwind arbitrary values for dynamic colors can be tricky; using inline style for intensity is safer.

**✓ Verification test:**
- Action: Render with data=[{date:"2025-02-17",value:5}, {date:"2025-02-16",value:2}]
- Expected: Cells show; hover shows tooltip
- Pass: Renders; no console errors

**Time estimate:** 2 hours

---

### Step 3.4: Create aggregateToDashboardData in lib/aggregate-transform.ts

**What:** Function to convert AggregateKPIResponse → DashboardData (metrics + charts).

**Why:** Reuse DashboardLayout; must exist before supervisor page.

**Runtime validation:** Add guards at entry to prevent TS-to-runtime mismatch when API shape changes:
```typescript
if (!res?.kpis) throw new Error('Invalid aggregate response: missing kpis');
if (typeof res.kpis.session_count !== 'number') throw new Error('Invalid kpis.session_count');
// Guard: null or missing trend array — avoid runtime error; use empty array
const trend = Array.isArray(res.trend) ? res.trend : [];
// Guard: null or missing calendar
const calendar = Array.isArray(res.calendar) ? res.calendar : [];
```

**Exact MetricData ids (avoid dashboard key collisions):**
```typescript
// metrics: explicit id strings for each KPI
{ id: 'avg-score', title: 'Avg Score', value: kpis.avg_score ?? '—' }
{ id: 'session-count', title: 'Sessions', value: String(kpis.session_count) }
{ id: 'top-performer', title: 'Top Performer', value: kpis.top_performer ?? '—' }
{ id: 'rework-count', title: 'Rework', value: String(kpis.rework_count) }
```

**Exact ChartData shape for LineChart (DashboardData.charts):**
```typescript
{
  id: 'trend-1',
  type: 'line',
  title: 'Score Trend',
  data: trend.map(t => ({ date: t.date, value: t.value }))
}
```
(Matches `LineChartDataPoint`: `{ date: string; value: number; label?: string }`)

**Subtasks:**
- [ ] Map kpis.avg_score → MetricData (id: 'avg-score', title "Avg Score", value or "—")
- [ ] Map kpis.session_count → MetricData (id: 'session-count')
- [ ] Map kpis.top_performer → MetricData (id: 'top-performer', or "—")
- [ ] Map kpis.rework_count → MetricData (id: 'rework-count')
- [ ] Map trend → ChartData: `{ id: 'trend-1', type: 'line', title: 'Score Trend', data: trend.map(t => ({ date: t.date, value: t.value })) }`
- [ ] Handle null avg_score, empty trend
- [ ] Handle trend with all zero values: chart should render (e.g. y-axis 0–100); avoid NaN or blank
- [ ] Create `my-app/src/__tests__/lib/aggregate-transform.test.ts` with:
  - **Happy path:** Input `{ kpis: { avg_score: 78, session_count: 12, top_performer: 'op1', rework_count: 2 }, trend: [{ date: '2025-02-17', value: 80 }], calendar: [{ date: '2025-02-17', value: 5 }] }` → assert `output.metrics.length === 4`, `output.metrics[0].id === 'avg-score'`, `output.charts[0].id === 'trend-1'`, `output.charts[0].data[0].value === 80`
  - **Edge: empty trend:** Input `{ kpis: { avg_score: null, session_count: 0, top_performer: null, rework_count: 0 }, trend: [], calendar: [] }` → assert no throw; charts[0].data === []
  - **Edge: null/missing trend:** Input `{ kpis: { avg_score: 80, session_count: 1, top_performer: 'op1', rework_count: 0 }, trend: null, calendar: [] }` → assert no throw; charts[0].data === [] (use [] fallback)
  - **Edge: all-zero trend:** Input `{ kpis: {...}, trend: [{ date: '2025-02-17', value: 0 }, { date: '2025-02-16', value: 0 }], calendar: [] }` → assert chart renders; no NaN
  - **Edge: malformed response:** Input `{ kpis: null }` or `{}` → assert throws with descriptive error

**✓ Verification test:**
- Action: Pass sample AggregateKPIResponse; assert output has metrics.length >= 4, charts length >= 1
- Pass: DashboardLayout accepts output without error

**Time estimate:** 1 hour

---

### Step 3.5: Create supervisor page at /supervisor

**What:** Page that fetches aggregate API and renders DashboardLayout + CalendarHeatmap.

**Why:** Primary user entry point.

**Full code example:**

```tsx
// my-app/src/app/(app)/supervisor/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { CalendarHeatmap } from '@/components/dashboard/CalendarHeatmap';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { fetchAggregateKPIs } from '@/lib/api';
import { aggregateToDashboardData } from '@/lib/aggregate-transform';
import type { AggregateKPIResponse } from '@/types/aggregate';
import type { DashboardData } from '@/types/dashboard';

export default function SupervisorPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [calendar, setCalendar] = useState<{ date: string; value: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();
    fetchAggregateKPIs({}, ac.signal)
      .then((res: AggregateKPIResponse) => {
        if (!cancelled) {
          setData(aggregateToDashboardData(res));
          setCalendar(res.calendar);
        }
      })
      .catch((err) => {
        if (!cancelled && err?.name !== 'AbortError') {
          console.error('[SupervisorPage] fetchAggregateKPIs failed:', err);
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, []);

  if (loading) return <div className="p-6">Loading...</div>;
  if (error) return <div className="p-6 text-red-500">Error: {error}</div>;
  if (!data) return <div className="p-6">No data</div>;

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-6">
        <DashboardLayout data={data} title="Supervisor Dashboard" />
        <div className="mt-8">
          <CalendarHeatmap data={calendar} title="Sessions by day" />
        </div>
      </div>
    </ErrorBoundary>
  );
}
```

**Note:** aggregateToDashboardData is created in Step 3.4. DashboardLayout expects DashboardData. To avoid duplicate headings (SupervisorPage vs DashboardLayout's default "Dashboard" h1), pass `title="Supervisor Dashboard"` to DashboardLayout. If DashboardLayout does not support a `title` prop, add it: accept `title?: string` and render it as the page h1 instead of the hardcoded "Dashboard".

**✓ Verification test:**
- Setup: Backend running, seeded
- Action: Navigate to /supervisor
- Expected: KPI tiles, chart, calendar; no errors
- Pass: Renders; data reflects backend

**Time estimate:** 2 hours

---

### Step 3.6: Orthogonality check — no 3D/micro-feedback imports

**What:** Grep supervisor page and related components for forbidden imports.

**Why:** Preserve orthogonality.

**Subtasks:**
- [ ] Grep for TorchViz3D, HeatmapPlate3D, HeatMap (thermal), FeedbackPanel, TorchAngleGraph in supervisor page, CalendarHeatmap, aggregate-transform
- [ ] Ensure none are imported

**✓ Verification test:**
- Action: rg "TorchViz3D|HeatmapPlate3D|HeatMap|FeedbackPanel|TorchAngleGraph" my-app/src/app/\(app\)/supervisor my-app/src/components/dashboard/CalendarHeatmap my-app/src/lib/aggregate-transform
- Pass: No matches

**Time estimate:** 0.25 hours

---

### Step 3.7: Add responsive layout for small screens

**What:** KPI tiles and charts stack on mobile.

**Why:** Usability.

**Subtasks:**
- [ ] Verify DashboardLayout uses responsive grid (grid-cols-1 md:grid-cols-2 lg:grid-cols-3)
- [ ] CalendarHeatmap fits on 320px width
- [ ] Test at 375px viewport

**✓ Verification test:**
- Action: Resize to 375px; reload /supervisor
- Pass: No horizontal scroll; readable

**Time estimate:** 0.5 hours

---

### Step 3.8: Orthogonality verification — add to CI or pre-commit

**What:** Document rule: supervisor module must not import 3D/micro-feedback.

**Why:** Prevent regressions.

**Subtasks:**
- [ ] Add comment in plan and README
- [ ] **Required:** Add ESLint no-restricted-imports in `my-app/.eslintrc*` for supervisor-related paths: disallow imports of `TorchViz3D`, `HeatmapPlate3D`, `HeatMap` (or equivalent thermal heatmap) in `my-app/src/app/(app)/supervisor`, `my-app/src/components/dashboard/CalendarHeatmap`, `my-app/src/lib/aggregate-transform`. Example rule: `{ "paths": ["**/supervisor/**", "**/dashboard/CalendarHeatmap*", "**/aggregate-transform*"], "patterns": ["*TorchViz3D*", "*HeatmapPlate3D*", "*HeatMap*"] }`
- [ ] Add checklist item in PR template

**✓ Verification test:**
- Action: rg "from.*TorchViz3D|from.*HeatmapPlate3D|from.*HeatMap" my-app/src/app/\(app\)/supervisor my-app/src/components/dashboard/CalendarHeatmap my-app/src/lib/aggregate-transform
- Pass: No matches

**Time estimate:** 0.25 hours

---

### Step 3.9: Add component test for SupervisorPage

**What:** Automated component test that mocks fetchAggregateKPIs and asserts KPI tiles and CalendarHeatmap render.

**Why:** Project rules require verification via automated tests (no manual browser checks). Phase 3 verification includes manual steps; this step satisfies the automated-test mandate.

**Implementation:**

```typescript
// my-app/src/__tests__/app/(app)/supervisor/page.test.tsx

import { render, screen } from '@testing-library/react';
import SupervisorPage from '@/app/(app)/supervisor/page';

// Mock fetchAggregateKPIs
jest.mock('@/lib/api', () => ({
  fetchAggregateKPIs: jest.fn(() =>
    Promise.resolve({
      kpis: {
        avg_score: 78,
        session_count: 12,
        top_performer: 'operator_01',
        rework_count: 2,
      },
      trend: [{ date: '2025-02-17', value: 80 }],
      calendar: [{ date: '2025-02-17', value: 5 }],
    })
  ),
}));

describe('SupervisorPage', () => {
  it('renders KPI tiles when data loads', async () => {
    render(<SupervisorPage />);
    await screen.findByText(/Supervisor Dashboard/i);
    // Assert multiple KPI values explicitly to guard against partial render
    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('operator_01')).toBeInTheDocument();
    expect(screen.getByText(/Avg Score/i)).toBeInTheDocument();
    expect(screen.getByText(/Sessions/i)).toBeInTheDocument();
    expect(screen.getByText(/Top Performer/i)).toBeInTheDocument();
    expect(screen.getByText(/Rework/i)).toBeInTheDocument();
  });

  it('renders CalendarHeatmap when calendar data exists', async () => {
    render(<SupervisorPage />);
    await screen.findByText(/Sessions by day|Activity/i);
    const heatmapRegion = document.querySelector('[class*="grid-cols-7"]');
    expect(heatmapRegion).toBeInTheDocument();
  });
});
```

**Subtasks:**
- [ ] Create `my-app/src/__tests__/app/(app)/supervisor/page.test.tsx` (follows project convention: page tests live in `__tests__/app/{route}/page.test.tsx`)
- [ ] Mock fetchAggregateKPIs with sample AggregateKPIResponse
- [ ] Assert KPI tiles render (avg_score, session_count, top_performer, rework_count)
- [ ] Assert CalendarHeatmap or its container renders

**✓ Verification test:**
- Action: `cd my-app && npm test -- supervisor/page`
- Pass: Tests pass; no manual browser checks required for Phase 3 verification

**Time estimate:** 1 hour

---

**Phase 3 total:** ~9.25 hours

---

## Phase 4 — Extensions: Date Filter and CSV Export

**Goal:** User can filter date range and export CSV.

**Time estimate:** 4–6 hours  
**Risk level:** 🟢 Low

---

### Step 4.1: Create export.ts with generateCSV and downloadCSV

**What:** generateCSV(rows) returns string; downloadCSV(filename, csv) triggers download.

**Why:** CSV export for supervisor reports.

**Full code example:**

```typescript
// my-app/src/lib/export.ts

export function generateCSV(rows: Record<string, string | number>[]): string {
  if (rows.length === 0) return "";
  const header = Object.keys(rows[0]).join(",");
  const body = rows.map((r) => Object.values(r).map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
  return header + "\n" + body;
}

export function downloadCSV(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```

**✓ Verification test:**
- Action: generateCSV([{a:1,b:"x"},{a:2,b:"y"}])
- Expected: "a,b\n\"1\",\"x\"\n\"2\",\"y\""
- Action: downloadCSV("test.csv", csv)
- Expected: File downloads
- Pass: Correct format; download works

**Time estimate:** 0.5 hours

---

### Step 4.2: Add date range filter UI to supervisor page

**What:** Preset buttons (Last 7 days, Last 30 days) and/or date picker.

**Why:** User can change range without code change.

**Minimal code snippet:**

```typescript
// In supervisor page (add useRef to imports)
const [dateStart, setDateStart] = useState<string>(() =>
  new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
);
const [dateEnd, setDateEnd] = useState<string>(() =>
  new Date().toISOString().slice(0, 10)
);

const applyPreset = (days: number) => {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - days);
  setDateEnd(end.toISOString().slice(0, 10));
  setDateStart(start.toISOString().slice(0, 10));
};

// Debounce BOTH preset buttons and date picker (300ms) to avoid redundant fetches on rapid clicks.
// Use 0ms on initial mount so first fetch is immediate.
const [fetchDateStart, setFetchDateStart] = useState(dateStart);
const [fetchDateEnd, setFetchDateEnd] = useState(dateEnd);
const isFirstDateSync = useRef(true);
useEffect(() => {
  const delay = isFirstDateSync.current ? 0 : 300;
  isFirstDateSync.current = false;
  const t = setTimeout(() => {
    setFetchDateStart(dateStart);
    setFetchDateEnd(dateEnd);
  }, delay);
  return () => clearTimeout(t);
}, [dateStart, dateEnd]);

useEffect(() => {
  let cancelled = false;
  const ac = new AbortController();
  fetchAggregateKPIs({ date_start: fetchDateStart, date_end: fetchDateEnd }, ac.signal)
    .then((res) => {
      if (!cancelled) {
        setData(aggregateToDashboardData(res));
        setCalendar(res.calendar);
      }
    })
    .catch(/* ... */)
    .finally(() => { if (!cancelled) setLoading(false); });
  return () => { cancelled = true; ac.abort(); };
}, [fetchDateStart, fetchDateEnd]);
```

**Preset buttons:**
```tsx
<button onClick={() => applyPreset(7)}>Last 7 days</button>
<button onClick={() => applyPreset(30)}>Last 30 days</button>
```

**Timezone for date strings:** Use `toISOString().slice(0, 10)` which yields UTC date (e.g. 2025-02-17). Backend interprets dates as UTC; date_end is inclusive. If displaying local dates in picker, convert to UTC before sending (e.g. `new Date(y, m, d).toISOString().slice(0,10)` for local midnight → UTC). Document: API expects YYYY-MM-DD in UTC.

**Subtasks:**
- [ ] Add state: dateStart, dateEnd
- [ ] Preset buttons: set range to -7, -30 days from today
- [ ] Pass date_start, date_end to fetchAggregateKPIs
- [ ] Refetch when range changes (useEffect dependency on dateStart, dateEnd)
- [ ] Debounce 300ms for BOTH preset buttons and date picker (0ms on initial mount)

**✓ Verification test:**
- Action: Click "Last 30 days"
- Expected: New fetch with wider range; data updates
- Pass: API called with correct params; UI reflects

**Time estimate:** 1.5 hours

---

### Step 4.3: Add Export CSV button to supervisor page

**What:** Button that fetches aggregate with include_sessions=true, generates CSV, triggers download.

**Why:** User can export for meetings.

**Subtasks:**
- [ ] Add Export CSV button
- [ ] On click: fetchAggregateKPIs({ date_start, date_end, include_sessions: true })
- [ ] Transform sessions to CSV rows (session_id, operator_id, weld_type, start_time, score_total, frame_count)
- [ ] generateCSV + downloadCSV
- [ ] Disable during load; handle empty sessions
- [ ] Limit: 90 days or 1000 sessions (backend enforces). **UI enforcement (mandatory):** When `response.sessions_truncated === true` or `response.sessions?.length === 1000`, show a **prominent alert** (banner visible on page, or inline near Export button): "Export limited to 1000 sessions. Data may be truncated. Consider narrowing the date range." Display before and/or after export—user must be aware; do not silently truncate. Optional: Log export truncation for monitoring (see Definition of Done).

**✓ Verification test:**
- Action: Click Export CSV
- Expected: File downloads; name like supervisor-export-2025-02-17.csv; contains session data
- Pass: File valid; opens in Excel

**Time estimate:** 1.5 hours

---

### Step 4.4: Add nav link to /supervisor

**What:** Link in sidebar or header to /supervisor.

**Why:** Discoverability.

**Subtasks:**
- [ ] Find nav component (e.g. layout, sidebar)
- [ ] Add link "Supervisor" → /supervisor

**✓ Verification test:**
- Action: Click Supervisor in nav
- Pass: Navigates to /supervisor

**Time estimate:** 0.5 hours

---

### Step 4.5: Handle export API failure (show error message)

**What:** When fetch fails during export, show user-friendly error.

**Why:** UX when network fails or backend returns 500.

**Subtasks:**
- [ ] Catch fetch error in Export button handler
- [ ] Show toast or inline message "Export failed. Please try again."
- [ ] Re-enable button after error
- [ ] Do not trigger download if no sessions

**✓ Verification test:**
- Action: Mock API to return 500; click Export
- Expected: Error message; no download
- Pass: User sees error; can retry

**Time estimate:** 0.5 hours

---

### Step 4.6: Empty state when no sessions in range

**What:** Show "No sessions in date range" when calendar and KPIs are empty.

**Why:** Clear UX.

**Subtasks:**
- [ ] When kpis.session_count === 0, show message
- [ ] Keep date filter usable; suggest wider range

**✓ Verification test:**
- Action: Select range with no sessions
- Expected: "No sessions in date range" or similar
- Pass: No errors; message visible

**Time estimate:** 0.5 hours

---

### Step 4.7: Keyboard accessibility for Export and date filter

**What:** Export button and date presets focusable; Enter/Space triggers. Screen-reader announcements for success/error.

**Why:** WCAG 2.1 AA.

**Subtasks:**
- [ ] Ensure Export button is <button> or has role="button" and tabIndex={0}
- [ ] Date preset buttons keyboard accessible
- [ ] Add aria-live="polite" region that announces "Export complete" or "Export failed" for screen readers
- [ ] Focus management after export (optional)

**✓ Verification test:**
- Action: Tab to Export; press Enter
- Expected: Export triggers
- Pass: Keyboard-only flow works

**Time estimate:** 0.25 hours

---

### Step 4.8: Add E2E test for date filter + CSV export

**What:** End-to-end test covering date range selection and CSV export flow.

**Why:** Prevents regressions in date calculations, export truncation, and download behavior. Critique: "No end-to-end test covering date filtering + CSV export."

**Implementation (Playwright or similar):**

```typescript
// my-app/e2e/supervisor-export.spec.ts (or in __tests__/e2e/ if using different runner)

import { test, expect } from '@playwright/test';

test.describe('Supervisor date filter and CSV export', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/supervisor');
    await page.waitForSelector('text=Supervisor Dashboard', { timeout: 10000 });
  });

  test('date filter updates data', async ({ page }) => {
    await page.click('button:has-text("Last 30 days")');
    await page.waitForTimeout(500);  // Debounce + fetch
    // Verify data refreshed (e.g. session count or chart visible)
    const chart = page.locator('[class*="grid-cols-7"]').or(page.locator('text=/\\d+/'));
    await expect(chart.first()).toBeVisible({ timeout: 5000 });
  });

  test('Export CSV downloads valid file', async ({ page }) => {
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('button:has-text("Export CSV")'),
    ]);
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/supervisor-export.*\.csv$/);
    const savePath = await download.path();
    expect(savePath).toBeTruthy();
    const { readFileSync } = await import('fs');
    const content = readFileSync(savePath, 'utf-8');
    expect(content).toContain('session_id');
    expect(content.split('\n').length).toBeGreaterThan(1);
  });
});
```

**Subtasks:**
- [ ] Add Playwright (or project's E2E runner) test file
- [ ] Test: Select "Last 30 days" → data refreshes
- [ ] Test: Click Export CSV → file downloads with correct name and CSV headers
- [ ] Run in CI (optional) or as pre-release check

**✓ Verification test:**
- Action: `cd my-app && npx playwright test supervisor-export` (or `npm run test:e2e`)
- Pass: Both tests pass

**Time estimate:** 1 hour

---

**Phase 4 total:** ~6.25 hours

---

## 3. Pre-Flight Checklist

### Phase 1 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Node.js v18+ | `node --version` | Install from nodejs.org |
| Python 3.10+ | `python --version` | Install Python |
| PostgreSQL running | `psql -U postgres -c "SELECT 1"` or docker | `docker-compose up db` |
| Dependencies | `cd backend && pip install -r requirements.txt` | pip install |
| Alembic | `alembic current` | pip install alembic |
| Seeded DB | `curl -X POST localhost:8000/api/dev/seed-mock-sessions` | Run seed |
| Dev seed enabled | ENV=development or DEBUG=1 | Set env |

**Checkpoint:** ⬜ All Phase 1 prerequisites met

### Phase 2 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1 complete | score_total column exists | Complete Phase 1 |
| Backfill run | SELECT score_total FROM sessions LIMIT 1 | Run backfill |

**Checkpoint:** ⬜ All Phase 2 prerequisites met

### Phase 3 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 2 complete | GET /api/sessions/aggregate returns 200 | Complete Phase 2 |
| Frontend deps | `cd my-app && npm install` | npm install |
| Backend running | `curl localhost:8000/health` | Start backend |

**Checkpoint:** ⬜ All Phase 3 prerequisites met

### Phase 4 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 3 complete | /supervisor renders | Complete Phase 3 |

**Checkpoint:** ⬜ All Phase 4 prerequisites met

---

## 4. Risk Heatmap

| Phase | Step | Risk | Probability | Impact | Detection | Mitigation |
|-------|------|------|-------------|--------|-----------|------------|
| 1 | 1.2 | Migration fails on prod | 🟡 20% | High | alembic upgrade errors | Test on copy of prod; rollback script |
| 1 | 1.4 | get_session_score doesn't persist | 🟡 25% | High | score_total stays null | Unit test; manual verify |
| 1 | 1.5 | Backfill OOM on large DB | 🟡 25% | Medium | Script kills | Batch 10 at a time |
| 1 | 1.2 | Column name collision | 🟢 5% | Medium | Migration error | Use unique name score_total |
| 1 | 1.3 | SessionModel.from_pydantic ignores score_total | 🟡 15% | Low | Backfill/model mismatch | Update both directions |
| 2 | 2.2 | Wrong KPI formula | 🟡 30% | Medium | Numbers differ from expected | Unit test with known data |
| 2 | 2.3 | Slow aggregate query | 🟡 20% | High | > 3s response | Index on start_time; limit range |
| 2 | 2.2 | Null score_total in avg causes division by zero | 🟡 10% | Medium | 500 error | Explicit guard: len(scored)==0 → avg_score=None; never divide |
| 2 | 2.3 | date_start/date_end timezone mismatch | 🟡 20% | Medium | Wrong sessions returned | Use UTC consistently |
| 2 | 2.7 | Unit test DB state leaks | 🟢 15% | Low | Flaky tests | Use transaction rollback |
| 3 | 3.3 | Calendar layout overflow | 🟡 30% | Low | Horizontal scroll | Responsive; max-width |
| 3 | 3.3 | Calendar timezone off-by-one | 🟡 15% | Medium | Wrong cell for date | Use UTC (setUTCDate, Date.UTC) in grid logic |
| 3 | 3.5 | Forbidden import added | 🟡 20% | High | Coupling | Grep in PR; lint rule |
| 3 | 3.2 | fetchAggregateKPIs CORS or wrong URL | 🟡 15% | High | Network error | Env strategy: NEXT_PUBLIC_API_URL per environment; CORS_ORIGINS on backend |
| 3 | 3.5 | useEffect cleanup (cancelled) wrong | 🟡 15% | Medium | Memory leak / setState after unmount | Use AbortController |
| 3 | 3.7 | aggregateToDashboardData wrong ChartData shape | 🟡 20% | Medium | Chart doesn't render | Match LineChartDataPoint |
| 4 | 4.3 | Export fails for large data | 🟡 25% | Medium | No download / timeout | Limit 90 days, 1000 rows; sessions_truncated flag |
| 4 | 4.3 | Truncated export not noticed by user | 🟡 20% | Medium | User trusts incomplete data | Mandatory prominent alert when sessions_truncated |
| 4 | 4.2 | Date picker timezone bug | 🟡 25% | Low | Off-by-one day | Use UTC in API; doc |
| 4 | 4.2 | Debounce too short — rapid clicks cause redundant fetches | 🟢 20% | Low | Multiple requests | 300ms debounce for presets + picker |
| 3 | 3.5 | React hydration mismatch | 🟢 10% | High | Console warning; layout shift | Server/client consistency |
| 3 | 3.7 | Tailwind dark mode class mismatch | 🟢 15% | Medium | Wrong colors in dark mode | Use dark: variants; test both |
| 4 | 4.3 | CSV special chars break format | 🟡 15% | Medium | Invalid CSV | Escape quotes in generateCSV |
| 4 | 4.5 | Export error leaves button disabled | 🟡 10% | Low | User stuck | Re-enable on catch |
| All | — | Orthogonality break | 🟡 20% | High | 3D import in supervisor | Code review; ESLint |

**Top 5 risks to address proactively:**
1. Migration failure — test on dev first
2. get_session_score persistence — add explicit test
3. Aggregate query performance — verify index; add limit
4. Orthogonality — grep in CI
5. Backfill OOM — batch processing

---

## 5. Success Criteria (End-to-End)

| # | Requirement | Target | Verification | Priority |
|---|-------------|--------|--------------|----------|
| 1 | User can view KPI tiles | avg_score, session_count, top_performer, rework_count | /supervisor shows 4 tiles | P0 |
| 2 | User can view trend chart | Score over time | LineChart with data | P0 |
| 3 | User can view calendar heatmap | Sessions per day | CalendarHeatmap visible | P0 |
| 4 | User can filter date range | Last 7, 30 days | Data refreshes | P0 |
| 5 | User can export CSV | File downloads with session data | Click Export → file downloads | P0 |
| 6 | Empty state | "No sessions in date range" | Select empty range | P1 |
| 7 | Aggregate API < 3s | 500 sessions | Measure response time | P0 |
| 8 | No frames in aggregate path | Metadata + score_total only | Code review | P0 |
| 9 | Orthogonality | No 3D/micro-feedback imports | Grep | P0 |
| 10 | Responsive | Works at 375px | Resize viewport | P1 |
| 11 | No console errors | Clean DevTools | Full flow | P0 |
| 12 | Backfill success | All COMPLETE sessions have score_total | Query DB | P0 |

---

## 6. Progress Tracking

| Phase | Total Steps | Completed | In Progress | Blocked | % Complete |
|-------|-------------|-----------|-------------|---------|------------|
| Phase 1 | 7 | 0 | 0 | 0 | 0% |
| Phase 2 | 9 | 0 | 0 | 0 | 0% |
| Phase 3 | 10 | 0 | 0 | 0 | 0% |
| Phase 4 | 8 | 0 | 0 | 0 | 0% |
| **TOTAL** | **34** | **0** | **0** | **0** | **0%** |

---

## 7. Common Failures & Fixes

### If migration fails with "column already exists"
- **Cause:** Migration run twice or manual change  
- **Fix:** alembic downgrade -1; fix migration; upgrade

### If get_session_score doesn't persist
- **Cause:** Missing commit; conditional logic wrong  
- **Fix:** Add db.commit(); verify session_model.score_total assignment; check status value

### If backfill OOM or script hangs
- **Cause:** Using .all() loads all sessions; hundreds with frames exhaust memory  
- **Fix:** Use limit(BATCH_SIZE) in a loop; process batches of 10 until no more match filter

### If aggregate returns 404 (GET /api/sessions/aggregate)
- **Cause:** aggregate_router registered after sessions_router; route matches /sessions/{session_id} with session_id="aggregate"  
- **Fix:** In main.py, include aggregate_router BEFORE sessions_router

### If aggregate returns 500
- **Cause:** AttributeError on score_total; KeyError in dict  
- **Fix:** Check SessionModel has score_total; fix aggregate_service dict keys

### If CalendarHeatmap empty
- **Cause:** calendar data empty; date format mismatch  
- **Fix:** Log calendar from API; ensure frontend passes correct shape

### If Export doesn't download
- **Cause:** Blob/cross-origin; browser block  
- **Fix:** Ensure same-origin; user gesture; check console for errors

### If date range shows wrong data
- **Cause:** Timezone off-by-one (local vs UTC); date_start/date_end format; date_end exclusive bug (sessions later on date_end day excluded)  
- **Fix:** API expects YYYY-MM-DD in UTC. Use `toISOString().slice(0,10)` for UTC date strings. If user picks local date, convert: `new Date(y, m-1, d).toISOString().slice(0,10)`. Ensure aggregate_service uses start_time < (date_end + 1 day) for inclusive end; log backend params

---

## 7.1 Known Issues & Limitations

| Issue | Impact | Mitigation | Future |
|-------|--------|------------|--------|
| **Implicit API contract** | Backend schema change could break frontend silently | Runtime guards in aggregateToDashboardData; tests for malformed input | Add contract tests or zod schema validation against OpenAPI |
| **No pagination for sessions** | Export with >1000 sessions truncates | Backend caps at 1000; sessions_truncated flag; prominent UI alert | Cursor-based pagination if needed |
| **Frontend error logging** | Production errors only in console | console.error on fetch failure; observability logs | Integrate Sentry/LogRocket for production |
| **Backend loads all sessions for include_sessions** | Very large date ranges could cause backend memory pressure | 90-day limit; 1000-session cap on response | Pagination if >5k sessions typical |

---

## 8. Definition of Done

- [ ] All P0 success criteria pass
- [ ] All Phase verification tests pass
- [ ] No imports from TorchViz3D, HeatmapPlate3D, HeatMap in supervisor module
- [ ] Code reviewed
- [ ] Aggregate API response time < 3s for 500 sessions
- [ ] Documentation updated (SETUP, README)
- [ ] **Changelog entry:** Add CHANGELOG entry (or release notes snippet) describing: WWAD supervisor dashboard at `/supervisor`, `GET /api/sessions/aggregate` endpoint, and `score_total` persistence on sessions. Example: `## [Unreleased] - WWAD Macro Analytics — Supervisor dashboard with KPI tiles, trend chart, calendar heatmap, CSV export; aggregate API; score_total column and backfill.`
- [ ] **Required observability (mission-critical dashboard):** Log aggregate endpoint requests: `date_start`, `date_end`, `include_sessions`, `sessions_truncated` (when true), and response time on completion. Backend: `logger.info("aggregate", extra={"date_start": ds, "date_end": de, "duration_ms": elapsed, "sessions_truncated": truncated})`. Frontend: Log export failures (and truncation when `sessions_truncated`) to console; consider Sentry/LogRocket for production error tracking.

---

## 9. Implementation Notes Template

**Step X.Y — [Name]:**  
**Date:**  
**Time taken:** ___ h (est: ___ h)  
**What went well:**  
**What went poorly:**  
**Unexpected challenges:**  
**Lessons learned:**  

---

## 10. Quality Metrics Checklist

| Metric | Minimum | Count |
|--------|---------|-------|
| Phases | 3 | 4 ✅ |
| Total steps | 30 | 34 ✅ |
| Critical steps with code | 10 | 8 |
| Verification tests | = steps | 33 ✅ |
| Risk entries | 20 | 10+ |
| Success criteria | 12 | 12 ✅ |

---

**Plan complete. Ready for implementation.**
