# Project Context

> **Purpose:** High-level project state for AI tools. What exists, what patterns to follow, what constraints to respect.
> **For AI:** Reference with `@.cursor/context/project-context.md` to avoid reimplementing features or violating patterns.
> **Last Updated:** 2026-02-18
> **Location:** Single source of truth: `.cursor/context/`

---

## Project Overview

**Name:** WarpSense  
**Type:** Web App + API (monorepo: ESP32, iPad, Next.js, FastAPI)  
**Stack:** Next.js 16, React 19, TypeScript, Tailwind, Three.js | FastAPI, PostgreSQL, SQLAlchemy  
**Stage:** MVP (production deploy ready)

**Purpose:** Reliable MVP for recording, replaying, and scoring welding sessions. Safety-adjacent industrial welding system — correctness, determinism, and explainability prioritized.

**Current State:**
- ✅ Session replay (heatmap, angle, 3D torch visualization)
- ✅ Session comparison (A | Delta | B)
- ✅ Rule-based scoring
- ✅ Mock data + backend seed
- ✅ Browser-only demo mode at `/demo` (zero backend/DB)
- ✅ One-click Docker deploy (`./deploy.sh`)
- ✅ Premium Apple-inspired landing (route groups `(marketing)` / `(app)`)
- ✅ WebGL context-loss hardening (ESLint rule, overlay, constants)
- ✅ Investor-grade demo (guided tour, team dashboard, Seagull path)
- ✅ WWAD macro-analytics (supervisor dashboard, aggregate API, score_total persistence)
- 🔄 Remote deploy validation
- 📋 Streaming/pagination for sessions >10k frames

---

## Architecture

### System Pattern
Client-Server (monorepo)

```
Frontend (Next.js) → Backend (FastAPI) → PostgreSQL
ESP32 Sensors → Backend (bulk ingest)
```

**Key Decisions:**
- **Heatmap = CSS Grid (not Recharts ScatterChart):** ScatterChart overlaps at 7500 points; CSS grid handles unlimited points cleanly
- **Playback = setInterval (not RAF):** RAF runs at 60fps; setInterval at 100fps shows every 10ms frame
- **Status Flow = One-Way (RECORDING→COMPLETE→ARCHIVED):** Prevents data corruption
- **Heat Dissipation = Backend Only:** Thermal frames sparse; backend has full context; frontend would need complex state
- **Temperature Colors = 8 Anchors:** Blue→purple gradient (0–500°C), WarpSense theme

### Tech Stack

**Frontend:** Next.js 16, React 19, TypeScript, Tailwind, Three.js/react-three-fiber, Recharts, Framer Motion  
**Backend:** FastAPI, Python, REST  
**Database:** PostgreSQL, SQLAlchemy  
**Infrastructure:** Docker Compose, DigitalOcean, monorepo

**Critical Dependencies:**
- `three`, `@react-three/fiber` (~500KB) — 3D torch visualization
- `recharts` — angle line chart
- snake_case everywhere (backend JSON → frontend types, no conversion layer)

---

## Implemented Features

> **AI Rule:** Don't reimplement what's listed here.

### 3D Visualization (TorchViz3D, TorchWithHeatmap3D)
**Status:** ✅  
**What:** TorchViz3D = 3D torch + weld pool. TorchWithHeatmap3D = unified torch + thermally-colored metal (5–10°C visible steps).  
**Location:** `TorchViz3D.tsx`, `TorchWithHeatmap3D.tsx`, `ThermalPlate.tsx`  
**Pattern:** Dynamic import with `ssr: false`, max 2 Canvas per page, `webglcontextlost` handler + overlay  
**Enforcement:** ESLint rule counts TorchViz3D and TorchWithHeatmap3D; max 2 per page  
**Integration:** Replay and demo use TorchWithHeatmap3D (thermal on metal). HeatmapPlate3D deprecated in replay; kept for dev/standalone.  
**See:** `documentation/WEBGL_CONTEXT_LOSS.md`, `.cursor/plans/unified-torch-heatmap-replay-plan.md`

### Replay System
**Status:** ✅  
**What:** Heatmap, TorchAngleGraph, TorchViz3D driven by shared playback timestamp  
**State:** Timeline state (`currentTimestamp`, `isPlaying`, etc.)  
**Location:** `app/replay/[sessionId]/page.tsx`  
**Integration:** `getFrameAtTimestamp`, `extractHeatmapData`, `extractAngleData`, `extractCenterTemperatureWithCarryForward`

