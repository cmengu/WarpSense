# Production Deploy (Docker + One-Click) — Implementation Plan

**Overall Progress:** 0% (0/18 steps completed)

---

## TLDR

One-command Docker deployment for the Shipyard Welding platform. After `./deploy.sh`, customers get PostgreSQL, FastAPI backend, and Next.js frontend running in ~5 minutes with migrations applied and demo data seeded. Replaces 2–3 hour manual setup across 20 failure points. **Key architecture:** Relative API URLs + Next.js streaming proxy make the frontend image portable (same image works on localhost, remote server, or behind reverse proxy); backend entrypoint runs migrations → seed → uvicorn so demo data exists before API serves traffic; deploy.sh verifies demo data via poll (up to 50s) before declaring success.

---

## Critical Architectural Decisions

### Decision 1: Relative API URLs + Next.js Proxy (Streaming) — Not Build-Time NEXT_PUBLIC_API_URL

**Choice:** Frontend uses relative URLs (`/api/*`); Next.js Route Handler proxies to backend at runtime via `BACKEND_URL` env var. Proxy **streams** responses (uses `res.body` directly) — never buffers large payloads.

**Rationale:** `NEXT_PUBLIC_API_URL` is baked at build time. If deployed to AWS, the browser would try localhost:8000. Rebuilding per environment is brittle. With relative URLs + streaming proxy: same image works on localhost, remote server, or behind reverse proxy. Session with 15,000 frames (~5–10MB JSON) must stream; buffering causes memory spike and OOM during investor demo.

**Trade-offs:** One Route Handler file; frontend always goes through Next.js for API. Slightly more latency (one hop). Enables single-origin, simpler CORS.

**Impact:** `api.ts` uses empty `API_BASE_URL`; `app/api/[...path]/route.ts` streams to backend; `docker-compose` sets `BACKEND_URL=http://backend:8000`; local dev uses `BACKEND_URL=http://localhost:8000` in `.env.local`.

---

### Decision 2: Seed at Backend Startup via Entrypoint Script — Not deploy.sh exec

**Choice:** Backend runs `docker-entrypoint.sh`: migrations → seed → uvicorn. Demo data exists before API serves traffic.

**Rationale:** Exec-after-start causes race: first 30s after deploy, /api/sessions/sess_expert_001 returns 404. Using an entrypoint script with explicit `cd /app` avoids cwd issues; `exec uvicorn` ensures proper signal handling (SIGTERM to PID 1).

**Trade-offs:** Slightly slower backend startup (~5–10s). Seed runs on every container start (idempotent).

**Impact:** Create `backend/docker-entrypoint.sh`; backend Dockerfile CMD runs entrypoint; remove seed from deploy.sh.

---

### Decision 3: Poll for Demo Data Verification — Not Fixed Sleep

**Choice:** deploy.sh polls `http://localhost:8000/api/sessions/sess_expert_001` up to 50s (10 tries × 5s) with 5s intervals. Exits early on 200; fails with log tail on final timeout.

**Rationale:** Health check passed ≠ API immediately ready. Fixed 5s sleep might not be enough on slow systems; too long wastes time on fast systems. Poll is robust and exits early on success.

**Trade-offs:** Slightly more complex script. Max 50s wait on worst case.

**Impact:** Step 4.3 uses `for i in $(seq 1 10)` loop with curl; break on success; exit 1 with logs on failure.

---

### Decision 4: Secure .env Generation

**Choice:** When generating `DB_PASSWORD`, write `.env` with `umask 077` so file is not world-readable. Never echo password to terminal.

**Rationale:** Default `echo ... > .env` creates world-readable file; password in terminal history.

**Impact:** `(umask 077; printf 'DB_PASSWORD=%s\n' "$DB_PASSWORD" > .env)`; overwrites .env on first deploy.

---

### Decision 5: CORS Includes localhost AND 127.0.0.1

**Choice:** Default `CORS_ORIGINS` includes both `http://localhost:3000` and `http://127.0.0.1:3000`.

**Rationale:** Browsers treat localhost and 127.0.0.1 as different origins. Customer accessing via `http://127.0.0.1:3000` would get CORS errors with only localhost.

**Impact:** docker-compose: `CORS_ORIGINS: "${CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000}"`.

---

### Decision 6: Explicit Per-Service Health Check — Not jq/grep

**Choice:** deploy.sh waits until each of postgres, backend, frontend reports healthy using `docker compose ps <service> --format '{{.Health}}'`. No jq, no grep on combined output.

