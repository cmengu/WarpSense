# Session 4 — Report Data Layer + Compliance UI: Exploration

**Source:** [docs/ISSUE_SESSION_REPORT_DATA_LAYER.md](../docs/ISSUE_SESSION_REPORT_DATA_LAYER.md)

---

## 1. Integration Points & Dependencies

### Backend (4A)

| Component | Location | Role |
|-----------|----------|------|
| Sessions route | `backend/routes/sessions.py` | Has `get_session`, `get_session_alerts`, `get_session_score`. New route `get_report_summary` will live here. |
| Frame loading | `FrameModel.frame_data` (JSON) → `Frame(**frame_data)` | Frames are stored as JSON; `to_pydantic()` yields Pydantic Frame. Report aggregator needs Frame list with `heat_input_kj_per_mm`, `arc_termination_type`, `travel_angle_degrees`. |
| Alert engine | `backend/realtime/alert_engine.py` | `get_session_alerts` loads frames, builds `FrameInput`, runs `push_frame`, returns `AlertPayload[]`. Report-summary will need the same alert output. |
| Scoring | `backend/services/scoring_service.py`, `backend/features/extractor.py` | **Do not touch.** Report aggregator is isolated. |

**Alert reuse:** `get_session_alerts` is an async route handler. The report-summary route has two options: (a) Extract alert computation into a shared function (e.g. `run_session_alerts(session_id, db) -> list[AlertPayload]`) used by both routes, or (b) Duplicate frame load + AlertEngine loop in report-summary. **Recommendation:** Extract to `services/alert_service.py` or similar; both routes call it. Avoids duplication and keeps single source of truth.

### Frontend (4B)

| Component | Location | Role |
|-----------|----------|------|
| Welder report page | `my-app/src/app/seagull/welder/[id]/page.tsx` | Fetches session, score, narrative, benchmarks, trajectory. Uses `Promise.allSettled`. Add `fetchReportSummary(sessionId)` to the fetch bundle. |
| ReportLayout | `my-app/src/components/layout/ReportLayout.tsx` | Slot-based: narrative, heatmaps, feedback, progress, trajectory, benchmarks, coaching, certification, actions. **No compliance slot yet.** Per rules: "Never remove a slot — only add new ones." Add `compliance?: React.ReactNode`. |
| PDF | `my-app/src/app/api/welder-report-pdf/route.ts` | Next.js API route. Receives JSON body, renders `WelderReportPDF`. Page POSTs to `getApiBase() + '/api/welder-report-pdf'` (same-origin). Add `reportSummary` to body. |
| WelderReportPDF | `my-app/src/components/pdf/WelderReportPDF.tsx` | React-PDF component. Add optional `reportSummary` prop; render compliance + excursion section when present. |

**API routing:** Session/score/alerts hit FastAPI backend (`buildUrl` → `API_BASE_URL`). PDF hits Next.js API route (`getApiBase()` + `/api/welder-report-pdf`). Report-summary will be backend: `buildUrl(\`/api/sessions/${sessionId}/report-summary\`)`.

### Frame type on frontend

`my-app/src/types/frame.ts` does **not** define `travel_angle_degrees`, `heat_input_kj_per_mm`, or `arc_termination_type`. The backend `Frame` and `frame_data` have them. The report-summary aggregator runs **only on the backend** — it receives Pydantic Frames, so no frontend Frame type change needed for 4A. For 4B, the frontend consumes `ReportSummary` (new type); excursions contain `timestamp_ms`, `defect_type`, etc. — no need to extend the Frame type for this feature.

---

## 2. Data Flow

### 4A — Backend

```
User/curl → GET /api/sessions/{id}/report-summary
    → Sessions route handler
    → Load SessionModel + FrameModels (limit 2000, same as alerts)
    → Convert frame_data dicts to Frame (Pydantic)
    → run_session_alerts(session_id, db) OR inline AlertEngine loop
    → compute_report_summary(session_id, frames, alerts)
    → Return ReportSummary JSON
```

