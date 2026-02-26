# Feature Implementation Plan: Compare Page Alert Feed

**Overall Progress:** `0%`

## TLDR

Add `GET /api/sessions/{session_id}/alerts` that runs stored frames through `AlertEngine` and returns pre-computed alerts. On the compare page: fetch alerts in parallel with sessions, show alert count summary above a two-column feed, clickable cards that seek and pause, full-column critical highlight. Add "Expert vs Novice" button on compare landing for self-serve demo. No changes to `AlertEngine` or `alert_models.py`.

---

## Critical Decisions

- **Backend alerts endpoint:** New route in `sessions.py`; 2000-frame cap; reuse `_ns_asymmetry_from_frame` logic inline (cannot import from scripts); load frames from DB via `FrameModel`, convert to `FrameInput`, run `AlertEngine.push_frame`, return `{ alerts: [...] }`.
- **Frontend structure:** Inline `AlertPayload` type and `AlertFeed` UI in compare page; no new component file unless it exceeds ~80 lines.
- **Expert vs Novice button:** Single `<Link>` on compare landing; href `/compare/sess_expert_001/sess_novice_001`.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| API base path for alerts | `/api/sessions/{id}/alerts` | codebase (sessions router uses prefix `/api`) | Step 2 | ✅ |
| Mock session IDs | `sess_expert_001`, `sess_novice_001` | backend/routes/dev.py, backend/data/mock_sessions.py | Step 4 | ✅ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping, output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read backend/routes/sessions.py in full. Capture:
(1) Exact signature of get_session (line range)
(2) Line number where @router.get("/sessions/{session_id}/score") appears
(3) Imports at top of file
(4) Run: ls backend/config/alert_thresholds.json  — file must exist or endpoint will 500 silently
(5) Run: cd backend && python -m pytest -q 2>/dev/null | tail -3  (record passing count)
(6) Run: find my-app/src/app -name "page.tsx" | grep compare
    Show full output. Must return exactly 2 paths: compare landing + compare inner.
    Record the shorter path as COMPARE_LANDING (landing = form page), the longer as COMPARE_INNER (inner = [sessionIdA]/[sessionIdB] page).
    Typical: my-app/src/app/compare/page.tsx (landing) and my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx (inner).
    If under (app): my-app/src/app/(app)/compare/... — use whichever find returns. Do not assume.
(7) Run: wc -l backend/routes/sessions.py my-app/src/lib/api.ts and wc -l for each compare path from (6)
    Use the exact paths from (6). For paths with brackets, quote them: wc -l "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"

