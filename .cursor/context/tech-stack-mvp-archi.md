# Overall Stack MVP v1 — Consolidated Architecture

> **Purpose:** Single source of truth for the Shipyard Welding MVP stack. Consolidates backend, frontend, 3D visualization, mock data, tests, and integration patterns.
>
> **Source documents:** backend-skeleton-architecture.md, frontend-skeleton-architecture.md, mock-tests-and-validation-tests.md, 3d-frontend-implementation.md, overall-stack-context.md
>
> **Last updated:** February 2025

---

## 1. Project Overview

### Purpose

Record welding sessions, replay them, and analyze quality via thermal profiles, torch angle, heat dissipation, and session-to-session comparison.

### Design Principles

| Principle | Meaning |
|-----------|---------|
| Append-only | Raw sensor data is never edited; only new data is added |
| Single source of truth | Backend calculates everything once; frontend consumes |
| Exact replays | Frontend shows exactly what happened — no guessing or interpolation |
| Type safety | Explicit types/units everywhere (`timestamp_ms`, `temp_celsius`, `distance_mm`) |
| Validation everywhere | Catch bad data early; never silently fail |
| Never guess values | If information is missing, return null/explicit error |
| Never mutate raw data | Extraction and transformation are pure |

### Stack Summary

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLAlchemy ORM |
| Frontend | React, Next.js, TypeScript |
| Styling | Tailwind CSS |
| 3D | Three.js, @react-three/fiber |

---

## 2. End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ ORIGIN: Mock Data OR Live Sensors                                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘
    Mock: backend/data/mock_sessions.py          Live: POST /api/sessions/{id}/frames
    generate_expert_session()                    1000–5000 frames/request
    generate_novice_session()                    addFrames(sessionId, frames)
                        │                                        │
                        ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ PERSISTENCE: PostgreSQL                                                             │
│   sessions table → SessionModel (ORM)                                                │
│   frames table → FrameModel.frame_data (JSONB) — full Frame per row                 │
│   Cascade delete, indexed by session_id + timestamp_ms                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ API: GET /api/sessions/{session_id}                                                  │
│   routes/sessions.py → SessionModel + FrameModel                                    │
│   include_thermal, time_range, pagination, streaming (>10000 frames)                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ FRONTEND: lib/api.ts → fetchSession(sessionId)                                       │
│   → Session (typed, snake_case)                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ REPLAY PAGE: app/replay/[sessionId]/page.tsx                                         │
│   useSessionMetadata(session) → duration, weld_type, frame_count                     │
│   useFrameData(frames) → thermal_frames, all_frames                                 │
│   extractHeatmapData() → HeatMap │ extractAngleData() → TorchAngleGraph               │
│   getFrameAtTimestamp() + extractCenterTemperatureWithCarryForward() → TorchViz3D   │
│   ScorePanel (placeholder)                                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Backend Architecture

### Entry Point — `backend/main.py`

- FastAPI app, title "Dashboard API", version 1.0.0
- CORS: `http://localhost:3000` only (Next.js default)
- GZip middleware (min 1000 bytes)
- Routers: `dashboard_router` (root), `sessions_router` (prefix `/api`)
- Health: `GET /health` → `{"status": "ok"}`

### Models

| Model | File | Key Fields |
|-------|------|------------|
| TemperaturePoint | models/thermal.py | `direction`, `temp_celsius` |
| ThermalSnapshot | models/thermal.py | `distance_mm`, `readings` (exactly 5) |
| Frame | models/frame.py | `timestamp_ms`, `volts`, `amps`, `angle_degrees`, `thermal_snapshots`, `heat_dissipation_rate_celsius_per_sec` |
| Session | models/session.py | `session_id`, `operator_id`, `frames`, `status`, `frame_count`, config fields |
| FrameDelta | models/comparison.py | `timestamp_ms`, `*_delta` fields (session_a - session_b) |
| SessionScore | models/scoring.py | `total`, `rules[]` |

### Session Status Transitions

```
RECORDING → INCOMPLETE, COMPLETE, FAILED
INCOMPLETE → RECORDING, FAILED, ARCHIVED
COMPLETE → ARCHIVED only
FAILED → ARCHIVED only
ARCHIVED → (terminal)
```

### Database

- **Connection:** `database/connection.py` — loads `backend/.env`, `DATABASE_URL` required (no fallback)
- **Tables:** `sessions`, `frames` (JSONB `frame_data` for full Frame)
- **Migrations:** Alembic (`001_initial_schema`, `002_add_disable_sensor_continuity_checks`)

### Services

| Service | Purpose |
|---------|---------|
| thermal_service.py | `calculate_heat_dissipation(prev, curr)` → (prev_center - curr_center) / 0.1 °C/sec |
| comparison_service.py | `compare_sessions(a, b)` → FrameDelta[] aligned by timestamp |

### Routes

| Endpoint | Status |
|----------|--------|
| GET /api/dashboard | ✅ Mock data from data/mock_data.py |
| GET /api/sessions | 501 Not Implemented |
| GET /api/sessions/{id} | ✅ Pagination, streaming, include_thermal |
| POST /api/sessions/{id}/frames | ✅ 1000–5000 frames, lock, heat dissipation at ingestion |
| GET /api/sessions/{id}/features | 501 Not Implemented |
| GET /api/sessions/{id}/score | 501 Not Implemented |

### Key Constraints (Backend)

| Constraint | Enforced In |
|------------|-------------|
| Frames 10 ms apart | Session validator, routes/sessions.py |
| No duplicate timestamps | DB UNIQUE, routes validator |
| 5 readings per thermal snapshot | ThermalSnapshot Pydantic |
| Heat dissipation at ingestion only | routes/sessions.py + thermal_service |
| 1000–5000 frames per request | routes/sessions.py |
| Pagination for >10k frames | routes/sessions.py |

---

## 4. Frontend Architecture

### Data Flow

```
Backend API → lib/api.ts (fetchSession, addFrames)
  → Session / Frame[] (types)
  → Constants (labels, ranges, validation)
  → Utils (frameUtils, heatmapData, angleData)
  → Hooks (useSessionMetadata, useFrameData, useSessionComparison)
  → Components (HeatMap, TorchAngleGraph, TorchViz3D)
```

### Types (snake_case, no conversion layer)

| Type | File | Mirrors Backend |
|------|------|-----------------|
| ThermalDirection, TemperaturePoint, ThermalSnapshot | types/thermal.ts | models/thermal.py |
| Frame | types/frame.ts | models/frame.py |
| Session, SessionStatus | types/session.ts | models/session.py |
| FrameDelta, ThermalDelta | types/comparison.ts | models/comparison.py |

### Utilities

| Utility | File | Purpose |
|---------|------|---------|
| extractCenterTemperature | frameUtils.ts | Safe thermal access (guards has_thermal_data, readings) |
| extractCenterTemperatureWithCarryForward | frameUtils.ts | Last-known temp for sparse thermal (3D) |
| getFrameAtTimestamp | frameUtils.ts | Exact match → nearest before → first frame |
| extractHeatmapData | heatmapData.ts | Time × distance → temp grid |
| extractAngleData | angleData.ts | Timestamp → angle time series |

### Hooks

| Hook | Purpose |
|------|---------|
| useSessionMetadata | Duration, weld_type_label, status, formatStartTime |
| useFrameData | thermal_frames, all_frames, time-range filtered |
| useSessionComparison | deltas, shared_count (mirrors backend compare_sessions) |

### Constants

| File | Content |
|------|---------|
| metals.ts | METAL_TYPES, METAL_TYPE_LABELS, METAL_PROPERTIES |
| sensors.ts | SENSOR_RANGES, SENSOR_UNITS, TEMPERATURE_RANGE_CELSIUS |
| validation.ts | FRAME_INTERVAL_MS (10), limits, ERROR_MESSAGES |

### Replay Page Components

| Component | Props | Data Source |
|-----------|-------|--------------|
| HeatMap | sessionId, data?: HeatmapData | extractHeatmapData(thermal_frames) |
| TorchAngleGraph | sessionId, data?: AngleData | extractAngleData(frames) |
| ScorePanel | sessionId, score? | Placeholder ("Coming soon") |
| TorchViz3D | angle, temp, label? | getFrameAtTimestamp + extractCenterTemperatureWithCarryForward |

---

## 5. 3D Frontend (TorchViz3D)

### Purpose

Side-by-side 3D torch + weld pool for Expert vs Novice comparison. Torch angle and center temp drive rotation and color.

### Architecture

```
TorchViz3D
├── Canvas (@react-three/fiber, ssr: false)
├── SceneContent
│   ├── Lighting (ambient, directional, point)
│   ├── Torch group (cylinder handle + sphere weld pool)
│   └── Workpiece (plane)
```

### Data Flow

```
currentTimestamp
  → getFrameAtTimestamp(session.frames, currentTimestamp)
  → angle_degrees → torch rotation ((angle - 45) * π/180)
  → extractCenterTemperatureWithCarryForward(frames, currentTimestamp) → temp
  → getTempColor(temp): blue (<310°C), yellow (310–455°C), red (>455°C)
```

### Integration

- **Replay page:** Two TorchViz3D side-by-side (primary session + comparison)
- **Dynamic import:** `ssr: false` — WebGL requires browser
- **Dev page:** `/dev/torch-viz` for isolated verification

### Dependencies

- three (~0.169), @react-three/fiber (~8.17) — ~500KB gzipped

---

## 6. Mock Data & Tests

### Mock Data — `backend/data/mock_sessions.py`

| Function | Frames | Use |
|----------|--------|-----|
| generate_expert_session() | 1500 | Stable amps, volts, angle; continuity ON |
| generate_novice_session() | 1500 | Erratic signals; thermal gap; continuity OFF |
| generate_large_session() | 30,000 | Performance tests |

**Physics model:** angle → north/south asymmetry; arc_power → center temp; distance → east > west.

### Backend Tests

| File | Purpose |
|------|---------|
| test_mock_sessions.py | Session structure, thermal, heat dissipation, comparison |
| test_validation.py | Model rejection (Session, Frame, ThermalSnapshot) |
| test_comparison_edge_cases.py | compare_sessions edge cases |
| test_heat_dissipation.py | thermal_service edge cases |
| test_serialization.py | Python round-trip, snake_case |
| test_api_integration.py | GET /api/sessions (conditional: SQLAlchemy) |
| test_performance.py | Benchmarks (conditional: pytest-benchmark) |

### Frontend Tests

| File | Purpose |
|------|---------|
| serialization.test.ts | JSON parse, validateSession/validateFrame |
| frameUtils.test.ts | extract*, filter*, hasRequiredSensors |
| page.test.tsx (replay) | Mocked fetchSession, component render |

### Test Data Flow

```
mock_sessions.generate_* → Session (Pydantic)
  → Backend validation tests
  → model_dump(mode="json") → JSON
  → Frontend serialization / frameUtils tests
  → API integration (in-memory SQLite → GET)
  → Replay page (fetchSession → components)
```

---

## 7. Canonical Types & Validation Boundaries

| Layer | Models | Validators |
|-------|--------|------------|
| Backend | Pydantic (Session, Frame, ThermalSnapshot, etc.) | frame_count match, timestamps ~10 ms, thermal distances, sensor continuity |
| API | JSON snake_case, ISO 8601, SessionStatus string | Same as Pydantic model_dump |
| Frontend | TypeScript interfaces | validateSession, validateFrame, validateThermalSnapshot (lightweight) |

**Rule:** Frontend never recomputes heat dissipation; backend is source of truth.

---

## 8. Key File Map

| Concern | Backend | Frontend |
|---------|---------|----------|
| Session model | models/session.py | types/session.ts |
| Frame model | models/frame.py | types/frame.ts |
| Thermal model | models/thermal.py | types/thermal.ts |
| Mock data | data/mock_sessions.py | — |
| Heat dissipation | services/thermal_service.py | utils/frameUtils.ts (extract only) |
| Session comparison | services/comparison_service.py | hooks/useSessionComparison.ts |
| Heatmap | — | utils/heatmapData.ts |
| Angle | — | utils/angleData.ts |
| 3D torch | — | components/welding/TorchViz3D.tsx |
| Scoring | scoring/rule_based.py (stub) | ScorePanel.tsx |
| API | routes/sessions.py | lib/api.ts |
| Replay | — | app/replay/[sessionId]/page.tsx |

---

## 9. Cross-Cutting Constraints

| Constraint | Where |
|------------|-------|
| Raw data append-only | routes/sessions.py |
| Heat dissipation at ingestion only | thermal_service, routes |
| Frontend never mutates raw data | frameUtils, heatmapData, angleData |
| snake_case, no conversion layer | All types, API |
| Guard has_thermal_data, thermal_snapshots, readings | frameUtils, heatmapData, useSessionComparison |
| Units in names | All models |
| Exact replay (no interpolation) | getFrameAtTimestamp, no synthetic frames |
| WebGL client-only | TorchViz3D dynamic import ssr: false |

---

## 10. Directory Structures

### Backend

```
backend/
├── main.py
├── models.py                    # Dashboard (root-level)
├── models/                      # Canonical welding models
├── database/                    # SQLAlchemy, connection
├── routes/                      # dashboard, sessions
├── services/                    # thermal, comparison
├── features/                    # extractor (stubs)
├── scoring/                     # rule_based (stubs)
├── data/                        # mock_data, mock_sessions
├── alembic/
└── tests/
```

### Frontend