### Heatmap
**Status:** ✅  
**What:** CSS Grid heatmap (unlimited points; Recharts ScatterChart fails at 7500+)  
**Location:** `components/welding/HeatMap.tsx`  
**Data:** `utils/heatmapData.ts` — `extractHeatmapData(thermal_frames)`

### HeatmapPlate3D (3D Warped Plate)
**Status:** ✅  
**What:** 3D metal plate with thermal vertex displacement and temp→color gradient. Replaces HeatMap on replay page when `thermal_frames.length > 0`. Uses 5-point IDW interpolation, custom GLSL shaders, OrbitControls.  
**Location:** `components/welding/HeatmapPlate3D.tsx`  
**Data:** `utils/thermalInterpolation.ts` — `interpolateThermalGrid`; `frameUtils.getFrameAtTimestamp`  
**Canvas count:** Replay = 2 TorchViz3D + 1 HeatmapPlate3D = 3 (see `constants/webgl.ts` MAX_CANVAS_PER_PAGE)  
**Fallback:** When no thermal data, HeatMap with heatmapData shown instead.

### Session Comparison
**Status:** ✅  
**What:** A | Delta | B view, `compareSessions()` → `FrameDelta[]`  
**Location:** `app/compare/[sessionIdA]/[sessionIdB]/page.tsx`, `hooks/useSessionComparison.ts`

### Rule-Based Scoring
**Status:** ✅  
**What:** `ScorePanel(sessionId)` fetches `GET /api/sessions/:id/score`  
**Backend:** Rule-based, stateless, reproducible

### Browser-Only Demo Mode
**Status:** ✅  
**What:** `/demo` — 100% in-browser synthesized welding data, zero backend/DB  
**Location:** `app/demo/`, `lib/demo-data.ts`, `DemoLayoutClient.tsx`  
**Contract:** Produces `Session` with `Frame[]` matching `extractHeatmapData`, `extractAngleData`, `extractCenterTemperatureWithCarryForward`  
**Deferral:** `generateExpertSession()` / `generateNoviceSession()` in `useEffect` to avoid blocking main thread on mount

### Investor-Grade Demo (Guided Tour + Team Path)
**Status:** ✅  
**What:** Guided tour overlay on `/demo` (expert vs novice narrative), "See Team Management" CTA → `/demo/team`, browser-only team dashboard with welder cards and individual reports  
**Location:** `components/demo/DemoTour.tsx`, `lib/demo-tour-config.ts`, `lib/demo-config.ts`, `lib/seagull-demo-data.ts`, `app/demo/team/`  
**Pattern:** Custom overlay (z-[200], isolate) above 3D; config-driven steps; debounced scrub to `NOVICE_SPIKE_MS` (2400); no third-party tour lib  
**Integration:** DemoTour → `onStepEnter` scrubs playback; CTA dismisses tour before navigate; `getDemoTeamData(welderId)` → HeatMap, FeedbackPanel, LineChart; PlaceholderHeatMap when no thermal data  
**Data:** `createMockScore()`, `getDemoTeamData()` — mock scores (expert 94, novice 42) match `generateAIFeedback` contract; `DEMO_WELDERS` from demo-config  
**AppNav:** Team link → `/seagull`; Demo CTA → `/demo/team`

### Premium Landing (Marketing)
**Status:** ✅  
**What:** Apple-inspired landing at `/` (canonical) and `/landing` (re-export)  
**Location:** `app/(marketing)/page.tsx`, `app/landing/page.tsx`  
**Layout:** Route groups `(marketing)` and `(app)` — layout controls nav visibility; no conditional `isLanding` in components  
**Integration:** `AppNav.tsx` shows/hides based on layout; `(app)` has dashboard, replay, compare, demo

### One-Click Docker Deploy
**Status:** ✅  
**What:** `./deploy.sh` — PostgreSQL, backend, frontend in one command  
**Flow:** Port check → generate secrets → build → up → health wait → optional seed  
**Files:** `deploy.sh`, `docker-compose.yml`, `DEPLOY.md`, `backend/Dockerfile`, `my-app/Dockerfile`  
**Note:** `NEXT_PUBLIC_API_URL` is build-time; remote deploy requires rebuild with server IP

