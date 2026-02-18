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