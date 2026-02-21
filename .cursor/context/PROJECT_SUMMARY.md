# WarpSense — Project Summary

> **Purpose:** Consolidated project documentation (~1000 words). Single entry point for understanding the system.  
> **Source:** All files under `.cursor/context/`  
> **Last Updated:** 2026-02-21

---

## 1. Project Overview

**WarpSense** is a safety-adjacent industrial welding quality intelligence system. The MVP delivers recording, replaying, and scoring of welding sessions with thermal profiles, torch angle analysis, and AI-style feedback. The system prioritizes **correctness, determinism, and explainability** over speed.

**Current Stage:** MVP complete, production-deploy ready. Key capabilities include session replay with 3D visualization, rule-based scoring, micro-feedback, macro-analytics for supervisors, defect annotation, longitudinal skill trajectory, warp-risk prediction, and AI narrative generation.

---

## 2. Tech Stack & Architecture

### Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **3D / Charts** | Three.js, @react-three/fiber, Recharts |
| **Backend** | Python, FastAPI, REST |
| **Database** | PostgreSQL, SQLAlchemy ORM |
| **Infrastructure** | Docker Compose, DigitalOcean, monorepo |

### High-Level Architecture

```
ESP32 Sensors → Backend (bulk ingest) → PostgreSQL
Frontend (Next.js) → Backend (FastAPI) → PostgreSQL
```

**Design Principles:**
- **Append-only:** Raw sensor data never edited; only new frames added
- **Backend as source of truth:** Heat dissipation, scoring, and aggregates computed once server-side
- **snake_case everywhere:** No conversion layer between backend JSON and frontend types
- **Never mutate raw data:** All extraction/transformation is pure

**Critical Constraints:**
- Frame interval: 10 ms (100 Hz)
- Bulk ingestion: 1000–5000 frames per POST
- Thermal sampling: Sparse (5 Hz)
- WebGL: Max 2–3 Canvas instances per page; context-loss handling required

---

## 3. Features & Related Files

### Session Replay

**What:** Heatmap, TorchAngleGraph, 3D torch visualization driven by shared playback timestamp. Supports side-by-side comparison with expert sessions.

**Files:**
- `app/replay/[sessionId]/page.tsx` — Replay page, playback state, timeline
- `components/welding/HeatMap.tsx` — CSS grid heatmap
- `components/welding/TorchAngleGraph.tsx` — Recharts angle chart
- `components/welding/TorchWithHeatmap3D.tsx` — Unified 3D torch + thermally-colored metal
- `utils/heatmapData.ts`, `utils/angleData.ts`, `utils/frameUtils.ts` — Data extraction
- `lib/api.ts` — `fetchSession`, `fetchScore`, `fetchAnnotations`

### Rule-Based Scoring

**What:** Five weld-quality rules (angle consistency, thermal symmetry, amps/volts stability, heat dissipation). Backend computes; frontend displays.

**Files:**
- `backend/services/scoring_service.py`, `backend/scoring/rule_based.py`
- `backend/routes/sessions.py` — GET /api/sessions/:id/score
- `components/welding/ScorePanel.tsx`

### Micro-Feedback (Frame-Level Guidance)

**What:** Angle drift and thermal symmetry alerts on replay. Clickable markers scrub to frame.

**Files:**
- `lib/micro-feedback.ts` — `generateMicroFeedback(frames)`
- `types/micro-feedback.ts`
- `components/welding/FeedbackPanel.tsx`, `components/welding/TimelineMarkers.tsx`

### WWAD Macro-Analytics (Supervisor Dashboard)

**What:** Team KPIs, trend chart, calendar heatmap, CSV export. Orthogonal to per-frame features; uses metadata + score_total only.

**Files:**
- `app/(app)/supervisor/page.tsx`
- `components/dashboard/CalendarHeatmap.tsx`, `lib/aggregate-transform.ts`, `lib/export.ts`
- `backend/routes/aggregate.py`, `backend/services/aggregate_service.py`

### Defect Pattern Library & Annotations

**What:** Session-scoped annotations (defect, near miss, technique error, equipment issue). Cross-session defect library with filters. Replay annotate mode.

**Files:**
- `backend/routes/annotations.py` — POST/GET /api/sessions/:id/annotations, GET /api/defects
- `backend/models/annotation.py`, `backend/schemas/annotation.py`
- `app/(app)/defects/page.tsx` — Defect library UI
- `components/welding/AddAnnotationPanel.tsx`, `components/welding/AnnotationMarker.tsx`
- `types/annotation.ts`

### Longitudinal Skill Trajectory

**What:** Chronological score history per welder, trend slope, projected next score. Multi-line Recharts chart.

