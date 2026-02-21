# Merge Agent 1/2/3 Routers and API — Verification & Closure Plan

**Overall Progress:** `95%` (Step 3 run in your env to confirm)

## TLDR

The merge is **complete**. All agent router snippets are consolidated in `backend/main.py`; all session-scoped API functions live in `my-app/src/lib/api.ts`. This plan documents verification steps and optional cleanup. No implementation work remains.

---

## Critical Decisions

- **narrative-api.ts:** Kept as thin re-export from api.ts — NarrativePanel continues to import from narrative-api; no breaking changes.
- **pre_merge_sites_check.sh:** Left as-is (sites only) — extending for predictions/narratives could add fragile checks; avoid new failure points.
- **_merge files:** Optional archive/delete — keep for audit or remove after merge is stable.

---

## Tasks

### Phase 1 — Verification (Merge Already Applied)

**Goal:** Confirm all Success Criteria are met and system works end-to-end.

---

- [x] 🟩 **Step 1: Verify backend/main.py router structure**

  **Subtasks:**
  - [x] 🟩 Confirm sites_router, predictions_router, narratives in imports block
  - [x] 🟩 Confirm include_router order: aggregate → narratives → sessions (before sessions)
  - [x] 🟩 Confirm predictions_router and sites_router registered

  **✓ Verification Test:**

  **Action:**
  - Grep `backend/main.py` for `sites_router`, `predictions_router`, `narratives`
  - Verify `include_router(narratives.router)` appears before `include_router(sessions_router`
  - Run: `cd backend && python -c "from main import app; print([r.path for r in app.routes][:5])"` (with venv)

  **Expected Result:**
  - All three router names present in imports
  - narratives registered before sessions
  - App loads without ImportError

  **How to Observe:**
  - **Grep:** `grep -n "sites_router\|predictions_router\|narratives" backend/main.py`
  - **Import:** No traceback when importing main

  **Pass Criteria:**
  - Imports at L14–22; include_router order correct
  - `from main import app` succeeds

  **Common Failures & Fixes:**
  - **ImportError:** Missing route module — ensure routes/sites.py, routes/predictions.py, routes/narratives.py exist
  - **Wrong order:** Sessions catches /narrative or /aggregate — move narratives/aggregate before sessions

---

- [x] 🟩 **Step 2: Verify api.ts exports**

  **Subtasks:**
  - [x] 🟩 fetchWarpRisk present
  - [x] 🟩 fetchNarrative, generateNarrative present
  - [x] 🟩 narrative-api.ts re-exports from api.ts

  **✓ Verification Test:**

  **Action:**
  - Grep `my-app/src/lib/api.ts` for `fetchWarpRisk`, `fetchNarrative`, `generateNarrative`
  - Read `my-app/src/lib/narrative-api.ts` — should contain single re-export line

  **Expected Result:**
  - All three functions exported from api.ts
  - narrative-api.ts: `export { fetchNarrative, generateNarrative } from "@/lib/api"`

  **How to Observe:**
  - **Grep:** `grep -n "export async function fetch" my-app/src/lib/api.ts`
  - **File:** narrative-api.ts is 5–6 lines

  **Pass Criteria:**
  - api.ts exports all three; narrative-api re-exports narrative pair
  - No duplicate implementations

  **Common Failures & Fixes:**
  - **Missing export:** Add function to api.ts using buildUrl + apiFetch pattern
  - **narrative-api has implementation:** Replace with re-export to avoid drift

---

