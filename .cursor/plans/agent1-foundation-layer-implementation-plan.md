# Agent 1 — Foundation Layer Implementation Plan (Refined)

---

## Overview

Backend has canonical enums and Pydantic schemas; frontend has shared types; Alembic chain 005→009 reserved; welders health endpoint live; ReportLayout with slot contract; welder page refactored to use it. Single source of truth for types; no circular imports; deterministic verification against rule_based.py.

---

## Prerequisites

- `backend/` is project root for Python
- `backend/scoring/rule_based.py` exists with rule_id strings (amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability)
- Pydantic installed
- Alembic configured; revision 004 is head (revision ID: `004_weld_thresholds_process_type`)
- `my-app/` has TypeScript; monorepo layout (backend and my-app in same repo)

---

## Phase Breakdown

## Phase 1 — Shared Backend Types & Schemas
Goal: Backend has canonical enums (`shared_enums.py`) and Pydantic schemas (`shared.py`) with no circular imports; models `__init__` exports all enums. WeldMetric derived from rule_based.py; verification is dynamic.
Risk: Medium
Estimate: 2h

## Phase 2 — Frontend Shared Types & Migration Stubs
Goal: TypeScript shared types exist; Alembic chain 005→009 reserved with empty stubs; welders health endpoint live. No 005–009 files exist before creating; FeedbackSeverity single source of truth.
Risk: Low
Estimate: 2h

## Phase 3 — ReportLayout & Page Refactor
Goal: ReportLayout component with slot contract exists; welder page uses it; error and loading branches preserved; visual output unchanged.
Risk: Medium
Estimate: 2h

---

## Steps

### Phase 1 — Shared Backend Types & Schemas

**Step 1.1 — Create shared_enums.py**

*What:* Create `backend/models/shared_enums.py` with the five enums. **WeldMetric values must be derived from rule_based.py** — do not hardcode. Use grep/parse of rule_based.py to extract rule_id strings and assert shared_enums matches.

*File:* `backend/models/shared_enums.py` (create)

*Depends on:* none

*Code:*
```python
"""Canonical enums for welding metrics, risk levels, and status types.

Used by schemas, routes, and future batches. Must NOT import from models or schemas.
Values must match rule_based.py rule_id strings exactly.
"""

from enum import Enum


class WeldMetric(str, Enum):
    """The 5 canonical metric names — must match rule_based.py rule_id strings."""
    AMPS_STABILITY = "amps_stability"
    ANGLE_CONSISTENCY = "angle_consistency"
    THERMAL_SYMMETRY = "thermal_symmetry"
    HEAT_DISS_CONSISTENCY = "heat_diss_consistency"
    VOLTS_STABILITY = "volts_stability"


class RiskLevel(str, Enum):
    """Backend risk level for scoring and thresholds."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class AnnotationType(str, Enum):
    """Type of session annotation."""
    DEFECT_CONFIRMED = "defect_confirmed"
    NEAR_MISS = "near_miss"
    TECHNIQUE_ERROR = "technique_error"
    EQUIPMENT_ISSUE = "equipment_issue"


class CoachingStatus(str, Enum):
    """Status of a coaching assignment."""
    ACTIVE = "active"
    COMPLETE = "complete"
    OVERDUE = "overdue"


class CertificationStatus(str, Enum):
    """Status of a certification track."""
    NOT_STARTED = "not_started"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    CERTIFIED = "certified"
```

*Verification (dynamic — derives from rule_based.py):*

Create `backend/scripts/verify_weld_metric_alignment.py`:

```python
"""Verify WeldMetric matches rule_based.py rule_id strings. Run as: PYTHONPATH=. python scripts/verify_weld_metric_alignment.py"""
import re
from pathlib import Path

rule_based_path = Path(__file__).parent.parent / "scoring" / "rule_based.py"
if not rule_based_path.exists():
    raise FileNotFoundError(f"rule_based.py not found at {rule_based_path}")

text = rule_based_path.read_text()
# Extract rule_id="..." from ScoreRule(rule_id="...", ...)
rule_ids = re.findall(r'rule_id\s*=\s*["\']([^"\']+)["\']', text)
rule_ids = [r for r in rule_ids if not r.startswith("_")]  # exclude any placeholder

from models.shared_enums import WeldMetric
expected = sorted(m.value for m in WeldMetric)
actual = sorted(set(rule_ids))

assert actual == expected, f"rule_based.py has {actual}; WeldMetric has {expected}. Align both."
assert len(expected) == 5
print("OK: WeldMetric matches rule_based.py")
```