Do not change anything. Show full output.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count sessions.py: ____
COMPARE_LANDING (from find): my-app/src/app/________________
COMPARE_INNER (from find): my-app/src/app/________________
Line count compare landing: ____
Line count compare inner: ____
Line count api.ts: ____
```
**Critical:** Steps 3 and 4 use COMPARE_LANDING and COMPARE_INNER from this snapshot. If find returns different paths (e.g. under (app)/), use those—do not assume compare/ at app root.

**Pre-flight checks:**
- [ ] Existing tests pass. Document test count: `____`
- [ ] `backend/config/alert_thresholds.json` exists (ls confirms; if missing, endpoint 500s and agent may invent incorrect fixes)
- [ ] `find ... | grep compare` returned exactly 2 paths. Record both; use them verbatim in Steps 3 and 4.
- [ ] `get_session` exists and accepts `session_id`, `include_thermal`, `time_range_start`, `time_range_end`, `limit`, `offset`, `stream`, `db`
- [ ] `FrameModel` has `frame_data` (JSON) and `timestamp_ms`
- [ ] `realtime.alert_engine.AlertEngine` and `realtime.alert_models.FrameInput`, `AlertPayload` exist

---

## Steps Analysis

- Step 1 (Backend alerts endpoint) — Critical (new API) — full code review — Idempotent: Yes
- Step 2 (api.ts fetchSessionAlerts) — Critical (API contract) — full code review — Idempotent: Yes
- Step 3 (Expert vs Novice button) — Non-critical — verification only — Idempotent: Yes
- Step 4 (Compare page: fetch + AlertFeed) — Critical (state, UI) — full code review — Idempotent: Yes

---

## Tasks

### Phase 1 — Backend

---

- [ ] 🟥 **Step 1: Add GET /api/sessions/{session_id}/alerts** — *Critical: new API endpoint*

  **Idempotent:** Yes — repeated calls return same result for same session.

  **Context:** Compare page needs pre-computed alerts. AlertEngine exists; we add a route that loads frames from DB, runs them through AlertEngine, returns JSON.

  **Pre-Read Gate:**
  - `grep -n "def get_session" backend/routes/sessions.py` → must return 1 match
  - `grep -n "FrameModel" backend/routes/sessions.py` → must exist
  - `grep -n "AlertEngine" backend/routes/sessions.py` → must return 0 (we add it)
  - `grep -n "from realtime" backend/routes/sessions.py` → must return 0 (we add it)

  **Anchor Uniqueness Check:**
  - Insert new handler after `@router.get("/sessions/{session_id}/score")` (around line 300). Add before `@router.post("/sessions/{session_id}/frames")` (around line 382).
  - Target: add new `@router.get("/sessions/{session_id}/alerts")` function.

  **Self-Contained Rule:** Code block is complete. No placeholder tokens.

  ```python
  # Add to backend/routes/sessions.py

  # At top, add imports (after existing imports, before router):
  from pathlib import Path

  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import AlertPayload, FrameInput

  # Add helper (inline, cannot import from scripts) — place after get_db(), before create_session:
  def _ns_asymmetry_from_frame_data(frame_data: dict) -> float:
      """North minus south at 10mm. 0 if no thermal. Mirrors simulate_realtime._ns_asymmetry_from_frame."""
      snapshots = frame_data.get("thermal_snapshots") or []
      if not snapshots:
          return 0.0
      snap = snapshots[0]
      readings = snap.get("readings") or []
      north = next((r["temp_celsius"] for r in readings if r.get("direction") == "north"), None)
      south = next((r["temp_celsius"] for r in readings if r.get("direction") == "south"), None)
      if north is None or south is None:
          return 0.0
      return float(north) - float(south)


  @router.get("/sessions/{session_id}/alerts")
  async def get_session_alerts(
      session_id: str,
      db: OrmSession = Depends(get_db),
  ):
      """
      Run session frames through AlertEngine, return pre-computed alerts.
      Caps at 2000 frames (same as compare page).
      """
      session_model = db.query(SessionModel).filter_by(session_id=session_id).first()
      if not session_model:
          raise HTTPException(status_code=404, detail="Session not found")

      frames_query = (
          db.query(FrameModel)
          .filter_by(session_id=session_id)
          .order_by(FrameModel.timestamp_ms.asc())
          .limit(2000)
      )
      frame_models = frames_query.all()

      config_path = Path(__file__).resolve().parent.parent / "config" / "alert_thresholds.json"
      engine = AlertEngine(str(config_path))
      alerts: list[dict] = []

      for i, fm in enumerate(frame_models):
          fd = dict(fm.frame_data)
          ns = _ns_asymmetry_from_frame_data(fd)
          ts_ms = fd.get("timestamp_ms")
          if ts_ms is None:
              ts_ms = fm.timestamp_ms
          fin = FrameInput(
              frame_index=i,
              timestamp_ms=float(ts_ms),
              travel_angle_degrees=fd.get("travel_angle_degrees"),
              travel_speed_mm_per_min=fd.get("travel_speed_mm_per_min"),
              ns_asymmetry=ns,
          )
          alert = engine.push_frame(fin)
          if alert:
              alerts.append(alert.model_dump())

      return {"alerts": alerts}
  ```

  **What it does:** Loads up to 2000 frames, converts each to FrameInput, runs AlertEngine, returns `{ alerts: AlertPayload[] }`.

  **Assumptions:**
  - `backend/config/alert_thresholds.json` exists (Path resolves from routes/sessions.py → backend/)
  - `FrameModel.frame_data` contains keys: `thermal_snapshots`, `travel_angle_degrees`, `travel_speed_mm_per_min`, `timestamp_ms`
  - Sessions router has prefix `/api` in main.py

  **Risks:**
  - Config path wrong → AlertEngine raises FileNotFoundError → verify path in pre-flight
  - frame_data missing keys → use .get() with None; AlertEngine handles null

  **Git Checkpoint:**
  ```bash
  git add backend/routes/sessions.py
  git commit -m "feat: add GET /api/sessions/{session_id}/alerts endpoint"
  ```

  **Subtasks:**
  - [ ] 🟥 Add imports for Path, AlertEngine, FrameInput, AlertPayload (no copy—SQLAlchemy frame_data is plain dict)
  - [ ] 🟥 Add _ns_asymmetry_from_frame_data helper
  - [ ] 🟥 Add get_session_alerts handler

  **✓ Verification Test:**

  **Type:** Integration
  **Action:** `curl -s http://localhost:8000/api/sessions/sess_novice_001/alerts` (requires backend running and seed)
  **Expected:** JSON with top-level key `alerts` (array). For seeded novice session: `alerts` length > 0 AND `alerts` length < frame count (e.g. well under 2000).
  **Observe:** `jq '.alerts | length'` and `curl -s .../sess_novice_001 | jq '.frame_count'`. Alert count must be less than frame count—if suppression is broken, every frame fires and count ≈ frame count, masking the bug.
  **Pass:** Status 200, `alerts` is array, novice has > 0 alerts, alert count < frame count
  **Fail:**
  - 404 → session not found; run `curl -X POST http://localhost:8000/api/dev/seed-mock-sessions`
  - 500 → check config path, frame_data shape; inspect traceback
  - alert count ≈ frame count → suppression broken, check AlertEngine time-based suppression

