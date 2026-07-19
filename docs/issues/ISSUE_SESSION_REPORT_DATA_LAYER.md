# Issue: Session 4 — Report Data Layer + Compliance UI

**Type:** Feature  
**Priority:** Normal  
**Effort:** Large (split into 4A + 4B)  
**Labels:** `backend` `frontend` `report` `compliance` `data-layer`

---

## TL;DR

The session report needs heat input aggregates, excursion counts, arc termination quality, and defect timestamps — none of which exist at session level today. Session 4 must be split: **4A** builds a dedicated `GET /api/sessions/{session_id}/report-summary` endpoint (isolated aggregator, no scoring changes); **4B** builds the compliance UI and PDF extension. Building UI before the data layer produces placeholder-only components.

---

## Critical Scope Problem

The original constraint "do not touch scoring logic" hides a blocker: **every meaningful compliance data point is uncomputed or unwired**.

| Data point | Current state |
|------------|---------------|
| Heat input min/max/mean | `Frame.heat_input_kj_per_mm` exists per-frame; never aggregated |
| Excursion count | Not computed |
| Arc termination quality | `Frame.arc_termination_type` exists per-frame; never aggregated |
| Defect timestamps | `GET /api/sessions/{id}/alerts` exists but not wired to report |

**SessionScore** produces `total` + `rules` (amps_stddev, angle_max_deviation, etc.) — not compliance aggregates. **extract_features** has different outputs (volts_range, porosity_event_count) and callers; extending it risks regression.

**Recommended split:** 4A (backend only) → 4B (frontend only). Run them as separate Cursor sessions to avoid context drift and placeholder invention.

---

## Current State vs Expected Outcome

### Current State

- **Welder report page:** `/seagull/welder/[id]` — score, feedback, heatmaps, trajectory, PDF download
- **PDF:** `@react-pdf/renderer` + `WelderReportPDF` + `POST /api/welder-report-pdf` — renders welder, score, feedback, narrative, certifications
- **Scoring:** `SessionScore` = `{ total, rules }`; `extract_features` = amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range, travel_speed_stddev, cyclogram_area, porosity_event_count
- **Alerts:** `GET /api/sessions/{id}/alerts` returns `{ alerts: AlertPayload[] }` with `timestamp_ms`, `rule_triggered`, etc. — not used by report
- **Frame:** Has `heat_input_kj_per_mm`, `arc_termination_type`, `travel_angle_degrees` — session-level aggregates do not exist

### Expected Outcome

- **4A:** `GET /api/sessions/{session_id}/report-summary` returns `ReportSummary` — heat input compliance, travel angle excursions, arc termination quality, defect counts, excursion log — all from frames + alerts
- **4B:** Report page shows `ComplianceSummaryPanel` + `ExcursionLogTable`; PDF extends with compliance section; both consume `report-summary` endpoint

---

## ReportSummary Schema (Define Before Code)

```python
from datetime import datetime
from typing import Dict, List, Literal, Optional

class ExcursionEntry(BaseModel):
    timestamp_ms: int
    defect_type: str
    parameter_value: float
    threshold_value: float
    duration_ms: Optional[int] = None
    source: Literal["alert", "frame_derived"]

class ReportSummary(BaseModel):
    session_id: str
    generated_at: datetime

    # Heat input compliance
    heat_input_min_kj_per_mm: Optional[float] = None
    heat_input_max_kj_per_mm: Optional[float] = None
    heat_input_mean_kj_per_mm: Optional[float] = None
    heat_input_wps_min: float = 0.5  # WPS range lower bound
    heat_input_wps_max: float = 0.9   # WPS range upper bound
    heat_input_compliant: bool = False

    # Torch angle
    travel_angle_excursion_count: int = 0
    travel_angle_worst_case_deg: Optional[float] = None
    travel_angle_threshold_deg: float = 25.0  # AWS D1.2 nominal

    # Arc termination
    total_arc_terminations: int = 0
    no_crater_fill_count: int = 0
    crater_fill_rate_pct: float = 0.0

    # Defect summary (from alerts)
    defect_counts_by_type: Dict[str, int] = {}
    total_defect_alerts: int = 0

    # Excursion log (merged from frames + alerts)
    excursions: List[ExcursionEntry] = []
```

---

## WPS Threshold Decision (Blocking)

The plan uses **hardcoded** values: `heat_input_wps_min = 0.5`, `heat_input_wps_max = 0.9`, `travel_angle_threshold_deg = 25.0`. A QA manager will ask "whose WPS is this?"