Run:
```bash
cd backend
mkdir -p scripts
# Create verify_weld_metric_alignment.py as above
PYTHONPATH=. python scripts/verify_weld_metric_alignment.py
```

Pass criteria:
  [ ] No ImportError
  [ ] verify_weld_metric_alignment.py passes (WeldMetric derived from rule_based.py)
  [ ] WeldMetric.AMPS_STABILITY.value == "amps_stability"
If it fails: Check rule_based.py path; ensure backend is in PYTHONPATH; verify rule_based.py has exact rule_ids in ScoreRule(rule_id="...")

*Estimate:* 0.25h

---

**Step 1.2 — Create schemas/shared.py**

*What:* **Create directory first:** `mkdir -p backend/schemas`. Then create `backend/schemas/shared.py` with MetricScore, METRIC_LABELS, and `make_metric_score()`. `make_metric_score` must raise KeyError if metric is not in METRIC_LABELS. `_assert_all_metrics_have_labels()` runs at import.

*File:* `backend/schemas/shared.py` (create)

*Depends on:* Step 1.1

*Pre-step (automated, not manual):*
```bash
mkdir -p backend/schemas
```

*Code:*
```python
"""Shared Pydantic schemas for welding APIs.

Imports from models.shared_enums only. Must NOT create circular imports.
"""

from pydantic import BaseModel, Field

from models.shared_enums import WeldMetric


METRIC_LABELS: dict[WeldMetric, str] = {
    WeldMetric.AMPS_STABILITY: "Amps Stability",
    WeldMetric.ANGLE_CONSISTENCY: "Angle Consistency",
    WeldMetric.THERMAL_SYMMETRY: "Thermal Symmetry",
    WeldMetric.HEAT_DISS_CONSISTENCY: "Heat Dissipation Consistency",
    WeldMetric.VOLTS_STABILITY: "Volts Stability",
}


def _assert_all_metrics_have_labels() -> None:
    """Fail fast if a WeldMetric is missing from METRIC_LABELS."""
    for m in WeldMetric:
        if m not in METRIC_LABELS:
            raise KeyError(f"METRIC_LABELS missing entry for {m}")


_assert_all_metrics_have_labels()


class MetricScore(BaseModel):
    """Single metric score with value 0–100 and human-readable label."""
    metric: WeldMetric
    value: float = Field(..., ge=0.0, le=100.0, description="Score 0–100")
    label: str = Field(..., description="Human-readable metric name")


def make_metric_score(metric: WeldMetric, value: float) -> MetricScore:
    """Create a MetricScore with the canonical label. Raises KeyError if metric not in METRIC_LABELS."""
    label = METRIC_LABELS[metric]
    return MetricScore(metric=metric, value=value, label=label)
```

*Verification:*
```bash
cd backend
PYTHONPATH=. python -c "
from schemas.shared import MetricScore, METRIC_LABELS, make_metric_score
from models.shared_enums import WeldMetric

# All 5 metrics
ms = make_metric_score(WeldMetric.AMPS_STABILITY, 85.0)
assert ms.metric == WeldMetric.AMPS_STABILITY
assert ms.value == 85.0
assert ms.label == 'Amps Stability'

# Boundary values
make_metric_score(WeldMetric.VOLTS_STABILITY, 0.0)
make_metric_score(WeldMetric.ANGLE_CONSISTENCY, 100.0)

# Invalid value should raise
from pydantic import ValidationError
try:
    MetricScore(metric=WeldMetric.AMPS_STABILITY, value=-1, label='x')
except ValidationError:
    pass
else:
    raise AssertionError('Expected ValidationError for value=-1')
try:
    MetricScore(metric=WeldMetric.AMPS_STABILITY, value=101, label='x')
except ValidationError:
    pass
else:
    raise AssertionError('Expected ValidationError for value=101')

assert len(METRIC_LABELS) == 5
for m in WeldMetric:
    assert m in METRIC_LABELS
print('OK')
"
```
Pass criteria:
  [ ] No ImportError
  [ ] make_metric_score returns valid MetricScore
  [ ] MetricScore rejects value=-1 and value=101 (ValidationError)
  [ ] MetricScore accepts 0 and 100
  [ ] All 5 WeldMetric entries in METRIC_LABELS