**Key decision:** Report-summary should cap frames at 2000 (same as get_session_alerts) for consistency. Sessions with > 2000 frames get partial aggregates — document as known limitation.

### 4B — Frontend

```
Page mount (welderId, sessionId)
    → useEffect: fetchSession, fetchScore, fetchReportSummary, ... (add report-summary)
    → Promise.allSettled
    → setReportSummary(result) if fulfilled
    → ReportLayout receives compliance={
          <ComplianceSummaryPanel data={reportSummary} />
          <ExcursionLogTable excursions={reportSummary?.excursions ?? []} />
        }
    → User clicks Download PDF
        → handleDownloadPDF: fetch narrative, capture chart, build payload including reportSummary
        → POST /api/welder-report-pdf { ..., reportSummary }
        → Next.js route renders WelderReportPDF with reportSummary
        → Returns PDF blob, triggers download
```

**State location:** Report summary lives in `WelderReportInner` state (`useState<ReportSummary | null>`). Could use `useReportSummary(sessionId)` hook — hook manages fetch, loading, error; page receives `{ data, loading, error }`. Compare page uses inline useEffect + useState for alerts; welder page uses same pattern for primary data. **Recommendation:** Add `useReportSummary` to match the "data hook first" spec and keep page logic clean.

---

## 3. Component Structure (4B)

```
WelderReportPage
├── WelderReportWithAsyncParams
│   └── WelderReportInner
│       ├── useReportSummary(sessionId)  ← NEW: { data, loading, error }
│       ├── ReportLayout
│       │   ├── ... existing slots ...
│       │   ├── compliance  ← NEW slot: wraps both panels
│       │   │   ├── ComplianceSummaryPanel  ← NEW
│       │   │   │   └── props: reportSummary (or null)
│       │   │   └── ExcursionLogTable  ← NEW
│       │   │       └── props: excursions[], sortable
│       │   └── actions (Download PDF — includes reportSummary in payload)
```

**ReportLayout slot:** Add `compliance?: React.ReactNode`. Render order in `space-y-8`: heatmaps → feedback → **compliance** → progress → trajectory → benchmarks → coaching/cert → actions. Insert compliance after feedback (compliance is more "raw QA" than "AI feedback").

**ComplianceSummaryPanel:** Three rows — Heat Input, Torch Angle, Arc Termination. Each row: label, actual value (or "—" if null), threshold range, pass/fail badge (green/red dot or pill). Accept `ReportSummary | null`; if null, show skeleton or "Loading compliance...".

**ExcursionLogTable:** Columns: Time (formatted mm:ss), Type, Value, Threshold, Duration. Client-side sort by timestamp (default) or type. Empty state: "No excursions recorded — session within compliance".

---

## 4. State Management

| State | Location | Trigger |
|-------|----------|---------|
| reportSummary | `useReportSummary` hook (or page useState) | useEffect on sessionId |
| pdfLoading, pdfError | Page (existing) | handleDownloadPDF |
| excursion sort | ExcursionLogTable internal (useState for sortBy, sortDir) | User clicks column header |

**Side effects:**
- `useEffect` in page (or inside useReportSummary): on mount + when sessionId changes, call `fetchReportSummary(sessionId)`. Set loading → fetch → set data/error → set loading false.
- `handleDownloadPDF` already has useEffect-like flow (callback); add reportSummary to payload when available. If reportSummary is null (e.g. fetch failed), PDF can still generate without compliance section — same pattern as narrative (optional).

---

## 5. Edge Cases

| Case | Handling |
|------|----------|
| **report-summary 404** | Session not found. Page already handles session/score 404. Report summary is additive — if it fails, show "Compliance data unavailable" in compliance slot, rest of page works. |
| **report-summary 500** | Alert engine/config error. Hook returns error; ComplianceSummaryPanel shows error message or empty state. |
| **Empty excursions** | ExcursionLogTable shows "No excursions — session within compliance". |
| **Null heat_input_* (no arc-on frames)** | ComplianceSummaryPanel shows "—" for actual value, badge "N/A" or gray. |
| **PDF without reportSummary** | WelderReportPDF already handles optional narrative, certifications. Add optional reportSummary; if absent, omit compliance section. PDF still generates. |
| **Session with 0 frames** | compute_report_summary: all aggregates default (0, None). heat_input_compliant=False (no data = not compliant). |
| **Frames without heat_input/arc_termination (legacy data)** | Aggregator uses only frames that have the field. If none, min/max/mean stay None, total_arc_terminations=0. |