```
my-app/src/
├── types/                       # thermal, frame, session, comparison
├── lib/api.ts
├── constants/                   # metals, sensors, validation
├── utils/                       # frameUtils, heatmapData, angleData
├── hooks/                       # useSessionMetadata, useFrameData, useSessionComparison
├── app/replay/[sessionId]/
├── components/welding/          # HeatMap, TorchAngleGraph, TorchViz3D, ScorePanel
└── __tests__/
```

---

## 11. API Contracts

### GET /api/sessions/{session_id}

| Param | Type | Default | Purpose |
|-------|------|---------|---------|
| include_thermal | bool | true | Include thermal_snapshots in frames |
| time_range_start | ms | — | Filter frames |
| time_range_end | ms | — | Filter frames |
| limit | 1–10000 | 1000 | Pagination |
| offset | >=0 | 0 | Pagination |
| stream | bool | false | Chunked JSON for >1000 frames |

**Response:** `Session` (id, frames[], metadata)

### POST /api/sessions/{session_id}/frames

**Request:** `Frame[]` (1000–5000 frames)

**Response:** `{ status, successful_count, failed_frames?, next_expected_timestamp, can_resume }`

---

## 12. Source Document Index

| Source File | Content Summary |
|-------------|-----------------|
| backend-skeleton-architecture.md | Models, DB, routes, services, validators, directory structure |
| frontend-skeleton-architecture.md | Types, utils, hooks, components, constants |
| mock-tests-and-validation-tests.md | Mock generators, test data flow, validation coverage |
| 3d-frontend-implementation.md | TorchViz3D, frame resolution, temperature color mapping |
| overall-stack-context.md | End-to-end flow, mock vs live, analysis capabilities |

---

**Maintenance:** Update after significant architecture changes. Run tests to verify: `cd backend && pytest -v` and `cd my-app && npm test`.

## 3D FRONTEND IMPLEMENTATION
# 3D Frontend Implementation — TorchViz3D

Documentation for the side-by-side 3D torch + weld pool visualization feature. High-level overview, architecture, and integration details.

**Reference:** `.cursor/plans/side-by-side_3d_comparison_f15447b8.plan.md`

---

## 1. High-Level Overview

### Purpose

**TorchViz3D** renders a 3D visualization of a welding torch and weld pool for side-by-side comparison (Expert vs Novice) on the replay page. The torch angle (`angle_degrees`) and weld pool temperature (center temp in °C) are driven by per-frame sensor data, providing an intuitive visual comparison of technique and heat application.

### Key Features

- **3D torch mesh:** Cylinder handle + sphere weld pool at tip
- **Dynamic rotation:** Torch rotates based on `angle_degrees` (45° = ideal upright)
- **Temperature-driven color:** Weld pool sphere color reflects center temperature (blue → yellow → red)
- **Synced playback:** Both 3D scenes update at the same `currentTimestamp` for side-by-side comparison
- **Visual consistency:** Temperature color bands align with 2D HeatMap gradient

### Current Status

✅ **Implemented:** TorchViz3D component, frame resolution utilities, replay page integration  
✅ **In use:** Replay page shows side-by-side 3D when comparison session is loaded  
🔄 **Future:** Compare page integration (optional enhancement)

---

## 2. Architecture

### 2.1 Component Structure

```
TorchViz3D (public component)
├── Wrapper div (h-64, rounded, border)
├── Label (optional, e.g. "Current Session" | "Comparison")
└── Canvas (@react-three/fiber)
    └── SceneContent
        ├── Lighting (ambient + directional + point lights)
        ├── Torch group (ref for rotation)
        │   ├── Handle (cylinder mesh)
        │   └── Weld pool (sphere mesh, emissive material)
        └── Workpiece (plane mesh, receives shadow)
```

### 2.2 Data Flow

```
Replay Page State
├── sessionData (primary session)
├── comparisonSession (optional, e.g. sess_novice_001)
└── currentTimestamp (shared timeline)

currentTimestamp
├── getFrameAtTimestamp(sessionData.frames, currentTimestamp)
│   └── → frameA (expert)
│       ├── angle_degrees → TorchViz3D angle prop
│       └── extractCenterTemperatureWithCarryForward(...)
│           └── → tempA → TorchViz3D temp prop
│
└── getFrameAtTimestamp(comparisonSession.frames, currentTimestamp)
    └── → frameB (novice)
        ├── angle_degrees → TorchViz3D angle prop
        └── extractCenterTemperatureWithCarryForward(...)
            └── → tempB → TorchViz3D temp prop

Side-by-side render:
┌─────────────────────────────────────┐
│  TorchViz3D (angleA, tempA)         │  TorchViz3D (angleB, tempB)
│  "Current Session"                  │  "Comparison (Novice)"
└─────────────────────────────────────┘
```

### 2.3 Integration Points

**Replay Page** (`app/replay/[sessionId]/page.tsx`):
- Fetches primary session + optional comparison session (`sess_novice_001`)
- Uses `getFrameAtTimestamp` and `extractCenterTemperatureWithCarryForward` to resolve current frame data
- Renders two `TorchViz3D` components side-by-side in a grid
- Dynamic import with `ssr: false` to avoid Next.js SSR issues with WebGL

**Compare Page** (`app/compare/[sessionIdA]/[sessionIdB]/page.tsx`):
- Not yet integrated (future enhancement)
- Would use same pattern: resolve frames at `currentTimestamp` for both sessions

---

## 3. Technical Implementation

### 3.1 Dependencies

- **three** (`^0.169.0`): Core 3D library
- **@react-three/fiber** (`^8.17.10`): React renderer for Three.js
- **@types/three** (`^0.169.0`): TypeScript types

**Bundle impact:** ~500KB gzipped (acceptable for demo/incubation).

### 3.2 Rotation Implementation

**Pattern:** `useRef` + `useFrame` (React Three Fiber pattern)

```typescript
const torchRef = useRef<THREE.Group>(null);

useFrame(() => {
  if (torchRef.current) {
    // 45° = upright; deviation rotates torch (radians)
    torchRef.current.rotation.x = ((angle - 45) * Math.PI) / 180;
  }
});
```

**Why useFrame:**
- Updates every frame (60fps) for smooth animation
- Avoids mutating refs during render (React anti-pattern)
- R3F-recommended pattern for per-frame updates

**Alternative considered:** `useEffect` + ref works but updates less smoothly (only on prop change, not every frame).

### 3.3 Temperature → Color Mapping

**Aligned with HeatMap gradient** for visual consistency:

```typescript
function getTempColor(temp: number): THREE.Color {
  if (temp < 310) return new THREE.Color(0x3b82f6); // Blue (<310°C)
  if (temp < 455) return new THREE.Color(0xeab308); // Yellow (310-455°C)
  return new THREE.Color(0xef4444); // Red (>455°C)
}
```

**Breakpoints match HeatMap conceptual bands:**
- Blue: Cold (<310°C)
- Yellow: Medium (310-455°C)
- Red: Hot (>455°C)

**Weld pool material:** Uses `emissive` + `emissiveIntensity={1.2}` for visible glow effect.

### 3.4 Frame Resolution Utilities

**`getFrameAtTimestamp(frames, timestamp)`** (`utils/frameUtils.ts`):
- Exact match first: `frames.find(f => f.timestamp_ms === timestamp)`
- Else: Nearest frame with `timestamp_ms <= timestamp` (walk backwards)
- Else: `frames[0]` (all frames after timestamp)

**`extractCenterTemperatureWithCarryForward(frames, currentTimestamp)`** (`utils/frameUtils.ts`):
- Finds frame at or before `currentTimestamp` (via `getFrameAtTimestamp` logic)
- Walks backwards to find last frame with thermal data
- Returns center temp from that frame, or `450°C` fallback

**Why carry-forward:** Thermal data is sparse (~100ms intervals); weld pool color should not flash every 10 frames. Carry-forward provides smooth visual continuity.

---

## 4. Component API

### Props

```typescript
interface TorchViz3DProps {
  /** Torch angle in degrees (e.g. 45 = ideal). Drives rotation around X. */
  angle: number;
  /** Center temperature in °C. Drives weld pool sphere color (blue → yellow → red). */
  temp: number;
  /** Optional label shown above the canvas (e.g. "Current Session", "Comparison"). */
  label?: string;
}
```

### Usage Example

```typescript
import dynamic from 'next/dynamic';

const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  { ssr: false }
);

// In component:
<TorchViz3D
  angle={frame?.angle_degrees ?? 45}
  temp={extractCenterTemperatureWithCarryForward(frames, currentTimestamp)}
  label="Current Session"
/>
```

---

## 5. Scene Configuration

### Camera

```typescript
camera={{ position: [0.8, 0.4, 1.2], fov: 50 }}
```

**Position:** Slightly elevated and offset for clear view of torch angle and weld pool.

### Lighting

- **Ambient light:** `intensity={0.8}` (bright base illumination)
- **Directional light:** `position={[5, 8, 5]}, intensity={1.2}, castShadow` (main light source)
- **Point lights:** Two at `[-3, 4, 3]` and `[3, 4, -3]`, `intensity={0.6}` (fill lighting)

### Geometry

- **Torch handle:** Cylinder (`radius: 0.04`, `height: 0.8`, `segments: 16`)
- **Weld pool:** Sphere (`radius: 0.12`, `segments: 24`)
- **Workpiece:** Plane (`width: 2`, `height: 2`)

### Materials

- **Handle:** `metalness={0.6}, roughness={0.4}` (metallic gray)
- **Weld pool:** `emissive={color}, emissiveIntensity={1.2}, metalness={0.1}, roughness={0.3}` (glowing, color-driven)
- **Workpiece:** `metalness={0.3}, roughness={0.7}` (matte metal)

---

## 6. Integration with Replay Page

### Current Implementation

**Location:** `app/replay/[sessionId]/page.tsx`

**Flow:**
1. Fetch primary session (`sessionId`)
2. Fetch comparison session (`sess_novice_001` hardcoded for incubation)
3. Resolve frames at `currentTimestamp` for both sessions
4. Render side-by-side `TorchViz3D` components above HeatMap/TorchAngleGraph

**Key code pattern:**

```typescript
const currentFrame = getFrameAtTimestamp(sessionData.frames, currentTimestamp);
const comparisonFrame = comparisonSession
  ? getFrameAtTimestamp(comparisonSession.frames, currentTimestamp)
  : null;

const tempA = extractCenterTemperatureWithCarryForward(
  sessionData.frames,
  currentTimestamp
);
const tempB = comparisonSession
  ? extractCenterTemperatureWithCarryForward(
      comparisonSession.frames,
      currentTimestamp
    )
  : 450;

// Render:
<div className="grid grid-cols-2 gap-8 mb-8">
  <TorchViz3D
    angle={currentFrame?.angle_degrees ?? 45}
    temp={tempA}
    label="Current Session"
  />
  {comparisonFrame && (
    <TorchViz3D
      angle={comparisonFrame.angle_degrees ?? 45}
      temp={tempB}
      label="Comparison (Novice)"
    />
  )}
</div>
```

### Dynamic Import (SSR Safety)

```typescript
const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  { ssr: false }
);
```

**Why:** WebGL/Canvas requires browser environment; Next.js SSR would fail. Dynamic import with `ssr: false` ensures component only loads on client.

---

## 7. Constraints and Edge Cases

### Constraints

- **Exact replay:** No interpolation; uses exact frame at `currentTimestamp` (via `getFrameAtTimestamp`)
- **Thermal continuity:** Carry-forward last known temp when frame has no thermal data
- **Client-only:** Component must run in browser (no SSR); use dynamic import
- **Bundle size:** ~500KB gzipped acceptable for demo; consider lazy loading if needed

### Edge Cases Handled

- **No thermal data at current frame:** `extractCenterTemperatureWithCarryForward` walks backwards to last thermal frame
- **Empty frames array:** `getFrameAtTimestamp` returns `null`; fallback to `angle=45, temp=450`
- **Comparison session 404:** Replay page handles gracefully; hides comparison block if `comparisonSession === null`
- **Canvas focus:** Keyboard shortcuts (Space/L/R) skip when canvas focused (`if (e.target instanceof HTMLCanvasElement) return`)

---

## 8. Performance Considerations

### Rendering

- **useFrame:** Updates rotation every frame (60fps); minimal overhead (single rotation calculation)
- **Color updates:** Only when `temp` prop changes; React memoization prevents unnecessary re-renders
- **Canvas:** Single WebGL context; efficient for two side-by-side scenes

### Optimization Opportunities (Future)

- **Lazy loading:** Load TorchViz3D only when comparison is enabled
- **Frame throttling:** If performance issues, update rotation every N frames instead of every frame
- **Geometry simplification:** Reduce sphere/cylinder segments if needed (currently 24/16)

---

## 9. Related Files

| File | Role |
|------|------|
| `components/welding/TorchViz3D.tsx` | Main 3D component (Canvas, SceneContent, rotation, color) |
| `utils/frameUtils.ts` | `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward` |
| `app/replay/[sessionId]/page.tsx` | Replay page integration (side-by-side 3D) |
| `app/dev/torch-viz/page.tsx` | Verification page (isolated testing) |
| `.cursor/plans/side-by-side_3d_comparison_f15447b8.plan.md` | Implementation plan |

---

## 10. Future Enhancements

### Potential Improvements

- **Compare page integration:** Add 3D block to compare page (currently only heatmaps)
- **Score comparison:** Show scores (100/100 vs 40/100) below each TorchViz3D
- **Animation smoothing:** Interpolate rotation between frames for smoother motion (if needed)
- **Customizable camera:** Allow user to rotate/zoom camera (OrbitControls)
- **Particle effects:** Optional spark/emission effects for weld pool (low priority)

### Not Planned