---

### Phase 2 — Frontend API

---

- [ ] 🟥 **Step 2: Add fetchSessionAlerts in api.ts** — *Critical: API contract*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "export async function fetchSession" my-app/src/lib/api.ts` → 1 match
  - `grep -n "buildUrl" my-app/src/lib/api.ts` → exists
  - `grep -n "fetchSessionAlerts" my-app/src/lib/api.ts` → 0 matches (we add it)

  **Anchor Uniqueness Check:**
  - Insert after `fetchSession` (ends ~line 270). Next function is `fetchScore`. Add `fetchSessionAlerts` between them.

  ```typescript
  // Add to my-app/src/lib/api.ts after fetchSession, before fetchScore

  /**
   * Pre-computed alert payload from AlertEngine.
   */
  export interface AlertPayload {
    frame_index: number;
    rule_triggered: string;
    severity: string;
    message: string;
    correction: string;
    timestamp_ms: number;
  }

  /**
   * Response from GET /api/sessions/{session_id}/alerts.
   */
  export interface SessionAlertsResponse {
    alerts: AlertPayload[];
  }

  /**
   * Fetch pre-computed alerts for a session.
   * Backend runs frames through AlertEngine; returns alerts for timeline display.
   */
  export async function fetchSessionAlerts(
    sessionId: string
  ): Promise<SessionAlertsResponse> {
    const url = buildUrl(`/api/sessions/${encodeURIComponent(sessionId)}/alerts`);
    return apiFetch<SessionAlertsResponse>(url);
  }
  ```

  **What it does:** Mirrors backend response; used by compare page.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/lib/api.ts
  git commit -m "feat: add fetchSessionAlerts and AlertPayload types"
  ```

  **Subtasks:**
  - [ ] 🟥 Add AlertPayload and SessionAlertsResponse types
  - [ ] 🟥 Add fetchSessionAlerts function

  **✓ Verification Test:**

  **Type:** Unit (with mock) or Integration
  **Action:** In test or browser console: `fetch('http://localhost:8000/api/sessions/sess_novice_001/alerts').then(r=>r.json()).then(d=>console.log(d.alerts?.length))`
  **Expected:** Number > 0 for seeded novice session.
  **Pass:** API returns `{ alerts: [...] }`.
  **Fail:** 404/500 → backend not running or not seeded.

