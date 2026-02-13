# Add Dev Wipe Mock Sessions Endpoint

**Type:** Feature  
**Priority:** Normal  
**Effort:** Small  
**Status:** Done  

---

## TL;DR

Add `POST /api/dev/wipe-mock-sessions` next to the existing seed route. Lets devs quickly reset mock data: seed → test → wipe → repeat.

---

## Current State vs Expected

| State | Current | Expected |
|-------|---------|----------|
| **Dev workflow** | Can seed mock sessions; no way to remove them without DB access | Seed + wipe both available as HTTP endpoints |
| **Usage** | Must manually delete rows or truncate if you want a clean slate | `curl -X POST .../wipe-mock-sessions` removes mock sessions |

---

## Relevant Files

| File | Change |
|------|--------|
| `backend/routes/dev.py` | Add `POST /wipe-mock-sessions` route |

---

## Implementation Notes

- **Where:** `backend/routes/dev.py`, alongside `seed-mock-sessions`
- **Guard:** Reuse `_is_dev_mode()` (same as seed — ENV=development or DEBUG=1)
- **Model:** `SessionModel` — filter by `session_id` (primary key), not `id`
- **Target IDs:** `sess_expert_001`, `sess_novice_001` (same as seed)
- **Cascade:** `SessionModel.frames` has `cascade="all, delete-orphan"` — deleting sessions removes frames automatically

```python
@router.post("/wipe-mock-sessions")
async def wipe_mock_sessions(db: OrmSession = Depends(get_db)):
    """..."""
    # ... guard, delete, commit ...
    return {"deleted": deleted, "ids": session_ids}
```

---

## Usage

```bash
# Seed
curl -X POST http://localhost:8000/api/dev/seed-mock-sessions

# Test frontend...

# Wipe
curl -X POST http://localhost:8000/api/dev/wipe-mock-sessions
```

---

## Risks / Notes

- No risk to production: route returns 403 when not in dev mode
- Consider returning `{"deleted": deleted}` so callers know how many rows were removed
