# Project Context — Shipyard Welding MVP (WarpSense)

> **Purpose:** Single source of truth for AI tools. What exists, what patterns to follow, what constraints to respect.  
> **For AI:** Reference `@.cursor/context/project-context.md` to avoid reimplementing features or violating patterns.  
> **Last Updated:** 2026-03-05

---

## 1. Project Overview

**Name:** WarpSense (Shipyard Welding MVP)  
**Type:** Full-stack web app  
**Stack:** Next.js, FastAPI, PostgreSQL, SQLAlchemy, React, TypeScript, Tailwind, Three.js  
**Stage:** MVP

**Purpose:** Safety-adjacent industrial welding quality intelligence: recording, replaying, and scoring welding sessions with thermal profiles, torch angle analysis, warp prediction, and AI feedback.

**Current State:**
- ✅ Session replay, scoring, warp-risk, AI narrative, trajectory, benchmarks, coaching, certification
- ✅ Compare sessions (side-by-side heatmaps, delta, 3D torch, alert feed)
- ✅ Multi-site org hierarchy, supervisor scoping
- ✅ iPad companion PWA (/live)
- ✅ System 1 rule-based edge alerts (3 proxy + 7 defect rules), Aluminum mock sessions
- ✅ Full-stack smoke tests
- ✅ Windowed WQI scoring (extract_features_for_frames, score_frames_windowed, wqi_timeline/mean/median/min/max/trend)
- ✅ Demo page API-wired (fetchSession, fetchSessionAlerts, useSessionComparison; no 3D)
- ✅ Panel Readiness dashboard (6 panels, stats bar, Expert Benchmark; PANEL_MOCK_SCORES fallback when unseeded; Promise.allSettled + timeout)
- 🔄 Post–Batch 4 verification
- 📋 ESP32 sensor integration, production deployment

---

## 2. Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js, React)                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /demo              Redirect to default pair → /demo/[A]/[B] (investor UX)        │
│  /demo/[A]/[B]     Investor comparison: WQI gauges, sparklines, alert feed, playback (no 3D) │
│  /dashboard        Panel Readiness: 6 panel cards, stats bar, filter tabs, Expert Benchmark  │
│  /seagull           Seagull Team dashboard (cards from WELDER_ARCHETYPES)        │
│  /seagull/welder/[id]  Welder report: ReportLayout, NarrativePanel, PDF download │
│  /replay/[id]       Replay + WarpRiskGauge                                       │
│  /compare           Compare landing: choose two session IDs → /compare/A/B       │
│  /compare/[A]/[B]   Side-by-side heatmaps, delta column, 3D torch, alert feed     │
│  /supervisor        WWAD macro-analytics (team KPIs, heatmap, CSV export)        │
│  /live              iPad companion PWA (warp-risk polling, angle indicator)     │
│  /realtime          Realtime alerts demo                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI, PostgreSQL)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /api/sessions/:id, /score, /warp-risk, /narrative, /aggregate, :id/alerts        │
│  /api/sites, /api/welders/:id/trajectory, /benchmarks, /coaching-plan, /cert    │
│  /api/dev/seed-mock-sessions  (dev only)                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ESP32 Sensors → Backend (bulk ingest) | simulate_realtime → AlertEngine → WS    │
│  ML: prediction_service (ONNX), narrative_service (Anthropic)                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Meaning |
|-----------|---------|
| Append-only | Raw sensor data never edited; only new frames added |
| Single source of truth | Backend calculates once; frontend displays |
| Exact replays | Frontend shows exactly what happened — no guessing |
| snake_case everywhere | Backend JSON → frontend types; no conversion layer |
| Never mutate raw data | Extraction/transformation are pure functions |

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **3D / Charts** | Three.js, @react-three/fiber, @react-three/drei, Recharts |
| **Backend** | Python, FastAPI, REST |
| **Database** | PostgreSQL, SQLAlchemy ORM |
| **Infrastructure** | Docker Compose, DigitalOcean, monorepo |

**Critical Constraints:**
- Frame interval: 10 ms (100 Hz) | Bulk: 1000–5000 frames per POST | Thermal: Sparse (5 Hz)
- WebGL: Max 1–2 Canvas per page; context-loss handling required

---

## 3. Implemented Features

> **AI Rule:** Don't reimplement what's listed here.

### Session Replay
**Status:** ✅  
**What:** Heatmap, TorchAngleGraph, 3D torch + thermally-colored metal driven by shared playback timestamp.  
**Location:** `app/replay/[sessionId]/page.tsx`, `HeatMap.tsx`, `TorchWithHeatmap3D.tsx`, `HeatmapPlate3D.tsx`  
**Integration:** `fetchSession`, `useFrameData`, `extractHeatmapData`, `extractAngleData`

### WeldTrail & 3D Torch Visualization
**Status:** ✅  
**What:** `WeldTrail` renders a colored point cloud on the workpiece showing torch path up to `activeTimestamp`. Arc-active frames only (volts/amps > 1). Uses cumulative distance for X-axis; falls back to timestamp-linear when `travel_speed_mm_per_min` is null. Color: green <200°C, orange <400°C, red ≥400°C.

**WeldTrail location:** `components/welding/WeldTrail.tsx` — `computeTrailData` (exported for tests), `isArcActive` from frameUtils. Pre-allocates 10000 points.

**TorchWithHeatmap3D:** Unified 3D scene (torch + thermal metal + WeldTrail). Used on **replay** and **compare** pages. Imports `TorchSceneContent` for torch geometry + lights; WeldTrail stays in TorchWithHeatmap3D (not extracted). Dynamic import with `ssr: false`.

**3D pages:** Replay (1× TorchWithHeatmap3D), Compare (2× TorchWithHeatmap3D side-by-side), Demo (2× TorchWithHeatmap3D in circles). All use dynamic import with ssr: false.  
**Constraint:** Max 2 Canvas per page; see `WEBGL_CONTEXT_LOSS.md`.  
**Docs:** `docs/ISSUE_WELD_TRAIL.md`, `docs/ISSUE_COMPARE_3D_TORCH_VISUALIZATION.md`

