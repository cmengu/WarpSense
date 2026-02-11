# Overall Stack Context — Mock Data to Frontend

Compiled context for the entire Shipyard Welding MVP stack. This document summarizes how data flows from mock data (or live sensors) through the backend to the frontend, and how weld sessions can be analyzed and visualized.

---

## 1. Scope and Architecture Overview

**Purpose:** Record welding sessions, replay them, and analyze quality via thermal profiles, torch angle, heat dissipation, and session-to-session comparison.

**Design principles (from workspace rules):**
- Raw sensor data is append-only.
- Feature extraction is pure and deterministic.
- Scoring is stateless and reproducible.
- Replays must be exact.
- Never silently fail; never guess values; explicit units in names.

---

## 2. End-to-End Data Flow — Mock to Frontend

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ ORIGIN: MOCK DATA OR LIVE SENSORS                                                  │
└────────────────────────────────────────────────────────────────────────────────────┘

  Option A: Mock (backend/data/mock_sessions.py)                 Option B: Live (ESP32/ingestion)
  ┌─────────────────────────────────────┐                        ┌─────────────────────────────────────┐
  │ generate_expert_session()            │                        │ POST /api/sessions/{id}/frames       │
  │ generate_novice_session()             │                        │ addFrames(sessionId, frames)        │
  │ generate_large_session()              │                        │ 1000–5000 frames per request         │
  │ → Session (Pydantic, in-memory)       │                        │ → routes/sessions.py                 │
  └─────────────────────────────────────┘                        └─────────────────────────────────────┘
                    │                                                        │
                    │ (tests only, or seed scripts)                           │
                    ▼                                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ PERSISTENCE: PostgreSQL (SQLAlchemy ORM)                                          │
│   sessions table → SessionModel                                                    │
│   frames table → FrameModel.frame_data (JSONB) — full Frame per row                │
└────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ API: GET /api/sessions/{session_id}                                                 │
│   routes/sessions.py → query SessionModel + FrameModel                             │
│   → frame_to_dict() (includes thermal_snapshots when include_thermal=true)         │
│   → session_payload(frames) → JSON                                                 │
└────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ FRONTEND: lib/api.ts → fetchSession(sessionId)                                     │
│   GET /api/sessions/{id} → response.json()                                         │
│   → Session (typed, snake_case)                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ REPLAY PAGE: app/replay/[sessionId]/page.tsx                                        │
│   sessionData → useSessionMetadata(session) → metadata (duration, weld_type, …)    │
│   session.frames → useFrameData(frames) → thermal_frames, all_frames               │
│   extractHeatmapData(thermal_frames) → HeatmapData                                 │
│   extractAngleData(frames) → AngleData                                             │
│   → HeatMap(data=heatmapData), TorchAngleGraph(data=angleData), ScorePanel        │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow — Mock Data Path (Development / Tests)

**File:** `backend/data/mock_sessions.py`

Mock sessions are **in-memory Pydantic Sessions**. They do not touch the database unless explicitly seeded (e.g. via test fixtures that insert into SQLite/Postgres).

**Flow when using mock data:**
```
generate_expert_session() / generate_novice_session()
    → generate_frames(duration_ms, get_amps, get_volts, get_angle, include_thermal_gap)
    → for t in [0, 10, 20, ...]: Frame with thermal_snapshots when t % 100 == 0
    → generate_thermal_snapshots(t, amps, volts, angle) → TemperaturePoint[] (physics model)
    → calculate_heat_dissipation(prev_frame, curr_frame) via thermal_service
    → Session(frames=[...], status=COMPLETE)
```

**To get mock data to the frontend:**
1. **Tests:** `test_api_integration.py` seeds `_minimal_frame_data` into in-memory SQLite; `test_mock_sessions.py` uses Session objects directly.
2. **Development:** No built-in seed route. To replay mock sessions in the browser:
   - Add a dev route that inserts `generate_expert_session()` / `generate_novice_session()` into the DB and returns `session_id`, then visit `/replay/{session_id}`; or
   - Mock `fetchSession` in the frontend to return `generate_expert_session().model_dump(mode="json")` (requires serializing Python output to JSON for frontend consumption).

---

## 4. Data Flow — Live Ingestion Path

**File:** `backend/routes/sessions.py`

**POST /api/sessions/{session_id}/frames**
- Accepts 1000–5000 frames per request.
- Validates: timestamps strictly increasing, 10 ms apart; thermal distances consistent.
- For each frame with thermal data: `calculate_heat_dissipation(prev_frame, curr_frame)` (or `get_previous_frame` from DB when prev not in batch).
- Persists `FrameModel.frame_data` (full Frame as JSONB).
- Returns `AddFramesResponse` (successful_count, failed_frames, next_expected_timestamp, can_resume).

**Flow:**
```
Frontend/ESP32 → addFrames(sessionId, frames)
    → POST /api/sessions/{id}/frames
    → Pydantic validation (Frame[], Session status)
    → thermal_service.calculate_heat_dissipation
    → FrameModel.from_pydantic(frame) → db.add()
    → SessionModel.frame_count, status updated
```

---

## 5. Analysis Capabilities — How We Can Analyze Sessions

### 5.1 Thermal Visualization (Heatmap)

**Backend:** No transformation; raw `thermal_snapshots` in each Frame.

**Frontend:** `utils/heatmapData.ts` → `extractHeatmapData(frames, direction?)`

**Flow:**
```
Session.frames (Frame[])
    → filterThermalFrames (has_thermal_data === true)
    → flatten thermal_snapshots[] → readings[] (default direction="center")
    → HeatmapData: points[], timestamps_ms[], distances_mm[], point_count
    → HeatMap component (grid: time × distance → temperature)
```

