
## Codebase summary

**1. Tech stack and main libraries**  
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Three.js, @react-three/fiber, @react-three/drei  
- my-app/package.json  
- Backend: FastAPI, uvicorn, SQLAlchemy, alembic, psycopg2  
- backend/requirements.txt  
- Tools: Jest, React Testing Library, pytest, httpx  

**2. Key directories**  
- my-app/ — Next.js frontend  
- backend/ — FastAPI backend  
- my-app/src/app/ — App router pages and routes  
- backend/routes/ — API route modules (aggregate, dashboard, sessions, dev)  
- backend/services/ — aggregate_service, thermal_service, comparison_service  
- backend/models/ — aggregate, session, scoring, thermal, frame, comparison  
- backend/database/ — connection, models, base  
- backend/scoring/ — rule-based scoring  
- backend/features/ — extractor  
- backend/alembic/ — DB migrations  
- my-app/src/components/ — UI (welding, dashboard, charts, demo)  
- my-app/src/lib/ — api, export, aggregate-transform, demo-config, ai-feedback  
- my-app/src/hooks/ — useSessionMetadata, useFrameData, useSessionComparison  
- my-app/e2e/ — Playwright E2E tests  

**3. Main entry points**  
- backend/main.py — FastAPI app  
- my-app/src/app/layout.tsx — Root layout  
- my-app/src/app/page.tsx — Home  
- package.json — npm run dev:all (concurrent backend + frontend)  

**4. Files to add/extend features**  
- backend/routes/*.py — new or updated API endpoints  
- backend/services/aggregate_service.py — aggregate logic  
- backend/models/session.py — session model  
- backend/database/models.py — DB schema  
- my-app/src/lib/api.ts — API client  
- my-app/src/app/replay/[sessionId]/page.tsx — replay view  
- my-app/src/app/compare/ — comparison view  
- my-app/src/components/welding/ — replay and torch components  
- my-app/src/app/(app)/supervisor/page.tsx — supervisor dashboard  
- backend/routes/aggregate.py — aggregate API  

**5. Architecture**  
- Monorepo, client–server: Next.js → FastAPI → PostgreSQL  
- Append-only sensor data, backend-only scoring, backend heat dissipation  
- REST APIs (snake_case JSON), WebGL limited to at most 2 Canvas per page