- **2.5D fallback:** Full 3D is acceptable; no CSS transform alternative needed
- **Separate compare route:** Replay page integration is sufficient for incubation

---

## 11. Verification and Testing

### Manual Verification

**Dev page:** `/dev/torch-viz` — Renders TorchViz3D with various angle/temp combinations for visual verification.

**Replay page:** `/replay/sess_expert_001` — Shows side-by-side 3D when comparison session is loaded.

### Test Scenarios

- ✅ Torch rotates with angle changes (30°, 45°, 60°)
- ✅ Weld pool color changes with temperature (250°C blue, 400°C yellow, 490°C red)
- ✅ Both scenes sync to same `currentTimestamp` during playback
- ✅ Graceful handling when comparison session missing (404)
- ✅ No SSR errors (dynamic import works)

---

**Last updated:** Based on implementation from `.cursor/plans/side-by-side_3d_comparison_f15447b8.plan.md`


## BACKEND ARCHITECTURE

# Backend Skeleton Architecture

Compiled context from every backend source file touched by Steps 0–8 of the canonical time-series implementation plan. Each section captures the file-level docstrings, inline comments, assumptions, constraints, and key design decisions verbatim or paraphrased.

---

## 1. Entry Point — `backend/main.py`

**Purpose:** FastAPI application entry point. Configures CORS, registers routes, and starts the server.

**Key details:**
- App title: "Dashboard API", version 1.0.0.
- CORS allows only `http://localhost:3000` (Next.js default port). Credentials, all methods, and all headers are allowed.
- GZip middleware is enabled with `minimum_size=1000` bytes.
- Two routers are registered:
  - `dashboard_router` — mounted at root (routes define their own `/api/dashboard` prefix).
  - `sessions_router` — mounted with `prefix="/api"` so route paths like `/sessions` become `/api/sessions`.
