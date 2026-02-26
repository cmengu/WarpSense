# Session 4 — Report Data Layer + Compliance UI: Execution Plan

**Overall Progress:** `100%` (Steps 1–7 done)

**Source:** [docs/ISSUE_SESSION_REPORT_DATA_LAYER.md](../docs/ISSUE_SESSION_REPORT_DATA_LAYER.md)

---

## TLDR

Build `GET /api/sessions/{session_id}/report-summary` (4A) and the compliance UI + PDF extension (4B). ReportSummary aggregates heat input, travel angle excursions (run-length collapsed), arc termination quality, defect counts from alerts, and excursion log. WPS thresholds live in `report_thresholds.json` keyed by process (aluminum_spray). Compliance slot renders first (before feedback); PDF omits compliance when reportSummary absent but logs server warning. Alert computation extracted to async `run_session_alerts`; route must await it.

---

## Critical Decisions

- **WPS config:** `backend/config/report_thresholds.json` keyed by process (e.g. `aluminum_spray`). Structure: `{"aluminum_spray": {"heat_input_min": 0.5, "heat_input_max": 0.9, "travel_angle_threshold": 25.0, "travel_angle_nominal": 12.0}}`. MVP has one entry; prevents refactor when steel WPS added.
- **ExcursionEntry:** Alert-sourced: `parameter_value`/`threshold_value` null; add optional `notes` from `AlertPayload.message`. Frame-derived: collapsed via run-length encoding; one entry per consecutive run with `duration_ms = last_ts - first_ts`, `parameter_value` = worst-case in run.
- **Slot order:** Compliance before feedback. Order: compliance → heatmaps → feedback → progress → trajectory → benchmarks → coaching → actions.
- **PDF without reportSummary:** Omit compliance section silently; log server-side warning when absent.
- **Async:** `run_session_alerts` is `async def`; report-summary route must `await` it. Route handler is `async def`.
- **Excursion collapse:** Consecutive frames in same excursion type collapsed into one ExcursionEntry with `duration_ms` and worst-case `parameter_value`. Single-frame runs are valid — emit with `duration_ms=0`. Do not skip.
- **useReportSummary:** AbortController cancels fetch on unmount. No placeholder "cancel" comments.
- **ComplianceSummaryPanel:** Accept `error?: string`, `isEmpty?: boolean`; four states: loading (skeleton), error (message), empty (loaded, nothing to show), data (three rows).
- **Caching:** Add `Cache-Control: max-age=60` on report-summary response.
- **process_type → config key:** `compute_report_summary` owns the full mapping. Route passes raw `process_type` from session. `compute_report_summary` maps `"aluminum"` → `"aluminum_spray"`, `"mig"` / None / unknown → `"aluminum_spray"`. Raises `ValueError` only if `"aluminum_spray"` is missing from config (cannot happen for MVP).

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| WPS threshold format | Keyed by process | Human | 4A Step 1 | Yes — report_thresholds.json |
| ExcursionEntry.notes | Optional, from AlertPayload.message | Human | 4A Step 1 | Yes |
| Slot order | Compliance first | Human | 4B Step 5 | Yes |
| Async/await | run_session_alerts async, await in route | Critique | 4A Step 2 | Yes |
| Run-length collapse | One entry per run | Critique | 4A Step 1 | Yes |
| process_type → config key | Single owner: compute_report_summary | Critique | 4A | Yes |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping: output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read backend/routes/sessions.py in full. Capture:
(1) Exact signature of get_session_alerts (async def, params)
(2) Lines 405–471: the alert loop structure (FrameModel → FrameInput → engine.push_frame)
(3) Every function that loads frames: grep -n "query.*FrameModel\|frame_models\|frames_query" backend/routes/sessions.py
(4) Read backend/models/frame.py: confirm heat_input_kj_per_mm, arc_termination_type, travel_angle_degrees exist
(5) Run: cd backend && python -m pytest tests/ -q --tb=no 2>&1 | tail -3
(6) Run: wc -l backend/routes/sessions.py backend/models/frame.py backend/realtime/alert_models.py