### Rule-Based Scoring
**Status:** ✅  
**What:** Five base rules (angle, thermal, amps, volts, heat_diss); Aluminum adds travel_speed, cyclogram, porosity.  
**Location:** `backend/services/scoring_service.py`, `backend/scoring/rule_based.py`, `backend/routes/sessions.py`  
**Frontend:** `ScorePanel.tsx`

### AWS D1.2 Decomposed Scoring
**Status:** ✅  
**What:** Canonical session score as structured components (heat input, torch angle, arc termination, defect alerts, interpass). Replaces abstract single-number with `DecomposedSessionScore`. Each component has excursions (timestamp_ms, duration_ms), passed flag, 0–1 score, and summary.

**Components (critical = heat_input, arc_termination, defect_alerts):**
- **heat_input:** kJ/mm = (amps × volts × 60) / (travel_speed × 1000); excursion when outside WPS range (config/scoring_config.json).
- **torch_angle:** >20° or <0° (drag) → excursion.
- **arc_termination:** `no_crater_fill` → excursion.
- **defect_alerts:** Critical rules (porosity, crater_crack, burn_through, arc_instability) → fail. Warnings (oxide_inclusion) → score penalty only.
- **interpass:** Timer proxy — gap < interpass_min_ms → violation (no plate sensor).

**Location:** `backend/scoring/models.py`, `backend/scoring/config.py`, `backend/scoring/heat_input.py`, `backend/scoring/components.py`, `backend/scoring/scorer.py`, `backend/config/scoring_config.json`

**Integration:** `GET /api/sessions/{id}/score` returns `session_score` (DecomposedSessionScore); legacy `total` kept for backward compat. `_build_alerts_from_frames` in `scorer.py` is single source for routes, rescore endpoint, and backfill script — do not duplicate.

**Rescore:** `POST /api/sessions/{id}/rescore` recomputes and persists `score_total`. Backfill: `python -m scripts.rescore_all_sessions` (run from backend). TODO: add auth guard before QA.

**Tests:** `backend/tests/test_scoring.py` — heat input, torch angle, arc termination, defect (critical vs warning), interpass, weighted overall.

### Warp Prediction ML
**Status:** ✅  
**What:** ONNX-based logistic regression; 50-frame rolling window → warp probability + RiskLevel (ok/warning/critical).  
**Location:** `backend/services/prediction_service.py`, `backend/routes/predictions.py`, `backend/models/warp_model.onnx`  
**Frontend:** `WarpRiskGauge.tsx`

### AI Narrative Engine
**Status:** ✅  
**What:** Anthropic-powered 3-paragraph coaching report, cached in `session_narratives` table.  
**Location:** `backend/services/narrative_service.py`, `backend/routes/narratives.py`  
**Frontend:** `NarrativePanel.tsx`

### Longitudinal Skill Trajectory
**Status:** ✅  
**What:** Per-welder chronological score history, trend slope, projected next score.  
**Location:** `backend/services/trajectory_service.py`; route in `welders.py`  
**Frontend:** `TrajectoryChart.tsx`

### Defect Pattern Library
**Status:** ✅  
**What:** Session-scoped annotations + cross-session defect library with deep-links to replay.  
**Location:** `backend/routes/annotations.py`, `backend/models/annotation.py`  
**Frontend:** `AnnotationMarker.tsx`, `AddAnnotationPanel.tsx`, `/defects` page

### Comparative Benchmarking (Batch 3)
**Status:** ✅  
**What:** Per-metric percentile rankings vs all welders; supervisor Rankings tab.  
**Location:** `backend/services/benchmark_service.py`; route in `welders.py`  
**Frontend:** `BenchmarkPanel.tsx`, `RankingsTable.tsx`  
**Constants:** TOP_PERCENTILE=75, BOTTOM_PERCENTILE=25

### Automated Coaching Protocol (Batch 3)
**Status:** ✅  
**What:** 12 seeded drills; auto-assignment based on benchmark; progress tracking.  
**Location:** `backend/services/coaching_service.py`; routes in `welders.py`  
**Frontend:** `CoachingPlanPanel.tsx`  
**Hook:** Auto-assign triggered in GET /score when total < 60

### Operator Credentialing (Batch 3)
**Status:** ✅  
**What:** 3 cert standards; welder status: certified/on_track/at_risk/not_started.  
**Location:** `backend/services/cert_service.py`; route in `welders.py`  
**Frontend:** `CertificationCard.tsx`

### Multi-Site Org Hierarchy (Batch 4)
**Status:** ✅  
**What:** sites + teams tables; nullable team_id on sessions; aggregate filter params.  
**Location:** `backend/routes/sites.py`, `backend/models/site.py`  
**Frontend:** `SiteSelector.tsx` in supervisor page

### iPad Companion PWA (Batch 4)
**Status:** ✅  
**What:** `/live` page; polling warp-risk; 2D SVG angle indicator; no WebGL; PWA manifest.  
**Location:** `app/(app)/live/page.tsx`, `LiveAngleIndicator.tsx`, `LiveStatusLED.tsx`

### WWAD Macro-Analytics
**Status:** ✅  
**What:** Team KPIs, trend chart, calendar heatmap, CSV export; site/team filtering.  
**Location:** `app/(app)/supervisor/page.tsx`, `backend/routes/aggregate.py`

### Micro-Feedback
**Status:** ✅  
**What:** Frame-level angle drift and thermal symmetry alerts; click-to-scrub.  
**Location:** `lib/micro-feedback.ts`, `FeedbackPanel.tsx`, `TimelineMarkers.tsx`

### System 1 Rule-Based Edge Alerts (Proxy + Defect)
**Status:** ✅  
**What:** Eleven real-time rules (3 proxy + 7 defect) with time-based suppression, zero I/O in push_frame.  
**Location:** `backend/realtime/` (alert_engine.py, alert_models.py, frame_buffer.py), `backend/config/alert_thresholds.json`

