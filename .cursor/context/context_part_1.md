# WarpSense — Context Part 1

> **Purpose:** Consolidated context for the WarpSense welding MVP. Covers Agent 1–3 implementations, Seagull pilot, demo, mock data, PDF, and rebrand.  
> **Last updated:** 2026-02-21

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js, React)                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /demo              Investor-grade demo + guided tour → CTA to /demo/team        │
│  /demo/team         Team dashboard (Mike Chen, Expert Benchmark)                 │
│  /demo/team/[id]    Welder report: HeatMap×2, FeedbackPanel, LineChart         │
│  /seagull           Seagull Team dashboard (cards from WELDER_ARCHETYPES)        │
│  /seagull/welder/[id]  Welder report: ReportLayout, NarrativePanel, PDF download │
│  /replay/[id]       Replay + WarpRiskGauge                                       │
│  /supervisor        WWAD macro-analytics (team KPIs, heatmap, CSV export)        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ fetchSession, fetchScore, fetchWarpRisk,
                                       │ fetchNarrative, fetchAggregateKPIs
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI, PostgreSQL)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /api/sessions/:id           Session + frames                                   │
│  /api/sessions/:id/score     Session score (total, rules)                        │
│  /api/sessions/:id/warp-risk Warp prediction (ONNX)                              │
│  /api/sessions/:id/narrative AI narrative (Anthropic, cached)                   │
│  /api/sessions/aggregate     Team KPIs, trend, heatmap (90-day, 1000-session cap) │
│  /api/welders/health         Welder health                                       │
│  /api/dev/seed-mock-sessions Seed 10 mock welders (dev only)                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ML / AI: prediction_service (ONNX), narrative_service (Anthropic)                 │
│  Data: WELDER_ARCHETYPES → generate_session_for_welder → SessionModel          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## File Index — What Each File Does

### Backend — Models & Schemas

| File | Purpose |
|------|---------|
| `backend/models/shared_enums.py` | All 5 shared enums for metrics, thresholds |
| `backend/models/__init__.py` | Exports enums, Session, SessionModel, etc. |
| `backend/models/narrative.py` | `session_narratives` table model |
| `backend/schemas/shared.py` | `MetricScore`, `METRIC_LABELS`, `make_metric_score` |
| `backend/schemas/narrative.py` | Narrative request/response schemas |

### Backend — Services

| File | Purpose |
|------|---------|
| `backend/services/prediction_service.py` | Warp risk prediction via ONNX; `model_available`, `risk_level` (ok/warning/critical) |
| `backend/services/narrative_service.py` | Anthropic narrative generation, caching, score-based invalidation |
| `backend/features/warp_features.py` | Shared warp features for training and inference |

### Backend — Routes

| File | Purpose |
|------|---------|
| `backend/main.py` | App entry; includes welders, predictions, narratives, aggregate routers |
| `backend/routes/welders.py` | `GET /api/welders/health` |
| `backend/routes/predictions.py` | Warp-risk endpoint; `get_session_frames_raw` helper in sessions |
| `backend/routes/narratives.py` | `POST /api/sessions/:id/narrative` |
| `backend/routes/sessions.py` | Session CRUD; `get_session_frames_raw` (lines 69–89) for prediction |
| `backend/routes/dev.py` | `POST /api/dev/seed-mock-sessions`, `POST /api/dev/wipe-mock-sessions` (ENV=development or DEBUG=1) |
| Aggregate routes | `GET /api/sessions/aggregate` (KPIs, heatmap, CSV) |

### Backend — Data & Scripts

| File | Purpose |
|------|---------|
| `backend/data/mock_welders.py` | `WELDER_ARCHETYPES` — welder_id, name, arc_type, sessions, base/delta |
| `backend/data/mock_sessions.py` | `generate_session_for_welder`, `generate_frames_for_arc` (arc-specific signals) |
| `backend/scripts/seed_demo_data.py` | Idempotent seed; run from deploy or manually |
| `backend/scripts/generate_training_data.py` | Training data for warp model |
| `backend/scripts/train_warp_model.py` | sklearn → ONNX warp model |
| `backend/alembic/versions/006_*.py` | `session_narratives` migration |