### WarpSense Micro-Feedback (Phase 1)
**Status:** ✅  
**What:** Frame-level actionable guidance for welders — angle drift and thermal symmetry alerts on replay. Client-side `generateMicroFeedback(frames)` → MicroFeedbackItem[]; FeedbackPanel + TimelineMarkers for click-to-scrub.  
**Location:** `lib/micro-feedback.ts`, `types/micro-feedback.ts`, `components/welding/FeedbackPanel.tsx`, `components/welding/TimelineMarkers.tsx`  
**Thresholds:** Angle: target 45°, warning ±5°, critical ±15°. Thermal: max(|N-S|, |E-W|) ≥ 20°C. Cap 50 items per type.  
**Guards:** Skips frames with missing cardinal readings (never uses DEFAULT_AMBIENT for variance); try-catch wrapper; 10k frames < 200ms.  
**Integration:** Replay page — useMemo generateMicroFeedback; FeedbackPanel with frames + onFrameSelect; TimelineMarkers overlay.  
**See:** `.cursor/issues/warpsense-micro-feedback-feature.md`, `.cursor/plans/warpsense-micro-feedback-implementation-plan.md`

### WWAD Macro-Analytics (Supervisor Dashboard)
**Status:** ✅  
**What:** Team-level KPIs, trend chart, calendar heatmap, CSV export — multi-session aggregate analytics for supervisors. Orthogonal to per-frame/micro-feedback; uses metadata + score_total only (no frames loaded).  
**Location:** `app/(app)/supervisor/page.tsx`, `components/dashboard/CalendarHeatmap.tsx`, `lib/aggregate-transform.ts`, `lib/export.ts`, `types/aggregate.ts` | `backend/routes/aggregate.py`, `backend/services/aggregate_service.py`, `backend/models/aggregate.py`  
**Pattern:** Reuses DashboardLayout, MetricCard, ChartCard; route `/supervisor`; date presets (7/30 days); lazy score_total persistence on GET /score; backfill script for existing sessions.  
**Orthogonality:** No imports from TorchViz3D, HeatmapPlate3D, HeatMap, FeedbackPanel — ESLint restricted for supervisor paths.  
**Integration:** `fetchAggregateKPIs()` → `aggregateToDashboardData()` → DashboardLayout + CalendarHeatmap; Export CSV uses `generateCSV`, `downloadCSV`; `sessions_truncated` alert when >1000 sessions.  
**See:** `.cursor/plans/wwad-macro-analytics-implementation-plan.md`, `.cursor/explore/wwad-macro-analytics-key-facts.md`

### Data Processing / Utilities
**Status:** ✅  
**Utilities:**  
- `extractCenterTemperature(frame)` — `utils/frameUtils.ts`  
- `extractCenterTemperatureWithCarryForward()` — thermal continuity for 3D  
- `getFrameAtTimestamp(frames, timestamp)`  
- `filterThermalFrames(frames)`  
- `compareSessions(sessionA, sessionB)`  
- `computeMinMaxTemp(points, fallbackMin?, fallbackMax?)` — `utils/heatmapTempRange.ts` — min/max from heatmap points with fallback; handles empty/null/NaN
- `generateMicroFeedback(frames)` — `lib/micro-feedback.ts` — angle drift + thermal symmetry; returns MicroFeedbackItem[] sorted by frameIndex
- `aggregateToDashboardData(res)` — `lib/aggregate-transform.ts` — AggregateKPIResponse → DashboardData (metrics + charts)
- `generateCSV(rows)`, `downloadCSV(filename, csv)` — `lib/export.ts` — CSV export for supervisor reports

---

## Data Models

### Session
```typescript
{ session_id, frames[], status, frame_count, start_time, weld_type, score_total? }
```
**score_total:** Precomputed total score (persisted on first GET /score for COMPLETE sessions); backfilled via `backfill_score_total.py`.  
**Used by:** Replay, Compare, ScorePanel, Demo, aggregate API  
**Flow:** API / mock / demo-data → `Session` → extractors → components

### Frame
```typescript
{ timestamp_ms, volts?, amps?, angle_degrees?, thermal_snapshots[], heat_dissipation_rate_celsius_per_sec?, has_thermal_data }
```
**Sparse data:** Thermal at 5 Hz (every 100ms); use `extractCenterTemperatureWithCarryForward` for 3D color continuity

### ThermalSnapshot
```typescript
{ distance_mm, readings[] }  // readings: center, north, south, east, west (5)
```