If it fails: Ensure shared_enums has no imports from models or schemas; run `mkdir -p backend/schemas`

*Estimate:* 0.25h

---

**Step 1.3 — Export shared_enums from models/__init__.py**

*What:* Add imports and exports for all enums from shared_enums to `backend/models/__init__.py`.

*File:* `backend/models/__init__.py` (modify)

*Depends on:* Step 1.1

*Code:*
```python
# Add after existing from .scoring import ... and before __all__:
from .shared_enums import (
    AnnotationType,
    CertificationStatus,
    CoachingStatus,
    RiskLevel,
    WeldMetric,
)

# Add to __all__ list:
"AnnotationType", "CertificationStatus", "CoachingStatus", "RiskLevel", "WeldMetric",
```

*Verification:*
```bash
cd backend
PYTHONPATH=. python -c "
from models import WeldMetric, RiskLevel, AnnotationType, CoachingStatus, CertificationStatus
assert WeldMetric.AMPS_STABILITY.value == 'amps_stability'
print('OK')
"
```

*Estimate:* 0.15h

---

**Step 1.4 — Create schemas __init__.py**

*What:* Create `backend/schemas/__init__.py`. Directory must exist (Step 1.2 pre-step creates it).

*File:* `backend/schemas/__init__.py` (create)

*Depends on:* Step 1.2

*Code:*
```python
"""Schemas package for API request/response models."""
```

*Verification:*
```bash
cd backend
PYTHONPATH=. python -c "
from schemas.shared import MetricScore, make_metric_score
from models.shared_enums import WeldMetric
ms = make_metric_score(WeldMetric.THERMAL_SYMMETRY, 50.0)
assert ms.label == 'Thermal Symmetry'
print('OK')
"
```
Pass criteria:
  [ ] from schemas.shared works
  [ ] MetricScore and make_metric_score usable
If it fails: Ensure schemas/__init__.py exists; run `mkdir -p backend/schemas`

*Estimate:* 0.05h

---

### Phase 2 — Frontend Shared Types & Migration Stubs

**Step 2.1 — Create shared.ts**

*What:* Create `my-app/src/types/shared.ts`. **FeedbackSeverity: single source of truth** — import and re-export from `@/types/ai-feedback`; do not redefine. WeldMetric union must match backend.

*File:* `my-app/src/types/shared.ts` (create)

*Depends on:* none

*Code:*
```typescript
/**
 * Shared types for welding APIs.
 * FeedbackSeverity: re-export from ai-feedback (single source of truth).
 * WeldMetric union must match backend models.shared_enums.WeldMetric values.
 */

export type { FeedbackSeverity } from "@/types/ai-feedback";

export type WelderID = string;
export type SessionID = string;
export type SiteID = string;
export type TeamID = string;

export type WeldMetric =
  | "amps_stability"
  | "angle_consistency"
  | "thermal_symmetry"
  | "heat_diss_consistency"
  | "volts_stability";

export const METRIC_LABELS: Record<WeldMetric, string> = {
  amps_stability: "Amps Stability",
  angle_consistency: "Angle Consistency",
  thermal_symmetry: "Thermal Symmetry",
  heat_diss_consistency: "Heat Dissipation Consistency",
  volts_stability: "Volts Stability",
};

export type RiskLevel = "ok" | "warning" | "critical";

export interface MetricScore {
  metric: WeldMetric;
  value: number;
  label: string;
}

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

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}
```

*Why this approach:* FeedbackSeverity re-exported from ai-feedback.ts — no duplicate definition. Prevents drift.

*Verification:*
```bash
cd my-app
npm run build 2>&1 | tail -30
```
Pass criteria:
  [ ] shared.ts compiles
  [ ] METRIC_LABELS has all 5 keys
  [ ] FeedbackSeverity from ai-feedback (info | warning | critical)

*Estimate:* 0.5h

---

**Step 2.2 — Create migration stub 005_sites_teams.py**

*What:* Create empty migration stub. **Preconditions (both required):**

1. **004 is head:** `alembic current` shows `004_weld_thresholds_process_type` (or earlier). If another revision is head, resolve chain first.