Do not change anything. Show full output.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count sessions.py: ____
Line count frame.py: ____
Line count alert_models.py: ____
get_session_alerts signature: async def get_session_alerts(session_id, db) — confirm
```

---

## Steps Analysis

| Step | Class | Reason | Idempotent |
|------|-------|--------|------------|
| 1 | Critical | New schemas, config, aggregator; run-length collapse | Yes |
| 2 | Critical | Alert extraction, API route, async/await | Yes |
| 3 | Non-critical | Unit tests, mock verification | Yes |
| 4 | Critical | New hook, api.ts, types | Yes |
| 5 | Critical | ReportLayout slot order, ComplianceSummaryPanel, error/isEmpty | Yes |
| 6 | Non-critical | ExcursionLogTable | Yes |
| 7 | Critical | PDF extension, server warning | Yes |

---

## Phase 1 — Session 4A (Backend)

**Goal:** `GET /api/sessions/{session_id}/report-summary` returns ReportSummary; alerts extracted; WPS config; run-length collapsed excursions.

---

### Step 1: WPS config + ReportSummary schemas + `compute_report_summary`

**Idempotent:** Yes.

**Pre-Read Gate:**
- `grep -n "heat_input_kj_per_mm\|arc_termination_type\|travel_angle_degrees" backend/models/frame.py` — must exist
- `ls backend/config/` — confirm alert_thresholds.json exists; report_thresholds.json must NOT exist yet

**Deliverables:**

1. **`backend/config/report_thresholds.json`** (new):

```json
{
  "aluminum_spray": {
    "heat_input_min": 0.5,
    "heat_input_max": 0.9,
    "travel_angle_threshold": 25.0,
    "travel_angle_nominal": 12.0
  }
}
```

2. **`backend/scoring/report_summary.py`** (new):
   - Load report_thresholds. **compute_report_summary owns the full process_type → config_key mapping.** Map: `"aluminum"` → `"aluminum_spray"`; `"mig"` / `None` / any other → `"aluminum_spray"`. Fallback config key is always `"aluminum_spray"`. Raise `ValueError` only if `"aluminum_spray"` is missing from config file.
   - `ExcursionEntry`: `timestamp_ms`, `defect_type`, `parameter_value: Optional[float]`, `threshold_value: Optional[float]`, `duration_ms: Optional[int]`, `source: Literal["alert","frame_derived"]`, `notes: Optional[str]`.
   - `ReportSummary`: schema per issue; WPS fields from config.
   - `compute_report_summary(session_id, frames, alerts, process_type: str) -> ReportSummary`:
     - Heat input: aggregate from frames; load wps_min/max from config; heat_input_compliant = mean in range.
     - Travel angle: run-length collapse — group consecutive frames where `|travel_angle - nominal| > threshold`; one ExcursionEntry per run with `timestamp_ms=first`, `duration_ms=last-first`, `parameter_value=worst` (max |angle - nominal| in run). **Single-frame runs are valid — emit with duration_ms=0. Do not skip.**
     - Arc termination: count crater_fill vs no_crater_fill from frames.
     - Defect counts: `Counter(a.rule_triggered for a in alerts)`.
     - Excursions: (a) Map alerts → ExcursionEntry (parameter_value/threshold_value=None, notes=a.message); (b) Add frame-derived entries from collapsed travel-angle runs; (c) Merge, sort by timestamp_ms.

**Run-length collapse (exact logic):**
- Iterate frames in order. When `|angle - nominal| > threshold`, start a run. Consecutive frames in excursion extend the run. When a frame exits excursion, emit one ExcursionEntry for the run. Use first frame timestamp, last - first for duration_ms, max deviation in run for parameter_value. Single-frame runs: emit with duration_ms=0. Do not add a guard that skips when duration_ms == 0.

**Git Checkpoint:** `git add backend/config/report_thresholds.json backend/scoring/report_summary.py && git commit -m "step 1: WPS config, ReportSummary schemas, compute_report_summary with run-length collapse"`

**Verification:**

```bash
cd backend && python -c "
from scoring.report_summary import compute_report_summary, ReportSummary
from models.frame import Frame
from realtime.alert_models import AlertPayload

# Excursion: |angle - nominal| > threshold. nominal=12, threshold=25 => angle < -13 or > 37.
# Use angle=40: |40-12|=28 > 25, so excursion.

# Single run: 5 consecutive excursion frames (angle=40)
f = [Frame(timestamp_ms=i*10, travel_angle_degrees=40, heat_input_kj_per_mm=0.7, arc_termination_type='crater_fill_present') for i in range(5)]
r = compute_report_summary('s1', f, [], 'aluminum')
assert r.session_id == 's1', r.session_id
assert r.heat_input_mean_kj_per_mm == 0.7, r.heat_input_mean_kj_per_mm
assert len(r.excursions) == 1, f'expected 1 collapsed run, got {len(r.excursions)}'
assert r.excursions[0].duration_ms == 40, f'expected duration 40 (last_ts 40 - first_ts 0), got {r.excursions[0].duration_ms}'
assert r.excursions[0].parameter_value == 28.0, f'expected max |40-12|=28, got {r.excursions[0].parameter_value}'
assert r.travel_angle_excursion_count == 5, f'expected 5 frame count, got {r.travel_angle_excursion_count}'