**Proxy rules (1–3):** thermal NS asymmetry, travel angle deviation, speed drop.  
**Defect rules (4–11):** porosity (drag + low speed), arc instability (sustained low voltage), crater crack (abrupt arc termination), oxide inclusion (negative angle), undercut (high amps + high speed), lack of fusion (low amps OR high speed), burn-through (high amps + low speed).

**Buffers:** `VoltageSustainBuffer` (timestamp-based, handles None); `CurrentRampDownBuffer` (arc-on arming 500ms, ramp-down detection). Stateful buffers **reset when required sensor data is None** (e.g. crater buffer resets on amps=None) to avoid false positives from sensor dropout.

**Data flow:** `FrameInput` must include `volts`, `amps` for defect rules; `simulate_realtime` and `get_session_alerts` pass them from frame_data. If volts/amps is None: log warning once, skip that rule — never silently fail.

**Integration:** `/realtime` page, POST /internal/alert, WebSocket broadcast, `GET /api/sessions/{id}/alerts`, compare page alert feed.

**Tests:** `backend/tests/test_alert_engine.py` — 17 tests including defect rule unit tests. `config/alert_thresholds_defect_test.json` used for defect-only tests (angle_deviation_critical=90 to avoid rule 2 firing on negative angles).

### Aluminum Mock Sessions (Mock Data Foundation)
**Status:** ✅  
**What:** Physically realistic aluminum expert and novice mock data for alerts, scoring, and compare testing.

**Expert mock (`_generate_stitch_expert_frames`):**
- Current: 160–200A target, arc-start spike (20 frames, state machine), corner drop at stitch 3/6/9 (0.85× amps before clamp)
- Voltage: CTWD-driven (AL_VOLTS_NOMINAL + ctwd deviation × 0.8), clamp 20–24V
- Travel speed: Base 380–420 mm/min (AL_TRAVEL_SPEED_BASE_MEAN ± SIGMA), 15% decel at bead start/end and corners
- Heat input: `(amps × volts × 60) / (travel_speed × 1000)` kJ/mm; expect 0.5–0.9
- Arc termination: `crater_fill_present` on last arc-on frame before transition (retroactive via `prev_arc_active`)

**Novice mock (`_generate_continuous_novice_frames`):**
- Travel angle: can go negative (drag); drifts with occasional pull into drag
- Current: ratio-based — hot 185–200 (frames 0–7%), cold 145–155 (13–53%), base 165–180; do not clamp to AL_AMPS_MIN (cold mid is defect signature)
- Voltage: short-circuit 17–18.5V when `arc_active and i >= 200 and (i - 200) % 500 < 10`; AL_VOLTS_NOISE_NOVICE for normal variance
- Arc termination: `no_crater_fill` on last arc-on frame before transition

**Porosity:** `_porosity_probability` — returns nonzero only when `travel_angle < 0 AND speed < 250` mm/min. Replaces angle deviation + CTWD logic.

**Frame schema (models/frame.py):**
- `heat_input_kj_per_mm: Optional[float]` (ge=0)
- `arc_termination_type: Optional[Literal["crater_fill_present", "no_crater_fill"]]`
- `travel_angle_degrees` ge relaxed to -30

**Utilities:** Module-level `_with_termination(f, label)` — Pydantic v1/v2 compatible via `hasattr(f, "model_copy")`.

**Location:** `backend/data/mock_sessions.py`, `backend/models/frame.py`, `backend/scripts/verify_aluminum_mock.py`  
**Pattern:** `rng = random.Random(session_index * 42)` (expert) / `* 99` (novice); never global `random.seed()`  
**Verification:** `cd backend && python -m scripts.verify_aluminum_mock` — frame count, travel speed p2/p98, heat input 0.5–0.9, novice negative angle, porosity ≥3, voltage variance ratio >1.5

### Threshold Configuration
**Status:** ✅  
**What:** Admin CRUD for mig/tig/stick/flux_core/aluminum.  
**Location:** `backend/routes/thresholds.py`, `backend/services/threshold_service.py`  
**Frontend:** `app/admin/thresholds/page.tsx`, `AngleArcDiagram.tsx`

### Session Report Data Layer (Report Summary + Compliance UI)
**Status:** ✅  
**What:** WPS compliance summary for welder reports: heat input, travel angle excursions (run-length collapsed), arc termination quality, defect counts from alerts. Renders in compliance slot (first, before heatmaps) and PDF.

**Backend:**
- `GET /api/sessions/{session_id}/report-summary` — aggregates frames + alerts → ReportSummary; `Cache-Control: max-age=60`
- `backend/scoring/report_summary.py` — `compute_report_summary()`, `ExcursionEntry`, `ReportSummary`; run-length collapse for travel angle; process_type → config key mapping (aluminum → aluminum_spray; mig/None/unknown → aluminum_spray)
- `backend/config/report_thresholds.json` — WPS thresholds keyed by process (heat_input_min/max, travel_angle_threshold, travel_angle_nominal); cached per process
- `backend/services/alert_service.py` — `run_session_alerts(session_id, db)` — async; loads frames (limit 2000), runs AlertEngine; returns `list[AlertPayload]` (objects, not dicts); `get_session_alerts` and `get_report_summary` await it

**Frontend:**
- `lib/api.ts` — `fetchReportSummary(sessionId, signal?)` — GET report-summary
- `hooks/useReportSummary(sessionId)` — { data, loading, error }; AbortController cancels on unmount
- `types/report-summary.ts` — `ReportSummary`, `ExcursionEntry` (snake_case, matches backend)
- `ComplianceSummaryPanel` — four states: error, loading (skeleton), empty ("Compliance data unavailable"), data (Heat Input, Torch Angle, Arc Termination rows with pass/fail)
- `ExcursionLogTable` — columns Time (m:ss), Type, Value, Threshold, Duration, Notes; client-side sort by timestamp or type; empty: "No excursions — session within compliance"

**ReportLayout slot order:** compliance → heatmaps → feedback → progress → trajectory → benchmarks → coaching/certification → actions

