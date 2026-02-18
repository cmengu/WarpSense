# WarpSense — Full Feature Implementation Plan
> **Purpose:** Authoritative reference for all 4 batches × 3 agents. Every file path, type signature, naming convention, and dependency is defined here. Agents must not deviate from these contracts.
> **Last Updated:** 2026-02-18

---

## SECTION 0 — GLOBAL STANDARDS
> Read this before writing a single line. All agents in all batches conform to these.

---

### 0.1 Naming Conventions

#### Python (Backend)
| Thing | Convention | Example |
|-------|-----------|---------|
| Files | snake_case | `trajectory_service.py` |
| Classes | PascalCase | `WelderTrajectory` |
| Pydantic models | PascalCase + suffix | `TrajectoryPointResponse` |
| SQLAlchemy models | PascalCase | `SessionAnnotation` |
| Functions | snake_case | `get_welder_trajectory()` |
| Constants | UPPER_SNAKE | `MAX_BENCHMARK_SESSIONS` |
| Enums | PascalCase class, UPPER value | `AnnotationType.DEFECT_CONFIRMED` |

#### TypeScript (Frontend)
| Thing | Convention | Example |
|-------|-----------|---------|
| Files/Components | PascalCase | `TrajectoryChart.tsx` |
| Utility files | camelCase | `trajectoryUtils.ts` |
| Types/Interfaces | PascalCase | `TrajectoryPoint` |
| Functions | camelCase | `fetchTrajectory()` |
| Constants | UPPER_SNAKE | `MAX_CHART_POINTS` |
| Enums (TS) | PascalCase class, PascalCase value | `RiskLevel.Warning` |
| CSS classes | Tailwind only — no custom classes |
| Component props interfaces | `{ComponentName}Props` | `TrajectoryChartProps` |

#### API Routes
```
/api/sessions/{session_id}                    — existing
/api/sessions/{session_id}/score              — existing
/api/sessions/{session_id}/narrative          — NEW Batch 1
/api/sessions/{session_id}/annotations        — NEW Batch 2
/api/sessions/{session_id}/warp-risk          — NEW Batch 1
/api/welders/{welder_id}/trajectory           — NEW Batch 2
/api/welders/{welder_id}/benchmarks           — NEW Batch 3
/api/welders/{welder_id}/coaching-plan        — NEW Batch 3
/api/welders/{welder_id}/certification-status — NEW Batch 3
/api/defects                                  — NEW Batch 2
/api/sites                                    — NEW Batch 4
/api/sites/{site_id}/teams                    — NEW Batch 4
/api/sessions/aggregate                       — existing, extended Batch 4
```

---

### 0.2 Shared Type Contracts
> These are defined ONCE. All agents import from these locations — never redefine inline.

#### Canonical Metric Names
Used identically in Python enums, TypeScript types, API responses, and DB column names.
```
angle_consistency
thermal_symmetry
amps_stability
volts_stability
heat_diss_consistency
```
**Python enum** — define in `backend/models/shared_enums.py` (created in Batch 0):
```python
class WeldMetric(str, Enum):
    ANGLE_CONSISTENCY = "angle_consistency"
    THERMAL_SYMMETRY = "thermal_symmetry"
    AMPS_STABILITY = "amps_stability"
    VOLTS_STABILITY = "volts_stability"
    HEAT_DISS_CONSISTENCY = "heat_diss_consistency"
```
**TypeScript type** — define in `my-app/src/types/shared.ts` (created in Batch 0):
```typescript
export type WeldMetric =
  | "angle_consistency"
  | "thermal_symmetry"
  | "amps_stability"
  | "volts_stability"
  | "heat_diss_consistency";

export const WELD_METRICS: WeldMetric[] = [
  "angle_consistency",
  "thermal_symmetry",
  "amps_stability",
  "volts_stability",
  "heat_diss_consistency",
];
```

#### Canonical Risk/Severity Levels
```
"ok" | "warning" | "critical"
```
**Python enum** — in `backend/models/shared_enums.py`:
```python
class RiskLevel(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
```
**TypeScript** — in `my-app/src/types/shared.ts`:
```typescript
export type RiskLevel = "ok" | "warning" | "critical";
```

#### Canonical Status Enums (per-feature)
Each feature defines its own status in its own types file. Pattern:
```typescript
// Always string literal unions, not TS enums — simpler JSON serialisation
export type CoachingStatus = "active" | "complete" | "overdue";
export type CertificationStatus = "on_track" | "at_risk" | "certified" | "not_started";
export type AnnotationType = "defect_confirmed" | "near_miss" | "technique_error" | "equipment_issue";
```

#### Canonical ID Types
```typescript
// my-app/src/types/shared.ts
export type WelderID = string;    // e.g. "mike-chen"
export type SessionID = string;   // e.g. "sess_novice_001"
export type SiteID = string;      // e.g. "site_001"
export type TeamID = string;      // e.g. "team_001"
```

#### MetricScore — used by Trajectory, Benchmarking, Coaching, Certification
```typescript
// my-app/src/types/shared.ts
export interface MetricScore {
  metric: WeldMetric;
  value: number;        // 0-100
  label: string;        // human-readable: "Angle Consistency"
}
```
**Python Pydantic** — in `backend/schemas/shared.py` (created Batch 0):
```python
class MetricScore(BaseModel):
    metric: WeldMetric
    value: float  # 0-100
    label: str
```

---

### 0.3 File Ownership Matrix
> Each file has ONE owning agent. No other agent touches it.

| File | Owner |
|------|-------|
| `backend/models/shared_enums.py` | Batch 0 Agent 1 |
| `backend/schemas/shared.py` | Batch 0 Agent 1 |
| `my-app/src/types/shared.ts` | Batch 0 Agent 1 |
| `my-app/src/components/layout/ReportLayout.tsx` | Batch 0 Agent 1 |
| `backend/routes/welders.py` | Batch 0 Agent 1 |
| `backend/alembic/versions/005_*.py` | Batch 1 Agent 1 |
| `backend/alembic/versions/006_*.py` | Batch 1 Agent 3 |
| `backend/alembic/versions/007_*.py` | Batch 2 Agent 2 |
| `backend/alembic/versions/008_*.py` | Batch 3 Agent 2 |
| `backend/alembic/versions/009_*.py` | Batch 3 Agent 3 |
| `backend/services/prediction_service.py` | Batch 1 Agent 2 |
| `backend/routes/predictions.py` | Batch 1 Agent 2 |
| `backend/services/narrative_service.py` | Batch 1 Agent 3 |
| `backend/routes/narratives.py` | Batch 1 Agent 3 |
| `backend/services/trajectory_service.py` | Batch 2 Agent 1 |
| `backend/models/annotation.py` | Batch 2 Agent 2 |
| `backend/routes/annotations.py` | Batch 2 Agent 2 |
| `backend/services/benchmark_service.py` | Batch 3 Agent 1 |
| `backend/services/coaching_service.py` | Batch 3 Agent 2 |
| `backend/services/cert_service.py` | Batch 3 Agent 3 |
| `backend/routes/sites.py` | Batch 4 Agent 1 |

---

### 0.4 Migration Numbering
> Reserve all numbers in Batch 0. Never skip. Never reuse.

| Number | Feature | Owner |
|--------|---------|-------|
| 001–004 | Existing | — |
| 005 | sites + teams + session team_id FK | Batch 1 Agent 1 |
| 006 | session_narratives | Batch 1 Agent 3 |
| 007 | session_annotations | Batch 2 Agent 2 |
| 008 | drills + coaching_assignments | Batch 3 Agent 2 |
| 009 | cert_standards + welder_certifications | Batch 3 Agent 3 |

---

### 0.5 API Client Pattern
> All new API calls go into `my-app/src/lib/api.ts`. Each agent appends their section — never overwrites another agent's functions.

Pattern for every new fetch function:
```typescript
export async function fetchTrajectory(welderId: WelderID): Promise<WelderTrajectory> {
  const res = await fetch(`${API_BASE}/api/welders/${welderId}/trajectory`);
  if (!res.ok) throw new Error(`fetchTrajectory failed: ${res.status}`);
  return res.json();
}
```
Rules:
- Always throw on non-ok (never return null silently)
- Always include function name in error message
- Always type the return
- Use `WelderID`, `SessionID` etc from `types/shared.ts` — not raw `string`

---

### 0.6 ReportLayout Slot Contract
> Defined in Batch 0. All agents drop panels into slots — never modify ReportLayout structure.

```typescript
// my-app/src/components/layout/ReportLayout.tsx
export interface ReportLayoutProps {
  // Header
  welderName: string;
  sessionId: SessionID;
  scoreTotal: number;
  // Slots — all optional; absent slots render nothing
  narrative?: React.ReactNode;      // Batch 1 Agent 3 / Batch 2 Agent 3
  trajectory?: React.ReactNode;     // Batch 2 Agent 1
  benchmarks?: React.ReactNode;     // Batch 3 Agent 1
  coaching?: React.ReactNode;       // Batch 3 Agent 2
  certification?: React.ReactNode;  // Batch 3 Agent 3
  // Always-present slots (existing content moves here)
  heatmaps?: React.ReactNode;
  feedback?: React.ReactNode;
}
```

---

## BATCH 0 — BLOCKING SETUP
**Duration:** 1 day. Single agent. Sequential. Nothing else starts until this is green.

---

### Batch 0 Agent 1 — Foundation Layer

**Purpose:** Create all shared infrastructure that every subsequent agent depends on. No feature logic — only types, stubs, and structural refactors.

---

#### Step 1: Shared Python Models

**Create** `backend/models/shared_enums.py`:
```python
"""
Canonical enums shared across all WarpSense services.
Import from here — never redefine these enums elsewhere.
"""
from enum import Enum

class WeldMetric(str, Enum):
    ANGLE_CONSISTENCY = "angle_consistency"
    THERMAL_SYMMETRY = "thermal_symmetry"
    AMPS_STABILITY = "amps_stability"
    VOLTS_STABILITY = "volts_stability"
    HEAT_DISS_CONSISTENCY = "heat_diss_consistency"

class RiskLevel(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"

class AnnotationType(str, Enum):
    DEFECT_CONFIRMED = "defect_confirmed"
    NEAR_MISS = "near_miss"
    TECHNIQUE_ERROR = "technique_error"
    EQUIPMENT_ISSUE = "equipment_issue"

class CoachingStatus(str, Enum):
    ACTIVE = "active"
    COMPLETE = "complete"
    OVERDUE = "overdue"

class CertificationStatus(str, Enum):
    NOT_STARTED = "not_started"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    CERTIFIED = "certified"
```

**Create** `backend/schemas/shared.py`:
```python
"""
Pydantic schemas shared across multiple routes/services.
Import from here — never redefine these schemas elsewhere.
"""
from pydantic import BaseModel
from .shared_enums import WeldMetric

class MetricScore(BaseModel):
    metric: WeldMetric
    value: float  # 0.0 – 100.0
    label: str    # Human-readable display name

METRIC_LABELS: dict[WeldMetric, str] = {
    WeldMetric.ANGLE_CONSISTENCY: "Angle Consistency",
    WeldMetric.THERMAL_SYMMETRY: "Thermal Symmetry",
    WeldMetric.AMPS_STABILITY: "Amps Stability",
    WeldMetric.VOLTS_STABILITY: "Volts Stability",
    WeldMetric.HEAT_DISS_CONSISTENCY: "Heat Dissipation Consistency",
}

def make_metric_score(metric: WeldMetric, value: float) -> MetricScore:
    return MetricScore(metric=metric, value=value, label=METRIC_LABELS[metric])
```

**Modify** `backend/models/__init__.py` — add exports:
```python
from .shared_enums import (
    WeldMetric, RiskLevel, AnnotationType, CoachingStatus, CertificationStatus
)
```

---

#### Step 2: Shared TypeScript Types

**Create** `my-app/src/types/shared.ts`:
```typescript
/**
 * Canonical shared types for WarpSense.
 * Import from here. Never redefine these elsewhere.
 */

// ─── ID Types ───────────────────────────────────────────────────────────────
export type WelderID = string;
export type SessionID = string;
export type SiteID = string;
export type TeamID = string;

// ─── Metric Names ────────────────────────────────────────────────────────────
export type WeldMetric =
  | "angle_consistency"
  | "thermal_symmetry"
  | "amps_stability"
  | "volts_stability"
  | "heat_diss_consistency";

export const WELD_METRICS: WeldMetric[] = [
  "angle_consistency",
  "thermal_symmetry",
  "amps_stability",
  "volts_stability",
  "heat_diss_consistency",
];

export const METRIC_LABELS: Record<WeldMetric, string> = {
  angle_consistency: "Angle Consistency",
  thermal_symmetry: "Thermal Symmetry",
  amps_stability: "Amps Stability",
  volts_stability: "Volts Stability",
  heat_diss_consistency: "Heat Dissipation Consistency",
};

// ─── Severity / Risk ─────────────────────────────────────────────────────────
export type RiskLevel = "ok" | "warning" | "critical";
export type FeedbackSeverity = "info" | "warning";  // existing — keep compatible

// ─── Metric Score ─────────────────────────────────────────────────────────────
export interface MetricScore {
  metric: WeldMetric;
  value: number;   // 0–100
  label: string;
}

// ─── Status Enums ─────────────────────────────────────────────────────────────
export type AnnotationType =
  | "defect_confirmed"
  | "near_miss"
  | "technique_error"
  | "equipment_issue";

export type CoachingStatus = "active" | "complete" | "overdue";

export type CertificationStatus =
  | "not_started"
  | "on_track"
  | "at_risk"
  | "certified";

// ─── Pagination ───────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

---

#### Step 3: Reserve Empty Migration Files

Create these files with headers only — no SQL yet. Actual content added by owning agent.

**Create** `backend/alembic/versions/005_sites_teams.py`:
```python
"""sites and teams tables, nullable team_id on sessions

Revision ID: 005
Revises: 004
Create Date: 2026-02-18
Owner: Batch 1 Agent 1
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # FILL IN: Batch 1 Agent 1
    pass

def downgrade() -> None:
    # FILL IN: Batch 1 Agent 1
    pass
```

**Create** `backend/alembic/versions/006_session_narratives.py`:
```python
"""session_narratives cache table

Revision ID: 006
Revises: 005
Create Date: 2026-02-18
Owner: Batch 1 Agent 3
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # FILL IN: Batch 1 Agent 3
    pass

def downgrade() -> None:
    # FILL IN: Batch 1 Agent 3
    pass
```

**Create** `backend/alembic/versions/007_session_annotations.py`:
```python
"""session_annotations table

Revision ID: 007
Revises: 006
Create Date: 2026-02-18
Owner: Batch 2 Agent 2
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # FILL IN: Batch 2 Agent 2
    pass

def downgrade() -> None:
    # FILL IN: Batch 2 Agent 2
    pass
```

**Create** `backend/alembic/versions/008_coaching_drills.py`:
```python
"""drills and coaching_assignments tables

Revision ID: 008
Revises: 007
Create Date: 2026-02-18
Owner: Batch 3 Agent 2
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # FILL IN: Batch 3 Agent 2
    pass

def downgrade() -> None:
    # FILL IN: Batch 3 Agent 2
    pass
```

**Create** `backend/alembic/versions/009_certifications.py`:
```python
"""cert_standards and welder_certifications tables

Revision ID: 009
Revises: 008
Create Date: 2026-02-18
Owner: Batch 3 Agent 3
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # FILL IN: Batch 3 Agent 3
    pass

def downgrade() -> None:
    # FILL IN: Batch 3 Agent 3
    pass
```

---

#### Step 4: welders.py Router Stub

**Create** `backend/routes/welders.py`:
```python
"""
Welder-scoped API routes.
All /api/welders/{welder_id}/... endpoints live here.
Do NOT add welder routes to sessions.py or aggregate.py.

Routes added per batch:
  Batch 2: GET /api/welders/{welder_id}/trajectory
  Batch 3: GET /api/welders/{welder_id}/benchmarks
  Batch 3: GET /api/welders/{welder_id}/coaching-plan
  Batch 3: POST /api/welders/{welder_id}/coaching-plan
  Batch 3: GET /api/welders/{welder_id}/certification-status
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db

router = APIRouter(prefix="/api/welders", tags=["welders"])


@router.get("/health")
def welders_health():
    """Stub health check — confirms router is registered."""
    return {"status": "ok", "router": "welders"}
```

**Modify** `backend/main.py` — add import and include:
```python
from .routes import welders  # add this import
# In app setup:
app.include_router(welders.router)
```

---

#### Step 5: ReportLayout Component

**Create** `my-app/src/components/layout/ReportLayout.tsx`:
```typescript
/**
 * ReportLayout — slot-based layout for welder report page.
 *
 * RULES:
 * - Never add feature logic here
 * - Never remove a slot — only add new ones
 * - All slots are optional — absent slots render nothing
 * - This component owns the visual grid; feature panels own their content
 */
import React from "react";
import { SessionID, WelderID } from "@/types/shared";

export interface ReportLayoutProps {
  // ─── Header data ───────────────────────────────────────────────────────────
  welderName: string;
  sessionId: SessionID;
  scoreTotal: number;
  weldType?: string;
  sessionDate?: string;

  // ─── Feature slots (all optional) ─────────────────────────────────────────
  /** AI Narrative — Batch 1/2 */
  narrative?: React.ReactNode;
  /** Side-by-side heatmaps — existing content */
  heatmaps?: React.ReactNode;
  /** Micro-feedback panel — existing content */
  feedback?: React.ReactNode;
  /** Longitudinal trend chart — Batch 2 */
  trajectory?: React.ReactNode;
  /** Benchmark distribution panel — Batch 3 */
  benchmarks?: React.ReactNode;
  /** Coaching drill assignments — Batch 3 */
  coaching?: React.ReactNode;
  /** Certification readiness — Batch 3 */
  certification?: React.ReactNode;
  /** Back link / actions bar — existing */
  actions?: React.ReactNode;
}