# Two runs: in-range frame (angle=15) in middle splits the run. Single-frame run at 30 has duration_ms=0.
f2 = [
    Frame(timestamp_ms=0, travel_angle_degrees=40, heat_input_kj_per_mm=0.7, arc_termination_type='crater_fill_present'),
    Frame(timestamp_ms=10, travel_angle_degrees=41, heat_input_kj_per_mm=0.7, arc_termination_type='crater_fill_present'),
    Frame(timestamp_ms=20, travel_angle_degrees=15, heat_input_kj_per_mm=0.7, arc_termination_type='crater_fill_present'),  # |15-12|=3 < 25, in range
    Frame(timestamp_ms=30, travel_angle_degrees=50, heat_input_kj_per_mm=0.7, arc_termination_type='crater_fill_present'),
]
r2 = compute_report_summary('s2', f2, [], 'aluminum')
assert len(r2.excursions) == 2, f'expected 2 runs (split by in-range frame), got {len(r2.excursions)}'
assert r2.excursions[0].timestamp_ms == 0
assert r2.excursions[0].duration_ms == 10
assert r2.excursions[1].timestamp_ms == 30
assert r2.excursions[1].duration_ms == 0, 'single-frame run: duration_ms should be 0 (last_ts - first_ts)'
assert r2.travel_angle_excursion_count == 3, f'expected 3 excursion frames (0, 1, 3), got {r2.travel_angle_excursion_count}'

print('ok')
"
```

---

### Step 2: Extract `run_session_alerts` + add report-summary route

**Idempotent:** Yes.

**Pre-Read Gate:**
- `grep -n "async def get_session_alerts" backend/routes/sessions.py` — exactly 1 match
- `grep -n "engine.push_frame" backend/routes/sessions.py` — find loop
- Confirm `run_session_alerts` does NOT exist: `grep -n "run_session_alerts" backend/` — 0 matches

**Deliverables:**

1. **`backend/services/alert_service.py`** (new):
   - `async def run_session_alerts(session_id: str, db) -> list[AlertPayload]`: Load frames (limit 2000), build FrameInput per frame, run AlertEngine, collect AlertPayload objects. Return `list[AlertPayload]` — **the actual Pydantic objects, NOT dicts**.
   - **CRITICAL:** `run_session_alerts` must NOT call `model_dump()`. It returns AlertPayload objects directly. `model_dump()` is called only inside `get_session_alerts` when building the HTTP response. If run_session_alerts returns dicts, compute_report_summary will call `a.rule_triggered` on a dict and raise AttributeError.
2. **`backend/routes/sessions.py`**:
   - Refactor `get_session_alerts` to call `alerts = await run_session_alerts(session_id, db)`, then `return {"alerts": [a.model_dump() for a in alerts]}`.
   - Add `async def get_report_summary(session_id, db)`:
     - Load session; 404 if missing.
     - Load frames (limit 2000) as Pydantic; same pattern as get_session.
     - `alerts = await run_session_alerts(session_id, db)` — **must await**.
     - `process_type = getattr(session_model, "process_type", None) or "mig"` — pass raw value. **Do not map to config key in the route.** Pass `process_type` to `compute_report_summary(session_id, frames, alerts, process_type)` — compute_report_summary owns the full mapping.
     - Return summary with `Cache-Control: max-age=60` in response headers.

**Anchor:** Insert new route after `get_session_alerts` (before `add_frames`). Use `from services.alert_service import run_session_alerts`.

**Git Checkpoint:** `git add backend/services/alert_service.py backend/routes/sessions.py && git commit -m "step 2: extract run_session_alerts, add GET report-summary route with await"`

**Verification (no running server required):**

```bash
cd backend && python -c "
from services.alert_service import run_session_alerts
import inspect
assert inspect.iscoroutinefunction(run_session_alerts), 'run_session_alerts must be async def'
print('ok')
"
```

**Manual curl test (requires running backend + seeded data):** After seeding, run `curl -s http://localhost:8000/api/sessions/sess_expert-benchmark_005/report-summary | head -c 500` — valid JSON. Not an automated gate.

---

### Step 3: Unit tests + mock verification

**Idempotent:** Yes.

**Deliverables:**