### FrameDelta
All Frame fields as `_delta` (sessionA - sessionB), `thermal_deltas[]`

---

## Patterns

> **AI Rule:** Follow these for consistency.

### Frame Resolution
**Use when:** Finding frame for a given playback timestamp  
**How:** Exact match, else nearest before timestamp, else first frame  
**Location:** `getFrameAtTimestamp()` in `utils/frameUtils.ts`

### SSR Safety
**Use when:** Browser-only components (WebGL, Canvas)  
**How:** `dynamic(() => import('...'), { ssr: false, loading: () => <div>Loading…</div> })`  
**Why:** Prevents Next.js SSR errors; WebGL requires browser

### Thermal Carry-Forward
**Use when:** Sparse thermal data in 3D color  
**How:** `extractCenterTemperatureWithCarryForward()` — walks backwards for last known temp  
**Why:** Avoids flicker when thermal_snapshots missing on sensor-only frames

### WebGL Context Limits
**Use when:** Adding 3D/Canvas components  
**How:** Max 2 Canvas per page (`MAX_TORCHVIZ3D_PER_PAGE` in `constants/webgl.ts`); add `webglcontextlost` listener; show "Refresh to restore" overlay  
**Enforcement:** ESLint rule `max-torchviz/max-torchviz3d-per-page`; tests assert ≤2 instances  
**Why:** Browsers limit ~8–16 WebGL contexts per tab  
**See:** `LEARNING_LOG.md`, `documentation/WEBGL_CONTEXT_LOSS.md`

### Visual Consistency (Temperature)
**Use when:** Color-based temperature displays  
**How:** 8 thermal anchors, blue→purple gradient (0–500°C). Blue/purple-only palette; no rainbow colors.

### Demo Config (Single Source of Truth)
**Use when:** Adding demo thresholds, mock scores, or tour values
**How:** All values in `lib/demo-config.ts` — `NOVICE_SPIKE_MS`, `MOCK_EXPERT_SCORE_VALUE`, `MOCK_NOVICE_FAILED_RULES`, `DEMO_WELDERS`
**Why:** No magic numbers elsewhere; mock and real AI logic share same thresholds

### Demo Tour Overlay
**Use when:** Guided narrative on /demo
**How:** `DemoTour` with `DEMO_TOUR_STEPS` from `demo-tour-config`; `onStepEnter` debounced (150ms) for scrub; z-[200] + isolate above 3D
**Why:** Custom overlay avoids third-party deps; scrub syncs narrative to playback

### Route Group Layout
**Use when:** Different layouts (marketing vs app) without conditional logic in components  
**How:** `(marketing)` and `(app)` route groups; each has its own layout; layout controls nav visibility  
**Why:** No `isLanding` branching in AppNav; structure drives behavior

### WWAD Orthogonality
**Use when:** Adding supervisor or aggregate-related code  
**How:** Zero imports from TorchViz3D, HeatmapPlate3D, HeatMap (thermal), FeedbackPanel, TorchAngleGraph in `supervisor/`, `CalendarHeatmap`, `aggregate-transform.ts`  
**Why:** Macro-analytics is orthogonal to micro-feedback; avoids coupling and bundle bloat  
**Enforcement:** ESLint `no-restricted-imports` for supervisor paths

### Env Fallback with Trim
**Use when:** Environment variables that may be empty string  
**How:** `process.env.X?.trim() || '/fallback'` — empty string yields fallback  
**Why:** `NEXT_PUBLIC_X=""` yields `""` not `undefined`

---

## Integration Points

> **AI Rule:** Use these, don't recreate.

### Backend API
```
GET  /api/sessions/:id?limit=2000&include_thermal=true
POST /api/sessions/:id/frames  (1000-5000 Frame[] per request)
GET  /api/sessions/:id/score   → SessionScore (persists score_total when computed)
GET  /api/sessions/aggregate?date_start=&date_end=&include_sessions= → AggregateKPIResponse
```

### Aggregate Data Flow (WWAD)
```
fetchAggregateKPIs({ date_start, date_end }) → AggregateKPIResponse
  → aggregateToDashboardData(res) → DashboardData
  → DashboardLayout(metrics, charts) + CalendarHeatmap(calendar)
Export: include_sessions=true → sessions[] → generateCSV → downloadCSV
```

