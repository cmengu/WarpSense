# Project Context

> **Purpose:** High-level project state for AI tools. What exists, what patterns to follow, what constraints to respect.
> **For AI:** Reference with `@CONTEXT.md` to avoid reimplementing features or violating patterns.
> **Last Updated:** 2025-02-15

---

## Project Overview

**Name:** WarpSense (Welding MVP)  
**Type:** Web App + API (monorepo: ESP32, iPad, Next.js, FastAPI)  
**Stack:** Next.js 14, React 18, TypeScript, Tailwind, Three.js | FastAPI, PostgreSQL, SQLAlchemy  
**Stage:** MVP

**Purpose:** Reliable MVP for recording, replaying, and scoring welding sessions. Safety-adjacent industrial welding system — correctness, determinism, and explainability prioritized.

**Current State:**
- ✅ Session replay (heatmap, angle, 3D torch visualization)
- ✅ Session comparison (A | Delta | B)
- ✅ Rule-based scoring
- ✅ Mock data + backend seed
- ✅ Browser-only demo mode at `/demo` (zero backend/DB)
- 🔄 Production hardening
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
- **Temperature Colors = 50°C Anchors:** Blue→yellow→red 13-step gradient (20–600°C)

### Tech Stack

**Frontend:** Next.js 14, React 18, TypeScript, Tailwind, Three.js/react-three-fiber, Recharts  
**Backend:** FastAPI, Python, REST  
**Database:** PostgreSQL, SQLAlchemy  
**Infrastructure:** DigitalOcean, monorepo

**Critical Dependencies:**
- `three`, `@react-three/fiber` (~500KB) — 3D torch visualization
- `recharts` — angle line chart
- snake_case everywhere (backend JSON → frontend types, no conversion layer)

---

## Implemented Features

> **AI Rule:** Don't reimplement what's listed here.

### 3D Visualization (TorchViz3D)
**Status:** ✅  
**What:** 3D torch + weld pool with angle and temperature  
**Location:** `components/welding/TorchViz3D.tsx`  
**Pattern:** Dynamic import with `ssr: false`, max 1–2 Canvas per page, `webglcontextlost` handler  
**Integration:** Replay page, compare page, `/dev/torch-viz` dev page  
**See:** `LEARNING_LOG.md`, `documentation/WEBGL_CONTEXT_LOSS.md`

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

### Session Comparison
**Status:** ✅  
**What:** A | Delta | B view, `compareSessions()` → `FrameDelta[]`  
**Location:** `app/compare/[idA]/[idB]/page.tsx`, `hooks/useSessionComparison.ts`

### Rule-Based Scoring
**Status:** ✅  
**What:** `ScorePanel(sessionId)` fetches `GET /api/sessions/:id/score`  
**Backend:** Rule-based, stateless, reproducible

### Browser-Only Demo Mode
**Status:** ✅  
**What:** `/demo` — 100% in-browser synthesized welding data, zero backend/DB  
**Location:** `app/demo/`, `lib/demo-data.ts`  
**Contract:** Produces `Session` with `Frame[]` matching `extractHeatmapData`, `extractAngleData`, `extractCenterTemperatureWithCarryForward`

### Data Processing / Utilities
**Status:** ✅  
**Utilities:**  
- `extractCenterTemperature(frame)` — `utils/frameUtils.ts`  
- `extractCenterTemperatureWithCarryForward()` — thermal continuity for 3D  
- `getFrameAtTimestamp(frames, timestamp)`  
- `filterThermalFrames(frames)`  
- `compareSessions(sessionA, sessionB)`

---

## Data Models

### Session
```typescript
{ session_id, frames[], status, frame_count, start_time, weld_type }
```
**Used by:** Replay, Compare, ScorePanel, Demo  
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
**How:** Max 1–2 Canvas per page; add `webglcontextlost` listener; show "Refresh to restore" overlay  
**Why:** Browsers limit ~8–16 WebGL contexts per tab  
**See:** `LEARNING_LOG.md`, `documentation/WEBGL_CONTEXT_LOSS.md`

### Visual Consistency (Temperature)
**Use when:** Color-based temperature displays  
**How:** 50°C anchors, blue→yellow→red 13-step gradient (20–600°C)

---

## Integration Points

> **AI Rule:** Use these, don't recreate.

### Backend API
```
GET  /api/sessions/:id?limit=2000&include_thermal=true
POST /api/sessions/:id/frames  (1000-5000 Frame[] per request)
GET  /api/sessions/:id/score   → SessionScore
```

### Frame Data Flow
```
fetchSession(id) → Session
  → useFrameData(frames) → thermal_frames
  → extractHeatmapData(thermal_frames) → HeatmapData
  → extractAngleData(frames) → AngleData
  → <HeatMap data={heatmapData} />
  → <TorchAngleGraph data={angleData} />
  → TorchViz3D(angle, temp)
```

### Key Components
- **TorchViz3D(angle, temp, label)** — 3D torch + weld pool (dynamic import required)
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
**Handle:** 1–2 Canvas max per page; context-loss overlay  
**Affects:** Any 3D/Canvas features  
**See:** `LEARNING_LOG.md`

---

## File Structure

```
my-app/
  app/                    # Pages, routes
    replay/[sessionId]/   # Replay page
    compare/[idA]/[idB]/  # Compare page
    demo/                 # Browser-only demo
    api/                  # API routes
  components/
    welding/              # TorchViz3D, HeatMap, TorchAngleGraph
    ui/                   # Shared UI
  lib/
    api.ts                # API client
    demo-data.ts          # Browser-only demo synthesis
  utils/
    frameUtils.ts         # getFrameAtTimestamp, thermal helpers
    heatmapData.ts        # extractHeatmapData
  types/                  # session, frame, thermal
  hooks/
    useSessionComparison.ts
backend/
  routes/sessions.py
  services/thermal_service.py
  data/mock_sessions.py
context/                  # Architecture docs
```

**Key Files:**
- `types/session.ts`, `types/frame.ts`, `types/thermal.ts` — Data models
- `lib/api.ts` — API client
- `utils/frameUtils.ts` — Frame utilities
- `utils/heatmapData.ts` — Heatmap extraction
- `context/context-tech-stack-mvp-architecture.md` — Detailed architecture
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
**Used by:** ScorePanel

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
@CONTEXT.md — Check if exists
@LEARNING_LOG.md — Check past issues (esp. WebGL/3D)

Implement [feature] following:
- Pattern: [from CONTEXT]
- Integration: [from CONTEXT]
- Constraints: [from CONTEXT]
```

### Debugging
```
@CONTEXT.md — [relevant section]
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
- [ ] Checked CONTEXT.md for existing implementation
- [ ] Reviewed patterns to follow
- [ ] Noted integration points
- [ ] Identified constraints
- [ ] Checked LEARNING_LOG.md

---

## Related Docs

| File | Purpose |
|------|---------|
| `LEARNING_LOG.md` | Mistakes & solutions (esp. WebGL context loss) |
| `context/context-tech-stack-mvp-architecture.md` | Detailed architecture, file map |
| `documentation/WEBGL_CONTEXT_LOSS.md` | WebGL context loss reference |
| `.cursorrules` | AI config, data integrity contract |
| `README.md` | Setup, quick start |

---

**Maintenance:** Update after features, weekly review, monthly validation.
