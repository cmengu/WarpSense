
Here’s what’s in place and what you should run locally.

## Agent 3 Batch 1 — AI Narrative Engine

### Files and status

| Component | Status |
|-----------|--------|
| **Migration 006** | Done — `session_narratives` table, index, `upgrade`/`downgrade` |
| **`backend/models/narrative.py`** | Done |
| **`backend/schemas/narrative.py`** | Done |
| **`backend/services/narrative_service.py`** | Done — Anthropic, caching, score-based invalidation |
| **`backend/routes/narratives.py`** | Done |
| **`my-app/src/types/narrative.ts`** | Done |
| **`my-app/src/lib/narrative-api.ts`** | Done — uses `buildUrl`/`apiFetch` from `api.ts` |
| **`my-app/src/components/welding/NarrativePanel.tsx`** | Done |
| **`backend/main.py`** | Narratives router already included |
| **`_merge/agent3_main.py`** | Present (merge instructions) |
| **`_merge/agent3_api.ts`** | Present (merge instructions) |

### Changes made

1. **`anthropic` in `requirements.txt`** — added `anthropic>=0.18.0` for narrative generation.
2. **`test_narrative_routes.py`** — new tests for:
   - `GET` 404 when no narrative exists
   - `POST` 404 when session is missing
   - `POST` 503 when `ANTHROPIC_API_KEY` is not set
   - `POST` 200 and response shape when service is mocked

### Verification checklist (run locally)

```bash
# 1. Backend: Install deps, run migrations, start server
cd backend
pip install anthropic  # or pip install -r requirements.txt
alembic upgrade head
# In another terminal: uvicorn main:app --reload

# 2. Seed mock sessions (creates sess_novice_001)
curl -X POST http://localhost:8000/api/dev/seed-mock-sessions

# 3. POST narrative — should return 200 with narrative_text
curl -X POST http://localhost:8000/api/sessions/sess_novice_001/narrative \
  -H "Content-Type: application/json" -d '{}'

# 4. Second call — should return cached: true
curl -X POST http://localhost:8000/api/sessions/sess_novice_001/narrative \
  -H "Content-Type: application/json" -d '{}'

# 5. Missing API key — should return 503 (run with unset key)
ANTHROPIC_API_KEY= curl -X POST http://localhost:8000/api/sessions/sess_novice_001/narrative \
  -H "Content-Type: application/json" -d '{}'

# 6. Frontend build
cd my-app && npm run build

# 7. Run narrative tests
cd backend && python -m pytest tests/test_narrative_routes.py -v
```

`NarrativePanel` is used on the welder detail page (`my-app/src/app/seagull/welder/[id]/page.tsx`) and shows loading skeleton → narrative text, with a “Regenerate” button.