---

### Phase 3 — Compare Landing: Expert vs Novice Button

---

- [ ] 🟥 **Step 3: Add Expert vs Novice button on compare landing** — *Non-critical*

  **Idempotent:** Yes.

  **File:** Use COMPARE_LANDING from pre-flight Baseline Snapshot (e.g. `my-app/src/app/compare/page.tsx`). Do not assume path—agent often hallucinates `(app)/compare/` when the actual path is `compare/` at app root.

  **Pre-Read Gate:**
  - `grep -n "Compare two sessions" <COMPARE_LANDING>` → 1 match (substitute path from pre-flight)
  - `grep -n "Expert vs Novice" <COMPARE_LANDING>` → 0 matches

  **Anchor Uniqueness Check:**
  - Insert after `<p className="text-sm text-zinc-600...">Enter two session IDs...</p>` (around line 40), before `<form`.

  ```tsx
  // Add in <COMPARE_LANDING> inside the main div, after the description paragraph, before <form>

  <Link
    href="/compare/sess_expert_001/sess_novice_001"
    className="mb-6 inline-block px-4 py-3 rounded-md bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
  >
    Expert vs Novice — Quick demo
  </Link>
  ```

  **What it does:** One-click navigation to seeded expert vs novice comparison.

  **Git Checkpoint:**
  ```bash
  git add <COMPARE_LANDING>
  git commit -m "feat: add Expert vs Novice quick demo button on compare landing"
  ```

  **Subtasks:**
  - [ ] 🟥 Add Link with href /compare/sess_expert_001/sess_novice_001

  **✓ Verification Test:**

  **Type:** E2E / Manual
  **Action:** Open /compare, click "Expert vs Novice — Quick demo"
  **Expected:** Navigate to /compare/sess_expert_001/sess_novice_001
  **Pass:** URL changes, sessions load (if seeded).
  **Fail:** 404 on compare page → routing issue; sessions fail to load → seed required.

---

### Phase 4 — Compare Page: Alerts Fetch + AlertFeed UI

---

