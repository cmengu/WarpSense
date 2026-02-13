# Tech Stack MVP Architecture

> Shipyard Welding MVP: record, replay, and analyze welding sessions. Backend (Python/FastAPI/PostgreSQL) → API → Frontend (Next.js/TypeScript).

---

## Critical Points of Failure

| Failure | Rule |
|---------|------|
| Frame timing | Frames MUST be 10 ms apart; no duplicate timestamps |
| Ingestion limits | 1000–5000 frames per request (hard limit); pagination required for >10k |
| Heat dissipation | Calculated ONLY at ingestion; frontend never recomputes |
| WebGL | TorchViz3D requires dynamic import with `ssr: false` |
| Thermal data | Sparse (~100 ms); use `extractCenterTemperatureWithCarryForward` |
| Thermal snapshots | Exactly 5 readings (center + 4 cardinal); each snapshot has 1 center reading |

---

## Key Design Decisions

- **Append-only:** Never edit raw sensor data; only add new frames
- **Backend source of truth:** Heat dissipation, scoring, validation live in backend
- **No conversion layer:** snake_case everywhere; TypeScript mirrors Pydantic
- **Exact replay:** No interpolation; `getFrameAtTimestamp` → exact match, else nearest before, else first frame
- **Never silently fail:** Guard `has_thermal_data`, `thermal_snapshots`, `readings` before access

---

## Data Models

| Model | Key Fields |
|-------|------------|
| Frame | `timestamp_ms`, `volts`, `amps`, `angle_degrees`, `thermal_snapshots[]`, `heat_dissipation_rate_celsius_per_sec` |
| Session | `session_id`, `frames[]`, `status`, `frame_count`, `thermal_sample_interval_ms` |
| ThermalSnapshot | `distance_mm`, `readings` (5 × TemperaturePoint) |

**Status transitions:** RECORDING → INCOMPLETE/COMPLETE/FAILED; COMPLETE/FAILED → ARCHIVED only.

---

## Integration Points

**API:** `fetchSession(id)`, `addFrames(id, frames)` — `lib/api.ts`  
**Utils:** `extractHeatmapData`, `extractAngleData`, `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward` — `utils/frameUtils.ts`, `heatmapData.ts`, `angleData.ts`  
**Hooks:** `useSessionMetadata`, `useFrameData`, `useSessionComparison`  
**Components:** HeatMap(sessionId, data), TorchAngleGraph(sessionId, data), TorchViz3D(angle, temp, label?)

---

## Constraints

| Constraint | Value |
|------------|-------|
| Frame interval | 10 ms (100 Hz) |
| Thermal interval | ~100 ms (5 Hz) |
| Frames/request | 1000–5000 |
| Bundle (3D) | ~500KB gzipped |
| DATABASE_URL | Required; no fallback |

---

## Key Files

| Concern | Backend | Frontend |
|---------|---------|----------|
| Session/Frame | models/session.py, frame.py | types/session.ts, frame.ts |
| Heat dissipation | services/thermal_service.py | frameUtils (extract only) |
| Comparison | services/comparison_service.py | useSessionComparison |
| Heatmap/Angle | — | heatmapData.ts, angleData.ts |
| 3D | — | TorchViz3D.tsx |
| API | routes/sessions.py | lib/api.ts |