**Rationale:** `grep -c "healthy"` can falsely match service names; NDJSON + jq returns wrong count. Explicit per-service checks show exactly which service is stuck on timeout.

**Impact:** Replace loop with `wait_for_health()` that checks postgres, backend, frontend by name.

---

## Dependency Ordering

| Step | Depends On | Blocks | Can Mock? |
|------|-----------|--------|-----------|
| 1.1 API proxy (streaming + timeout) | Nothing | 1.2, 3.x | N/A |
| 1.2 api.ts relative URLs | 1.1 | 3.1 | Yes (mock fetch) |
| 2.1 PostgreSQL verify | Nothing | 2.2 | N/A |
| 2.2 Backend entrypoint + seed | 2.1 | 4.3, 4.4 | Yes |
| 2.3 Backend CORS | Nothing | Integration | No |
| 3.1 Frontend Dockerfile (remove build arg) | 1.2 | 4.x | Yes |
| 3.2 Frontend BACKEND_URL | — | deploy | No |
| 4.1 deploy.sh secure .env | Nothing | 4.2 | No |
| 4.2 deploy.sh health check | All services | 4.3 | No |
| 4.3 deploy.sh verify seed (poll) | 4.2, 2.2 | Success | No |
| 4.4 deploy.sh remove seed exec | 2.2 | — | No |
| 4.5 Port check (optional) | Nothing | up | No |
| 5.1 .env.example | Nothing | User setup | N/A |
| 5.2 DEPLOY.md | All phases | — | N/A |

**Parallelizable:** 1.1 + 2.1 together; 1.2 after 1.1; 2.3 anytime.

---

## Risk Heatmap

| Phase | Step | Risk | Probability | What Could Go Wrong | Early Detection | Mitigation |
|-------|------|------|-------------|---------------------|-----------------|------------|
| 1 | 1.1 Proxy buffers large response | 🔴 70% | OOM on 15k-frame session | time-to-first-byte > 5s | Stream res.body, no arrayBuffer |
| 1 | 1.1 Timeout not supported | 🟢 15% | AbortSignal.timeout missing in Node <18 | Test fails | Require Node 18+ |
| 2 | 2.2 Entrypoint / seed cwd | 🟡 40% | PYTHONPATH or cwd wrong | docker logs traceback | cd /app in entrypoint |
| 4 | 4.2 Health check format | 🟡 45% | `--format` differs by compose version | Script fails/hangs | Test on Docker 20+, Compose V2 |
| 4 | 4.3 Poll before ready | 🟢 15% | Curl before backend serves | False negative | Poll 10×5s; retry on 404 |
| 4 | Port conflict | 🟡 35% | 3000/8000 in use | Bind error | Pre-check lsof; clear error |

**Highest priority:** API proxy streaming (production blocker), Health check logic (reliability), Poll verification (user trust).

---

## Implementation Phases

### Phase 1 — API Proxy & Portable Frontend (4–6 hours)

