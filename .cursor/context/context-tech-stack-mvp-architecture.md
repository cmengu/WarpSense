# Architecture Quick Reference

> **Purpose:** Daily driver for AI. Read this FIRST before generating code.  
> **For deep dives:** See full ARCHITECTURE.md (only when implementing major features).

---

## What Exists

**Backend:** FastAPI + PostgreSQL + SQLAlchemy  
**Frontend:** Next.js 14 + React 18 + TypeScript + Tailwind + Three.js  
**Features:** Session replay (heatmap/angle/3D torch), session comparison (A|Delta|B), rule-based scoring

**Status:** ✅ MVP complete (replay, compare, mock data, 3D visualization)

---

## Critical Constraints (NEVER VIOLATE)

### Data Integrity
- **Append-only:** Raw sensor data never edited, only new frames added
- **Backend is source of truth:** Heat dissipation calculated ONCE at ingestion, never recomputed frontend
- **No conversion layer:** snake_case everywhere (backend JSON → frontend types)
- **Never mutate raw data:** All extraction/transformation is pure functions

### Timing & Limits
- **Frame interval:** Exactly 10ms apart (100 Hz sampling rate)
- **Bulk ingestion:** 1000-5000 frames per POST request (hard limit, enforced)
- **Thermal sampling:** Sparse (5 Hz, every 100ms / every 10th frame)
- **Session max:** 30,000 frames (5 minutes at 100 Hz)

### Frontend Constraints
- **SSR safety:** WebGL/Canvas components MUST use `dynamic import` with `ssr: false`
- **Thermal continuity:** Use carry-forward pattern (last known temp) for smooth 3D color
- **Pagination:** Sessions >10k frames require streaming or pagination
- **Bundle size:** Three.js ~500KB acceptable for demo, lazy load for production

---

## Key Design Decisions

### Why These Choices Were Made

**Heatmap = CSS Grid (not Recharts ScatterChart)**  
→ ScatterChart overlaps at 7500 points; CSS grid handles unlimited points cleanly

**Playback = setInterval (not requestAnimationFrame)**  
→ RAF runs at 60fps (skips frames); setInterval at 100fps shows every 10ms frame

**Status Flow = One-Way (RECORDING→COMPLETE→ARCHIVED)**  
→ Prevents data corruption from re-recording over complete sessions

**Heat Dissipation = Backend Only**  
→ Thermal frames are sparse; backend has full context; frontend would need complex state

**Temperature Colors = 50°C Anchors**  
→ Visible change every 50°C (20→600°C) using blue→yellow→red 13-step gradient

---

## Integration Points

### Backend API
```
GET  /api/sessions/:id?limit=2000&include_thermal=true
POST /api/sessions/:id/frames  (1000-5000 Frame[])
GET  /api/sessions/:id/score   (SessionScore)
```

### Frontend Data Flow
```
fetchSession(id) → Session
  → useFrameData(frames) → thermal_frames
  → extractHeatmapData(thermal_frames) → HeatmapData
  → extractAngleData(frames) → AngleData
  → <HeatMap data={heatmapData} />
  → <TorchAngleGraph data={angleData} />
```

### Key Components
```
TorchViz3D(angle, temp, label)  // 3D torch + weld pool
HeatMap(data, activeTimestamp)  // CSS grid heatmap
TorchAngleGraph(data, active)   // Recharts line chart
ScorePanel(sessionId)           // Rule-based scoring display
```

### Utilities (Always Use These)
```
extractCenterTemperature(frame)              → number | null
extractCenterTemperatureWithCarryForward()   → number (for 3D)
getFrameAtTimestamp(frames, timestamp)       → Frame | null
filterThermalFrames(frames)                  → Frame[]
compareSessions(sessionA, sessionB)          → FrameDelta[]
```

---

## File Map (Critical Paths)

| Need | File |
|------|------|
| Session/Frame types | types/session.ts, types/frame.ts |
| Thermal types | types/thermal.ts |
| API client | lib/api.ts |
| Frame utilities | utils/frameUtils.ts |
| Heatmap extraction | utils/heatmapData.ts |
| Session comparison | hooks/useSessionComparison.ts |
| Replay page | app/replay/[sessionId]/page.tsx |
| Compare page | app/compare/[idA]/[idB]/page.tsx |
| Mock data | backend/data/mock_sessions.py |
| Session routes | backend/routes/sessions.py |
| Heat dissipation | backend/services/thermal_service.py |

---

## Common Failure Points

### What Usually Goes Wrong

❌ **Forgetting `ssr: false` on 3D components** → SSR crashes on WebGL  
✅ Use: `dynamic(() => import('...'), { ssr: false })`

❌ **Recomputing heat dissipation frontend** → Wrong values (missing context)  
✅ Use: `frame.heat_dissipation_rate_celsius_per_sec` (pre-calculated)

❌ **Not handling sparse thermal data** → 3D color flickers  
✅ Use: `extractCenterTemperatureWithCarryForward()` (walks backwards)

❌ **Sending <1000 or >5000 frames per POST** → 400 error  
✅ Batch frames in 1000-5000 chunks

❌ **Mutating raw frame data** → Breaks playback  
✅ All utils return new objects/arrays

❌ **Accessing `thermal_snapshots` without guards** → Crashes on sensor-only frames  
✅ Check: `frame.has_thermal_data && frame.thermal_snapshots?.length`

---

## Data Models (Key Fields Only)

**Session:** `session_id`, `frames[]`, `status`, `frame_count`, `start_time`, `weld_type`

**Frame:** `timestamp_ms`, `volts?`, `amps?`, `angle_degrees?`, `thermal_snapshots[]`, `heat_dissipation_rate_celsius_per_sec?`, `has_thermal_data`

**ThermalSnapshot:** `distance_mm`, `readings[]` (exactly 5: center, north, south, east, west)

**TemperaturePoint:** `direction`, `temp_celsius`

**FrameDelta:** All Frame fields as `_delta` (sessionA - sessionB), `thermal_deltas[]`

---

## When to Read Full ARCHITECTURE.md

- Implementing new features (scoring, new visualizations)
- Modifying data models or validation
- Adding new API endpoints
- Performance optimization
- Database migrations
- Understanding physics model for mock data

**For 90% of tasks, this document is enough.**

---

**Related:** `LEARNING_LOG.md` (past mistakes), `ARCHITECTURE.md` (full details), `.cursorrules` (AI config)