### Frontend — Types

| File | Purpose |
|------|---------|
| `my-app/src/types/shared.ts` | Shared types matching backend enums |
| `my-app/src/types/ai-feedback.ts` | `AIFeedbackResult`, `FeedbackItem`, `FeedbackTrend` |
| `my-app/src/types/narrative.ts` | Narrative types |
| `my-app/src/types/prediction.ts` | Warp risk types |
| `my-app/src/types/aggregate.ts` | Aggregate KPI types |

### Frontend — API & Lib

| File | Purpose |
|------|---------|
| `my-app/src/lib/api.ts` | `fetchSession`, `fetchScore`, `fetchWarpRisk`, `fetchNarrative`, `fetchAggregateKPIs` |
| `my-app/src/lib/ai-feedback.ts` | `generateAIFeedback(session, score, historicalScores)` — rule-based feedback |
| `my-app/src/lib/narrative-api.ts` | Narrative fetch (uses `buildUrl`/`apiFetch` from api.ts) |
| `my-app/src/lib/pdf-chart-capture.ts` | `captureChartToBase64(elementId)` — html-to-image, 10s timeout |
| `my-app/src/lib/demo-config.ts` | Demo config (single source of truth) |
| `my-app/src/lib/demo-tour-config.ts` | DemoTour steps config |
| `my-app/src/lib/seagull-demo-data.ts` | Seagull demo data |
| `my-app/src/utils/heatmapTempRange.ts` | `computeMinMaxTemp` |

### Frontend — App Routes

| File | Purpose |
|------|---------|
| `my-app/src/app/demo/page.tsx` | Investor-grade demo; DemoTour (4 steps) |
| `my-app/src/app/demo/team/page.tsx` | Team dashboard (Mike Chen 42, Expert Benchmark 94) |
| `my-app/src/app/demo/team/[welderId]/page.tsx` | Welder report (HeatMap×2, FeedbackPanel, LineChart) |
| `my-app/src/app/seagull/page.tsx` | Seagull Team dashboard; `Promise.allSettled(fetchScore)` |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Welder report; ReportLayout, NarrativePanel, PDF download |
| `my-app/src/app/replay/[sessionId]/page.tsx` | Replay + WarpRiskGauge; 10s timeout for warp-risk |
| `my-app/src/app/supervisor/page.tsx` | WWAD macro-analytics dashboard |

### Frontend — Components

| File | Purpose |
|------|---------|
| `my-app/src/components/layout/ReportLayout.tsx` | Slot-based layout for welder report (narrative slot) |
| `my-app/src/components/welding/FeedbackPanel.tsx` | Renders feedback items; info=blue, warning=violet |
| `my-app/src/components/welding/NarrativePanel.tsx` | Fetches narrative; loading skeleton → text → Regenerate |
| `my-app/src/components/welding/WarpRiskGauge.tsx` | Warp risk display (ok/warning/critical; 0.55, 0.75 thresholds) |
| `my-app/src/components/pdf/WelderReportPDF.tsx` | PDF layout — Document, Page, score circle, coach feedback, optional chart, narrative |
| `my-app/src/components/demo/DemoTour.tsx` | Guided tour overlay (4 steps) |

### Frontend — API Routes

| File | Purpose |
|------|---------|
| `my-app/src/app/api/welder-report-pdf/route.ts` | POST; validates body, renders WelderReportPDF; `narrative?: string`; 5MB/2MB limits |

### Styling & Theme (WarpSense Rebrand)