export function ReportLayout({
  welderName,
  sessionId,
  scoreTotal,
  weldType,
  sessionDate,
  narrative,
  heatmaps,
  feedback,
  trajectory,
  benchmarks,
  coaching,
  certification,
  actions,
}: ReportLayoutProps) {
  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="border-b border-neutral-800 bg-neutral-900 px-8 py-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{welderName}</h1>
            <p className="text-sm text-neutral-400 mt-1">
              Session: {sessionId}
              {weldType && <span className="ml-3 text-neutral-500">{weldType.toUpperCase()}</span>}
              {sessionDate && <span className="ml-3 text-neutral-500">{sessionDate}</span>}
            </p>
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold text-cyan-400">{scoreTotal}</div>
            <div className="text-xs text-neutral-400 mt-1">/ 100</div>
          </div>
        </div>
        {actions && <div className="mt-4">{actions}</div>}
      </div>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div className="px-8 py-6 space-y-8 max-w-7xl mx-auto">
        {narrative && (
          <section aria-label="AI Narrative">
            {narrative}
          </section>
        )}

        {heatmaps && (
          <section aria-label="Thermal Heatmaps">
            {heatmaps}
          </section>
        )}

        {feedback && (
          <section aria-label="Micro Feedback">
            {feedback}
          </section>
        )}

        {trajectory && (
          <section aria-label="Skill Trajectory">
            {trajectory}
          </section>
        )}

        {benchmarks && (
          <section aria-label="Benchmark Comparison">
            {benchmarks}
          </section>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {coaching && (
            <section aria-label="Coaching Plan">
              {coaching}
            </section>
          )}
          {certification && (
            <section aria-label="Certification Status">
              {certification}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

export default ReportLayout;
```

---

#### Step 6: Refactor seagull/welder/[id]/page.tsx

**Modify** `my-app/src/app/seagull/welder/[id]/page.tsx`:

Move all existing JSX into the new slot structure. The refactor is structural only — no logic changes.

Before (conceptual):
```tsx
return (
  <div>
    <header>...</header>
    <HeatMap />
    <HeatMap />
    <FeedbackPanel />
    <LineChart />
    ...
  </div>
)
```

After:
```tsx
return (
  <ReportLayout
    welderName={welder.name}
    sessionId={session.session_id}
    scoreTotal={score.total}
    weldType={session.weld_type}
    actions={<ActionsBar />}
    heatmaps={<SideBySideHeatmaps session={session} expertSession={expertSession} />}
    feedback={<FeedbackPanel items={feedbackResult.feedback_items} />}
    // narrative={} — empty for now, Batch 2 Agent 3 fills this
    // trajectory={} — empty for now, Batch 2 Agent 1 fills this
    // benchmarks={} — empty for now, Batch 3 Agent 1 fills this
    // coaching={} — empty for now, Batch 3 Agent 2 fills this
    // certification={} — empty for now, Batch 3 Agent 3 fills this
  />
)
```

Extract the heatmaps and actions bar into small local components inside the same file to keep JSX clean. Do not create new files for these — they are page-specific subcomponents.

---

#### Batch 0 Verification Checklist
- [ ] `GET /api/welders/health` returns `{ status: "ok" }`
- [ ] `backend/models/shared_enums.py` imports cleanly from routes/sessions.py without circular imports
- [ ] `my-app/src/types/shared.ts` exports all types with zero TS errors
- [ ] `ReportLayout` renders existing welder report correctly (visual regression: no change in output)
- [ ] All 5 migration files exist with correct `down_revision` chain: 005→006→007→008→009
- [ ] `npm run build` passes
- [ ] `pytest backend/tests/ -x` passes

---

## BATCH 1 — THREE AGENTS IN PARALLEL
**Prerequisite:** Batch 0 complete and verified.
**Duration:** Days 2–8.
**Agents:** Multi-Site Data Model | Warp Prediction ML | AI Narrative Engine

---

### Batch 1 Agent 1 — Multi-Site Data Model

**Files owned:** `005_sites_teams.py`, `backend/models/site.py`, `backend/schemas/site.py`
**Files read (not modified):** `backend/models/shared_enums.py`, `backend/database.py`
**Files NOT touched:** Any route, any frontend file, any other migration

---

#### Step 1: Fill Migration 005

**Modify** `backend/alembic/versions/005_sites_teams.py`:
```python
def upgrade() -> None:
    # ── sites ──────────────────────────────────────────────────────────────
    op.create_table(
        "sites",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    # ── teams ──────────────────────────────────────────────────────────────
    op.create_table(
        "teams",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("site_id", sa.String(64),
                  sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_teams_site_id", "teams", ["site_id"])

    # ── sessions.team_id — nullable FK, zero data impact ──────────────────
    op.add_column(
        "sessions",
        sa.Column("team_id", sa.String(64),
                  sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_sessions_team_id", "sessions", ["team_id"])

def downgrade() -> None:
    op.drop_index("ix_sessions_team_id", "sessions")
    op.drop_column("sessions", "team_id")
    op.drop_index("ix_teams_site_id", "teams")
    op.drop_table("teams")
    op.drop_table("sites")
```

---

#### Step 2: SQLAlchemy Models

**Create** `backend/models/site.py`:
```python
"""
SQLAlchemy models for Site and Team.
Sessions reference Team via nullable team_id FK.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    location = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    teams = relationship("Team", back_populates="site", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String(64), primary_key=True)
    site_id = Column(String(64), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    site = relationship("Site", back_populates="teams")
```

**Modify** `backend/models/session.py` — add team_id column (no relationship needed for MVP):
```python
# Add to SessionModel class:
team_id = Column(String(64), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
```

---

#### Step 3: Pydantic Schemas

**Create** `backend/schemas/site.py`:
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class SiteCreate(BaseModel):
    id: str
    name: str
    location: Optional[str] = None


class TeamCreate(BaseModel):
    id: str
    site_id: str
    name: str


class TeamResponse(BaseModel):
    id: str
    site_id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class SiteResponse(BaseModel):
    id: str
    name: str
    location: Optional[str]
    created_at: datetime
    teams: List[TeamResponse] = []

    class Config:
        from_attributes = True
```

---

#### Step 4: Seed One Demo Site

**Modify** `backend/scripts/seed_demo_data.py` — append at bottom of seed function:
```python
def _seed_demo_site(db: Session) -> None:
    """Seed one demo site and team for multi-site UI testing."""
    from ..models.site import Site, Team
    if db.query(Site).filter_by(id="site_demo_001").first():
        return
    site = Site(id="site_demo_001", name="Harbor Shipyard", location="Singapore")
    team = Team(id="team_demo_001", site_id="site_demo_001", name="Bay 3 Welding Team")
    db.add(site)
    db.add(team)
    db.commit()
```

---

#### Batch 1 Agent 1 Verification Checklist
- [ ] `alembic upgrade 005` runs without error on a clean DB
- [ ] `alembic downgrade 004` reverts cleanly
- [ ] `sessions` table has nullable `team_id` column
- [ ] `Site` and `Team` models import without circular dependency
- [ ] Existing session endpoints still pass all tests (team_id=null is transparent)

---

### Batch 1 Agent 2 — Warp Prediction ML

**Files owned:** `backend/scripts/generate_training_data.py`, `backend/scripts/train_warp_model.py`, `backend/services/prediction_service.py`, `backend/routes/predictions.py`, `my-app/src/components/welding/WarpRiskGauge.tsx`, `my-app/src/types/prediction.ts`
**Files read:** `backend/data/mock_sessions.py`, `backend/models/shared_enums.py`, `my-app/src/types/shared.ts`
**Files NOT touched:** Any migration, welders.py, narrative files, ReportLayout

---

#### Step 1: Training Data Generation

**Create** `backend/scripts/generate_training_data.py`:
```python
"""
Generates training_data.csv for warp prediction model.

Feature vector per frame (rolling 50-frame window):
  - angle_mean: mean angle_degrees over window
  - angle_std: std dev of angle_degrees over window
  - amps_mean: mean amps over window
  - amps_std: std dev of amps over window
  - volts_mean: mean volts over window
  - temp_current: center temperature at frame (carry-forward)
  - thermal_asymmetry: max(|N-S|, |E-W|) if thermal data present, else -1
  - thermal_asymmetry_delta: change in asymmetry vs 10 frames prior, else 0

Label:
  - will_breach: 1 if thermal asymmetry >= 20°C within next 30 frames, else 0

Usage:
  python -m backend.scripts.generate_training_data --output data/training_data.csv
"""
import argparse
import csv
import sys
from pathlib import Path

# Insert project root so backend package resolves
sys.path.insert(0, str(Path(__file__).parents[2]))

from backend.data.mock_sessions import generate_session_for_welder
from backend.data.mock_welders import WELDER_ARCHETYPES

WINDOW_SIZE = 50          # frames in rolling window
LOOKAHEAD_FRAMES = 30     # frames to look ahead for breach label
THERMAL_BREACH_CELSIUS = 20.0  # asymmetry threshold

def extract_asymmetry(frame: dict) -> float:
    """Returns max cardinal asymmetry or -1 if no thermal data."""
    snapshots = frame.get("thermal_snapshots") or []
    if not snapshots:
        return -1.0
    readings = {r["direction"]: r["temp_celsius"] for r in snapshots[0]["readings"]}
    ns = abs(readings.get("north", 0) - readings.get("south", 0))
    ew = abs(readings.get("east", 0) - readings.get("west", 0))
    return max(ns, ew)

def extract_features(window: list[dict], frame: dict) -> dict:
    angles = [f.get("angle_degrees", 45.0) for f in window if f.get("angle_degrees") is not None]
    amps = [f.get("amps", 150.0) for f in window if f.get("amps") is not None]
    volts = [f.get("volts", 22.0) for f in window if f.get("volts") is not None]

    import statistics
    asym = extract_asymmetry(frame)
    prev_frame = window[-10] if len(window) >= 10 else window[0]
    prev_asym = extract_asymmetry(prev_frame)
    asym_delta = (asym - prev_asym) if asym >= 0 and prev_asym >= 0 else 0.0

    # Carry-forward center temp
    temp = -1.0
    for f in reversed(window):
        snapshots = f.get("thermal_snapshots") or []
        if snapshots:
            for r in snapshots[0]["readings"]:
                if r["direction"] == "center":
                    temp = r["temp_celsius"]
                    break
        if temp >= 0:
            break

    return {
        "angle_mean": statistics.mean(angles) if angles else 45.0,
        "angle_std": statistics.stdev(angles) if len(angles) > 1 else 0.0,
        "amps_mean": statistics.mean(amps) if amps else 150.0,
        "amps_std": statistics.stdev(amps) if len(amps) > 1 else 0.0,
        "volts_mean": statistics.mean(volts) if volts else 22.0,
        "temp_current": temp,
        "thermal_asymmetry": asym,
        "thermal_asymmetry_delta": asym_delta,
    }

def compute_labels(frames: list[dict]) -> list[int]:
    """Returns 1 if asymmetry breach within LOOKAHEAD_FRAMES, else 0."""
    labels = []
    for i, _ in enumerate(frames):
        lookahead = frames[i: i + LOOKAHEAD_FRAMES]
        breach = any(
            extract_asymmetry(f) >= THERMAL_BREACH_CELSIUS
            for f in lookahead
        )
        labels.append(1 if breach else 0)
    return labels

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/training_data.csv")
    args = parser.parse_args()

    rows = []
    for welder in WELDER_ARCHETYPES:
        for session_idx in range(welder["sessions"]):
            session = generate_session_for_welder(
                welder["welder_id"], welder["arc"], session_idx,
                f"sess_{welder['welder_id']}_{session_idx + 1:03d}"
            )
            frames = [f.dict() if hasattr(f, "dict") else f for f in session.frames]
            labels = compute_labels(frames)

            for i in range(WINDOW_SIZE, len(frames)):
                window = frames[i - WINDOW_SIZE: i]
                features = extract_features(window, frames[i])
                features["will_breach"] = labels[i]
                rows.append(features)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    pos = sum(r["will_breach"] for r in rows)
    print(f"Generated {len(rows)} samples. Positive rate: {pos/len(rows):.2%}")

if __name__ == "__main__":
    main()
```

---

#### Step 2: Model Training

**Create** `backend/scripts/train_warp_model.py`:
```python
"""
Trains warp prediction model and exports to ONNX.

Usage:
  python -m backend.scripts.train_warp_model \
    --input data/training_data.csv \
    --output backend/models/warp_model.onnx

Requirements (add to requirements.txt):
  scikit-learn>=1.4.0
  skl2onnx>=1.16.0
  onnxruntime>=1.17.0
"""
import argparse
import csv
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/training_data.csv")
    parser.add_argument("--output", default="backend/models/warp_model.onnx")
    args = parser.parse_args()

    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import roc_auc_score
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    FEATURE_COLS = [
        "angle_mean", "angle_std", "amps_mean", "amps_std",
        "volts_mean", "temp_current", "thermal_asymmetry", "thermal_asymmetry_delta"
    ]

    with open(args.input) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    X = np.array([[float(r[c]) for c in FEATURE_COLS] for r in rows], dtype=np.float32)
    y = np.array([int(r["will_breach"]) for r in rows])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=500)),
    ])
    pipeline.fit(X_train, y_train)

    y_prob = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    print(f"Test AUC: {auc:.4f}")
    if auc < 0.70:
        print("WARNING: AUC below 0.70 — check training data quality")

    # Export ONNX
    initial_type = [("float_input", FloatTensorType([None, len(FEATURE_COLS)]))]
    onnx_model = convert_sklearn(pipeline, initial_types=initial_type)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"Exported to {args.output}")

if __name__ == "__main__":
    main()
```

---

#### Step 3: Prediction Service

**Create** `backend/services/prediction_service.py`:
```python
"""
Warp prediction service.
Loads ONNX model at startup; exposes predict_warp_risk().

The ONNX model path is resolved relative to this file.
If the model file does not exist, service degrades gracefully
(returns RiskLevel.OK with probability 0.0).
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np

from ..models.shared_enums import RiskLevel

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / "models" / "warp_model.onnx"

FEATURE_COLS = [
    "angle_mean", "angle_std", "amps_mean", "amps_std",
    "volts_mean", "temp_current", "thermal_asymmetry", "thermal_asymmetry_delta",
]

WARNING_THRESHOLD = 0.55
CRITICAL_THRESHOLD = 0.75

_session: Optional[object] = None  # onnxruntime.InferenceSession


def _get_session():
    global _session
    if _session is None:
        if not MODEL_PATH.exists():
            logger.warning("warp_model.onnx not found — prediction service degraded")
            return None
        try:
            import onnxruntime as ort
            _session = ort.InferenceSession(str(MODEL_PATH))
            logger.info("Warp prediction model loaded from %s", MODEL_PATH)
        except Exception as e:
            logger.error("Failed to load warp model: %s", e)
    return _session


def predict_warp_risk(frame_window: list[dict]) -> dict:
    """
    Given a window of up to 50 frames (as dicts), returns:
    {
        "probability": float,          # 0.0 – 1.0
        "risk_level": RiskLevel,       # "ok" | "warning" | "critical"
        "model_available": bool,
    }

    Frames are raw frame dicts matching the Frame schema.
    """
    sess = _get_session()
    if sess is None:
        return {"probability": 0.0, "risk_level": RiskLevel.OK, "model_available": False}

    try:
        features = _extract_features(frame_window)
        X = np.array([[features[c] for c in FEATURE_COLS]], dtype=np.float32)
        input_name = sess.get_inputs()[0].name
        result = sess.run(None, {input_name: X})
        # result[1] = [{0: p_negative, 1: p_positive}] for LogisticRegression
        prob = float(result[1][0][1])

        if prob >= CRITICAL_THRESHOLD:
            level = RiskLevel.CRITICAL
        elif prob >= WARNING_THRESHOLD:
            level = RiskLevel.WARNING
        else:
            level = RiskLevel.OK

        return {"probability": round(prob, 4), "risk_level": level, "model_available": True}
    except Exception as e:
        logger.error("predict_warp_risk error: %s", e)
        return {"probability": 0.0, "risk_level": RiskLevel.OK, "model_available": False}


def _extract_asymmetry(frame: dict) -> float:
    snapshots = frame.get("thermal_snapshots") or []
    if not snapshots:
        return -1.0
    readings = {r["direction"]: r["temp_celsius"] for r in snapshots[0]["readings"]}
    ns = abs(readings.get("north", 0) - readings.get("south", 0))
    ew = abs(readings.get("east", 0) - readings.get("west", 0))
    return max(ns, ew)


def _extract_features(window: list[dict]) -> dict:
    import statistics
    angles = [f.get("angle_degrees", 45.0) for f in window if f.get("angle_degrees") is not None]
    amps = [f.get("amps", 150.0) for f in window if f.get("amps") is not None]
    volts = [f.get("volts", 22.0) for f in window if f.get("volts") is not None]

    asym = _extract_asymmetry(window[-1]) if window else -1.0
    prev = window[-10] if len(window) >= 10 else window[0]
    prev_asym = _extract_asymmetry(prev)
    asym_delta = (asym - prev_asym) if asym >= 0 and prev_asym >= 0 else 0.0

    temp = -1.0
    for f in reversed(window):
        snapshots = f.get("thermal_snapshots") or []
        if snapshots:
            for r in snapshots[0]["readings"]:
                if r["direction"] == "center":
                    temp = r["temp_celsius"]
                    break
        if temp >= 0:
            break

    return {
        "angle_mean": statistics.mean(angles) if angles else 45.0,
        "angle_std": statistics.stdev(angles) if len(angles) > 1 else 0.0,
        "amps_mean": statistics.mean(amps) if amps else 150.0,
        "amps_std": statistics.stdev(amps) if len(amps) > 1 else 0.0,
        "volts_mean": statistics.mean(volts) if volts else 22.0,
        "temp_current": temp,
        "thermal_asymmetry": asym,
        "thermal_asymmetry_delta": asym_delta,
    }
```

---

#### Step 4: Predictions Route

**Create** `backend/routes/predictions.py`:
```python
"""
Warp risk prediction endpoints.
Separate from welders.py and sessions.py — prediction is session-scoped but orthogonal.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal

from ..database import get_db
from ..models.shared_enums import RiskLevel
from ..services.prediction_service import predict_warp_risk
from ..routes.sessions import get_session_frames_raw  # reuse existing helper

router = APIRouter(prefix="/api/sessions", tags=["predictions"])


class WarpRiskResponse(BaseModel):
    session_id: str
    probability: float
    risk_level: RiskLevel
    model_available: bool
    window_frames_used: int


@router.get("/{session_id}/warp-risk", response_model=WarpRiskResponse)
def get_warp_risk(session_id: str, db: Session = Depends(get_db)):
    """
    Returns warp risk probability for the most recent 50 frames of a session.
    Uses ONNX model. Degrades gracefully if model unavailable.
    """
    frames = get_session_frames_raw(session_id, db, limit=50)
    if frames is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    result = predict_warp_risk(frames)
    return WarpRiskResponse(
        session_id=session_id,
        window_frames_used=len(frames),
        **result,
    )
```

**Note:** `get_session_frames_raw` is a helper you add to `backend/routes/sessions.py`:
```python
def get_session_frames_raw(session_id: str, db: Session, limit: int = 50) -> list[dict] | None:
    """Returns the last `limit` frames of a session as raw dicts, or None if not found."""
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        return None
    frames = (
        db.query(FrameModel)
        .filter_by(session_id=session_id)
        .order_by(FrameModel.timestamp_ms.desc())
        .limit(limit)
        .all()
    )
    return [f.to_dict() for f in reversed(frames)]
```

**Modify** `backend/main.py`:
```python
from .routes import predictions
app.include_router(predictions.router)
```

---

#### Step 5: Frontend Types + Component

**Create** `my-app/src/types/prediction.ts`:
```typescript
import { RiskLevel, SessionID } from "./shared";

export interface WarpRiskResponse {
  session_id: SessionID;
  probability: number;        // 0.0 – 1.0
  risk_level: RiskLevel;
  model_available: boolean;
  window_frames_used: number;
}
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { WarpRiskResponse } from "@/types/prediction";
import { SessionID } from "@/types/shared";

export async function fetchWarpRisk(sessionId: SessionID): Promise<WarpRiskResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/warp-risk`);
  if (!res.ok) throw new Error(`fetchWarpRisk failed: ${res.status}`);
  return res.json();
}
```

**Create** `my-app/src/components/welding/WarpRiskGauge.tsx`:
```typescript
/**
 * WarpRiskGauge — semicircle probability gauge for warp prediction.
 *
 * Props:
 *   probability: 0.0–1.0
 *   riskLevel: "ok" | "warning" | "critical"
 *   modelAvailable: boolean
 *
 * Colours:
 *   ok       → cyan-400
 *   warning  → amber-400
 *   critical → red-500
 */
"use client";
import React from "react";
import { RiskLevel } from "@/types/shared";

interface WarpRiskGaugeProps {
  probability: number;
  riskLevel: RiskLevel;
  modelAvailable: boolean;
  className?: string;
}

const RISK_COLORS: Record<RiskLevel, { stroke: string; text: string; bg: string }> = {
  ok:       { stroke: "#22d3ee", text: "text-cyan-400",  bg: "bg-cyan-400/10" },
  warning:  { stroke: "#fbbf24", text: "text-amber-400", bg: "bg-amber-400/10" },
  critical: { stroke: "#ef4444", text: "text-red-500",   bg: "bg-red-500/10" },
};

const RISK_LABELS: Record<RiskLevel, string> = {
  ok:       "LOW RISK",
  warning:  "WARP WARNING",
  critical: "WARP CRITICAL",
};

export function WarpRiskGauge({
  probability,
  riskLevel,
  modelAvailable,
  className = "",
}: WarpRiskGaugeProps) {
  const colors = RISK_COLORS[riskLevel];
  const pct = Math.min(1, Math.max(0, probability));

  // Semicircle SVG: centre (60,60), radius 50, sweep from 180° to 0°
  const r = 50;
  const cx = 60;
  const cy = 60;
  const startAngle = Math.PI;           // leftmost point
  const endAngle = startAngle - pct * Math.PI;  // sweeps right as pct increases
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = pct > 0.5 ? 1 : 0;

  if (!modelAvailable) {
    return (
      <div className={`flex flex-col items-center ${className}`}>
        <div className="text-xs text-neutral-500 uppercase tracking-widest">Warp Risk</div>
        <div className="text-xs text-neutral-600 mt-1">Model unavailable</div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col items-center ${colors.bg} rounded-lg p-4 ${className}`}>
      <div className="text-xs text-neutral-400 uppercase tracking-widest mb-2">Warp Risk</div>
      <svg width="120" height="70" viewBox="0 0 120 70" aria-label={`Warp risk: ${Math.round(pct * 100)}%`}>
        {/* Track */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#262626"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Active arc */}
        {pct > 0 && (
          <path
            d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
            fill="none"
            stroke={colors.stroke}
            strokeWidth="10"
            strokeLinecap="round"
          />
        )}
        {/* Percentage text */}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fill={colors.stroke}
          fontSize="18"
          fontWeight="bold"
          fontFamily="monospace"
        >
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <div className={`text-xs font-semibold tracking-widest ${colors.text} mt-1`}>
        {RISK_LABELS[riskLevel]}
      </div>
    </div>
  );
}

export default WarpRiskGauge;
```

**Wire into replay page** — `my-app/src/app/replay/[sessionId]/page.tsx`:

Add to imports:
```typescript
import dynamic from "next/dynamic";
import { fetchWarpRisk } from "@/lib/api";
import { WarpRiskResponse } from "@/types/prediction";

const WarpRiskGauge = dynamic(
  () => import("@/components/welding/WarpRiskGauge").then((m) => m.WarpRiskGauge),
  { ssr: false }
);
```

Add state:
```typescript
const [warpRisk, setWarpRisk] = useState<WarpRiskResponse | null>(null);

useEffect(() => {
  let mounted = true;
  fetchWarpRisk(sessionId)
    .then((r) => { if (mounted) setWarpRisk(r); })
    .catch(() => {}); // non-critical
  return () => { mounted = false; };
}, [sessionId]);
```

Render alongside TorchViz3D:
```tsx
{warpRisk && (
  <WarpRiskGauge
    probability={warpRisk.probability}
    riskLevel={warpRisk.risk_level}
    modelAvailable={warpRisk.model_available}
  />
)}
```

---

#### Batch 1 Agent 2 Verification Checklist
- [ ] `generate_training_data.py` produces CSV with balanced classes (positive rate 10–40%)
- [ ] `train_warp_model.py` reports AUC ≥ 0.70
- [ ] `warp_model.onnx` exists at `backend/models/warp_model.onnx`
- [ ] `GET /api/sessions/sess_novice_001/warp-risk` returns valid JSON
- [ ] Degraded mode (no ONNX file): returns `{ probability: 0.0, risk_level: "ok", model_available: false }`
- [ ] WarpRiskGauge renders all three risk states (ok/warning/critical) in Storybook / visual test
- [ ] `npm run build` passes

---

### Batch 1 Agent 3 — AI Narrative Engine

**Files owned:** `006_session_narratives.py`, `backend/models/narrative.py`, `backend/schemas/narrative.py`, `backend/services/narrative_service.py`, `backend/routes/narratives.py`, `my-app/src/lib/narrative-prompt.ts`, `my-app/src/components/welding/NarrativePanel.tsx`, `my-app/src/types/narrative.ts`
**Files read:** `backend/models/shared_enums.py`, `my-app/src/types/shared.ts`
**Files NOT touched:** Any migration except 006, welders.py, predictions files, ReportLayout

---

#### Step 1: Fill Migration 006

**Modify** `backend/alembic/versions/006_session_narratives.py`:
```python
def upgrade() -> None:
    op.create_table(
        "session_narratives",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(64),
                  sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
                  unique=True, nullable=False),
        sa.Column("narrative_text", sa.Text, nullable=False),
        sa.Column("score_snapshot", sa.Float, nullable=True),  # score at generation time
        sa.Column("model_version", sa.String(64), nullable=False, default="claude-sonnet-4-6"),
        sa.Column("generated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_session_narratives_session_id", "session_narratives", ["session_id"])

def downgrade() -> None:
    op.drop_index("ix_session_narratives_session_id", "session_narratives")
    op.drop_table("session_narratives")
```

---

#### Step 2: SQLAlchemy Model

**Create** `backend/models/narrative.py`:
```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, func
from ..database import Base


class SessionNarrative(Base):
    __tablename__ = "session_narratives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"),
        unique=True, nullable=False
    )
    narrative_text = Column(Text, nullable=False)
    score_snapshot = Column(Float, nullable=True)
    model_version = Column(String(64), nullable=False, default="claude-sonnet-4-6")
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

---

#### Step 3: Pydantic Schemas

**Create** `backend/schemas/narrative.py`:
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NarrativeResponse(BaseModel):
    session_id: str
    narrative_text: str
    model_version: str
    generated_at: datetime
    cached: bool  # True if returned from DB cache

    class Config:
        from_attributes = True


class NarrativeGenerateRequest(BaseModel):
    force_regenerate: bool = False
```
---

#### Step 4: Narrative Service

**Create** `backend/services/narrative_service.py`:
```python
"""
Narrative generation service.
Calls Anthropic API; caches result in session_narratives table.
Re-generates only if score changed or force_regenerate=True.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import anthropic
from sqlalchemy.orm import Session as DBSession

from ..models.narrative import SessionNarrative
from ..models.session import SessionModel
from ..schemas.narrative import NarrativeResponse

logger = logging.getLogger(__name__)

MODEL_ID = "claude-sonnet-4-6"
MAX_NARRATIVE_TOKENS = 600


def get_or_generate_narrative(
    session_id: str,
    db: DBSession,
    force_regenerate: bool = False,
) -> NarrativeResponse:
    """
    Returns cached narrative if available and score unchanged.
    Otherwise calls Anthropic and caches result.
    Raises ValueError if session not found.
    """
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")

    current_score = session.score_total

    # Check cache
    if not force_regenerate:
        cached = db.query(SessionNarrative).filter_by(session_id=session_id).first()
        if cached:
            score_unchanged = (
                cached.score_snapshot is None
                or current_score is None
                or abs(cached.score_snapshot - current_score) < 0.01
            )
            if score_unchanged:
                return NarrativeResponse(
                    session_id=session_id,
                    narrative_text=cached.narrative_text,
                    model_version=cached.model_version,
                    generated_at=cached.generated_at,
                    cached=True,
                )

    # Build context for prompt
    context = _build_session_context(session_id, db)
    prompt = _build_prompt(context)

    # Call Anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL_ID,
        max_tokens=MAX_NARRATIVE_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    narrative_text = message.content[0].text.strip()

    # Upsert cache
    existing = db.query(SessionNarrative).filter_by(session_id=session_id).first()
    if existing:
        existing.narrative_text = narrative_text
        existing.score_snapshot = current_score
        existing.model_version = MODEL_ID
        existing.generated_at = datetime.now(timezone.utc)
    else:
        record = SessionNarrative(
            session_id=session_id,
            narrative_text=narrative_text,
            score_snapshot=current_score,
            model_version=MODEL_ID,
        )
        db.add(record)
    db.commit()

    return NarrativeResponse(
        session_id=session_id,
        narrative_text=narrative_text,
        model_version=MODEL_ID,
        generated_at=datetime.now(timezone.utc),
        cached=False,
    )


def _build_session_context(session_id: str, db: DBSession) -> dict:
    """Pulls score, rules, and recent welder history for prompt building."""
    from ..services.scoring_service import get_session_score  # existing
    score = get_session_score(session_id, db)

    # Get last 5 score_totals for this welder (via operator_id)
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    historical_scores = []
    if session and session.operator_id:
        history = (
            db.query(SessionModel.score_total)
            .filter(
                SessionModel.operator_id == session.operator_id,
                SessionModel.session_id != session_id,
                SessionModel.score_total.isnot(None),
            )
            .order_by(SessionModel.start_time.desc())
            .limit(5)
            .all()
        )
        historical_scores = [h.score_total for h in history]

    return {
        "session_id": session_id,
        "weld_type": session.weld_type if session else "unknown",
        "score_total": score.total if score else None,
        "rules": [
            {"name": r.name, "score": r.score, "status": r.status}
            for r in (score.rules if score else [])
        ],
        "historical_scores": historical_scores,
    }


def _build_prompt(ctx: dict) -> str:
    """
    Builds the Anthropic prompt.
    System instructions enforce 3-paragraph structure.
    """
    historical_str = (
        ", ".join(str(round(s)) for s in ctx["historical_scores"])
        if ctx["historical_scores"]
        else "no prior sessions"
    )

    failing = [r for r in ctx["rules"] if r["status"] != "pass"]
    passing = [r for r in ctx["rules"] if r["status"] == "pass"]

    return f"""You are WarpSense, an industrial welding quality AI coach.
Write exactly 3 paragraphs for a welder performance report. Do not use headers, bullets, or markdown.

Session data:
- Weld type: {ctx['weld_type'].upper()}
- Overall score: {ctx['score_total'] or 'N/A'} / 100
- Failing rules: {', '.join(r['name'] for r in failing) or 'none'}
- Passing rules: {', '.join(r['name'] for r in passing) or 'none'}
- Recent score history: {historical_str}

Paragraph 1 (2 sentences): Overall verdict. State the score and whether the weld meets quality standards.
Paragraph 2 (2-3 sentences): Specific evidence. Reference the exact failing metrics by name and describe what they indicate physically about the weld technique.
Paragraph 3 (2 sentences): Actionable correction. Give one specific technique adjustment and state the expected improvement.

Tone: direct, technical, coach-like. No filler phrases."""
```

---

#### Step 5: Narrative Route

**Create** `backend/routes/narratives.py`:
```python
"""
Session narrative endpoints.
GET returns cached narrative (404 if none generated yet).
POST generates (or regenerates) and caches narrative.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.narrative import SessionNarrative
from ..schemas.narrative import NarrativeResponse, NarrativeGenerateRequest
from ..services.narrative_service import get_or_generate_narrative

router = APIRouter(prefix="/api/sessions", tags=["narratives"])


@router.get("/{session_id}/narrative", response_model=NarrativeResponse)
def get_narrative(session_id: str, db: Session = Depends(get_db)):
    """Returns cached narrative. 404 if not yet generated."""
    cached = db.query(SessionNarrative).filter_by(session_id=session_id).first()
    if not cached:
        raise HTTPException(status_code=404, detail="Narrative not yet generated")
    return NarrativeResponse(
        session_id=session_id,
        narrative_text=cached.narrative_text,
        model_version=cached.model_version,
        generated_at=cached.generated_at,
        cached=True,
    )


@router.post("/{session_id}/narrative", response_model=NarrativeResponse)
def generate_narrative(
    session_id: str,
    body: NarrativeGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generates and caches narrative. Regenerates if force_regenerate=True."""
    try:
        return get_or_generate_narrative(session_id, db, force_regenerate=body.force_regenerate)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# Register in main.py
```

**Modify** `backend/main.py`:
```python
from .routes import narratives
app.include_router(narratives.router)
```

---

#### Step 6: Frontend Types

**Create** `my-app/src/types/narrative.ts`:
```typescript
import { SessionID } from "./shared";

export interface NarrativeResponse {
  session_id: SessionID;
  narrative_text: string;
  model_version: string;
  generated_at: string;   // ISO 8601
  cached: boolean;
}
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { NarrativeResponse } from "@/types/narrative";

export async function fetchNarrative(sessionId: SessionID): Promise<NarrativeResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/narrative`);
  if (!res.ok) throw new Error(`fetchNarrative failed: ${res.status}`);
  return res.json();
}

export async function generateNarrative(
  sessionId: SessionID,
  forceRegenerate = false
): Promise<NarrativeResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/narrative`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_regenerate: forceRegenerate }),
  });
  if (!res.ok) throw new Error(`generateNarrative failed: ${res.status}`);
  return res.json();
}
```

---

#### Step 7: NarrativePanel Component

**Create** `my-app/src/components/welding/NarrativePanel.tsx`:
```typescript
/**
 * NarrativePanel — displays AI-generated narrative for a session.
 * Fetches on mount; shows loading/error states.
 * "Regenerate" triggers POST with force_regenerate=true.
 */
"use client";
import React, { useEffect, useState } from "react";
import { SessionID } from "@/types/shared";
import { NarrativeResponse } from "@/types/narrative";
import { fetchNarrative, generateNarrative } from "@/lib/api";
import { logError } from "@/lib/logger";

interface NarrativePanelProps {
  sessionId: SessionID;
}

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "generating" }
  | { status: "ready"; data: NarrativeResponse }
  | { status: "error"; message: string };

export function NarrativePanel({ sessionId }: NarrativePanelProps) {
  const [state, setState] = useState<State>({ status: "loading" });

  const load = (forceRegenerate = false) => {
    setState({ status: forceRegenerate ? "generating" : "loading" });
    const action = forceRegenerate
      ? generateNarrative(sessionId, true)
      : fetchNarrative(sessionId).catch(() => generateNarrative(sessionId, false));

    let mounted = true;
    action
      .then((data) => { if (mounted) setState({ status: "ready", data }); })
      .catch((err) => {
        logError("NarrativePanel", err);
        if (mounted) setState({ status: "error", message: "Failed to generate narrative." });
      });
    return () => { mounted = false; };
  };

  useEffect(() => load(), [sessionId]);

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          AI Coach Report
        </h2>
        {state.status === "ready" && (
          <div className="flex items-center gap-4">
            <span className="text-xs text-neutral-600">
              {state.data.cached ? "Cached" : "Generated"} · {formatDate(state.data.generated_at)}
            </span>
            <button
              onClick={() => load(true)}
              className="text-xs text-cyan-400 hover:text-cyan-300 underline"
            >
              Regenerate
            </button>
          </div>
        )}
      </div>

      {(state.status === "loading" || state.status === "generating") && (
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-neutral-800 rounded w-full" />
          <div className="h-4 bg-neutral-800 rounded w-5/6" />
          <div className="h-4 bg-neutral-800 rounded w-4/6" />
        </div>
      )}

      {state.status === "error" && (
        <p className="text-sm text-red-400">{state.message}</p>
      )}

      {state.status === "ready" && (
        <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-line">
          {state.data.narrative_text}
        </p>
      )}
    </div>
  );
}

export default NarrativePanel;
```

---

#### Batch 1 Agent 3 Verification Checklist
- [ ] `POST /api/sessions/sess_novice_001/narrative` returns 200 with narrative_text
- [ ] Second call with same session returns `cached: true`
- [ ] `POST` with `force_regenerate: true` calls Anthropic again
- [ ] `GET /api/sessions/sess_novice_001/narrative` returns 200 after first POST
- [ ] Missing `ANTHROPIC_API_KEY` returns 503 (not 500)
- [ ] `NarrativePanel` shows skeleton loading state, then text
- [ ] `npm run build` passes

---

## BATCH 2 — THREE AGENTS IN PARALLEL
**Prerequisite:** Batch 1 complete and verified.
**Duration:** Days 9–18.
**Agents:** Longitudinal Trajectory | Defect Library + Annotations | Narrative Frontend Integration

---

### Batch 2 Agent 1 — Longitudinal Skill Trajectory

**Files owned:** `backend/services/trajectory_service.py`, `backend/schemas/trajectory.py`, `my-app/src/types/trajectory.ts`, `my-app/src/components/welding/TrajectoryChart.tsx`
**Files modified:** `backend/routes/welders.py` (add route), `my-app/src/lib/api.ts` (add fetch), `my-app/src/app/seagull/welder/[id]/page.tsx` (add trajectory slot)
**Files read:** `backend/models/shared_enums.py`, `backend/schemas/shared.py`, `my-app/src/types/shared.ts`
**Files NOT touched:** Any migration, any narrative/prediction/annotation files

---

#### Step 1: Pydantic Schemas

**Create** `backend/schemas/trajectory.py`:
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .shared import MetricScore


class TrajectoryPoint(BaseModel):
    """Score data for a single session in a welder's history."""
    session_id: str
    session_date: datetime
    score_total: float
    metrics: List[MetricScore]   # one MetricScore per WeldMetric
    session_index: int           # 1-based chronological index


class WelderTrajectory(BaseModel):
    welder_id: str
    points: List[TrajectoryPoint]
    # Computed trend: slope of score_total over last 5 sessions
    trend_slope: Optional[float] = None  # positive = improving
    projected_next_score: Optional[float] = None


class TrajectoryProjection(BaseModel):
    """Linear extrapolation from last 5 sessions."""
    current_score: float
    projected_next: float
    sessions_to_target: Optional[int] = None  # to reach 80/100
    target_score: float = 80.0
```

---

#### Step 2: Trajectory Service

**Create** `backend/services/trajectory_service.py`:
```python
"""
Trajectory service — per-welder longitudinal score history.
Queries sessions by operator_id; returns chronological TrajectoryPoints.
"""
import logging
from typing import Optional
import statistics

from sqlalchemy.orm import Session as DBSession

from ..models.session import SessionModel
from ..models.shared_enums import WeldMetric
from ..schemas.trajectory import TrajectoryPoint, WelderTrajectory
from ..schemas.shared import make_metric_score
from ..services.scoring_service import get_session_score  # existing

logger = logging.getLogger(__name__)

TARGET_SCORE = 80.0


def get_welder_trajectory(welder_id: str, db: DBSession) -> WelderTrajectory:
    """
    Returns full chronological score history for a welder.
    welder_id maps to operator_id in sessions table.
    """
    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.operator_id == welder_id,
            SessionModel.status == "COMPLETE",
        )
        .order_by(SessionModel.start_time.asc())
        .all()
    )

    points = []
    for idx, session in enumerate(sessions, start=1):
        score = get_session_score(session.session_id, db)
        if score is None:
            continue

        metrics = _extract_metric_scores(score)
        points.append(TrajectoryPoint(
            session_id=session.session_id,
            session_date=session.start_time,
            score_total=float(score.total),
            metrics=metrics,
            session_index=idx,
        ))

    trend_slope, projected = _compute_projection(points)

    return WelderTrajectory(
        welder_id=welder_id,
        points=points,
        trend_slope=trend_slope,
        projected_next_score=projected,
    )


def _extract_metric_scores(score) -> list:
    """Maps existing ScoreRule names to canonical WeldMetric values."""
    # Mapping from rule names used in scoring_service to WeldMetric enum
    RULE_TO_METRIC = {
        "angle_consistency": WeldMetric.ANGLE_CONSISTENCY,
        "thermal_symmetry": WeldMetric.THERMAL_SYMMETRY,
        "amps_stability": WeldMetric.AMPS_STABILITY,
        "volts_stability": WeldMetric.VOLTS_STABILITY,
        "heat_diss_consistency": WeldMetric.HEAT_DISS_CONSISTENCY,
    }
    result = []
    for rule in score.rules:
        metric = RULE_TO_METRIC.get(rule.name)
        if metric:
            result.append(make_metric_score(metric, float(rule.score)))
    return result


def _compute_projection(points: list[TrajectoryPoint]):
    """Linear regression on last 5 score_total values."""
    recent = [p.score_total for p in points[-5:]]
    if len(recent) < 2:
        return None, None

    n = len(recent)
    x = list(range(n))
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(recent)

    numerator = sum((x[i] - x_mean) * (recent[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0, recent[-1]

    slope = numerator / denominator
    projected = recent[-1] + slope
    projected = max(0.0, min(100.0, projected))
    return round(slope, 4), round(projected, 2)
```

---

#### Step 3: Add Route to welders.py

**Modify** `backend/routes/welders.py` — append:
```python
# Add imports at top:
from ..services.trajectory_service import get_welder_trajectory
from ..schemas.trajectory import WelderTrajectory

# Add route:
@router.get("/{welder_id}/trajectory", response_model=WelderTrajectory)
def get_trajectory(welder_id: str, db: Session = Depends(get_db)):
    """Returns chronological score history for a welder."""
    return get_welder_trajectory(welder_id, db)
```

---

#### Step 4: Frontend Types

**Create** `my-app/src/types/trajectory.ts`:
```typescript
import { WelderID, SessionID, MetricScore } from "./shared";

export interface TrajectoryPoint {
  session_id: SessionID;
  session_date: string;     // ISO 8601
  score_total: number;      // 0–100
  metrics: MetricScore[];
  session_index: number;    // 1-based
}

export interface WelderTrajectory {
  welder_id: WelderID;
  points: TrajectoryPoint[];
  trend_slope: number | null;       // positive = improving
  projected_next_score: number | null;
}
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { WelderTrajectory } from "@/types/trajectory";

export async function fetchTrajectory(welderId: WelderID): Promise<WelderTrajectory> {
  const res = await fetch(`${API_BASE}/api/welders/${welderId}/trajectory`);
  if (!res.ok) throw new Error(`fetchTrajectory failed: ${res.status}`);
  return res.json();
}
```

---

#### Step 5: TrajectoryChart Component

**Create** `my-app/src/components/welding/TrajectoryChart.tsx`:
```typescript
/**
 * TrajectoryChart — multi-line Recharts chart for welder skill trajectory.
 *
 * Lines:
 *   - Total Score (white, thicker)
 *   - Angle Consistency (cyan)
 *   - Thermal Symmetry (amber)
 *   - Amps Stability (violet)
 *
 * Shows projected next score as a dashed extension.
 */
"use client";
import React from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from "recharts";
import { WelderTrajectory, TrajectoryPoint } from "@/types/trajectory";
import { WeldMetric, METRIC_LABELS } from "@/types/shared";

interface TrajectoryChartProps {
  trajectory: WelderTrajectory;
  height?: number;
}

const METRIC_COLORS: Partial<Record<WeldMetric, string>> = {
  angle_consistency: "#22d3ee",
  thermal_symmetry:  "#fbbf24",
  amps_stability:    "#a78bfa",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function buildChartData(points: TrajectoryPoint[], projectedNext: number | null) {
  const rows = points.map((p) => {
    const row: Record<string, number | string> = {
      date: formatDate(p.session_date),
      score_total: p.score_total,
    };
    for (const m of p.metrics) {
      row[m.metric] = m.value;
    }
    return row;
  });

  if (projectedNext !== null && rows.length > 0) {
    rows.push({
      date: "Projected",
      score_total: projectedNext,
      _projected: 1,
    });
  }

  return rows;
}

export function TrajectoryChart({ trajectory, height = 280 }: TrajectoryChartProps) {
  const { points, projected_next_score, trend_slope } = trajectory;

  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6 text-center text-sm text-neutral-500">
        No session history available yet.
      </div>
    );
  }

  const data = buildChartData(points, projected_next_score);
  const trendLabel =
    trend_slope === null ? null :
    trend_slope > 0.5 ? "↑ Improving" :
    trend_slope < -0.5 ? "↓ Declining" :
    "→ Stable";
  const trendColor =
    trend_slope === null ? "text-neutral-400" :
    trend_slope > 0.5 ? "text-green-400" :
    trend_slope < -0.5 ? "text-red-400" : "text-neutral-400";

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          Skill Trajectory
        </h2>
        {trendLabel && (
          <span className={`text-sm font-semibold ${trendColor}`}>{trendLabel}</span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis dataKey="date" tick={{ fill: "#737373", fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fill: "#737373", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#171717", border: "1px solid #404040" }}
            labelStyle={{ color: "#a3a3a3" }}
            itemStyle={{ color: "#e5e5e5" }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "#737373" }}
          />
          <ReferenceLine y={80} stroke="#404040" strokeDasharray="4 4" label={{ value: "Target 80", fill: "#525252", fontSize: 10 }} />

          {/* Total score — primary line */}
          <Line
            type="monotone" dataKey="score_total" name="Total Score"
            stroke="#ffffff" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }}
          />

          {/* Per-metric lines */}
          {Object.entries(METRIC_COLORS).map(([metric, color]) => (
            <Line
              key={metric}
              type="monotone" dataKey={metric} name={METRIC_LABELS[metric as WeldMetric]}
              stroke={color} strokeWidth={1.5} dot={false} strokeOpacity={0.7}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {projected_next_score !== null && (
        <p className="text-xs text-neutral-500 mt-2 text-right">
          Projected next session: <span className="text-neutral-300">{Math.round(projected_next_score)}/100</span>
        </p>
      )}
    </div>
  );
}

export default TrajectoryChart;
```

---

#### Step 6: Wire into Welder Report

**Modify** `my-app/src/app/seagull/welder/[id]/page.tsx`:

Add to existing Promise.all fetch block:
```typescript
import { fetchTrajectory } from "@/lib/api";
import { WelderTrajectory } from "@/types/trajectory";
import { TrajectoryChart } from "@/components/welding/TrajectoryChart";

// Add trajectory to Promise.all:
const [session, expertSession, score, trajectory] = await Promise.all([
  fetchSession(sessionId),
  fetchSession(EXPERT_SESSION_ID),
  fetchScore(sessionId),
  fetchTrajectory(welderId).catch(() => null),  // non-blocking
]);

// In ReportLayout:
trajectory={trajectory ? <TrajectoryChart trajectory={trajectory} /> : undefined}
```

---

#### Batch 2 Agent 1 Verification Checklist
- [ ] `GET /api/welders/mike-chen/trajectory` returns array of TrajectoryPoints
- [ ] `trend_slope` is non-null when ≥ 2 sessions exist
- [ ] Empty history (new welder) returns `{ points: [], trend_slope: null }`
- [ ] `TrajectoryChart` renders without error with 1, 5, and 10 points
- [ ] Welder report page renders `TrajectoryChart` in trajectory slot
- [ ] Hardcoded `[68, 72, 75]` MOCK_HISTORICAL removed from page.tsx

---

### Batch 2 Agent 2 — Defect Pattern Library + Replay Annotation

**Files owned:** `007_session_annotations.py`, `backend/models/annotation.py`, `backend/schemas/annotation.py`, `backend/routes/annotations.py`, `my-app/src/types/annotation.ts`, `my-app/src/components/welding/AnnotationMarker.tsx`, `my-app/src/components/welding/AddAnnotationPanel.tsx`, `my-app/src/app/(app)/defects/page.tsx`
**Files modified:** `backend/main.py` (router register), `my-app/src/lib/api.ts` (fetch functions), replay page (annotation markers)
**Files NOT touched:** Any trajectory, narrative, or prediction files. `TimelineMarkers.tsx` — read only, do not modify

---

#### Step 1: Fill Migration 007

**Modify** `backend/alembic/versions/007_session_annotations.py`:
```python
def upgrade() -> None:
    op.create_table(
        "session_annotations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(64),
                  sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp_ms", sa.Integer, nullable=False),
        sa.Column("annotation_type", sa.String(32), nullable=False),
        # Values: defect_confirmed | near_miss | technique_error | equipment_issue
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_session_annotations_session_id", "session_annotations", ["session_id"])
    op.create_index("ix_session_annotations_type", "session_annotations", ["annotation_type"])

def downgrade() -> None:
    op.drop_index("ix_session_annotations_type", "session_annotations")
    op.drop_index("ix_session_annotations_session_id", "session_annotations")
    op.drop_table("session_annotations")
```

---

#### Step 2: SQLAlchemy Model

**Create** `backend/models/annotation.py`:
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from ..database import Base
from ..models.shared_enums import AnnotationType


class SessionAnnotation(Base):
    __tablename__ = "session_annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    timestamp_ms = Column(Integer, nullable=False)
    annotation_type = Column(String(32), nullable=False)
    note = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

---

#### Step 3: Pydantic Schemas

**Create** `backend/schemas/annotation.py`:
```python
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
from ..models.shared_enums import AnnotationType


class AnnotationCreate(BaseModel):
    timestamp_ms: int
    annotation_type: AnnotationType
    note: Optional[str] = None
    created_by: Optional[str] = None

    @field_validator("timestamp_ms")
    @classmethod
    def must_be_positive(cls, v):
        if v < 0:
            raise ValueError("timestamp_ms must be non-negative")
        return v


class AnnotationResponse(BaseModel):
    id: int
    session_id: str
    timestamp_ms: int
    annotation_type: AnnotationType
    note: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DefectLibraryItem(BaseModel):
    """Cross-session defect entry for the defect library page."""
    id: int
    session_id: str
    timestamp_ms: int
    annotation_type: AnnotationType
    note: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    weld_type: Optional[str]   # from session
    operator_id: Optional[str]  # from session (anonymisable)

    class Config:
        from_attributes = True
```

---

#### Step 4: Annotations Route

**Create** `backend/routes/annotations.py`:
```python
"""
Annotation endpoints.
Session-scoped: POST/GET /api/sessions/{id}/annotations
Cross-session defect library: GET /api/defects
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from ..models.annotation import SessionAnnotation
from ..models.session import SessionModel
from ..models.shared_enums import AnnotationType
from ..schemas.annotation import AnnotationCreate, AnnotationResponse, DefectLibraryItem

router = APIRouter(tags=["annotations"])


@router.post(
    "/api/sessions/{session_id}/annotations",
    response_model=AnnotationResponse,
    status_code=201,
)
def create_annotation(
    session_id: str,
    body: AnnotationCreate,
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    ann = SessionAnnotation(
        session_id=session_id,
        timestamp_ms=body.timestamp_ms,
        annotation_type=body.annotation_type.value,
        note=body.note,
        created_by=body.created_by,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


@router.get(
    "/api/sessions/{session_id}/annotations",
    response_model=List[AnnotationResponse],
)
def get_session_annotations(session_id: str, db: Session = Depends(get_db)):
    return (
        db.query(SessionAnnotation)
        .filter_by(session_id=session_id)
        .order_by(SessionAnnotation.timestamp_ms.asc())
        .all()
    )


@router.get("/api/defects", response_model=List[DefectLibraryItem])
def get_defect_library(
    annotation_type: Optional[AnnotationType] = Query(None),
    weld_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """
    Cross-session defect library.
    Returns confirmed/near-miss annotations with session metadata.
    """
    q = (
        db.query(SessionAnnotation, SessionModel)
        .join(SessionModel, SessionModel.session_id == SessionAnnotation.session_id)
    )
    if annotation_type:
        q = q.filter(SessionAnnotation.annotation_type == annotation_type.value)
    if weld_type:
        q = q.filter(SessionModel.weld_type == weld_type)

    rows = q.order_by(SessionAnnotation.created_at.desc()).limit(limit).all()

    result = []
    for ann, sess in rows:
        result.append(DefectLibraryItem(
            id=ann.id,
            session_id=ann.session_id,
            timestamp_ms=ann.timestamp_ms,
            annotation_type=ann.annotation_type,
            note=ann.note,
            created_by=ann.created_by,
            created_at=ann.created_at,
            weld_type=sess.weld_type,
            operator_id=sess.operator_id,
        ))
    return result
```

**Modify** `backend/main.py`:
```python
from .routes import annotations
app.include_router(annotations.router)
```

---

#### Step 5: Frontend Types

**Create** `my-app/src/types/annotation.ts`:
```typescript
import { SessionID, AnnotationType } from "./shared";

export interface Annotation {
  id: number;
  session_id: SessionID;
  timestamp_ms: number;
  annotation_type: AnnotationType;
  note: string | null;
  created_by: string | null;
  created_at: string;  // ISO 8601
}

export interface AnnotationCreate {
  timestamp_ms: number;
  annotation_type: AnnotationType;
  note?: string;
  created_by?: string;
}

export interface DefectLibraryItem extends Annotation {
  weld_type: string | null;
  operator_id: string | null;
}

export const ANNOTATION_TYPE_LABELS: Record<AnnotationType, string> = {
  defect_confirmed: "Confirmed Defect",
  near_miss:        "Near Miss",
  technique_error:  "Technique Error",
  equipment_issue:  "Equipment Issue",
};

export const ANNOTATION_TYPE_COLORS: Record<AnnotationType, string> = {
  defect_confirmed: "text-red-400 border-red-500",
  near_miss:        "text-amber-400 border-amber-500",
  technique_error:  "text-orange-400 border-orange-500",
  equipment_issue:  "text-violet-400 border-violet-500",
};
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { Annotation, AnnotationCreate, DefectLibraryItem } from "@/types/annotation";
import { AnnotationType } from "@/types/shared";

export async function fetchAnnotations(sessionId: SessionID): Promise<Annotation[]> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/annotations`);
  if (!res.ok) throw new Error(`fetchAnnotations failed: ${res.status}`);
  return res.json();
}

export async function createAnnotation(
  sessionId: SessionID,
  body: AnnotationCreate
): Promise<Annotation> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`createAnnotation failed: ${res.status}`);
  return res.json();
}