2. **No 005–009 files exist:** Run `ls backend/alembic/versions/00[5-9]*.py 2>/dev/null | wc -l` — must output 0. If any exist, **ABORT.** They may be from a prior partial run. Manually inspect and remove or rename before proceeding.

**Documented revision IDs:**
- 004 filename: `004_weld_thresholds_and_process_type.py`
- 004 revision ID: `004_weld_thresholds_process_type` (use this in down_revision)
- 005 revision ID: `005_sites_teams`

*File:* `backend/alembic/versions/005_sites_teams.py` (create)

*Depends on:* none

*Pre-step:*
```bash
cd backend

# Abort if 005-009 already exist
COUNT=$(ls alembic/versions/00[5-9]*.py 2>/dev/null | wc -l)
if [ "$COUNT" -gt 0 ]; then
  echo "ABORT: 005-009 migration files already exist:"
  ls alembic/versions/00[5-9]*.py 2>/dev/null
  echo "Resolve before creating new stubs. Remove or rename if from prior partial run."
  exit 1
fi

# Verify 004 is current or earlier
alembic current
```

*Code:*
```python
"""Reserve migration for sites and teams tables. Owner: Batch 1 Agent 1."""

revision = "005_sites_teams"
down_revision = "004_weld_thresholds_process_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

*Verification:*
```bash
cd backend
alembic upgrade head
# Expected: Upgrades to 005_sites_teams
alembic downgrade -1
# Expected: Downgrades to 004 without error
alembic upgrade head
alembic history
# Expected: Linear 004→005 (no branches)
```
Pass criteria:
  [ ] Pre-step: 005-009 count is 0; alembic current shows 004 or earlier
  [ ] upgrade head succeeds
  [ ] downgrade -1 succeeds
  [ ] down_revision == "004_weld_thresholds_process_type"

*Estimate:* 0.2h

---

**Step 2.3 — Create migration stub 006_session_narratives.py**

*What:* Create `backend/alembic/versions/006_session_narratives.py` with down_revision="005_sites_teams".

*File:* `backend/alembic/versions/006_session_narratives.py` (create)

*Depends on:* Step 2.2

*Code:*
```python
"""Reserve migration for session narratives. Owner: Batch 1 Agent 3."""
revision = "006_session_narratives"
down_revision = "005_sites_teams"
branch_labels = None
depends_on = None
def upgrade() -> None: pass
def downgrade() -> None: pass
```

*Verification:* `alembic upgrade head` succeeds; `alembic downgrade -1` succeeds; current shows 006 after upgrade.

*Estimate:* 0.05h

---

**Step 2.4 — Create migration stub 007_session_annotations.py**

*What:* Create `backend/alembic/versions/007_session_annotations.py` with down_revision="006_session_narratives".

*File:* `backend/alembic/versions/007_session_annotations.py` (create)

*Depends on:* Step 2.3

*Code:*
```python
"""Reserve migration for session annotations. Owner: Batch 2 Agent 2."""
revision = "007_session_annotations"
down_revision = "006_session_narratives"
branch_labels = None
depends_on = None
def upgrade() -> None: pass
def downgrade() -> None: pass
```

*Verification:* `alembic upgrade head` succeeds; `alembic downgrade -1` succeeds.

*Estimate:* 0.05h

---

**Step 2.5 — Create migration stub 008_coaching_drills.py**

*What:* Create `backend/alembic/versions/008_coaching_drills.py` with down_revision="007_session_annotations".

*File:* `backend/alembic/versions/008_coaching_drills.py` (create)

*Depends on:* Step 2.4

*Code:*
```python
"""Reserve migration for coaching drills. Owner: Batch 3 Agent 2."""
revision = "008_coaching_drills"
down_revision = "007_session_annotations"
branch_labels = None
depends_on = None
def upgrade() -> None: pass
def downgrade() -> None: pass
```

*Verification:* `alembic upgrade head` succeeds; `alembic downgrade -1` succeeds.

*Estimate:* 0.05h

---

**Step 2.6 — Create migration stub 009_certifications.py**

*What:* Create `backend/alembic/versions/009_certifications.py` with down_revision="008_coaching_drills".

*File:* `backend/alembic/versions/009_certifications.py` (create)

*Depends on:* Step 2.5

*Code:*
```python
"""Reserve migration for certifications. Owner: Batch 3 Agent 3."""
revision = "009_certifications"
down_revision = "008_coaching_drills"
branch_labels = None
depends_on = None
def upgrade() -> None: pass
def downgrade() -> None: pass
```

*Verification:* `alembic upgrade head` succeeds; `alembic history` shows linear 004→005→006→007→008→009 with no branches.

*Estimate:* 0.05h

---

**Step 2.7 — Create welders router with health endpoint** — CRITICAL

*What:* Create `backend/routes/welders.py` with GET `/health` returning `{ "status": "ok", "router": "welders" }`. Register in `main.py` with prefix `/api/welders`. **Router route path is `/health` only** — prefix supplies `/api/welders`. Result: GET /api/welders/health.

**main.py structure:** If main.py was refactored, locate the route registration block (search for `include_router`) and add welders_router there. Typical placement: with other API routers (dashboard_router, aggregate_router, sessions_router, thresholds_router, dev_router).

*File:* `backend/routes/welders.py` (create), `backend/main.py` (modify)

*Depends on:* none

*Code:*
```python
# backend/routes/welders.py
"""Welders API routes. Health check only."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def welders_health():
    return {"status": "ok", "router": "welders"}
```

For `main.py` — add import (with other route imports) and include_router (before `@app.get("/health")`):

```python
# Import (add with others):
from routes.welders import router as welders_router

# Registration (add after dev_router, before @app.get("/health")):
app.include_router(welders_router, prefix="/api/welders")
```

*Verification:*
```bash
cd backend
PYTHONPATH=. pytest -q -k "welders_health or test_welders" 2>/dev/null || python -c "
from fastapi.testclient import TestClient
from main import app
c = TestClient(app)
r = c.get('/api/welders/health')
assert r.status_code == 200
assert r.json() == {'status': 'ok', 'router': 'welders'}
# Double prefix check: /api/api/welders/health must 404 (wrong registration)
r2 = c.get('/api/api/welders/health')
assert r2.status_code == 404
print('OK')
"
```

*Estimate:* 0.25h

---

**Step 2.8 — Add test for welders health endpoint**

*What:* Add pytest that (1) asserts GET /api/welders/health returns 200 and expected JSON, (2) asserts GET /api/api/welders/health returns 404 (no double prefix).

*File:* `backend/tests/test_welders_health.py` (create)

*Depends on:* Step 2.7

*Code:*
```python
"""Test welders router health endpoint."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_welders_health_returns_ok():
    """GET /api/welders/health returns status ok and router welders."""
    res = client.get("/api/welders/health")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ok"
    assert data.get("router") == "welders"