---

## 6. Implementation Approach

### New files

```
backend/
  scoring/
    report_summary.py       ← ReportSummary, ExcursionEntry schemas; compute_report_summary()
  tests/
    test_report_summary.py  ← Unit tests with synthetic frames + alerts

my-app/src/
  hooks/
    useReportSummary.ts     ← fetchReportSummary, { data, loading, error }
  components/
    welding/
      ComplianceSummaryPanel.tsx   ← Three rows, pass/fail badges
      ExcursionLogTable.tsx       ← Sortable table, empty state
  types/
    report-summary.ts       ← ReportSummary, ExcursionEntry TS interfaces
```

### Modified files

```
backend/
  routes/
    sessions.py            ← Add GET /sessions/{id}/report-summary
  (optional) services/
    alert_service.py       ← Extract run_session_alerts() for reuse (or inline in report-summary)

my-app/src/
  lib/
    api.ts                 ← Add fetchReportSummary(), ReportSummary type (or in types/)
  app/seagull/welder/[id]/
    page.tsx               ← useReportSummary; add compliance slot; include reportSummary in PDF payload
  components/
    layout/
      ReportLayout.tsx     ← Add compliance?: React.ReactNode slot
    pdf/
      WelderReportPDF.tsx  ← Add reportSummary prop, render compliance + excursions
  app/api/
    welder-report-pdf/
      route.ts             ← Accept reportSummary in body, pass to WelderReportPDF
```

### Why this structure

- **report_summary.py in scoring/:** Aggregation logic is scoring-adjacent (evaluates compliance) but isolated. No import of rule_based or extract_features.
- **useReportSummary as dedicated hook:** Keeps page lean; hook encapsulates fetch + loading + error. Reusable if another page needs report summary.
- **ComplianceSummaryPanel + ExcursionLogTable separate:** Panel is compact (3 rows); table can grow (sorting, pagination later). Separation of concerns.
- **ReportLayout compliance slot:** Matches existing slot pattern; page composes the slot content.
- **Types in types/report-summary.ts:** Keeps api.ts focused on fetch; types can be imported by hook, components, PDF.

---

## 7. Ambiguities & Open Questions

### Blocking (decide before 4A)

1. **WPS threshold source:** Hardcoded 0.5/0.9, config file, or per-session? Issue says "decide before 4A". Config file (`backend/config/report_thresholds.json`) is low-effort and documents the values.

2. **Travel angle nominal:** Excursion = |travel_angle − nominal| > 25°. What is nominal? Issue suggests 12° (expert push). Is it per-session (e.g. from thresholds) or global constant? If global, add to config.

### Clarifications (nice to have)

3. **ExcursionEntry from AlertPayload:** AlertPayload has `frame_index`, `rule_triggered`, `timestamp_ms`, `message`, `correction`. No `parameter_value`, `threshold_value`, `duration_ms`. The aggregator must derive these. Options: (a) Map rule_triggered → human label; use a placeholder for parameter/threshold (e.g. "—") for alert-sourced entries; (b) Extend AlertPayload in a future change. For MVP, (a) — show rule_triggered and timestamp; parameter_value/threshold_value can be "—" for now.

4. **frame_derived excursions:** Which frame-level conditions produce an ExcursionEntry? Heat input outside [0.5, 0.9]? Travel angle outside ±25°? Both? Document in compute_report_summary.

5. **ReportLayout slot order:** Compliance after feedback, before progress — confirm.

6. **Duration for sustained alerts:** Arc instability, lack of fusion can span multiple frames. duration_ms = last_alert_timestamp − first_alert_timestamp for same rule in a burst? Or leave null for MVP?

