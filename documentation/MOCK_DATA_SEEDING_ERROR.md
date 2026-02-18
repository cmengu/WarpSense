# Mock Data Seeding Error — Column Missing

**Error:** `column sessions.score_total does not exist`

**Category:** Backend / Database  
**Severity:** High (blocks seed, replay, dashboard)  
**Date documented:** 2026-02-18

---

## Exact Error Message

```
psycopg2.errors.UndefinedColumn: column sessions.score_total does not exist
LINE 1: ...sessions.version AS sessions_version, sessions.score_total AS sessions_score_total, sessions.process_type AS sessions_process_type...
```

Often also mentions `sessions.process_type` if both migrations were pending.

---

## What It Means

The **PostgreSQL database schema is out of sync** with the SQLAlchemy models. The code expects columns (`score_total`, `process_type`) that were never added to the `sessions` table via migrations.

**Impact:**
- `POST /api/dev/seed-mock-sessions` returns 500 Internal Server Error
- Replay page cannot load session data
- Dashboard and seagull routes may fail
- Backend health check can pass (DB connects) but queries fail

---

## Root Cause

| Cause | Description |
|-------|-------------|
| **Migrations not run** | Alembic migrations 003 and 004 add `score_total` and `process_type`. If the DB was created before those migrations existed, or you switched to a fresh DB, the columns are missing. |
| **Fresh database** | New PostgreSQL instance or wiped DB has base schema only; migrations must be applied. |
| **Schema drift** | Someone altered models without running or creating migrations. |

**Why it plagues us:** The backend starts successfully (DB connection works). The error only surfaces when the seed route or session queries run—so the first symptom is "Internal Server Error" when seeding, with no obvious clue until we inspect the traceback.

---

## The Fix

Run Alembic migrations from the backend directory:

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

This applies:
- **003_add_score_total** — adds `score_total` (nullable)
- **004_weld_thresholds_process_type** — adds `process_type`, creates `weld_thresholds` table

Then seed again:

```bash
curl -X POST http://localhost:8000/api/dev/seed-mock-sessions
```

---

## Prevention

### Before First Run (or New DB)

1. **Run migrations before seeding:**
   ```bash
   cd backend && source venv/bin/activate && alembic upgrade head
   ```

2. **Verify schema:** After migrations, `\d sessions` in `psql` should show `score_total` and `process_type`.

### Process Level

- [ ] Add to **QUICK_START.md** or **STARTME.md**: "If fresh DB: run `alembic upgrade head` before seed."
- [ ] Consider adding a **pre-seed health check** that queries `sessions` with `LIMIT 0` to surface missing-column errors early.

### AI / Onboarding

When setting up a new environment or helping someone debug "Internal Server Error" on seed:

> "If seed returns 500, check for `UndefinedColumn` in the response. Run `alembic upgrade head` in the backend directory. See documentation/MOCK_DATA_SEEDING_ERROR.md."

---

## Related Migrations

| Migration | Adds |
|-----------|------|
| `003_add_score_total` | `sessions.score_total` (Integer, nullable) |
| `004_weld_thresholds_process_type` | `sessions.process_type` (String, default `"mig"`), `weld_thresholds` table |

---

## Quick Reference

| Symptom | Likely Cause | Fix |
|---------|---------------|-----|
| Seed returns 500, "score_total does not exist" | Migrations not applied | Local: `alembic upgrade head` |
| Seed returns 403 | ENV not `development` | Start backend with `ENV=development` |
| Seed succeeds but replay fails | CORS or backend down | See STARTME.md network notes |
