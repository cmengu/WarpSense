# Code Review — Mock Data to Frontend

Comprehensive review of the entire data flow from backend mock generation through API to frontend querying and analysis.

---

## High-Level Summary

### Data Flow Architecture (Intended)

```
Mock (mock_sessions.py) ──► DB (PostgreSQL) ──► API (GET /sessions/{id}) ──► Frontend (fetchSession) ──► Replay Page
         │                         │                       │                          │
         │                         │                       │                          └─► useFrameData, extractHeatmapData, etc.
         └── OR ── Live ingestion (POST /frames)
```

### Critical Finding: **Broken Development Path**

The mock data path is **not wired end-to-end** for development:

1. **No seed mechanism**: `generate_expert_session()` / `generate_novice_session()` produce valid `Session` objects but never reach the database. The API queries `SessionModel` from PostgreSQL—which is empty on a fresh install.
2. **No session creation endpoint**: There is no `POST /sessions` to create a session before `POST /sessions/{id}/frames` can ingest data.
3. **Result**: Visiting `/replay/sess_expert_001` always returns 404 unless the database has been manually seeded.

---

## ✅ Looks Good

- **Logging**: No stray `console.log` in production code; ErrorBoundary uses `logError()` with context. Backend has no debug logging in hot paths.
- **TypeScript**: No `any` types; proper interfaces for Frame, Session, ThermalSnapshot, etc. snake_case alignment with backend.
- **Error handling**: Replay page catches fetch errors; API client throws descriptive errors. ErrorBoundary catches React errors.
- **React/Hooks**: `useEffect` has cleanup (`cancelled` flag); `useMemo` dependencies are correct.
- **Performance**: `useFrameData`, `useSessionMetadata`, `extractHeatmapData`, `extractAngleData` use memoization.
- **Data integrity**: Mock data, validation tests, frameUtils avoid mutating raw data. Heat dissipation pre-calculated on backend.
- **Serialization**: Backend uses `model_dump(mode="json")`; snake_case preserved; serialization tests cover round-trips.
- **Field alignment**: `timestamp_ms`, `heat_dissipation_rate_celsius_per_sec`, `thermal_snapshots`, etc. match across Python and TypeScript.

---

## ⚠️ Issues Found

### **CRITICAL** — [Data Flow] No path from mock data to frontend in development

**Problem**: Mock sessions from `generate_expert_session()` / `generate_novice_session()` are never seeded into the database. GET /api/sessions/{id} queries an empty DB → 404.

**Fix**: Add a seed route (dev-only) or seed script that:
1. Creates `SessionModel` + `FrameModel` rows from `generate_expert_session()` and `generate_novice_session()`.
2. Use `SessionModel.from_pydantic(session)` and persist. See fix plan below.

---

### **HIGH** — [backend/tests/test_api_integration.py:47–71] `_minimal_frame_data` omits `has_thermal_data`

**Problem**: `_minimal_frame_data()` builds raw dicts without `has_thermal_data`. When `with_thermal=True`, frames have `thermal_snapshots` but no `has_thermal_data`. The API returns `frame_data` as-is. Frontend `filterThermalFrames` and `extractHeatmapData` check `has_thermal_data` first—if missing, they treat frames as non-thermal even when `thermal_snapshots` has data.

**Fix**:
```python
def _minimal_frame_data(timestamp_ms: int, with_thermal: bool = False) -> dict:
    data: dict = {
        "timestamp_ms": timestamp_ms,
        "volts": 22.0,
        "amps": 150.0,
        "angle_degrees": 45.0,
        "thermal_snapshots": [],
        "has_thermal_data": False,  # ADD
        "optional_sensors": None,
        "heat_dissipation_rate_celsius_per_sec": None,
    }
    if with_thermal:
        data["thermal_snapshots"] = [...]
        data["has_thermal_data"] = True  # ADD
    return data
```

---

### **HIGH** — [mock_sessions.py:45–46] Imports use `models.*` instead of `backend.models.*`

**Problem**: `from models.frame import Frame` assumes `models` is on the path. When running from project root (e.g. `python -m backend.data.mock_sessions` or pytest with different cwd), imports may fail. Tests use `sys.path.insert` to add backend parent.

**Fix**: Use relative imports or ensure `backend` is the package root: `from backend.models.frame import Frame` (requires `backend` as a package) or keep current structure and document that `PYTHONPATH=.` or running from `backend/` is required. The current setup works when tests/scripts run from `backend/`; add a note to QUICK_START.md if missing.

---

### **MEDIUM** — [Backend] No `POST /sessions` to create sessions

**Problem**: To add frames via `POST /sessions/{id}/frames`, a session must already exist. There is no way to create one via the API. Only manual DB inserts or migrations can create sessions.

