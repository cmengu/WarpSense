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
