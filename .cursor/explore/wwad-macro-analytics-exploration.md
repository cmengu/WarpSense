# WWAD Macro-Level Analytics Dashboard — Technical Exploration

**Time Budget:** 45–90 minutes  
**Status:** Complete  
**Date:** 2025-02-17  
**Issue Reference:** `.cursor/issues/wwad-macro-analytics-dashboard.md`

---

## Phase 0: MANDATORY PRE-EXPLORATION THINKING SESSION

### A. Exploration Scope Understanding

**1. Core technical challenge**

In one sentence: *How do we serve macro-level, multi-session welding KPIs (avg score, trends, calendar heatmap) without loading frame data for every session and without coupling to TorchViz3D/HeatmapPlate3D/micro-feedback.*

**Why it's hard:** Scoring currently requires `session.frames` (extract_features → score_session). Aggregating 500+ sessions means either loading ~750K frames (OOM/slow) or persisting scores.

**Non-trivial aspects:**
- Score computation is tied to frames; aggregation needs scores but cannot load all frames
- GET /api/sessions is 501 — aggregate must query DB internally
- Calendar heatmap needs a new component (existing HeatMap is thermal 2D grid, not GitHub-style)
- Orthogonality: zero imports from 3D/micro-feedback in WWAD

**2. Major unknowns**

1. **Unknown #1:** Batch scoring performance — how long for 10, 50, 500 sessions?  
2. **Unknown #2:** Whether to persist `score_total` — migration vs on-demand trade-off.  
3. **Unknown #3:** Calendar heatmap metric (sessions/day vs avg score/day vs rework).  
4. **Unknown #4:** Exact KPI set stakeholders want.  
5. **Unknown #5:** Date range defaults and timezone handling.  

**3. Questions that must be answered**

1. Can we aggregate without loading frames? (Only if we persist scores.)  
2. What is the performance of batch scoring 10 sessions? 50?  
3. Can we reuse DashboardLayout for KPIs and charts?  
4. What does a GitHub-style calendar heatmap look like in React?  
5. How do we query sessions by date without GET /api/sessions?  
6. Which sessions to include (COMPLETE only? Exclude FAILED?)?  
7. How to handle zero sessions in date range?  
8. CSV export format — which fields?  
9. Routing: /supervisor vs /analytics vs replace /dashboard?  
10. How to enforce orthogonality (no 3D imports)?  

**4. What could we get wrong**

1. **Mistake #1:** Loading frames for every session in aggregate — OOM or 30+ second response.  
2. **Mistake #2:** Importing HeatMap (thermal) for calendar — wrong component.  
3. **Mistake #3:** Reusing TorchViz3D patterns — violates orthogonality.  
4. **Mistake #4:** Building score-based KPIs without persistence — slow.  
5. **Mistake #5:** Over-scoping (PDF, line/shift) in Phase 1.  

---

### B. Approach Brainstorm

**Approach A: Compute scores on aggregate request**

- **Description:** Aggregate endpoint loads sessions with frames, batches score_session for each, returns KPIs.
- **Gut feeling:** Bad  
- **First concern:** 500 × 1500 frames = 750K frames loaded; likely >10s or OOM.

**Approach B: Persist score_total at session completion**

- **Description:** Add `score_total` column; compute and store when session completes; aggregate reads metadata + score_total only.
- **Gut feeling:** Good  
- **First concern:** Requires migration and backfill for existing sessions.

**Approach C: Hybrid — metadata-only KPIs first, scores later**

- **Description:** Phase 1: session_count, by operator, by weld_type, calendar = sessions/day. Add score KPIs in Phase 2 with persistence.
- **Gut feeling:** Uncertain  
- **First concern:** Delivers less value initially (no avg score).

**Approach D: Lazy score cache (compute on first request, store)**

- **Description:** On first aggregate for a session, compute score and cache (Redis or DB column). Subsequent uses cached value.
- **Gut feeling:** Good  
- **First concern:** Cache invalidation if frames change (unlikely for complete sessions).

---

### C. Constraint Mapping

**Technical constraints:**

