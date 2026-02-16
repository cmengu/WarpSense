# [Feature] Production Deploy (Docker + One-Click)

## TL;DR

Deploying the Shipyard Welding platform to a customer server currently requires 15+ manual steps over 2–3 hours with ~20 potential failure points: installing PostgreSQL, creating DB, cloning the repo, installing Python and Node dependencies, running migrations, configuring .env, and starting backend and frontend separately. This blocks customer trials and makes the platform appear unprofessional. The core problem is the absence of a packaged, repeatable deployment path. We need a one-command deploy via Docker Compose that builds and runs PostgreSQL, backend, and frontend containers, applies migrations automatically, seeds demo data, and exposes the app at http://localhost:3000 in ~5 minutes. This aligns with our vision of a production-ready, enterprise-grade welding analytics platform.

---

## Current State (What Exists Today)

### What's in place

- **Backend:** `backend/main.py`
  - FastAPI app, CORS via `CORS_ORIGINS` env var (default `http://localhost:3000`)
  - Health endpoint: `GET /health` returns `{"status":"ok"}` when DB reachable
  - Requires `DATABASE_URL` (from `backend/.env` or env); fails fast if unset
  - Start: `uvicorn main:app --host 0.0.0.0 --port 8000`

- **Database:** `backend/database/connection.py`, `backend/alembic/`
  - PostgreSQL via `DATABASE_URL` (no fallback)
  - Alembic migrations in `backend/alembic/versions/` (001_initial_schema, 002_add_disable_sensor_continuity_checks)
  - `load_env_from_backend()` loads `backend/.env` when present

- **Seed:** `backend/routes/dev.py`, `backend/data/mock_sessions.py`
  - `POST /api/dev/seed-mock-sessions` when `ENV=development` or `DEBUG=1`
  - `generate_expert_session(session_id="sess_expert_001")`, `generate_novice_session(session_id="sess_novice_001")`
  - `SessionModel.from_pydantic(session)` used for persistence

- **Frontend:** `my-app/`
  - Next.js 16, `npm run build` + `npm start` for production
  - API base URL: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) in `my-app/src/lib/api.ts`
  - API calls are made from the **browser**, so the URL must be reachable from the user's machine

- **Setup scripts:**
  - `backend/setup.sh`: venv + pip install + .env template
  - `start-all.sh`: starts backend (uvicorn) + frontend (npm run dev) for local dev

### What's missing

- No `docker-compose.yml`
- No `backend/Dockerfile` or `my-app/Dockerfile`
- No `deploy.sh` one-command script
- No `.env.example` at repo root for Docker (backend has `backend/.env.example`)

### Broken / manual user flows

1. Customer: "Can we try this on our server?" → Engineer spends 2–3 hours manually installing PostgreSQL, Python, Node, cloning, configuring, migrating, starting services
2. Deploy to 10 customers → 10 different setups, no guarantee of consistency
3. New engineer onboarding → Must follow STARTME, QUICK_START, backend/SETUP, frontend setup separately

### Technical gaps

- Backend uses `CORS_ORIGINS` (not `ALLOWED_ORIGINS` as in some Docker plans)
- Seed in deploy script must call `generate_expert_session(session_id="sess_expert_001")` (not mutate after creation)
- Frontend `NEXT_PUBLIC_API_URL` must be the URL the **browser** uses (e.g. `http://localhost:8000` when accessing via localhost; `http://<server-ip>:8000` when remote). `http://backend:8000` is wrong (only resolvable inside Docker network)
- Backend healthcheck: `requests` not in requirements; use `curl` or add `requests`/`httpx`

---

## Desired Outcome (What Should Happen)

### User-facing changes

- User can run `./deploy.sh` from repo root
- Script completes in ~5 minutes (first run; image pulls)
- User sees clear success message with URLs: Frontend 3000, Demo 3000/demo, Backend docs 8000/docs
- User can open http://localhost:3000 (or http://&lt;server-ip&gt;:3000) and use the app
- Demo sessions `sess_expert_001`, `sess_novice_001` are seeded and viewable at `/replay/sess_expert_001`, `/replay/sess_novice_001`

### Technical changes

- New: `docker-compose.yml` (root), `backend/Dockerfile`, `my-app/Dockerfile`
- New: `deploy.sh` (root, executable)
- New: `.env.example` at root for Docker (DB_PASSWORD, optional vars)
- Modified: `.gitignore` — ensure `.env` is ignored
- No code changes to backend/frontend logic (containerization only)

### Success criteria (minimum 10 acceptance criteria)