export async function fetchDefectLibrary(params?: {
  annotation_type?: AnnotationType;
  weld_type?: string;
}): Promise<DefectLibraryItem[]> {
  const qs = new URLSearchParams();
  if (params?.annotation_type) qs.set("annotation_type", params.annotation_type);
  if (params?.weld_type) qs.set("weld_type", params.weld_type);
  const res = await fetch(`${API_BASE}/api/defects?${qs}`);
  if (!res.ok) throw new Error(`fetchDefectLibrary failed: ${res.status}`);
  return res.json();
}
```

---

#### Step 6: AnnotationMarker Component

**Create** `my-app/src/components/welding/AnnotationMarker.tsx`:
```typescript
/**
 * AnnotationMarker — renders annotation pins on replay timeline.
 * Follows same pattern as TimelineMarkers.tsx (read that file first).
 * Does NOT modify TimelineMarkers.tsx.
 */
"use client";
import React from "react";
import { Annotation, ANNOTATION_TYPE_COLORS, ANNOTATION_TYPE_LABELS } from "@/types/annotation";

interface AnnotationMarkerProps {
  annotations: Annotation[];
  firstTimestamp: number;
  lastTimestamp: number;
  onAnnotationClick: (timestamp_ms: number) => void;
}

export function AnnotationMarker({
  annotations,
  firstTimestamp,
  lastTimestamp,
  onAnnotationClick,
}: AnnotationMarkerProps) {
  const range = lastTimestamp - firstTimestamp;
  if (range <= 0 || annotations.length === 0) return null;

  return (
    <div className="relative h-4 w-full" aria-label="Annotation markers">
      {annotations.map((ann) => {
        const pct = ((ann.timestamp_ms - firstTimestamp) / range) * 100;
        const colorClass = ANNOTATION_TYPE_COLORS[ann.annotation_type];
        return (
          <button
            key={ann.id}
            title={`${ANNOTATION_TYPE_LABELS[ann.annotation_type]}${ann.note ? `: ${ann.note}` : ""}`}
            onClick={() => onAnnotationClick(ann.timestamp_ms)}
            style={{ left: `${pct}%` }}
            className={`absolute -translate-x-1/2 w-2 h-4 border-l-2 cursor-pointer opacity-80 hover:opacity-100 ${colorClass}`}
            aria-label={ANNOTATION_TYPE_LABELS[ann.annotation_type]}
          />
        );
      })}
    </div>
  );
}