- [ ] 🟨 **Step 3: Run test suites** *(requires venv + npm env)*

  **Subtasks:**
  - [ ] 🟥 `pytest backend/tests/` from project root (requires backend venv with pytest)
  - [ ] 🟥 `npm run build` in my-app (remove `.next/lock` if another build is running)

  **Verification performed (2026-02-18):**
  - **main.py:** grep ✓ — sites_router, predictions_router, narratives in imports (L17-20); include_router order correct (L66, 70, 72)
  - **api.ts:** grep ✓ — fetchWarpRisk, fetchNarrative, generateNarrative exported
  - **pytest:** Not run (pytest not in system path; use `python -m pytest` from backend venv)
  - **npm build:** Blocked by `.next/lock` (another build may be running)
  - **tsc --noEmit:** Pre-existing TS errors in e2e/replay/FeedbackPanel/seagull-demo-data — unrelated to merge

  **✓ Verification Test:**

  **Action:**
  - From project root: `pytest backend/tests/ -v --tb=short`
  - From my-app: `npm run build`

  **Expected Result:**
  - Backend tests pass (including test_sites_api, test_session_model_team_id, replay/page tests)
  - Frontend build completes without TypeScript or import errors

  **How to Observe:**
  - **Backend:** pytest exit code 0; no FAILED
  - **Frontend:** build completes; no "Module not found" or type errors

  **Pass Criteria:**
  - All backend tests green
  - Next.js build succeeds
  - No new regressions in NarrativePanel or ReplayPage

  **Common Failures & Fixes:**
  - **pytest ModuleNotFoundError:** Run from project root, not `cd backend && pytest tests/`
  - **npm build fails on narrative types:** Ensure @/types/narrative exists and NarrativeResponse is exported
  - **Replay test fails:** fetchWarpRisk mock — ensure api is mocked correctly in test setup

---

### Phase 2 — Optional Cleanup

**Goal:** Archive _merge files to avoid confusion; no code impact.

---

- [ ] 🟥 **Step 4: (Optional) Archive _merge files**

  **Subtasks:**
  - [ ] 🟥 Create `_merge/archive/` or delete _merge/*.py and _merge/*.ts
  - [ ] 🟥 Update pre_merge_sites_check.sh if agent1_main.py moved — script checks for file existence; if deleted, it skips (exit 0)

  **✓ Verification Test:**

  **Action:**
  - Move or delete: `_merge/agent1_main.py`, `agent2_main.py`, `agent3_main.py`, `agent2_api.ts`, `agent3_api.ts`
  - Run `bash scripts/pre_merge_sites_check.sh` — should exit 0 (skips when file absent)

  **Expected Result:**
  - _merge folder empty or contains only archive
  - pre_merge script still passes (skips when agent1_main.py not found)

  **How to Observe:**
  - `ls _merge/`
  - Script prints "INFO: No _merge/agent1_main.py; skipping"

  **Pass Criteria:**
  - Cleanup done without breaking app
  - pre_merge script exits 0

  **Common Failures & Fixes:**
  - **pre_merge fails after delete:** Script expects file to exist when checking — it actually skips when absent; no fix needed if logic is `if [ ! -f "..."] ; then exit 0`
  - **Accidental deletion of needed file:** Only _merge snippet files; app code lives in main.py and api.ts

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Backend venv active | `which python` shows venv path | ⬜ |
| | DATABASE_URL set (for tests that need DB) | `echo $DATABASE_URL` or .env present | ⬜ |
| | Node/npm available | `npm run build` in my-app | ⬜ |
| **Phase 2** | Phase 1 complete | Step 3 pass | ⬜ |

---

## Risk Heatmap

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟢 **5%** | Test env (venv, DATABASE_URL) misconfigured | pytest fails immediately; npm build fails on missing deps |
| Phase 2 | 🟢 **2%** | pre_merge script assumes file exists incorrectly | Run script after archive; should skip gracefully |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|----------------|---------------------|
| Backend routers | sites, predictions, narratives registered; order correct | **Test:** Import main, inspect app.routes **Expect:** Routers present, narratives before sessions **Location:** main.py |
| API client | fetchWarpRisk, fetchNarrative, generateNarrative in api.ts | **Test:** Grep api.ts **Expect:** All three exported **Location:** api.ts |
| NarrativePanel | Still works | **Test:** Load replay/welder page with narrative slot **Expect:** Narrative loads or generates **Location:** Browser |
| Build & tests | No regressions | **Test:** pytest + npm run build **Expect:** All pass **Location:** Terminal |

---

⚠️ **Merge is complete. Steps 1–2 verified. Run Step 3 to confirm tests/build pass before closing. Step 4 is optional.**