### Frame Data Flow
```
fetchSession(id) → Session
  → useFrameData(frames) → thermal_frames
  → extractHeatmapData(thermal_frames) → HeatmapData
  → extractAngleData(frames) → AngleData
  → thermal_frames.length > 0
      ? <HeatmapPlate3D frames={thermal_frames} activeTimestamp={…} />
      : <HeatMap data={heatmapData} />
  → <TorchAngleGraph data={angleData} />
  → TorchViz3D(angle, temp)
```

### Key Components
- **FeedbackPanel(items, frames?, onFrameSelect?)** — AI + micro-feedback; session-level (WelderReport) or frame-level (Replay)
- **CalendarHeatmap(data, title?)** — GitHub-style activity grid; sessions per day (supervisor dashboard)
- **TimelineMarkers(items, frames, firstTimestamp, lastTimestamp, onFrameSelect)** — Micro-feedback markers on replay timeline
- **TorchViz3D(angle, temp, label)** — 3D torch + weld pool (dynamic import required)
- **HeatmapPlate3D(frames, activeTimestamp, maxTemp, plateSize)** — 3D warped plate (replaces HeatMap when thermal; dynamic import required)
- **HeatMap(data, activeTimestamp)** — CSS grid heatmap
- **TorchAngleGraph(data, active)** — Recharts line chart
- **ScorePanel(sessionId)** — Rule-based scoring display

---

## Constraints

> **AI Rule:** Respect these, don't work around them.

### Data Integrity
- **Append-only:** Raw sensor data never edited; only new frames added
- **Backend is source of truth:** Heat dissipation calculated once at ingestion
- **snake_case everywhere:** No conversion layer
- **Never mutate raw data:** All extraction/transformation is pure functions

### Timing & Limits
- **Frame interval:** 10ms (100 Hz)
- **Bulk ingestion:** 1000–5000 frames per POST
- **Thermal sampling:** Sparse (5 Hz / every 100ms)
- **Session max:** 30,000 frames (5 min at 100 Hz)

### SSR Limitations
**What:** WebGL/Canvas requires browser  
**Handle:** ✅ `dynamic(..., { ssr: false })` | ❌ Direct import  
**Affects:** TorchViz3D, any Canvas/WebGL

### Sparse Thermal Data
**What:** Thermal_snapshots only on every 10th frame  
**Handle:** `extractCenterTemperatureWithCarryForward()`  
**Affects:** 3D torch color

### Bundle Size
**What:** Keep feature bundles <600KB gzipped  
**Current:** Three.js ~500KB acceptable for demo  
**Future:** Lazy load for production

### WebGL Context Limit
**What:** ~8–16 WebGL contexts per tab  
**Handle:** Max 2 TorchViz3D + 1 HeatmapPlate3D = 3 Canvas on replay; context-loss overlay  
**Affects:** TorchViz3D, HeatmapPlate3D, any 3D/Canvas features  
**See:** `LEARNING_LOG.md`

### Aggregate Limits
**What:** Date range and export caps for supervisor dashboard  
**Handle:** Backend enforces date range ≤ 90 days; sessions list capped at 1000; `sessions_truncated` flag when truncated  
**Affects:** /supervisor, Export CSV; UI must show prominent alert when truncated

---

## File Structure