- Health check endpoint at `GET /health` returns `{"status": "ok"}`.
- Development mode: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`.
- Production note in comment: "In production, use: `uvicorn main:app --host 0.0.0.0 --port 8000`".

**Assumptions:**
- Frontend is always a Next.js app on port 3000 during development.
- Only one allowed CORS origin for the MVP.

---

## 2. Thermal Models — `backend/models/thermal.py`

**File docstring (verbatim):**
> Thermal sensor models for canonical time-series contract.
> Every thermal frame MUST look like this, or the system rejects it.
> Only data that is already mapped to this shape is allowed to enter — everything else is rejected immediately.
> Sensor chaos → Sensor-specific model → Adapter logic (your code) → ThermalSnapshot (strict gatekeeper) ← this is the file.
> Right now, 5 readings → cardinal directions → same distance.

**Models:**

### `TemperaturePoint`
- `direction`: Literal `"center" | "north" | "south" | "east" | "west"` — required.
- `temp_celsius`: float — required, no range constraint in Pydantic (DB or service layer must bound).

### `ThermalSnapshot`
- `distance_mm`: float — required, distance along weld in millimeters.
- `readings`: exactly 5 `TemperaturePoint` entries enforced by `min_length=5, max_length=5` AND a redundant `field_validator` that re-checks `len(value) != 5`.

**Constraints / Assumptions:**
- Exactly 5 readings per snapshot: center + 4 cardinal directions.
- The adapter layer upstream must convert raw sensor data into this shape before it reaches the model.
- If the hardware changes to more or fewer directions, this model must be updated.

---

## 3. Frame Model — `backend/models/frame.py`

**File docstring (verbatim):**
> Frame model for canonical time-series welding data.
> Everything we know about the weld at one 10ms instant.
> There are some optional data, adapt for next time.
> Key points of failure:
> Welding does require back-and-forth passes, so a strictly increasing distance validator is a simplification for AI/plotting convenience, not a reflection of the true motion.
> Timestamp should have strictly increasing validator.

**Fields:**
- `timestamp_ms`: int, >= 0 — milliseconds since session start.
- `volts`: Optional[float] — voltage in volts.
- `amps`: Optional[float] — current in amps.
- `angle_degrees`: Optional[float] — torch angle in degrees.
- `thermal_snapshots`: List[ThermalSnapshot] — may be empty (not every frame has thermal data).
- `optional_sensors`: Optional[Dict[str, bool]] — flags for which sensors were available on this frame.
- `heat_dissipation_rate_celsius_per_sec`: Optional[float] — pre-calculated during ingestion, not on-demand.
- `has_thermal_data`: computed bool, `True` when `thermal_snapshots` is non-empty.

**Validators:**
1. **`validate_snapshot_distances`**: Thermal snapshot distances must be strictly increasing with no duplicates. This is explicitly noted as a simplification — real welding involves back-and-forth passes, but this constraint exists for AI/plotting convenience.
2. **`validate_center_reading_per_snapshot`**: Each thermal snapshot must contain exactly one `"center"` reading. Enforces that the center temperature (used for heat dissipation calculation) is always present.

**Assumptions:**
- Sensor sampling rate is 100 Hz (one frame every 10 ms).
- Thermal snapshots are only present on some frames (every ~100 ms = every 10th frame at 5 Hz thermal sampling).
- Heat dissipation is pre-calculated at ingestion time and stored — never computed on-demand.
- volts, amps, and angle_degrees are all optional because not every sensor may be present on every frame.

**Known simplification:**
- Strictly increasing distance is not physically accurate for multi-pass welds. This is a deliberate trade-off for plotting simplicity.

---

## 4. Session Model — `backend/models/session.py`

**File docstring (verbatim):**
> Session model for canonical time-series welding data.
> The Session model wraps frames and enforces that the entire weld is temporally, spatially, and electrically consistent before use.

### `SessionStatus` enum
Values: `RECORDING`, `INCOMPLETE`, `COMPLETE`, `FAILED`, `ARCHIVED`.

### `Session` fields
- **Metadata (required):** `session_id`, `operator_id`, `start_time` (datetime), `weld_type`.
- **Configuration (required):** `thermal_sample_interval_ms` (>0), `thermal_directions` (list, min 1), `thermal_distance_interval_mm` (>0), `sensor_sample_rate_hz` (>0).
- **Frames:** `frames` list, defaults to empty.
- **Status tracking:** `status` (default RECORDING), `frame_count`, `expected_frame_count` (optional), `last_successful_frame_index` (optional), `validation_errors` (list of strings), `completed_at` (optional datetime).
- **Test escape hatch:** `disable_sensor_continuity_checks` (bool, default False).

### Status transition rules
- Assumption: linear progression with archive as terminal state.
- `RECORDING` → `INCOMPLETE`, `COMPLETE`, `FAILED`
- `INCOMPLETE` → `RECORDING`, `FAILED`, `ARCHIVED`
- `COMPLETE` → `ARCHIVED` only
- `FAILED` → `ARCHIVED` only
- `ARCHIVED` → nothing (terminal)
- Self-transitions are always allowed.

### Validators (run in order after construction)

1. **`validate_frame_count`**: `frame_count` must exactly equal `len(frames)`. Prevents silent mismatch.
2. **`validate_frame_timestamps`**: 
   - No duplicate timestamps allowed.
   - Consecutive frames must be ~10 ms apart (tolerance: ±1 ms for floating-point precision).
   - Misordered frames are rejected.
3. **`validate_thermal_distance_consistency`**:
   - Collects all unique distances from all thermal frames across the session.
   - Sorted distances must follow the declared `thermal_distance_interval_mm` with ≤0.1 mm tolerance.
   - Ensures heatmap grid alignment across all frames.
4. **`validate_complete_session`** (when `status == COMPLETE`):
   - `expected_frame_count` is required.
   - `frame_count` must equal `expected_frame_count`.
   - `last_successful_frame_index` must equal `frame_count - 1`.
   - `completed_at` is required.
5. **`validate_sensor_continuity`** (can be disabled for test data):
   - Amps must not jump more than 20% between consecutive frames.
   - Volts must not jump more than 10% between consecutive frames.
   - Special handling: if previous value is 0, any non-zero value is a jump from zero (rejected).

**Assumptions:**
- Hardware produces frames at exactly 10 ms intervals (100 Hz).
- 1 ms timestamp tolerance accounts for floating-point precision.
- 0.1 mm distance tolerance accounts for hardware measurement precision.
- Sensor continuity checks assume smooth electrical output; can be disabled for synthetic/test data.

---

## 5. Comparison Models — `backend/models/comparison.py`

**File docstring (verbatim):**
> Comparison models for session-to-session deltas.
> FrameDelta is a structured container for deltas — it doesn't calculate anything itself; your comparison code fills it with the differences.

**Models:**

### `TemperatureDelta`
- `direction`: str — thermal direction label.
- `delta_temp_celsius`: float — `session_a - session_b`.

### `ThermalDelta`
- `distance_mm`: float — distance along weld.
- `readings`: List[TemperatureDelta] — per-direction temperature deltas.

### `FrameDelta`
- `timestamp_ms`: int, >= 0.
- `amps_delta`, `volts_delta`, `angle_degrees_delta`, `heat_dissipation_rate_celsius_per_sec_delta`: all Optional[float], all computed as `session_a - session_b`.
- `thermal_deltas`: List[ThermalDelta].

**Assumptions:**
- Comparison is generic: any two sessions, no binary expert/novice role assumption.
- Delta sign convention: positive means session_a is higher than session_b.
- These models are passive containers — the comparison service fills them.

---

## 6. Scoring Models — `backend/models/scoring.py`

**File docstring (verbatim):**
> Scoring models for rule-based evaluation.
> This code models a session's rule-based scoring: each rule has a threshold and pass/fail, and SessionScore aggregates them into a total score plus detailed per-rule results.

**Models:**

### `ScoreRule`
- `rule_id`: str — identifies the rule.
- `threshold`: float — the threshold value.
- `passed`: bool — whether the rule passed.

### `SessionScore`
- `total`: int — aggregate score.
- `rules`: List[ScoreRule] — individual rule results.

---

## 7. Legacy Session Model — `backend/models/session_model.py`

**File docstring (verbatim):**
> Pydantic models for welding session data structures.
> Will match TypeScript interfaces for type safety.

**Models (deprecated, being replaced):**
- `SessionMeta`: `session_id`, `start_timestamp_ms`, `firmware_version`.
- `HeatMapPoint`: `x_mm`, `y_mm`, `intensity_norm`.
- `ScoreRule` / `SessionScore`: duplicates of `scoring.py` models.
- `WeldingSession`: meta, optional heat_map, optional torch_angle_deg, optional score.

**Note:** This file is the old model that is being replaced by the canonical models in Steps 1–3. It still exists for backwards compatibility with the dashboard route.

---

## 8. Model Exports — `backend/models/__init__.py`

**File docstring (verbatim):**
> Models package exports for canonical time-series contract.

**Exports:**
- `DashboardData` — dynamically imported from root-level `backend/models.py` using `importlib` to avoid circular imports.
- All canonical models: `Frame`, `FrameDelta`, `Session`, `SessionScore`, `SessionStatus`, `ScoreRule`, `TemperatureDelta`, `TemperaturePoint`, `ThermalDelta`, `ThermalSnapshot`.

**Constraint:** Uses `importlib.util.spec_from_file_location` to load the root-level `models.py` (which defines `DashboardData`) to avoid name collision with the `models/` package.

---

## 9. Dashboard Models — `backend/models.py` (root-level)

**File docstring (verbatim):**
> Pydantic models for dashboard data structures.
> Matches TypeScript interfaces for type safety and validation.

**Models:**
- `MetricData`: id, title, value (int or string), optional change, optional trend ("up"/"down"/"neutral").
- `ChartDataPoint`: flexible structure supporting line (date), bar (category), and pie (name) charts.
- `ChartData`: id, type ("line"/"bar"/"pie"), title, data points, optional color.
- `DashboardData`: metrics list + charts list.

**Note:** This is separate from the welding models. It powers the generic dashboard route. Lives at root level to avoid circular imports with the `models/` package.

---

## 10. Database — `backend/database/`

### `backend/database/__init__.py`
**File docstring (verbatim):**
> This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
> Database package exports. Make folder a package, optional imports.

Exports: `Base`, `SessionModel`.

### `backend/database/base.py`
**File docstring (verbatim):**
> This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
> SQLAlchemy declarative base. Blueprint for all tables.

- Single `Base` class using `DeclarativeBase`.
- All ORM models inherit from this.

### `backend/database/connection.py`
**File docstring (verbatim):**
> This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
> Database connection setup for PostgreSQL. Set up DB connection & sessions.

**Behavior:**
- `load_env_from_backend()`: resolves `backend/.env` relative to this file's location using `Path(__file__).resolve().parent.parent`. Loads with `python-dotenv` if the file exists.
- `get_database_url()`: calls `load_env_from_backend()`, then reads `DATABASE_URL` from env. Raises `ValueError` if not set — never silently fails.
- Engine and `SessionLocal` are created at import time (module-level).
- `SessionLocal` configured with `autoflush=False, autocommit=False, future=True`.

**Constraints:**
- `DATABASE_URL` must be set in environment or in `backend/.env`. There is no fallback or default.
- Engine uses SQLAlchemy 2.0 future mode (`future=True`).
- `.env` path is deterministic: always `backend/.env`, not dependent on current working directory.

### `backend/database/models.py`
**File docstring (verbatim):**
> This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
> SQLAlchemy ORM models for canonical time-series sessions.
> This file defines SQLAlchemy ORM models, which are Python classes that map to database tables.
> This is separate from Pydantic — Pydantic is for validation in Python, SQLAlchemy is for storing/querying in a database.

#### `SessionModel` (table: `sessions`)
- Primary key: `session_id` (String, indexed).
- Indexed columns: `operator_id`, `start_time`, `weld_type`.
- JSON columns: `thermal_directions`, `validation_errors`.
- Concurrency columns: `locked_until` (DateTime with timezone), `version` (Integer, default 1).
- `status` defaults to `"recording"`.
- Relationship: `frames` — one-to-many with `FrameModel`, cascade delete, ordered by `timestamp_ms`.
- Provides `from_pydantic(session)` and `to_pydantic()` for bidirectional conversion.
- Frame conversion is done via static helper methods `_frames_to_models` and `_frames_from_models`.

#### `FrameModel` (table: `frames`)
- Primary key: `id` (auto-increment Integer).
- `session_id`: foreign key to `sessions.session_id` with `ON DELETE CASCADE`.
- `timestamp_ms`: Integer, not nullable.
- `frame_data`: JSON (JSONB in PostgreSQL), stores the full Pydantic frame as a dictionary.
- Provides `from_pydantic(frame)` and `to_pydantic()` for bidirectional conversion.
- `to_pydantic()` reconstructs a `Frame` from `frame_data` dict.

**Key design decision:** Frame data is stored as JSONB in `frame_data` column rather than fully normalized columns. This preserves the full Pydantic model structure and makes schema evolution easier, at the cost of not being able to query individual sensor values via SQL.

---

## 11. Alembic Migrations

### `backend/alembic/env.py`
- Loads `backend/.env` using `Path(__file__).resolve().parents[1] / ".env"` — same resolution strategy as `database/connection.py`, so migrations work regardless of working directory.
- Requires `DATABASE_URL` — raises `ValueError` if not set.
- Uses `NullPool` for online migrations (no connection pooling during migration).
- Imports `Base` metadata from `database.base` for autogenerate support.

### `001_initial_schema.py`
**File docstring (verbatim):**
> Initial schema for canonical time-series sessions.
> This script sets up the database for your welding sessions, ensuring every session and frame is stored with proper constraints, indexes, and JSON fields. It's the backbone for your ORM + Pydantic models to persist and validate data.

**`sessions` table:**
- `session_id` (String PK), `operator_id`, `start_time` (TIMESTAMPTZ), `weld_type`.
- Config columns: `thermal_sample_interval_ms`, `thermal_directions` (JSONB), `thermal_distance_interval_mm`, `sensor_sample_rate_hz`.
- Status: `status` (Text, default `"recording"`) with CHECK constraint limiting to `('recording','incomplete','complete','failed','archived')`.
- Tracking: `frame_count`, `expected_frame_count`, `last_successful_frame_index`, `validation_errors` (JSONB, default `[]`), `completed_at`.
- Concurrency: `locked_until` (TIMESTAMPTZ), `version` (Integer, default 1).
- Indexes: `operator_id`, `start_time`, `weld_type`.

**`frames` table:**
- `id` (Integer PK, auto-increment), `session_id` (FK → sessions, CASCADE delete), `timestamp_ms` (Integer), `frame_data` (JSONB).
- CHECK: `timestamp_ms >= 0` — no negative timestamps.
- UNIQUE: `(session_id, timestamp_ms)` — prevents duplicate frames in a session.
- Index: `(session_id, timestamp_ms DESC)` — optimized for "get previous frame" lookups.

### `002_add_disable_sensor_continuity_checks.py`
- Adds `disable_sensor_continuity_checks` (Boolean, NOT NULL, default false) to `sessions` table.
- Server default is applied then removed (Alembic pattern for adding NOT NULL column to existing rows).

---

## 12. Thermal Service — `backend/services/thermal_service.py`

**File docstring (verbatim):**
> Thermal service utilities for heat dissipation calculations.
> Heat dissipation is only calculated when both current and previous frames have valid center temperature data; otherwise it safely returns None.

### `get_previous_frame(session_id, timestamp_ms, db)`
- Queries the database for the most recent frame before `timestamp_ms` for a given session.
- Uses `ORDER BY timestamp_ms DESC LIMIT 1` — relies on `idx_frames_session_timestamp` index.
- Returns `Optional[Frame]` (Pydantic, not ORM).

### `_extract_center_temperature_celsius(frame)`
- Private helper. Extracts center temperature from the first thermal snapshot.
- Returns `None` if: no thermal data, empty snapshots, empty readings, or no `"center"` reading found.
- Assumption: center temperature comes from the first snapshot's `"center"` reading.

### `calculate_heat_dissipation(prev_frame, curr_frame, db, session_id)`
- **Formula:** `(prev_center_temp - curr_center_temp) / 0.1` — units: °C/sec.
- Positive result = cooling. Negative result = heating.
- If `prev_frame is None` and `db` + `session_id` are provided, it falls back to a DB lookup via `get_previous_frame`.
- Returns `None` for any edge case: no previous frame, no thermal data on either frame, missing center readings, empty snapshots.
- **Assumption:** Thermal snapshots appear every 100 ms (0.1 sec), so the divisor is always 0.1.
- Supports both in-memory prev_frame (during batch ingestion) and DB-fetched prev_frame (for first frame of a new batch).

**Constraints:**
- Pure function when `db=None`. Stateless and deterministic given the same inputs.
- Never guesses values — returns `None` explicitly for all missing-data scenarios.

---

## 13. Comparison Service — `backend/services/comparison_service.py`

**File docstring (verbatim):**
> Service for comparing two sessions by timestamp.
> This file aligns frames by timestamp and outputs structured deltas so you can see exactly how two welding sessions differ frame-by-frame, including thermal, electrical, and mechanical metrics.

### `compare_sessions(session_a, session_b)`
- Indexes each session's frames by `timestamp_ms` into a dict.
- Computes the intersection of timestamps (only shared timestamps are compared).
- For each shared timestamp, computes:
  - `amps_delta`, `volts_delta`, `angle_degrees_delta`, `heat_dissipation_rate_celsius_per_sec_delta` (all `a - b`, None if either is None).
  - `thermal_deltas`: matched by `distance_mm`, then by `direction`. Only produces deltas where both sessions have data at the same distance and direction.

**Constraints:**
- Generic comparison: no assumption about which session is "expert" or "novice".
- Only frames with matching timestamps are compared; non-overlapping frames are silently skipped.
- If one session is shorter, only the overlapping portion produces deltas.

---

## 14. Sessions API — `backend/routes/sessions.py`

**File docstring (verbatim):**
> Sessions API routes. Exposes endpoints for welding session data.
> This API is the bridge between your sensors (frontend or ESP32) and the backend models, validating and storing high-frequency welding data while calculating thermal metrics for later comparison.
> Key points of failure:
> - The frame data must be between 1000 and 5000 frames per request.
> - Frame Timestamps must be strictly increasing, 10ms apart.
> - Session status: Cannot add frames if status == COMPLETE.
> - Concurrency: Session cannot be uploaded to if currently locked (locked_until).
> - Streaming threshold: Total frames > 1000 triggers streaming; otherwise uses paginated JSON.

### Dependency: `get_db()`
- Creates a `SessionLocal()`, yields it, and closes on teardown.

### `GET /api/sessions` — **Not implemented** (501).

### `GET /api/sessions/{session_id}`
- Query parameters: `include_thermal` (bool, default True), `time_range_start` (ms), `time_range_end` (ms), `limit` (1–10000, default 1000), `offset` (>= 0), `stream` (bool, default False).
- If `frame_count > 10000` and not streaming and `offset == 0`: returns 400 requiring pagination or streaming.
- Streaming mode (when `stream=true` and frames > 1000): yields chunked JSON with `X-Streaming: true` header, using `yield_per(1000)` for DB cursor batching.
- Non-streaming: standard `OFFSET/LIMIT` pagination.
- Thermal filtering: when `include_thermal=false`, `thermal_snapshots` is replaced with `[]` in each frame's data.

### `GET /api/sessions/{session_id}/features` — **Not implemented** (501).

### `GET /api/sessions/{session_id}/score` — **Not implemented** (501).

### `POST /api/sessions/{session_id}/frames`
- Accepts `List[Frame]` body.
- **Hard constraint:** 1000 ≤ len(frames) ≤ 5000 per request. Fewer or more are rejected with 400.
- Uses `SELECT ... FOR UPDATE` to lock the session row during the transaction.
- **Status check:** Rejects if `status == COMPLETE` (400).
- **Concurrency check:** Rejects if `locked_until > now` (409).
- Sets `locked_until = now + 30 seconds` as an optimistic lock during processing.
- **Timestamp validation:**
  - Frames must be sorted by timestamp.
  - No duplicate timestamps.
  - If existing frames exist, the first new frame must be exactly `last_timestamp + 10`.
  - Consecutive frames must be exactly 10 ms apart (no tolerance here — stricter than session-level validator).
- **Heat dissipation:** Calculated in-memory during ingestion loop using the previous frame (DB-fetched for the first frame of the batch, then in-memory for subsequent frames). Result stored in `heat_dissipation_rate_celsius_per_sec`.
- **Transaction:** All frames inserted via `db.add_all()` inside `db.begin()` — all-or-nothing.
- On validation errors: lock is released, returns `{status: "failed", failed_frames: [...]}`.
- On success: returns `{status: "success", successful_count, next_expected_timestamp, can_resume: true}`.
- On `IntegrityError`: rollback, return failed status with "Database constraint violated".
- On any other exception: rollback, return failed status with error message.

**Assumptions:**
- Sensors or ESP32 devices upload frames in sequential batches of 1000–5000.
- A 30-second lock timeout is sufficient for one upload batch.
- Timezone-aware datetime comparisons handle both aware and naive `locked_until` values.

---

## 15. Dashboard Route — `backend/routes/dashboard.py`

**File docstring (verbatim):**
> Dashboard API routes. Exposes endpoints for dashboard data.

### `GET /api/dashboard`
- Returns `DashboardData` from `mock_dashboard_data` in `data/mock_data.py`.
- Converts raw dict to Pydantic model for validation.
- Comment: "To update the data, edit `backend/data/mock_data.py` and refresh the frontend."

---

## 16. Mock Data — `backend/data/mock_data.py`

**File docstring (verbatim):**
> Mock dashboard data - SINGLE SOURCE OF TRUTH.
> Edit this file to update dashboard data. Changes will automatically reflect in the frontend when it fetches from the API.
> To update dashboard data:
> 1. Edit the dictionaries below
> 2. Save the file (backend will auto-reload if using uvicorn --reload)
> 3. Refresh the frontend browser
> 4. Frontend will fetch updated data from GET /api/dashboard

**Constraint:** This is explicitly designated as the single source of truth for dashboard data. All dashboard data edits must happen here.

---

## 17. Feature Extraction — `backend/features/extractor.py`

**File docstring (verbatim):**
> Feature extraction from raw sensor data.
> Computes features like pressure, heat, torch angle from raw sensor readings.

**Status:** All functions are placeholder stubs returning empty dicts. Marked with `TODO: Implement`.

Functions: `extract_features`, `extract_pressure_features`, `extract_temperature_features`, `extract_torch_angle_features`.

---

## 18. Scoring — `backend/scoring/rule_based.py`

**File docstring (verbatim):**
> Rule-based scoring logic for welding sessions.
> Phase 1 scoring uses simple rule checks with placeholder thresholds.

**Status:** All functions are placeholder stubs returning zero scores and empty/failing rules.

Functions: `score_session`, `check_pressure_rule`, `check_temperature_rule`, `check_torch_angle_rule`, `check_speed_rule`.

**Constraint:** Phase 1 uses simple rule-based scoring only — no ML, no auto-tuned thresholds.

---

## 19. Environment Configuration — `backend/.env`

```
DATABASE_URL=postgresql://welding_dev:welding_password_123@localhost:5432/welding_sessions
ENVIRONMENT=development
DEBUG=true
```

**Constraints:**
- PostgreSQL database name: `welding_sessions`.
- Development credentials: `welding_dev` / `welding_password_123`.
- Local PostgreSQL on default port 5432.
- Two places load this file; both resolve to `backend/.env` relative to the file path (not cwd):
  1. `database/connection.py` — loads `backend/.env` via `Path(__file__).resolve().parent.parent`.
  2. `alembic/env.py` — loads `backend/.env` via `Path(__file__).resolve().parents[1]`.

---

## 20. Cross-Cutting Constraints and Invariants

These constraints are enforced across multiple files and layers:

| Constraint | Enforced In |
|---|---|
| Frames must be 10 ms apart | `Session.validate_frame_timestamps`, `routes/sessions.py` `add_frames` |
| No duplicate timestamps | `Session.validate_frame_timestamps`, `routes/sessions.py`, DB UNIQUE constraint |
| Thermal snapshots have exactly 5 readings | `ThermalSnapshot` Pydantic field + validator |
| Each snapshot has exactly 1 center reading | `Frame.validate_center_reading_per_snapshot` |
| Thermal distances are strictly increasing | `Frame.validate_snapshot_distances` |
| Thermal distance intervals are consistent across session | `Session.validate_thermal_distance_consistency` |
| Cannot add frames to COMPLETE session | `Session.validate_complete_session`, `routes/sessions.py` |
| Amps ≤ 20% jump between frames | `Session.validate_sensor_continuity` |
| Volts ≤ 10% jump between frames | `Session.validate_sensor_continuity` |
| Heat dissipation pre-calculated at ingestion | `routes/sessions.py` `add_frames`, `thermal_service.py` |
| timestamp_ms >= 0 | `Frame` Pydantic field, DB CHECK constraint |
| Frames per request: 1000–5000 | `routes/sessions.py` `add_frames` |
| Pagination required for > 10,000 frames | `routes/sessions.py` `get_session` |
| `DATABASE_URL` must be set | `database/connection.py`, `alembic/env.py` |
| Session status CHECK constraint | DB migration, `SessionStatus` enum |
| Cascade delete: session → frames | DB FK constraint, ORM relationship |

---

## 21. Unimplemented Endpoints (Stubs)

| Endpoint | Status |
|---|---|
| `GET /api/sessions` | 501 Not Implemented |
| `GET /api/sessions/{session_id}/features` | 501 Not Implemented |
| `GET /api/sessions/{session_id}/score` | 501 Not Implemented |

---

## 22. Directory Structure

```
backend/
├── main.py                          # FastAPI entry point
├── models.py                        # Dashboard Pydantic models (root-level)
├── db_client.py                     # (legacy, not examined)
├── __init__.py
├── .env                             # DATABASE_URL, ENVIRONMENT, DEBUG
│
├── models/                          # Canonical Pydantic models
│   ├── __init__.py                  # Exports all models
│   ├── thermal.py                   # TemperaturePoint, ThermalSnapshot
│   ├── frame.py                     # Frame
│   ├── session.py                   # Session, SessionStatus
│   ├── comparison.py                # FrameDelta, ThermalDelta, TemperatureDelta
│   ├── scoring.py                   # ScoreRule, SessionScore
│   └── session_model.py            # (deprecated) WeldingSession, SessionMeta, HeatMapPoint
│
├── database/                        # SQLAlchemy ORM + connection
│   ├── __init__.py                  # Exports Base, SessionModel
│   ├── base.py                      # DeclarativeBase
│   ├── connection.py                # Engine, SessionLocal, .env loading
│   └── models.py                    # SessionModel, FrameModel (ORM)
│
├── routes/                          # API routes
│   ├── __init__.py
│   ├── dashboard.py                 # GET /api/dashboard
│   └── sessions.py                  # GET/POST /api/sessions/...
│
├── services/                        # Business logic
│   ├── thermal_service.py           # Heat dissipation calculation
│   └── comparison_service.py        # Session-to-session comparison
│
├── features/                        # Feature extraction (stubs)
│   ├── __init__.py
│   └── extractor.py
│
├── scoring/                         # Scoring logic (stubs)
│   ├── __init__.py
│   └── rule_based.py
│
├── data/                            # Mock/seed data
│   ├── __init__.py
│   └── mock_data.py                 # Dashboard mock data
│
├── alembic/                         # Database migrations
│   ├── env.py                       # Migration runner config
│   └── versions/
│       ├── 001_initial_schema.py    # sessions + frames tables
│       └── 002_add_disable_sensor_continuity_checks.py
│
└── tests/                           # Test suite
    ├── __init__.py
    ├── test_thermal_models.py
    ├── test_frame_model.py
    ├── test_session_model.py
    ├── test_comparison_models.py
    ├── test_comparison_service.py
    ├── test_thermal_service.py
    ├── test_database_orm.py
    ├── test_database_schema.py
    ├── test_sessions_api.py
    ├── test_model_exports.py
    └── test_router_prefix.py