def test_welders_health_no_double_api_prefix():
    """GET /api/api/welders/health must 404 — ensures no wrong double prefix registration."""
    res = client.get("/api/api/welders/health")
    assert res.status_code == 404
```

*Verification:*
```bash
cd backend
PYTHONPATH=. pytest tests/test_welders_health.py -v
```

*Estimate:* 0.15h

---

### Phase 3 — ReportLayout & Page Refactor

**Step 3.1 — Create ReportLayout component**

*What:* Create `my-app/src/components/layout/ReportLayout.tsx`. **Pre-step:** `mkdir -p my-app/src/components/layout` if directory does not exist. Optional slots: narrative, heatmaps, feedback, trajectory, benchmarks, coaching, certification, actions. **NEVER modify slot contract after this step.**

*File:* `my-app/src/components/layout/ReportLayout.tsx` (create)

*Depends on:* none

*Pre-step:*
```bash
mkdir -p my-app/src/components/layout
```

*Code:*
```typescript
"use client";

import type { ReactNode } from "react";

/**
 * Slot-based layout for welder report pages.
 *
 * CONTRACT: Do NOT modify the slot props (narrative, heatmaps, feedback, etc.)
 * after creation. Future agents only drop content into slots.
 */

export interface ReportLayoutProps {
  narrative?: ReactNode;
  heatmaps?: ReactNode;
  feedback?: ReactNode;
  trajectory?: ReactNode;
  benchmarks?: ReactNode;
  coaching?: ReactNode;
  certification?: ReactNode;
  actions?: ReactNode;
}

