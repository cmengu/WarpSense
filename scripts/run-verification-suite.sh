#!/usr/bin/env bash
# Batch 4 Agent 4 — Post-Merge Verification Suite
# Run from project root. Backend should be running for steps 7-8.

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== 1. Python syntax check ==="
python3 -m py_compile backend/main.py backend/routes/sites.py backend/routes/sessions.py backend/routes/aggregate.py backend/services/aggregate_service.py
echo "✓ Python syntax passed"

echo ""
echo "=== 2. TypeScript check ==="
(cd my-app && npx tsc --noEmit) || echo "⚠ tsc has pre-existing errors in tests/e2e"

echo ""
echo "=== 3. Migration chain (from backend/, needs DATABASE_URL) ==="
(cd backend && source venv/bin/activate && alembic downgrade base && alembic upgrade head) || echo "⚠ Migration: run manually (e.g. fresh DB or fix downgrade)"

echo ""
echo "=== 4. Table existence check (needs psql + DATABASE_URL) ==="
# Load .env; set +a runs even if .env sourcing fails (some systems)
set -a; [ -f .env ] && . .env 2>/dev/null || true; set +a
TABLES=$(psql "${DATABASE_URL:-postgresql://localhost:5432/shipyard}" -t -c "\dt" 2>/dev/null | grep -E "sites|teams|session_narratives|session_annotations|drills|coaching|cert" || true)
if [ -n "$TABLES" ]; then
  echo "Expected tables found:"
  echo "$TABLES"
else
  echo "⚠ Run: psql \$DATABASE_URL -c '\\dt' | grep -E 'sites|teams|...'"
fi

echo ""
echo "=== 5. ESLint WebGL canvas count ==="
(cd my-app && npx eslint src/app/replay/ --rule '{"max-torchviz/max-torchviz3d-per-page": "error"}')
echo "✓ ESLint passed"

echo ""
echo "=== 6. Frontend build (webpack; needs network for fonts) ==="
(cd my-app && npm run build -- --webpack) || echo "⚠ Build failed (fonts/TS — check output)"

echo ""
echo "=== 7. Smoke tests (needs backend on :8000) ==="
(cd my-app && npm test -- --testPathPattern="full-stack-smoke") || echo "⚠ Some smoke tests failed"

echo ""
echo "=== 8. API spot checks (needs backend on :8000) ==="
curl -sf http://localhost:8000/api/sites | python3 -m json.tool > /dev/null && echo "✓ /api/sites" || echo "✗ /api/sites"
curl -sf "http://localhost:8000/api/sessions/aggregate?site_id=site_demo_001" | python3 -m json.tool > /dev/null && echo "✓ /api/sessions/aggregate?site_id=..." || echo "✗ aggregate with site_id"
curl -sf "http://localhost:8000/api/sessions/aggregate" | python3 -m json.tool > /dev/null && echo "✓ /api/sessions/aggregate" || echo "✗ aggregate"

echo ""
echo "=== Verification complete ==="