| File | Purpose |
|------|---------|
| `my-app/src/theme.ts` | `THERMAL_COLOR_ANCHORS`, `CHART_PALETTE`, blue/purple/violet |
| `my-app/src/components/AppNav.tsx` | Demo link blue; navigation |
| `my-app/src/components/welding/TorchViz3D.tsx` | Angle guide ring, grid — blue |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | Blue accent |
| `my-app/src/components/welding/HeatmapPlate3D.tsx` | Violet context-loss UI |
| `my-app/src/app/(app)/dashboard/page.tsx` | Blue/violet states |
| `my-app/src/components/demo/DemoLayoutClient.tsx` | Violet error fallback |
| `my-app/src/app/seagull/page.tsx` | "Score unavailable" violet |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Violet error state |
| `my-app/src/app/dev/torch-viz/page.tsx` | Blue theme, "Blue / Purple" |

---

## Key Flows

### Seagull Welder Report

```
/seagull/welder/[id] → fetchSession×2 + fetchScore + NarrativePanel (own fetch)
  → ReportLayout(narrative={<NarrativePanel />})
  → generateAIFeedback(session, score, historicalScores) → FeedbackPanel
  → HeatMap×2 (shared tempToColorRange), LineChart
  → PDF: fetchNarrative → captureChartToBase64("trend-chart") → POST /api/welder-report-pdf
```

### Warp Prediction

```
Training: generate_training_data.py → train_warp_model.py → warp_model.onnx
Inference: GET /api/sessions/:id/warp-risk → prediction_service (ONNX)
  → risk_level ok (≤0.55) | warning (0.55–0.75) | critical (>0.75)
  → model_available: false if ONNX missing
```

### Narrative

```
POST /api/sessions/:id/narrative → narrative_service (Anthropic)
  → Cached by session_id; invalidated on score change
  → NarrativePanel: fetch → skeleton → text → Regenerate
  → PDF: optional narrative in WelderReportPDF
```

### Mock Sessions

```
WELDER_ARCHETYPES (10 welders, arc_types) → generate_session_for_welder
  → generate_frames_for_arc(arc, session_idx)
  → Session IDs: sess_{welder_id}_{001..00n}
  → POST /api/dev/seed-mock-sessions (idempotent)
```

### PDF Report

```
Download PDF → captureChartToBase64("trend-chart") → POST /api/welder-report-pdf
  → Body: welder, score, feedback, chartDataUrl?, narrative?
  → WelderReportPDF: dark theme, score circle, AI Coach Report, Coach Feedback, chart
  → sanitizeText for control chars
```

---

## Patterns & Constraints

- **Hooks before early returns:** Call all hooks before any `if (error) return ...`.
- **Promise.all vs allSettled:** Dashboard uses allSettled (partial success); WelderReport uses all (all-or-nothing).
- **WELDER_MAP:** `mike-chen` → `sess_novice_001`; `expert-benchmark` → `sess_expert_001`; others: id as sessionId.
- **Next.js async params:** `params` is `Promise`; use `isPromise(params)` + Suspense + `use(params)`.
- **Logging:** `logError("ComponentName", err)` — not `console.error`.
- **WWAD orthogonality:** No 3D/micro-feedback imports in supervisor code.
- **Aggregate limits:** 90-day range, 1000-session cap, truncation alert.
- **Chart capture:** Client-side only; `id="trend-chart"`; 10s timeout; null on failure.

---

## Verification

```bash
# Backend
curl http://localhost:8000/api/welders/health
curl -X POST http://localhost:8000/api/dev/seed-mock-sessions
curl http://localhost:8000/api/sessions/sess_novice_001/warp-risk
curl -X POST http://localhost:8000/api/sessions/sess_novice_001/narrative -H "Content-Type: application/json" -d '{}'

# Frontend
cd my-app && npm run build
cd my-app && npm test -- --run
```

---

## Related Docs

| File | Purpose |
|------|---------|
| `.cursor/plans/function-gemma-on-device-ai-plan.md` | FunctionGemma, AI demo |
| `.cursor/plans/merge-agent-routers-and-api-plan.md` | Router merge |
| `LEARNING_LOG.md` | WebGL context limits, lessons |