export function ReportLayout({
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
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="grid grid-cols-1 gap-8">
        {narrative && <div data-slot="narrative">{narrative}</div>}
        {heatmaps && <div data-slot="heatmaps">{heatmaps}</div>}
        {feedback && <div data-slot="feedback">{feedback}</div>}
        {trajectory && <div data-slot="trajectory">{trajectory}</div>}
        {benchmarks && <div data-slot="benchmarks">{benchmarks}</div>}
        {coaching && <div data-slot="coaching">{coaching}</div>}
        {certification && <div data-slot="certification">{certification}</div>}
        {actions && <div data-slot="actions">{actions}</div>}
      </div>
    </div>
  );
}
```

*Verification:*
```bash
cd my-app
npm run build 2>&1 | tail -20
```

*Estimate:* 0.25h

---

**Step 3.2 — Refactor welder page to use ReportLayout** — CRITICAL

*What:* Modify `my-app/src/app/seagull/welder/[id]/page.tsx`. **CRITICAL: Preserve error and loading early-return branches.** Only replace the **success-path return** (the block after `if (loading || !report || !session)`). Do NOT remove or modify:
- `if (error)` block (lines ~214–230)
- `if (loading || !report || !session)` block (lines ~233–239)

The success-path return is the block that renders when data is loaded. Replace that block with ReportLayout and slot mapping. All variables (colorFn, heatmapData, expertHeatmapData, report, score, etc.) remain in scope — they are defined before any early return.

*Slot mapping:*
- **narrative:** Header card (h1, score, skill_level, trend, active_threshold_spec) + AI summary block (blue-50, "🤖 AI Analysis: {report.summary}")
- **heatmaps:** Thermal Comparison section (h2 "Thermal Comparison", HeatMap(s))
- **feedback:** Detailed Feedback section (h2 "Detailed Feedback", FeedbackPanel)
- **benchmarks:** Progress Over Time (h2, LineChart in #trend-chart)
- **actions:** Button group (Email Report, Download PDF, pdfError)
- **trajectory, coaching, certification:** undefined

Back link stays **outside** ReportLayout.

*File:* `my-app/src/app/seagull/welder/[id]/page.tsx` (modify)

*Depends on:* Step 3.1

*Code (success-path return only — insert after the loading/error early returns):*

```tsx
// Add import at top:
import { ReportLayout } from "@/components/layout/ReportLayout";

// REPLACE ONLY the success return block. KEEP the error and loading returns unchanged.
// Success return starts after: if (loading || !report || !session) { return ... }

return (
  <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
    <div className="mb-4">
      <Link href="/seagull" className="text-blue-600 dark:text-blue-400 hover:underline text-sm">
        ← Back to Team Dashboard
      </Link>
    </div>
    <ReportLayout
      narrative={
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold">{displayName} — Weekly Report</h1>
            <div className="text-right">
              <div className="text-5xl font-bold text-blue-600">{report.score}/100</div>
              <div className="text-sm text-zinc-600 dark:text-zinc-400">{report.skill_level} • {report.trend}</div>
              {score?.active_threshold_spec && (
                <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                  Evaluated against {score.active_threshold_spec.weld_type.toUpperCase()} spec — Target {score.active_threshold_spec.angle_target}° ±{score.active_threshold_spec.angle_warning}°
                </div>
              )}
            </div>
          </div>
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 border-l-4 border-blue-500 rounded">
            <p className="text-sm font-medium">🤖 AI Analysis: {report.summary}</p>
          </div>
        </div>
      }
      heatmaps={
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Thermal Comparison</h2>
          {expertSession ? (
            <div className="grid grid-cols-2 gap-8">
              <div>
                <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">Expert Benchmark</h3>
                <HeatMap sessionId="expert" data={expertHeatmapData} colorFn={colorFn} label="Expert" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">Your Weld</h3>
                <HeatMap sessionId={sessionId} data={heatmapData} colorFn={colorFn} label={displayName} />
              </div>
            </div>
          ) : (
            <div>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">Expert comparison unavailable — run seed to add sess_expert-benchmark_005.</p>
              <HeatMap sessionId={sessionId} data={heatmapData} colorFn={colorFn} label={displayName} />
            </div>
          )}
        </div>
      }
      feedback={
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Detailed Feedback</h2>
          <FeedbackPanel items={report.feedback_items} />
        </div>
      }
      benchmarks={
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Progress Over Time</h2>
          <div id="trend-chart" style={{ width: 600, height: 200 }} data-testid="trend-chart">
            <LineChart data={chartData ?? []} color="#3b82f6" height={200} />
          </div>
        </div>
      }
      actions={
        <div className="flex flex-col gap-4">
          <div className="flex gap-4">
            <button className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed" disabled title="Email report — coming soon">
              📧 Email Report (coming soon)
            </button>
            <button className="bg-zinc-200 text-zinc-800 px-6 py-3 rounded-lg font-semibold hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed" onClick={handleDownloadPDF} disabled={loading || pdfLoading}>
              {pdfLoading ? "⏳ Generating..." : "📄 Download PDF"}
            </button>
          </div>
          {pdfError && <p className="text-red-600 dark:text-red-400 text-sm">{pdfError}</p>}
        </div>
      }
    />
  </div>
);
```

*Verification:*
```bash
cd my-app
npm run build
npm run test -- --testPathPattern="seagull/welder" --run
```

Add to `page.test.tsx` — slot contract and slot-content correctness (prevent swap):

```typescript
// In "renders report with score..." test, after existing assertions:
const heatmapsSlot = document.querySelector('[data-slot="heatmaps"]');
expect(heatmapsSlot).toBeInTheDocument();
expect(heatmapsSlot).toHaveTextContent(/Thermal Comparison/);
expect(heatmapsSlot).not.toHaveTextContent(/Detailed Feedback/);