**Options:**
1. **MVP:** Hardcode with config file (e.g. `report_thresholds.json`) — document constants, single source
2. **Later:** Per-session WPS reference (stored with session, passed by welder's WPS document)

**Decide before 4A starts.** Even a config file is better than magic numbers in compliance logic.

---

## Session 4A — Report Data Layer (Backend)

**Scope:** Backend only. No scoring, extract_features, or frontend changes.

### Step 1: `report_summary` aggregator

- New file: `backend/scoring/report_summary.py`
- Function: `compute_report_summary(session_id: str, frames: List[Frame], alerts: List[AlertPayload]) -> ReportSummary`
- Aggregates: heat_input from frames, travel_angle excursions from frames, arc_termination_type counts, merges alerts into ExcursionEntry list
- Verification: unit test with known frame list; assert all fields populated

### Step 2: Wire to API route

- New route: `GET /api/sessions/{session_id}/report-summary`
- Loads frames from session; calls AlertEngine/get_session_alerts internally; calls `compute_report_summary`
- Returns `ReportSummary` JSON
- Verification: `curl` returns valid JSON with all fields

### Step 3: Verify against mock

- Expert session: `crater_fill_rate_pct == 100`, `heat_input_compliant == True`
- Novice session: `no_crater_fill_count > 0`, `travel_angle_excursion_count > 0`, `heat_input_compliant == False`
- **Done-when gate:** Passes before touching UI

---

## Session 4B — Report UI + PDF Extension

**Scope:** Frontend only. Assumes 4A endpoint exists and returns valid data.

### Step 4: Frontend data hook

- `useReportSummary(sessionId)` — fetches report-summary
- TypeScript type mirrors `ReportSummary`
- No UI yet — data layer only

### Step 5: Compliance summary panel

- `ComplianceSummaryPanel` — Heat Input, Torch Angle, Arc Termination rows
- Each: label, actual value, WPS threshold, pass/fail badge
- Add below score display on `/seagull/welder/[id]`

### Step 6: Excursion log table

- `ExcursionLogTable` — Time, Type, Value, Threshold, Duration
- Client-side sort; empty state: "No excursions — session within compliance"

### Step 7: PDF extension

- Extend `WelderReportPDF` with compliance + excursion section
- Add `reportSummary` to PDF POST payload; page includes it in download request

---

## Relevant Files

| File | Action |
|------|--------|
| `backend/scoring/report_summary.py` | **New** — ReportSummary schema, compute_report_summary |
| `backend/routes/sessions.py` | Add GET /sessions/{id}/report-summary |
| `backend/tests/test_report_summary.py` | **New** — unit tests for aggregator |
| `my-app/src/hooks/useReportSummary.ts` | **New** — data hook |
| `my-app/src/components/welding/ComplianceSummaryPanel.tsx` | **New** |
| `my-app/src/components/welding/ExcursionLogTable.tsx` | **New** |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Add ComplianceSummaryPanel, ExcursionLogTable; include reportSummary in PDF POST |
| `my-app/src/components/pdf/WelderReportPDF.tsx` | Extend with compliance section |
| `my-app/src/app/api/welder-report-pdf/route.ts` | Accept and pass reportSummary |

---

## Cursor Prompts

### Session 4A

```
I need to build a report data layer only. Do not touch alerts logic, scoring logic, extract_features, or any frontend.

Here is the ReportSummary schema I need [paste schema above].

The data sources are:
- Frame list from session (each Frame has heat_input_kj_per_mm, arc_termination_type, travel_angle_degrees)
- Alert list from get_session_alerts (or AlertEngine run over session frames)

Audit the current session and frame models before writing any code. Build compute_report_summary first, unit test it with a known frame list, then wire to the API route.
```

### Session 4B

```
I need to build the report UI only. Do not touch backend, scoring, or alerts logic.

The endpoint GET /api/sessions/{session_id}/report-summary already exists and returns ReportSummary.
TypeScript types: ExcursionEntry { timestamp_ms, defect_type, parameter_value, threshold_value, duration_ms?, source }
ReportSummary: session_id, generated_at, heat_input_*, travel_angle_*, total_arc_terminations, crater_fill_rate_pct, defect_counts_by_type, total_defect_alerts, excursions[]

The existing page is /seagull/welder/[id]. The existing PDF component is WelderReportPDF.

Build the data hook first. Then ComplianceSummaryPanel. Then ExcursionLogTable. Then extend the PDF last. Design each component layout before writing code.
```

---

## Dependencies

- **Session 1 (Mock Data Foundation):** Expert has `crater_fill_present`, novice has `no_crater_fill`, heat_input in range; negative travel_angle for novice. Without it, 4A verification against novice/expert may not distinguish.
- **Session 2 (Defect Alert Rules):** Alerts API returns defect rules; defect_counts_by_type populated from rule_triggered.
- Both should be complete for full "done when" verification. 4A can still deliver with partial alerts (empty defect_counts if rules not implemented).

---

## Risk / Notes

- **Isolation:** 4A does not extend SessionScore or extract_features. New endpoint, new schema, minimal regression surface.
- **Travel angle excursion:** Threshold 25° per AWS D1.2; use `travel_angle_degrees` from Frame. Nominal push is ~12°; excursion = |angle − nominal| > threshold. Confirm nominal from session metadata or hardcode 12° for MVP.
- **ExcursionEntry.source:** `alert` = from AlertPayload; `frame_derived` = from frame scan (e.g. heat_input outside WPS range). Merging requires consistent timestamp_ms.

---

## Vision Alignment

From `vision.md`: *"Something they can forward — a PDF report, a link, a screenshot that travels on its own"* and *"Feedback that is actionable ('angle too steep at timestamp 00:47') not abstract."* The compliance report and excursion log make defect data auditable and forwardable — exactly what investors and QA need.