```
## Frontend architeture

# Frontend Implementation Summary — Shipyard MVP (Steps 1–13)

Compiled context for what is implemented in the frontend per **`.cursor/plans/shipyard-mvp-implementation-plan.md`**. High-level overview, key files, and data flow. Backend is referenced only where the frontend depends on it (API, types).

---

## 1. Scope and Implementation Overview

**Purpose:** The frontend implements the Shipyard Welding MVP: replay sessions with thermal heatmap and torch-angle chart, timeline controls (slider, play/pause, keyboard), rule-based scoring display, and a compare page with two sessions plus a delta heatmap.

**Plan progress:** 100% (13/13 steps). All frontend-facing steps are done.

**Design decisions (from plan):**
- **Heatmap:** CSS grid of divs (columns = time, rows = distance), not Recharts ScatterChart — avoids overlapping circles at 7500 points.
- **Playback:** `setInterval` at 100 updates/sec (FRAME_INTERVAL_MS = 10), not `requestAnimationFrame` (60 fps would skip frames).
- **Session fetch:** `fetchSession(sessionId, { limit: 2000 })` so ~1500-frame expert sessions load fully.
- **Scoring:** Backend GET /score; frontend ScorePanel shows total + per-rule ✓/✗ with threshold and actual_value.
- **Compare:** Single timeline, 3 columns (Session A | Delta | Session B); delta color: red = A hotter, blue = B hotter, white = same.

---

## 2. End-to-End Data Flow — Frontend

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ API: lib/api.ts                                                                     │
│   fetchSession(sessionId, { limit: 2000 }) → GET /api/sessions/{id}                │
│   fetchScore(sessionId)           → GET /api/sessions/{id}/score                    │
│   → Session (snake_case), SessionScore                                              │
└────────────────────────────────────────────────────────────────────────────────────┘
                                          │
         ┌────────────────────────────────┼────────────────────────────────┐
         ▼                                ▼                                ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ REPLAY PAGE         │    │ SCORE (replay page)  │    │ COMPARE PAGE        │
│ app/replay/         │    │ ScorePanel           │    │ app/compare/        │
│ [sessionId]/page    │    │ fetchScore on mount  │    │ [sessionIdA]/       │
│                     │    │ loading → 100/100    │    │ [sessionIdB]/page   │
│ fetchSession        │    │ or error             │    │ Promise.all(fetch   │
│ → useSessionMetadata│    │ rules[] with         │    │   A, fetch B)       │
│ → useFrameData      │    │ actual_value         │    │ useSessionComparison│
│ → extractHeatmapData│    └─────────────────────┘    │ → 3 columns         │
│ → extractAngleData  │                                │   A | Delta | B     │
│ → HeatMap,           │                                │ extractDeltaHeatmap │
│   TorchAngleGraph    │                                │   Data for middle   │
│ slider + Play/Pause  │                                │ single slider       │
│ Space / L/R keys     │                                └─────────────────────┘
└─────────────────────┘
```

---

## 3. Phase-by-Phase Frontend Implementation

### 3.1 Phase 1 — Make Data Visible (Steps 1–3)

**Step 1 — fetchSession limit**  
Replay page calls `fetchSession(sessionId, { limit: 2000 })` in a `useEffect`; cancelled flag on unmount; loading/error/success state. Full expert session (~1500 frames) loads without truncation.

**Step 2 — HeatMap (div grid)**  
- **utils/heatmapData.ts:** `tempToColor(temp_celsius)` uses a **multi-anchor scale with a visible change every 50°C** from 20°C to 600°C: blue → sky → cyan → teal → green → lime → yellow → amber → orange → red → dark red (13 anchors at 20, 70, 120, … 570, 600). Linear interpolation between consecutive anchors so small temperature steps (e.g. 50°C) produce a distinct shade change. `tempToColorRange(minTemp, maxTemp)` for compare-page shared scale; `extractHeatmapData(frames, direction?)` → `HeatmapData` (points, timestamps_ms, distances_mm, point_count).  
- **components/welding/HeatMap.tsx:** CSS grid of divs (columns = timestamps, rows = distances), `overflow-x-auto`; optional `activeTimestamp` (±50 ms) highlights column; optional `colorFn`, `label`, `valueLabel` for reuse on compare (delta) column.

**Step 3 — TorchAngleGraph (LineChart)**  
- **utils/angleData.ts:** `extractAngleData(frames)` → points, min/max/avg angle.  
- **components/welding/TorchAngleGraph.tsx:** Recharts LineChart; XAxis = timestamp_ms, YAxis = angle_degrees; ReferenceLine y={45}; optional `activeTimestamp` as vertical cursor.

---

### 3.2 Phase 2 — Replay Controls (Steps 4–6)

**Step 4 — State + slider**  
Replay page state: `currentTimestamp`, `isPlaying`, `playbackSpeed` (1). Slider min/max from `useFrameData` first/last timestamp; value = `currentTimestamp`; onChange pauses and sets timestamp. Time label: `(currentTimestamp / 1000) s`.

**Step 5 — Playback loop**  
`useEffect` with `setInterval(..., FRAME_INTERVAL_MS / playbackSpeed)`; advances `currentTimestamp` by 10 ms per tick; stops at `last_timestamp_ms` and sets `isPlaying` false; cleanup clears interval. Play/Pause button; `activeTimestamp={currentTimestamp}` passed to HeatMap and TorchAngleGraph.

**Step 6 — Keyboard shortcuts**  
`window.addEventListener('keydown')`: Space = toggle play; ArrowLeft/Right = step ±10 ms (clamped); `preventDefault` on Space and arrows; ignore when focus in INPUT/TEXTAREA/SELECT. Cleanup on unmount.

---

### 3.3 Phase 3 — Scoring (Step 10 frontend)

**Step 10 — GET /score + ScorePanel**  
- **lib/api.ts:** `fetchScore(sessionId)`, `SessionScore`, `ScoreRule` (rule_id, threshold, passed, actual_value).  
- **components/welding/ScorePanel.tsx:** Fetch on mount; loading ("Loading score..."), error (message), success: total (e.g. 100/100), list of rules with ✓/✗, threshold, actual_value. Cancelled flag to avoid setState after unmount.

---

### 3.4 Phase 4 — Compare Page (Steps 12–13)

**Step 12 — Compare page**  
- **app/compare/page.tsx:** Form with Session A and Session B inputs; `?sessionA=` pre-fills A (e.g. from replay "Compare with another session" link). Navigate to `/compare/[sessionIdA]/[sessionIdB]`.  
- **app/compare/[sessionIdA]/[sessionIdB]/page.tsx:** `Promise.all([fetchSession(idA, { limit: 2000 }), fetchSession(idB, { limit: 2000 })])`; `useSessionComparison(sessionA, sessionB)` → deltas; `useFrameData` per session; single `currentTimestamp` + slider + Play/Pause + Space/L/R; 3-column grid: Session A heatmap | Delta heatmap | Session B heatmap. Breadcrumbs to Dashboard and each replay. "No overlapping frames" message when `comparison.deltas.length === 0`.  
- **app/replay/[sessionId]/page.tsx:** "Compare with another session" link → `/compare?sessionA={sessionId}`.

**Step 13 — Delta heatmap**  
- **utils/deltaHeatmapData.ts:** `extractDeltaHeatmapData(deltas, direction?)` flattens `FrameDelta.thermal_deltas` into same `HeatmapData` shape (temp_celsius = delta_temp_celsius); `deltaTempToColor(delta_celsius)` — blue (-50) → white (0) → red (+50).  
- **components/welding/HeatMap.tsx:** Optional `colorFn` (default `tempToColor`), `label`, `valueLabel` ('temperature' | 'delta') so compare page uses `deltaTempToColor` and tooltips like "Δ +12.5°C" in the middle column.

---

## 4. Data Flow — Key Frontend Paths

### 4.1 Replay page

```
params.sessionId
    → fetchSession(sessionId, { limit: 2000 })
    → Session → setSessionData

sessionData
    → useSessionMetadata(session) → weld_type_label, duration_display, frame_count
    → useFrameData(session.frames) → thermal_frames, first_timestamp_ms, last_timestamp_ms

thermal_frames → extractHeatmapData(..., "center") → HeatmapData
session.frames → extractAngleData(...)               → AngleData

currentTimestamp (state; slider + playback + keyboard)
    → HeatMap(data=heatmapData, activeTimestamp=currentTimestamp)
    → TorchAngleGraph(data=angleData, activeTimestamp=currentTimestamp)

ScorePanel(sessionId) → fetchScore(sessionId) → loading | 100/100 + rules | error
```

### 4.2 Compare page

```
params.sessionIdA, params.sessionIdB
    → Promise.all([fetchSession(idA, { limit: 2000 }), fetchSession(idB, { limit: 2000 })])
    → sessionA, sessionB

sessionA, sessionB
    → useSessionComparison(sessionA, sessionB) → deltas, shared_count, total_a, total_b
    → useFrameData(sessionA.frames), useFrameData(sessionB.frames)

heatmapDataA = extractHeatmapData(frameDataA.thermal_frames)
heatmapDataB = extractHeatmapData(frameDataB.thermal_frames)
deltaHeatmapData = extractDeltaHeatmapData(comparison.deltas, "center")

currentTimestamp from deltas[0].timestamp_ms .. deltas[n].timestamp_ms
    → 3× HeatMap: A (tempToColor), Delta (deltaTempToColor, valueLabel="delta"), B (tempToColor)
```

---

## 5. Canonical Types and Constants (Frontend)

| Concern | File | Notes |
|--------|------|--------|
| Session, Frame (snake_case) | types/session.ts, types/frame.ts | Match backend API JSON |
| ThermalSnapshot, TemperaturePoint | types/thermal.ts | direction, temp_celsius |
| FrameDelta, ThermalDelta, TemperatureDelta | types/comparison.ts | Session A − B; validateFrameDelta |
| SessionScore, ScoreRule | lib/api.ts | total, rules[], actual_value |
| FRAME_INTERVAL_MS (10) | constants/validation.ts | Playback and step size |

---

## 6. Key File Map — Frontend (Shipyard MVP)