const feedbackSlot = document.querySelector('[data-slot="feedback"]');
expect(feedbackSlot).toBeInTheDocument();
expect(feedbackSlot).toHaveTextContent(/Detailed Feedback/);
expect(feedbackSlot).not.toHaveTextContent(/Thermal Comparison/);

const narrativeSlot = document.querySelector('[data-slot="narrative"]');
expect(narrativeSlot).toBeInTheDocument();
expect(narrativeSlot).toHaveTextContent(/AI Analysis/);
expect(narrativeSlot).toHaveTextContent(/Weekly Report/);
```

Add test for error state:
```typescript
it("renders error state with back link when fetch fails", async () => {
  mockFetchSession.mockRejectedValueOnce(new Error("Network error"));
  mockFetchScore.mockRejectedValueOnce(new Error("Network error"));
  render(<WelderReportPage params={{ id: "mike-chen" }} />);
  await waitFor(() => {
    expect(screen.getByText(/⚠️ Error/)).toBeInTheDocument();
  });
  expect(screen.getByRole("link", { name: /Back to Team Dashboard/ })).toHaveAttribute("href", "/seagull");
});
```

Pass criteria:
  [ ] Build passes
  [ ] Tests pass
  [ ] Error and loading branches preserved
  [ ] Slot content correctness (no swap)
  [ ] Error state test passes

*Estimate:* 0.5h

---

## Risk Heatmap

| Phase.Step | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| 1.1 | Circular import | Med | High | Keep shared_enums dependency-free |
| 1.2 | schemas import cycle | Med | High | schemas imports only models.shared_enums |
| 2.2 | 005-009 already exist; overwrite | High | High | Pre-step: abort if files exist |
| 2.2 | Wrong down_revision | Low | High | Exact "004_weld_thresholds_process_type"; verify downgrade -1 |
| 2.3–2.6 | Migration branch | Low | High | Verify linear chain |
| 2.7 | Double /api prefix | Low | Med | prefix="/api/welders"; route="/health"; test asserts /api/api/ 404 |
| 3.2 | Error/loading branches removed | Med | High | Explicit: preserve both; add error-state test |
| 3.2 | Slot swap | Med | Med | Assert slot has correct content and NOT wrong content |
| 3.1 | Slot contract modified | Med | High | Document "NEVER modify" |

---

## Pre-Flight Checklist

```
Phase 1:
[ ] backend/ is Python root — cd backend && python -c "import models"
[ ] rule_based.py exists — grep rule_id backend/scoring/rule_based.py
[ ] mkdir -p backend/schemas

Phase 2:
[ ] shared_enums.py and schemas/shared.py exist
[ ] alembic current shows 004 or earlier
[ ] ls backend/alembic/versions/00[5-9]*.py 2>/dev/null | wc -l == 0
[ ] 004 revision ID: grep revision backend/alembic/versions/004*.py → 004_weld_thresholds_process_type