export default AnnotationMarker;
```

---

#### Step 7: AddAnnotationPanel Component

**Create** `my-app/src/components/welding/AddAnnotationPanel.tsx`:
```typescript
/**
 * AddAnnotationPanel — click-to-annotate modal for replay page.
 * Shown when user enables "Annotate Mode" toggle.
 */
"use client";
import React, { useState } from "react";
import { AnnotationCreate, ANNOTATION_TYPE_LABELS } from "@/types/annotation";
import { AnnotationType } from "@/types/shared";
import { createAnnotation } from "@/lib/api";
import { logError } from "@/lib/logger";
import { SessionID } from "@/types/shared";

interface AddAnnotationPanelProps {
  sessionId: SessionID;
  selectedTimestampMs: number | null;
  onAnnotationSaved: () => void;  // caller refreshes annotation list
  onClose: () => void;
}

const ANNOTATION_TYPES: AnnotationType[] = [
  "defect_confirmed",
  "near_miss",
  "technique_error",
  "equipment_issue",
];

export function AddAnnotationPanel({
  sessionId,
  selectedTimestampMs,
  onAnnotationSaved,
  onClose,
}: AddAnnotationPanelProps) {
  const [type, setType] = useState<AnnotationType>("defect_confirmed");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (selectedTimestampMs === null) return;
    setSaving(true);
    setError(null);
    try {
      const body: AnnotationCreate = {
        timestamp_ms: selectedTimestampMs,
        annotation_type: type,
        note: note.trim() || undefined,
      };
      await createAnnotation(sessionId, body);
      onAnnotationSaved();
      onClose();
    } catch (err) {
      logError("AddAnnotationPanel", err);
      setError("Failed to save annotation. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-700 bg-neutral-900 p-4 w-72">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Add Annotation</h3>
        <button onClick={onClose} className="text-neutral-500 hover:text-white text-lg leading-none">×</button>
      </div>

      {selectedTimestampMs !== null && (
        <p className="text-xs text-neutral-500 mb-3">
          At <span className="text-neutral-300">{(selectedTimestampMs / 1000).toFixed(2)}s</span>
        </p>
      )}

      <label className="block text-xs text-neutral-400 mb-1">Type</label>
      <select
        value={type}
        onChange={(e) => setType(e.target.value as AnnotationType)}
        className="w-full bg-neutral-800 border border-neutral-700 rounded px-2 py-1.5 text-sm text-white mb-3"
      >
        {ANNOTATION_TYPES.map((t) => (
          <option key={t} value={t}>{ANNOTATION_TYPE_LABELS[t]}</option>
        ))}
      </select>

      <label className="block text-xs text-neutral-400 mb-1">Note (optional)</label>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
        placeholder="What did you observe?"
        className="w-full bg-neutral-800 border border-neutral-700 rounded px-2 py-1.5 text-sm text-white resize-none mb-3"
      />

      {error && <p className="text-xs text-red-400 mb-2">{error}</p>}

      <button
        onClick={handleSave}
        disabled={saving || selectedTimestampMs === null}
        className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:bg-neutral-700 disabled:text-neutral-500 text-black font-semibold py-1.5 rounded text-sm"
      >
        {saving ? "Saving…" : "Save Annotation"}
      </button>
    </div>
  );
}

export default AddAnnotationPanel;
```

---

#### Step 8: Defect Library Page

**Create** `my-app/src/app/(app)/defects/page.tsx`:
```typescript
/**
 * Defect Library — cross-session searchable defect database.
 * Route: /defects
 * Orthogonal to WWAD supervisor page — no imports from supervisor/.
 */
"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DefectLibraryItem, ANNOTATION_TYPE_LABELS, ANNOTATION_TYPE_COLORS } from "@/types/annotation";
import { AnnotationType } from "@/types/shared";
import { fetchDefectLibrary } from "@/lib/api";
import { logError } from "@/lib/logger";

const ALL_TYPES: Array<{ value: AnnotationType | ""; label: string }> = [
  { value: "", label: "All Types" },
  { value: "defect_confirmed", label: "Confirmed Defects" },
  { value: "near_miss",        label: "Near Misses" },
  { value: "technique_error",  label: "Technique Errors" },
  { value: "equipment_issue",  label: "Equipment Issues" },
];

export default function DefectLibraryPage() {
  const [items, setItems] = useState<DefectLibraryItem[]>([]);
  const [filterType, setFilterType] = useState<AnnotationType | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchDefectLibrary({ annotation_type: filterType || undefined })
      .then((data) => { if (mounted) { setItems(data); setLoading(false); } })
      .catch((err) => {
        logError("DefectLibraryPage", err);
        if (mounted) { setError("Failed to load defect library."); setLoading(false); }
      });
    return () => { mounted = false; };
  }, [filterType]);

  return (
    <div className="min-h-screen bg-neutral-950 text-white px-8 py-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold">Defect Pattern Library</h1>
          <div className="flex gap-2">
            {ALL_TYPES.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setFilterType(value as AnnotationType | "")}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  filterType === value
                    ? "bg-cyan-500 text-black"
                    : "bg-neutral-800 text-neutral-400 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="space-y-2">
            {[1,2,3].map(i => <div key={i} className="h-16 bg-neutral-900 rounded animate-pulse" />)}
          </div>
        )}

        {error && <p className="text-red-400 text-sm">{error}</p>}

        {!loading && !error && items.length === 0 && (
          <p className="text-neutral-500 text-sm text-center mt-12">
            No annotations yet. Add annotations in the Replay view.
          </p>
        )}

        {!loading && !error && (
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3"
              >
                <div className="flex items-center gap-4">
                  <span className={`text-xs font-semibold border rounded px-2 py-0.5 ${ANNOTATION_TYPE_COLORS[item.annotation_type]}`}>
                    {ANNOTATION_TYPE_LABELS[item.annotation_type]}
                  </span>
                  <div>
                    <p className="text-sm text-white">{item.note || "No note"}</p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {item.weld_type?.toUpperCase() ?? "Unknown"} · {item.operator_id ?? "Unknown"} · {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <Link
                  href={`/replay/${item.session_id}?t=${item.timestamp_ms}`}
                  className="text-xs text-cyan-400 hover:text-cyan-300 whitespace-nowrap ml-4"
                >
                  View in Replay →
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

---

#### Batch 2 Agent 2 Verification Checklist
- [ ] `POST /api/sessions/sess_novice_001/annotations` creates annotation, returns 201
- [ ] `GET /api/sessions/sess_novice_001/annotations` returns array
- [ ] `GET /api/defects` returns cross-session items with weld_type
- [ ] `GET /api/defects?annotation_type=defect_confirmed` filters correctly
- [ ] `AnnotationMarker` renders pins at correct positions for 3 test annotations
- [ ] `AddAnnotationPanel` saves and calls `onAnnotationSaved`
- [ ] Defect library page loads, filters, and deep-links to replay

---

### Batch 2 Agent 3 — Narrative Frontend Integration

**Files owned:** nothing new
**Files modified:** `my-app/src/app/seagull/welder/[id]/page.tsx` (wire NarrativePanel), `my-app/src/components/pdf/WelderReportPDF.tsx` (narrative section), `my-app/src/app/api/welder-report-pdf/route.ts` (extend body schema)
**Files read:** `my-app/src/components/welding/NarrativePanel.tsx` (Batch 1 Agent 3), `my-app/src/types/narrative.ts`, `my-app/src/lib/api.ts`
**Files NOT touched:** Any Batch 2 Agent 1 or Agent 2 files

---

#### Step 1: Wire NarrativePanel into Welder Report

**Modify** `my-app/src/app/seagull/welder/[id]/page.tsx`:

Add import:
```typescript
import { NarrativePanel } from "@/components/welding/NarrativePanel";
```

Update ReportLayout call — narrative slot was previously empty:
```tsx
narrative={<NarrativePanel sessionId={sessionId} />}
```

This is the complete change to the report page for this agent. NarrativePanel fetches its own data internally — no new Promise.all entries needed.

---

#### Step 2: Extend PDF Body Schema

**Modify** `my-app/src/app/api/welder-report-pdf/route.ts`:

Add optional narrative to the validation schema (extend the existing Zod schema):
```typescript
// In the existing Zod body schema, add:
narrative: z.string().max(2000).optional().nullable(),
```

Pass through to renderer:
```typescript
// In the renderToBuffer call:
narrative: body.narrative ?? null,
```

---

#### Step 3: Extend WelderReportPDF Component

**Modify** `my-app/src/components/pdf/WelderReportPDF.tsx`:

Add narrative prop:
```typescript
interface WelderReportPDFProps {
  // ... existing props ...
  narrative?: string | null;
}
```

Add narrative section after score circle — before feedback items:
```tsx
{narrative && (
  <View style={{ marginTop: 16, padding: 12, backgroundColor: "#1a1a2e", borderRadius: 6 }}>
    <Text style={{ fontSize: 8, color: "#737373", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>
      AI Coach Report
    </Text>
    <Text style={{ fontSize: 9, color: "#d4d4d4", lineHeight: 1.6 }}>
      {sanitizeText(narrative)}
    </Text>
  </View>
)}
```

---

#### Step 4: Wire narrative into PDF download handler

**Modify** `my-app/src/app/seagull/welder/[id]/page.tsx`:

In `handleDownloadPDF`, fetch narrative before building the PDF body:
```typescript
const handleDownloadPDF = async () => {
  let narrativeText: string | null = null;
  try {
    const n = await fetchNarrative(sessionId);
    narrativeText = n.narrative_text;
  } catch {
    // non-blocking — PDF still generates without narrative
  }

  // existing POST to /api/welder-report-pdf:
  const body = {
    // ... existing fields ...
    narrative: narrativeText,
  };
  // rest of existing handler unchanged
};
```

---

#### Batch 2 Agent 3 Verification Checklist
- [ ] Welder report page renders NarrativePanel in narrative slot
- [ ] NarrativePanel shows skeleton, then text, then regenerate button
- [ ] PDF with narrative: narrative section appears between score circle and feedback
- [ ] PDF without narrative (fetchNarrative 404): generates cleanly without section
- [ ] `npm run build` passes

---

## BATCH 3 — THREE AGENTS IN PARALLEL
**Prerequisite:** Batch 2 complete and verified.
**Duration:** Days 19–30.
**Agents:** Comparative Benchmarking | Coaching Protocol | Credentialing

---

### Batch 3 Agent 1 — Comparative Benchmarking Engine

**Files owned:** `backend/services/benchmark_service.py`, `backend/schemas/benchmark.py`, `my-app/src/types/benchmark.ts`, `my-app/src/components/welding/BenchmarkPanel.tsx`
**Files modified:** `backend/routes/welders.py` (add route), `my-app/src/lib/api.ts`, `my-app/src/app/seagull/welder/[id]/page.tsx` (benchmarks slot), `my-app/src/app/(app)/supervisor/page.tsx` (Rankings tab)
**Files NOT touched:** Coaching files, Certification files, any migration

---

#### Step 1: Benchmark Schemas

**Create** `backend/schemas/benchmark.py`:
```python
from pydantic import BaseModel
from typing import List
from .shared import MetricScore, WeldMetric


class MetricBenchmark(BaseModel):
    metric: WeldMetric
    label: str
    welder_value: float          # 0–100
    population_mean: float
    population_min: float
    population_max: float
    population_std: float
    percentile: float            # 0–100 (welder vs population)
    tier: str                    # "top" | "mid" | "bottom"


class WelderBenchmarks(BaseModel):
    welder_id: str
    population_size: int         # number of welders in comparison
    metrics: List[MetricBenchmark]
    overall_percentile: float    # based on score_total
```

---

#### Step 2: Benchmark Service

**Create** `backend/services/benchmark_service.py`:
```python
"""
Benchmark service — computes per-metric percentile rankings.

Population: all welders' MOST RECENT complete session with a score.
Result is per-metric distribution + welder's position within it.

Note: coaching_service.py calls this service by importing get_welder_benchmarks().
Do NOT call coaching_service from here (circular).
"""
import logging
import statistics
from typing import Optional

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from ..models.session import SessionModel
from ..models.shared_enums import WeldMetric
from ..schemas.benchmark import MetricBenchmark, WelderBenchmarks
from ..schemas.shared import METRIC_LABELS
from ..services.scoring_service import get_session_score  # existing
from ..services.trajectory_service import _extract_metric_scores  # reuse extractor

logger = logging.getLogger(__name__)

TOP_PERCENTILE = 75.0
BOTTOM_PERCENTILE = 25.0


def get_welder_benchmarks(welder_id: str, db: DBSession) -> WelderBenchmarks:
    """
    Returns per-metric benchmark for welder_id against all other welders.
    Uses each welder's most recent COMPLETE session.
    """
    # Get all distinct operator_ids with complete sessions
    operator_ids = [
        row.operator_id for row in
        db.query(SessionModel.operator_id)
        .filter(SessionModel.status == "COMPLETE", SessionModel.operator_id.isnot(None))
        .distinct()
        .all()
    ]

    # For each operator, get their most recent session's score
    population: dict[str, dict[WeldMetric, float]] = {}
    for op_id in operator_ids:
        latest = (
            db.query(SessionModel)
            .filter(SessionModel.operator_id == op_id, SessionModel.status == "COMPLETE")
            .order_by(SessionModel.start_time.desc())
            .first()
        )
        if not latest:
            continue
        score = get_session_score(latest.session_id, db)
        if not score:
            continue
        metric_scores = _extract_metric_scores(score)
        population[op_id] = {ms.metric: ms.value for ms in metric_scores}

    if welder_id not in population:
        logger.warning("Welder %s not in benchmark population", welder_id)
        # Return empty benchmarks rather than raising
        return WelderBenchmarks(
            welder_id=welder_id, population_size=0, metrics=[], overall_percentile=0.0
        )

    welder_metrics = population[welder_id]
    metrics_result = []

    for metric in WeldMetric:
        values = [v[metric] for v in population.values() if metric in v]
        if len(values) < 2:
            continue

        welder_val = welder_metrics.get(metric, 0.0)
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        pop_min = min(values)
        pop_max = max(values)
        percentile = _compute_percentile(welder_val, values)

        if percentile >= TOP_PERCENTILE:
            tier = "top"
        elif percentile <= BOTTOM_PERCENTILE:
            tier = "bottom"
        else:
            tier = "mid"

        metrics_result.append(MetricBenchmark(
            metric=metric,
            label=METRIC_LABELS[metric],
            welder_value=round(welder_val, 2),
            population_mean=round(mean, 2),
            population_min=round(pop_min, 2),
            population_max=round(pop_max, 2),
            population_std=round(std, 2),
            percentile=round(percentile, 1),
            tier=tier,
        ))

    # Overall percentile from score_total
    welder_session = (
        db.query(SessionModel)
        .filter(SessionModel.operator_id == welder_id, SessionModel.status == "COMPLETE")
        .order_by(SessionModel.start_time.desc())
        .first()
    )
    all_scores = [
        s.score_total for s in
        db.query(SessionModel.score_total)
        .filter(SessionModel.status == "COMPLETE", SessionModel.score_total.isnot(None))
        .all()
        if s.score_total is not None
    ]
    overall_pct = 0.0
    if welder_session and welder_session.score_total and all_scores:
        overall_pct = _compute_percentile(welder_session.score_total, all_scores)

    return WelderBenchmarks(
        welder_id=welder_id,
        population_size=len(population),
        metrics=metrics_result,
        overall_percentile=round(overall_pct, 1),
    )


def _compute_percentile(value: float, population: list[float]) -> float:
    """Percentage of population values strictly below `value`."""
    below = sum(1 for v in population if v < value)
    return (below / len(population)) * 100
```

---

#### Step 3: Add Route to welders.py

**Modify** `backend/routes/welders.py` — append:
```python
from ..services.benchmark_service import get_welder_benchmarks
from ..schemas.benchmark import WelderBenchmarks

@router.get("/{welder_id}/benchmarks", response_model=WelderBenchmarks)
def get_benchmarks(welder_id: str, db: Session = Depends(get_db)):
    """Returns per-metric benchmark for welder vs all other welders."""
    return get_welder_benchmarks(welder_id, db)
```

---

#### Step 4: Frontend Types

**Create** `my-app/src/types/benchmark.ts`:
```typescript
import { WelderID, WeldMetric } from "./shared";

export interface MetricBenchmark {
  metric: WeldMetric;
  label: string;
  welder_value: number;
  population_mean: number;
  population_min: number;
  population_max: number;
  population_std: number;
  percentile: number;   // 0–100
  tier: "top" | "mid" | "bottom";
}

export interface WelderBenchmarks {
  welder_id: WelderID;
  population_size: number;
  metrics: MetricBenchmark[];
  overall_percentile: number;
}
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { WelderBenchmarks } from "@/types/benchmark";

export async function fetchBenchmarks(welderId: WelderID): Promise<WelderBenchmarks> {
  const res = await fetch(`${API_BASE}/api/welders/${welderId}/benchmarks`);
  if (!res.ok) throw new Error(`fetchBenchmarks failed: ${res.status}`);
  return res.json();
}
```

---

#### Step 5: BenchmarkPanel Component

**Create** `my-app/src/components/welding/BenchmarkPanel.tsx`:
```typescript
/**
 * BenchmarkPanel — horizontal distribution gauges per metric.
 * Shows welder's position on a min→mean→max range.
 * Tier colours: top=green, mid=yellow, bottom=red.
 */
"use client";
import React from "react";
import { WelderBenchmarks, MetricBenchmark } from "@/types/benchmark";

interface BenchmarkPanelProps {
  benchmarks: WelderBenchmarks;
}

const TIER_COLORS = {
  top:    { bar: "bg-green-500",  text: "text-green-400", badge: "bg-green-500/10 text-green-400 border-green-500/30" },
  mid:    { bar: "bg-amber-500",  text: "text-amber-400", badge: "bg-amber-500/10 text-amber-400 border-amber-500/30" },
  bottom: { bar: "bg-red-500",    text: "text-red-400",   badge: "bg-red-500/10 text-red-400 border-red-500/30" },
};

function GaugeRow({ m }: { m: MetricBenchmark }) {
  const colors = TIER_COLORS[m.tier];
  const range = m.population_max - m.population_min;
  const pct = range > 0 ? ((m.welder_value - m.population_min) / range) * 100 : 50;
  const meanPct = range > 0 ? ((m.population_mean - m.population_min) / range) * 100 : 50;

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-neutral-400">{m.label}</span>
        <div className="flex items-center gap-2">
          <span className={`text-lg font-bold tabular-nums ${colors.text}`}>
            {Math.round(m.welder_value)}
          </span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${colors.badge}`}>
            {Math.round(m.percentile)}th%
          </span>
        </div>
      </div>
      {/* Track */}
      <div className="relative h-2 bg-neutral-800 rounded-full">
        {/* Mean marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-0.5 h-4 bg-neutral-600"
          style={{ left: `${meanPct}%` }}
          title={`Population mean: ${Math.round(m.population_mean)}`}
        />
        {/* Welder dot */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-neutral-950 ${colors.bar}`}
          style={{ left: `${pct}%`, transform: "translate(-50%, -50%)" }}
        />
      </div>
      <div className="flex justify-between text-xs text-neutral-600 mt-1">
        <span>{Math.round(m.population_min)}</span>
        <span className="text-neutral-500">avg {Math.round(m.population_mean)}</span>
        <span>{Math.round(m.population_max)}</span>
      </div>
    </div>
  );
}

export function BenchmarkPanel({ benchmarks }: BenchmarkPanelProps) {
  if (benchmarks.population_size < 2) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6 text-sm text-neutral-500 text-center">
        Benchmarking requires at least 2 welders in the system.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          Benchmark Comparison
        </h2>
        <span className="text-xs text-neutral-600">
          vs {benchmarks.population_size} welders · {Math.round(benchmarks.overall_percentile)}th percentile overall
        </span>
      </div>
      {benchmarks.metrics.map((m) => (
        <GaugeRow key={m.metric} m={m} />
      ))}
    </div>
  );
}

export default BenchmarkPanel;
```

---

#### Step 6: Wire into Welder Report + Supervisor Rankings Tab

**Modify** `my-app/src/app/seagull/welder/[id]/page.tsx`:
```typescript
import { fetchBenchmarks } from "@/lib/api";
import { WelderBenchmarks } from "@/types/benchmark";
import { BenchmarkPanel } from "@/components/welding/BenchmarkPanel";

// Add to Promise.all (non-blocking):
const [session, expertSession, score, trajectory, benchmarks] = await Promise.all([
  fetchSession(sessionId),
  fetchSession(EXPERT_SESSION_ID),
  fetchScore(sessionId),
  fetchTrajectory(welderId).catch(() => null),
  fetchBenchmarks(welderId).catch(() => null),
]);

// In ReportLayout:
benchmarks={benchmarks ? <BenchmarkPanel benchmarks={benchmarks} /> : undefined}
```

**Modify** `my-app/src/app/(app)/supervisor/page.tsx` — add Rankings tab. The supervisor page already has a tab structure from WWAD. Add a new tab:

```typescript
// Extend existing tab list:
{ id: "rankings", label: "Rankings" }

// New tab panel:
{activeTab === "rankings" && <RankingsTable />}
```

**Create** `my-app/src/components/dashboard/RankingsTable.tsx`:
```typescript
/**
 * RankingsTable — supervisor view of all welders ranked by metric.
 * WWAD orthogonality: imports from benchmark types only, not from
 * TorchViz3D, HeatMap, FeedbackPanel, or TorchAngleGraph.
 */
"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { WelderBenchmarks } from "@/types/benchmark";
import { WeldMetric, METRIC_LABELS, WELD_METRICS } from "@/types/shared";
import { fetchBenchmarks } from "@/lib/api";

// Hardcoded to WELDER_ARCHETYPES IDs — same pattern as existing supervisor page
const WELDER_IDS = [
  "mike-chen", "expert-benchmark",
  // Add all 10 archetype IDs here matching mock_welders.py
];

export function RankingsTable() {
  const [data, setData] = useState<WelderBenchmarks[]>([]);
  const [sortBy, setSortBy] = useState<WeldMetric | "overall">("overall");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled(WELDER_IDS.map(id => fetchBenchmarks(id)))
      .then(results => {
        const successful = results
          .filter((r): r is PromiseFulfilledResult<WelderBenchmarks> => r.status === "fulfilled")
          .map(r => r.value);
        setData(successful);
        setLoading(false);
      });
  }, []);

  const sorted = [...data].sort((a, b) => {
    if (sortBy === "overall") return b.overall_percentile - a.overall_percentile;
    const aMetric = a.metrics.find(m => m.metric === sortBy)?.percentile ?? 0;
    const bMetric = b.metrics.find(m => m.metric === sortBy)?.percentile ?? 0;
    return bMetric - aMetric;
  });

  if (loading) return <div className="h-32 bg-neutral-900 rounded animate-pulse" />;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-800">
              <th className="px-4 py-3 text-left text-xs text-neutral-500 font-medium">Rank</th>
              <th className="px-4 py-3 text-left text-xs text-neutral-500 font-medium">Welder</th>
              <th
                className={`px-4 py-3 text-right text-xs font-medium cursor-pointer hover:text-white ${sortBy === "overall" ? "text-cyan-400" : "text-neutral-500"}`}
                onClick={() => setSortBy("overall")}
              >
                Overall %ile
              </th>
              {WELD_METRICS.map(metric => (
                <th
                  key={metric}
                  className={`px-4 py-3 text-right text-xs font-medium cursor-pointer hover:text-white ${sortBy === metric ? "text-cyan-400" : "text-neutral-500"}`}
                  onClick={() => setSortBy(metric)}
                >
                  {METRIC_LABELS[metric].split(" ")[0]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((w, i) => (
              <tr key={w.welder_id} className="border-b border-neutral-800/50 hover:bg-neutral-800/30">
                <td className="px-4 py-3 text-neutral-500 tabular-nums">{i + 1}</td>
                <td className="px-4 py-3">
                  <Link href={`/seagull/welder/${w.welder_id}`} className="text-cyan-400 hover:text-cyan-300">
                    {w.welder_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-right font-semibold tabular-nums">
                  {Math.round(w.overall_percentile)}th
                </td>
                {WELD_METRICS.map(metric => {
                  const m = w.metrics.find(x => x.metric === metric);
                  return (
                    <td key={metric} className={`px-4 py-3 text-right tabular-nums ${
                      m?.tier === "top" ? "text-green-400" :
                      m?.tier === "bottom" ? "text-red-400" : "text-neutral-300"
                    }`}>
                      {m ? `${Math.round(m.percentile)}th` : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

#### Batch 3 Agent 1 Verification Checklist
- [ ] `GET /api/welders/mike-chen/benchmarks` returns all 5 metrics with percentile values
- [ ] Population of 1 returns `population_size: 1`, empty metrics
- [ ] `BenchmarkPanel` renders gauges with correct dot positions
- [ ] Welder report shows benchmark panel in benchmarks slot
- [ ] Rankings table sorts correctly by each metric column
- [ ] WWAD orthogonality: no imports from TorchViz3D/HeatMap/FeedbackPanel in RankingsTable

---

### Batch 3 Agent 2 — Automated Coaching Protocol Engine

**Files owned:** `008_coaching_drills.py`, `backend/models/coaching.py`, `backend/schemas/coaching.py`, `backend/services/coaching_service.py`, `my-app/src/types/coaching.ts`, `my-app/src/components/welding/CoachingPlanPanel.tsx`
**Files modified:** `backend/routes/welders.py` (2 routes), `my-app/src/lib/api.ts`, welder report page (coaching slot)
**Files read:** `backend/schemas/benchmark.py`, `backend/services/benchmark_service.py` (import get_welder_benchmarks), `my-app/src/types/shared.ts`
**CRITICAL RULE:** coaching_service imports benchmark_service but NEVER the reverse. benchmark_service must remain import-free of coaching.

---

#### Step 1: Fill Migration 008

**Modify** `backend/alembic/versions/008_coaching_drills.py`:
```python
def upgrade() -> None:
    # ── drills ────────────────────────────────────────────────────────────
    op.create_table(
        "drills",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("target_metric", sa.String(64), nullable=False),
        # Values: WeldMetric enum strings
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("sessions_required", sa.Integer, nullable=False, server_default="3"),
        sa.Column("success_threshold", sa.Float, nullable=False, server_default="70.0"),
        # If welder's metric score reaches this value, drill is complete
    )

    # ── coaching_assignments ──────────────────────────────────────────────
    op.create_table(
        "coaching_assignments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("welder_id", sa.String(128), nullable=False),  # operator_id
        sa.Column("drill_id", sa.Integer, sa.ForeignKey("drills.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        # Values: active | complete | overdue
        sa.Column("sessions_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_coaching_assignments_welder_id", "coaching_assignments", ["welder_id"])
    op.create_index("ix_coaching_assignments_status", "coaching_assignments", ["status"])

def downgrade() -> None:
    op.drop_index("ix_coaching_assignments_status", "coaching_assignments")
    op.drop_index("ix_coaching_assignments_welder_id", "coaching_assignments")
    op.drop_table("coaching_assignments")
    op.drop_table("drills")
```

---

#### Step 2: Seed Drills

Add drill seeding to `backend/scripts/seed_demo_data.py`:
```python
SEED_DRILLS = [
    # angle_consistency (3 drills)
    {"target_metric": "angle_consistency", "title": "30-45-60 Angle Progression",
     "description": "Practice at 30°, 45°, and 60° for 5 minutes each. Focus on wrist stability. Use a guide block to feel the target angle before removing it.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "angle_consistency", "title": "Slow-Motion Angle Hold",
     "description": "Weld at half normal travel speed. Prioritise holding the torch angle constant over travel speed. Record 3 sessions.",
     "sessions_required": 3, "success_threshold": 72.0},
    {"target_metric": "angle_consistency", "title": "Angle Awareness Drill",
     "description": "Before each weld, verbally state the target angle. After each weld, estimate the actual average angle and compare to readout.",
     "sessions_required": 2, "success_threshold": 70.0},
    # thermal_symmetry (3 drills)
    {"target_metric": "thermal_symmetry", "title": "Reduced Travel Speed",
     "description": "Drop travel speed by 20%. Slower travel distributes heat more evenly across the joint width. Monitor N-S symmetry gauge.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "thermal_symmetry", "title": "Centreline Focus",
     "description": "Place a chalk line on the workpiece and keep the torch tip within 2mm of it throughout the weld.",
     "sessions_required": 2, "success_threshold": 70.0},
    {"target_metric": "thermal_symmetry", "title": "Pre-heat Pattern Practice",
     "description": "Apply pre-heat in a symmetrical pattern before welding. Verify N-S and E-W temps are within 5°C before starting.",
     "sessions_required": 2, "success_threshold": 72.0},
    # amps_stability (2 drills)
    {"target_metric": "amps_stability", "title": "Steady Contact Distance",
     "description": "Maintain consistent contact tip to work distance. Use a feeler gauge (12mm) to calibrate starting position before each run.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "amps_stability", "title": "Voltage-Amps Coupling Check",
     "description": "Verify machine settings match material spec sheet before each session. Check for worn contact tips.",
     "sessions_required": 2, "success_threshold": 70.0},
    # volts_stability (2 drills)
    {"target_metric": "volts_stability", "title": "Arc Length Consistency",
     "description": "Focus on maintaining constant arc length by watching the weld pool width (should stay uniform). Practice on scrap for 10 minutes first.",
     "sessions_required": 3, "success_threshold": 75.0},
    {"target_metric": "volts_stability", "title": "Travel Speed Uniformity",
     "description": "Use a metronome (80 BPM) to set travel rhythm. Consistent speed prevents voltage spikes from sudden pauses.",
     "sessions_required": 2, "success_threshold": 70.0},
    # heat_diss_consistency (2 drills)
    {"target_metric": "heat_diss_consistency", "title": "Cool-Down Interval Protocol",
     "description": "Add 30-second intervals between passes. Monitor center temp; do not start next pass until below 200°C.",
     "sessions_required": 3, "success_threshold": 70.0},
    {"target_metric": "heat_diss_consistency", "title": "Backstepping Technique",
     "description": "Practice backstep welding pattern (weld right-to-left in segments). Reduces cumulative heat buildup.",
     "sessions_required": 3, "success_threshold": 72.0},
]

def _seed_drills(db: Session) -> None:
    from ..models.coaching import Drill
    if db.query(Drill).count() >= len(SEED_DRILLS):
        return
    for d in SEED_DRILLS:
        db.add(Drill(**d))
    db.commit()
```

---

#### Step 3: SQLAlchemy Models

**Create** `backend/models/coaching.py`:
```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, func
from ..database import Base


class Drill(Base):
    __tablename__ = "drills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_metric = Column(String(64), nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    sessions_required = Column(Integer, nullable=False, default=3)
    success_threshold = Column(Float, nullable=False, default=70.0)


class CoachingAssignment(Base):
    __tablename__ = "coaching_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    welder_id = Column(String(128), nullable=False)
    drill_id = Column(Integer, ForeignKey("drills.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    sessions_completed = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

---

#### Step 4: Pydantic Schemas

**Create** `backend/schemas/coaching.py`:
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from ..models.shared_enums import WeldMetric, CoachingStatus


class DrillResponse(BaseModel):
    id: int
    target_metric: WeldMetric
    title: str
    description: str
    sessions_required: int
    success_threshold: float

    class Config:
        from_attributes = True


class CoachingAssignmentResponse(BaseModel):
    id: int
    welder_id: str
    drill: DrillResponse
    assigned_at: datetime
    status: CoachingStatus
    sessions_completed: int
    completed_at: Optional[datetime]
    # Progress derived field:
    current_metric_value: Optional[float] = None  # populated by service

    class Config:
        from_attributes = True


class CoachingPlanResponse(BaseModel):
    welder_id: str
    active_assignments: List[CoachingAssignmentResponse]
    completed_assignments: List[CoachingAssignmentResponse]
    auto_assigned: bool  # True if a new assignment was just created
```

---

#### Step 5: Coaching Service

**Create** `backend/services/coaching_service.py`:
```python
"""
Coaching service — drill assignment and progress evaluation.

DEPENDENCY RULE:
  coaching_service → benchmark_service (one-way only)
  benchmark_service must NEVER import coaching_service.

Assignment logic:
  - Takes benchmark_data (WelderBenchmarks) as parameter — caller fetches it
  - Selects drills for the 2 worst-performing metrics (lowest percentile)
  - Skips metrics already covered by an active assignment
  - Auto-triggered when score < AUTO_ASSIGN_THRESHOLD or same rule fails 3 consecutive sessions
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_

from ..models.coaching import Drill, CoachingAssignment
from ..models.shared_enums import WeldMetric, CoachingStatus
from ..schemas.coaching import CoachingPlanResponse, CoachingAssignmentResponse, DrillResponse
from ..schemas.benchmark import WelderBenchmarks

logger = logging.getLogger(__name__)

AUTO_ASSIGN_THRESHOLD = 60.0   # total score below this triggers auto-assign
MAX_ACTIVE_ASSIGNMENTS = 2     # never pile on more than 2 drills at once


def get_coaching_plan(welder_id: str, db: DBSession) -> CoachingPlanResponse:
    """Returns active and completed assignments for a welder."""
    active = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "active")
        .all()
    )
    completed = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "complete")
        .order_by(CoachingAssignment.completed_at.desc())
        .limit(10)
        .all()
    )

    def enrich(assignment: CoachingAssignment) -> CoachingAssignmentResponse:
        drill = db.query(Drill).filter_by(id=assignment.drill_id).first()
        return CoachingAssignmentResponse(
            id=assignment.id,
            welder_id=assignment.welder_id,
            drill=DrillResponse.model_validate(drill),
            assigned_at=assignment.assigned_at,
            status=CoachingStatus(assignment.status),
            sessions_completed=assignment.sessions_completed,
            completed_at=assignment.completed_at,
        )

    return CoachingPlanResponse(
        welder_id=welder_id,
        active_assignments=[enrich(a) for a in active],
        completed_assignments=[enrich(a) for a in completed],
        auto_assigned=False,
    )


def assign_coaching_plan(
    welder_id: str,
    benchmark_data: WelderBenchmarks,
    db: DBSession,
) -> CoachingPlanResponse:
    """
    Creates new assignments for the 2 worst metrics if not already assigned.
    Caller is responsible for fetching benchmark_data before calling this.
    Returns updated coaching plan.
    """
    # Find active metrics already covered
    active = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "active")
        .all()
    )

    if len(active) >= MAX_ACTIVE_ASSIGNMENTS:
        logger.info("Welder %s already has %d active assignments", welder_id, len(active))
        plan = get_coaching_plan(welder_id, db)
        plan.auto_assigned = False
        return plan

    covered_metrics = set()
    for a in active:
        drill = db.query(Drill).filter_by(id=a.drill_id).first()
        if drill:
            covered_metrics.add(drill.target_metric)

    # Sort metrics by percentile ascending (worst first)
    worst_metrics = sorted(
        [m for m in benchmark_data.metrics if m.metric.value not in covered_metrics],
        key=lambda m: m.percentile,
    )

    new_assignments = 0
    for bm in worst_metrics:
        if new_assignments + len(active) >= MAX_ACTIVE_ASSIGNMENTS:
            break
        if bm.percentile >= 50:
            continue  # only assign drills for below-median metrics

        drill = (
            db.query(Drill)
            .filter_by(target_metric=bm.metric.value)
            .order_by(Drill.success_threshold.asc())
            .first()
        )
        if not drill:
            continue

        assignment = CoachingAssignment(
            welder_id=welder_id,
            drill_id=drill.id,
            status="active",
            sessions_completed=0,
        )
        db.add(assignment)
        new_assignments += 1

    if new_assignments > 0:
        db.commit()

    plan = get_coaching_plan(welder_id, db)
    plan.auto_assigned = new_assignments > 0
    return plan


def evaluate_progress(welder_id: str, db: DBSession) -> int:
    """
    Called after each session. Checks if active assignments' target metrics
    have crossed the success_threshold. Marks complete if so.
    Returns count of assignments marked complete.
    """
    from ..services.benchmark_service import get_welder_benchmarks

    active = (
        db.query(CoachingAssignment)
        .filter(CoachingAssignment.welder_id == welder_id,
                CoachingAssignment.status == "active")
        .all()
    )
    if not active:
        return 0

    benchmarks = get_welder_benchmarks(welder_id, db)
    metric_values = {m.metric.value: m.welder_value for m in benchmarks.metrics}
    completed = 0

    for assignment in active:
        drill = db.query(Drill).filter_by(id=assignment.drill_id).first()
        if not drill:
            continue

        assignment.sessions_completed += 1
        current_val = metric_values.get(drill.target_metric, 0.0)

        if current_val >= drill.success_threshold:
            assignment.status = "complete"
            assignment.completed_at = datetime.now(timezone.utc)
            completed += 1

    db.commit()
    return completed
```

---

#### Step 6: Add Routes to welders.py

**Modify** `backend/routes/welders.py` — append:
```python
from ..services.coaching_service import get_coaching_plan, assign_coaching_plan
from ..services.benchmark_service import get_welder_benchmarks
from ..schemas.coaching import CoachingPlanResponse

@router.get("/{welder_id}/coaching-plan", response_model=CoachingPlanResponse)
def get_coaching(welder_id: str, db: Session = Depends(get_db)):
    """Returns active and completed coaching assignments for a welder."""
    return get_coaching_plan(welder_id, db)

@router.post("/{welder_id}/coaching-plan", response_model=CoachingPlanResponse)
def trigger_coaching_assignment(welder_id: str, db: Session = Depends(get_db)):
    """
    Evaluates benchmark data and assigns drills for worst-performing metrics.
    Safe to call multiple times — respects MAX_ACTIVE_ASSIGNMENTS guard.
    """
    benchmark_data = get_welder_benchmarks(welder_id, db)
    return assign_coaching_plan(welder_id, benchmark_data, db)
```

---

#### Step 7: Frontend Types

**Create** `my-app/src/types/coaching.ts`:
```typescript
import { WelderID, WeldMetric, CoachingStatus } from "./shared";

export interface Drill {
  id: number;
  target_metric: WeldMetric;
  title: string;
  description: string;
  sessions_required: number;
  success_threshold: number;
}

export interface CoachingAssignment {
  id: number;
  welder_id: WelderID;
  drill: Drill;
  assigned_at: string;   // ISO 8601
  status: CoachingStatus;
  sessions_completed: number;
  completed_at: string | null;
  current_metric_value: number | null;
}

export interface CoachingPlan {
  welder_id: WelderID;
  active_assignments: CoachingAssignment[];
  completed_assignments: CoachingAssignment[];
  auto_assigned: boolean;
}
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { CoachingPlan } from "@/types/coaching";

export async function fetchCoachingPlan(welderId: WelderID): Promise<CoachingPlan> {
  const res = await fetch(`${API_BASE}/api/welders/${welderId}/coaching-plan`);
  if (!res.ok) throw new Error(`fetchCoachingPlan failed: ${res.status}`);
  return res.json();
}

export async function triggerCoachingAssignment(welderId: WelderID): Promise<CoachingPlan> {
  const res = await fetch(`${API_BASE}/api/welders/${welderId}/coaching-plan`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`triggerCoachingAssignment failed: ${res.status}`);
  return res.json();
}
```

---

#### Step 8: CoachingPlanPanel Component

**Create** `my-app/src/components/welding/CoachingPlanPanel.tsx`:
```typescript
/**
 * CoachingPlanPanel — active drill assignments with progress.
 */
"use client";
import React, { useEffect, useState } from "react";
import { CoachingPlan, CoachingAssignment } from "@/types/coaching";
import { METRIC_LABELS } from "@/types/shared";
import { fetchCoachingPlan, triggerCoachingAssignment } from "@/lib/api";
import { logError } from "@/lib/logger";
import { WelderID } from "@/types/shared";

interface CoachingPlanPanelProps {
  welderId: WelderID;
}

function AssignmentCard({ a }: { a: CoachingAssignment }) {
  const pct = a.current_metric_value !== null
    ? Math.min(100, (a.current_metric_value / a.drill.success_threshold) * 100)
    : null;

  const statusColor = {
    active:   "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
    complete: "text-green-400 border-green-500/30 bg-green-500/5",
    overdue:  "text-red-400 border-red-500/30 bg-red-500/5",
  }[a.status];

  return (
    <div className={`rounded-lg border p-4 ${statusColor}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-sm font-semibold text-white">{a.drill.title}</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {METRIC_LABELS[a.drill.target_metric]} · {a.sessions_completed}/{a.drill.sessions_required} sessions
          </p>
        </div>
        <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded ${statusColor}`}>
          {a.status}
        </span>
      </div>

      <p className="text-xs text-neutral-400 leading-relaxed mb-3">{a.drill.description}</p>

      {pct !== null && (
        <div>
          <div className="flex justify-between text-xs text-neutral-500 mb-1">
            <span>Progress to target ({Math.round(a.drill.success_threshold)})</span>
            <span>{Math.round(pct)}%</span>
          </div>
          <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-cyan-500 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {a.status === "complete" && (
        <p className="text-xs text-green-400 mt-2">
          ✓ Drill complete · {a.completed_at ? new Date(a.completed_at).toLocaleDateString() : ""}
        </p>
      )}
    </div>
  );
}

export function CoachingPlanPanel({ welderId }: CoachingPlanPanelProps) {
  const [plan, setPlan] = useState<CoachingPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    let mounted = true;
    fetchCoachingPlan(welderId)
      .then((p) => { if (mounted) { setPlan(p); setLoading(false); } })
      .catch((err) => {
        logError("CoachingPlanPanel", err);
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [welderId]);

  const handleAssign = async () => {
    setAssigning(true);
    try {
      const p = await triggerCoachingAssignment(welderId);
      setPlan(p);
    } catch (err) {
      logError("CoachingPlanPanel.handleAssign", err);
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          Coaching Plan
        </h2>
        {!loading && (
          <button
            onClick={handleAssign}
            disabled={assigning}
            className="text-xs text-cyan-400 hover:text-cyan-300 underline disabled:text-neutral-600"
          >
            {assigning ? "Assigning…" : "Assign Drills"}
          </button>
        )}
      </div>

      {loading && <div className="h-24 bg-neutral-800 rounded animate-pulse" />}

      {!loading && plan && (
        <>
          {plan.auto_assigned && (
            <div className="text-xs text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 rounded px-3 py-2 mb-3">
              New drills assigned based on your latest benchmarks.
            </div>
          )}

          {plan.active_assignments.length === 0 ? (
            <p className="text-sm text-neutral-500 text-center py-4">
              No active drills. Click "Assign Drills" to get recommendations.
            </p>
          ) : (
            <div className="space-y-3">
              {plan.active_assignments.map((a) => (
                <AssignmentCard key={a.id} a={a} />
              ))}
            </div>
          )}

          {plan.completed_assignments.length > 0 && (
            <details className="mt-4">
              <summary className="text-xs text-neutral-600 cursor-pointer hover:text-neutral-400">
                {plan.completed_assignments.length} completed drill(s)
              </summary>
              <div className="space-y-2 mt-2">
                {plan.completed_assignments.map((a) => (
                  <AssignmentCard key={a.id} a={a} />
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  );
}

export default CoachingPlanPanel;
```

---

#### Step 9: Wire into Welder Report

**Modify** `my-app/src/app/seagull/welder/[id]/page.tsx`:
```typescript
import { CoachingPlanPanel } from "@/components/welding/CoachingPlanPanel";

// In ReportLayout:
coaching={<CoachingPlanPanel welderId={welderId} />}
```

Note: CoachingPlanPanel fetches its own data internally — no new Promise.all entry needed.

---

#### Wire evaluate_progress into score endpoint

**Modify** `backend/routes/sessions.py` — in the GET score handler, after persisting score_total:
```python
from ..services.coaching_service import evaluate_progress

# After existing score_total persistence:
if session.operator_id:
    try:
        evaluate_progress(session.operator_id, db)
    except Exception as e:
        logger.warning("evaluate_progress failed for %s: %s", session.operator_id, e)
        # Non-critical — do not fail the score request
```

---

#### Batch 3 Agent 2 Verification Checklist
- [ ] Migration 008 runs clean; `drills` table has 12 seeded rows
- [ ] `POST /api/welders/mike-chen/coaching-plan` returns plan with 1–2 active assignments
- [ ] Second POST respects `MAX_ACTIVE_ASSIGNMENTS = 2` guard
- [ ] `GET /api/sessions/sess_novice_001/score` triggers evaluate_progress without error
- [ ] `CoachingPlanPanel` renders active drills with progress bars
- [ ] `Assign Drills` button triggers POST and updates UI

---

### Batch 3 Agent 3 — Operator Credentialing + Certification Tracking

**Files owned:** `009_certifications.py`, `backend/models/certification.py`, `backend/schemas/certification.py`, `backend/services/cert_service.py`, `my-app/src/types/certification.ts`, `my-app/src/components/welding/CertificationCard.tsx`
**Files modified:** `backend/routes/welders.py` (add route), `my-app/src/lib/api.ts`, welder report page (certification slot), PDF route + component (extend schema)
**Files NOT touched:** Coaching files, benchmark files, any Batch 3 Agent 1 or Agent 2 files

---

#### Step 1: Fill Migration 009

**Modify** `backend/alembic/versions/009_certifications.py`:
```python
def upgrade() -> None:
    # ── cert_standards ────────────────────────────────────────────────────
    op.create_table(
        "cert_standards",
        sa.Column("id", sa.String(32), primary_key=True),
        # e.g. "aws_d1_1", "iso_9606", "internal_basic"
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("required_score", sa.Float, nullable=False),
        sa.Column("sessions_required", sa.Integer, nullable=False),
        sa.Column("weld_type", sa.String(32), nullable=True),
        # null = applies to all weld types
    )

    # ── welder_certifications ─────────────────────────────────────────────
    op.create_table(
        "welder_certifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("welder_id", sa.String(128), nullable=False),
        sa.Column("cert_standard_id", sa.String(32),
                  sa.ForeignKey("cert_standards.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_started"),
        # Values: not_started | on_track | at_risk | certified
        sa.Column("evaluated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("qualifying_session_ids", sa.JSON, nullable=True),
        # List of session_ids that qualified for this cert
        sa.UniqueConstraint("welder_id", "cert_standard_id", name="uq_welder_cert"),
    )
    op.create_index("ix_welder_certifications_welder_id", "welder_certifications", ["welder_id"])

def downgrade() -> None:
    op.drop_index("ix_welder_certifications_welder_id", "welder_certifications")
    op.drop_table("welder_certifications")
    op.drop_table("cert_standards")
```

---

#### Step 2: Seed Certification Standards

Add to `backend/scripts/seed_demo_data.py`:
```python
def _seed_cert_standards(db: Session) -> None:
    from ..models.certification import CertStandard
    STANDARDS = [
        {"id": "aws_d1_1",       "name": "AWS D1.1 Structural Welding",
         "required_score": 80.0, "sessions_required": 3, "weld_type": None},
        {"id": "iso_9606",        "name": "ISO 9606 Welding Qualification",
         "required_score": 85.0, "sessions_required": 4, "weld_type": None},
        {"id": "internal_basic",  "name": "Internal Basic Certification",
         "required_score": 65.0, "sessions_required": 2, "weld_type": None},
    ]
    for s in STANDARDS:
        if not db.query(CertStandard).filter_by(id=s["id"]).first():
            db.add(CertStandard(**s))
    db.commit()
```

---

#### Step 3: SQLAlchemy Models

**Create** `backend/models/certification.py`:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, UniqueConstraint, func
from ..database import Base


class CertStandard(Base):
    __tablename__ = "cert_standards"

    id = Column(String(32), primary_key=True)
    name = Column(String(256), nullable=False)
    required_score = Column(Float, nullable=False)
    sessions_required = Column(Integer, nullable=False)
    weld_type = Column(String(32), nullable=True)


class WelderCertification(Base):
    __tablename__ = "welder_certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    welder_id = Column(String(128), nullable=False)
    cert_standard_id = Column(String(32), ForeignKey("cert_standards.id"), nullable=False)
    status = Column(String(32), nullable=False, default="not_started")
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    qualifying_session_ids = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("welder_id", "cert_standard_id", name="uq_welder_cert"),
    )
```

---

#### Step 4: Pydantic Schemas

**Create** `backend/schemas/certification.py`:
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from ..models.shared_enums import CertificationStatus


class CertStandardResponse(BaseModel):
    id: str
    name: str
    required_score: float
    sessions_required: int
    weld_type: Optional[str]

    class Config:
        from_attributes = True


class CertificationStatusResponse(BaseModel):
    cert_standard: CertStandardResponse
    status: CertificationStatus
    evaluated_at: datetime
    qualifying_sessions: int     # count of sessions meeting the score threshold
    sessions_needed: int         # remaining sessions needed
    current_avg_score: Optional[float]
    sessions_to_target: Optional[int]  # projected sessions at current rate
    qualifying_session_ids: Optional[List[str]]

    class Config:
        from_attributes = True


class WelderCertificationSummary(BaseModel):
    welder_id: str
    certifications: List[CertificationStatusResponse]
```
---

#### Step 5: Certification Service

**Create** `backend/services/cert_service.py`:
```python
"""
Certification service — evaluates welder readiness against cert standards.
Reads score history from sessions table.
No dependency on coaching_service or benchmark_service.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from ..models.certification import CertStandard, WelderCertification
from ..models.session import SessionModel
from ..models.shared_enums import CertificationStatus
from ..schemas.certification import (
    CertificationStatusResponse, WelderCertificationSummary, CertStandardResponse
)

logger = logging.getLogger(__name__)


def get_certification_status(welder_id: str, db: DBSession) -> WelderCertificationSummary:
    """
    Evaluates welder against all cert standards.
    Upserts welder_certifications rows with latest status.
    """
    standards = db.query(CertStandard).all()
    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.operator_id == welder_id,
            SessionModel.status == "COMPLETE",
            SessionModel.score_total.isnot(None),
        )
        .order_by(SessionModel.start_time.desc())
        .all()
    )

    results = []
    for std in standards:
        # Filter sessions by weld_type if standard specifies it
        relevant = [
            s for s in sessions
            if std.weld_type is None or s.weld_type == std.weld_type
        ]

        qualifying = [s for s in relevant if s.score_total >= std.required_score]
        qual_count = len(qualifying)
        avg_score = (
            sum(s.score_total for s in relevant[:5]) / min(len(relevant), 5)
            if relevant else None
        )

        # Determine status
        if qual_count >= std.sessions_required:
            status = CertificationStatus.CERTIFIED
        elif qual_count > 0:
            status = CertificationStatus.ON_TRACK
        elif avg_score and avg_score < std.required_score - 15:
            status = CertificationStatus.AT_RISK
        elif relevant:
            status = CertificationStatus.ON_TRACK
        else:
            status = CertificationStatus.NOT_STARTED

        sessions_needed = max(0, std.sessions_required - qual_count)

        # Projection: if avg_score < required, estimate improvement rate
        sessions_to_target = None
        if status not in (CertificationStatus.CERTIFIED,):
            if avg_score and avg_score < std.required_score:
                gap = std.required_score - avg_score
                if len(relevant) >= 2:
                    recent_scores = [s.score_total for s in relevant[:5]]
                    if len(recent_scores) >= 2:
                        rate = (recent_scores[0] - recent_scores[-1]) / len(recent_scores)
                        if rate > 0:
                            sessions_to_target = int(gap / rate) + sessions_needed

        # Upsert certification record
        record = db.query(WelderCertification).filter_by(
            welder_id=welder_id, cert_standard_id=std.id
        ).first()
        now = datetime.now(timezone.utc)
        if record:
            record.status = status.value
            record.evaluated_at = now
            record.qualifying_session_ids = [s.session_id for s in qualifying]
        else:
            record = WelderCertification(
                welder_id=welder_id,
                cert_standard_id=std.id,
                status=status.value,
                evaluated_at=now,
                qualifying_session_ids=[s.session_id for s in qualifying],
            )
            db.add(record)

        results.append(CertificationStatusResponse(
            cert_standard=CertStandardResponse.model_validate(std),
            status=status,
            evaluated_at=now,
            qualifying_sessions=qual_count,
            sessions_needed=sessions_needed,
            current_avg_score=round(avg_score, 1) if avg_score else None,
            sessions_to_target=sessions_to_target,
            qualifying_session_ids=[s.session_id for s in qualifying],
        ))

    db.commit()
    return WelderCertificationSummary(welder_id=welder_id, certifications=results)
```

---

#### Step 6: Add Route to welders.py

**Modify** `backend/routes/welders.py` — append:
```python
from ..services.cert_service import get_certification_status
from ..schemas.certification import WelderCertificationSummary

@router.get("/{welder_id}/certification-status", response_model=WelderCertificationSummary)
def get_certifications(welder_id: str, db: Session = Depends(get_db)):
    """Evaluates welder against all cert standards. Upserts records."""
    return get_certification_status(welder_id, db)
```

---

#### Step 7: Frontend Types

**Create** `my-app/src/types/certification.ts`:
```typescript
import { WelderID, CertificationStatus } from "./shared";

export interface CertStandard {
  id: string;
  name: string;
  required_score: number;
  sessions_required: number;
  weld_type: string | null;
}

export interface CertificationStatusItem {
  cert_standard: CertStandard;
  status: CertificationStatus;
  evaluated_at: string;    // ISO 8601
  qualifying_sessions: number;
  sessions_needed: number;
  current_avg_score: number | null;
  sessions_to_target: number | null;
  qualifying_session_ids: string[] | null;
}

export interface WelderCertificationSummary {
  welder_id: WelderID;
  certifications: CertificationStatusItem[];
}
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { WelderCertificationSummary } from "@/types/certification";

export async function fetchCertificationStatus(
  welderId: WelderID
): Promise<WelderCertificationSummary> {
  const res = await fetch(`${API_BASE}/api/welders/${welderId}/certification-status`);
  if (!res.ok) throw new Error(`fetchCertificationStatus failed: ${res.status}`);
  return res.json();
}
```

---

#### Step 8: CertificationCard Component

**Create** `my-app/src/components/welding/CertificationCard.tsx`:
```typescript
/**
 * CertificationCard — per-standard readiness panel.
 * Shows status badge, progress bar, sessions remaining, projected timeline.
 */
"use client";
import React, { useEffect, useState } from "react";
import { WelderCertificationSummary, CertificationStatusItem } from "@/types/certification";
import { CertificationStatus, WelderID } from "@/types/shared";
import { fetchCertificationStatus } from "@/lib/api";
import { logError } from "@/lib/logger";

interface CertificationCardProps {
  welderId: WelderID;
}

const STATUS_STYLES: Record<CertificationStatus, {
  badge: string; bar: string; icon: string;
}> = {
  certified:   { badge: "bg-green-500/10 text-green-400 border-green-500/30",  bar: "bg-green-500",  icon: "✓" },
  on_track:    { badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",     bar: "bg-cyan-500",   icon: "→" },
  at_risk:     { badge: "bg-red-500/10 text-red-400 border-red-500/30",        bar: "bg-red-500",    icon: "⚠" },
  not_started: { badge: "bg-neutral-800 text-neutral-500 border-neutral-700",  bar: "bg-neutral-700", icon: "○" },
};

function CertRow({ item }: { item: CertificationStatusItem }) {
  const styles = STATUS_STYLES[item.status];
  const progress = Math.min(100,
    (item.qualifying_sessions / item.cert_standard.sessions_required) * 100
  );

  return (
    <div className="py-3 border-b border-neutral-800 last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-white">{item.cert_standard.name}</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            Score ≥ {item.cert_standard.required_score} · {item.cert_standard.sessions_required} sessions
          </p>
        </div>
        <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded border ${styles.badge}`}>
          {styles.icon} {item.status.replace("_", " ")}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden mb-1.5">
        <div
          className={`h-full rounded-full transition-all ${styles.bar}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex justify-between text-xs text-neutral-600">
        <span>
          {item.qualifying_sessions}/{item.cert_standard.sessions_required} qualifying sessions
        </span>
        {item.status === "certified" ? (
          <span className="text-green-400">Certified</span>
        ) : item.sessions_to_target ? (
          <span>~{item.sessions_to_target} sessions to cert</span>
        ) : item.current_avg_score ? (
          <span>Avg: {item.current_avg_score}/100</span>
        ) : null}
      </div>
    </div>
  );
}

export function CertificationCard({ welderId }: CertificationCardProps) {
  const [summary, setSummary] = useState<WelderCertificationSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    fetchCertificationStatus(welderId)
      .then((s) => { if (mounted) { setSummary(s); setLoading(false); } })
      .catch((err) => {
        logError("CertificationCard", err);
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [welderId]);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400 mb-4">
        Certification Readiness
      </h2>

      {loading && <div className="h-32 bg-neutral-800 rounded animate-pulse" />}

      {!loading && !summary && (
        <p className="text-sm text-neutral-500">Unable to load certification data.</p>
      )}

      {!loading && summary && (
        <div>
          {summary.certifications.map((item) => (
            <CertRow key={item.cert_standard.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export default CertificationCard;
```

---

#### Step 9: Wire into Welder Report and PDF

**Modify** `my-app/src/app/seagull/welder/[id]/page.tsx`:
```typescript
import { CertificationCard } from "@/components/welding/CertificationCard";

// In ReportLayout:
certification={<CertificationCard welderId={welderId} />}
```

**Modify** `my-app/src/components/pdf/WelderReportPDF.tsx`:

Extend props:
```typescript
interface WelderReportPDFProps {
  // ... existing ...
  certifications?: Array<{
    name: string;
    status: string;
    qualifying_sessions: number;
    sessions_required: number;
  }> | null;
}
```

Add certification section after feedback items:
```tsx
{certifications && certifications.length > 0 && (
  <View style={{ marginTop: 16 }}>
    <Text style={{ fontSize: 8, color: "#737373", textTransform: "uppercase",
                   letterSpacing: 1, marginBottom: 6 }}>
      Certification Readiness
    </Text>
    {certifications.map((c, i) => (
      <View key={i} style={{ flexDirection: "row", justifyContent: "space-between",
                              paddingVertical: 3, borderBottomWidth: 0.5,
                              borderBottomColor: "#262626" }}>
        <Text style={{ fontSize: 9, color: "#d4d4d4" }}>{sanitizeText(c.name)}</Text>
        <Text style={{ fontSize: 9, color: "#737373" }}>
          {c.qualifying_sessions}/{c.sessions_required} · {sanitizeText(c.status)}
        </Text>
      </View>
    ))}
  </View>
)}
```

**Modify** `my-app/src/app/api/welder-report-pdf/route.ts` — extend Zod schema:
```typescript
certifications: z.array(z.object({
  name: z.string(),
  status: z.string(),
  qualifying_sessions: z.number(),
  sessions_required: z.number(),
})).optional().nullable(),
```

---

#### Batch 3 Agent 3 Verification Checklist
- [ ] Migration 009 runs clean; 3 cert_standards seeded
- [ ] `GET /api/welders/mike-chen/certification-status` returns all 3 standards with status
- [ ] Expert welder (high scores) shows CERTIFIED or ON_TRACK for aws_d1_1
- [ ] Novice welder shows AT_RISK or NOT_STARTED for aws_d1_1
- [ ] `CertificationCard` renders all 3 standards with progress bars
- [ ] PDF with certifications: table section renders correctly

---

## BATCH 4 — THREE AGENTS IN PARALLEL
**Prerequisite:** Batch 3 complete and verified.
**Duration:** Days 31–42.
**Agents:** Multi-Site UI | iPad PWA | Wire + Harden

---

### Batch 4 Agent 1 — Multi-Site UI + Supervisor Scoping

**Files owned:** `backend/routes/sites.py`, `my-app/src/types/site.ts`, `my-app/src/components/dashboard/SiteSelector.tsx`
**Files modified:** `backend/routes/aggregate.py` (add filters), `backend/services/aggregate_service.py` (add WHERE), `my-app/src/lib/api.ts`, supervisor page, seagull dashboard
**Files NOT touched:** Any Batch 4 Agent 2 or Agent 3 files

---

#### Step 1: Sites Route

**Create** `backend/routes/sites.py`:
```python
"""
Sites and teams CRUD endpoints.
Multi-site filtering for aggregate queries uses site_id/team_id params on existing routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.site import Site, Team
from ..schemas.site import SiteCreate, TeamCreate, SiteResponse, TeamResponse

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.get("", response_model=List[SiteResponse])
def list_sites(db: Session = Depends(get_db)):
    return db.query(Site).order_by(Site.name).all()


@router.post("", response_model=SiteResponse, status_code=201)
def create_site(body: SiteCreate, db: Session = Depends(get_db)):
    if db.query(Site).filter_by(id=body.id).first():
        raise HTTPException(status_code=409, detail=f"Site {body.id} already exists")
    site = Site(**body.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/{site_id}/teams", response_model=List[TeamResponse])
def list_teams(site_id: str, db: Session = Depends(get_db)):
    site = db.query(Site).filter_by(id=site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    return db.query(Team).filter_by(site_id=site_id).order_by(Team.name).all()


@router.post("/{site_id}/teams", response_model=TeamResponse, status_code=201)
def create_team(site_id: str, body: TeamCreate, db: Session = Depends(get_db)):
    site = db.query(Site).filter_by(id=site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    team = Team(**body.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team
```

**Modify** `backend/main.py`:
```python
from .routes import sites
app.include_router(sites.router)
```

---

#### Step 2: Extend Aggregate Service for Filters

**Modify** `backend/services/aggregate_service.py`:

In the main KPI query function, add optional filters:
```python
def get_aggregate_kpis(
    db: Session,
    date_start: date,
    date_end: date,
    site_id: Optional[str] = None,
    team_id: Optional[str] = None,
) -> AggregateKPIResponse:
    """
    Existing function signature extended with optional site_id/team_id.
    When None, returns all sessions (backwards compatible).
    """
    q = db.query(SessionModel).filter(
        SessionModel.start_time >= date_start,
        SessionModel.start_time <= date_end_inclusive,
        SessionModel.status == "COMPLETE",
    )
    # NEW: apply optional filters
    if team_id:
        q = q.filter(SessionModel.team_id == team_id)
    elif site_id:
        # Get all team_ids for this site
        team_ids = [t.id for t in db.query(Team).filter_by(site_id=site_id).all()]
        if team_ids:
            q = q.filter(SessionModel.team_id.in_(team_ids))
        else:
            q = q.filter(sa.false())  # no teams = no sessions

    # Rest of existing function unchanged
```

**Modify** `backend/routes/aggregate.py`:

Add query params:
```python
@router.get("/api/sessions/aggregate")
def get_aggregate(
    # ... existing params ...
    site_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return get_aggregate_kpis(db, date_start, date_end,
                               site_id=site_id, team_id=team_id)
```

---

#### Step 3: Frontend Site Types + API

**Create** `my-app/src/types/site.ts`:
```typescript
export interface Site {
  id: string;
  name: string;
  location: string | null;
  created_at: string;
  teams: Team[];
}

export interface Team {
  id: string;
  site_id: string;
  name: string;
  created_at: string;
}
```

**Modify** `my-app/src/lib/api.ts` — append:
```typescript
import { Site } from "@/types/site";

export async function fetchSites(): Promise<Site[]> {
  const res = await fetch(`${API_BASE}/api/sites`);
  if (!res.ok) throw new Error(`fetchSites failed: ${res.status}`);
  return res.json();
}
```

---

#### Step 4: SiteSelector Component

**Create** `my-app/src/components/dashboard/SiteSelector.tsx`:
```typescript
/**
 * SiteSelector — site/team dropdown for supervisor dashboard.
 * Stores selection in URL search params (?site=X&team=Y).
 * WWAD orthogonality: no thermal/welding imports.
 */
"use client";
import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Site } from "@/types/site";
import { fetchSites } from "@/lib/api";

export function SiteSelector() {
  const router = useRouter();
  const params = useSearchParams();
  const [sites, setSites] = useState<Site[]>([]);

  useEffect(() => {
    fetchSites().then(setSites).catch(() => {});
  }, []);

  const currentSite = params.get("site") ?? "";
  const currentTeam = params.get("team") ?? "";

  const selectedSite = sites.find(s => s.id === currentSite);

  const update = (site: string, team: string) => {
    const p = new URLSearchParams(params.toString());
    if (site) p.set("site", site); else p.delete("site");
    if (team) p.set("team", team); else p.delete("team");
    router.push(`?${p.toString()}`);
  };

  if (sites.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <select
        value={currentSite}
        onChange={(e) => update(e.target.value, "")}
        className="bg-neutral-800 border border-neutral-700 rounded px-3 py-1.5 text-sm text-white"
      >
        <option value="">All Sites</option>
        {sites.map(s => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      {selectedSite && selectedSite.teams.length > 0 && (
        <select
          value={currentTeam}
          onChange={(e) => update(currentSite, e.target.value)}
          className="bg-neutral-800 border border-neutral-700 rounded px-3 py-1.5 text-sm text-white"
        >
          <option value="">All Teams</option>
          {selectedSite.teams.map(t => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
      )}
    </div>
  );
}
```

**Modify** `my-app/src/app/(app)/supervisor/page.tsx`:
```typescript
import { SiteSelector } from "@/components/dashboard/SiteSelector";
import { useSearchParams } from "next/navigation";

// In supervisor page header:
<SiteSelector />

// Pass site/team to fetchAggregateKPIs:
const searchParams = useSearchParams();
const siteId = searchParams.get("site") ?? undefined;
const teamId = searchParams.get("team") ?? undefined;

fetchAggregateKPIs({ date_start, date_end, site_id: siteId, team_id: teamId })
```

---

#### Batch 4 Agent 1 Verification Checklist
- [ ] `GET /api/sites` returns seeded demo site
- [ ] `GET /api/sites/site_demo_001/teams` returns demo team
- [ ] `GET /api/sessions/aggregate?site_id=site_demo_001` filters correctly
- [ ] `GET /api/sessions/aggregate` (no params) still returns all sessions
- [ ] SiteSelector renders and updates URL params
- [ ] Supervisor page re-fetches when site/team param changes

---

### Batch 4 Agent 2 — iPad Companion PWA

**Prerequisite:** Batch 1 Agent 2's `GET /api/sessions/{id}/warp-risk` and prediction service must be fully working.
**Files owned:** `my-app/public/manifest.json`, `my-app/src/app/(app)/live/page.tsx`, `my-app/src/components/welding/LiveAngleIndicator.tsx`, `my-app/src/components/live/LiveStatusLED.tsx`
**Files modified:** `my-app/next.config.js` (PWA), `my-app/src/lib/api.ts` (live poll)
**Files NOT touched:** TorchViz3D, HeatmapPlate3D, any other 3D files

---

#### Step 1: PWA Manifest

**Create** `my-app/public/manifest.json`:
```json
{
  "name": "WarpSense Live",
  "short_name": "WarpSense",
  "description": "Live weld quality monitoring for the bay floor",
  "start_url": "/live",
  "display": "standalone",
  "orientation": "landscape",
  "background_color": "#0a0a0a",
  "theme_color": "#22d3ee",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

**Modify** `my-app/src/app/layout.tsx` — add to `<head>`:
```tsx
<link rel="manifest" href="/manifest.json" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
```

---

#### Step 2: Live Angle Indicator (2D SVG — no WebGL)

**Create** `my-app/src/components/welding/LiveAngleIndicator.tsx`:
```typescript
/**
 * LiveAngleIndicator — 2D SVG semicircle angle display.
 * No WebGL. No Canvas. Touch-optimised.
 * Shows target angle zone, warning zone, critical zone.
 *
 * Target: 45°. Warning: ±5°. Critical: ±15°.
 * These match existing micro-feedback thresholds in micro-feedback.ts.
 */
"use client";
import React from "react";
import { RiskLevel } from "@/types/shared";

interface LiveAngleIndicatorProps {
  currentAngle: number;
  targetAngle?: number;
  riskLevel: RiskLevel;
  size?: number;
}

const RISK_COLOR: Record<RiskLevel, string> = {
  ok:       "#22d3ee",
  warning:  "#fbbf24",
  critical: "#ef4444",
};

function polarToXY(angleDeg: number, radius: number, cx: number, cy: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
}

export function LiveAngleIndicator({
  currentAngle,
  targetAngle = 45,
  riskLevel,
  size = 200,
}: LiveAngleIndicatorProps) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const color = RISK_COLOR[riskLevel];

  const currentPos = polarToXY(currentAngle, r, cx, cy);
  const targetPos = polarToXY(targetAngle, r, cx, cy);

  return (
    <svg
      width={size} height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-label={`Torch angle: ${Math.round(currentAngle)} degrees`}
    >
      {/* Background arc track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#262626" strokeWidth={12} />

      {/* Warning zone arcs */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#92400e" strokeWidth={12}
        strokeDasharray={`${(10 / 360) * 2 * Math.PI * r} ${2 * Math.PI * r}`}
        strokeDashoffset={-((targetAngle - 5 - 90) / 360) * 2 * Math.PI * r}
      />

      {/* Target angle marker */}
      <line
        x1={cx} y1={cy}
        x2={targetPos.x} y2={targetPos.y}
        stroke="#525252" strokeWidth={2} strokeDasharray="4 4"
      />

      {/* Current angle needle */}
      <line
        x1={cx} y1={cy}
        x2={currentPos.x} y2={currentPos.y}
        stroke={color} strokeWidth={4} strokeLinecap="round"
      />
      <circle cx={currentPos.x} cy={currentPos.y} r={6} fill={color} />
      <circle cx={cx} cy={cy} r={8} fill={color} />

      {/* Angle value */}
      <text x={cx} y={cy + r * 0.5}
        textAnchor="middle" fill={color}
        fontSize={size * 0.12} fontWeight="bold" fontFamily="monospace">
        {Math.round(currentAngle)}°
      </text>
      <text x={cx} y={cy + r * 0.7}
        textAnchor="middle" fill="#525252"
        fontSize={size * 0.07} fontFamily="monospace">
        target {targetAngle}°
      </text>
    </svg>
  );
}

export default LiveAngleIndicator;
```

---

#### Step 3: Live Status LED

**Create** `my-app/src/components/live/LiveStatusLED.tsx`:
```typescript
/**
 * LiveStatusLED — full-width traffic light for iPad mount view.
 * Height configurable; defaults to 120px for large bay-floor visibility.
 */
"use client";
import React from "react";
import { RiskLevel } from "@/types/shared";

interface LiveStatusLEDProps {
  riskLevel: RiskLevel;
  message?: string;
  height?: number;
}

const LED_CONFIG: Record<RiskLevel, { bg: string; text: string; label: string }> = {
  ok:       { bg: "bg-green-600",  text: "text-green-100",  label: "NOMINAL" },
  warning:  { bg: "bg-amber-500",  text: "text-amber-100",  label: "WARP WARNING" },
  critical: { bg: "bg-red-600",    text: "text-red-100",    label: "WARP CRITICAL" },
};

export function LiveStatusLED({ riskLevel, message, height = 120 }: LiveStatusLEDProps) {
  const config = LED_CONFIG[riskLevel];
  return (
    <div
      className={`w-full flex flex-col items-center justify-center rounded-xl transition-colors duration-300 ${config.bg}`}
      style={{ height }}
    >
      <span className={`text-4xl font-black tracking-widest uppercase ${config.text}`}>
        {config.label}
      </span>
      {message && (
        <span className={`text-sm mt-1 opacity-80 ${config.text}`}>{message}</span>
      )}
    </div>
  );
}

export default LiveStatusLED;
```

---

#### Step 4: Live Page

**Create** `my-app/src/app/(app)/live/page.tsx`:
```typescript
/**
 * /live — iPad companion PWA page.
 * Polls warp-risk every 5s (no WebSocket for MVP; polling is simpler and reliable).
 * Touch-optimised. No WebGL. Minimum 48px touch targets.
 *
 * Layout (landscape):
 *   Left 2/3: Status LED + Angle Indicator
 *   Right 1/3: Session info + Latest alert toast
 */
"use client";
import React, { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { LiveStatusLED } from "@/components/live/LiveStatusLED";
import { LiveAngleIndicator } from "@/components/welding/LiveAngleIndicator";
import { WarpRiskResponse } from "@/types/prediction";
import { RiskLevel } from "@/types/shared";
import { fetchWarpRisk } from "@/lib/api";
import { logError } from "@/lib/logger";

const POLL_INTERVAL_MS = 5000;
const DEFAULT_SESSION = "sess_novice_001";

export default function LivePage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session") ?? DEFAULT_SESSION;

  const [risk, setRisk] = useState<WarpRiskResponse | null>(null);
  const [angle, setAngle] = useState<number>(45);
  const [lastAlert, setLastAlert] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const poll = async () => {
    try {
      const data = await fetchWarpRisk(sessionId);
      setRisk(data);
      setConnected(true);
      if (data.risk_level !== "ok") {
        setLastAlert(`Warp risk: ${Math.round(data.probability * 100)}% at ${new Date().toLocaleTimeString()}`);
      }
    } catch (err) {
      logError("LivePage.poll", err);
      setConnected(false);
    }
  };

  useEffect(() => {
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [sessionId]);

  const riskLevel: RiskLevel = risk?.risk_level ?? "ok";

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col p-4 gap-4" style={{ touchAction: "manipulation" }}>

      {/* Connection indicator */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white tracking-widest uppercase">WarpSense Live</h1>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-xs text-neutral-500">{connected ? "Connected" : "Disconnected"}</span>
          <span className="text-xs text-neutral-600 ml-2">{sessionId}</span>
        </div>
      </div>

      {/* Main grid */}
      <div className="flex-1 grid grid-cols-3 gap-4">
        {/* Left: Status + Angle */}
        <div className="col-span-2 flex flex-col gap-4">
          <LiveStatusLED riskLevel={riskLevel} height={120} />
          <div className="flex-1 flex items-center justify-center bg-neutral-900 rounded-xl">
            <LiveAngleIndicator
              currentAngle={angle}
              riskLevel={riskLevel}
              size={240}
            />
          </div>
        </div>

        {/* Right: Info panel */}
        <div className="flex flex-col gap-3">
          {/* Warp probability */}
          <div className="bg-neutral-900 rounded-xl p-4 text-center">
            <p className="text-xs text-neutral-500 uppercase tracking-widest mb-1">Warp Risk</p>
            <p className={`text-5xl font-black tabular-nums ${
              riskLevel === "critical" ? "text-red-400" :
              riskLevel === "warning"  ? "text-amber-400" : "text-cyan-400"
            }`}>
              {risk ? `${Math.round(risk.probability * 100)}%` : "—"}
            </p>
          </div>

          {/* Latest alert */}
          {lastAlert && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
              <p className="text-xs text-amber-400 font-semibold uppercase tracking-wider mb-1">Last Alert</p>
              <p className="text-xs text-amber-300">{lastAlert}</p>
              <button
                onClick={() => setLastAlert(null)}
                className="mt-2 text-xs text-neutral-500 hover:text-neutral-300 min-h-[48px] w-full text-left"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Session selector */}
          <div className="bg-neutral-900 rounded-xl p-4 mt-auto">
            <p className="text-xs text-neutral-500 uppercase tracking-widest mb-2">Session</p>
            <p className="text-sm text-white font-mono">{sessionId}</p>
            <p className="text-xs text-neutral-600 mt-1">
              Updated {new Date().toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

#### Batch 4 Agent 2 Verification Checklist
- [ ] `/live` renders on 1024×768 (iPad landscape) without horizontal scroll
- [ ] All interactive elements have min 48px touch target
- [ ] Status LED transitions green/amber/red based on risk_level
- [ ] Polling fires every 5s; "Disconnected" shows when API unreachable
- [ ] No TorchViz3D or Canvas elements anywhere in live page
- [ ] `manifest.json` valid JSON; links from layout head
- [ ] `npm run build` passes

---

### Batch 4 Agent 3 — Wire + Harden

**Files owned:** none new
**Files modified:** `backend/routes/sessions.py` (coaching auto-trigger), `my-app/src/app/seagull/welder/[id]/page.tsx` (final wiring audit), `context/CONTEXT.md`
**Purpose:** Connect the loose wires across all batches, verify the full stack, update documentation.

---

#### Step 1: Auto-Assign Coaching After Score

**Modify** `backend/routes/sessions.py`:

In `GET /api/sessions/{session_id}/score`, after the existing score_total persistence block, add:
```python
from ..services.coaching_service import assign_coaching_plan, evaluate_progress
from ..services.benchmark_service import get_welder_benchmarks
from ..models.shared_enums import CertificationStatus

# After score_total persisted:
if session.operator_id:
    try:
        # Progress evaluation — marks completed drills
        evaluate_progress(session.operator_id, db)

        # Auto-assign new drills if score below threshold
        if score.total < 60:
            benchmark_data = get_welder_benchmarks(session.operator_id, db)
            assign_coaching_plan(session.operator_id, benchmark_data, db)
    except Exception as e:
        logger.warning("Post-score coaching hook failed for %s: %s",
                       session.operator_id, e)
        # Never fail the score request due to coaching errors
```

---

#### Step 2: Full ReportLayout Audit

Verify `my-app/src/app/seagull/welder/[id]/page.tsx` has all slots populated:
```tsx
<ReportLayout
  welderName={...}
  sessionId={sessionId}
  scoreTotal={score.total}
  weldType={session.weld_type}
  sessionDate={new Date(session.start_time).toLocaleDateString()}
  actions={<ActionsBar />}
  narrative={<NarrativePanel sessionId={sessionId} />}
  heatmaps={<SideBySideHeatmaps ... />}
  feedback={<FeedbackPanel ... />}
  trajectory={trajectory ? <TrajectoryChart trajectory={trajectory} /> : undefined}
  benchmarks={benchmarks ? <BenchmarkPanel benchmarks={benchmarks} /> : undefined}
  coaching={<CoachingPlanPanel welderId={welderId} />}
  certification={<CertificationCard welderId={welderId} />}
/>
```

---

#### Step 3: Migration Chain Verification

Run the full migration sequence on a fresh DB:
```bash
alembic downgrade base
alembic upgrade head
```

Verify table existence:
```bash
psql -c "\dt" | grep -E "sites|teams|session_narratives|session_annotations|drills|coaching|cert"
```

Expected tables: `sites`, `teams`, `session_narratives`, `session_annotations`, `drills`, `coaching_assignments`, `cert_standards`, `welder_certifications`.

---

#### Step 4: End-to-End Smoke Test

**Create** `my-app/src/__tests__/e2e/full-stack-smoke.test.ts`:
```typescript
/**
 * Full-stack smoke test: seed → score → narrative → trajectory →
 * benchmarks → coaching → certification → PDF
 *
 * Requires running backend + seeded data.
 * Run: npm test -- --testPathPattern="full-stack-smoke"
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WELDER_ID = "mike-chen";
const SESSION_ID = "sess_novice_001";

describe("Full stack smoke", () => {
  test("score endpoint returns total", async () => {
    const r = await fetch(`${BASE}/api/sessions/${SESSION_ID}/score`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(typeof d.total).toBe("number");
  });

  test("warp-risk endpoint returns risk_level", async () => {
    const r = await fetch(`${BASE}/api/sessions/${SESSION_ID}/warp-risk`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(["ok", "warning", "critical"]).toContain(d.risk_level);
  });

  test("trajectory returns points array", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/trajectory`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.points)).toBe(true);
  });

  test("benchmarks returns metrics array", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/benchmarks`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.metrics)).toBe(true);
  });

  test("coaching-plan returns assignments", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/coaching-plan`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.active_assignments)).toBe(true);
  });

  test("certification-status returns certifications", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/certification-status`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.certifications)).toBe(true);
    expect(d.certifications.length).toBe(3);
  });

  test("narrative POST + GET cycle", async () => {
    const post = await fetch(`${BASE}/api/sessions/${SESSION_ID}/narrative`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force_regenerate: false }),
    });
    expect(post.ok).toBe(true);
    const get = await fetch(`${BASE}/api/sessions/${SESSION_ID}/narrative`);
    expect(get.ok).toBe(true);
    const d = await get.json();
    expect(typeof d.narrative_text).toBe("string");
    expect(d.narrative_text.length).toBeGreaterThan(50);
  });

  test("defects endpoint returns array", async () => {
    const r = await fetch(`${BASE}/api/defects`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d)).toBe(true);
  });

  test("sites endpoint returns array", async () => {
    const r = await fetch(`${BASE}/api/sites`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d)).toBe(true);
  });
});
```

---

#### Step 5: WebGL Canvas Count Assertion

Verify ESLint rule still passes on replay page:
```bash
cd my-app && npx eslint src/app/replay/ --rule '{"max-torchviz/max-torchviz3d-per-page": "error"}'
```

---

#### Step 6: Update CONTEXT.md

**Modify** `context/CONTEXT.md` — update the "Implemented Features" section. Add these entries:

```markdown
### Warp Prediction ML
**Status:** ✅
**What:** ONNX-based logistic regression; 50-frame rolling window → warp probability + RiskLevel
**Location:** `backend/services/prediction_service.py`, `backend/routes/predictions.py`, `backend/models/warp_model.onnx`
**Frontend:** `WarpRiskGauge.tsx` — semicircle gauge on replay page
**Training:** `generate_training_data.py` + `train_warp_model.py`

### AI Narrative Engine
**Status:** ✅
**What:** Anthropic-powered 3-paragraph coaching report, cached in `session_narratives` table
**Location:** `backend/services/narrative_service.py`, `backend/routes/narratives.py`
**Frontend:** `NarrativePanel.tsx` — fetches internally, regenerate button
**PDF:** Optional narrative section in WelderReportPDF

### Longitudinal Skill Trajectory
**Status:** ✅
**What:** Per-welder chronological score history, trend slope, projected next score
**Location:** `backend/services/trajectory_service.py`; route in `welders.py`
**Frontend:** `TrajectoryChart.tsx` — multi-line Recharts; replaces hardcoded MOCK_HISTORICAL

### Defect Pattern Library
**Status:** ✅
**What:** Session-scoped annotations + cross-session defect library with deep-links to replay
**Location:** `backend/routes/annotations.py`, `backend/models/annotation.py`
**Frontend:** `AnnotationMarker.tsx`, `AddAnnotationPanel.tsx`, `/defects` page

### Comparative Benchmarking
**Status:** ✅
**What:** Per-metric percentile rankings vs all welders; supervisor Rankings tab
**Location:** `backend/services/benchmark_service.py`; route in `welders.py`
**Frontend:** `BenchmarkPanel.tsx`, `RankingsTable.tsx`

### Automated Coaching Protocol
**Status:** ✅
**What:** 12 seeded drills; auto-assignment based on benchmark; progress tracking
**Location:** `backend/services/coaching_service.py`; routes in `welders.py`
**Frontend:** `CoachingPlanPanel.tsx`
**Hook:** Auto-assign triggered in GET /score when total < 60

### Operator Credentialing
**Status:** ✅
**What:** 3 cert standards (AWS D1.1, ISO 9606, Internal Basic); session-based readiness evaluation
**Location:** `backend/services/cert_service.py`; route in `welders.py`
**Frontend:** `CertificationCard.tsx`; PDF extension

### Multi-Site Org Hierarchy
**Status:** ✅
**What:** sites + teams tables; nullable team_id on sessions; aggregate filter params
**Location:** `backend/routes/sites.py`, `backend/models/site.py`
**Frontend:** `SiteSelector.tsx` in supervisor page

### iPad Companion PWA
**Status:** ✅
**What:** `/live` page; polling warp-risk; 2D angle indicator; no WebGL; PWA manifest
**Location:** `app/(app)/live/page.tsx`, `LiveAngleIndicator.tsx`, `LiveStatusLED.tsx`
```

---

#### Batch 4 Agent 3 Verification Checklist
- [ ] `alembic downgrade base && alembic upgrade head` completes without error
- [ ] Full smoke test suite passes (9/9 tests green)
- [ ] ESLint WebGL canvas count passes
- [ ] `npm run build` passes
- [ ] Welder report page renders all 7 slots (narrative, heatmaps, feedback, trajectory, benchmarks, coaching, certification)
- [ ] `context/CONTEXT.md` updated with all new features
- [ ] Score endpoint triggers coaching auto-assign without error for novice welder

---

## SUMMARY: Dependency Graph

```
Batch 0 ─── Blocking Setup (ReportLayout, shared types, migration stubs, welders.py)
    │
    ├─── Batch 1A: Multi-Site Data Model (005 migration, Site/Team models)
    ├─── Batch 1B: Warp Prediction ML (ONNX, predictions route, WarpRiskGauge)
    └─── Batch 1C: AI Narrative Engine (006 migration, narrative service, NarrativePanel)
         │
         ├─── Batch 2A: Trajectory (trajectory service, TrajectoryChart, welders route)
         ├─── Batch 2B: Defect Library (007 migration, annotations route, defect page)
         └─── Batch 2C: Narrative Frontend (wire NarrativePanel, PDF extension)
              │
              ├─── Batch 3A: Benchmarking (benchmark service, BenchmarkPanel, Rankings)
              ├─── Batch 3B: Coaching (008 migration, coaching service, CoachingPlanPanel)
              └─── Batch 3C: Credentialing (009 migration, cert service, CertificationCard)
                   │
                   ├─── Batch 4A: Multi-Site UI (sites route, SiteSelector, aggregate filter)
                   ├─── Batch 4B: iPad PWA (live page, LiveStatusLED, LiveAngleIndicator)
                   └─── Batch 4C: Wire + Harden (auto-trigger, smoke tests, CONTEXT.md)
```

## FILE COLLISION SUMMARY (guaranteed safe by this plan)

| File | Sole Owner | Batch |
|------|-----------|-------|
| `shared_enums.py` | Batch 0 Agent 1 | 0 |
| `schemas/shared.py` | Batch 0 Agent 1 | 0 |
| `types/shared.ts` | Batch 0 Agent 1 | 0 |
| `ReportLayout.tsx` | Batch 0 Agent 1 | 0 |
| `routes/welders.py` | All agents append via PATCH — never overwrite full file | 2–3 |
| `lib/api.ts` | All agents append — never overwrite full file | 1–4 |

**welders.py and api.ts are the only shared files across agents. The rule is APPEND ONLY — each agent adds their section to the bottom. Never overwrite the full file. Instruct agents to use str_replace_editor targeting named function boundaries, not full-file rewrites.**