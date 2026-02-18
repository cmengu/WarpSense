#!/bin/bash
# Pre-merge check: if _merge/agent1_main.py exists, main.py MUST have sites router
# and GET /api/sites/health MUST return 200.
# Run from project root. Fails build when merge file exists but merge not applied.
# Requires: backend venv activated (or python3 with FastAPI/sqlalchemy installed).

set -e
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
cd "$ROOT"

if [ ! -f "_merge/agent1_main.py" ]; then
  echo "INFO: No _merge/agent1_main.py; skipping sites merge check."
  exit 0
fi

# Merge file exists — verify merge applied
if ! grep -q "sites_router" backend/main.py || ! grep -q "include_router(sites_router)" backend/main.py; then
  echo "ERROR: _merge/agent1_main.py exists but main.py does not include sites_router. Paste the merge snippet."
  exit 1
fi

# Verify route is reachable (not 404); stub/wrong prefix would still fail
# Patch check_db_connectivity so route check runs without real DB (lifespan would fail otherwise)
cd backend
python3 -c "
import unittest.mock
with unittest.mock.patch('main.check_db_connectivity', return_value=True):
    from main import app
    from fastapi.testclient import TestClient
    c = TestClient(app)
    r = c.get('/api/sites/health')
if r.status_code != 200:
    print('ERROR: GET /api/sites/health returned', r.status_code, '— merge may be applied but route unreachable')
    exit(1)
d = r.json()
if d.get('router') != 'sites':
    print('ERROR: Response router=', d.get('router'), 'expected sites')
    exit(1)
print('OK: sites router registered and reachable')
"