Phase 3:
[ ] shared.ts exists — test -f my-app/src/types/shared.ts
[ ] Welder health: Preferred — curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/welders/health (expect 200)
      Fallback (CI/headless): cd backend && PYTHONPATH=. pytest tests/test_welders_health.py -q
      Note: pytest loads app in-process; does not verify live server. For E2E, start server and curl.
[ ] test -f my-app/src/components/layout/ReportLayout.tsx
[ ] test -f my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx
```

---

## Backend/Frontend Type Alignment (CI)

Add `backend/tests/test_metric_labels_alignment.py` and run as part of test suite:

```python
"""Assert backend METRIC_LABELS and WeldMetric align with frontend shared.ts. Run in pytest."""
import ast
from pathlib import Path

from models.shared_enums import WeldMetric
from schemas.shared import METRIC_LABELS

backend_values = sorted(m.value for m in WeldMetric)
assert backend_values == sorted(k.value for k in METRIC_LABELS.keys())

frontend_path = Path(__file__).parent.parent.parent / "my-app" / "src" / "types" / "shared.ts"
assert frontend_path.exists(), f"Frontend shared.ts not found at {frontend_path}"
text = frontend_path.read_text()

# Each WeldMetric value must appear as a string literal in the WeldMetric union
for v in backend_values:
    assert f'"{v}"' in text or f"'{v}'" in text, f"Frontend shared.ts missing WeldMetric value {v}"
```

Add to Phase 1 success: `pytest backend/tests/test_metric_labels_alignment.py` passes.

---

## Success Criteria

| # | Condition | Verification |
|---|-----------|--------------|
| 1 | GET /api/welders/health returns { status: "ok", router: "welders" } | curl or TestClient 200 |
| 2 | No circular import | pytest backend/tests/ -x |
| 3 | shared.ts compiles | npm run build |
| 4 | Welder page: same sections, slots correct, error/loading preserved | page.test.tsx + slot asserts + error-state test |
| 5 | 005 exists, down_revision correct | grep down_revision 005*.py |
| 6 | 006–009 linear chain | alembic history |
| 7 | ReportLayout 8 slots | Check ReportLayoutProps |
| 8 | test_metric_labels_alignment passes | pytest |
| 9 | FeedbackSeverity single source (ai-feedback) | shared.ts re-exports, no redefine |
| 10 | MetricScore boundary 0,100 valid; -1,101 invalid | Step 1.2 verification |

---

## Phase 2 → Phase 3 Handoff

```bash
cd backend && alembic history
# Expected: 004 → 005 → 006 → 007 → 008 → 009 linear
```

---

## Rollback Procedure

**Phase 1:** Delete shared_enums.py, schemas/; revert models/__init__.py. Delete scripts/verify_weld_metric_alignment.py.

**Phase 2:** Before downgrading, run `alembic current` to note revision. Delete 005–009; revert main.py; delete routes/welders.py, tests/test_welders_health.py. Run `alembic downgrade 004_weld_thresholds_process_type`. Verify: `alembic current` shows 004.

**Phase 3:** Revert welder page; delete ReportLayout.tsx; revert page.test.tsx.

---

## Known Issues & Limitations

1. **WeldMetric hand-maintained:** Backend enum and frontend union are not code-generated. Run test_metric_labels_alignment on changes.
2. **Phase 3 pre-flight:** curl assumes server on localhost:8000. Pytest fallback validates in-process app only, not live server.
3. **main.py structure:** Plan assumes include_router block exists. If main.py refactored, add welders_router to equivalent location.
4. **Jest testPathPattern:** Plan uses `--testPathPattern="seagull/welder"`. If jest.config.js uses different patterns, adjust to match page.test.tsx path.
5. **004 filename vs revision:** Filename is `004_weld_thresholds_and_process_type.py`; revision ID is `004_weld_thresholds_process_type` (no "and").

---

## Progress Tracker

```
| Phase | Steps | Done | In Progress | Blocked | % |
|-------|-------|------|-------------|---------|---|
| Phase 1 | 4 | 0 | 0 | 0 | 0% |
| Phase 2 | 8 | 0 | 0 | 0 | 0% |
| Phase 3 | 2 | 0 | 0 | 0 | 0% |
| TOTAL | 14 | 0 | 0 | 0 | 0% |
```
