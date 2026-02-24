# WarpSense — Context Part 2

> **Purpose:** Tech stack, architecture, 3D viz, thresholds, micro-feedback, and critical constraints.  
> **Last updated:** 2026-02-21

---

## 1. Tech Stack & Architecture

### Stack Summary

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLAlchemy ORM |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind |
| 3D | Three.js, @react-three/fiber, @react-three/drei |
| Styling | Tailwind CSS, Orbitron + JetBrains Mono (3D) |

### System Pattern

```
Frontend (Next.js) → Backend (FastAPI) → PostgreSQL
ESP32 Sensors → Backend (bulk ingest)
```

### Design Principles

| Principle | Meaning |
|-----------|---------|
| Append-only | Raw sensor data never edited; only new data added |
| Single source of truth | Backend calculates once; frontend consumes |
| Exact replays | Frontend shows exactly what happened — no guessing |
| snake_case everywhere | Backend JSON → frontend types; no conversion layer |
| Never mutate raw data | Extraction/transformation are pure functions |

---

## 2. Data Flow (End-to-End)

```
Mock/Live → PostgreSQL → GET /api/sessions/:id
  → fetchSession(sessionId)
  → useFrameData(frames) → thermal_frames
  → extractHeatmapData() / extractAngleData() / extractCenterTemperatureWithCarryForward()
  → HeatMap, TorchAngleGraph, TorchViz3D, HeatmapPlate3D
```

### Frame Resolution

- **getFrameAtTimestamp(frames, timestamp):** Exact match → nearest before → first frame
- **extractCenterTemperatureWithCarryForward:** Walks backwards for last known temp (thermal sparse at 5 Hz)

---

## 3. Critical Constraints (Never Violate)

### Data Integrity

- Append-only raw sensor data
- Backend is source of truth for heat dissipation (calculated at ingestion)
- Never mutate raw data; all extraction is pure

### Timing & Limits

- Frame interval: 10 ms (100 Hz)
- Bulk ingestion: 1000–5000 frames per POST
- Thermal sampling: Sparse (5 Hz / every 100 ms)
- Session max: 30,000 frames

### Frontend

- **SSR safety:** WebGL/Canvas MUST use `dynamic(..., { ssr: false })`
- **WebGL context limit:** Max 1–2 Canvas per page (~8–16 per tab)
- **Thermal continuity:** Use `extractCenterTemperatureWithCarryForward` for 3D color

---

## 4. Threshold Configuration

### What Exists

Threshold admin UI — CRUD for mig/tig/stick/flux_core. Backend: GET/PUT /api/thresholds; in-memory cache; invalidated on PUT.

### Files

| File | Purpose |
|------|---------|
| `backend/routes/thresholds.py` | GET /api/thresholds, PUT /api/thresholds/:weld_type |
| `backend/services/threshold_service.py` | get_thresholds, get_all_thresholds, invalidate_cache |
| `backend/models/thresholds.py` | WeldTypeThresholds, WeldThresholdUpdate |
| `backend/alembic/versions/004_weld_thresholds_and_process_type.py` | weld_thresholds table |
| `my-app/src/app/admin/thresholds/page.tsx` | Tabs, form, handleSave |
| `my-app/src/components/admin/AngleArcDiagram.tsx` | SVG semicircle (target angle); aria-label |
| `my-app/src/types/thresholds.ts` | WeldTypeThresholds, ActiveThresholdSpec |
| `my-app/src/lib/api.ts` | fetchThresholds(), updateThreshold() |

### Validation

angle_target > 0; warning_margin ≤ critical_margin; thermal_warning ≤ thermal_critical. Known process types: mig, tig, stick, flux_core only.

---

## 5. TorchViz3D — 3D Visualization

### Purpose

3D torch + weld pool for replay. Angle and center temp drive rotation and color. Industrial typography (Orbitron, JetBrains Mono), PBR, HDRI, WebGL context-loss handling.

### Props (unchanged)

```typescript
interface TorchViz3DProps {
  angle: number;   // degrees; 45 = upright
  temp: number;    // °C; drives weld pool color
  label?: string;
}
```

### Temp → Color

- Blue (<310°C) → Yellow (310–455°C) → White (>455°C) — aligned with WarpSense blue/purple theme

### Files

| File | Purpose |
|------|---------|
| `my-app/src/components/welding/TorchViz3D.tsx` | Main 3D component; HUD; context-loss overlay |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | Unified torch + thermally-colored metal |
| `my-app/src/components/welding/HeatmapPlate3D.tsx` | 3D warped plate; thermal vertex displacement |
| `my-app/src/components/welding/HeatmapPlate3D.tsx` | Replaces HeatMap when thermal_frames.length > 0 |
| `my-app/src/app/dev/torch-viz/page.tsx` | Dev demo; single instance; dynamic import |
| `my-app/src/__tests__/drei-import.test.ts` | OrbitControls, Environment, ContactShadows |
| `my-app/src/__tests__/components/welding/TorchViz3D.test.tsx` | HUD, props, context-loss overlay |
| `documentation/WEBGL_CONTEXT_LOSS.md` | WebGL context loss reference |
| `my-app/constants/webgl.ts` | MAX_TORCHVIZ3D_PER_PAGE |

