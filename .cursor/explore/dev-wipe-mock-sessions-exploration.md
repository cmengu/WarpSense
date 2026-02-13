# Exploration: Dev Wipe Mock Sessions Endpoint

## Summary

Add `POST /api/dev/wipe-mock-sessions` to delete the mock sessions (`sess_expert_001`, `sess_novice_001`). Single file change, mirrors seed route, no frontend impact.

---

## Current State

### Route registration (main.py)

```
app.include_router(dev_router, prefix="/api/dev", tags=["dev"])
```

- Existing: `POST /api/dev/seed-mock-sessions`
- New: `POST /api/dev/wipe-mock-sessions`

### Dev route structure (dev.py)

- `_is_dev_mode()` — checks `ENV=development` or `DEBUG=1`
- `get_db()` — yields SQLAlchemy session
- `seed_mock_sessions` — deletes existing, generates Pydantic sessions, converts to `SessionModel`, commits

### Data model

| Table    | PK        | FK / cascade |
|----------|-----------|--------------|
| sessions | session_id | — |
| frames   | id        | session_id → sessions.session_id, `ondelete="CASCADE"` |

ORM: `SessionModel.frames` has `cascade="all, delete-orphan"`.

Deleting a session causes frames to be removed via:
1. ORM cascade
2. DB-level FK `ondelete="CASCADE"` (if bulk delete bypasses ORM)

---

## Integration

### Data flow

```
User/dev runs: curl -X POST http://localhost:8000/api/dev/wipe-mock-sessions
       │
       ▼
FastAPI routes to wipe_mock_sessions()
       │
       ├── _is_dev_mode() → false → 403
       │
       └── _is_dev_mode() → true
               │
               ▼
       db.query(SessionModel).filter(session_id.in_(['sess_expert_001','sess_novice_001'])).delete()
               │
               ▼
       db.commit()
               │
               ▼
       return {"deleted": N}
```

### Dependencies

| Dependency            | Status |
|-----------------------|--------|
| `SessionModel`        | Already imported in dev.py |
| `get_db`, `_is_dev_mode` | In dev.py |
| DB connection         | Via existing `get_db` |
| main.py route wiring  | No change (wipe lives under same dev router) |

### Constraints

- Dev-only: 403 when not in dev mode (same as seed)
- Target sessions: `sess_expert_001`, `sess_novice_001`
- Must stay in sync with seed if seed IDs change

---

## High-Level Mock Execution

### Implementation pattern

```
wipe_mock_sessions():
  - Guard: if not _is_dev_mode() → HTTPException(403)
  - session_ids = ["sess_expert_001", "sess_novice_001"]
  - deleted = db.query(SessionModel).filter(SessionModel.session_id.in_(session_ids)).delete(synchronize_session=False)
  - db.commit()
  - return {"deleted": deleted}
```

### Why bulk delete

- Seed uses iterate-and-delete; wipe can use bulk delete because:
  - Single table (sessions)
  - Fixed set of IDs
  - DB cascade handles frames
- Bulk delete is simpler and returns count directly.

### Edge cases

| Case                      | Handling |
|---------------------------|----------|
| Neither session exists    | `deleted=0` — success |
| One session exists        | `deleted=1` — success |
| Both exist                | `deleted=2` — success |
| Not in dev mode           | 403 before DB access |
| DB error during delete    | Exception propagates (FastAPI 500) |
| DB error during commit    | Exception propagates (FastAPI 500) |

No special handling needed; idempotent and safe.

---

## Files to Modify

```
backend/
  routes/
    dev.py                    MODIFY — add wipe_mock_sessions route

Optional (docs only):
  QUICK_START.md              MODIFY — add wipe curl example in “Using Seed” section
```

No new files.

---

## Implementation Approach

### Why this structure

1. Single file change: all dev routes live in `dev.py`.
2. Same guard as seed: `_is_dev_mode()`.
3. Same pattern: async route, `Depends(get_db)`, explicit IDs, commit, JSON response.
4. Bulk delete: one query, count returned, DB cascade for frames.

### Alternatives considered

| Option                               | Rejected because |
|--------------------------------------|------------------|
| Wipe all sessions                    | Too destructive; might remove non-mock data |
| Parameter to choose what to wipe      | Overkill for dev-only endpoint |
| New file `routes/dev_wipe.py`         | Only one route; keep with seed in dev.py |
| Fetch then delete (ORM cascade only) | Bulk delete + DB cascade is simpler |

---

## SQLAlchemy detail

`delete(synchronize_session=False)`:

- Emits `DELETE FROM sessions WHERE session_id IN ('sess_expert_001','sess_novice_001')`.
- Returns number of rows deleted.
- `synchronize_session=False` avoids identity map sync during bulk delete.
- DB FK `ondelete="CASCADE"` deletes matching rows in `frames`.

---

## Response shape

```json
{"deleted": 2}
```

Or `{"deleted": 0}` if neither session existed. Keeps behavior clear for scripts/tools.

---

## Tests (optional)

No tests exist for `seed-mock-sessions`. If adding tests:

```
backend/tests/
  test_dev_routes.py (NEW) — or add to existing test file
    - test_wipe_returns_403_when_not_dev_mode
    - test_wipe_deletes_mock_sessions_when_dev_mode
    - test_wipe_idempotent_returns_0_when_none_exist
```

Requires `ENV=development` or `DEBUG=1` for dev routes. Not blocking for a first implementation.

---

## Documentation

- QUICK_START.md: add a short “Wipe mock sessions” subsection with the curl command.
- Issue snippet: already has full implementation notes.

---

## Questions / Ambiguities

1. **Response format** — Is `{"deleted": N}` sufficient, or do we also want `{"deleted": N, "ids": ["sess_expert_001", "sess_novice_001"]}` for clarity?
2. **Tests** — Add pytest coverage for wipe (and optionally seed) now, or defer?
3. **QUICK_START** — Update with wipe example, or leave for a later docs pass?
