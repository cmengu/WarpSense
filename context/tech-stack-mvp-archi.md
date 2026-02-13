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
