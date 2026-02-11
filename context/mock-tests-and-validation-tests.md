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
