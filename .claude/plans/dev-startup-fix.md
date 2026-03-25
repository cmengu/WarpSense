# Plan: Reliable Dev Startup for Analysis Page

**Overall Progress:** `0%`

---

## TLDR

Two failure modes prevent clean `npm run dev` startup: (1) `start-all.sh` hard-exits if `backend/venv` is missing rather than creating it; (2) both `start-all.sh` and `package.json dev:backend` start uvicorn directly, bypassing `backend/start.sh` which is the only launcher that runs `alembic upgrade head` — so DB tables don't exist when lifespan fires `init_system.run()`, seeding silently fails, and the analysis page has no sessions. Fix: make `backend/start.sh` the single source of truth for backend startup (auto-create venv, always sync deps, run migrations, start server), then wire both launchers through it.

---

## Architecture Overview

**The problem this plan solves:**

- `start-all.sh` lines 18–23: checks `[ ! -d "backend/venv" ]` and calls `exit 1` instead of creating it.
- `start-all.sh` lines 26–31 and `package.json dev:backend`: both call uvicorn directly with `source venv/bin/activate && uvicorn ...`, skipping `alembic upgrade head`. If the DB schema doesn't exist, `init_system.run()` throws, the warning is swallowed, and no sessions are seeded.
- `backend/start.sh` lines 22–27: uses a sentinel file `venv/.installed` to skip `pip install`. If `requirements.txt` changes after setup, new deps are never installed.
- `backend/start.sh` line 9: uses `python` (may resolve to Python 2 or not be found); `setup.sh` correctly uses `python3`.

**What stays unchanged:**

- `backend/setup.sh` — untouched; still used for first-time environment creation.
- `backend/main.py`, `init_system.py`, all routes — no backend logic changes.
- `my-app/` — no frontend changes.
- `package.json` root-level scripts except `dev:backend`.

**What this plan changes:**

- `backend/start.sh` — becomes the single source of truth: venv auto-create with `python3`, always-quiet pip sync, migrations, then uvicorn with `--reload` and `ENV=development`.
- `start-all.sh` — removes the hard-exit venv check; delegates backend startup to `(cd backend && bash start.sh)` with a longer health-check wait for migration time.
- `package.json dev:backend` — delegates to `cd backend && bash start.sh` instead of manual venv activation.

**Critical decisions:**

| Decision | Alternative considered | Why rejected |
|----------|----------------------|--------------|
| Always run `pip install -r requirements.txt --quiet` | Keep sentinel file | Sentinel doesn't detect `requirements.txt` changes; `--quiet` makes it fast (~1s) when deps are current |
| Delegate `start-all.sh` to `bash start.sh` | Inline migrations in `start-all.sh` | `start.sh` is already the canonical backend runner; two code paths for the same sequence is the original bug |
| `python3` for venv creation | Keep `python` | `python` resolves to Python 2 on some macOS setups; `python3` is explicit |

**Known limitations:**

| Limitation | Why acceptable | Upgrade path |
|-----------|----------------|--------------|
| `pip install --quiet` adds ~1s to startup | Negligible vs. migration + ChromaDB init time (~10s total) | Pin deps with `pip-compile` for zero-overhead check |
| Health poll runs up to 30s on first run | Covers cold migration + ChromaDB init (~10–15s typical) | No upgrade needed — poll exits as soon as `/health` responds |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Run the following commands from the repo root. Show full output. Do not change anything.