---

## 8. High-Level Mock Execution

### 4A — Backend

```python
# backend/scoring/report_summary.py (skeleton)
def compute_report_summary(session_id: str, frames: List[Frame], alerts: List[AlertPayload]) -> ReportSummary:
    heat_vals = [f.heat_input_kj_per_mm for f in frames if f.heat_input_kj_per_mm is not None]
    heat_min = min(heat_vals) if heat_vals else None
    heat_max = max(heat_vals) if heat_vals else None
    heat_mean = mean(heat_vals) if heat_vals else None
    heat_compliant = (heat_mean is not None and wps_min <= heat_mean <= wps_max)

    # Travel angle: |angle - nominal| > threshold → excursion
    nominal = 12.0  # or from config
    excursions_angle = [f for f in frames if f.travel_angle_degrees is not None 
                        and abs(f.travel_angle_degrees - nominal) > travel_angle_threshold]
    travel_angle_excursion_count = len(excursions_angle)

    # Arc termination: count crater_fill vs no_crater_fill
    terminations = [f for f in frames if f.arc_termination_type is not None]
    no_crater = sum(1 for f in terminations if f.arc_termination_type == "no_crater_fill")
    total_term = len(terminations)
    crater_fill_rate = 100 * (total_term - no_crater) / total_term if total_term else 0

    # Defect counts from alerts
    defect_counts = Counter(a.rule_triggered for a in alerts)

    # Excursions: map alerts to ExcursionEntry; add frame_derived for heat/angle
    excursions = []
    for a in alerts:
        excursions.append(ExcursionEntry(timestamp_ms=a.timestamp_ms, defect_type=a.rule_triggered, ...))
    for f in excursions_angle:
        excursions.append(ExcursionEntry(..., source="frame_derived"))
    excursions.sort(key=lambda e: e.timestamp_ms)

    return ReportSummary(session_id=..., generated_at=datetime.now(timezone.utc), ...)
```

```python
# backend/routes/sessions.py — new handler
@router.get("/sessions/{session_id}/report-summary")
async def get_report_summary(session_id: str, db: OrmSession = Depends(get_db)):
    session_model = db.query(SessionModel).filter_by(session_id=session_id).first()
    if not session_model:
        raise HTTPException(404, "Session not found")
    frames = load_frames_as_pydantic(db, session_id, limit=2000)
    alerts = run_session_alerts(session_id, db)  # or inline
    return compute_report_summary(session_id, frames, alerts)
```

### 4B — Frontend

```typescript
// useReportSummary — high level
function useReportSummary(sessionId: string | null) {
  const [data, setData] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!sessionId) { setLoading(false); return; }
    setLoading(true);
    fetchReportSummary(sessionId)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
    return () => { /* cancel if unmount */ };
  }, [sessionId]);
  return { data, loading, error };
}

// ComplianceSummaryPanel — render logic
if (!reportSummary) return <Skeleton /> or "Loading compliance...";
// Three rows: Heat Input | actual mean / range | WPS 0.5–0.9 | ✓ or ✗
//           Torch Angle | excursion count / worst | ±25° | ✓ or ✗
//           Arc Termination | crater fill rate | 100% target | ✓ or ✗

// ExcursionLogTable — render logic
if (excursions.length === 0) return <p>No excursions — session within compliance</p>;
// Table: Time | Type | Value | Threshold | Duration
// Sort state: sortBy ('timestamp_ms' | 'defect_type'), sortDir (asc | desc)
```

---

## 9. Questions to Confirm

1. **WPS config:** Proceed with `report_thresholds.json` (heat_input 0.5–0.9, travel_angle 25°, nominal 12°) for MVP?
2. **ExcursionEntry.field mapping from AlertPayload:** Use rule_triggered as defect_type; parameter_value/threshold_value = null or "—" for alert-sourced entries until we extend AlertPayload?
3. **Compliance slot placement:** After feedback, before progress — correct?
4. **PDF without reportSummary:** Omit compliance section (like narrative); no error — correct?