1. **`backend/tests/test_report_summary.py`** (new):
   - Test with synthetic frames (heat_input, arc_termination, travel_angle) and alerts.
   - Assert ReportSummary fields populated; run-length collapse produces one entry per run.
   - Test empty frames, no arc terminations, config load.
   - Test AlertPayload with `.message` maps to ExcursionEntry.notes.
   - Test process_type mapping: "aluminum", "mig", None all resolve to aluminum_spray thresholds.
2. Manual or script: Expert session `crater_fill_rate_pct == 100`, `heat_input_compliant == True`; novice `no_crater_fill_count > 0`, `travel_angle_excursion_count > 0`.

**Verification:** `cd backend && python -m pytest tests/test_report_summary.py -v`

---

## Phase 2 — Session 4B (Frontend)

**Goal:** Compliance slot before feedback, ComplianceSummaryPanel (with error, isEmpty), ExcursionLogTable, PDF extension with server warning.

---

### Step 4: `fetchReportSummary` + `useReportSummary` hook + types

**Idempotent:** Yes.

**Deliverables:**

1. **`my-app/src/types/report-summary.ts`** (new): `ReportSummary`, `ExcursionEntry` interfaces matching backend.
2. **`my-app/src/lib/api.ts`**:
   - `fetchReportSummary(sessionId: string): Promise<ReportSummary>` — GET `/api/sessions/${sessionId}/report-summary`, via buildUrl.
3. **`my-app/src/hooks/useReportSummary.ts`** (new):
   - `useReportSummary(sessionId: string | null) => { data, loading, error }`
   - useEffect: if !sessionId → setLoading(false), return. Else create AbortController, pass signal to fetch, then setData/setError. In cleanup: `controller.abort()`. No placeholder cancel comments—implement actual abort.

**Verification:** Add temporary `console.log(useReportSummary('sess_expert-benchmark_005'))` on welder page; confirm data loads, no state-update-after-unmount in console. **After confirming, remove the console.log before the Step 4 git commit.**

**Git Checkpoint:** `git add my-app/src/types/report-summary.ts my-app/src/lib/api.ts my-app/src/hooks/useReportSummary.ts && git commit -m "step 4: fetchReportSummary, useReportSummary hook, report-summary types"`

---

### Step 5: ReportLayout compliance slot + ComplianceSummaryPanel

**Idempotent:** Yes.

**Pre-Read Gate:**
- `grep -n "heatmaps\?\|\|feedback\?\|\|" my-app/src/components/layout/ReportLayout.tsx` — confirm slot order
- ReportLayout slots: backLink, narrative (in header), heatmaps, feedback, progress, trajectory, benchmarks, coaching, certification, actions
- **New order:** compliance → heatmaps → feedback → progress → trajectory → benchmarks → coaching/certification → actions

**Deliverables:**

1. **`my-app/src/components/layout/ReportLayout.tsx`**:
   - Add `compliance?: React.ReactNode` to props.
   - In `space-y-8`, render compliance **first** (before heatmaps): `{compliance && <section aria-label="Compliance">{compliance}</section>}` then heatmaps, feedback, etc.
2. **`my-app/src/components/welding/ComplianceSummaryPanel.tsx`** (new):
   - Props: `data: ReportSummary | null`, `error?: string | null`, `isEmpty?: boolean`
   - Four states: (a) `error` set → render error message; (b) `!data && !error && !isEmpty` → skeleton (loading); (c) `isEmpty` (caller passes true when `!loading && !data && !error`) → "Compliance data unavailable"; (d) `data` present → three rows (Heat Input, Torch Angle, Arc Termination) with label, actual, threshold, pass/fail badge.
3. **`my-app/src/app/seagull/welder/[id]/page.tsx`**:
   - Add `useReportSummary(sessionId)`.
   - Add compliance slot. **Must use React fragment** — two adjacent JSX elements require a wrapper. Valid syntax:
   ```tsx
   compliance={
     <>
       <ComplianceSummaryPanel
         data={reportSummary ?? null}
         error={reportSummaryError ?? undefined}
         isEmpty={!reportSummaryLoading && !reportSummary && !reportSummaryError}
       />
       <ExcursionLogTable excursions={reportSummary?.excursions ?? []} />
     </>
   }
   ```
   - Pass `reportSummaryLoading` and `reportSummaryError` from useReportSummary. When `isEmpty` is true, ComplianceSummaryPanel shows "Compliance data unavailable" instead of skeleton.

**Verification:** Novice welder page shows compliance section first; expert shows green badges; error state shows message when report-summary fails; empty state (no data after load) shows "Compliance data unavailable".

---

### Step 6: ExcursionLogTable

**Idempotent:** Yes.

**Deliverables:**

