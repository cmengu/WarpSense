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