1. **[ ]** `./deploy.sh` runs from repo root without errors
2. **[ ]** Deploy completes in &lt;10 minutes on first run (typical connection)
3. **[ ]** `docker-compose ps` shows all 3 services `Up (healthy)`
4. **[ ]** `curl http://localhost:8000/health` returns `{"status":"ok"}`
5. **[ ]** `curl http://localhost:8000/api/sessions/sess_expert_001` returns valid session (after seed)
6. **[ ]** Browser at http://localhost:3000 loads homepage
7. **[ ]** Browser at http://localhost:3000/demo loads demo page
8. **[ ]** Replay at http://localhost:3000/replay/sess_expert_001 loads session data from API
9. **[ ]** DB password generated securely and saved to `.env` when not set
10. **[ ]** Re-running `./deploy.sh` on same machine is idempotent (no crash; seed skips if data exists)
11. **[ ]** `docker-compose down` stops all services; `docker-compose down -v` removes data
12. **[ ]** Works on Ubuntu 22.04 (or similar) with Docker 20+ and Docker Compose v2

### Quality requirements

- Works on Linux (Ubuntu 22.04, Debian, Amazon Linux 2)
- macOS: Docker Desktop (development / local verification)
- Script checks Docker and docker-compose before starting
- No hardcoded secrets; `DB_PASSWORD` generated or from env
- Backend runs Alembic migrations on startup (`alembic upgrade head`)
- Health checks: postgres (pg_isready), backend (/health), frontend (wget/spider)

---

## Scope Boundaries (What's In/Out)

### In scope

- Docker Compose stack: PostgreSQL 15-alpine, FastAPI backend, Next.js frontend
- One-command `deploy.sh`: prerequisites check, build, up, health wait, demo seed
- Persistent volume for `postgres_data`
- Backend auto-migrates on container start
- Demo data seeding (sess_expert_001, sess_novice_001) on first deploy
- `.env.example` at root; `.env` generated by deploy (DB_PASSWORD)
- Documentation: README section or DEPLOY.md with prerequisites and commands

### Out of scope

- Kubernetes, Helm, or other orchestrators
- CI/CD pipeline integration (separate work)
- Production TLS/HTTPS, reverse proxy (Nginx/Traefik)
- Multi-node / clustering
- Automated backups or DB maintenance
- Docker-based development workflow (keep existing venv + npm dev)
- Remote access / NAT configuration (document firewall if needed)

---

## Known Constraints & Context

### Technical constraints

- Must use existing backend (`main.py`), frontend (`my-app`), and Alembic migrations
- Backend expects `DATABASE_URL`; connection loads from `backend/.env` when present; docker-compose will pass `DATABASE_URL` via env (overrides file)
- Backend uses `CORS_ORIGINS` (comma-separated), not `ALLOWED_ORIGINS`
- Frontend `NEXT_PUBLIC_API_URL` is baked in at build time; for same-host: `http://localhost:8000`; for remote access, user may need to set it before build (or use same-origin proxy in future)
- `requirements.txt` does not include `requests`; backend healthcheck in Docker should use `curl` (ensure base image has it) or add minimal dep

### Business constraints

- Target: customer trials in 5 minutes instead of 2–3 hours
- Must work on AWS, Azure, DigitalOcean, on-prem (any host with Docker)

### Design constraints

- Match project conventions: append-only data, single source of truth, no silent failures
- Use postgres:15-alpine, python:3.11-slim, node:20-alpine for consistency and smaller images

---

## Related Context (Prior Art & Dependencies)

### Existing code

- `backend/routes/dev.py` — seed pattern (generate_expert_session, generate_novice_session, SessionModel.from_pydantic)
- `backend/scripts/verify_steps_with_db.py` — similar seed logic with DB
- `backend/database/connection.py` — `load_env_from_backend()`, `get_database_url()`, `SessionLocal`
- `backend/database/models.py` — `SessionModel.from_pydantic(session)`
- `backend/data/mock_sessions.py` — `generate_expert_session(session_id=...)`, `generate_novice_session(session_id=...)`
- `my-app/src/lib/api.ts` — `API_BASE_URL` from `NEXT_PUBLIC_API_URL`

### Related docs

- `.cursor/issues/docker.md` — prior Docker architecture and implementation notes
- `context/tech-stack-mvp-archi.md` — stack and data flow
- `backend/SETUP.md` — local setup
- `QUICK_START.md` — first-time setup
- `documentation/WEBGL_CONTEXT_LOSS.md`, `LEARNING_LOG.md` — 3D/WebGL context limits (no change for deploy)

### Dependencies

- Blocked by: None (ready to start)
- Blocks: Future production hardening (TLS, reverse proxy, monitoring)

---

## Open Questions & Ambiguities

1. **NEXT_PUBLIC_API_URL for remote access**
   - Why unclear: Build-time var; when user accesses via `http://<server-ip>:3000`, browser must reach `<server-ip>:8000`
   - Impact: Remote users may see API failures if URL is wrong
   - Current assumption: For MVP, document that same-machine (localhost) works out of box; for remote, set `NEXT_PUBLIC_API_URL=http://<host>:8000` before `docker-compose build` or add optional env to compose