1. **`my-app/src/components/welding/ExcursionLogTable.tsx`** (new):
   - Props: `excursions: ExcursionEntry[]`
   - Columns: Time (mm:ss), Type, Value, Threshold, Duration, Notes (optional)
   - Client-side sort by timestamp (default asc) or type. Empty state: "No excursions — session within compliance".
   - Time format: `Math.floor(ms/60000)` for minutes, `Math.floor((ms%60000)/1000)` for seconds; display as `m:ss`.

2. **`my-app/src/__tests__/components/welding/ExcursionLogTable.test.tsx`** (new):
   - Import `@testing-library/react`, `ExcursionLogTable`, type `ExcursionEntry`.
   - Render with excursions in reverse timestamp order: `[{timestamp_ms: 200000, defect_type: "b", parameter_value: 1, threshold_value: 2, source: "frame_derived" as const}, {timestamp_ms: 100000, defect_type: "a", parameter_value: 1, threshold_value: 2, source: "frame_derived" as const}]`.
   - With default sort by timestamp asc, first data row shows 1:40 (100000ms). Assert: `expect(screen.getByText("1:40")).toBeInTheDocument()` and that "1:40" appears before "3:20" in document order (e.g. `document.body.textContent.indexOf("1:40") < document.body.textContent.indexOf("3:20")`). A broken or absent sort would show 3:20 first.
   - Empty state: render with `excursions={[]}`, assert `screen.getByText(/No excursions/i)`.

**Verification:** `cd my-app && npm run test -- ExcursionLogTable.test --run`
- Pass: first row shows 1:40 when data passed as [200000, 100000]; empty state shows "No excursions".
- Fail: first row shows 3:20 → sort is broken or absent.

---

### Step 7: PDF extension + server warning

**Idempotent:** Yes.

**Deliverables:**

1. **`my-app/src/components/pdf/WelderReportPDF.tsx`**:
   - Add optional `reportSummary?: ReportSummary | null` prop.
   - When present, render compliance section (summary stats + excursion table).
2. **`my-app/src/app/api/welder-report-pdf/route.ts`**:
   - Accept optional `reportSummary` in body.
   - If absent: log warning (e.g. `logError` or `logger.warning` with "reportSummary absent in PDF request — fetch may have failed"), omit from WelderReportPDF.
   - Pass reportSummary to WelderReportPDF when present.
3. **`my-app/src/app/seagull/welder/[id]/page.tsx`**:
   - In `handleDownloadPDF` payload, add `reportSummary: reportSummary ?? undefined` (from useReportSummary data).

**Verification:**
- Download PDF from novice session — contains compliance section.
- **Server warning test:** In `route.ts`, temporarily add `const testBody = { ...body, reportSummary: undefined };` and use `testBody` instead of `body` for the render. Run a PDF request (trigger download from welder page). Check server logs for the warning. Revert the temporary change.

---

## Regression Guard

| System | Pre-change | Post-change |
|--------|------------|-------------|
| get_session_alerts | Returns alerts | Same; now delegates to run_session_alerts |
| Welder report page | Renders without compliance | Renders with compliance first |
| PDF download | Works without reportSummary | Works; omits section, logs warning |
| Test count | Baseline | ≥ baseline |

---

## Rollback

**Confirmed:** 7 steps = 7 commits. Backend: Steps 1–3. Frontend: Steps 4–7.

```bash
git revert --no-commit HEAD~7..HEAD
git commit -m "rollback session report data layer"
cd backend && python -m pytest tests/ -q
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| report-summary endpoint | Returns ReportSummary | Python import test passes; curl when server running |
| run_session_alerts return type | AlertPayload objects | compute_report_summary receives objects, no AttributeError |
| Run-length collapse | One entry per run; single-frame emits duration_ms=0 | Step 1 verification: len(excursions)==1, two-run split, travel_angle_excursion_count==3 |
| process_type mapping | Single owner: compute_report_summary | Route passes raw; Step 3 test verifies mig/aluminum/None resolve |
| Async/await | No coroutine bugs | inspect.iscoroutinefunction(run_session_alerts) |
| Compliance slot order | First, before feedback | Visual check; compliance section before heatmaps |
| Compliance slot JSX | Valid (fragment) | No compile error; two components wrapped in <> </> |
| ComplianceSummaryPanel states | loading, error, empty, data | Four distinct renders |
| ExcursionLogTable sort | Default asc by timestamp | Test: reverse-ordered data → first row "1:40" |
| PDF without reportSummary | Omit section, log warning | Manual: testBody with reportSummary undefined → check logs |
| useReportSummary unmount | No state updates after unmount | Remove console.log before commit; navigate away during fetch, no console errors |