```
my-app/
  app/                      # Pages, routes
    (marketing)/            # Landing (/), terms, privacy — no nav
    (app)/                  # Dashboard
      supervisor/           # WWAD supervisor dashboard (macro-analytics)
    landing/                # Re-export of (marketing)/page (backwards compat)
    replay/[sessionId]/     # Replay page
    compare/[sessionIdA]/[sessionIdB]/  # Compare page
    demo/                   # Browser-only demo (own layout)
      team/                 # Team dashboard + welder reports (browser-only)
    seagull/                # Seagull pilot (API-dependent team path)
    dev/torch-viz/          # Dev 3D test page
    api/                    # API routes
  components/
    demo/                   # DemoTour (guided tour overlay)
    dashboard/              # DashboardLayout, MetricCard, CalendarHeatmap (WWAD)
    welding/                # TorchViz3D, HeatMap, TorchAngleGraph
    ui/                     # Shared UI
  lib/
    api.ts                  # API client
    demo-data.ts            # Browser-only demo synthesis
    demo-config.ts          # Demo thresholds, NOVICE_SPIKE_MS, DEMO_WELDERS (single source of truth)
    demo-tour-config.ts     # Tour step definitions for DemoTour
    seagull-demo-data.ts    # createMockScore, getDemoTeamData (browser-only team path)
    aggregate-transform.ts  # aggregateToDashboardData (AggregateKPIResponse → DashboardData)
    export.ts               # generateCSV, downloadCSV (supervisor export)
  utils/
    frameUtils.ts           # getFrameAtTimestamp, thermal helpers
    heatmapData.ts          # extractHeatmapData, tempToColorRange
    heatmapTempRange.ts     # computeMinMaxTemp
    thermalInterpolation.ts # interpolateThermalGrid, sanitizeTemp (5-point IDW)
  constants/
    webgl.ts                # MAX_TORCHVIZ3D_PER_PAGE
  types/                    # session, frame, thermal, aggregate
  hooks/
    useSessionComparison.ts
  eslint-rules/
    max-torchviz3d-per-page.cjs  # Enforces ≤2 TorchViz3D per page
backend/
  routes/sessions.py
  routes/aggregate.py         # GET /api/sessions/aggregate
  services/thermal_service.py
  services/aggregate_service.py
  models/aggregate.py        # AggregateKPIResponse Pydantic
  scripts/backfill_score_total.py
  scripts/verify_backfill.py
  init-db.sql
  scripts/seed_demo_data.py
.cursor/context/            # Single source of truth — project context, architecture docs
```

**Key Files:**
- `types/session.ts`, `types/frame.ts`, `types/thermal.ts`, `types/aggregate.ts` — Data models
- `lib/api.ts` — API client
- `lib/demo-config.ts` — Demo thresholds (no magic numbers elsewhere)
- `lib/seagull-demo-data.ts` — Mock team data for /demo/team
- `utils/frameUtils.ts` — Frame utilities
- `utils/heatmapData.ts` — Heatmap extraction
- `lib/aggregate-transform.ts` — AggregateKPIResponse → DashboardData
- `lib/export.ts` — CSV export (supervisor)
- `constants/webgl.ts` — WebGL limit constant (shared by ESLint, tests)
- `.cursor/context/context-tech-stack-mvp-architecture.md` — Detailed architecture
- `LEARNING_LOG.md` — Past mistakes (e.g. WebGL context loss)

---

## API Contracts

### GET /api/sessions/:id
**Purpose:** Fetch session with frames (optionally thermal)  
**Query:** `?limit=2000&include_thermal=true`  
**Response:** `{ session_id, frames[], status, ... }`  
**Used by:** Replay, Compare, ScorePanel

### POST /api/sessions/:id/frames
**Purpose:** Bulk ingest frames  
**Request:** `Frame[]` (1000–5000 per request)  
**Response:** Session updated  
**Constraint:** 1000–5000 frames per POST

### GET /api/sessions/:id/score
**Purpose:** Rule-based session score  
**Response:** `SessionScore`  
**Persistence:** Lazy write-through: if COMPLETE, has frames, and score_total is null, persists score_total to session row  
**Used by:** ScorePanel

### GET /api/sessions/aggregate
**Purpose:** Aggregate KPIs for supervisor dashboard  
**Query:** `?date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&include_sessions=false` (UTC; date_end inclusive; max 90 days)  
**Response:** `{ kpis: { avg_score, session_count, top_performer, rework_count }, trend, calendar, sessions?, sessions_truncated }`  
**Used by:** Supervisor page; no frames loaded (metadata + score_total only)

---

## Component APIs

### TorchViz3D
**Purpose:** 3D torch + weld pool  
**Props:** `angle: number`, `temp: number`, `label?: string`  
**Location:** `components/welding/TorchViz3D.tsx`  
**Requirements:** Must use dynamic import (`ssr: false`); 1–2 Canvas max per page

### HeatMap
**Purpose:** CSS grid thermal heatmap  
**Props:** `data: HeatmapData`, `activeTimestamp?: number`  
**Location:** `components/welding/HeatMap.tsx`

### TorchAngleGraph
**Purpose:** Recharts angle line chart  
**Props:** `data: AngleData`, `active?: number`  
**Location:** `components/welding/TorchAngleGraph.tsx`

### DemoTour
**Purpose:** Guided tour overlay for investor narrative  
**Props:** `steps: TourStep[]`, `onStepEnter?`, `onComplete?`, `onSkip?`, `onStepLog?`  
**Location:** `components/demo/DemoTour.tsx`  
**Requirements:** z-[200] isolate; focus trap; aria-modal, role="dialog"; Escape to skip