**Files:**
- `backend/routes/welders.py` — GET /api/welders/:id/trajectory
- `backend/services/trajectory_service.py`, `backend/schemas/trajectory.py`
- `lib/api.merge_agent1.ts` — `fetchTrajectory`
- `components/welding/TrajectoryChart.tsx`
- `lib/welder-report-utils.ts` — `computeHistoricalScores`, `getTrajectoryFromResults`

### Warp Risk Prediction (ML)

**What:** ONNX-based warp probability per session. WarpRiskGauge on replay. Graceful degradation when model unavailable.

**Files:**
- `backend/routes/predictions.py` — GET /api/sessions/:id/warp-risk
- `backend/services/prediction_service.py`, `backend/features/warp_features.py`
- `components/welding/WarpRiskGauge.tsx`
- `lib/api.ts` — `fetchWarpRisk`

### AI Narrative Engine

**What:** Anthropic-generated session narrative. Cached; score-based invalidation. NarrativePanel on welder report; PDF export includes narrative.

**Files:**
- `backend/routes/narratives.py`, `backend/services/narrative_service.py`
- `backend/models/narrative.py`, `backend/schemas/narrative.py`
- `components/welding/NarrativePanel.tsx`
- `lib/api.ts` — `fetchNarrative`, `generateNarrative`

### Welder Report & PDF Export

**What:** Individual welder report with score, AI feedback, heatmaps, trend chart, trajectory, narrative. PDF download with chart capture, optional narrative.

**Files:**
- `app/seagull/welder/[id]/page.tsx` — Welder report page
- `components/layout/ReportLayout.tsx` — Slot-based layout
- `app/api/welder-report-pdf/route.ts` — POST handler
- `components/pdf/WelderReportPDF.tsx` — PDF layout
- `lib/pdf-chart-capture.ts` — `captureChartToBase64`
- `lib/ai-feedback.ts` — `generateAIFeedback`

### Threshold Configuration

**What:** Admin CRUD for weld-type thresholds (mig/tig/stick/flux_core). Angle, thermal, amps, volts, heat dissipation.

**Files:**
- `backend/routes/thresholds.py`, `backend/services/threshold_service.py`
- `app/admin/thresholds/page.tsx`, `components/admin/AngleArcDiagram.tsx`

### Mock Data & Seeding

**What:** 10 mock welders with skill arcs. Idempotent seed; dev-only routes.

**Files:**
- `backend/data/mock_welders.py` — WELDER_ARCHETYPES
- `backend/data/mock_sessions.py` — Frame generation
- `backend/routes/dev.py` — POST /api/dev/seed-mock-sessions
- `backend/scripts/seed_demo_data.py`

### Investor-Grade Demo

**What:** Guided tour on /demo, team dashboard, browser-only team path. DemoTour overlay, config-driven steps.

**Files:**
- `app/demo/`, `app/demo/team/`
- `components/demo/DemoTour.tsx`
- `lib/demo-config.ts`, `lib/demo-tour-config.ts`, `lib/seagull-demo-data.ts`

### Landing & Marketing

**What:** Apple-inspired landing at `/`. Route groups `(marketing)` / `(app)` control layout and nav.

**Files:**
- `app/(marketing)/page.tsx`, `app/landing/page.tsx`
- `components/AppNav.tsx`

---

## 4. Key Data Models

- **Session:** `session_id`, `frames[]`, `status`, `frame_count`, `start_time`, `weld_type`, `score_total?`
- **Frame:** `timestamp_ms`, `volts`, `amps`, `angle_degrees`, `thermal_snapshots[]`, `heat_dissipation_rate_celsius_per_sec`, `has_thermal_data`
- **ThermalSnapshot:** `distance_mm`, `readings[]` (center, north, south, east, west)
- **SessionScore:** `total`, `rules[]` (rule_id, passed, actual_value, threshold)

---

## 5. Integration Points

**Backend API (core):**
- GET /api/sessions/:id, POST /api/sessions/:id/frames
- GET /api/sessions/:id/score, /warp-risk, /narrative
- GET /api/sessions/aggregate
- GET /api/welders/:id/trajectory
- POST/GET /api/sessions/:id/annotations, GET /api/defects

**Frontend flow:** `fetchSession` → `useFrameData` → `extractHeatmapData` / `extractAngleData` → HeatMap, TorchAngleGraph, TorchWithHeatmap3D

---

## 6. Related Documentation

| File | Purpose |
|------|---------|
| `LEARNING_LOG.md` | Past mistakes, WebGL context loss |
| `documentation/WEBGL_CONTEXT_LOSS.md` | WebGL limits, context-loss handling |
| `DEPLOY.md` | One-click Docker deploy |
| `.cursorrules` | AI config, data integrity contract |