(1) cat backend/start.sh
(2) cat start-all.sh
(3) grep -n "dev:backend" package.json
(4) ls backend/venv 2>/dev/null && echo "venv exists" || echo "venv missing"
(5) ls backend/.env 2>/dev/null && echo ".env exists" || echo ".env missing"
```

**Baseline Snapshot (agent fills during pre-flight):**
```
backend/start.sh sentinel check line: ____
start-all.sh venv check line:         ____
package.json dev:backend value:       ____
venv state:                           ____
.env state:                           ____
```

**Automated checks (all must pass before Step 1):**
- [ ] `grep -n "pip install -r requirements.txt" backend/start.sh` returns exactly 1 match — the pip install line inside the sentinel block we are replacing
- [ ] `grep -n "exit 1" start-all.sh` returns exactly 1 match — the hard-exit we are removing
- [ ] `grep -n "dev:backend" package.json` returns exactly 1 match

---

## Environment Matrix

| Step | Notes |
|------|-------|
| Steps 1–3 | Script/config changes only — no DB or dependency changes |

---

## Tasks

---

- [ ] 🟥 **Step 1: Fix `backend/start.sh` — auto-create venv with python3, always-quiet pip sync**

  **Step Architecture Thinking:**

  **Pattern applied:** Single source of truth. `start.sh` is the canonical backend runner. All callers (start-all.sh, package.json) delegate to it. Fix all startup deficiencies here once rather than in each caller.

  **Why this step exists here in the sequence:** Steps 2 and 3 both delegate to this file. It must be correct before being wired in.

  **Why this file is the right location:** It is the only script that sequences venv → deps → migrations → server. The bug is here; the fix belongs here.

  **Alternative approach considered and rejected:** Fixing venv creation in `start-all.sh` directly — creates a second code path for the same logic, reproducing the original fragmentation bug.

  **What breaks if this step deviates:** If `alembic upgrade head` is removed or moved after `uvicorn`, lifespan fires before tables exist and seeding silently fails.

  ---

  **Idempotent:** Yes — creating a venv that already exists is a no-op; `pip install --quiet` with satisfied deps exits in ~1s; `alembic upgrade head` with current schema exits immediately.

  **Pre-Read Gate:**
  - Run `grep -n "pip install -r requirements.txt" backend/start.sh` — must return exactly 1 match. If 0 → step already applied, skip. If 2+ → STOP.
  - Run `grep -c "alembic upgrade head" backend/start.sh` — must return 1. If 0 → STOP.

  **Self-Contained Rule:** Code block below is the complete replacement file.

  **No-Placeholder Rule:** No `<VALUE>` tokens.

  Replace `backend/start.sh` in full:

  ```bash
  #!/bin/bash
  # Start script for FastAPI backend.
  # Safe to call from any directory — cd into backend/ before invoking:
  #   cd backend && bash start.sh
  # ENV defaults to development; pass ENV=production to override.
  set -e

  # ── 1. Resolve script directory so paths work regardless of caller cwd ──────
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$SCRIPT_DIR"

  # ── 2. Create venv if missing ────────────────────────────────────────────────
  if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      python3 -m venv venv
  fi

  # ── 3. Activate venv ─────────────────────────────────────────────────────────
  source venv/bin/activate

  # ── 4. Sync dependencies (fast when already satisfied) ───────────────────────
  echo "Syncing dependencies..."
  pip install -r requirements.txt --quiet

  # ── 5. Require .env ──────────────────────────────────────────────────────────
  if [ ! -f ".env" ]; then
      echo "ERROR: backend/.env not found."
      echo "  Run: cp backend/.env.example backend/.env"
      echo "  Then edit .env and set DATABASE_URL."
      exit 1
  fi

  # ── 6. Run DB migrations (idempotent — skips if schema is current) ───────────
  echo "Running database migrations..."
  alembic upgrade head

  # ── 7. Start server ───────────────────────────────────────────────────────────
  export ENV="${ENV:-development}"
  echo "Starting FastAPI server (ENV=$ENV) on http://localhost:8000"
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```

  **What it does:** Resolves its own directory so it works when called from root (`cd backend && bash start.sh`) or from within backend. Creates venv with `python3` if absent. Always runs `pip install --quiet` to catch `requirements.txt` changes. Requires `.env` with a clear error. Runs migrations before starting uvicorn. Defaults `ENV=development`.

  **Why this approach:** `SCRIPT_DIR` + `cd "$SCRIPT_DIR"` is the standard pattern for making bash scripts location-independent. `pip install --quiet` with a warm cache takes ~1s and eliminates the stale-sentinel bug.

  **Assumptions:**
  - `python3` is available on `$PATH` (standard on macOS with Homebrew or Xcode tools).
  - `backend/.env` exists (user has run setup at least once; error message guides them if not).

  **Risks:**
  - `pip install --quiet` takes longer on first install (~60–120s) — mitigation: expected; only happens once per machine.
  - `alembic upgrade head` fails if `DATABASE_URL` in `.env` is wrong — mitigation: error is explicit, user sees it before uvicorn starts.

  **Git Checkpoint:**
  ```bash
  git add backend/start.sh
  git commit -m "fix(backend): start.sh auto-creates venv with python3, always-quiet pip sync, location-independent"
  ```

  **✓ Verification Test:**

  **Type:** Unit (script inspection)

  **Action:**
  ```bash
  grep -n "SCRIPT_DIR" backend/start.sh
  grep -n "python3 -m venv" backend/start.sh
  grep -n "pip install -r requirements.txt --quiet" backend/start.sh
  grep -n "alembic upgrade head" backend/start.sh
  grep -c "venv/.installed" backend/start.sh
  ```

  **Expected:**
  - `SCRIPT_DIR` line present
  - `python3 -m venv venv` line present
  - `pip install -r requirements.txt --quiet` line present
  - `alembic upgrade head` line present
  - `venv/.installed` count returns **0** (sentinel block fully removed)

  **Pass:** All four expected lines present; `venv/.installed` count is 0.

  **Fail:**
  - `venv/.installed` count non-zero → old file was not replaced → re-read `backend/start.sh` and confirm edit was saved

---

- [ ] 🟥 **Step 2: Update `start-all.sh` — remove hard-exit venv check, delegate backend to `start.sh`**

  **Step Architecture Thinking:**

  **Pattern applied:** Delegation. The script's only job is to orchestrate process lifecycle (kill ports, launch both servers, trap SIGINT). It should not re-implement startup logic that `start.sh` already owns.

  **Why this step exists here in the sequence:** Step 1 made `start.sh` correct. This step makes `start-all.sh` use it.

  **Why this file is the right location:** This is the file users invoke for local dev (`bash start-all.sh`). Its venv check is the one that hard-exits.

  **Alternative approach considered and rejected:** Keeping the venv check and calling `setup.sh` inline — would run pip twice per startup (once here, once in `start.sh`).

  **What breaks if this step deviates:** If the `sleep` is too short, the health check fires before migrations complete and prints "⚠️ Backend may still be starting" even on a healthy start.

  ---

  **Idempotent:** Yes — script replacement is idempotent.

  **Pre-Read Gate:**
  - Run `grep -n "exit 1" start-all.sh` — must return exactly 1 match (the venv check). If 0 → step already applied, skip.

  Replace `start-all.sh` in full:

  ```bash
  #!/bin/bash
  # Start script for both frontend and backend.
  # Run from the repo root: bash start-all.sh

  set -e

  echo "Starting WarpSense development servers..."
  echo ""

  # ── 1. Kill existing processes on dev ports ───────────────────────────────────
  echo "Cleaning up existing processes..."
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
  lsof -ti:3000 | xargs kill -9 2>/dev/null || true
  lsof -ti:3001 | xargs kill -9 2>/dev/null || true
  lsof -ti:3002 | xargs kill -9 2>/dev/null || true
  rm -f my-app/.next/lock my-app/.next/dev/lock 2>/dev/null || true
  sleep 1
  echo ""

  # ── 2. Start backend ──────────────────────────────────────────────────────────
  # Delegates entirely to backend/start.sh which handles:
  #   venv creation, pip sync, .env check, alembic migrations, uvicorn
  echo "Starting backend on http://localhost:8000..."
  (cd backend && bash start.sh) &
  BACKEND_PID=$!

  # Wait for migrations + ChromaDB init before health check (allow up to 30s)
  echo "Waiting for backend startup (migrations + ChromaDB init)..."
  for i in $(seq 1 30); do
      sleep 1
      if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
          echo "Backend is ready (${i}s)"
          break
      fi
      if [ "$i" -eq 30 ]; then
          echo "WARNING: Backend did not respond after 30s — check for errors above"
      fi
  done
  echo ""

  # ── 3. Start frontend ─────────────────────────────────────────────────────────
  echo "Starting frontend on http://localhost:3000..."
  (cd my-app && npm run dev) &
  FRONTEND_PID=$!

  echo ""
  echo "Both servers are starting!"
  echo "  Backend:  http://localhost:8000"
  echo "  Frontend: http://localhost:3000"
  echo ""
  echo "Press CTRL+C to stop both servers"

  # ── 4. Trap CTRL+C → kill both ────────────────────────────────────────────────
  # INT TERM EXIT: EXIT fires on set -e triggered exits too, preventing orphaned frontend.
  trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM EXIT
  wait
  ```

  **What it does:** Removes the hard-exit venv check. Delegates the entire backend startup to `backend/start.sh` (which handles venv, pip, migrations, uvicorn). Replaces the fixed `sleep 2` with a 30-second poll loop that exits as soon as `/health` responds.

  **Why this approach:** The poll loop gives accurate feedback — the log shows "Backend is ready (12s)" instead of silently waiting. 30s ceiling covers cold-start (venv creation + pip install takes up to 2 minutes; but that should only happen on first run, and on subsequent runs migration + ChromaDB init is ~8–12s).

  **Assumptions:**
  - `curl` is available (standard on macOS).
  - `/health` is a valid endpoint on the backend (confirmed: `main.py` registers it).

  **Risks:**
  - First-run venv creation takes up to 2 minutes — the 30s poll will print the WARNING message, but the backend process continues in the background. Mitigation: run `cd backend && bash setup.sh` once before the first `bash start-all.sh` on a new machine.

  **Git Checkpoint:**
  ```bash
  git add start-all.sh
  git commit -m "fix(start-all): remove hard-exit venv check, delegate to backend/start.sh, poll-wait for health"
  ```

  **✓ Verification Test:**

  **Type:** Unit (script inspection)

  **Action:**
  ```bash
  grep -n "exit 1" start-all.sh
  grep -n "bash start.sh" start-all.sh
  grep -n "alembic" start-all.sh
  grep -n "curl -sf" start-all.sh
  ```

  **Expected:**
  - `exit 1` returns **0 matches** (hard-exit removed)
  - `bash start.sh` returns 1 match
  - `alembic` returns **0 matches** (not duplicated here; lives in `start.sh`)
  - `curl -sf` returns 1 match (poll loop)

  **Pass:** Hard-exit removed; delegation to `start.sh` present; poll loop present.

  **Fail:**
  - `exit 1` still present → old file not replaced → re-read and confirm

---

- [ ] 🟥 **Step 3: Update `package.json dev:backend` — delegate to `backend/start.sh`**

  **Step Architecture Thinking:**

  **Pattern applied:** Delegation (same as Step 2). `package.json` scripts are entry points, not startup-logic containers.

  **Why this step exists here in the sequence:** `npm run dev` is the user's primary entry point. Without this fix, `npm run dev` still bypasses migrations even after Steps 1–2.

  **Why this file is the right location:** `package.json dev:backend` is the script invoked by `npm run dev → dev:all → dev:backend`. The manual `source venv/bin/activate && uvicorn` here is the remaining bypass path.

  **Alternative approach considered and rejected:** Keeping `source venv/bin/activate` in package.json and adding `alembic upgrade head` before uvicorn inline — `&&`-chaining 5 commands in a json string is brittle and duplicates `start.sh`.

  **What breaks if this step deviates:** If `ENV=development` is not passed, dev-only routes (`/api/dev/seed-mock-sessions`) are not registered and the seeding endpoint is unreachable.

  ---

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - Run `grep -n "dev:backend" package.json` — must return exactly 1 match containing `source venv/bin/activate`. If already contains `bash start.sh` → step already applied, skip.

  **Self-Contained Rule:** Edit is a single-line replacement.

  Edit `package.json`. Replace the `dev:backend` value:

  **Old value:**
  ```
  "dev:backend": "cd backend && source venv/bin/activate && ENV=development python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000",
  ```

  **New value:**
  ```
  "dev:backend": "cd backend && ENV=development bash start.sh",
  ```

  **What it does:** `cd backend` sets the working directory so `start.sh`'s `SCRIPT_DIR` resolves correctly. `ENV=development` is set in the environment before calling `bash start.sh`, making it available to the script via `${ENV:-development}`. The script handles everything from venv to uvicorn.

  **Why this approach:** Single-line, readable, and all startup logic lives in one place.

  **Assumptions:**
  - `bash` is available (macOS default: yes).
  - `ENV=development bash start.sh` passes the env var into the bash subprocess (standard POSIX `VAR=val command` syntax).

  **Risks:**
  - `npm run dev` now runs migrations before starting uvicorn, adding ~2s to startup on an already-migrated DB — mitigation: acceptable; `alembic upgrade head` exits immediately when schema is current.

  **Git Checkpoint:**
  ```bash
  git add package.json
  git commit -m "fix(package.json): dev:backend delegates to backend/start.sh (venv+deps+migrations+server)"
  ```

  **✓ Verification Test:**

  **Type:** Integration

  **Action:**
  ```bash
  grep "dev:backend" package.json
  ```

  **Expected:**
  ```
  "dev:backend": "cd backend && ENV=development bash start.sh",
  ```

  **Pass:** Value contains `bash start.sh` and does not contain `source venv/bin/activate`.

  **Fail:**
  - Old value still present → edit was not saved → re-read `package.json` and confirm

---

## End-to-End Verification

After all three steps, run:

```bash
bash start-all.sh
```

**Expected sequence in terminal output:**
1. `Cleaning up existing processes...` — ports cleared
2. `Starting backend on http://localhost:8000...`
3. `Syncing dependencies...` — pip runs quietly
4. `Running database migrations...` — alembic prints revision
5. `Starting FastAPI server (ENV=development) on http://localhost:8000`
6. `Backend is ready (Ns)` — health check succeeds
7. `Starting frontend on http://localhost:3000...`
8. Browser → `http://localhost:3000/analysis` → session list shows 10 aluminium sessions