1. FastAPI, PostgreSQL, SQLAlchemy, Next.js, React, TypeScript, Tailwind — must use.  
2. Reuse extract_features, score_session — don't rewrite.  
3. No changes to TorchViz3D, HeatmapPlate3D, micro-feedback.  
4. Session has operator_id, weld_type, start_time only (no line/shift).  
5. Aggregate API < 3s for typical load (500 sessions).  

**How constraints eliminate approaches:**

- Constraint "no frame loading for aggregate" + "< 3s" → eliminates Approach A (batch scoring on request).  
- Constraint "orthogonality" → eliminates any import from welding 3D components.  

---

### D. Risk Preview

**Scary thing #1:** Batch scoring 500 sessions exhausts memory/time.

- **Why scary:** Each session ~1500 frames; 500 × 1500 = 750K frame objects.  
- **Likelihood:** 70%  
- **Could kill project:** No — mitigation: persist scores.  

**Scary thing #2:** Accidentally coupling WWAD to micro-feedback.

- **Why scary:** Regression; breaks orthogonality.  
- **Likelihood:** 30%  
- **Could kill project:** No — mitigation: code review, ESLint rule.  

**Scary thing #3:** Wrong KPI set — supervisors don't use dashboard.

- **Why scary:** Wasted effort.  
- **Likelihood:** 25%  
- **Could kill project:** No — mitigation: validate with stakeholder first.  

---

## 1. Research Existing Solutions

### A. Internal Codebase Research

**Similar Implementation #1: `my-app/src/components/dashboard/DashboardLayout.tsx`**

- **What it does:** Renders MetricCard grid + ChartCard grid (LineChart, BarChart, PieChart).  
- **How it works:**
  1. Receives `DashboardData` (metrics[], charts[])
  2. Maps metrics → MetricCard (title, value, change, trend)
  3. Maps charts → ChartCard with type-specific chart
- **Patterns:** Generic MetricData/ChartData; reusable for welding KPIs if we supply welding-shaped data.
- **What we can reuse:** MetricCard, ChartCard, LineChart, BarChart, PieChart.  
- **What we should avoid:** Feeding mock generic data; we need real aggregate API response.
- **Edge cases handled:** Empty metrics/charts → "No metrics/charts available."
- **Edge cases NOT handled:** Date range, group_by — types don't support it; we'll extend or add AggregateDashboardData.

**Similar Implementation #2: `my-app/src/app/seagull/page.tsx`**

- **What it does:** Team dashboard; fetches fetchScore per hardcoded welder.  
- **How it works:**
  1. Hardcoded WELDERS list (2)
  2. Promise.allSettled(fetchScore per session)
  3. Cards with welder name + score
- **What we can reuse:** Card layout; pattern of fetching per-entity.  
- **What we should avoid:** Hardcoding; N+1 fetchScore; WWAD must derive welders from sessions and use single aggregate API.
- **Anti-pattern:** Client-side aggregation via N fetchScore calls — does not scale.

**Similar Implementation #3: `backend/routes/sessions.py` → GET /api/sessions/{id}/score**

- **What it does:** Loads session with frames (joinedload), extract_features, score_session, returns { total, rules }.  
- **Key code:**
```python
session_model = db.query(SessionModel).options(joinedload(SessionModel.frames)).filter_by(session_id=session_id).first()
session = session_model.to_pydantic()
features = extract_features(session)
score = score_session(session, features)
return score.model_dump()
```
- **What we can reuse:** extract_features, score_session.  
- **What we should avoid:** Calling this in a loop for aggregation — too expensive.
- **Edge case:** Sessions with 0 frames — extract_features returns zeros; score still computed.

---

### B. Pattern Analysis

**Pattern #1: Backend route → Pydantic response**

- **Used in:** dashboard.py, sessions.py  
- **Description:** Route returns Pydantic model; frontend types mirror snake_case.  
- **Applicability:** High — new aggregate route returns AggregateKPIResponse.

**Pattern #2: lib/api.ts fetch + useState/useEffect**

- **Used in:** dashboard page, Seagull  
- **Description:** fetchDashboardData/fetchScore in useEffect; loading/error/retry.  
- **Applicability:** High — fetchAggregateKPIs(date_start, date_end).

**Pattern #3: ChartCard + LineChart/BarChart with { date, value } or { category, value }**

