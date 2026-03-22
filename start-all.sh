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