**PDF:** Optional `reportSummary` in POST body; when absent, log warning and omit compliance section. Welder page passes `reportSummary: reportSummary ?? undefined` to PDF route.

**Tests:** `backend/tests/test_report_summary.py` — run-length collapse, process_type mapping, alert notes, empty frames. `ExcursionLogTable.test.tsx` — sort order, empty state.

### Welder Report & PDF Export
**Status:** ✅  
**What:** ReportLayout slots; PDF with chart capture, narrative, certifications, compliance (reportSummary).  
**Location:** `app/seagull/welder/[id]/page.tsx`, `ReportLayout.tsx`, `WelderReportPDF.tsx`, `app/api/welder-report-pdf/route.ts`

### Panel Readiness (Dashboard)
**Status:** ✅  
**What:** 6 panel cards with latest scores, stats bar (ACTIVE PANELS, AVG READINESS, JOINTS INSPECTED, SURVEYOR-READY), filter tabs (All Panels, Needs Inspection, Surveyor-Ready), Expert Benchmark card. Uses `Promise.allSettled` with per-fetch 5s timeout so one failure doesn't block others. Cards sorted by score ascending (worst first). Per-panel: inspection decision (clear/needs-dpi/needs-xray/needs-surveyor), risk level (green/amber/red), stage badge. Links: /replay/[sessionId], /seagull/welder/[panelId], /compare for non-expert.

**Data:** Static `PANELS` array in page; session IDs `sess_{panel.id}_{sessionCount}`. `PANEL_MOCK_SCORES` fallback map (panel ID → score) when API returns null (404/network) — panels show numeric scores without backend seed. Real API scores always win. Once panel sessions are seeded, delete `PANEL_MOCK_SCORES`.

**Patterns:** `fetchScoreWithTimeout` clears timer in `finally` to avoid leaks; logs via `logWarn` on failure. Fallback: `PANEL_MOCK_SCORES[f.panel.id] ?? null` in allSettled handler. `data-score-tier` on badges for test compatibility. Types: `Panel`, `PanelScoreResult` in `types/panel.ts`.

**Location:** `app/(app)/dashboard/page.tsx`  
**Tests:** `__tests__/app/(app)/dashboard/page.test.tsx` — panel assertions, sort by score, links.

### Investor Demo (API-Wired)
**Status:** ✅  
**What:** `/demo` redirects to `/demo/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001`. Full investor comparison UI at `/demo/[sessionIdA]/[sessionIdB]` driven by real APIs: `fetchSession`, `fetchSessionAlerts`, `useSessionComparison`.

**Features:** WQI gauges (session.score_total), parameter sparklines (heat, amp, angle from frames), two side-by-side circles with TorchWithHeatmap3D (Session A vs B thermal heatmaps), two-column alert feed (severity + message; no correction status until API supports it), playback bar with shared timeline.

**3D pattern:** TorchWithHeatmap3D MUST use `dynamic(..., { ssr: false })` — never static import. See LEARNING_LOG.md 2026-03-02. Camera: `cameraPosition={[-1.49, 1.21, -0.007]}`, `cameraFov={72}` for square viewports; `enableOrbitControls={true}` allows user drag.

**Data flow:** Promise.all sessions → Promise.allSettled alerts → useSessionComparison(sessionA, sessionB) → deltas at shared timestamps. Sparkline history via useMemo from comparison.deltas (avoids setState thrash). Current values from `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward`.

**Location:** `app/demo/page.tsx` (redirect), `app/demo/[sessionIdA]/[sessionIdB]/page.tsx`  
**Tests:** `app/__tests__/app/demo/page.test.tsx` — DemoPageInner, fetchSession/Alerts mocks, WQI -- when null, alerts unavailable, 404, no-overlap.  
**Related:** `lib/demo-config.ts`, `lib/seagull-demo-data.ts` (used by /demo/team and seagull flows; demo comparison page does not use them).

### Compare Sessions
**Status:** ✅  
**What:** Side-by-side comparison of two welding sessions: heatmaps, temperature delta (A − B), 3D torch visualization, and alert feed. Single shared timeline drives all columns.  
**Location:** `app/compare/page.tsx` (landing), `app/compare/[sessionIdA]/[sessionIdB]/page.tsx` (comparison view)  
**Pattern:** Timestamp-only alignment; no role assumption (caller picks A vs B)  
**Integration:** Replay page links via "Compare with another session" (pre-fills `sessionA`, optionally `sessionB` from `?compare=`)

**Routes:**
- `/compare` — Landing: two inputs + "Expert vs Novice" quick demo. Query params `sessionA`, `sessionB` pre-fill (e.g. from replay).
- `/compare/[sessionIdA]/[sessionIdB]` — Comparison view.

**Data flow:**
```
fetchSession(A), fetchSession(B) — parallel
fetchSessionAlerts(A), fetchSessionAlerts(B) — parallel (Promise.allSettled; failures isolated)
→ useSessionComparison(sessionA, sessionB) → deltas aligned by timestamp
→ extractHeatmapData(frameDataA/B), extractDeltaHeatmapData(deltas)
→ compareColorFn: shared min/max across A+B for heatmap scale
→ deltaTempToColor: blue (-50°C) → white (0) → purple (+50°C)
```

**Components:**
- `HeatMap` × 3 (Session A, Delta A−B, Session B) — shared `compareColorFn` for A/B; `deltaTempToColor` for delta.
- `TorchWithHeatmap3D` × 2 — side-by-side 3D torch + thermally colored metal.
- Alert feed: two columns, `visibleAlerts` filtered by `floorTs`; click → seek; critical → column flash (800ms).

**Hooks & utils:**
- `useSessionComparison` — memoized; mirrors `backend/services/comparison_service.py → compare_sessions`.
- `compareSessions`, `computeThermalDeltas` — pure; align by `timestamp_ms`; only shared timestamps produce deltas.
- `extractDeltaHeatmapData` — flattens `FrameDelta.thermal_deltas` to `HeatmapData` for grid.
- `useFrameData` — thermal frames for each session.