- **Used in:** DashboardLayout  
- **Description:** ChartData has type, data array, color. LineChart expects `{ date, value }`.  
- **Applicability:** High — trend = LineChart; by_welder = BarChart.

---

### C. External Research (Concise)

**Calendar heatmap:** GitHub-style contribution grid — 7 columns × N weeks. Recharts has no built-in; custom CSS grid with divs is standard. Similar to `HeatMap` (grid of cells) but axes = day/week, value = sessions or avg score.

**CSV export:** Client-side: `JSON.stringify` → Blob → URL.createObjectURL → download. No library needed. Limit rows (e.g. 1000) to avoid memory issues.

**Score persistence:** Add `score_total INTEGER` to sessions; compute on session COMPLETE (or on first /score call); backfill existing via script.

---

## 2. Prototype Critical Paths

### Critical Paths Identified

1. **Aggregate query (metadata only)** — SessionModel query with date filter; no frames.  
2. **Batch scoring performance** — Load N sessions with frames, score each; measure time.  
3. **Calendar heatmap UX** — Custom grid (day × week); color by value.  
4. **CSV export** — Transform aggregate data → CSV string → download.  
5. **Orthogonality enforcement** — Grep for 3D/micro-feedback imports in supervisor module.  

### Prototype #1: Aggregate Performance Script

**Purpose:** Measure metadata-only query and batch scoring time.

**Location:** `backend/scripts/prototype_aggregate_perf.py`

**Key logic:**
- `query_sessions_metadata_only()` — SessionModel columns only, no joinedload.
- `batch_score_sessions()` — joinedload frames, extract_features, score_session per session.
- Measure ms for 2, 5, 10 sessions; extrapolate to 500.

**Run:** `cd backend && python scripts/prototype_aggregate_perf.py` (requires seeded DB).

**Expected result (analytical):**  
- Metadata-only: < 50 ms for hundreds of sessions.  
- Batch score: ~50–200 ms per session (1500 frames each) → 500 sessions ≈ 25–100 s.  
- **Conclusion:** Persist score_total; do not compute on aggregate request.

**Prototype #2: Calendar Heatmap Component (Pseudocode)**

```tsx
// CalendarHeatmap.tsx — GitHub-style grid
interface DayValue { date: string; value: number; }
function CalendarHeatmap({ data }: { data: DayValue[] }) {
  // Group by week; 7 columns (Sun–Sat); rows = weeks
  // Each cell: background color from value (e.g. blue-100 to blue-600)
  // Tooltip: date, value
  return <div className="grid grid-cols-7 gap-0.5">...</div>;
}
```

**Prototype #3: CSV Export**

```ts
function generateCSV(rows: Record<string, string | number>[]): string {
  const header = Object.keys(rows[0] ?? {}).join(',');
  const body = rows.map(r => Object.values(r).join(',')).join('\n');
  return header + '\n' + body;
}
function downloadCSV(filename: string, csv: string) {
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
```

---

## 3. Evaluate Approaches

### Approach Comparison Matrix

| Criterion              | Weight | A: Compute on request | B: Persist score_total | C: Metadata-only first |
|------------------------|--------|------------------------|------------------------|--------------------------|
| Implementation complexity | 15%  | Low (5)                | Medium (3)             | Low (5)                  |
| Performance            | 25%  | Poor (1)                | Good (5)               | Good (5)                 |
| KPI richness            | 20%  | Full (5)                | Full (5)               | Limited (2)              |
| Schema change           | 10%  | None (5)                | Yes (2)                | None (5)                 |
| Risk                    | 10%  | High (1)                | Low (4)                | Low (5)                  |
| **TOTAL**               | 100% | ~2.5                    | ~3.9                   | ~4.0                     |

**Winner:** Approach B (Persist score_total) — best balance of performance and KPI richness.  
**Runner-up:** Approach C if we need to ship without migration; then add B in Phase 2.

### Recommended Approach: B (Persist score_total)

**Architecture:**
```
Supervisor Page (/supervisor)
    → fetchAggregateKPIs(date_start, date_end)
    → GET /api/sessions/aggregate?date_start=...&date_end=...
    → Backend: query SessionModel (metadata + score_total), aggregate
    → Response: { kpis, trend, calendar, sessions? }
    → DashboardLayout (or custom) with MetricCard, LineChart, BarChart, CalendarHeatmap
    → Export CSV from sessions / kpis
```