2. **init-db.sql**
   - Why unclear: Some plans reference `./backend/init-db.sql` for custom init
   - Impact: Alembic handles schema; init-db.sql is optional for extra setup
   - Current assumption: Omit for MVP; Alembic migrations sufficient

3. **docker-compose vs docker compose**
   - Why unclear: v1 uses `docker-compose`, v2 uses `docker compose`
   - Impact: Script compatibility
   - Current assumption: Prefer `docker compose` (v2) with fallback to `docker-compose`

4. **Minimum RAM**
   - Why unclear: No formal requirement
   - Impact: Large sessions or low RAM could cause OOM
   - Current assumption: Document 2GB minimum in README/DEPLOY.md

5. **Port conflicts**
   - Why unclear: 3000/8000/5432 might be in use
   - Impact: Containers fail to bind
   - Current assumption: Script checks ports with `lsof` or similar; exits with clear message if in use

---

## Initial Risk Assessment

1. **Frontend API URL misconfiguration**
   - Why risky: `NEXT_PUBLIC_API_URL` baked at build; wrong value = broken API calls from browser
   - Impact: Replay/demo pages fail to load data
   - Likelihood: Medium (common Docker gotcha)

2. **CORS mismatch**
   - Why risky: Backend uses `CORS_ORIGINS`; Docker plans sometimes say `ALLOWED_ORIGINS`
   - Impact: Browser blocks API requests
   - Likelihood: Low (easy to fix once identified)

3. **Seed script path/imports**
   - Why risky: Deploy runs Python in container; must run from `/app` with correct PYTHONPATH
   - Impact: Seed fails; no demo data
   - Likelihood: Medium (import paths differ in container)

4. **Healthcheck timing**
   - Why risky: Backend depends on postgres; frontend depends on backend; slow start can fail health checks
   - Impact: deploy.sh timeout or false failure
   - Likelihood: Low (adjust start_period and timeouts)

5. **Base image tooling**
   - Why risky: python:3.11-slim may lack `curl`; healthcheck assumes it
   - Impact: Healthcheck fails
   - Likelihood: Low (install curl in Dockerfile or use Python/httpx)

---

## Classification & Metadata

**Type:** feature  
**Priority:** high  
**Effort:** medium (12–20 hours)  
**Category:** infrastructure  

---

## Strategic Context (Product Vision Alignment)

- Supports goal: "Production-ready platform that customers can self-host"
- Enables: Faster trials, repeatable deploys across environments, enterprise credibility
- Addresses: Top friction point — "too complicated to deploy"

**User impact**

- Frequency: Every new customer trial, internal demo, staging deploy
- User segment: Sales, customers evaluating, DevOps
- Satisfaction impact: Reduces setup from hours to minutes; signals professionalism

**Technical impact**

- Code health: Neutral (adds infra, no app logic change)
- Team velocity: Faster onboarding, consistent environments
- Tech debt: Minimal (isolated Docker configs)

---

## Implementation Reference (From Prior Planning)

The following structure is provided as reference for exploration/planning. Exploration phase should validate and adapt.

### Container layout

```
postgres (5432) ← backend (8000) ← frontend (3000)
         ↓              ↓                ↓
    postgres_data   alembic upgrade   npm run build
                    head + uvicorn    npm start
```

### Key file additions

- `docker-compose.yml` — services: postgres, backend, frontend; volumes; networks; healthchecks
- `backend/Dockerfile` — multi-stage; python:3.11-slim; alembic upgrade head + uvicorn
- `my-app/Dockerfile` — multi-stage; node:20-alpine; npm run build; npm start
- `deploy.sh` — check Docker; generate DB_PASSWORD; build; up; wait healthy; seed demo data

### Env var mapping

| Service   | Key vars                                                |
|-----------|----------------------------------------------------------|
| postgres  | POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD            |
| backend   | DATABASE_URL, CORS_ORIGINS, ENVIRONMENT, DEBUG           |
| frontend  | NEXT_PUBLIC_API_URL (build-time; browser-reachable URL)  |

---

## Self-Review Checklist

- [x] Spent adequate time on context and codebase search
- [x] Title specific and actionable
- [x] TL;DR explains what and why
- [x] Current state with file references
- [x] 10+ acceptance criteria
- [x] Scope in/out defined
- [x] Constraints and dependencies listed
- [x] Open questions and assumptions documented
- [x] 5 risks identified
- [x] Classification filled
- [x] Strategic context included
- [x] Codebase searched for related patterns
- [x] Documentation reviewed

---

## Next Steps

1. **Exploration Phase** — Validate Dockerfile paths, env vars, seed script; confirm CORS_ORIGINS; resolve NEXT_PUBLIC_API_URL for remote access
2. **Create Plan** — Step-by-step implementation with verification commands
3. **Execute** — Implement, test locally, verify on clean Ubuntu/DigitalOcean if possible