**Backend:**
- `GET /api/sessions/{session_id}/alerts` — runs frames through `AlertEngine`, returns `{ alerts: AlertPayload[] }`. Same 2000-frame cap as compare page.
- `backend/services/comparison_service.py` — `compare_sessions()`; frontend hook mirrors this logic (client-side for responsiveness).

**Types:** `FrameDelta`, `ThermalDelta`, `TemperatureDelta` in `types/comparison.ts` — mirrors backend Pydantic; snake_case; sign: positive = A hotter than B.

**Tests:** `app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx` (ComparePageInner), `hooks/useSessionComparison.test.ts`

---

## 4. Batch 3 — Dependency Architecture (Critical)

```
benchmark_service   ← coaching_service
        ↑                    ↑
   cert_service     (independent; NO imports from benchmark/coaching)
```

**Rules:**
- `benchmark_service` → MUST NEVER import `coaching_service`
- `coaching_service` → MAY import `benchmark_service` (lazy import inside `evaluate_progress()` only)
- `cert_service` → NO imports from `benchmark_service` or `coaching_service`
- `RankingsTable` → Import ONLY from `@/types/benchmark`, `@/types/shared`, `@/lib/api` — never from TorchViz3D, coaching, cert

---

## 5. Batch 4 — Agent Branch-and-Merge Pattern

**Shared files (NEVER edit directly in parallel):** `api.ts`, `welders.py`, `main.py`, `layout.tsx`, `next.config`  
**Fragment naming:** `<path-with-slashes-as-dots>.AGENT<N>.fragment` in `_fragments/`

| Agent | Scope |
|-------|-------|
| **Agent 1** | Multi-Site: sites.py, SiteSelector, aggregate site_id/team_id, fetchSites |
| **Agent 2** | iPad PWA: manifest, /live, LiveAngleIndicator, LiveStatusLED, fetchWarpRisk |
| **Agent 3** | Wire + Harden: coaching hook, ReportLayout audit, full-stack-smoke.test.ts |
| **Agent 4** | Merge Agent: integrate fragments, run verification suite |

### Agent 4 Merge Summary
1. backend/main.py — sites router | 2. aggregate_service — site_id/team_id | 3. aggregate — params | 4. api.ts — fetchSites, fetchWarpRisk | 5. layout — PWA tags | 6. next.config — manifest headers | 7. sessions — coaching hook | 8. seagull/welder — ReportLayout props | 9. supervisor — SiteSelector | 10. context/CONTEXT.md — feature entries

---

## 6. Data Models

### Session
```typescript
{ id, welder_id, status, frames[], metadata, weld_type, process_type?, team_id? }
```

### Frame
```typescript
{ timestamp_ms, volts, amps, angle_degrees, thermal_snapshots[],
  heat_dissipation_rate_celsius_per_sec, travel_speed_mm_per_min?, travel_angle_degrees?,
  ctwd_mm?, heat_input_kj_per_mm?, arc_termination_type? }
```
**heat_input_kj_per_mm:** kJ/mm = (amps × volts × 60) / (travel_speed × 1000); expert 0.5–0.9.  
**arc_termination_type:** `"crater_fill_present"` (expert) | `"no_crater_fill"` (novice); set on last arc-on frame before transition.  
**travel_angle_degrees:** ge=-30 (can be negative = drag).

### FrameInput (AlertEngine)
```typescript
{ frame_index, timestamp_ms?, travel_angle_degrees?, travel_speed_mm_per_min?, volts?, amps?, ns_asymmetry }
```
**timestamp_ms:** If set, AlertEngine uses simulated time for suppression (required for fast replay).  
**volts, amps:** Optional; required for arc_instability, crater_crack, undercut, lack_of_fusion, burn_through. When None, rules log warning and skip. `simulate_realtime` and `get_session_alerts` pass from frame_data.

### Site / Team
```typescript
Site: { id, name, location, created_at, teams: Team[] }
Team: { id, site_id, name, created_at }
```

### FrameDelta (Compare)
```typescript
{ timestamp_ms, amps_delta, volts_delta, angle_degrees_delta,
  heat_dissipation_rate_celsius_per_sec_delta, thermal_deltas: ThermalDelta[] }
```
**Sign:** positive = session_a − session_b; A hotter. Aligned by `timestamp_ms` only; shared timestamps only.

### AlertPayload (Session Alerts)
```typescript
{ frame_index, rule_triggered, severity, message, correction, timestamp_ms }
```
**Source:** `AlertEngine` run over stored frames; `GET /api/sessions/{id}/alerts`.

### ReportSummary / ExcursionEntry (Session Report Data Layer)
```typescript
ExcursionEntry: { timestamp_ms, defect_type, parameter_value?, threshold_value?, duration_ms?, source: "alert"|"frame_derived", notes? }
ReportSummary: {
  session_id, generated_at,
  heat_input_min/max/mean_kj_per_mm?, heat_input_wps_min/max, heat_input_compliant,
  travel_angle_excursion_count, travel_angle_worst_case_deg?, travel_angle_threshold_deg,
  total_arc_terminations, no_crater_fill_count, crater_fill_rate_pct,
  defect_counts_by_type, total_defect_alerts, excursions: ExcursionEntry[]
}
```
**Source:** `GET /api/sessions/{id}/report-summary`; `compute_report_summary()` in `backend/scoring/report_summary.py`. Excursions merge alert-derived (notes from AlertPayload.message) and frame-derived (run-length collapsed travel angle). Process_type mapping owned by `compute_report_summary`.

### DecomposedSessionScore / ExcursionEvent / ScoreComponent
```typescript
ExcursionEvent: { timestamp_ms, parameter, value, threshold, duration_ms }
ScoreComponent: { name, passed, score, excursions[], summary }
DecomposedSessionScore: {
  session_id, overall_score, passed,
  components: { heat_input, torch_angle, arc_termination, defect_alerts, interpass },
  frame_count, arc_on_frame_count, computed_at_ms, wps_range_kj_per_mm
}
```
**overall_score:** Weighted mean of component scores. **passed:** All critical components passed. **Source:** `score_session_decomposed()` in `scoring/scorer.py`.