**Analysis:** Per-frame center temperature at each distance; north/south asymmetry indicates angle drift; east > west indicates travel direction.

---

### 5.2 Torch Angle Over Time

**Backend:** `angle_degrees` stored per Frame (optional).

**Frontend:** `utils/angleData.ts` → `extractAngleData(frames)`

**Flow:**
```
Session.frames (Frame[])
    → filter frames with angle_degrees != null
    → sort by timestamp
    → AngleData: points[], min_angle_degrees, max_angle_degrees, avg_angle_degrees
    → TorchAngleGraph component (time-series line chart)
```

**Analysis:** Angle drift (e.g. novice 45° → 65°) correlates with north/south thermal asymmetry.

---

### 5.3 Heat Dissipation Rate

**Backend:** `services/thermal_service.py` → `calculate_heat_dissipation(prev_frame, curr_frame)`

**Formula:** `(prev_center_temp - curr_center_temp) / 0.1` — units: °C/sec. Positive = cooling.

**Flow:**
```
During ingestion: prev_frame (from batch or DB) + curr_frame
    → _extract_center_temperature_celsius(prev), _extract_center_temperature_celsius(curr)
    → (prev - curr) / 0.1
    → stored in frame.heat_dissipation_rate_celsius_per_sec

Frontend: frameUtils.extractHeatDissipation(frame)
    → returns frame.heat_dissipation_rate_celsius_per_sec ?? null (no recomputation)
```

**Analysis:** Expert: ~20–40°C/sec consistent cooling. Novice: erratic 10–120°C/sec with amps spikes.

---

### 5.4 Session-to-Session Comparison

**Backend:** `services/comparison_service.py` → `compare_sessions(session_a, session_b)`

**Frontend:** `hooks/useSessionComparison.ts` → `compareSessions(sessionA, sessionB)` (mirrors backend).

**Flow:**
```
session_a.frames, session_b.frames
    → index by timestamp_ms
    → shared_timestamps = intersection
    → for each shared timestamp:
        FrameDelta(timestamp_ms, amps_delta, volts_delta, angle_degrees_delta,
                   heat_dissipation_rate_celsius_per_sec_delta, thermal_deltas)
    → List[FrameDelta]
```

**Analysis:** Where expert vs novice differ: amps spikes, volt drift, angle drift, thermal asymmetry, heat dissipation swings.

---

### 5.5 Rule-Based Scoring (Placeholder)

**Backend:** `scoring/rule_based.py` → `score_session(session, features)`  
**Features:** `features/extractor.py` → `extract_features(session)` (returns `{}` — TODO).

**Current state:** Returns `SessionScore(total=0, rules=[])`. ScorePanel shows "Coming soon".

**Intended flow:**
```
Session → extract_features() → features dict
    → score_session(session, features) → SessionScore (rules[], total)
    → API / frontend ScorePanel
```

---

## 6. Canonical Types and Validation Boundaries

| Layer | Models | Validators |
|-------|--------|------------|
| Backend | Session, Frame, ThermalSnapshot, TemperaturePoint (Pydantic) | frame_count match, timestamps ~10ms, thermal distances, sensor continuity, thermal snapshot structure |
| API | JSON (snake_case, ISO 8601 datetimes, SessionStatus string) | Same shape as Pydantic `model_dump(mode="json")` |
| Frontend | Session, Frame, ThermalSnapshot (TypeScript interfaces) | validateSession, validateFrame, validateThermalSnapshot (lightweight runtime guards) |

**Constraint:** Frontend never recomputes heat dissipation; backend is the source of truth.

---

## 7. Key File Map — Where Things Live

| Concern | Backend | Frontend |
|---------|---------|----------|
| Session model | models/session.py | types/session.ts |
| Frame model | models/frame.py | types/frame.ts |
| Thermal model | models/thermal.py | types/thermal.ts |
| Mock data | data/mock_sessions.py | — (or fetch from dev API) |
| Heat dissipation | services/thermal_service.py | utils/frameUtils.ts (extract only) |
| Session comparison | services/comparison_service.py | hooks/useSessionComparison.ts |
| Heatmap extraction | — | utils/heatmapData.ts |
| Angle extraction | — | utils/angleData.ts |
| Scoring | scoring/rule_based.py, features/extractor.py | components/welding/ScorePanel.tsx |
| API | routes/sessions.py | lib/api.ts |
| Replay page | — | app/replay/[sessionId]/page.tsx |

---

## 8. Cross-Cutting Constraints

| Constraint | Where Enforced |
|------------|----------------|
| Raw sensor data append-only | routes/sessions.py (add frames only; no updates) |
| Heat dissipation computed at ingestion only | thermal_service, routes/sessions.py |
| Frontend never mutates raw data | frameUtils, heatmapData, angleData (pure functions) |
| snake_case everywhere, no conversion layer | All types, API, constants |
| Always guard has_thermal_data, thermal_snapshots, readings | frameUtils, heatmapData, useSessionComparison |
| Units in names (timestamp_ms, temp_celsius, etc.) | All models and types |
| Replays exact (no interpolation) | Frame ordering, no synthetic frames |

---

## 9. Related Context Files

- **backend-skeleton-architecture.md** — Backend models, DB, routes, services.
- **frontend-skeleton-architecture.md** — Frontend types, utils, hooks, components.
- **mock-tests-and-validation-tests.md** — Test data flow, mock consumers, validation coverage.
