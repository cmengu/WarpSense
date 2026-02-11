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
