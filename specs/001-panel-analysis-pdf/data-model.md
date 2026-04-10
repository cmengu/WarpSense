# Data Model: Panel-Centric Analysis & PDF Revamp

**Branch**: `001-panel-analysis-pdf` | **Phase**: 1 — Design | **Date**: 2026-03-26

---

## Entities

### MockSession (extended)

Existing entity in `src/types/warp-analysis.ts`. Two fields are added to support panel grouping.

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | `string` | yes | Unique session identifier (unchanged) |
| `welder_id` | `string` | yes | Welder identifier (unchanged) |
| `welder_name` | `string` | yes | Display name of the welder (unchanged) |
| `arc_type` | `string` | yes | Arc category (unchanged) |
| `arc_on_ratio` | `number \| null` | yes | Arc-on ratio metric (unchanged) |
| `disposition` | `WarpDisposition \| null` | yes | PASS / CONDITIONAL / REWORK_REQUIRED (unchanged) |
| `started_at` | `string` | yes | ISO 8601 timestamp (unchanged) |
| **`panel_id`** | `string` | **NEW** | Identifier of the weld panel this session belongs to (e.g., `"PANEL-A01"`) |
| **`panel_name`** | `string` | **NEW** | Human-readable panel name (e.g., `"Deck Panel A-01"`) |

**Validation rules**:
- `panel_id` must be non-empty
- `panel_name` must be non-empty
- Multiple sessions may share the same `panel_id` (a panel can have multiple weld sessions)
- A session belongs to exactly one panel

---

### WeldPanel (derived, client-side only)

Computed by grouping `MockSession[]` by `panel_id` in the Analysis page. Not persisted separately.

| Field | Type | Description |
|---|---|---|
| `panel_id` | `string` | Unique panel identifier |
| `panel_name` | `string` | Human-readable label |
| `welder_names` | `string[]` | Distinct welder names who worked on this panel |
| `sessions` | `MockSession[]` | All sessions belonging to this panel |
| `panel_disposition` | `WarpDisposition \| null` | Worst-case disposition across all sessions (REWORK_REQUIRED > CONDITIONAL > PASS > null) |

**Derivation logic**:
```
panel_disposition =
  if any session.disposition === "REWORK_REQUIRED" → "REWORK_REQUIRED"
  else if any session.disposition === "CONDITIONAL" → "CONDITIONAL"
  else if all sessions.disposition === "PASS" → "PASS"
  else → null  (any session still unanalysed)
```

**Relationships**:
- `WeldPanel` contains 1..N `MockSession` records
- `WeldPanel.welder_names` is derived from `distinct(session.welder_name)` across all sessions in the panel

---

### PDFPanelRequest (updated API contract)

Input schema for `POST /api/welder-report-pdf`. Fields marked **CHANGED** replace or extend existing fields.

| Field | Type | Required | Description |
|---|---|---|---|
| **`panel`** | `{ id: string; name: string }` | **CHANGED** (was `welder`) | Panel identifier and name — primary subject of the report |
| `welder_attribution` | `string \| null` | **NEW** | Comma-separated welder name(s) to show as attribution (e.g., "Ahmad Razif, Lee Wei") |
| `score` | `{ total: number; rules?: unknown[] }` | yes | Weld quality score 0–100 (unchanged) |
| `feedback` | `{ summary?: string; feedback_items?: unknown[] }` | no | Feedback items (unchanged) |
| `chartDataUrl` | `string \| null` | no | PNG data URI for chart image (unchanged) |
| `narrative` | `string \| null` | no | AI Coach narrative (unchanged) |
| `reportSummary` | `ReportSummary \| null` | no | Compliance section data (unchanged) |
| `certifications` | `Certification[] \| null` | no | Certification records (unchanged) |
| `sessionDate` | `string \| null` | no | Session date string (unchanged) |
| `duration` | `string \| null` | no | Session duration string (unchanged) |
| `station` | `string \| null` | no | Welding station label (unchanged) |
| `rework_cost_usd` | `number \| null` | no | Estimated rework cost in USD (unchanged, display demoted) |
| `disposition` | `string \| null` | no | Overall disposition (unchanged) |
| `agentInsights` | `AgentInsight[] \| null` | no | Per-agent findings (see below) |

#### AgentInsight (updated)

| Field | Type | Required | Description |
|---|---|---|---|
| `agent_name` | `string` | yes | Agent identifier (e.g., `"thermal_agent"`) |
| `disposition` | `string` | no | Agent-level verdict (unchanged) |
| `root_cause` | `string` | no | What happened — Part 1 of narrative (unchanged field, new display role) |
| `corrective_actions` | `string[]` | no | Corrective actions list (unchanged) |
| **`disposition_rationale`** | `string \| null` | **NEW** | What this means in the analysis — Part 2 of narrative |
| **`consequence`** | `string \| null` | **NEW** | How this may result in a faulty weld — Part 3 of narrative (deterministic lookup from defect category) |
| **`reject_label`** | `string \| null` | **NEW** | Short rejection label for the visual indicator (e.g., "HEAT EXCEEDANCE", "GEOMETRY DEVIATION") |

---

### State Transitions

**Analysis page panel selection flow**:
```
Initial → PanelList renders (sidebar) → User clicks panel
  → panel selected → first session in panel auto-selected for analysis
  → AnalysisTimeline renders for selected session
  → User can click other sessions within the panel detail view
```

**PDF report generation flow** (unchanged orchestration, updated payload):
```
QualityReportCard "Download PDF" click
  → captureChartToBase64()
  → build PDFPanelRequest (panel as primary, welder as attribution)
  → POST /api/welder-report-pdf
  → renderToBuffer(WelderReportPDF with new props)
  → download response
```

---

## State Shape Changes (Analysis Page)

**Before (welder-centric)**:
```typescript
selectedSession: MockSession | null   // session = primary unit
```

**After (panel-centric)**:
```typescript
selectedPanel: WeldPanel | null       // panel = primary sidebar unit
selectedSession: MockSession | null   // session = secondary (within panel)
```

The right-panel analysis view continues to operate on `selectedSession.session_id`. The panel is a navigation wrapper only — it does not change the analysis pipeline.