| Concern | File | Role |
|---------|------|------|
| Session fetch, score fetch | lib/api.ts | fetchSession(sessionId, params?), fetchScore(sessionId); SessionScore, ScoreRule |
| Replay page | app/replay/[sessionId]/page.tsx | Fetch session (limit 2000), metadata, frame data, heatmap/angle extraction, slider, play, keyboard, HeatMap, TorchAngleGraph, ScorePanel |
| Compare form | app/compare/page.tsx | Session A/B inputs; ?sessionA=; navigate to /compare/[idA]/[idB] |
| Compare page | app/compare/[sessionIdA]/[sessionIdB]/page.tsx | Parallel fetch both; useSessionComparison; 3-column HeatMaps; single slider/play/keyboard |
| Heatmap extraction | utils/heatmapData.ts | extractHeatmapData(frames, direction?), tempToColor(temp_celsius) — 50°C anchors 20→600°C; tempToColorRange(min, max) for compare |
| Delta heatmap extraction | utils/deltaHeatmapData.ts | extractDeltaHeatmapData(deltas, direction?), deltaTempToColor(delta_celsius) |
| Angle extraction | utils/angleData.ts | extractAngleData(frames) → points, min/max/avg |
| Frame filtering / thermal | utils/frameUtils.ts | filterThermalFrames, hasThermalData, extractCenterTemperature, etc. |
| Session comparison | hooks/useSessionComparison.ts | compareSessions(A, B), useSessionComparison(A, B); FrameDelta[] |
| Frame data for replay/compare | hooks/useFrameData.ts | thermal_frames, first/last timestamp from frames |
| Session metadata | hooks/useSessionMetadata.ts | weld_type_label, duration_display, frame_count from Session |
| HeatMap | components/welding/HeatMap.tsx | Div grid; tempToColor or colorFn; activeTimestamp; label; valueLabel |
| TorchAngleGraph | components/welding/TorchAngleGraph.tsx | Recharts LineChart; angle over time; ReferenceLine 45°; activeTimestamp |
| ScorePanel | components/welding/ScorePanel.tsx | fetchScore on mount; loading/error/success; total + rules with actual_value |
| TorchViz3D | components/welding/TorchViz3D.tsx | 3D torch + weld pool (angle, temp); R3F Canvas; useFrame rotation; temp→color blue/yellow/red; used for side-by-side comparison |

---

## 7. Cross-Cutting Constraints (Frontend)

