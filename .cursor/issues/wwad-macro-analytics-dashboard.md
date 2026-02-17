# [Feature] WWAD: Macro-Level Multi-Session Analytics Dashboard for Supervisors

**Time Budget:** 30-45 minutes MINIMUM for comprehensive issue capture.  
**Status:** Open  
**Created:** 2025-02-17

---

## Phase 0: Understand the Workflow Position

**This is Step 1 of 3:**
1. **Create Issue** ← This document (capture the WHAT and WHY)
2. **Explore Feature** (deep dive into HOW)
3. **Create Plan** (step-by-step implementation)

**Your job right now:** Capture the problem/idea completely; provide enough context for exploration; document what you know (and what you don't); set clear boundaries and expectations. Think deeply about implications; question your own assumptions.

**NOT your job right now:** Figure out implementation details (that's exploration); write code snippets (that's planning); solve edge cases (that's exploration).

---

## MANDATORY PRE-ISSUE THINKING SESSION (15 minutes minimum)

### A. Brain Dump (5 minutes minimum)

**Raw thinking (300+ words):**

The MVP today is laser-focused on the individual welder: per-session replay with 3D heatmaps (TorchViz3D, HeatmapPlate3D), frame-level scoring (5 rules → 0–100), and micro-feedback tied to each weld. A supervisor walking onto the shop floor wants something entirely different: "How is my team performing this week?" "Which welders need training?" "What's our rework rate across Line 2?" The current dashboard at `/dashboard` shows generic mock data (Total Users, Revenue, Active Sessions) — completely unrelated to welding. The Seagull pilot at `/seagull` shows per-welder cards with scores, but it's hardcoded to 2 welders and fetches `fetchScore` per session; there's no aggregation, no team KPIs, no shift/line/project rollups.

What exactly is missing? Macro-level analytics. We need supervisor-facing views: KPI tiles (e.g., average score per team, thermal deviation counts across sessions), trend lines (scores over time by welder or by shift), heatmap calendars (activity by date), and exportable reports (CSV, PDF) for management meetings. The key insight: this should be **orthogonal** to the existing MVP. WWAD uses session-level aggregates only — precomputed scores, feature histograms, metadata (operator_id, weld_type, start_time). No per-frame data. No TorchViz3D. No HeatmapPlate3D. No micro-feedback logic. Adding WWAD should not touch a single line in the 3D visualization or scoring pipeline.

What prompted this thought? The user explicitly contrasted Current MVP vs WWAD in a clear table. Current: per-session, per-frame, tightly coupled with micro-feedback and 3D. WWAD: multi-session, team/line/project, decoupled, aggregate-only. The user said "Bottom line: WWAD is macro-focused, purely aggregate, and orthogonal — it adds supervisor-level analytics without touching any files, logic, or components from the MVP micro-feedback system."

Assumptions: (1) Session metadata (operator_id, weld_type, start_time) is sufficient for initial aggregation; line/shift/project might need new fields. (2) We can batch-score sessions server-side without loading frames for aggregation. (3) Supervisors want at-a-glance KPIs, not drill-down into frame replay. (4) CSV/PDF export is a Phase 1 requirement. (5) The existing DashboardLayout (MetricCard, ChartCard, LineChart, BarChart, PieChart) can be reused or replaced — the mock data structure is generic enough to swap in welding KPIs.

What could go wrong? GET /api/sessions returns 501 — we can't list sessions without implementing that first. Database has no line_id, shift_id, project_id — aggregation by "line" or "shift" requires schema or convention (e.g., operator_id prefix, weld_type as project). Performance: aggregating 10k+ sessions could be slow without materialized views or caching.

What don't we know? Whether supervisors have explicit line/shift/project hierarchies. How many sessions per yard per week (scale). Whether export format is CSV-only or PDF-only or both. Whether calendar heatmap is week view or month view.

Who is affected? Supervisors, yard managers, training coordinators. Not individual welders doing replay. Urgency: Medium — enables management-level use case; doesn't block core MVP.

### B. Question Storm (20+ questions)

1. What triggers the aggregation? (On page load? Scheduled job? Manual refresh?)
2. When does the supervisor view the dashboard? (Morning briefing? End of shift?)
3. Who experiences this? (Supervisors only? Also welders?)
4. How often do sessions get created per day per yard?
5. What's the impact if we don't build this? (Supervisors can't see team trends.)
6. What's the impact if we do? (Training/scheduling decisions become data-driven.)
7. Are we assuming operator_id = welder identity? (Yes, per Session model.)
8. Are we assuming weld_type can proxy for project? (Maybe; needs confirmation.)
9. Do we need line or shift metadata? (Session has none; operator_id only.)
10. What similar issues exist? (Seagull pilot: per-welder; main dashboard: mock generic.)
11. What did we learn from Seagull? (fetchScore per session; Promise.allSettled; hardcoded welder list.)
12. How do we aggregate scores without loading frames? (Score is computed from features; features need frames — or we store score in DB?)
13. Should we persist session scores in DB at completion? (Currently computed on-demand.)
14. What's the date range for "this week" or "this month"? (Configurable? Timezone?)
15. How many KPIs is enough? (3–5 tiles? 10?)
16. What chart types are needed? (Line: trend; Bar: by welder; Heatmap: calendar.)
17. Can we reuse MetricCard, ChartCard, LineChart? (Yes, types are generic.)
18. Is CSV export enough for Phase 1? (User said "CSV/PDF" — both?)
19. Does GET /api/sessions need to be implemented first? (Yes, or we need an aggregate-only endpoint that queries sessions internally.)
20. What's the relationship to the main /dashboard page? (Replace it? New route /analytics? Separate /supervisor?)
21. How do we avoid breaking micro-feedback when adding aggregation? (Strict separation: no imports from TorchViz3D/HeatmapPlate3D in WWAD.)
22. What's the rework metric? (Session model has no rework flag — inferred from score? User-defined?)

### C. Five Whys Analysis

**Problem:** Supervisors cannot see team-level welding performance trends or aggregated KPIs.

**Why #1:** Why is this a problem? — They have no visibility into multi-welder, multi-session performance.

**Why #2:** Why is that a problem? — They can't make data-driven training, scheduling, or resource allocation decisions.

**Why #3:** Why is that a problem? — Yard efficiency suffers; rework and training gaps go undetected.

**Why #4:** Why is that a problem? — Pilot yards expect management-level analytics; current MVP only serves individual welders.

**Why #5:** Why is that the real problem? — The product vision includes supervisor insights, but the system only delivers per-session, per-frame micro views.

**Root cause identified:** MVP is micro-focused (per-session, per-frame); no macro aggregation layer exists. WWAD fills that gap with session-level aggregates, orthogonal to existing components.

---

## Required Information Gathering

### 1. Understand the Request

**User's initial request (from task description):**

The user provided a structured comparison:

**Current MVP:**
- Focus: per-session, per-welder, per-frame
- Dashboard tied to frame-level scoring, 3D (TorchViz3D, HeatmapPlate3D)
- Individual welder performance only
- Hard to get team-level trends
- Cannot aggregate KPIs across shifts, teams, projects without custom queries
- No calendar heatmaps, supervisor summaries, exportable reports
- Tightly coupled with micro-feedback → changes to 3D/scoring can break dashboard

**WWAD Proposal:**
- Focus: macro-level, multi-session analytics
- Team-level KPIs, trends across welders, lines, shifts
- Aggregate thermal deviation counts, rework metrics
- Not tied to per-frame visualization or micro-feedback
- Includes supervisor insights and exportable reporting from aggregated session data only
- Backend: new `/api/sessions/aggregate` (or similar), precomputed metrics, no per-frame data
- Frontend: KPI tiles, line/bar charts, heatmap calendar, CSV/PDF exports
- Data pipeline: Session → score + metrics aggregation → trend/KPI dashboard
- Completely decoupled from 3D replay and micro-feedback

**Clarifications obtained:**
- WWAD is explicitly orthogonal: no changes to TorchViz3D, HeatmapPlate3D, micro-feedback logic
- Session-level aggregation only; no frame data needed
- Supervisor/yard manager is the primary user
- Export (CSV/PDF) is in scope

**Remaining ambiguities:**
- Line/shift/project hierarchy — Session has operator_id, weld_type, start_time only
- Whether to implement GET /api/sessions first or have aggregate endpoint query sessions internally
- Exact KPI set (which metrics)
- Date range defaults and timezone handling

### 2. Search for Context

#### Codebase Search Findings

**Similar existing features found:**

1. **Feature:** `my-app/src/components/dashboard/DashboardLayout.tsx`
   - **What it does:** Renders MetricCard grid + ChartCard grid; receives DashboardData (metrics[], charts[])
   - **Relevant patterns:** Generic MetricData (id, title, value, change, trend); ChartData (line, bar, pie)
   - **What we can reuse:** MetricCard, ChartCard, LineChart, BarChart, PieChart — swap mock data for welding KPIs
   - **What we should avoid:** DashboardLayout expects flat metrics/charts; WWAD may need grouped KPIs (by welder, by date)

2. **Feature:** `my-app/src/app/seagull/page.tsx`
   - **What it does:** Team dashboard; fetches fetchScore per welder; displays cards with welder name + score
   - **Relevant patterns:** Hardcoded WELDERS list; Promise.allSettled; Link to welder report
   - **What we can reuse:** Card layout, fetchScore (if we keep per-session scoring)
   - **What we should avoid:** Hardcoding welder list; WWAD should derive welders from sessions

3. **Feature:** `my-app/src/app/seagull/welder/[id]/page.tsx`
   - **What it does:** Per-welder report with heatmaps, AI feedback, trend chart (mock historical)
   - **Relevant patterns:** fetchSession + fetchScore; HeatMap; LineChart for trend
   - **What we can reuse:** LineChart for trend; FeedbackPanel pattern not needed for WWAD
   - **What we should avoid:** Frame-level HeatMap; WWAD is aggregate-only

4. **Feature:** `backend/routes/dashboard.py` → `GET /api/dashboard`
   - **What it does:** Returns mock_dashboard_data (Total Users, Revenue, etc.)
   - **Relevant patterns:** Pydantic DashboardData; backend/data/mock_data.py
   - **What we can reuse:** Endpoint pattern; could add `/api/dashboard/aggregate` or replace
   - **What we should avoid:** Mock generic data; WWAD needs real session-derived KPIs

5. **Feature:** `backend/routes/sessions.py` → `GET /api/sessions/{id}/score`
   - **What it does:** Loads session with frames, extract_features, score_session, returns { total, rules }
   - **Relevant patterns:** Per-session scoring; requires frames
   - **What we can reuse:** extract_features, score_session for aggregation (batch per session)
   - **What we should avoid:** Loading frames for aggregate KPIs if we can precompute/store scores

**Existing patterns to follow:**
1. **Pattern:** snake_case types mirror backend (Session, Frame, DashboardData)
   - **Why good:** No conversion layer; backend JSON → frontend types directly
   - **How to apply:** New AggregateKPIResponse, SessionSummary types mirror backend

2. **Pattern:** lib/api.ts fetch functions, ErrorBoundary, loading/error states
   - **Why good:** Consistent API client, error handling
   - **How to apply:** fetchAggregateKPIs(), fetchSupervisorDashboard()

**Anti-patterns to avoid:**
1. **Anti-pattern:** Importing TorchViz3D, HeatmapPlate3D, HeatMap in WWAD pages
   - **Why bad:** Couples macro view with micro-feedback; violates orthogonality
   - **What to do instead:** Use only MetricCard, ChartCard, LineChart, BarChart; add new CalendarHeatmap if needed

2. **Anti-pattern:** Computing aggregates client-side from per-session fetches
   - **Why bad:** N+1 queries; slow; doesn't scale
   - **What to do instead:** Backend aggregate endpoint returns precomputed KPIs

**Related components/utilities:**
- `MetricCard` at `my-app/src/components/dashboard/MetricCard.tsx` — KPI tile
- `ChartCard` at `my-app/src/components/dashboard/ChartCard.tsx` — Chart wrapper
- `LineChart` at `my-app/src/components/charts/LineChart.tsx` — Trend line
- `BarChart` at `my-app/src/components/charts/BarChart.tsx` — Category bars
- `extract_features` at `backend/features/extractor.py` — 5 features for scoring
- `score_session` at `backend/scoring/rule_based.py` — 0–100 per session

**Data models/types that exist:**
- `Session` at `my-app/src/types/session.ts` — session_id, operator_id, start_time, weld_type, frames[], status, frame_count
- `DashboardData` at `my-app/src/types/dashboard.ts` — metrics: MetricData[], charts: ChartData[]
- `SessionScore` at `my-app/src/lib/api.ts` — total, rules[]

#### Documentation Search

- **CONTEXT.md:** Session flow (API → Session → extractors → components); no aggregation; Seagull is per-welder
- **context/tech-stack-mvp-archi.md:** GET /api/sessions 501; GET /api/dashboard returns mock; sessions have operator_id, weld_type, start_time
- **README/ARCHITECTURE:** Monorepo; FastAPI + Next.js; PostgreSQL

**Key insights from documentation:**
1. GET /api/sessions is 501 — must be implemented or bypassed by aggregate endpoint that queries DB directly
2. Session has operator_id, weld_type, start_time — sufficient for operator-level and weld-type aggregation; line/shift need extension
3. Score is computed on-demand; no persisted score in DB — aggregation would need to either batch-compute or add score persistence

### 3. Web Research (if applicable)

**Not deeply required for initial issue** — aggregation patterns are standard (group by, aggregate). Calendar heatmap UX: GitHub-style contribution graph is common. CSV export: standard. PDF export: jsPDF or similar. Defer detailed research to exploration phase.

---

## 🧠 THINKING CHECKPOINT #1 (10 minutes minimum)

### 1. What am I assuming that might be wrong?

1. **Assumption:** operator_id is sufficient to identify welders for team aggregation.
   - **If wrong:** Yards use operator_id for machine/station, not person
   - **How to verify:** Check with product/stakeholder; review mock_sessions operator_id usage
   - **Likelihood:** Low
   - **Impact if wrong:** Medium — may need welder_id or similar

2. **Assumption:** We can aggregate without persisting session scores.
   - **If wrong:** Batch-loading 1000 sessions + frames for scoring is too slow
   - **How to verify:** Profile; consider materialized score table or cached aggregates
   - **Likelihood:** Medium
   - **Impact if wrong:** High — slow supervisor dashboard

3. **Assumption:** Calendar heatmap shows "sessions per day" or "average score per day."
   - **If wrong:** Supervisors want different metric (rework count, arc-on hours)
   - **How to verify:** User research; stakeholder confirmation
   - **Likelihood:** Medium
   - **Impact if wrong:** Low — can adjust metric

4. **Assumption:** WWAD lives at a new route (e.g. /analytics or /supervisor), not replacing /dashboard.
   - **If wrong:** Product wants single dashboard that switches context
   - **How to verify:** Clarify with product
   - **Likelihood:** Low
   - **Impact if wrong:** Low — routing is trivial

5. **Assumption:** CSV export is sufficient for Phase 1; PDF can be Phase 2.
   - **If wrong:** PDF is mandatory for management meetings
   - **How to verify:** Prioritization with stakeholder
   - **Likelihood:** Medium
   - **Impact if wrong:** Medium — PDF adds client-side lib (e.g. jsPDF)

### 2. What questions would a skeptical engineer ask?

1. Q: Where does the session list come from if GET /api/sessions is 501? A: Aggregate endpoint queries SessionModel directly; we don't need a public list endpoint for internal aggregation.
2. Q: Won't scoring 1000 sessions with frames exhaust memory? A: We should either persist scores at session completion or use a lightweight aggregate query (e.g. session metadata + optional precomputed score table).
3. Q: How do we avoid duplicating extract_features/score_session logic? A: Reuse existing backend functions; aggregate service calls them per session in batch.
4. Q: What if there are zero sessions? A: Empty state: "No sessions in date range" with date picker.
5. Q: Does the frontend need to know about frames at all? A: No. WWAD consumes only aggregate API responses.
6. Q: What about timezone for "this week"? A: Backend should accept timezone or use UTC; document in API contract.
7. Q: Can we use the existing DashboardData type? A: Partially; metrics/charts shape fits, but we may need new fields (date_range, group_by).
8. Q: Is there a rate limit on the aggregate endpoint? A: Should add one for production; not blocking MVP.
9. Q: How do we test aggregate logic? A: Unit tests with seeded sessions; assert KPIs match expected aggregates.
10. Q: Does this block micro-feedback work? A: No. Orthogonal. No shared files.

### 3. What am I not seeing?

**Edge cases:**
1. Sessions with status INCOMPLETE or FAILED — include or exclude in aggregates?
2. Sessions with zero frames — can't score; how do we count them?
3. Date range spanning years — performance of large aggregates
4. operator_id collision across yards (multi-tenant?)
5. Weld type not set (empty string) — group as "unknown"?

**Failure modes:**
1. Aggregate endpoint timeout on large date range
2. Stale cache if sessions added after last aggregation
3. Export fails for very large result sets
4. Calendar heatmap empty for sparse data — UX

**Dependencies:**
1. GET /api/sessions or equivalent list capability (or internal DB query in aggregate route)
2. Possible migration: add `score_total` column to sessions table for performance
3. Recharts or similar for charts — already present

### 4. Explain this to a junior developer

"We have a welding app where welders see their own session replay and score. Supervisors don't have a view. They want to see 'How did my team do this week?' — average scores, trends, who needs training. That's WWAD: a macro analytics dashboard. It uses only session-level data: who welded, when, what type, and the score. No frame-level data, no 3D heatmaps. We're adding a new backend endpoint that aggregates sessions by date, welder, weld type, and returns KPIs. The frontend shows KPI tiles, trend charts, and a calendar heatmap. We keep it completely separate from the replay and 3D components so we don't break anything. The key rule: WWAD never imports TorchViz3D or HeatmapPlate3D or micro-feedback logic."

### 5. Red team this issue

**Problem 1:** Score computation requires frames; loading frames for N sessions is expensive.
- **Why:** extract_features needs session.frames; score_session needs features
- **Impact:** Slow or OOM on large aggregation
- **Mitigation:** Persist score at session completion (new column or table); or lightweight feature cache

**Problem 2:** No line/shift metadata — "team-level" is underspecified.
- **Why:** Session has operator_id only; "team" could mean group of operators
- **Impact:** Ambiguous requirements; may build wrong aggregates
- **Mitigation:** Phase 1: aggregate by operator_id and weld_type; defer line/shift to schema extension

**Problem 3:** Main /dashboard shows unrelated mock data; confusion about which dashboard is for whom.
- **Why:** Two dashboards: one generic mock, one (future) welding aggregate
- **Impact:** User confusion; duplicate concepts
- **Mitigation:** Replace /dashboard with welding KPIs, or clearly separate /dashboard (generic) vs /supervisor (WWAD)

**Problem 4:** Exporting 10k sessions to CSV could be huge.
- **Why:** Unbounded export
- **Impact:** Timeout, memory, download size
- **Mitigation:** Limit export (e.g. last 90 days); pagination; streaming

**Problem 5:** Calendar heatmap — what metric? Sessions count? Avg score? Rework?
- **Why:** Multiple valid choices; affects both backend and UX
- **Impact:** Rebuild if wrong
- **Mitigation:** Start with session count per day; make metric configurable later

---

## Issue Structure

### 1. Title

**[Feature] WWAD: Macro-Level Multi-Session Analytics Dashboard for Supervisors**

- [x] Starts with type tag
- [x] Specific (macro, multi-session, supervisor)
- [x] Under 100 characters
- [x] No jargon (WWAD = working name; macro/supervisor are clear)
- [x] Action-oriented (adds dashboard)

### 2. TL;DR (Executive Summary)

**5–7 sentences (150+ words):**

Supervisors and yard managers cannot view team-level welding performance trends. The current MVP delivers per-session replay, 3D heatmaps, and per-welder scores (e.g. Seagull pilot), but no aggregated KPIs across welders, shifts, or time periods. The core problem is that the system is micro-focused: all dashboards and visualizations depend on frame-level data and are tightly coupled with TorchViz3D, HeatmapPlate3D, and micro-feedback logic. Currently, supervisors have no way to answer "How did the team perform this week?" or "Which welders need training?" without custom database queries. We need a macro-level analytics dashboard (WWAD) that displays KPI tiles, trend charts, and a calendar heatmap derived solely from aggregated session data (scores, metadata), with optional CSV/PDF export. This aligns with the product vision of enabling management-level decisions for training, scheduling, and resource allocation. This is a medium-effort feature (estimated 24–40 hours) with high strategic value for pilot yards and enterprise sales.

### 3. Current State (What Exists Today)

#### A. What's Already Built

**UI Components:**

1. **Component:** `my-app/src/components/dashboard/DashboardLayout.tsx`
   - **What it does:** Renders metrics grid (MetricCard) and charts grid (ChartCard with LineChart, BarChart, PieChart)
   - **Current capabilities:** Accepts DashboardData; responsive grid; dark mode
   - **Limitations:** Fed by mock data; metrics are generic (Total Users, Revenue); not welding-specific
   - **Dependencies:** MetricCard, ChartCard, LineChart, BarChart, PieChart, types/dashboard
   - **Last modified:** (check git)

2. **Component:** `my-app/src/app/(app)/dashboard/page.tsx`
   - **What it does:** Fetches fetchDashboardData(), renders DashboardLayout + Welding Sessions list (hardcoded sess_expert_001, sess_novice_001)
   - **Current capabilities:** Loading, error, retry; demo CTA
   - **Limitations:** Dashboard data is mock; sessions list is static
   - **Dependencies:** lib/api fetchDashboardData, ErrorBoundary
   - **Last modified:** (check git)

3. **Component:** `my-app/src/app/seagull/page.tsx`
   - **What it does:** Team dashboard; hardcoded 2 welders; fetchScore per session; cards with score
   - **Current capabilities:** Per-welder score display; Link to welder report
   - **Limitations:** Hardcoded WELDERS; no aggregation; no trends; no export
   - **Dependencies:** fetchScore, lib/api
   - **Last modified:** (check git)

4. **Component:** `my-app/src/app/seagull/welder/[id]/page.tsx`
   - **What it does:** Welder report: score, AI feedback, side-by-side heatmaps (HeatMap), trend chart (mock MOCK_HISTORICAL)
   - **Current capabilities:** fetchSession, fetchScore, HeatMap, LineChart, FeedbackPanel
   - **Limitations:** Per-session; requires frame data for heatmaps; trend is mock
   - **Dependencies:** useFrameData, extractHeatmapData, HeatMap, FeedbackPanel, generateAIFeedback
   - **Last modified:** (check git)

**API Endpoints:**

1. **Endpoint:** `GET /api/dashboard`
   - **What it does:** Returns mock_dashboard_data (metrics, charts)
   - **Request shape:** None
   - **Response shape:** DashboardData (metrics[], charts[])
   - **Auth required:** No
   - **Rate limited:** No
   - **Missing:** Real welding data; aggregation

2. **Endpoint:** `GET /api/sessions`
   - **What it does:** 501 Not Implemented
   - **Missing:** Cannot list sessions; blocks aggregate use cases

3. **Endpoint:** `GET /api/sessions/{session_id}`
   - **What it does:** Returns session with frames (paginated, streamable)
   - **Request shape:** session_id, include_thermal, time_range_start, time_range_end, limit, offset, stream
   - **Response shape:** Session with frames[]
   - **Auth required:** No
   - **Rate limited:** No
   - **Missing:** Not for aggregation (returns full frames)

4. **Endpoint:** `GET /api/sessions/{session_id}/score`
   - **What it does:** Loads session with frames, extract_features, score_session; returns { total, rules }
   - **Request shape:** session_id
   - **Response shape:** SessionScore
   - **Auth required:** No
   - **Missing:** Per-session only; no batch aggregate

**Data Models:**

1. **Type:** `DashboardData` at `my-app/src/types/dashboard.ts`
```typescript
interface DashboardData {
  metrics: MetricData[];
  charts: ChartData[];
}
```
   - **Purpose:** Dashboard layout input
   - **Used by:** DashboardLayout, dashboard page
   - **Limitations:** Generic; no date_range, no group_by

2. **Type:** `Session` at `my-app/src/types/session.ts`
   - **Purpose:** Welding session with frames
   - **Used by:** Replay, Compare, Score, Seagull
   - **Limitations:** No score persisted; no line_id, shift_id, project_id

3. **Type:** `SessionModel` at `backend/database/models.py`
   - **Purpose:** sessions table: session_id, operator_id, start_time, weld_type, status, frame_count, ...
   - **Used by:** All session routes
   - **Limitations:** No score column; no line/shift/project

#### B. Current User Flows

**Flow 1: Supervisor views main dashboard**
```
Step 1: User navigates to /dashboard
  ↓
Step 2: Frontend fetches GET /api/dashboard
  ↓
Step 3: User sees generic metrics (Total Users, Revenue, Active Sessions) + hardcoded session links
  ↓
Current limitation: No welding-specific KPIs; no team trends
```

**Flow 2: Supervisor views Seagull team dashboard**
```
Step 1: User navigates to /seagull
  ↓
Step 2: Frontend fetches fetchScore for each hardcoded welder (2)
  ↓
Step 3: User sees 2 cards with welder name + score
  ↓
Current limitation: Hardcoded; no aggregation; no trends; no export
```

**Flow 3: Individual welder views replay**
```
Step 1: User navigates to /replay/{sessionId}
  ↓
Step 2: Frontend fetches fetchSession, loads frames
  ↓
Step 3: User sees 3D heatmap, angle graph, timeline
  ↓
Not relevant to WWAD: Per-session, per-frame; supervisor doesn't use this for team view
```

#### C. Broken/Incomplete User Flows

1. **Flow:** Supervisor wants "Average team score this week"
   - **Current behavior:** Cannot; no aggregate endpoint; Seagull shows 2 hardcoded welders only
   - **Why it fails:** No aggregation logic; no session list
   - **User workaround:** Manual DB queries or spreadsheet
   - **Frequency:** Every shift review
   - **Impact:** No data-driven decisions

2. **Flow:** Supervisor wants "Which welders improved over last month?"
   - **Current behavior:** Cannot; no trend data; WelderReport has mock historical only
   - **Why it fails:** No multi-session trend aggregation
   - **User workaround:** None
   - **Frequency:** Monthly reviews
   - **Impact:** Training gaps go undetected

3. **Flow:** Supervisor wants "Export session summary for management meeting"
   - **Current behavior:** Cannot; no export; Email/PDF buttons in WelderReport are stubs
   - **Why it fails:** No export implementation
   - **User workaround:** Screenshots or manual copy-paste
   - **Frequency:** Weekly/monthly
   - **Impact:** Friction in reporting

#### D. Technical Gaps Inventory

**Frontend gaps:**
- No aggregate KPI components (or reuse MetricCard with real data)
- No calendar heatmap component
- No export (CSV/PDF) implementation
- No supervisor-specific layout/routing
- Missing AggregateDashboardData or similar types

**Backend gaps:**
- No GET /api/sessions (501) or equivalent list
- No /api/sessions/aggregate or /api/dashboard/aggregate endpoint
- No precomputed score persistence (optional)
- No batch scoring service for N sessions
- No line/shift/project metadata in Session

**Integration gaps:**
- Dashboard fetches mock data; no welding API integration for KPIs

**Data gaps:**
- Session scores not stored; recomputed on each /score call
- No aggregate cache or materialized view

### 4. Desired Outcome (What Should Happen)

#### A. User-Facing Changes

**Primary User Flow: Supervisor views macro analytics**
```
User does:
1. Navigate to /supervisor or /analytics (or replaces /dashboard)
2. Optionally select date range (default: last 7 days)
3. Optionally filter by weld_type or operator_id
4. View KPI tiles, trend chart, calendar heatmap
5. Click "Export CSV" or "Export PDF" to download report

User sees:
1. KPI tiles: e.g. "Avg Score (82)", "Sessions (47)", "Top Performer (op_42)", "Rework Count (3)"
2. Trend chart: Score over time (by day or by welder)
3. Calendar heatmap: Activity or score by date (GitHub-style)
4. Optional: Table of sessions with score, operator, date

User receives:
1. CSV file with session list and aggregates (when exporting)
2. PDF summary (when exporting PDF)

Success state: Supervisor has at-a-glance team performance; can export for meetings
```

**UI Changes:**
1. **New/Modified element:** KPI tiles
   - **Location:** Top of supervisor dashboard
   - **Appearance:** Same as MetricCard; welding-specific labels and values
   - **Behavior:** Static from API; no drill-down in Phase 1
   - **States:** default, loading, error, empty

2. **New element:** Trend chart
   - **Location:** Below KPIs
   - **Appearance:** LineChart (date vs avg score or count)
   - **Behavior:** Data from aggregate API
   - **States:** default, loading, empty

3. **New element:** Calendar heatmap
   - **Location:** Below trend chart
   - **Appearance:** Grid of cells (e.g. 7×12 weeks); color intensity by metric
   - **Behavior:** Hover shows value; click optional
   - **States:** default, loading, empty

4. **New element:** Export buttons
   - **Location:** Toolbar or footer
   - **Appearance:** "Export CSV", "Export PDF"
   - **Behavior:** Trigger download; loading state during generation
   - **States:** default, loading, error

#### B. Technical Changes

**New files to create:**
1. `backend/routes/aggregate.py` (or extend dashboard.py)
   - **Type:** API route
   - **Purpose:** GET /api/sessions/aggregate or /api/dashboard/aggregate
   - **Key responsibilities:** Query sessions; compute or fetch scores; aggregate by date, operator_id, weld_type; return KPIs, trend data, calendar data
   - **Dependencies:** SessionModel, extract_features, score_session (or cached scores)
   - **Exported:** Router

2. `backend/services/aggregate_service.py`
   - **Type:** Service
   - **Purpose:** Batch aggregation logic: date range filter, group by, compute KPIs
   - **Key responsibilities:** get_aggregate_kpis(date_start, date_end, group_by?)
   - **Dependencies:** DB session, models
   - **Exported:** get_aggregate_kpis

3. `my-app/src/app/(app)/supervisor/page.tsx` (or /analytics)
   - **Type:** Page
   - **Purpose:** Supervisor dashboard; fetch aggregate API; render KPIs, charts, calendar, export
   - **Key responsibilities:** fetchAggregateKPIs; DashboardLayout or custom layout
   - **Dependencies:** api.ts, dashboard components
   - **Exported:** default

4. `my-app/src/lib/export.ts` (or similar)
   - **Type:** Utility
   - **Purpose:** generateCSV(aggregateData), generatePDF(aggregateData)
   - **Dependencies:** Optional jsPDF for PDF
   - **Exported:** generateCSV, generatePDF

5. `my-app/src/components/dashboard/CalendarHeatmap.tsx`
   - **Type:** Component
   - **Purpose:** Render calendar grid; color by metric
   - **Dependencies:** None (or Recharts if needed)
   - **Exported:** CalendarHeatmap

**Existing files to modify:**
1. `my-app/src/lib/api.ts`
   - **Current state:** fetchDashboardData, fetchSession, fetchScore, addFrames
   - **Changes needed:** Add fetchAggregateKPIs(date_start?, date_end?)
   - **Risk level:** Low
   - **Why risky:** Minimal; additive

2. `my-app/src/types/dashboard.ts` (or new types/aggregate.ts)
   - **Current state:** DashboardData, MetricData, ChartData
   - **Changes needed:** Add AggregateKPIResponse or extend DashboardData with welding-specific shape
   - **Risk level:** Low

3. `backend/main.py`
   - **Current state:** Registers dashboard_router, sessions_router, dev_router
   - **Changes needed:** Include aggregate router
   - **Risk level:** Low

**New API endpoint:**
1. `GET /api/sessions/aggregate` (or GET /api/dashboard/aggregate)
   - **Purpose:** Return team-level KPIs, trend data, calendar data for supervisor dashboard
   - **Request shape:**
```
Query params:
  date_start?: string (ISO date)
  date_end?: string (ISO date)
  group_by?: 'day' | 'welder' | 'weld_type'
```
   - **Response shape:**
```typescript
{
  kpis: { avg_score: number; session_count: number; ... };
  trend: { date: string; value: number }[];
  calendar: { date: string; value: number }[];  // or similar
  sessions?: SessionSummary[];  // optional for export
}
```
   - **Auth required:** No (Phase 1)
   - **Rate limits:** Consider adding for production

**Data model changes:**
1. **Optional:** Add `score_total` column to sessions table
   - **Purpose:** Avoid recomputing score for every aggregate query
   - **Migration:** Add column; backfill on session complete; use in aggregate
   - **Breaking:** No

#### C. Success Criteria (Minimum 12 Acceptance Criteria)

**User can criteria:**
1. **[ ]** User can view KPI tiles showing team-level metrics (avg score, session count) for a date range
   - **Verification:** Navigate to supervisor dashboard; see at least 3 KPI tiles with numeric values
   - **Expected behavior:** Values reflect actual session data from DB

2. **[ ]** User can view a trend chart (score or count over time)
   - **Verification:** Chart visible; data points match aggregate
   - **Expected behavior:** Line or bar chart; x-axis = date or welder

3. **[ ]** User can view a calendar heatmap showing activity or score by date
   - **Verification:** Grid of cells; color intensity varies by metric
   - **Expected behavior:** Hover shows value; responsive

4. **[ ]** User can select a date range (e.g. last 7 days, last 30 days)
   - **Verification:** Date picker or preset buttons; data refreshes
   - **Expected behavior:** API receives date_start, date_end

5. **[ ]** User can export aggregate data as CSV
   - **Verification:** Click "Export CSV"; file downloads
   - **Expected behavior:** CSV contains session summaries and/or KPIs

6. **[ ]** User can see empty state when no sessions in date range
   - **Verification:** Select range with no sessions; see "No data" message
   - **Expected behavior:** No errors; clear message

**System does criteria:**
7. **[ ]** System aggregates sessions by date range from database
   - **Verification:** Backend query filters by start_time
   - **Expected behavior:** Only sessions in range included

8. **[ ]** System computes or retrieves session scores for aggregation
   - **Verification:** KPIs include score-derived metrics
   - **Expected behavior:** Uses extract_features + score_session or cached score

9. **[ ]** System returns aggregate response in < 3 seconds for typical load (e.g. 500 sessions)
   - **Verification:** Measure API response time
   - **Expected behavior:** Under 3s

10. **[ ]** System does not load frame data for aggregation (session metadata + score only)
    - **Verification:** Code review; no frames fetched for aggregate
    - **Expected behavior:** Orthogonal to replay; no frame payload

11. **[ ]** System handles 501 on GET /api/sessions by using internal DB query in aggregate endpoint
    - **Verification:** Aggregate endpoint works without public list endpoint
    - **Expected behavior:** No dependency on GET /api/sessions

12. **[ ]** System does not modify TorchViz3D, HeatmapPlate3D, or micro-feedback components
    - **Verification:** Grep for imports; no WWAD imports of those
    - **Expected behavior:** Orthogonality preserved

**Quality criteria:**
- **Performance:** Aggregate API < 3s for 500 sessions
- **Accessibility:** WCAG 2.1 Level AA; keyboard nav for export
- **Browser compatibility:** Chrome 90+, Firefox 88+, Safari 14+
- **Error handling:** Graceful message on API failure; retry option

### 5. Scope Boundaries (What's In/Out)

#### In Scope (What WILL Be Done)

1. **[ ]** Backend aggregate endpoint returning KPIs, trend, calendar data
   - **Why in scope:** Core requirement
   - **User value:** Supervisor sees team metrics
   - **Effort:** 8–12 hours

2. **[ ]** Supervisor dashboard page (new route) with KPI tiles, trend chart, calendar heatmap
   - **Why in scope:** Primary UI
   - **User value:** At-a-glance view
   - **Effort:** 8–12 hours

3. **[ ]** Date range filter (preset or picker)
   - **Why in scope:** Essential for "this week" / "this month"
   - **User value:** Flexible analysis
   - **Effort:** 2–4 hours

4. **[ ]** CSV export of aggregate/session summary
   - **Why in scope:** User requirement
   - **User value:** Reporting for meetings
   - **Effort:** 2–4 hours

5. **[ ]** Aggregate by operator_id and weld_type (no line/shift)
   - **Why in scope:** Session has these; sufficient for Phase 1
   - **User value:** Per-welder, per-weld-type view
   - **Effort:** Included in backend

**Total effort for in-scope:** ~24–40 hours

#### Out of Scope (What Will NOT Be Done)

1. **[ ]** PDF export
   - **Why out of scope:** CSV covers 80% of export use case; PDF adds dependency
   - **When might we do this:** Phase 2 if requested
   - **Workaround for now:** CSV in Excel; print or convert

2. **[ ]** Line, shift, project metadata and aggregation
   - **Why out of scope:** Session schema has no such fields
   - **When might we do this:** Schema migration + Phase 2
   - **Workaround for now:** Use operator_id, weld_type as proxies

3. **[ ]** Implementing GET /api/sessions as a public list endpoint
   - **Why out of scope:** Aggregate endpoint can query DB internally
   - **When might we do this:** If other features need session list
   - **Workaround for now:** Aggregate owns its query

4. **[ ]** Persisting session scores in DB (materialized)
   - **Why out of scope:** May not be needed if aggregate is fast
   - **When might we do this:** If performance requires it
   - **Workaround for now:** Compute on aggregate request

5. **[ ]** Drill-down from KPI to session replay
   - **Why out of scope:** Phase 1 is overview only
   - **When might we do this:** Phase 2
   - **Workaround for now:** Link to existing /replay/{id} from session table if we add one

#### Scope Justification

- **Optimizing for:** Speed to market; orthogonality; minimal schema change
- **Deferring:** PDF, line/shift, score persistence, drill-down
- **Rationale:** Phase 1 proves supervisor value with least scope; iterate based on feedback

### 6. Known Constraints & Context

#### Technical Constraints

**Must use:**
- FastAPI, PostgreSQL, SQLAlchemy (existing stack)
- Next.js, React, TypeScript, Tailwind (existing frontend)
- snake_case types mirroring backend
- Existing extract_features, score_session (reuse, don't rewrite)

**Must work with:**
- SessionModel, FrameModel (existing schema)
- operator_id, weld_type, start_time (existing fields)
- Recharts (already in project for LineChart, BarChart)

**Cannot change:**
- TorchViz3D, HeatmapPlate3D, micro-feedback logic (orthogonality)
- Session model structure (without migration)

**Must support:**
- Browsers: Chrome 90+, Firefox 88+, Safari 14+
- Responsive layout for supervisor view

#### Business Constraints

- **Timeline:** No hard deadline stated
- **Resources:** Assume single developer
- **Dependencies:** None blocking

#### Design Constraints

- Follow WarpSense theme (blue/purple; see CONTEXT.md)
- MetricCard, ChartCard patterns from existing dashboard
- Accessibility: WCAG 2.1 AA

### 7. Related Context (Prior Art & Dependencies)

#### Similar Features in Codebase

**Feature 1: Seagull team dashboard** (`my-app/src/app/seagull/page.tsx`)
- **What it does:** Per-welder score cards; hardcoded list
- **Similar because:** Supervisor-facing; team view
- **Patterns to reuse:** Card layout; fetchScore
- **Mistakes to avoid:** Hardcoding; no aggregation; no trends

**Feature 2: Main dashboard** (`my-app/src/app/(app)/dashboard/page.tsx`)
- **What it does:** Generic mock metrics + session links
- **Similar because:** Dashboard layout
- **Patterns to reuse:** DashboardLayout, MetricCard, ChartCard
- **Mistakes to avoid:** Mock data; unrelated metrics

**Feature 3: WelderReport** (`my-app/src/app/seagull/welder/[id]/page.tsx`)
- **What it does:** Per-welder report with heatmaps, AI feedback, trend
- **Similar because:** Trend chart
- **Patterns to reuse:** LineChart
- **Mistakes to avoid:** Frame-level HeatMap; mock historical data

#### Related Issues

- **Seagull pilot expansion** (`.cursor/issues/seagull-pilot-expansion.md`): Per-welder UI; WWAD extends to multi-session aggregate
- **Warpsense micro-feedback** (`.cursor/issues/warpsense-micro-feedback-feature.md`): Frame-level; orthogonal to WWAD

#### Dependency Tree

```
WWAD (this issue)
  ↑
  Depends on: None (can use internal DB query)
  ↓
  Blocks: None
  Related: Seagull (same user persona, different granularity)
```

### 8. Open Questions & Ambiguities

**Question #1:** Should we persist session scores in DB to speed up aggregation?
- **Why unclear:** Performance vs implementation complexity
- **Impact if wrong:** Slow aggregates or unnecessary migration
- **Who can answer:** Tech lead; profile first
- **Current assumption:** Compute on demand; add persistence if slow
- **Confidence:** Medium
- **Risk if wrong:** Medium

**Question #2:** What is the primary metric for the calendar heatmap?
- **Why unclear:** Sessions per day? Avg score per day? Rework count?
- **Impact if wrong:** Wrong insight
- **Who can answer:** Product / supervisor user
- **Current assumption:** Session count per day
- **Confidence:** Low
- **Risk if wrong:** Low (easy to change)

**Question #3:** New route: /supervisor, /analytics, or replace /dashboard?
- **Why unclear:** Information architecture
- **Impact if wrong:** Navigation confusion
- **Who can answer:** Product
- **Current assumption:** New route /supervisor
- **Confidence:** Medium
- **Risk if wrong:** Low

**Question #4:** Include failed/incomplete sessions in aggregates?
- **Why unclear:** Definition of "activity"
- **Impact if wrong:** Misleading KPIs
- **Who can answer:** Product
- **Current assumption:** Exclude FAILED; include INCOMPLETE (they have scores if they have frames)
- **Confidence:** Low
- **Risk if wrong:** Low

**Question #5:** Date range timezone: UTC or user local?
- **Why unclear:** Session start_time is UTC; user may be in local TZ
- **Impact if wrong:** Off-by-one-day at boundaries
- **Who can answer:** Tech; document decision
- **Current assumption:** UTC for backend; frontend can display local
- **Confidence:** Medium
- **Risk if wrong:** Low

**Question #6:** What KPIs beyond avg_score and session_count?
- **Why unclear:** User didn't specify full list
- **Impact if wrong:** Missing useful metrics
- **Who can answer:** Product / supervisor
- **Current assumption:** avg_score, session_count, top_performer (operator_id with best avg), optionally rework (sessions with score < threshold)
- **Confidence:** Low
- **Risk if wrong:** Medium

**Question #7:** Export limit (max sessions / max date range)?
- **Why unclear:** Unbounded export can timeout
- **Impact if wrong:** Export fails for large datasets
- **Who can answer:** Tech
- **Current assumption:** Limit to 90 days or 1000 sessions
- **Confidence:** Medium
- **Risk if wrong:** Low

**Question #8:** Does GET /api/sessions need to be implemented for other reasons?
- **Why unclear:** 501 may block other work
- **Impact if wrong:** Duplicate work if we implement it elsewhere
- **Who can answer:** Tech / backlog
- **Current assumption:** No; aggregate endpoint is self-contained
- **Confidence:** High
- **Risk if wrong:** Low

**Question #9:** Recharts for calendar heatmap or custom CSS grid?
- **Why unclear:** Recharts has no built-in calendar heatmap
- **Impact if wrong:** Implementation approach
- **Who can answer:** Tech
- **Current assumption:** Custom CSS grid (like HeatMap component pattern)
- **Confidence:** Medium
- **Risk if wrong:** Low

**Question #10:** Authentication/authorization for supervisor dashboard?
- **Why unclear:** MVP may be open; enterprise needs auth
- **Impact if wrong:** Security gap
- **Who can answer:** Product / security
- **Current assumption:** No auth in Phase 1 (same as rest of app)
- **Confidence:** Medium
- **Risk if wrong:** Medium (if deployed to production)

**Blockers:** None marked. **Important:** Q2 (calendar metric), Q6 (KPI list).

### 9. Initial Risk Assessment

**Risk #1: Technical — Performance of batch scoring**
- **Description:** Aggregating 500+ sessions requires scoring each; loading frames for each could be slow
- **Why risky:** extract_features + score_session need frames; N sessions × frames = heavy
- **Probability:** 40%
- **Impact if occurs:** High — supervisor dashboard unusably slow
- **Mitigation:** Persist score at session completion; or lightweight batch with limit; profile early
- **Contingency:** Add score_total column; backfill; use in aggregate
- **Owner:** Backend dev

**Risk #2: Technical — GET /api/sessions 501**
- **Description:** No way to list sessions; aggregate must query DB directly
- **Why risky:** If aggregate needs session list, we must implement internal query
- **Probability:** 100% (current state)
- **Impact if occurs:** Low — we can query SessionModel in aggregate route
- **Mitigation:** Aggregate endpoint owns its SQLAlchemy query; no dependency on list endpoint
- **Contingency:** Implement GET /api/sessions later if needed elsewhere
- **Owner:** Backend dev

**Risk #3: Scope — Line/shift metadata missing**
- **Description:** Session has no line_id, shift_id; "team" is ambiguous
- **Why risky:** Supervisors may expect "Line 2" or "Shift A" filters
- **Probability:** 60%
- **Impact if occurs:** Medium — Phase 1 limited to operator_id, weld_type
- **Mitigation:** Document limitation; use operator_id as welder proxy; defer schema extension
- **Contingency:** Migration in Phase 2
- **Owner:** Product

**Risk #4: Execution — Scope creep (PDF, drill-down)**
- **Description:** Stakeholders ask for PDF export or session drill-down in Phase 1
- **Why risky:** Adds effort; delays delivery
- **Probability:** 30%
- **Impact if occurs:** Medium
- **Mitigation:** Clear scope doc; CSV + Phase 2 for PDF
- **Contingency:** Push to Phase 2
- **Owner:** PM

**Risk #5: User — Wrong KPI set**
- **Description:** We build avg_score, session_count but supervisors want rework_rate, arc_on_ratio
- **Why risky:** Rework may not be in schema; arc_on_ratio needs frame-level
- **Probability:** 30%
- **Impact if occurs:** Medium — some KPIs impossible without schema/scope change
- **Mitigation:** Confirm KPI list before implementation
- **Contingency:** Add feasible KPIs; document gaps
- **Owner:** Product

**Risk #6: Technical — Calendar heatmap UX**
- **Description:** Sparse data (few sessions per day) makes heatmap look empty
- **Why risky:** UX may be confusing
- **Probability:** 40%
- **Impact if occurs:** Low
- **Mitigation:** Sensible color scale; empty state; tooltip
- **Contingency:** Simplify or remove calendar in Phase 1
- **Owner:** Frontend dev

**Risk #7: Integration — Breaking orthogonality**
- **Description:** Accidentally import TorchViz3D or micro-feedback in WWAD
- **Why risky:** Coupling; regression
- **Probability:** 20%
- **Impact if occurs:** High
- **Mitigation:** Code review; ESLint rule to forbid imports from welding 3D in supervisor module
- **Contingency:** Revert; strict module boundaries
- **Owner:** Dev

**Risk #8: Business — Low adoption**
- **Description:** Supervisors don't use dashboard; prefer spreadsheets
- **Why risky:** Wasted effort
- **Probability:** 25%
- **Impact if occurs:** Medium
- **Mitigation:** Pilot with real supervisors; iterate on KPIs
- **Contingency:** Simplify; focus on export
- **Owner:** Product

**Risk Matrix:**

| Risk | Probability | Impact | Priority |
|------|------------|--------|----------|
| #1 Batch scoring perf | 40% | High | P0 |
| #2 GET /api/sessions 501 | 100% | Low | P2 |
| #3 Line/shift missing | 60% | Medium | P1 |
| #4 Scope creep | 30% | Medium | P1 |
| #5 Wrong KPIs | 30% | Medium | P1 |
| #6 Calendar UX | 40% | Low | P2 |
| #7 Orthogonality | 20% | High | P0 |
| #8 Low adoption | 25% | Medium | P2 |

**Top 3 Risks:** #1 (perf), #7 (orthogonality), #3 (line/shift). Plan: Profile aggregate early; enforce no 3D/micro-feedback imports; document operator_id = welder for Phase 1.

### 10. Classification & Metadata

**Type:** feature

**Priority:** P2 (Normal)
- High impact for supervisor persona; not blocking core MVP (replay, scoring, demo)
- Enables management-level use case; differentiator for pilot yards
- No urgent deadline

**Priority justification (100+ words):**
WWAD addresses a clear gap: supervisors have no team-level visibility. The MVP serves individual welders well (replay, score, Seagull per-welder cards) but offers nothing for yard managers who need trends, KPIs, and exportable reports. This is a strategic feature for pilot deployments and enterprise sales — supervisors are key stakeholders. However, it does not block core MVP delivery (replay, scoring, demo are complete). We prioritize it as P2: important for roadmap, but not critical path. If resources allow, tackling it next makes sense to round out the product story. If not, it can wait for a later sprint.

**Effort:** Medium (24–40 hours)

**Complexity breakdown:**
- Backend aggregate service + route: 8–12 hours
- Frontend supervisor page + components: 8–12 hours
- Date filter + calendar heatmap: 4–6 hours
- CSV export: 2–4 hours
- Testing + integration: 4–6 hours
- **Total:** ~26–40 hours

**Confidence:** Medium — aggregation is straightforward; performance unknown until we profile; KPI set may evolve.

**Category:** Fullstack (backend + frontend)

**Tags:** user-facing, high-impact, needs-research (KPI definition)

### 11. Strategic Context (Product Vision Alignment)

#### Product Roadmap Fit

- **Q2 Goal (assumed):** Expand from individual welder tools to team/supervisor capabilities
- **This issue supports:** Supervisor-level analytics; data-driven training and scheduling
- **Contribution:** ~30% toward "team/supervisor" pillar
- **Metric impact:** Enables tracking of team performance; prerequisite for "training effectiveness" metrics

- **Product vision:** WarpSense as reliable MVP for recording, replaying, scoring — and surfacing insights for training and QA
- **This issue advances:** Supervisors can act on welding data; replay/score become organizational assets
- **Strategic importance:** High for pilot yards; medium for core MVP

#### Capabilities Unlocked

1. **Future: Training program effectiveness**
   - **How WWAD enables:** Baseline team KPIs; can measure improvement after training
   - **When:** Post-pilot

2. **Future: Scheduling optimization**
   - **How WWAD enables:** Identify low performers; assign mentors or adjust shifts
   - **When:** Phase 2

3. **Future: Export to ERP / BI**
   - **How WWAD enables:** CSV export can feed external systems
   - **When:** Integration phase

#### User Impact Analysis

- **User segment:** Supervisors, yard managers
- **Size:** 1–5 per pilot yard; scales with enterprise
- **Benefit:** At-a-glance team performance; export for meetings
- **Value:** Time saved vs manual queries; data-driven decisions

- **User segment:** Training coordinators
- **Size:** Same as above
- **Benefit:** Identify welders needing training
- **Value:** Targeted training; faster skill uptake

**Impact metrics:**
- **Frequency of use:** 1–2× per day (shift review)
- **Time saved:** ~15–30 min/day vs manual
- **Adoption:** Expected high if KPIs match supervisor needs

#### Technical Impact

- **Improves:** Completeness of product; supervisor persona coverage
- **Maintains:** Orthogonality; no regression to replay/3D
- **Reduces:** Manual reporting friction
- **Adds:** New route, new backend service; minimal tech debt if scoped well

---

## 🧠 THINKING CHECKPOINT #2 (10 minutes minimum)

### Self-Critique Questions

1. **Would a new team member understand this?** List 5 unclear things:
   - "WWAD" acronym — spell out (Workspace Welding Analytics Dashboard or similar) in intro
   - Exact KPI list still fuzzy
   - Calendar heatmap spec could use a mockup reference
   - "Rework" metric — how derived? (Score < X?)
   - Relationship between /dashboard and /supervisor could be clearer

2. **Can someone explore deeply without questions?** Potential questions:
   - What SQL does the aggregate query look like? → Exploration phase
   - What does CalendarHeatmap look like? → Exploration phase
   - How do we avoid loading frames? → Use cached score or batch with limit

3. **Did I quantify impact?** Count: ~15 numbers (hours, %, sessions, etc.). Adequate.

4. **Did I provide evidence?** Yes: file paths, endpoint shapes, type definitions, codebase references.

5. **Did I think about failure?** Yes: 8 risks; performance, orthogonality, scope.

6. **Did I connect to bigger picture?** Yes: roadmap, vision, capabilities unlocked.

7. **Is this detailed enough?** Word count ~4500+. Meets template.

8. **Did I challenge assumptions?** Yes: 5 assumptions with verification steps.

### Quality Metrics Checklist

| Metric | Minimum | Pass? |
|--------|---------|-------|
| Total words | 3,000 | Yes (~4500) |
| Pre-thinking words | 500 | Yes |
| Acceptance criteria | 12 | Yes |
| Open questions | 10 | Yes |
| Risks identified | 8 | Yes |
| Similar features documented | 3 | Yes (5) |
| Related issues linked | 2 | Yes |
| Assumptions documented | 5 | Yes |

---

## After Issue Creation

**Immediate next steps:**
1. Share issue with stakeholder for 5-minute validation (KPI set, calendar metric)
2. Get answers to important questions (#2, #6)
3. Schedule exploration session
4. Proceed to Phase 2: Explore Feature

**This issue becomes the foundation for exploration and planning.**
