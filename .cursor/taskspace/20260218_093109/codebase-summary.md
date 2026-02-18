
---

## Codebase summary (≤50 lines)

### 1. Tech stack and libraries
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Three.js, @react-three/fiber, @react-three/drei
- **Backend:** Python 3, FastAPI, Uvicorn, python-dotenv
- **DB:** PostgreSQL, SQLAlchemy, Alembic, psycopg2
- **Testing:** Jest, React Testing Library, Playwright (e2e), pytest, httpx

### 2. Main directories and roles
- `my-app/` — Next.js frontend (welding UI)
- `my-app/src/app/` — Next.js App Router routes
- `my-app/src/components/` — React components
- `my-app/src/lib/` — API client and shared logic
- `my-app/src/types/` — TypeScript types
- `my-app/src/utils/` — Pure helpers
- `backend/` — FastAPI server
- `backend/routes/` — API route modules
- `backend/services/` — Business logic (aggregate, thermal, comparison)
- `backend/models/` — Pydantic schemas and domain models
- `backend/database/` — SQLAlchemy ORM and connection
- `backend/alembic/` — Migrations

### 3. Entry points
- `backend/main.py` — FastAPI app and route setup
- `my-app/src/app/layout.tsx` — Root layout
- `my-app/src/app/page.tsx` — Landing
- `package.json` — Monorepo scripts (`dev`, `test`, `build`)

### 4. Files important for new features
- `backend/routes/sessions.py` — Session CRUD and frames API
- `backend/routes/aggregate.py` — Aggregate KPIs
- `backend/services/aggregate_service.py` — Aggregate logic
- `backend/database/models.py` — ORM models
- `backend/models/session.py`, `backend/models/frame.py` — Session/frame models
- `my-app/src/lib/api.ts` — Backend API client
- `my-app/src/app/replay/[sessionId]/page.tsx` — Replay page
- `my-app/src/app/(app)/dashboard/page.tsx` — Dashboard
- `my-app/src/app/(app)/supervisor/page.tsx` — Supervisor view
- `my-app/src/components/welding/` — Welding viz components

### 5. Architecture
- Monorepo with separate Next.js and FastAPI apps
- 3-tier: API routes → services → database/models
- Frontend calls backend via `api.ts`
- Session/frame centric; append-only raw data
- Backend computes features and scores; frontend focuses on display and replay