- [ ] 🟥 **Step 4: Compare page — fetch alerts, AlertFeed, count summary, clickable cards, critical highlight** — *Critical*

  **Idempotent:** Yes.

  **File:** Use COMPARE_INNER from pre-flight Baseline Snapshot (e.g. `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`). Do not assume path—agent often hallucinates `(app)/compare/` when the actual path is `compare/` at app root.

  **Pre-Read Gate:**
  - `grep -n "fetchSession(sessionIdA" <COMPARE_INNER>` → 1 match (substitute path from pre-flight)
  - `grep -n "setCurrentTimestamp" <COMPARE_INNER>` → exists
  - `grep -n "setIsPlaying" <COMPARE_INNER>` → exists
  - `grep -n "grid grid-cols-1 md:grid-cols-3" <COMPARE_INNER>` → 1 match (heatmap grid)

  **Anchor Uniqueness Check:**
  - Load logic: `const [dataA, dataB] = await Promise.all([...])` — add alert fetches with error isolation (Promise.allSettled or per-fetch try/catch; do not mix in same Promise.all without isolation)
  - Alert feed: insert new section after heatmap grid `</div>`, before closing `</div>` of max-w-full mx-auto

  **Self-Contained Rule:** All changes in one step. No placeholders.

  **Implementation outline (apply as edits):**

  4a. Add state and fetch:
  - `const [alertsA, setAlertsA] = useState<AlertPayload[]>([]);`
  - `const [alertsB, setAlertsB] = useState<AlertPayload[]>([]);`
  - `const [alertsErrorA, setAlertsErrorA] = useState<string | null>(null);`
  - `const [alertsErrorB, setAlertsErrorB] = useState<string | null>(null);`
  - **Error isolation:** Do NOT wrap session + alert fetches in one Promise.all with a single try/catch—one failed alert fetch would kill the whole page load. Use either: (1) run session fetches in `Promise.all([fetchSession(A), fetchSession(B)])` and alert fetches in `Promise.allSettled([fetchSessionAlerts(A), fetchSessionAlerts(B)])` and handle each result, or (2) run all four in Promise.all but wrap each `fetchSessionAlerts` call in its own try/catch so a rejection only affects that column.
  - On success: `setAlertsA(res.alerts)`, `setAlertsErrorA(null)`. On error: `console.warn` the error (do not import from @/lib/logger—use console.warn only), `setAlertsErrorA("Alerts unavailable")`, `setAlertsA([])`. Same for B.
  - Import `fetchSessionAlerts`, `type AlertPayload` from `@/lib/api`

  4b. Compute visible alerts with useMemo:
  - `const visibleAlertsA = useMemo(() => alertsA.filter(a => a.timestamp_ms <= (currentTimestamp ?? firstTimestamp ?? 0)).sort((a,b)=>b.timestamp_ms-a.timestamp_ms), [alertsA, currentTimestamp, firstTimestamp]);`
  - `const visibleAlertsB = useMemo(() => alertsB.filter(a => a.timestamp_ms <= (currentTimestamp ?? firstTimestamp ?? 0)).sort((a,b)=>b.timestamp_ms-a.timestamp_ms), [alertsB, currentTimestamp, firstTimestamp]);`
  - Dependency array must include `[alertsA, alertsB, currentTimestamp, firstTimestamp]` (split per column).

  4c. Alert count summary (above feed):
  - New section before AlertFeed: two columns, "Session A: {visibleAlertsA.length} alerts" | "Session B: {visibleAlertsB.length} alerts". When `alertsErrorA` is set, show "Session A: Alerts unavailable" (styled as error text, e.g. `text-amber-600`). Same for B.

  4d. Alert feed grid (two columns):
  - Wrapper div with `grid grid-cols-2 gap-4`
  - Column A: map over visibleAlertsA, render card with `key={`${alert.timestamp_ms}-${alert.rule_triggered}-${alert.frame_index}`}` (never use array index as key—breaks new-card animation detection when items shift)
  - Column B: map over visibleAlertsB, render card with same key pattern
  - Each card: rule label map (rule1→"Thermal asymmetry", rule2→"Torch angle", rule3→"Travel speed"), severity badge (warning=amber, critical=red), message, "⚡ Haptic → gun" tag
  - Card onClick: `() => { setCurrentTimestamp(alert.timestamp_ms); setIsPlaying(false); }`
  - Card classes: `cursor-pointer`, `hover:bg-zinc-100 dark:hover:bg-zinc-800`, `p-3 rounded border`

  4e. Critical full-column highlight:
  - Track `prevVisibleIdsA`, `prevVisibleIdsB` (or timestamps) via useRef
  - State: `columnACriticalFlash`, `columnBCriticalFlash`
  - In useEffect with dependency array `[visibleAlertsA, visibleAlertsB]`: when visibleAlertsA changes, check if any new alert has severity==="critical"; if yes, set columnACriticalFlash true, setTimeout clear after 800ms. Same for B. Must include `[visibleAlertsA, visibleAlertsB]` in the dependency array—without it the effect either never fires or fires on every render.
  - Apply conditional class to column div: `columnACriticalFlash ? 'ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse' : ''`

  4f. Non-critical card highlight:
  - When new warning enters, add brief card-level `animate-pulse` (e.g. 1.5s) — use key or timestamp to detect "new" and apply class that fades.

  **What it does:** Fetches alerts in parallel, shows count and feed, clickable cards seek and pause, critical alerts trigger full-column flash.

  **Assumptions:**
  - `firstTimestamp`, `lastTimestamp` are set when comparison has deltas
  - `setCurrentTimestamp`, `setIsPlaying` are in scope (they are in ComparePageInner)

  **Risks:**
  - Fetch fails for one session → log error, set alertsErrorA/B, surface "Alerts unavailable" in that column; sessions still load
  - Canvas limit → AlertFeed is DOM-only, no new Canvas

  **Git Checkpoint:**
  ```bash
  git add <COMPARE_INNER>
  git commit -m "feat: add alert feed with count summary, clickable cards, critical highlight"
  ```

  **Subtasks:**
  - [ ] 🟥 Add alertsA, alertsB, alertsErrorA, alertsErrorB state and fetch in load (error isolation; console.warn on failure, surface "Alerts unavailable")
  - [ ] 🟥 Add visibleAlertsA, visibleAlertsB via useMemo with deps [alertsA, alertsB, currentTimestamp, firstTimestamp]
  - [ ] 🟥 Add alert count summary UI (show "Alerts unavailable" when alertsError set)
  - [ ] 🟥 Add two-column AlertFeed with cards (key=`${timestamp_ms}-${rule_triggered}-${frame_index}`)
  - [ ] 🟥 Add clickable card onClick (seek + pause)
  - [ ] 🟥 Add critical full-column highlight useEffect with deps [visibleAlertsA, visibleAlertsB]

  **✓ Verification Test:**

  **Type:** E2E / Manual
  **Action:** Navigate to /compare/sess_expert_001/sess_novice_001 (with seed). Observe alert count, scrub timeline, click an alert card.
  **Expected:** Count updates with timeline; expert column ~0, novice column populates; click seeks and pauses; critical alert triggers column flash.
  **Debugging:** If column flash never triggers, add `console.log(alert.severity)` in the card onClick—confirm the backend returns `"critical"` not `"warning"`. Flash only fires for severity==="critical"; if backend sends "warning" the condition never matches.
  **Pass:** All behaviors observed.
  **Fail:** Alerts empty → backend not returning; fetch error → check network/API URL. Column flash absent → log alert.severity; if "warning" then backend AlertEngine may not be producing critical alerts for this session.