### CalendarHeatmap
**Purpose:** GitHub-style sessions-per-day activity grid (WWAD; not thermal heatmap)  
**Props:** `data: { date: string; value: number }[]`, `title?`, `emptyMessage?`, `weeksToShow?`  
**Location:** `components/dashboard/CalendarHeatmap.tsx`  
**Integration:** Supervisor page; data from aggregate API calendar

---

## Not Implemented

> **AI Rule:** Don't assume these exist.

### Streaming/pagination for large sessions
**Status:** 📋 Planned  
**What:** Sessions >10k frames need streaming or pagination  
**Why not yet:** MVP focused on shorter sessions

### Python parity for demo-data
**Status:** 💡 Idea  
**What:** Align `lib/demo-data.ts` thermal model with `backend/data/mock_sessions.py`  
**Why not yet:** Deferred follow-up

---

## Explicitly Rejected

> **AI Rule:** Don't suggest these.

### Recharts ScatterChart for heatmap
**What:** Using scatter chart for 7500+ thermal points  
**Why rejected:** Overlaps; unreadable  
**Alternative:** CSS Grid heatmap

### requestAnimationFrame for playback
**What:** 60fps-driven playback  
**Why rejected:** Skips 10ms frames; not 1:1 with data  
**Alternative:** setInterval at 100fps

### Frontend heat dissipation calc
**What:** Compute heat_dissipation_rate_celsius_per_sec in frontend  
**Why rejected:** Sparse thermal; backend has full context  
**Alternative:** Use pre-calculated `frame.heat_dissipation_rate_celsius_per_sec`

### Multiple Canvases per page (6+)
**What:** 6 TorchViz3D instances on one page  
**Why rejected:** Exhausts WebGL context limit → white screen  
**Alternative:** 1–2 Canvas max; scissor/multi-view if needed  
**See:** `LEARNING_LOG.md`

---

## AI Prompting Patterns

### Adding Feature
```
@.cursor/context/project-context.md — Check if exists
@LEARNING_LOG.md — Check past issues (esp. WebGL/3D)

Implement [feature] following:
- Pattern: [from CONTEXT]
- Integration: [from CONTEXT]
- Constraints: [from CONTEXT]
```

### Debugging
```
@.cursor/context/project-context.md — [relevant section]
@LEARNING_LOG.md — Similar issues

Expected: [based on CONTEXT]
Actual: [what's happening]
```

### 3D / WebGL
```
Check LEARNING_LOG.md and documentation/WEBGL_CONTEXT_LOSS.md.
Use at most 1–2 Canvas instances per page. Add webglcontextlost listeners
and show "Refresh to restore" overlay.
```

---

## Quick Checklist

Before prompting AI:
- [ ] Checked .cursor/context/ for existing implementation
- [ ] Reviewed patterns to follow
- [ ] Noted integration points
- [ ] Identified constraints
- [ ] Checked LEARNING_LOG.md

---

## Related Docs

| File | Purpose |
|------|---------|
| `LEARNING_LOG.md` | Mistakes & solutions (esp. WebGL context loss) |
| `.cursor/context/context-tech-stack-mvp-architecture.md` | Detailed architecture, file map |
| `documentation/WEBGL_CONTEXT_LOSS.md` | WebGL context loss reference |
| `documentation/MOCK_DATA_SEEDING_ERROR.md` | Seed/migration troubleshooting |
| `DEPLOY.md` | One-click Docker deploy instructions |
| `.cursorrules` | AI config, data integrity contract |
| `README.md` | Setup, quick start |
| `.cursor/plans/wwad-macro-analytics-implementation-plan.md` | WWAD implementation plan |
| `.cursor/explore/wwad-macro-analytics-key-facts.md` | WWAD key files, architecture, risks |

---

**Maintenance:** Update after features, weekly review, monthly validation.

**CONTEXT UPDATE REQUIREMENTS:**
- Update .cursor/context/project-context.md with new features/patterns
- Document new components/utilities created
- Add new API endpoints or data models
- Update architecture decisions if changed
- Add new constraints or limitations discovered
- Update file structure if new directories added
- Document integration patterns used
- Add to "Implemented Features" section

Keep .cursor/context/ as the single source of truth. Be thorough.