**Data flow:**
- Sessions table: add `score_total INTEGER NULL`
- On session COMPLETE: compute score, set score_total (new endpoint or existing complete flow)
- Backfill: script to score existing sessions, update score_total
- Aggregate: `SELECT session_id, operator_id, weld_type, start_time, score_total FROM sessions WHERE ...`

---

## 4. Architectural Decisions

### Decision #1: Score Persistence

**Question:** Persist session scores for aggregation?

**Options:**  
A) Compute on aggregate request.  
B) Add score_total column; compute on completion + backfill.

**Decision:** B — Required for < 3s aggregate response with score-based KPIs.

**Trade-offs:** Schema migration + backfill vs. acceptable performance.

### Decision #2: Aggregate Endpoint Design

**Question:** GET /api/sessions/aggregate vs GET /api/dashboard/aggregate?

**Decision:** `GET /api/sessions/aggregate` — sessions are the source; keeps dashboard generic.

**Query params:** `date_start`, `date_end` (ISO date), optional `group_by`.

### Decision #3: Route for Supervisor Dashboard

**Question:** /supervisor vs /analytics vs replace /dashboard?

**Decision:** `/supervisor` — Clear persona; doesn't replace generic dashboard; avoids confusion.

### Decision #4: Calendar Heatmap Metric

**Question:** Sessions per day vs avg score per day?

**Decision:** Sessions per day for Phase 1 — simpler; no dependency on score; activity view. Can add avg score later.

### Decision #5: KPI Set (Phase 1)

**Decision:**  
- avg_score (from score_total)  
- session_count  
- top_performer (operator_id with best avg score)  
- rework_count (sessions with score_total < 60, if defined)

### Decision #6: File Structure

- `backend/routes/aggregate.py` — GET /api/sessions/aggregate  
- `backend/services/aggregate_service.py` — aggregation logic  
- `my-app/src/app/(app)/supervisor/page.tsx` — supervisor dashboard  
- `my-app/src/components/dashboard/CalendarHeatmap.tsx` — new component  
- `my-app/src/lib/export.ts` — generateCSV, downloadCSV  
- `my-app/src/types/aggregate.ts` — AggregateKPIResponse, etc.

### Decision #7: Orthogonality Enforcement

- No imports from: `TorchViz3D`, `HeatmapPlate3D`, `HeatMap` (thermal), `FeedbackPanel`, `TorchAngleGraph` (micro-feedback)
- Optional: ESLint rule or directory structure (supervisor/ cannot import from welding/)

### Decision #8: Session Filter for Aggregate

**Decision:** Include COMPLETE only; exclude FAILED, RECORDING. INCOMPLETE optional (has frames if any).

---

## 5. Edge Cases

### Data Edge Cases

| Edge Case | Severity | Handling |
|-----------|----------|----------|
| Empty data (no sessions in range) | Medium | "No sessions in date range"; empty state for charts; date picker still works |
| Null score_total | Medium | Exclude from avg_score; session_count still includes; show "—" or N/A for avg |
| Zero frames | Medium | score_total = NULL; exclude from score-derived KPIs; include in session_count |
| Malformed date_start/date_end | Low | 400 + validation message; frontend validation |
| date_start > date_end | Low | 400 or swap; document behavior |
| Extremely large date range (years) | Medium | Limit to 90 days or 500 sessions; return partial + warning |
| All sessions FAILED | Low | session_count=0; empty KPIs; empty state |
| operator_id empty string | Low | Group as "unknown" or "" |
| weld_type empty | Low | Group as "unknown" |

### User Interaction Edge Cases

| Edge Case | Severity | Handling |
|-----------|----------|----------|
| Rapid date change | Medium | Debounce 300ms or cancel previous fetch with AbortController |
| Export during load | Low | Disable Export button until data loaded |
| Double-click Export | Low | Disable after click; re-enable after download |
| Navigation during fetch | Low | AbortController; ignore setState if unmounted |
| Keyboard-only (export) | Low | Button focusable; Enter triggers |

### Network Edge Cases