---

## Regression Guard

**Systems at risk:**
- Sessions API — new route added; existing routes unchanged
- Compare page — new state and UI; heatmaps and timeline unchanged

**Regression verification:**

| System | Pre-change behavior | Post-change verification |
|--------|---------------------|---------------------------|
| GET /api/sessions/{id} | Returns session with frames | Same; no change |
| Compare page heatmaps | Three columns, timeline works | Same; heatmaps render |
| Compare landing | Form with two inputs | Form still works; new button added |

**Test count:** Run `cd backend && python -m pytest -q` and `cd my-app && npm test -- --run` — count must be ≥ pre-flight baseline.

---

## Rollback Procedure

Revert the branch as a whole. Do not revert individual commits with `HEAD~N`—tilde notation shifts after each revert and selects the wrong commits.

```bash
# If on a feature branch: delete the branch and return to main.
git checkout main
git branch -D <feature-branch-name>

# If on main: identify the commit range, then revert the range.
git log --oneline   # find first and last commit hashes for this feature
git revert --no-commit <first_commit>^..<last_commit>
git commit -m "revert: compare alert feed feature"
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| GET /api/sessions/{id}/alerts | Returns { alerts: [...] } | curl endpoint → 200, JSON has alerts array |
| fetchSessionAlerts | Typed, uses buildUrl | Import in compare page, no type error |
| Expert vs Novice button | Navigates to comparison | Click from /compare → URL /compare/sess_expert_001/sess_novice_001 |
| Alert count summary | Updates with currentTimestamp | Scrubbing timeline changes count |
| Clickable alert card | Seeks and pauses | Click card → currentTimestamp = alert.timestamp_ms, isPlaying = false |
| Critical highlight | Full column flashes 0.5–1s | Critical alert appears → column glows briefly |
| Test count | ≥ baseline | pytest and npm test pass |