### Constraints

- Props unchanged: angle, temp, label
- SSR: always `dynamic(..., { ssr: false })`
- Max 1–2 Canvas per page
- Typography: Orbitron (headers), JetBrains Mono (data) — no Inter/Arial

### Metal Plane Clipping (welding3d)

`welding3d.ts` constants: WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y. TorchWithHeatmap3D uses WORKPIECE_GROUP_Y so metal never clips through torch. metal_surface_max_Y < weld pool center; METAL_TO_TORCH_GAP = 0.15.

---

## 6. WarpSense Micro-Feedback

### Purpose

Frame-level actionable guidance — angle drift and thermal symmetry alerts. Client-side `generateMicroFeedback(frames)` → MicroFeedbackItem[]; FeedbackPanel + TimelineMarkers for click-to-scrub.

### Thresholds

- Angle: target 45°, warning ±5°, critical ±15°
- Thermal: max(|N-S|, |E-W|) ≥ 20°C
- Cap 50 items per type; sorted by frameIndex

### Files

| File | Purpose |
|------|---------|
| `my-app/src/types/micro-feedback.ts` | MicroFeedbackType, MicroFeedbackSeverity, MicroFeedbackItem (frameIndex, type) |
| `my-app/src/lib/micro-feedback.ts` | generateMicroFeedback(frames) |
| `my-app/src/types/ai-feedback.ts` | FeedbackItem extended with optional frameIndex, type |
| `my-app/src/components/welding/FeedbackPanel.tsx` | SEVERITY_STYLES (info/warning/critical); frames?; onFrameSelect?; data-testid="micro-feedback-item" |
| `my-app/src/components/welding/TimelineMarkers.tsx` | Severity-colored markers; click-to-scrub |

### Integration

Replay page: `useMemo(() => generateMicroFeedback(frames))`; FeedbackPanel + TimelineMarkers wired; FeedbackPanel shows clickable micro items.

---

## 7. Key Design Decisions

| Decision | Why |
|----------|-----|
| Heatmap = CSS Grid | Recharts ScatterChart overlaps at 7500+ points |
| Playback = setInterval | RAF runs 60fps; setInterval 100fps shows every 10ms frame |
| Status = One-Way (RECORDING→COMPLETE→ARCHIVED) | Prevents data corruption |
| Heat dissipation = Backend only | Thermal sparse; backend has full context |
| Temperature colors = 8 anchors | Blue→purple gradient (0–500°C) |

---

## 8. File Map (Critical Paths)

| Need | File |
|------|------|
| Session/Frame types | types/session.ts, types/frame.ts |
| Thermal types | types/thermal.ts |
| API client | lib/api.ts |
| Frame utilities | utils/frameUtils.ts |
| Heatmap extraction | utils/heatmapData.ts |
| Thermal interpolation | utils/thermalInterpolation.ts |
| Session comparison | hooks/useSessionComparison.ts |
| Replay page | app/replay/[sessionId]/page.tsx |
| Compare page | app/compare/[sessionIdA]/[sessionIdB]/page.tsx |
| Mock data | backend/data/mock_sessions.py |
| Session routes | backend/routes/sessions.py |
| Heat dissipation | backend/services/thermal_service.py |
| Micro-feedback | lib/micro-feedback.ts |
| WebGL constants | constants/webgl.ts |

---

## 9. Common Failure Points

| ❌ Wrong | ✅ Right |
|---------|---------|
| Forgetting `ssr: false` on 3D | `dynamic(..., { ssr: false })` |
| Recomputing heat dissipation frontend | Use `frame.heat_dissipation_rate_celsius_per_sec` |
| Not handling sparse thermal | `extractCenterTemperatureWithCarryForward()` |
| <1000 or >5000 frames per POST | Batch in 1000–5000 chunks |
| Mutating raw frame data | All utils return new objects |
| Missing thermal guards | Check `has_thermal_data && thermal_snapshots?.length` |
| Multiple Canvases (6+) | Max 1–2 per page; see LEARNING_LOG.md |

---

## 10. Wi-Fi / Connectivity (Metal Clipping Fix)

Phase 2 **metal plane clipping** fix:

- `welding3d.ts`: WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y
- TorchWithHeatmap3D: WORKPIECE_GROUP_Y; workpiece/ring/grid/shadows use constants
- Clipping assertions in welding3d.test.ts
- metal_surface_max_Y < weld pool center; METAL_TO_TORCH_GAP = 0.15

---

## 11. Related Docs

| File | Purpose |
|------|---------|
| `LEARNING_LOG.md` | Past mistakes (esp. WebGL context loss) |
| `documentation/WEBGL_CONTEXT_LOSS.md` | WebGL context loss reference |
| `.cursorrules` | Data integrity contract |
| `context_part_1.md` | Agent 1–3, Seagull, demo, mock, PDF |