**Fix**: Add `POST /api/sessions` that creates a `SessionModel` with status RECORDING, returns `session_id`. Alternatively, the seed route can create sessions as part of dev setup.

---

### **MEDIUM** — [Frontend] Optional `has_thermal_data` when API returns legacy/incomplete data

**Problem**: If the API ever returns frames without `has_thermal_data` (e.g. from old data, test seeds, or manual inserts), frontend utils will incorrectly filter them out. The Frame type declares `has_thermal_data: boolean` (required), but JSON can omit it.

**Fix**: In `filterThermalFrames`, add a fallback when `has_thermal_data` is undefined:
```typescript
return frames.filter((f) => f.has_thermal_data ?? f.thermal_snapshots?.length > 0);
```
This makes the frontend resilient to incomplete API responses while still preferring the explicit flag.

---

### **LOW** — [my-app/src/types/session.ts] Session type lacks `disable_sensor_continuity_checks`

**Problem**: Backend `session_payload` returns `disable_sensor_continuity_checks`, but the TypeScript `Session` interface does not include it. Extra fields are usually fine (JSON allows them), but for full contract alignment it should be declared.

**Fix**: Add `disable_sensor_continuity_checks?: boolean` to the Session interface for documentation and future use.

---

### **LOW** — [Replay page] No ErrorBoundary around charts

**Problem**: If `HeatMap` or `TorchAngleGraph` throws (e.g. malformed data), the whole page can crash. The project has `ErrorBoundary` but it may not wrap the replay page charts.

**Fix**: Wrap the replay visualization section in `<ErrorBoundary>` so a single chart failure does not take down the entire page.

---

## Minute Detail — Field-by-Field Verification

| Layer | Field | Backend | API Response | Frontend Type | Status |
|-------|-------|---------|--------------|---------------|--------|
| Frame | timestamp_ms | ✅ | ✅ | ✅ | OK |
| Frame | volts, amps, angle_degrees | ✅ | ✅ | ✅ | OK |
| Frame | thermal_snapshots | ✅ | ✅ | ✅ | OK |
| Frame | has_thermal_data | ✅ (computed) | ⚠️ (missing when frame_data is raw dict) | ✅ | Fix test seed |
| Frame | heat_dissipation_rate_celsius_per_sec | ✅ | ✅ | ✅ | OK |
| Frame | optional_sensors | ✅ | ✅ | ✅ | OK |
| Session | session_id, operator_id | ✅ | ✅ | ✅ | OK |
| Session | start_time | ISO 8601 | ISO string | string | OK |
| Session | status | enum | string | SessionStatus | OK |
| Session | frames | Frame[] | frame_data dicts | Frame[] | OK |

---

## Fix Plan

### Phase 1: Unblock Development (CRITICAL)

1. **Add dev seed route** (`backend/routes/sessions.py`):
   - `POST /api/dev/seed-mock-sessions` (or `GET /api/dev/seed-mock-sessions` for simplicity)
   - Only enabled when `ENV=development` or `DEBUG=1`
   - Imports `generate_expert_session`, `generate_novice_session`
   - Uses `SessionModel.from_pydantic(session)` to create DB rows
   - Inserts via existing `SessionLocal`
   - Returns `{ "seeded": ["sess_expert_001", "sess_novice_001"] }`
   - Document in QUICK_START: run backend, call seed, then visit `/replay/sess_expert_001`

2. **Fix `_minimal_frame_data`** in `test_api_integration.py`:
   - Add `has_thermal_data: with_thermal` so seeded frames match the contract
   - Ensures integration tests produce API responses the frontend can use correctly

### Phase 2: Resilience (HIGH/MEDIUM)

3. **Frontend fallback for `has_thermal_data`**:
   - Update `filterThermalFrames` to fall back to `thermal_snapshots?.length > 0` when `has_thermal_data` is undefined
   - Same pattern in `extractHeatmapData` if it directly checks the flag

4. **Optional: `POST /api/sessions`**:
   - Create session with RECORDING status
   - Required for live ingestion flow; can defer if only using mock for now

### Phase 3: Polish (LOW)

5. Add `disable_sensor_continuity_checks` to Session TypeScript interface
6. Wrap replay charts in `ErrorBoundary`
7. Document Python path requirements for mock_sessions (QUICK_START, SETUP)

---

## Summary

| Category | Count |
|----------|-------|
| Files reviewed | ~25 |
| Critical issues | 1 |
| High issues | 2 |
| Medium issues | 2 |
| Low issues | 2 |

**Priority**: Implement Phase 1 (seed route + test fix) to unblock end-to-end development. Phase 2 improves robustness. Phase 3 is optional polish.
