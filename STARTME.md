# Start Me

Quick commands to get the app running.

## Port already in use?

```bash
lsof -ti:8000 | xargs kill -9   # backend
lsof -ti:3000 | xargs kill -9   # frontend
```

## Start Backend

```bash
cd backend
source venv/bin/activate
export ENV=development
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Start Frontend

In a second terminal:

```bash
cd my-app
npm run dev
```

## Seed & Wipe Mock Data

```bash
# Seed (populate)
curl -X POST http://localhost:8000/api/dev/seed-mock-sessions

# Wipe (reset)
curl -X POST http://localhost:8000/api/dev/wipe-mock-sessions
```

Open: http://localhost:3000 | http://localhost:3000/replay/sess_expert_001 | http://localhost:3000/replay/sess_novice_001

## Verify implementation (Steps 1–13)

```bash
# Frontend tests (all)
cd my-app && npm test -- --no-watch --passWithNoTests

# Backend tests with real DB: create SQLite file, seed expert/novice, run validate_frame_fields + pytest
cd backend && source venv/bin/activate && python scripts/verify_steps_with_db.py
```

See **docs/VERIFICATION_REPORT_STEPS_1_TO_13.md** for full verification commands and data-check details.

---

## Where each doc lives

| File | Purpose |
|------|---------|
| **STARTME.md** (root) | This file — quick run commands |
| **QUICK_START.md** (root) | First-time setup (database, .env, npm scripts, troubleshooting) |
| **README.md** (root) | Project overview, structure, tests |
| **backend/SETUP.md** | Backend setup (venv, deps, env vars) |
| **backend/README.md** | Backend API overview |
| **backend/ENV_SETUP.md** | DATABASE_URL and .env details |