**Goal:** Frontend uses relative URLs; Next.js proxy streams /api/* to backend with timeout and error handling. Same image works on localhost and remote servers.

**Why this phase first:** Fixes the biggest deployment risk before containerization. Must work with large sessions (15k frames) for investor demo.

**Time Estimate:** 4–6 hours (includes streaming debugging, large-response testing)

**Risk Level:** 🟡 50%

---

#### 🟥 Step 1.1: Create Next.js API Proxy Route Handler — *Critical: Architecture + Production blocker for large sessions*

**Why this is critical:** New data flow for all API calls. Buffering large responses causes OOM; streaming is mandatory for sessions with 15k+ frames.

**Context:**
- Backend routes: /health, /api/dashboard, /api/sessions, /api/sessions/{id}, /api/sessions/{id}/score, /api/sessions/{id}/frames, /api/dev/*
- Backend uses `StreamingResponse` for sessions with stream=true and >1000 frames
- Proxy must forward method, headers, body, query params
- **Must stream** `res.body` — never `await res.arrayBuffer()` for large payloads
- 30s timeout to prevent hung requests
- Specific error handling: TimeoutError → 504, AbortError → 499, network → 502

**Files:**
- **Create:** `my-app/src/app/api/[...path]/route.ts`

**Code Implementation:**

```typescript
// my-app/src/app/api/[...path]/route.ts

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const PROXY_TIMEOUT_MS = 30000; // 30s

function buildBackendUrl(path: string[], request: NextRequest): string {
  const pathStr = path.join('/');
  const url = new URL(`/api/${pathStr}`, BACKEND_URL);
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });
  return url.toString();
}

async function copyHeaders(request: NextRequest, excludeHost = true): Promise<Headers> {
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (excludeHost && key.toLowerCase() === 'host') return;
    headers.set(key, value);
  });
  return headers;
}

async function proxyRequest(
  request: NextRequest,
  params: { path: string[] },
  method: string
) {
  const { path } = params;
  const backendUrl = buildBackendUrl(path, request);
  const headers = await copyHeaders(request);
  const body = method !== 'GET' && method !== 'HEAD' ? await request.arrayBuffer() : undefined;

  try {
    const res = await fetch(backendUrl, {
      method,
      headers,
      body,
      signal: AbortSignal.timeout(PROXY_TIMEOUT_MS),
    });

    const contentType = res.headers.get('content-type') || 'application/json';

    // CRITICAL: Stream response, do NOT buffer. Large sessions (15k frames = 5–10MB)
    // would cause memory spike and OOM if buffered.
    return new Response(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: {
        'Content-Type': contentType,
        ...(res.headers.get('content-length') && {
          'Content-Length': res.headers.get('content-length')!,
        }),
      },
    });
  } catch (err) {
    if (err instanceof Error) {
      if (err.name === 'TimeoutError' || err.name === 'AbortError') {
        return NextResponse.json(
          { detail: err.name === 'TimeoutError' ? 'Request timeout' : 'Request cancelled' },
          { status: err.name === 'TimeoutError' ? 504 : 499 }
        );
      }
    }
    console.error('API proxy error:', err);
    return NextResponse.json(
      { detail: 'Backend unreachable' },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params, 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params, 'POST');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params, 'PUT');
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params, 'PATCH');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, await params, 'DELETE');
}
```

**Note:** `AbortSignal.timeout(30000)` (Node 18+) throws `DOMException` with `name === 'TimeoutError'` on timeout.

**Subtasks:**
- [ ] 🟥 Create `my-app/src/app/api/[...path]/route.ts` (note: Next.js 13+ app router uses `[...path]` for catch-all)
- [ ] 🟥 Implement GET, POST, PUT, PATCH, DELETE
- [ ] 🟥 Return streaming response: `new Response(res.body, {...})` — no `arrayBuffer()`
- [ ] 🟥 Add 30s timeout via `AbortSignal.timeout(30000)`
- [ ] 🟥 Handle TimeoutError (504), AbortError (499), generic (502)
- [ ] 🟥 Add `BACKEND_URL` to `.env.example` (default `http://localhost:8000`)

**✓ Verification Test:**

**Action:**
1. Set `BACKEND_URL=http://localhost:8000` in `my-app/.env.local`
2. Start backend: `cd backend && uvicorn main:app --reload --port 8000`
3. Seed data: Ensure sess_expert_001 exists (run `backend/scripts/seed_demo_data.py` after backend DB is ready, or use POST /api/dev/seed-mock-sessions in development)
4. Start frontend: `cd my-app && npm run dev`
5. Test proxy: `curl -s http://localhost:3000/api/dashboard | head -c 200`
6. **Large session (streaming):** `curl -w '\nTime-to-first-byte: %{time_starttransfer}s\n' -o /dev/null -s http://localhost:3000/api/sessions/sess_expert_001` — time-to-first-byte should be < 500ms
7. Test backend down: stop backend, `curl http://localhost:3000/api/dashboard` → 502

**Expected Result:**
- GET /api/dashboard returns proxied JSON
- GET /api/sessions/sess_expert_001 streams; time-to-first-byte < 500ms
- Network tab shows request to 3000, not 8000
- Backend unreachable → 502 with `{ detail: 'Backend unreachable' }`

**How to Observe:**
- **Visual:** Dashboard/replay pages load data
- **Console:** No errors in Next.js server logs
- **Network:** Browser DevTools → Network → requests to localhost:3000/api/*
- **curl:** `curl -w '%{time_starttransfer}' -o /dev/null -s http://localhost:3000/api/sessions/sess_expert_001`

**Pass Criteria:**
- GET /api/dashboard succeeds
- GET /api/sessions/sess_expert_001 succeeds; time-to-first-byte < 500ms
- POST /api/sessions forwards body
- 502 when backend down
- No `arrayBuffer()` or buffering of response body in proxy code

**Common Failures & Fixes:**
- **If time-to-first-byte > 5s:** Proxy is buffering — ensure `return new Response(res.body, ...)` not `await res.arrayBuffer()`
- **If 502 always:** Verify BACKEND_URL and backend running
- **If "Cannot find module" for route:** File must be at `app/api/[...path]/route.ts` (Next.js app router)
- **If /api/dashboard 404:** Backend uses /api prefix for sessions; dashboard may be at /api/dashboard — verify backend routes

---

#### 🟥 Step 1.2: Update api.ts to Use Relative URLs — *Critical: Data flow*

**Why this is critical:** Switches all API calls from absolute to relative URLs. All fetch calls must hit same-origin so proxy handles them.

**Context:**
- Current: `API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"` — absolute URLs
- Target: `API_BASE_URL = ''` — relative URLs; buildUrl returns pathname + search
- api.test.ts expects `buildUrl("/api/sessions/sess_001")` to equal `${API_BASE_URL}/api/sessions/sess_001` — must update to `/api/sessions/sess_001` when base empty

**Files:**
- **Modify:** `my-app/src/lib/api.ts` (lines 26-27, buildUrl function)
- **Modify:** `my-app/src/__tests__/lib/api.test.ts` (buildUrl and API_BASE_URL expectations)

**Code Implementation:**

```typescript
// my-app/src/lib/api.ts — configuration section

/**
 * Backend API base URL.
 * Empty = relative URLs; Next.js proxy at /api/* handles routing.
 * (NEXT_PUBLIC_API_URL kept for backward compat in non-Docker dev.)
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

function buildUrl(
  path: string,
  params: Record<string, string | number | boolean | undefined> = {}
): string {
  const base = API_BASE_URL || 'http://localhost'; // Dummy origin for URL parsing when relative
  const url = new URL(path, base);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }
  return API_BASE_URL ? url.toString() : url.pathname + url.search;
}
```

**Subtasks:**
- [ ] 🟥 Set `API_BASE_URL` from `NEXT_PUBLIC_API_URL || ''` (empty when not set = relative)
- [ ] 🟥 Update `buildUrl` to return `pathname + search` when base empty
- [ ] 🟥 Update `my-app/src/__tests__/lib/api.test.ts`:
  - Change `buildUrl` test: when `API_BASE_URL` is `''`, `buildUrl('/api/sessions/sess_001')` returns `/api/sessions/sess_001` (not full URL)
  - Change `API_BASE_URL` test: expect `''` when `NEXT_PUBLIC_API_URL` unset (or mock it for both modes)
  - `fetchSession` etc. tests: called URL should be relative when in relative mode
- [ ] 🟥 Ensure tests pass: `cd my-app && npm test -- api.test.ts`

**✓ Verification Test:**

**Action:**
1. With proxy and backend running
2. Open http://localhost:3000/replay/sess_expert_001
3. Network tab: requests go to localhost:3000/api/... (not 8000)
4. Data loads

**Pass Criteria:**
- `buildUrl('/api/sessions', {})` returns `/api/sessions` when API_BASE_URL empty
- `buildUrl('/api/sessions/sess_1', { limit: 10 })` returns `/api/sessions/sess_1?limit=10`
- api.test.ts passes
- Replay page loads session data

**Common Failures & Fixes:**
- **If buildUrl returns full URL:** Check fallback when API_BASE_URL is '' — use pathname + search
- **If tests fail:** api.test.ts may set API_BASE_URL via env; ensure relative-URL tests added/updated

---

### Phase 2 — Infrastructure Foundation (2–3 hours)

**Goal:** PostgreSQL and backend containers run; migrations apply; seed runs at startup via entrypoint; backend healthy.

**Time Estimate:** 2–3 hours

**Risk Level:** 🟡 40%

---

#### 🟥 Step 2.1: PostgreSQL Service (Verify & Harden)

**Subtasks:**
- [ ] 🟥 Verify postgres service in docker-compose.yml (already exists)
- [ ] 🟥 Ensure init-db.sql mount is `:ro` (already `:ro` in current)
- [ ] 🟥 Health check present and correct: `pg_isready -U welding_user -d welding_sessions`

**Files:** `docker-compose.yml` (verify only; may need no changes)

**✓ Verification Test:**

**Action:**
1. `docker compose up -d postgres`
2. Wait 15s
3. `docker compose exec postgres psql -U welding_user -d welding_sessions -c "SELECT 1"`

**Expected Result:** Outputs `1`

**Pass Criteria:** psql returns exit 0, prints 1

---

#### 🟥 Step 2.2: Backend Entrypoint Script + Seed in CMD — *Critical: Startup order + robustness*

**Why this is critical:** Seed must run before uvicorn. Shell `sh -c "..."` does not guarantee cwd; seed script uses `Path(__file__).parents[1]` which assumes /app. Entrypoint with explicit `cd /app` and `exec uvicorn` ensures correct cwd and signal handling.

**Context:**
- Current CMD: `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000`
- Seed script: `python scripts/seed_demo_data.py` at `/app/scripts/seed_demo_data.py`; parents[1] = /app
- New: Create `docker-entrypoint.sh`; CMD runs it

**Files:**
- **Create:** `backend/docker-entrypoint.sh`
- **Modify:** `backend/Dockerfile` (add COPY entrypoint, chmod, CMD)

**Code Implementation:**

**File: backend/docker-entrypoint.sh**

```bash
#!/bin/bash
set -e
cd /app

echo "Running migrations..."
alembic upgrade head

echo "Seeding demo data (idempotent)..."
python scripts/seed_demo_data.py || { echo "Seed failed"; exit 1; }

echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
```

**File: backend/Dockerfile — changes**

```dockerfile
# After COPY . . and before USER appuser, add:
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Replace CMD (remove current CMD line)
CMD ["/app/docker-entrypoint.sh"]
```

**Subtasks:**
- [ ] 🟥 Create `backend/docker-entrypoint.sh`
- [ ] 🟥 Add `cd /app` at start
- [ ] 🟥 Run alembic, seed, then `exec uvicorn`
- [ ] 🟥 Update Dockerfile: COPY entrypoint, chmod +x, CMD

**✓ Verification Test:**

**Action:**
1. `docker compose down -v`
2. `docker compose up -d postgres backend`
3. `docker compose logs -f backend` — expect "Running migrations" → "Demo data seeded" or "already exists" → "Starting uvicorn"
4. Immediately after healthy: `curl -sf http://localhost:8000/api/sessions/sess_expert_001 | head -c 500`
5. Restart: `docker compose restart backend` — logs show "Demo data already exists, skipping."

**Expected Result:**
- sess_expert_001 returns 200 as soon as backend healthy
- Idempotent on restart
- No cwd-related import errors

**Pass Criteria:**
- curl returns 200 with JSON
- Logs show seed ran before uvicorn
- Restart skips seed (already exists)

**Common Failures & Fixes:**
- **If "ModuleNotFoundError: data.mock_sessions":** PYTHONPATH issue — seed runs from /app; ensure `cd /app` in entrypoint
- **If "Seed failed":** Check database connectivity; postgres must be healthy first
- **If chmod fails in Dockerfile:** COPY before RUN chmod; entrypoint must be in /app before USER switch

---

#### 🟥 Step 2.3: Backend CORS — Add 127.0.0.1

**Subtasks:**
- [ ] 🟥 Set `CORS_ORIGINS: "${CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000}"` in docker-compose backend service
- [ ] 🟥 Document in .env.example for remote: `CORS_ORIGINS=http://YOUR_IP:3000,...`

**Files:** `docker-compose.yml` (backend environment), `.env.example`

**✓ Verification Test:**

**Action:**
1. Set `CORS_ORIGINS=http://192.168.1.100:3000` in .env (use your LAN IP)
2. `docker compose up -d backend`
3. From another machine, open frontend at http://YOUR_IP:3000; API should not CORS-fail

**Pass Criteria:** No CORS errors when accessing from 127.0.0.1 or custom IP

---

### Phase 3 — Frontend Container (1–2 hours)

**Goal:** Frontend container builds and runs; proxy routes to backend. No build-time API URL.

**Time Estimate:** 1–2 hours

**Risk Level:** 🟢 20%

---

#### 🟥 Step 3.1: Frontend Dockerfile — Remove NEXT_PUBLIC_API_URL Build Arg

**Subtasks:**
- [ ] 🟥 Remove `ARG NEXT_PUBLIC_API_URL` and `ENV NEXT_PUBLIC_API_URL` from my-app/Dockerfile (if present)
- [ ] 🟥 Remove `args: NEXT_PUBLIC_API_URL` from docker-compose frontend service

**Files:** `my-app/Dockerfile`, `docker-compose.yml`

**✓ Verification Test:**

**Action:**
1. `docker compose build frontend --no-cache`
2. `docker compose up -d`
3. Open http://localhost:3000/demo, http://localhost:3000/replay/sess_expert_001
4. Data loads via proxy (requests to 3000, not 8000)

**Pass Criteria:** Build succeeds; demo and replay pages load data

---

#### 🟥 Step 3.2: Frontend Service — Add BACKEND_URL

**Subtasks:**
- [ ] 🟥 Add `BACKEND_URL: http://backend:8000` to frontend service environment in docker-compose
- [ ] 🟥 Next.js server-side proxy uses this to reach backend on internal network

**Files:** `docker-compose.yml` (frontend environment)

**✓ Verification Test:**

**Action:**
1. `docker compose up -d`
2. `curl -s http://localhost:3000/api/dashboard | head -c 200`

**Expected Result:** Dashboard JSON

**Pass Criteria:** curl returns valid JSON from dashboard endpoint

---

### Phase 4 — Deploy Script Fixes (3–4 hours)

**Goal:** deploy.sh generates secure .env, waits for all 3 healthy (explicit per-service), verifies demo data via poll, no longer runs seed.

**Time Estimate:** 3–4 hours

**Risk Level:** 🟡 45%

---

#### 🟥 Step 4.1: Secure .env Generation — *Critical: Secrets*

**Files:** `deploy.sh`

**Code Implementation:**

```bash
if [ -z "$DB_PASSWORD" ]; then
  echo "🔐 Generating secure database password..."
  export DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
  (umask 077; printf 'DB_PASSWORD=%s\n' "$DB_PASSWORD" > .env)
  echo "✅ Password saved to .env (keep this file secure!)"
else
  echo "✅ Using existing DB_PASSWORD from environment"
fi
```

**Subtasks:**
- [ ] 🟥 Use `(umask 077; printf ... > .env)` instead of `echo ... > .env`
- [ ] 🟥 Never echo DB_PASSWORD to terminal

**✓ Verification Test:**

**Action:**
1. Remove .env if exists
2. Run deploy.sh (or source the password block in isolation)
3. `ls -la .env` → file permission should be `-rw-------` (600)

**Pass Criteria:** `.env` has mode 600 (owner read/write only)

---

#### 🟥 Step 4.2: Wait for All 3 Services Healthy — *Critical: Correct logic*

**Why this is critical:** Grep on combined output can falsely match; explicit per-service check is reliable.

**Files:** `deploy.sh`

**Code Implementation:**

```bash
wait_for_health() {
  local max_wait=120
  local elapsed=0

  while [ $elapsed -lt $max_wait ]; do
    local postgres_health="$($COMPOSE ps postgres --format '{{.Health}}' 2>/dev/null || echo "starting")"
    local backend_health="$($COMPOSE ps backend --format '{{.Health}}' 2>/dev/null || echo "starting")"
    local frontend_health="$($COMPOSE ps frontend --format '{{.Health}}' 2>/dev/null || echo "starting")"

    if [ "$postgres_health" = "healthy" ] && \
       [ "$backend_health" = "healthy" ] && \
       [ "$frontend_health" = "healthy" ]; then
      echo ""
      echo "✅ All 3 services healthy"
      return 0
    fi

    printf "."
    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo ""
  echo "❌ Timeout. Service status:"
  echo "  postgres: $postgres_health"
  echo "  backend: $backend_health"
  echo "  frontend: $frontend_health"
  $COMPOSE ps
  return 1
}

# Replace the for loop with:
echo "⏳ Waiting for services to start (up to 120 seconds)..."
wait_for_health || exit 1
```

**Subtasks:**
- [ ] 🟥 Replace existing health-wait loop with `wait_for_health`
- [ ] 🟥 Check each service by name: `$COMPOSE ps postgres --format '{{.Health}}'`
- [ ] 🟥 On timeout, print each service's health
- [ ] 🟥 Exit 1 on timeout

**✓ Verification Test:**

**Action:**
1. `docker compose down`
2. `./deploy.sh`
3. Script prints "✅ All 3 services healthy" only when all three healthy
4. Simulate failure: `docker compose stop backend` then run deploy — should eventually timeout with backend status shown

**Pass Criteria:** Clear per-service status on timeout; no false "healthy" from grep

---

#### 🟥 Step 4.3: Verify Demo Data — Poll Up to 50s — *Critical: User trust*

**Why this is critical:** Health check passed ≠ API immediately ready. Fixed 5s sleep is brittle. Poll exits early on success; robust on slow systems.

**Files:** `deploy.sh`

**Code Implementation:**

```bash
# After health check passes, verify demo data exists (poll up to 50s)
echo "🔍 Verifying demo data..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/api/sessions/sess_expert_001 >/dev/null 2>&1; then
    echo "✅ Demo data verified"
    break
  fi
  if [ $i -eq 10 ]; then
    echo "❌ Demo data missing after 50s. Check backend logs:"
    $COMPOSE logs backend | tail -50
    exit 1
  fi
  printf "."
  sleep 5
done
```

**Subtasks:**
- [ ] 🟥 Add verification block after health check
- [ ] 🟥 Poll curl up to 10 times with 5s sleep (50s max)
- [ ] 🟥 Break on first 200
- [ ] 🟥 On final failure: print backend log tail, exit 1

**✓ Verification Test:**

**Action:**
1. Temporarily break seed (e.g. wrong path in entrypoint: `python scripts/nonexistent.py`)
2. deploy.sh should eventually fail with "Demo data missing" and log output
3. Fix seed; deploy should pass with "✅ Demo data verified" early (within first few retries)

**Pass Criteria:**
- Deploy fails with clear message when seed broken
- Deploy passes when seed works
- Exits early when curl succeeds (doesn't wait full 50s on success)

**Common Failures & Fixes:**
- **If always fails even when seed works:** Backend may not be listening on host yet — ensure port 8000 is mapped and backend binds 0.0.0.0
- **If curl hangs:** Add `-m 10` to curl for per-request timeout

---

#### 🟥 Step 4.4: Remove Seed from deploy.sh

**Subtasks:**
- [ ] 🟥 Remove "🌱 Seeding demo data..." block (the `$COMPOSE exec -T backend python scripts/seed_demo_data.py` block)
- [ ] 🟥 Seed is now in backend entrypoint (Step 2.2)

**Files:** `deploy.sh`

**✓ Verification Test:** deploy.sh no longer contains `exec.*seed_demo_data`

---

#### 🟥 Step 4.5: Optional Port Check

**Subtasks:**
- [ ] 🟥 Before `$COMPOSE up -d`, check ports 3000 and 8000
- [ ] 🟥 If in use: `lsof -i :3000` or equivalent; exit with "Port 3000 is in use. Stop the process or change the port."

**Files:** `deploy.sh`

**Code snippet:**

```bash
check_ports() {
  for port in 3000 8000; do
    if lsof -i :$port >/dev/null 2>&1; then
      echo "❌ Port $port is in use. Free it before deploying:"
      lsof -i :$port
      exit 1
    fi
  done
}
# Call before: $COMPOSE up -d
check_ports
```

**✓ Verification Test:** Start something on 3000, run deploy.sh → exits with clear message

---

### Phase 5 — Documentation (1 hour)

**Goal:** .env.example and DEPLOY.md complete. Document streaming, CORS, verify steps.

---

#### 🟥 Step 5.1: Update .env.example

**Files:** `.env.example`

**Content:**

```
# Shipyard Welding — Environment variables for Docker deploy
# Copy to .env and customize: cp .env.example .env
# deploy.sh will auto-generate DB_PASSWORD if not set

# Database (required for deploy.sh)
DB_PASSWORD=CHANGE_ME_ON_DEPLOY

# Backend URL for Next.js API proxy (server-side only)
# Local dev: http://localhost:8000
# Docker: http://backend:8000 (set in docker-compose)
BACKEND_URL=http://localhost:8000

# For remote deployment, add your server's origin to CORS:
# CORS_ORIGINS=http://YOUR_SERVER_IP:3000,http://localhost:3000,http://127.0.0.1:3000
```

**Note:** NEXT_PUBLIC_API_URL no longer needed for Docker (relative URLs + proxy).

---

#### 🟥 Step 5.2: Update DEPLOY.md

**Subtasks:**
- [ ] 🟥 Document that NEXT_PUBLIC_API_URL is not needed for Docker deploy
- [ ] 🟥 Document BACKEND_URL, CORS_ORIGINS for remote
- [ ] 🟥 Add "Minimum 2GB RAM"
- [ ] 🟥 Document streaming proxy (large sessions work)
- [ ] 🟥 Verify all curl commands work
- [ ] 🟥 Document deploy.sh verification steps (health check, demo data poll)

**Files:** `DEPLOY.md`

---

## Pre-Flight Checklist

**Print this and check before starting each phase:**

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Node 18+ installed | `node --version` → v18.x.x or higher | ⬜ |
| | Backend runs locally | `cd backend && uvicorn main:app --port 8000` → healthy | ⬜ |
| | Database + seed | sess_expert_001 exists (run seed script) | ⬜ |
| **Phase 2** | Docker 20+ | `docker --version` | ⬜ |
| | Docker Compose V2 or v1 | `docker compose version` or `docker-compose --version` | ⬜ |
| **Phase 3** | Phase 1+2 complete | API proxy works, backend containerized | ⬜ |
| **Phase 4** | Phase 3 complete | All services build and run | ⬜ |
| **Phase 5** | Phase 4 complete | deploy.sh passes end-to-end | ⬜ |

---

## Success Criteria (End-to-End)

**After all phases complete, these must be true:**

| Feature Requirement | Target Behavior | Verification Method |
|---------------------|-----------------|---------------------|
| **One-command deploy** | `./deploy.sh` completes | Run from repo root → "✅ Deployment Complete!" |
| **All services healthy** | 3/3 healthy | `docker compose ps` shows healthy |
| **API portable** | Same image on localhost and remote | Deploy to EC2; access via http://IP:3000 |
| **Demo data at startup** | No 404 for sess_expert_001 | curl immediately after healthy |
| **Demo data verified** | deploy fails if seed missing | Break seed; deploy fails with log tail |
| **Large session streams** | 15k frames doesn't OOM | curl sess_expert_001; time-to-first-byte < 500ms |
| **Secure .env** | Not world-readable | `ls -la .env` → 600 |
| **Stop/remove** | down, down -v work | `docker compose down`, `docker compose down -v` |
| **Idempotent re-run** | Second deploy succeeds | Run ./deploy.sh twice |
| **Poll verification** | Exits early on success | deploy passes; doesn't wait full 50s |

---

## Progress Tracking

**Update this table as you complete steps:**

| Phase | Steps | Completed | Percentage |
|-------|-------|-----------|------------|
| Phase 1 | 2 | 0 | 0% |
| Phase 2 | 3 | 0 | 0% |
| Phase 3 | 2 | 0 | 0% |
| Phase 4 | 5 | 0 | 0% |
| Phase 5 | 2 | 0 | 0% |
| **Total** | **18** | **0** | **0%** |

---

## Notes & Learnings

[Add during implementation]

---

## Critical vs Non-Critical Steps

| Step | Critical? | Reason |
|------|-----------|--------|
| 1.1 API Proxy | ✅ Yes | Data flow; streaming blocks OOM |
| 1.2 api.ts | ✅ Yes | Data flow |
| 2.1 PostgreSQL | ❌ No | Verify only |
| 2.2 Entrypoint + seed | ✅ Yes | Startup order, robustness |
| 2.3 CORS | ❌ No | Config |
| 3.1–3.2 Frontend | ❌ No | Config |
| 4.1 Secure .env | ✅ Yes | Secrets |
| 4.2 Health check | ✅ Yes | Reliability |
| 4.3 Verify seed (poll) | ✅ Yes | User trust |
| 4.4–4.5 deploy | ❌ No | Cleanup, optional |
| 5.1–5.2 Docs | ❌ No | Documentation |

---

## Quality Checklist (Complete Before Finalizing Plan)

- [x] Did I spend 30+ minutes creating this plan?
- [x] Are all steps specific and actionable?
- [x] Does every step have a verification test with clear pass/fail criteria?
- [x] Did I identify which steps are critical and need code review?
- [x] For critical steps, did I include actual code snippets (not pseudocode)?
- [x] Are dependencies between steps clear and correct?
- [x] Did I break work into phases that each deliver user value?
- [x] Is the risk heatmap realistic based on complexity?
- [x] Are time estimates realistic?
- [x] Did I document architectural decisions at the top?
- [x] Are verification tests environment-agnostic (no hardcoded paths)?
- [x] Do verification tests explain HOW to observe results?
- [x] Did I include common failure scenarios and fixes?
- [x] Is the pre-flight checklist complete for each phase?
- [x] Are success criteria measurable and testable?
- [x] Step 4.3 uses poll (up to 50s, 5s intervals) per human feedback

---

⚠️ **IMPORTANT RULES**

1. Do NOT mark a step done until its verification test passes
2. If blocked, mark in progress and document
3. If 2x over estimate, pause and reassess
4. Update plan when reality diverges