**Post-startup session count check (run after `Backend is ready` prints):**
```bash
curl -s http://localhost:8000/api/mock-sessions | python3 -c \
  "import sys,json; d=json.load(sys.stdin); assert len(d)==10, f'Expected 10 sessions, got {len(d)}'; print(f'OK: {len(d)} sessions')"
```
Pass: prints `OK: 10 sessions`. Fail: assertion error → seeding did not complete → see "Session list empty" row below.

**Fail diagnostics:**

| Symptom | Cause | Check |
|---------|-------|-------|
| `ERROR: backend/.env not found` | `.env` not created | `cp backend/.env.example backend/.env` then edit `DATABASE_URL` |
| `alembic upgrade head` fails with `OperationalError` | PostgreSQL not running or `DATABASE_URL` wrong | Confirm Postgres is up; check `backend/.env` `DATABASE_URL` value |
| Poll runs to 30s WARNING, `/health` returns 503 | `/health` checks DB connectivity and returns 503 when DB is unreachable — this is expected behavior, not a uvicorn failure | Check `DATABASE_URL` in `backend/.env`; confirm PostgreSQL is running |
| `Backend is ready` never prints (30s timeout) | ChromaDB or LLM key issue during lifespan | Check backend terminal for traceback; look at `GROQ_API_KEY` in `.env` |
| Session list empty | Seeding failed silently | POST `http://localhost:8000/api/dev/seed-mock-sessions` manually |
| `npm run dev` still uses old uvicorn command | `package.json` edit not saved | `grep dev:backend package.json` — must show `bash start.sh` |

---

## Regression Guard

| System | Pre-change behaviour | Post-change verification |
|--------|---------------------|--------------------------|
| `npm run dev` | Starts uvicorn directly (skips migrations) | Now runs `start.sh` → migrations → uvicorn; verify backend starts on port 8000 |
| `bash start-all.sh` | Exits if venv missing | Now auto-creates venv via `start.sh`; verify it starts without `exit 1` |
| `backend/start.sh` | Skips pip if sentinel present | Now always runs `pip install --quiet`; verify with `grep "pip install" backend/start.sh` — must show `--quiet` with no surrounding sentinel `if` block |

---

## Rollback

```bash
git revert HEAD~3..HEAD   # reverts all three commits
```

Or per-step:
```bash
git revert <commit-hash-step-3>   # restore package.json
git revert <commit-hash-step-2>   # restore start-all.sh
git revert <commit-hash-step-1>   # restore backend/start.sh
```