---

## 7. File Index (Critical Paths)

### Backend — Routes
| File | Purpose |
|------|---------|
| `backend/main.py` | App entry; includes welders, predictions, narratives, aggregate, sites, etc. |
| `backend/routes/sessions.py` | Session CRUD, score, get_session_frames_raw, get_session_alerts, get_report_summary |
| `backend/routes/welders.py` | trajectory, benchmarks, coaching-plan, certification-status |
| `backend/routes/predictions.py` | Warp-risk endpoint |
| `backend/routes/aggregate.py` | GET /api/sessions/aggregate (site_id, team_id) |
| `backend/routes/sites.py` | CRUD sites, teams |
| `backend/routes/dev.py` | seed-mock-sessions, wipe-mock-sessions |

### Backend — Services & Data
| File | Purpose |
|------|---------|
| `backend/services/alert_service.py` | run_session_alerts — AlertEngine over session frames; used by alerts + report-summary |
| `backend/services/prediction_service.py` | ONNX warp risk |
| `backend/services/narrative_service.py` | Anthropic narrative, caching |
| `backend/services/aggregate_service.py` | get_aggregate_kpis |
| `backend/services/comparison_service.py` | compare_sessions — align by timestamp; backend source of truth |
| `backend/data/mock_sessions.py` | generate_session_for_welder, stitch_expert, continuous_novice |
| `backend/data/mock_welders.py` | WELDER_ARCHETYPES |
| `backend/realtime/alert_engine.py` | Rule evaluation, suppression |
| `backend/config/alert_thresholds.json` | Thermal 25/40, angle 6.5/8, speed 13/18, defect thresholds (voltage_lo_V, crater_*, porosity, undercut, lack_of_fusion, burn_through) |
| `backend/config/alert_thresholds_defect_test.json` | Test config for defect rule unit tests (angle_deviation_critical=90 to isolate porosity/oxide) |
| `backend/scoring/models.py` | ExcursionEvent, ScoreComponent, DecomposedSessionScore (Pydantic) |
| `backend/scoring/config.py` | load_scoring_config — WPS range, component weights |
| `backend/scoring/heat_input.py` | calculate_heat_input_component — kJ/mm vs WPS range |
| `backend/scoring/components.py` | torch angle, arc termination, defect alerts, interpass components |
| `backend/scoring/scorer.py` | score_session_decomposed, _build_alerts_from_frames (single source) |
| `backend/scoring/report_summary.py` | compute_report_summary, ExcursionEntry, ReportSummary; report_thresholds.json (cached) |
| `backend/config/scoring_config.json` | WPS range 0.9–1.5 kJ/mm, component weights (must sum to 1.0) |
| `backend/config/report_thresholds.json` | WPS thresholds: heat_input_min/max, travel_angle_threshold/nominal (aluminum_spray) |