| Constraint | Where Enforced |
|------------|----------------|
| fetchSession with limit 2000 for full replay | app/replay/[sessionId]/page.tsx, app/compare/.../page.tsx |
| setInterval for playback (not RAF) | app/replay/..., app/compare/... (FRAME_INTERVAL_MS / playbackSpeed) |
| HeatMap: div grid, not ScatterChart | components/welding/HeatMap.tsx |
| activeTimestamp ±50 ms for column highlight | HeatMap.tsx (ACTIVE_TOLERANCE_MS) |
| Delta color: red = A hotter, blue = B hotter | utils/deltaHeatmapData.ts (deltaTempToColor), compare page middle column |
| Temperature scale: visible change every 50°C (20–600°C) | utils/heatmapData.ts (TEMP_COLOR_ANCHORS: blue→sky→cyan→teal→green→lime→yellow→amber→orange→red) |
| Snake_case from API; no conversion layer | types/*, lib/api.ts |
| Guard has_thermal_data / thermal_snapshots / readings | frameUtils, heatmapData, deltaHeatmapData, useSessionComparison |
| Cancelled flag on async fetch (unmount safety) | Replay page, Compare page, ScorePanel |

---

## 8. Related Context Files

- **overall-stack-context.md** — End-to-end stack: mock/API to frontend, analysis capabilities, key file map (backend + frontend).
- **frontend-skeleton-architecture.md** — Frontend types, hooks, components (broader than Shipyard MVP).
- **.cursor/plans/shipyard-mvp-implementation-plan.md** — Full 13-step plan, verification tests, pass criteria.

## basic frontend architetcture

# Frontend Skeleton Architecture

Compiled context from every frontend source file touched by **Steps 9–15** of the canonical time-series implementation plan. Each section captures file-level docstrings, key comments, assumptions, constraints, and data flow. The frontend is the strict TypeScript mirror of the backend Pydantic contract — snake_case everywhere, no conversion layer.

---

## 1. Scope and Data Flow

**Steps covered:** 9 (Thermal types), 10 (Frame type), 11 (Session type), 12 (Comparison types), 13 (API client), 13B (Constants), 14 (frameUtils), 14B (Hooks), 15 (heatmapData, angleData, HeatMap/TorchAngleGraph).

**End-to-end data flow:**
```
Backend API (JSON) → lib/api.ts (fetchSession / addFrames)
  → Session / Frame[] (types)
  → Constants (labels, ranges, validation rules)
  → Utils (frameUtils, heatmapData, angleData) — safe extraction & transformation
  → Hooks (useSessionMetadata, useFrameData, useSessionComparison) — memoized for React
  → Components (HeatMap, TorchAngleGraph) — receive pre-extracted data only
```

**Design principles (from workspace rules):**
- Never silently fail: defensive null/empty checks before accessing `readings`, `thermal_snapshots`, optional sensor fields.
- Never mutate raw data: extraction and transformation are pure.
- Explicit units in names: `timestamp_ms`, `temp_celsius`, `distance_mm`, `angle_degrees`, etc.
- Frontend validation is lightweight runtime guards; backend enforces timestamp ordering, thermal distance consistency, sensor continuity.

---

## 2. Thermal Types — `my-app/src/types/thermal.ts`

**File docstring (verbatim):**
> This file is the frontend's strict mirror of the backend thermal gate — it makes invalid thermal data impossible to use, not just impossible to store.
> Data flow: Sensor hardware → Backend Pydantic validation → JSON API → These types.

**Types and constants:**
- **`ThermalDirection`**: `"center" | "north" | "south" | "east" | "west"` — canonical directions only.
- **`THERMAL_DIRECTIONS`**: readonly array of all five directions (iteration, validation).
- **`READINGS_PER_SNAPSHOT`**: 5 — matches backend `min_length=5, max_length=5`.
- **`TemperaturePoint`**: `direction` (ThermalDirection), `temp_celsius` (number).
- **`ThermalSnapshot`**: `distance_mm` (number), `readings` (TemperaturePoint[]). Invariants: exactly 5 readings, one per direction, `distance_mm` > 0.

**Runtime validation:**
- **`isThermalDirection(value)`**: type guard for string → ThermalDirection.
- **`validateThermalSnapshot(snapshot)`**: returns string[] of errors; checks distance > 0, readings length 5, each canonical direction exactly once.

**Assumptions:**
- Every thermal snapshot has exactly 5 readings (center + 4 cardinal). Distances in mm, temperatures in °C. Snapshots every `thermal_sample_interval_ms` (typically 100 ms / 5 Hz).

---

## 3. Frame Type — `my-app/src/types/frame.ts`

**File docstring (verbatim):**
> Frame type definition for the canonical time-series contract. Mirrors backend/models/frame.py exactly. Field names use snake_case — no conversion layer.
> A Frame represents everything the system knows about the weld at a single 10 ms instant (100 Hz sampling). Not all sensors fire every frame: electrical sensors may be absent (null); thermal snapshots only every ~100 ms (5 Hz); heat dissipation pre-calculated on ingestion.
> WARNING: Always check `has_thermal_data` before accessing `thermal_snapshots`. Always null-check optional fields before arithmetic.

**Fields:**
- **Required:** `timestamp_ms` (number, >= 0), `thermal_snapshots` (array, may be empty), `has_thermal_data` (boolean, backend-computed).
- **Optional (null allowed):** `volts`, `amps`, `angle_degrees`, `heat_dissipation_rate_celsius_per_sec`, `optional_sensors` (Record<string, boolean> | null).

**Runtime validation:**
- **`validateFrame(frame)`**: checks timestamp non-negative integer; `has_thermal_data` consistent with `thermal_snapshots.length`; thermal distances strictly increasing; each snapshot passes `validateThermalSnapshot`; optional numeric fields null or finite.

**Assumptions:**
- 100 Hz frame rate (10 ms interval). Thermal data on subset of frames (~5 Hz). Heat dissipation from backend only — do not recompute.

---

## 4. Session Type — `my-app/src/types/session.ts`

**File docstring (verbatim):**
> Session type definition for the canonical time-series contract. Mirrors backend/models/session.py exactly. A Session is the top-level container: identity & audit metadata, sensor configuration, ordered frame list, ingestion status tracking. The backend enforces heavy validation; the frontend mirrors the shape and provides lightweight runtime guards.

**SessionStatus and transitions:**
- **`SessionStatus`**: `"recording" | "incomplete" | "complete" | "failed" | "archived"`.
- **`SESSION_STATUSES`**: readonly array of all statuses.
- **`VALID_STATUS_TRANSITIONS`**: map of current status → allowed next statuses. Same-status allowed (no-op).
- **`isValidStatusTransition(previous, next)`**: mirrors backend transition rules.

**Session interface (grouped):**
- **Identity:** `session_id`, `operator_id`, `start_time` (ISO 8601 string), `weld_type`.
- **Config:** `thermal_sample_interval_ms`, `thermal_directions`, `thermal_distance_interval_mm`, `sensor_sample_rate_hz` (all required, > 0).
- **Data:** `frames` (Frame[]). WARNING: may contain up to 30,000 frames; use pagination/streaming for large sessions.
- **Status tracking:** `status`, `frame_count`, `expected_frame_count` (null until complete), `last_successful_frame_index`, `validation_errors`, `completed_at` (null unless complete).

**Runtime validation:**
- **`validateSession(session)`**: required strings non-empty; numeric config > 0; `thermal_directions` length >= 1; valid status; `frame_count === frames.length`; when status === "complete", expects `expected_frame_count`, `last_successful_frame_index === frame_count - 1`, `completed_at`. Does not validate frames or cross-frame invariants (backend responsibility).

---

## 5. Comparison Types — `my-app/src/types/comparison.ts`

**File docstring (verbatim):**
> Comparison type definitions for session-to-session deltas. Mirrors backend/models/comparison.py exactly. These types are generic: delta between any two sessions (session_a - session_b). No binary role assumption (expert vs novice). Sign: positive = session_a higher than session_b. Deltas aligned by timestamp; only timestamps present in both sessions produce deltas.

**Interfaces:**
- **`TemperatureDelta`**: `direction` (string), `delta_temp_celsius` (number).
- **`ThermalDelta`**: `distance_mm` (number), `readings` (TemperatureDelta[]).
- **`FrameDelta`**: `timestamp_ms`; `amps_delta`, `volts_delta`, `angle_degrees_delta`, `heat_dissipation_rate_celsius_per_sec_delta` (all number | null); `thermal_deltas` (ThermalDelta[]). All deltas are (session_a - session_b); null when either session lacks the reading.

**Runtime validation:**
- **`validateFrameDelta(delta)`**: timestamp non-negative integer; optional delta fields null or finite number; `thermal_deltas[].distance_mm` positive.

---

## 6. API Client — `my-app/src/lib/api.ts`

**File docstring (verbatim):**
> API client for the Shipyard Welding backend. All functions communicate with the FastAPI backend at API_BASE_URL. Types match backend Pydantic models exactly (snake_case). Error handling: network failures throw with descriptive message; non-2xx throw with status + backend detail; callers should catch and display errors to the operator.

**Configuration:**
- **`API_BASE_URL`**: `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`.

**Shared types (exported):**
- **`FetchSessionParams`**: optional `include_thermal`, `time_range_start`, `time_range_end`, `limit` (1–10000), `offset`, `stream`.
- **`FrameError`**: `index`, `timestamp_ms`, `error` (for ingestion failures).
- **`AddFramesResponse`**: `status`, `successful_count`, `failed_frames`, `next_expected_timestamp`, `can_resume`.

**Internal helpers:**
- **`buildUrl(path, params)`**: appends only defined params to query string; omits undefined.
- **`apiFetch<T>(url, init)`**: try/catch for network errors; on !response.ok parses body.detail (FastAPI string or array of `{ msg?, ... }`), normalizes array to `msg` strings joined by "; ", then throws `Error(\`API error ${status}: ${detail}\`)`. Returns `response.json()` on success.

**Public API:**
- **`fetchDashboardData()`**: GET /api/dashboard → DashboardData.
- **`fetchSession(sessionId, params?)`**: GET /api/sessions/{id} with query params; returns Session. sessionId is encoded with `encodeURIComponent`.
- **`addFrames(sessionId, frames)`**: POST /api/sessions/{id}/frames, JSON body; returns AddFramesResponse. Frames 1000–5000 per request per backend.

**Exported for tests:** `buildUrl`, `apiFetch`, `API_BASE_URL`.

---

## 7. Constants — `my-app/src/constants/`

### 7.1 Metals — `metals.ts`

**File docstring (verbatim):**
> Any change here can ripple through components, services, tests, and occasionally the backend. Metal type constants. Centralizes metal type identifiers, display labels, physical properties. NOTE: MVP defaults; update when hardware team provides actual metal-specific parameters.

- **`METAL_TYPES`**: readonly array of valid weld_type identifiers (must match backend DB).
- **`MetalType`**: union type from METAL_TYPES.
- **`METAL_TYPE_LABELS`**: Record<MetalType, string> for display.
- **`MetalProperties`**: `melting_point_celsius`, `thermal_conductivity_w_per_mk`, `preheat_temp_celsius`, `typical_voltage_range_volts`, `typical_amperage_range_amps`.
- **`METAL_PROPERTIES`**: Record<MetalType, MetalProperties> (reference values; units in field names).

### 7.2 Sensors — `sensors.ts`

**File docstring (verbatim):**
> Sensor configuration constants. Centralizes valid ranges, display units, temperature limits. These ranges are for display/warning purposes; backend enforces hard constraints.

- **`SensorRange`**: `min`, `max`, `unit`.
- **`SENSOR_RANGES`**: volts, amps, angle_degrees, speed_mm_per_sec (min/max/unit).
- **`SENSOR_UNITS`**: display units for volts, amps, angle_degrees, speed, temp_celsius, distance_mm, heat_dissipation_rate, timestamp_ms.
- **`TEMPERATURE_RANGE_CELSIUS`**: `min` (-20), `max` (2000) for thermal sensor range.

### 7.3 Validation — `validation.ts`

**File docstring (verbatim):**
> Validation constants for the canonical time-series contract. These values must match the backend validation rules exactly. Source of truth: backend/models/session.py, frame.py, thermal.py, backend/routes/sessions.py.

**Frame timing:** `FRAME_INTERVAL_MS` (10), `FRAME_INTERVAL_TOLERANCE_MS` (1), `THERMAL_SAMPLE_INTERVAL_MS` (100), `SENSOR_SAMPLE_RATE_HZ` (100).

**Session limits:** `MAX_SESSION_DURATION_MS` (5 min), `MAX_FRAMES_PER_SESSION` (30_000).

**Ingestion:** `MIN_FRAMES_PER_REQUEST` (1000), `MAX_FRAMES_PER_REQUEST` (5000).

**Pagination:** `DEFAULT_PAGE_SIZE` (1000), `MAX_PAGE_SIZE` (10_000).

**Sensor continuity:** `MAX_AMPS_JUMP_RATIO` (0.20), `MAX_VOLTS_JUMP_RATIO` (0.10).

**Thermal:** `READINGS_PER_THERMAL_SNAPSHOT` (5), `THERMAL_DISTANCE_TOLERANCE_MM` (0.1).

**`ERROR_MESSAGES`**: user-facing strings for SESSION_NOT_FOUND, SESSION_LOCKED, FRAMES_OUT_OF_ORDER, DUPLICATE_TIMESTAMPS, THERMAL_DISTANCE_MISMATCH, AMPS/VOLTS_JUMP, PAYLOAD_TOO_LARGE, NETWORK_ERROR, UNKNOWN_ERROR.

**`VALIDATION_RULES`**: single object summarizing the above for form validators / pre-API checks.

---

## 8. Utilities — `my-app/src/utils/`

### 8.1 Frame utilities — `frameUtils.ts`

**File docstring (verbatim):**
> Safe extraction utilities for Frame data. Centralize null-checking and optional-field access. ALWAYS use these instead of accessing thermal fields directly. Handle: first frame, missing thermal frames, empty readings, null sensor readings. Mirrors backend/services/thermal_service.py.

**Functions:**
- **`extractCenterTemperature(frame)`**: returns number | null. Guards: has_thermal_data, thermal_snapshots length, first snapshot readings length, find center by direction.
- **`extractTemperatureByDirection(frame, direction, snapshotIndex?)`**: same guards; returns temp at given direction and snapshot index.
- **`extractAllTemperatures(frame, snapshotIndex?)`**: returns TemperaturePoint[] or [].
- **`extractHeatDissipation(frame)`**: returns `frame.heat_dissipation_rate_celsius_per_sec ?? null` (backend pre-calculated).
- **`hasRequiredSensors(frame)`**: true iff volts, amps, angle_degrees are all non-null.
- **`filterThermalFrames(frames)`**: frames where has_thermal_data === true.
- **`filterFramesByTimeRange(frames, startMs, endMs)`**: inclusive; null bound = no limit.

**Constraint:** All thermal access goes through guards on `has_thermal_data`, `thermal_snapshots`, and `snapshot.readings` to avoid silent failures on malformed data.

### 8.2 Heatmap data — `heatmapData.ts`

**File docstring (verbatim):**
> Heatmap data extraction for thermal visualization. Transforms canonical Frame data into a grid (time × distance → temperature). Output is a flat array for any heatmap library (recharts, d3, visx). Defensive: skips snapshots with missing or empty readings.

- **`HeatmapDataPoint`**: `timestamp_ms`, `distance_mm`, `temp_celsius`, `direction`.
- **`HeatmapData`**: `points`, `timestamps_ms` (sorted unique), `distances_mm` (sorted unique), `point_count`.
- **`extractHeatmapData(frames, direction?)`**: default direction "center"; only frames with has_thermal_data; per snapshot guards `readings`; builds points and unique timestamp/distance sets; returns sorted arrays.

### 8.3 Angle data — `angleData.ts`

**File docstring (verbatim):**
> Torch angle data extraction for time-series visualization. Transforms Frame data into (timestamp, angle) time series for line charts.

- **`AngleDataPoint`**: `timestamp_ms`, `angle_degrees`.
- **`AngleData`**: `points`, `point_count`, `min_angle_degrees`, `max_angle_degrees`, `avg_angle_degrees` (null when no data).
- **`extractAngleData(frames)`**: filters out frames with null angle_degrees; sorts by timestamp; computes min/max/avg when non-empty.

---

## 9. Hooks — `my-app/src/hooks/`

### 9.1 useSessionMetadata — `useSessionMetadata.ts`

**File docstring (verbatim):**
> Hook for validating and formatting session metadata. Centralizes session metadata access so components don't parse dates, look up labels, or validate IDs themselves.

- **Return type `SessionMetadataResult`**: session_id, operator_id, start_date (Date | null), start_time_display, weld_type, weld_type_label, status, frame_count, duration_ms, duration_display, is_recording, is_complete, validation_errors.
- **Pure helpers (exported):** `formatDuration(ms)`, `formatStartTime(date)`, `getWeldTypeLabel(weldType)` (uses METAL_TYPE_LABELS, fallback to raw value).
- **Hook `useSessionMetadata(session)`**: useMemo on session; returns null if session null; derives duration from last frame timestamp; formats start_time via Date parse.

### 9.2 useFrameData — `useFrameData.ts`

**File docstring (verbatim):**
> Hook for parsing and filtering frame data safely. Wraps frameUtils in a React hook with memoization.

- **Return type `FrameDataResult`**: all_frames (time-range filtered), thermal_frames, total_count, thermal_count, has_any_thermal, first_timestamp_ms, last_timestamp_ms.
- **Hook `useFrameData(frames, startMs?, endMs?)`**: useMemo on [frames, startMs, endMs]; applies filterFramesByTimeRange then filterThermalFrames.

### 9.3 useSessionComparison — `useSessionComparison.ts`

**File docstring (verbatim):**
> Hook for comparing two welding sessions. Mirrors backend compare_sessions() — aligns by timestamp only, no role assumption. Runs on frontend for responsiveness; backend is source of truth for persisted comparisons. Performance: O(n) in total frames; for very large sessions (e.g. 10k+ each) consider server-side or pagination.

- **Pure functions (exported):** `deltaOptional(a, b)` (a - b or null); `computeThermalDeltas(frameA, frameB)` (guards thermal_snapshots and snapshot.readings; matches by distance then direction); `compareSessions(sessionA, sessionB)` (index by timestamp, shared timestamps only, builds FrameDelta[]).
- **Return type `SessionComparisonResult`**: deltas, shared_count, only_in_a_count, only_in_b_count, total_a, total_b.
- **Hook `useSessionComparison(sessionA, sessionB)`**: useMemo on [sessionA, sessionB]; returns null if either null; else compareSessions(a, b).

---

## 10. Replay Page — `my-app/src/app/replay/[sessionId]/page.tsx`

**Purpose:** Displays replay visualization for a specific welding session (sessionId from route params).

**State:** sessionData (Session | null), loading, error. Uses `Session` type (WeldingSession removed).

**Effect (current):**
- NOTE: Replay visualization deferred to Phase 2 (after live session validation). Will wire fetchSession() → extractHeatmapData() / extractAngleData() → components in next iteration. Currently only sets loading false.

**UI:** Loading state, error state, success state with HeatMap and TorchAngleGraph by sessionId (no data passed yet); ScorePanel below.

---

## 11. Visualization Components — `my-app/src/components/welding/`

### 11.1 HeatMap — `HeatMap.tsx`

**File docstring (verbatim):**
> Visualizes heat distribution over time. Accepts pre-extracted heatmap data from extractHeatmapData(). The component does NOT fetch or transform raw frame data — data transformation is the caller's responsibility. sessionId for labelling; data optional (null = loading/empty).

**Props:** `sessionId: string`, `data?: HeatmapData | null`.

**Behavior:** Early return when !data || data.point_count === 0 (no thermal data message). Otherwise renders summary: point_count, timestamps count, distances count and "Visualization rendering coming soon". No chart library wired yet.

### 11.2 TorchAngleGraph — `TorchAngleGraph.tsx`

**File docstring (verbatim):**
> Graphs torch angle over time. Accepts pre-extracted angle data from extractAngleData(). Does NOT fetch or transform raw frame data. sessionId for labelling; data optional (null = loading/empty).

**Props:** `sessionId: string`, `data?: AngleData | null`.

**Behavior:** Early return when !data || data.point_count === 0 (no angle data message). Otherwise renders summary: point_count, min/max/avg angle and "Visualization rendering coming soon". No chart library wired yet.

---

## 12. Cross-Cutting Constraints

| Constraint | Where |
|------------|--------|
| snake_case for all API/contract fields | All types, API client, constants |
| No conversion layer backend ↔ frontend | Types mirror Pydantic; same field names |
| Always guard has_thermal_data / thermal_snapshots / readings | frameUtils, heatmapData, useSessionComparison |
| Heat dissipation from backend only; do not recompute | frame.ts TSDoc, frameUtils.extractHeatDissipation |
| Session validation does not check frames or cross-frame invariants | validateSession in session.ts |
| API errors: normalize body.detail (string or array) for message | api.ts apiFetch |
| Replay data wiring deferred to Phase 2 | replay page useEffect comment |
| HeatMap / TorchAngleGraph receive only pre-extracted data | Component docstrings and props |

---

## 13. Directory Structure (Steps 9–15)

```
my-app/src/
├── types/
│   ├── thermal.ts          # ThermalDirection, TemperaturePoint, ThermalSnapshot, guards
│   ├── frame.ts            # Frame, validateFrame
│   ├── session.ts          # SessionStatus, Session, validateSession, transitions
│   ├── comparison.ts       # FrameDelta, ThermalDelta, TemperatureDelta, validateFrameDelta
│   └── dashboard.ts        # (existing; unchanged by Steps 9–15)
│
├── lib/
│   └── api.ts              # API_BASE_URL, fetchSession, addFrames, fetchDashboardData, buildUrl, apiFetch
│
├── constants/
│   ├── metals.ts           # METAL_TYPES, METAL_TYPE_LABELS, METAL_PROPERTIES
│   ├── sensors.ts          # SENSOR_RANGES, SENSOR_UNITS, TEMPERATURE_RANGE_CELSIUS
│   └── validation.ts       # Timing, limits, ERROR_MESSAGES, VALIDATION_RULES
│
├── utils/
│   ├── frameUtils.ts       # extractCenterTemperature, extractTemperatureByDirection, extractAllTemperatures,
│   │                        # extractHeatDissipation, hasRequiredSensors, filterThermalFrames, filterFramesByTimeRange
│   ├── heatmapData.ts      # HeatmapDataPoint, HeatmapData, extractHeatmapData
│   └── angleData.ts        # AngleDataPoint, AngleData, extractAngleData
│
├── hooks/
│   ├── useSessionMetadata.ts   # formatDuration, formatStartTime, getWeldTypeLabel, useSessionMetadata
│   ├── useFrameData.ts         # useFrameData (filter by time + thermal)
│   └── useSessionComparison.ts # deltaOptional, computeThermalDeltas, compareSessions, useSessionComparison
│
├── app/
│   └── replay/
│       └── [sessionId]/
│           └── page.tsx    # Replay page; Session state; HeatMap/TorchAngleGraph without data (Phase 2 wiring)
│
├── components/
│   └── welding/
│       ├── HeatMap.tsx     # Props: sessionId, data?: HeatmapData | null
│       └── TorchAngleGraph.tsx  # Props: sessionId, data?: AngleData | null
│
└── __tests__/
    ├── types/              # thermal, frame, session, comparison
    ├── constants/          # constants.test.ts
    ├── lib/                # api.test.ts
    ├── utils/              # frameUtils, heatmapData, angleData
    ├── hooks/              # useSessionMetadata, useFrameData, useSessionComparison
    └── components/welding/ # HeatMap, TorchAngleGraph
```

---

## 14. Intended Phase 2 Wiring (Replay)

When replay is implemented, the flow will be:

1. Replay page: `fetchSession(params.sessionId)` (and optionally pagination/streaming).
2. On success: `session.frames` → `extractHeatmapData(session.frames)` and `extractAngleData(session.frames)`.
3. Pass `heatmapData` and `angleData` into `<HeatMap sessionId={...} data={heatmapData} />` and `<TorchAngleGraph sessionId={...} data={angleData} />`.
4. Components already accept these props; only the page needs to fetch and transform, then pass data down.

# validation and test

# Mock Tests and Validation Tests (Steps 16–21)

Compiled context from every test file and mock data source touched by **Steps 16–21** of the canonical time-series implementation plan. This document captures how data flows between mock generators, validation tests, serialization tests, API integration tests, performance benchmarks, and the replay page.

---

## 1. Scope and Data Flow Overview

**Steps covered:** 16 (Mock data), 17 (Validation & edge cases), 18 (Serialization), 19 (Frontend utilities), 20 (API integration & performance), 21 (Integration & cleanup).

**End-to-end data flow across tests and application:**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. MOCK DATA SOURCE — backend/data/mock_sessions.py                             │
│    generate_expert_session() → Session (1500 frames, stable signals)              │
│    generate_novice_session() → Session (1500 frames, erratic + thermal gap)      │
│    generate_large_session()  → Session (30,000 frames, expert signals)            │
│    generate_thermal_snapshots(timestamp_ms, amps, volts, angle_deg) → physics   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. BACKEND VALIDATION — backend/models/*.py (Pydantic)                           │
│    Session, Frame, ThermalSnapshot, TemperaturePoint                             │
│    Validators: frame_count match, timestamps ~10ms, thermal distances, continuity │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. BACKEND TESTS (Steps 17–18)                                                   │
│    test_mock_sessions.py    ← consumes mock_sessions (expert, novice, large)     │
│    test_validation.py      ← builds minimal _frame(), _base_session() in-test     │
│    test_comparison_edge_cases.py ← _frame(), _session() helpers, no mock_sessions│
│    test_heat_dissipation.py     ← _frame(ts, center_temp) inline                 │
│    test_serialization.py   ← _readings(), Session/Frame/ThermalSnapshot inline   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. SERIALIZATION BOUNDARY — Python model_dump(mode="json") → JSON string          │
│    snake_case fields, ISO 8601 datetimes, SessionStatus as string                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. FRONTEND TESTS (Steps 18–19)                                                  │
│    serialization.test.ts   ← JSON.parse(JSON.stringify(obj)) simulates API        │
│    frameUtils.test.ts     ← makeThermalFrame(), makeSensorOnlyFrame() inline      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. API INTEGRATION (Step 20) — backend/tests/test_api_integration.py            │
│    In-memory SQLite → _insert_frames(), _make_session() → GET /api/sessions/{id} │
│    Data: _minimal_frame_data(ts, with_thermal) → FrameModel.frame_data (JSONB)  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 7. REPLAY PAGE (Step 21) — my-app/src/app/replay/[sessionId]/page.tsx            │
│    fetchSession(sessionId) → Session                                             │
│    useSessionMetadata(session) → metadata                                        │
│    useFrameData(frames) → thermal_frames                                         │
│    extractHeatmapData(thermal_frames) → HeatMap data                             │
│    extractAngleData(frames) → TorchAngleGraph data                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mock Data — `backend/data/mock_sessions.py`

**File docstring (verbatim):**
> Mock session data generation for canonical time-series contract. All sensor values are causally linked — changing one affects the others.

### Physical model

| Input | Effect on thermals |
|-------|-------------------|
| `angle_degrees` | north/south asymmetry: north_offset = +angle × 3.0°C/°, south_offset = -angle × 3.0°C/° |
| `arc_power_watts = volts × amps` | center temperature magnitude; more power = hotter |
| `distance_mm` | temperature drop along weld; east (travel direction) hotter than west |

### Signal generators

**Expert:**
- `expert_amps(t)`: stable ~150A, warmup oscillation that decays in 500ms (avoids 0→non-zero jump).
- `expert_volts(t)`: stable ~22.5V.
- `expert_angle(t)`: holds ~45° ± 1° tremor.

**Novice:**
- `novice_amps(t)`: spiky, occasional 100ms spikes every ~2s (within 20% continuity when escape hatch on).
- `novice_volts(t)`: drifts 22V → 18V over 15s.
- `novice_angle(t)`: drifts 45° → 65° over 15s.

### Session builders

| Function | Frames | Duration | Characteristics |
|----------|--------|----------|------------------|
| `generate_expert_session()` | 1500 | 15s | continuity checks ON |
| `generate_novice_session()` | 1500 | 15s | `include_thermal_gap=True`, continuity OFF |
| `generate_large_session()` | 30,000 | 5min | expert signals, for perf tests |

### Data flow into tests

```
mock_sessions.generate_expert_session()
    → generate_frames(duration_ms, expert_amps, expert_volts, expert_angle)
    → for each t in [0, 10, 20, ...]: Frame with thermal_snapshots when t % 100 == 0
    → generate_thermal_snapshots(t, amps, volts, angle) → TemperaturePoint[] per direction
    → calculate_heat_dissipation via thermal_service (prev_center - curr_center) / 0.1
    → Session(frames=..., status=COMPLETE)
```

**Consumers:** `test_mock_sessions.py`, `test_performance.py`, `test_heat_dissipation.py` (integration section).

---

## 3. Backend Tests — Data Sources and Flow

### 3.1 `test_mock_sessions.py` (Step 16)

**Data source:** `data.mock_sessions` (generate_expert_session, generate_novice_session, generate_large_session).

**Data flow:**
```
generate_expert_session() / generate_novice_session()
    → Session (Pydantic)
    → assert session passes validation
    → get_thermal_frames(session) = [f for f in session.frames if f.has_thermal_data]
    → get_center_temp(frame), get_direction_temp(frame, "north")
```

**Key tests:**
- Session structure: frame_count, status, continuity flag.
- Frame timing: timestamps 0, 10, 20, ... 10ms apart.
- Thermal structure: 150 thermal frames (expert), thermal gap (novice), 5 readings per snapshot.
- Heat dissipation: frame 0 → null, second thermal frame → non-null, post-gap → null.
- Physics: center hottest at 10mm, east > west, expert north/south symmetric, novice asymmetric.
- Comparison: `compare_sessions(expert, novice)` → deltas on amps, volts, angle, thermals.

### 3.2 `test_validation.py` (Step 17)

**Data source:** In-test helpers `_base_session()`, `_frame()`, `_readings()`. No mock_sessions.

**Data flow:**
```
_base_session(frames, **overrides) → dict
    → Session(**dict) with invalid field → pytest.raises(ValidationError)

_frame(timestamp_ms, distances, **overrides) → Frame
    → ThermalSnapshot(distance_mm, readings=_readings()) when distances provided
```

**Coverage:** Session (frame_count, config, required fields, completion invariants, timestamps, thermal interval), Frame (timestamp, volts, amps, angle), ThermalSnapshot (distance, readings), TemperaturePoint (direction, temp).

### 3.3 `test_comparison_edge_cases.py` (Step 17)

**Data source:** In-test `_frame()`, `_session()`. No mock_sessions.

**Data flow:**
```
_frame(ts, amps, volts, angle_degrees, distances)
    → Session a, Session b with different timestamps / thermal distances
    → compare_sessions(a, b) → List[FrameDelta]
```

**Scenarios:** No overlap → empty; partial overlap → shared count; different thermal distances → empty thermal_deltas; identical sessions → all deltas 0; sparse thermal → thermal_deltas only at matching frames.

### 3.4 `test_heat_dissipation.py` (Step 17)

**Data source:** In-test `_frame(timestamp_ms, center_temp, with_thermal)`.

**Data flow:**
```
_frame(0, 500.0)  → Frame with thermal at 500°C
_frame(10, 480.0) → Frame with thermal at 480°C
    → calculate_heat_dissipation(prev, curr) → (500-480)/0.1 = 200°C/sec
```

**Edge cases:** prev/curr None, no thermal, cooling, heating, zero rate, variable interval, mock session integration.

### 3.5 `test_serialization.py` (Step 18)

**Data source:** In-test `_readings(center_temp)`, inline Session/Frame/ThermalSnapshot construction.

**Data flow:**
```
Session(...) / Frame(...) / ThermalSnapshot(...)
    → model_dump(mode="json") → dict
    → Session.model_validate(dumped) / JSON round-trip
```

**Coverage:** snake_case, extreme floats, null handling, ISO 8601, SessionStatus string.

### 3.6 `test_api_integration.py` (Step 20)

**Data source:** In-test `_minimal_frame_data(ts, with_thermal)`, `_make_session()`, `_insert_frames()`.

**Data flow:**
```
SQLite :memory:
    → SessionModel(session_id, ...) → db.add()
    → FrameModel(session_id, ts, frame_data=_minimal_frame_data(...)) → db.add()
    → TestClient.get("/api/sessions/{id}", params=...) → response.json()
```

**Conditional:** Skips when SQLAlchemy not installed.

### 3.7 `test_performance.py` (Step 20)

**Data source:** `generate_expert_session`, `generate_novice_session`, `generate_large_session` from mock_sessions.

**Data flow:**
```
generate_large_session() → model_dump(mode="json")
    → benchmark(Session.model_validate(dumped))
    → assert mean < PERFORMANCE_VALIDATE_S (env configurable)
```

**Conditional:** Skips when pytest-benchmark not installed.

---

## 4. Frontend Tests — Data Sources and Flow

### 4.1 `serialization.test.ts` (Step 18)

**Data source:** Inline JSON objects matching backend shape (snake_case).

**Data flow:**
```
JSON.stringify({ session_id: "...", frames: [], ... })
    → JSON.parse(json) as Session
    → validateSession(parsed) → []
    → validateFrame(parsed) when frame tests
```

**Simulates:** API response → JSON.parse → typed object. Validates snake_case, null handling, ISO 8601, SessionStatus strings.

### 4.2 `frameUtils.test.ts` (Step 19)

**Data source:** In-test `makeThermalFrame()`, `makeSensorOnlyFrame()`, `makeSnapshot()`, `makeReadings()`.

**Data flow:**
```
makeThermalFrame({ thermal_snapshots: [makeSnapshot(10, 425.3)] })
    → extractCenterTemperature(frame) → 425.3
    → extractHeatDissipation(frame) → -5.2 or null
    → hasRequiredSensors(frame) → true/false
    → filterThermalFrames([sensorFrame, thermalFrame]) → [thermalFrame]
```

**Edge cases:** has_thermal_data false, thermal_snapshots undefined/empty, readings empty, no center, optional_sensors null/undefined, empty frames array.

---

## 5. Replay Page Data Flow (Step 21)

**File:** `my-app/src/app/replay/[sessionId]/page.tsx`

**Data flow:**
```
params.sessionId (route)
    → fetchSession(sessionId) — GET /api/sessions/{id}
    → Session (JSON from backend)
    → setSessionData(session)

sessionData
    → useSessionMetadata(session) → { weld_type_label, duration_display, frame_count, ... }
    → useFrameData(session.frames, null, null) → { thermal_frames, all_frames, ... }

frameData.thermal_frames
    → extractHeatmapData(thermal_frames) → HeatmapData (points, timestamps_ms, distances_mm)

session.frames
    → extractAngleData(frames) → AngleData (points, min/max/avg angle)

heatmapData, angleData
    → <HeatMap sessionId={...} data={heatmapData} />
    → <TorchAngleGraph sessionId={...} data={angleData} />
```

**Replay page test:** Mocks `fetchSession` with a minimal Session; asserts components render after load.

---

## 6. Test Data Summary Table

| Test File | Primary Data Source | Helper Functions |
|-----------|---------------------|------------------|
| test_mock_sessions.py | mock_sessions.generate_* | get_center_temp, get_direction_temp, get_thermal_frames |
| test_validation.py | _base_session, _frame, _readings | — |
| test_comparison_edge_cases.py | _frame, _session, _readings | — |
| test_heat_dissipation.py | _frame(ts, center_temp) | — |
| test_serialization.py | _readings, inline models | — |
| test_api_integration.py | _minimal_frame_data, _make_session, _insert_frames | — |
| test_performance.py | mock_sessions.generate_* | — |
| serialization.test.ts | makeReadingsJson, inline JSON | — |
| frameUtils.test.ts | makeThermalFrame, makeSensorOnlyFrame, makeSnapshot | — |
| replay page.test.tsx | jest.mock(fetchSession) with resolved Session | — |

---

## 7. Cross-Cutting Constraints

| Constraint | Where Enforced |
|------------|----------------|
| Mock data passes Session validators | test_mock_sessions (expert, novice, large) |
| Validation rejects invalid data | test_validation (Session, Frame, ThermalSnapshot, TemperaturePoint) |
| Serialization preserves snake_case | test_serialization, serialization.test.ts |
| frameUtils handle null/empty safely | frameUtils.test.ts |
| API returns session with frames | test_api_integration (when SQLAlchemy present) |
| Performance thresholds configurable via env | test_performance (PERFORMANCE_VALIDATE_S, etc.) |
| Replay page fetches and transforms | page.tsx, replay page.test.tsx (mocked fetch) |

---

## 8. Directory Structure (Tests)

```
backend/tests/
├── test_mock_sessions.py       # Step 16 — physics model, expert/novice comparison
├── test_validation.py          # Step 17 — model rejection tests
├── test_comparison_edge_cases.py # Step 17 — compare_sessions edge cases
├── test_heat_dissipation.py    # Step 17 — thermal_service edge cases
├── test_serialization.py       # Step 18 — Python round-trip, snake_case
├── test_api_integration.py     # Step 20 — GET /api/sessions (conditional)
└── test_performance.py         # Step 20 — benchmarks (conditional)

my-app/src/__tests__/
├── serialization.test.ts       # Step 18 — JSON parse, validate
├── utils/frameUtils.test.ts   # Step 19 — extract*, filter*, hasRequiredSensors
└── app/replay/[sessionId]/
    └── page.test.tsx          # Step 21 — replay page with mocked fetchSession
```

---

## 9. Running Tests

**Backend (all tests in steps 16–21):**
```bash
cd backend
PYTHONPATH=. pytest tests/test_mock_sessions.py tests/test_validation.py tests/test_comparison_edge_cases.py tests/test_heat_dissipation.py tests/test_serialization.py -v
```

**API integration (requires SQLAlchemy):**
```bash
pip install SQLAlchemy pysqlite
PYTHONPATH=. pytest tests/test_api_integration.py -v
```

**Performance (requires pytest-benchmark):**
```bash
pip install pytest-benchmark
PERFORMANCE_VALIDATE_S=2.5 pytest tests/test_performance.py -v --benchmark-only
```

**Frontend:**
```bash
cd my-app
npm test
```