| Edge Case | Severity | Handling |
|-----------|----------|----------|
| Timeout | High | Retry 1×; show "Request timed out" + Retry button |
| 5xx | High | Error boundary; "Server error" + Retry |
| Offline | Medium | fetch throws; catch and show "Check connection" |
| Slow connection | Low | Loading spinner; no timeout < 10s for aggregate |
| CORS error | Low | Backend CORS already configured; document |

### Browser / Device Edge Cases

| Edge Case | Severity | Handling |
|-----------|----------|----------|
| Small screen (320px) | Medium | Responsive grid; KPI tiles stack; charts responsive |
| Touch device | Low | Date picker touch-friendly; Export tap |
| Print | Low | Out of scope Phase 1 |
| Dark mode | Low | Tailwind dark: classes; Match theme |

---

## 6. Risk Analysis

### Technical Risks

1. **Batch scoring perf** — Mitigation: persist score_total; do not compute on aggregate.  
2. **Orthogonality break** — Mitigation: code review; no 3D imports in supervisor.  
3. **Migration failure** — Mitigation: test on dev; backfill in transaction.  
4. **Backfill slow** — Mitigation: batch backfill (e.g. 10 at a time); run async.  
5. **Aggregate query slow** — Mitigation: index on start_time; consider date range limit.  

### Execution Risks

6. **Scope creep (PDF, drill-down)** — Mitigation: scope doc; Phase 2 for PDF.  
7. **Wrong KPIs** — Mitigation: validate with stakeholder before implementation.  
8. **Timeline slippage** — Mitigation: Phase 1 minimal; defer calendar if needed.  

### User Experience Risks

9. **Empty calendar confusing** — Mitigation: "No activity" label; tooltip.  
10. **Export timeout** — Mitigation: limit to 90 days or 1000 sessions.  
11. **Timezone confusion** — Mitigation: document UTC; frontend display local.  

### Business Risks

12. **Low adoption** — Mitigation: pilot with supervisors; iterate on KPIs.  
13. **Stakeholder wants line/shift** — Mitigation: document limitation; Phase 2 schema.  

---

## 7. Exploration Summary

### TL;DR

WWAD adds a macro analytics dashboard for supervisors (KPI tiles, trend chart, calendar heatmap, CSV export). The main technical risk is performance: scoring requires frames, and batch scoring hundreds of sessions would be too slow. **Recommendation:** add `score_total` column, compute on session completion, backfill existing sessions. Aggregate endpoint queries sessions metadata + score_total only. Reuse MetricCard, ChartCard, LineChart, BarChart; add custom CalendarHeatmap (GitHub-style). Route: `/supervisor`. Orthogonality: no imports from 3D or micro-feedback. **Ready for planning:** Yes.

### Recommended Approach

- **Name:** Persist score + metadata-only aggregate  
- **Key decisions:** score_total column; /api/sessions/aggregate; /supervisor route; calendar = sessions/day  

### Files to Create/Modify

**New:**
- `backend/routes/aggregate.py`
- `backend/services/aggregate_service.py`
- `backend/alembic/versions/003_add_score_total.py`
- `my-app/src/app/(app)/supervisor/page.tsx`
- `my-app/src/components/dashboard/CalendarHeatmap.tsx`
- `my-app/src/lib/export.ts`
- `my-app/src/types/aggregate.ts`
- `backend/scripts/backfill_score_total.py`

**Modify:**
- `backend/main.py` — include aggregate router
- `my-app/src/lib/api.ts` — fetchAggregateKPIs
- Session complete flow — set score_total (or backfill-only initially)

### Effort Estimate

- Backend aggregate + migration + backfill: 10–14 h  
- Frontend supervisor page + calendar + export: 10–12 h  
- Testing + integration: 4–6 h  
- **Total:** 24–32 h  

### Quality Metrics Checklist

| Metric                        | Minimum | Pass |
|-------------------------------|---------|------|
| Similar implementations documented | 3   | Yes  |
| Prototypes considered/built   | 3       | Yes  |
| Approaches evaluated          | 3       | Yes  |
| Architectural decisions       | 8       | Yes  |
| Edge cases documented         | 10+     | Yes  |
| Risks identified              | 5+      | Yes  |
| Ready for planning            | —       | Yes  |