### Frontend — Key Files
| File | Purpose |
|------|---------|
| `lib/api.ts` | fetchSession, fetchSessionAlerts, fetchReportSummary, fetchScore, fetchWarpRisk, fetchNarrative, fetchSites, fetchAggregateKPIs |
| `utils/frameUtils.ts` | getFrameAtTimestamp, extractCenterTemperatureWithCarryForward |
| `utils/heatmapData.ts`, `utils/angleData.ts` | Data extraction |
| `lib/micro-feedback.ts` | generateMicroFeedback(frames) |
| `app/replay/[sessionId]/page.tsx` | Replay + WarpRiskGauge |
| `app/demo/page.tsx` | Demo landing: redirect to default pair |
| `app/demo/[sessionIdA]/[sessionIdB]/page.tsx` | Investor comparison: WQI gauges, sparklines, alert feed, playback (2D only) |
| `app/compare/page.tsx` | Compare landing: session A/B inputs, Expert vs Novice demo |
| `app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | Compare view: heatmaps, delta, 3D torch, alert feed |
| `components/welding/WeldTrail.tsx` | Colored point cloud torch path on workpiece; used by TorchWithHeatmap3D |
| `hooks/useSessionComparison.ts` | compareSessions, useSessionComparison — mirrors backend |
| `hooks/useReportSummary.ts` | fetch report summary; AbortController on unmount |
| `utils/deltaHeatmapData.ts` | extractDeltaHeatmapData, deltaTempToColor |
| `types/comparison.ts` | FrameDelta, ThermalDelta, TemperatureDelta |
| `types/panel.ts` | Panel, PanelScoreResult, PanelRiskLevel, InspectionDecision |
| `types/report-summary.ts` | ReportSummary, ExcursionEntry — matches backend |
| `app/seagull/welder/[id]/page.tsx` | Welder report, ReportLayout, compliance slot |
| `components/welding/ComplianceSummaryPanel.tsx` | Heat Input, Torch Angle, Arc Termination rows; 4 states |
| `components/welding/ExcursionLogTable.tsx` | Excursion log; sort by timestamp/type; empty state |
| `app/(app)/dashboard/page.tsx` | Panel Readiness: 6 panels, stats bar, filter tabs, Expert Benchmark |
| `app/(app)/supervisor/page.tsx` | WWAD dashboard |
| `app/(app)/live/page.tsx` | iPad PWA |
| `components/welding/TorchWithHeatmap3D.tsx` | Unified 3D torch + thermal metal + WeldTrail |

---

## 8. Patterns

### Frame Resolution
**Use when:** Mapping timestamp to frame  
**How:** Exact match → nearest before → first frame  
**Location:** `utils/frameUtils.ts`

### Thermal Continuity (Sparse Data)
**Use when:** 3D color from sparse thermal (5 Hz)  
**How:** `extractCenterTemperatureWithCarryForward` — walk backwards for last known temp

### SSR Safety (WebGL/Canvas)
**Use when:** Browser-only components (R3F Canvas, TorchWithHeatmap3D, any WebGL)  
**How:** `dynamic(..., { ssr: false })` — NEVER static import  
**Why:** WebGL/DOM do not exist during Next.js SSR; static import causes blank canvas or hydration mismatch. See LEARNING_LOG.md 2026-03-02 (Demo circle heatmap).  
**Reference:** Replay and compare pages use dynamic import for TorchWithHeatmap3D; cross-check before adding to new pages.

### Simulated Timestamp for Alerts
**Use when:** Replaying frames faster than real-time  
**How:** Pass `timestamp_ms = frame_index * 10` to FrameInput  
**Why:** Wall-clock suppression would cap alerts when replay runs in <1s

### Alert Messages Use Config, Never Hardcode
**Use when:** Alert messages/corrections mention threshold values (voltage, amps, speed)  
**How:** Interpolate from config: `f"voltage < {self._cfg['voltage_lo_V']}V sustained"`  
**Why:** Config changes (e.g. different material/WPS) would otherwise show wrong numbers to welder or QA — diagnostic trust problem

### Stateful Alert Buffers Reset on Missing Data
**Use when:** Rule depends on volts/amps and frame has None  
**How:** Call `buffer.reset()` when required field is None (e.g. crater buffer on amps=None)  
**Why:** Sensor dropout followed by amps=0 at bead end could fire false crater alert using stale history

### Compare Session Alignment
**Use when:** Side-by-side session comparison  
**How:** Align frames by `timestamp_ms` only; only shared timestamps produce deltas. No role assumption (A/B arbitrary).  
**Location:** `useSessionComparison`, `backend/services/comparison_service.py`  
**Scale:** A and B heatmaps share `compareColorFn` (min/max over both); delta uses `deltaTempToColor` (-50°C→blue, 0→white, +50°C→purple)

### Promise.race Timeout Cleanup
**Use when:** Wrapping async work with a timeout via `Promise.race([fn(), timeout])`  
**How:** Store `setTimeout` id; call `clearTimeout(id)` in a `finally` block so the timer is cleared when the race settles (whether fn wins or timeout wins).  
**Why:** If fn wins first, the timeout stays scheduled until it fires — leak and wasted work.  
**Location:** `fetchScoreWithTimeout` in dashboard page.

### Compare Alert Fetch Isolation
**Use when:** Fetching alerts for both sessions on compare page  
**How:** `Promise.allSettled([fetchSessionAlerts(A), fetchSessionAlerts(B)])` — one failure does not kill page load.  
**Why:** Session fetches succeed even if alerts endpoint fails; show "Alerts unavailable" per column

### Report Summary: run_session_alerts for Both Alerts and Report
**Use when:** Need alerts for a session (alerts endpoint or report-summary)  
**How:** Call `run_session_alerts(session_id, db)` from `backend/services/alert_service.py` — async; returns `list[AlertPayload]` (objects). Routes call `model_dump()` only when building HTTP response. Report-summary awaits it and passes objects to `compute_report_summary`.  
**Why:** Single place for FrameInput mapping, AlertEngine config path, ns_asymmetry; no duplication.

### Report Summary: process_type Mapping Owned by Aggregator
**Use when:** Resolving session process_type to WPS config key  
**How:** Route passes raw `process_type`; `compute_report_summary` in `report_summary.py` owns `PROCESS_TYPE_TO_CONFIG_KEY` (aluminum→aluminum_spray; mig/None/unknown→aluminum_spray).  
**Why:** Do not map in route; aggregator is single owner.

### Scoring: Single Source for Alert Build
**Use when:** Need to run frames through AlertEngine for scoring  
**How:** Call `_build_alerts_from_frames(frames)` from `scoring/scorer.py` — used by GET /score, POST /rescore, rescore_all_sessions script.  
**Why:** Do not duplicate AlertEngine + FrameInput logic in routes or scripts; one place to fix config path, field mapping, ns_asymmetry.

### Scoring Config Weight Validation
**Use when:** Loading scoring_config.json with component weights  
**How:** Validate `arc_termination_weight + heat_input_weight + torch_angle_weight + defect_alert_weight + interpass_weight ≈ 1.0` (abs(total - 1.0) < 1e-6).  
**Why:** Misconfigured weights skew overall_score; fail fast on load.

### Deterministic Mock Data
**Use when:** Seeding or generating mock frames  
**How:** `rng = random.Random(seed)`; never global `random.seed()`  
**Why:** Parallel callers keep reproducibility

### Pydantic v1/v2 Compatibility (Frame/model_copy)
**Use when:** Copying Pydantic models with updates (e.g. `arc_termination_type`)  
**How:** `hasattr(obj, "model_copy")` — if true use `obj.model_copy(update={...})`, else `obj.copy(update={...})`  
**Why:** v1 uses `.copy`, v2 uses `.model_copy`. Avoid `except AttributeError` — it swallows unrelated attribute errors and makes debugging hard.

### Mock Data Defensive Guards
**Use when:** Function receives numeric params that may cause division by zero  
**How:** At top of function: `param = max(param, 1.0)` or similar — guard at boundary, not at call sites  
**Why:** Callers may change; one-line guard is zero risk.

### Hooks Before Early Returns
Call all hooks before any `if (error) return ...`.

### WELDER_MAP
`mike-chen` → `sess_novice_001`; `expert-benchmark` → `sess_expert_001`; others: id as sessionId.

---

## 9. Constraints

### WebGL Context Limit
**What:** Browsers limit ~8–16 WebGL contexts per tab  
**Handle:** ✅ 1–2 Canvas instances max per page | ❌ 6+ Canvases  
**Reference:** `documentation/WEBGL_CONTEXT_LOSS.md`, `LEARNING_LOG.md`

### Data Integrity
**What:** Raw sensor data append-only; scoring stateless; replays exact  
**Handle:** Never mutate raw data; never guess values

### Live Page (iPad PWA)
**What:** No WebGL; touch-optimised  
**Handle:** 2D SVG only; min 48px touch targets

### Common Failure Points
| ❌ Wrong | ✅ Right |
|---------|---------|
| Static import of TorchWithHeatmap3D on new pages | `dynamic(..., { ssr: false })` — match replay/compare |
| Forgetting `ssr: false` on 3D | `dynamic(..., { ssr: false })` |
| Recomputing heat dissipation frontend | Use `frame.heat_dissipation_rate_celsius_per_sec` |
| Not handling sparse thermal | `extractCenterTemperatureWithCarryForward()` |
| Global random.seed() | `rng = random.Random(seed)` |
| Multiple Canvases (6+) | Max 1–2 per page |
| Hardcoding "19.5V" or "140A" in alert messages | Use `self._cfg["voltage_lo_V"]` etc. in f-strings |
| Leaving crater buffer state when amps=None | Call `_crater_buffer.reset()` to avoid false positives |
| try/except AttributeError for Pydantic copy | Use `hasattr(obj, "model_copy")` — explicit, no swallowed errors |
| Inline magic numbers in mock generators | Extract to constants (AL_*_BASE_MEAN, etc.) |
| Docstring contradicting implementation | Update docstring immediately — wrong doc causes "fix" that breaks code |
| Promise.race with setTimeout, no cleanup | Clear timer in `finally` block — else leaks when fn wins first |
| `document.querySelector` in React tests | Use `within(container).getByText()` + `toHaveAttribute` — Testing Library pattern |
| Dead mocks (useRouter when page doesn't use it) | Remove unused `jest.mock` and mock vars — clutters tests |

---

## 10. API Contracts (Extended)

### GET /api/sessions/{session_id}/alerts
**Purpose:** Pre-compute alerts by running stored frames through AlertEngine.  
**Response:** `{ alerts: AlertPayload[] }`  
**Cap:** 2000 frames (same as compare page)  
**Used by:** Compare page alert feed. Delegates to `run_session_alerts()`.

### GET /api/sessions/{session_id}/report-summary
**Purpose:** Session compliance summary for report UI and PDF.  
**Response:** `ReportSummary` (heat input, travel angle excursions, arc termination, defect counts, excursions)  
**Headers:** `Cache-Control: max-age=60`  
**Used by:** Welder report page (`useReportSummary`), PDF route (optional body param)

### GET /api/sessions/{session_id}/score
**Purpose:** Session score (legacy total + decomposed components) + windowed WQI when session has ≥10 frames.  
**Response:** `{ total, rules, session_score: DecomposedSessionScore, active_threshold_spec, wqi_timeline?, mean_wqi?, median_wqi?, min_wqi?, max_wqi?, wqi_trend? }`  
**Windowed WQI:** 50-frame tumbling windows; `wqi_timeline` = [{frame_start, frame_end, wqi}]; trend = improving|degrading|stable when ≥4 windows. Persisted on first score for COMPLETE sessions.  
**Note:** `session_score` is canonical; `total` kept for backward compat. Decomposed score suppressed in production on exception.

### POST /api/sessions/{session_id}/rescore
**Purpose:** Recompute decomposed score and persist score_total. For backfill after scoring changes.  
**Request:** None (session_id in path)  
**Response:** `DecomposedSessionScore` (model_dump)  
**TODO:** Add auth guard before QA exposure.

---

## 11. Verification & Run Commands

### Start dev
```bash
npm run dev
```

### Kill and restart
```bash
lsof -ti :8000 | xargs kill 2>/dev/null || true
lsof -ti :3000 | xargs kill 2>/dev/null || true
cd /path/to/project && npm run dev
```

### Verification suite
```bash
./scripts/run-verification-suite.sh
```

### Smoke tests (backend on :8000)
```bash
cd my-app && npm test -- --testPathPattern="full-stack-smoke"
```

### Aluminum mock verification
```bash
cd backend && python3 -m scripts.verify_aluminum_mock
```

### Preflight check (demo)
```bash
python -m scripts.preflight_check
```

### Python syntax
```bash
python -m py_compile backend/main.py backend/routes/sites.py backend/routes/sessions.py backend/routes/aggregate.py backend/services/aggregate_service.py
```

---

## 12. Related Docs

| File | Purpose |
|------|---------|
| `LEARNING_LOG.md` | Past mistakes, WebGL context loss |
| `documentation/WEBGL_CONTEXT_LOSS.md` | WebGL limits |
| `.cursorrules` | AI config, data integrity contract |
| `DEPLOY.md` | One-click Docker deploy |
| `.cursor/plans/batch3-agent*.md` | Batch 3 implementation plans |
| `.cursor/plans/batch4-agent*.md` | Batch 4 agent instructions |
| `.cursor/plans/compare-alert-feed.md` | Compare alert feed implementation plan |
| `docs/ISSUE_COMPARE_ALERT_FEED.md` | Compare alert feed issue spec |
| `docs/ISSUE_DEFECT_ALERT_RULES.md` | Defect alert rules issue spec |
| `.cursor/plans/defect-alert-rules-implementation.md` | Defect alert implementation plan |
| `docs/ISSUE_MOCK_DATA_FOUNDATION.md` | Mock data foundation issue spec |
| `.cursor/plans/mock-data-foundation-execution.md` | Mock data implementation plan |
| `.cursor/plans/demo-page-api-integration-refined.md` | Demo page API wiring plan |
| `.cursor/plans/demo-page-api-integration-execution.md` | Demo page execution (route structure, data flow) |
| `.cursor/plans/windowed-wqi-scoring.md` | Windowed WQI scoring plan |
| `.cursor/plans/scoring-decomposition-execution.md` | Scoring decomposition + heat input implementation plan |
| `docs/ISSUE_SESSION_REPORT_DATA_LAYER.md` | Session report data layer issue spec |
| `.cursor/plans/session-report-data-layer-execution.md` | Report summary + compliance UI implementation plan |
| `.cursor/plans/dashboard-welder-visual-redesign.md` | Welder Roster dashboard redesign plan (superseded by panel readiness) |
| `.cursor/plans/panel-readiness-dashboard.md` | Panel Readiness dashboard — welders → panels migration |
| `.cursor/plans/panel_mock_data.md` | PANEL_MOCK_SCORES fallback when API returns null |
