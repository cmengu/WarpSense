# Implementation Plan: Panel-Centric Analysis & PDF Revamp

**Branch**: `001-panel-analysis-pdf` | **Date**: 2026-03-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-panel-analysis-pdf/spec.md`

---

## Summary

Refactor the Analysis page sidebar from a welder-session list to a panel-grouped list (panels show which senior welder(s) worked on them). Update the PDF report to make the weld panel the primary subject, display a prominent 1–100 quality score, demote the rework cost to a compact secondary element, and replace the raw agent findings with a three-part humanised rejection narrative per flagging agent. Visual polish across both surfaces.

**Technical approach**: Panel data is enriched client-side via a static mapping file (sessions come from a FastAPI backend and cannot be modified). `WeldPanel` is derived by grouping enriched sessions. A new `PanelList.tsx` replaces `SessionList` in the sidebar. `WelderReportPDF.tsx` is updated for the new layout and extended agent narrative. No new back-end services, no new LLM calls, no new npm packages.

---

## Technical Context

**Language/Version**: TypeScript 5.0+ / Node.js (Next.js runtime)
**Primary Dependencies**: Next.js 16.1.6 (App Router), React 19.2.3, `@react-pdf/renderer` 4.3.2, Tailwind CSS 4.0, Recharts 3.7.0, Lucide React 0.576.0
**Storage**: Sessions fetched from FastAPI backend via `/api/warp/mock-sessions` proxy. Panel enrichment is a client-side static mapping — no database changes.
**Testing**: No automated test suite; manual browser + PDF download verification.
**Target Platform**: Web (desktop browser, Next.js app)
**Project Type**: Web application (full-stack Next.js, App Router)
**Performance Goals**: PDF generation < 3 seconds; sidebar panel switch < 200ms
**Constraints**: `@react-pdf/renderer` — PDF primitives only (View, Text, Image, StyleSheet); no SVG, no DOM, no Tailwind inside PDF components.
**Scale/Scope**: Single application; tens of sessions per panel list.

---

## Constitution Check

Constitution file is a placeholder template — no gates enforced. No new projects, no new external dependencies, no new databases. Clean.

---

## Conflict Analysis (vs. actual codebase)

The following conflicts were found between the original plan and the real code. Each is resolved below.

### C1 — Sessions come from FastAPI backend, not a local constant

**Original plan**: "Find `MOCK_SESSIONS` constant in `page.tsx` or `my-app/src/lib/` and add `panel_id`/`panel_name`."

**Reality**: `fetchMockSessions()` in `warp-api.ts` calls `GET /api/warp/mock-sessions`, which proxies to the FastAPI backend. There is no editable local constant.

**Resolution**: Create `my-app/src/lib/panel-mapping.ts` — a client-side static map of `welder_id → { panel_id, panel_name }`. `groupSessionsByPanel()` reads this map when enriching sessions. Welders who are not in the map get a generated panel (`panel_id = welder_id`, `panel_name = welder_name`). This approach requires zero backend changes and degrades gracefully.

Do NOT add `panel_id`/`panel_name` to the `MockSession` TypeScript interface — instead, derive `WeldPanel` directly from sessions + the mapping without modifying the shared type (avoids TypeScript errors across all existing consumers of `MockSession`).

### C2 — Agent names are PascalCase throughout the codebase

**Original plan**: `CONSEQUENCE_BY_AGENT` keyed on `thermal_agent`, `geometry_agent`, `process_agent`.

**Reality**: `WelderReportPDF.tsx` uses `AGENT_ORDER = ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"]`. `QualityReportCard.AGENT_DISPLAY` also uses PascalCase keys. `parseSpecialistRows()` extracts `agent_name` from `llm_raw_response` JSON — the backend emits PascalCase names.

**Resolution**: `CONSEQUENCE_BY_AGENT`, `REJECT_LABEL_BY_AGENT`, and all per-agent lookups must use PascalCase keys: `"ThermalAgent"`, `"GeometryAgent"`, `"ProcessStabilityAgent"`.

### C3 — `route.ts` requires `feedback` field (hard 400 if absent)

**Original plan**: Contract marked `feedback` as optional.

**Reality**: Lines 154–157 in `route.ts` return 400 if `body.feedback` is absent. `QualityReportCard.handleExportPdf` always sends `feedback` (derived from `report.corrective_actions`). This currently works.

**Resolution**: Keep `feedback` as a required field in the route — do not change this validation. `QualityReportCard` continues to send it. The plan's API contract was wrong; the corrected contract retains `feedback` as required.

### C4 — No `quality_score` field on `WarpReport`; score is hardcoded in client

**Original plan**: "Use existing `score.total`" — assumed a quality score was available from the report.

**Reality**: `WarpReport.confidence` is AI model confidence (0–1 float), not a quality score. `QualityReportCard.handleExportPdf` hardcodes: `PASS → 85`, `CONDITIONAL → 55`, `REWORK_REQUIRED → 30`. `WelderTrendPoint.quality_score` exists but is not available inside `QualityReportCard` (it comes from a separate trend fetch by welder_id).

**Resolution**: Keep the disposition-based score mapping. Make the score hero in the PDF render this value as `"X / 100"` prominently. Document as a known limitation: score will be derived from live `quality_score` when the backend surfaces it on `WarpReport`. No changes to the scoring logic.

### C5 — No per-agent `disposition_rationale` available from backend

**Original plan**: Each agent narrative Part 2 ("In the analysis:") populated from per-agent `disposition_rationale`.

**Reality**: `WarpReport` has one top-level `disposition_rationale`. `specialistRows` parsed from `llm_raw_response` have `root_cause` and `corrective_actions` per agent — no `disposition_rationale` per agent.

**Resolution**: Use a deterministic per-agent rationale template (similar to `CONSEQUENCE_BY_AGENT`). Add `RATIONALE_BY_AGENT: Record<string, string>` in `QualityReportCard.tsx`:

```typescript
const RATIONALE_BY_AGENT: Record<string, string> = {
  ThermalAgent:
    "This heat excursion places the heat-affected zone outside the WPS-specified bounds, indicating insufficient travel speed or pre-heat control.",
  GeometryAgent:
    "The geometric deviation suggests torch angle drift or inconsistent standoff distance, resulting in a weld profile that does not meet dimensional acceptance criteria.",
  ProcessStabilityAgent:
    "The process anomaly reflects inconsistent arc behaviour, which typically results from parameter drift, contact tip wear, or shielding gas fluctuation.",
};
```

For passing agents all three narrative fields are null — no narrative block rendered.

### C6 — Panel context not threaded to `QualityReportCard`

**Original plan**: `QualityReportCard` builds the PDF payload with `panel.id` and `panel.name` from session data.

**Reality**: `QualityReportCard` only receives `report: WarpReport` and `welderDisplayName: string | null`. It has no access to panel data. The panel context must be threaded via props:

```
page.tsx
  → AnalysisTimeline (new props: panelId, panelName)
    → QualityReportCard (new props: panelId, panelName)
```

`AnalysisTimeline` currently uses `welderDisplayName` from the parent — this prop is kept and renamed to `displayContext` (receives `panel_name`). Two additional props `panelId` and `panelName` are added and threaded through to `QualityReportCard`.

### C7 — Corrective actions in PDF come from `feedback.feedback_items`, not `agentInsights`

**Original plan**: Per-agent corrective actions appear in each agent's PDF section.

**Reality**: `WelderReportPDF.tsx` renders corrective actions from `feedback.feedback_items` (a global list). The `agentInsights` cards in the PDF currently only show `root_cause` — no corrective actions.

**Resolution**: For the new per-agent narrative layout, each agent's corrective actions come from `agentInsights[n].corrective_actions` (already present on `specialistRows` from `llm_raw_response`). The global `feedback.feedback_items`-based corrective actions section is removed from the PDF (it was a duplicate of the per-agent actions). The route continues to accept and validate `feedback` (C3 above) — the PDF component simply stops rendering it as the global section.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-panel-analysis-pdf/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output (updated below)
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── pdf-api.md       ← Phase 1 output (updated below)
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
my-app/src/
├── lib/
│   └── panel-mapping.ts              ← NEW: static welder_id → panel mapping; groupSessionsByPanel(); WeldPanel type
├── app/
│   ├── (app)/analysis/
│   │   └── page.tsx                  ← MODIFY: replace SessionList with PanelList; add selectedPanel state; thread panelId/panelName to AnalysisTimeline
│   └── api/
│       └── welder-report-pdf/
│           └── route.ts              ← MODIFY: accept panel instead of welder; make welder_attribution optional; extend agentInsights with rationale/consequence/reject_label fields; feedback stays required
├── components/
│   ├── analysis/
│   │   ├── PanelList.tsx             ← NEW: panel-grouped sidebar; receives panels: WeldPanel[] as prop
│   │   ├── SessionList.tsx           ← RETAIN unchanged
│   │   ├── AnalysisTimeline.tsx      ← MODIFY: rename welderDisplayName → displayContext; add panelId/panelName props; thread to QualityReportCard
│   │   └── QualityReportCard.tsx     ← MODIFY: add panelId/panelName props; rebuild PDF payload; add CONSEQUENCE_BY_AGENT/RATIONALE_BY_AGENT/REJECT_LABEL_BY_AGENT lookups
│   └── pdf/
│       └── WelderReportPDF.tsx       ← MODIFY: panel header, welder attribution, score hero, compact rework cost inline, per-agent three-part narrative with reject badge, remove global corrective actions section
```

**Structure Decision**: Single web application, all changes within `my-app/`. One new file (`panel-mapping.ts`), one new component (`PanelList.tsx`). No new packages.

---

## Phase 0: Research

Research complete. See [research.md](./research.md) for original decisions.

**Updated decisions (post conflict analysis)**:

| # | Original Decision | Correction |
|---|---|---|
| 1 | Add `panel_id`/`panel_name` to `MockSession` type | Do NOT touch `MockSession` type. Create `panel-mapping.ts` instead; derive panels without modifying the shared type. |
| 2 | Consequence lookup uses snake_case agent keys | Use PascalCase: `ThermalAgent`, `GeometryAgent`, `ProcessStabilityAgent` |
| 3 | `feedback` field optional in route | `feedback` stays required in route (existing validation unchanged) |
| 4 | Use `score.total` from WarpReport | Score is hardcoded by disposition in QualityReportCard — keep this approach |
| 5 | Per-agent `disposition_rationale` from llm_raw_response | Not available per-agent; use `RATIONALE_BY_AGENT` deterministic template |
| 6 | QualityReportCard derives panel data from session | Panel data must be threaded as props: page.tsx → AnalysisTimeline → QualityReportCard |
| 7 | Per-agent corrective actions in PDF from agentInsights | Correct — from `specialistRows[n].corrective_actions`; remove global feedback section from PDF |

---

## Phase 1: Design

### Data Model (updated)

`MockSession` type is **not modified**. Instead:

```typescript
// my-app/src/lib/panel-mapping.ts

export interface WeldPanel {
  panel_id: string;
  panel_name: string;
  welder_names: string[];       // distinct welder names across all sessions in this panel
  sessions: MockSession[];
  panel_disposition: WarpDisposition | null; // worst-case: REWORK_REQUIRED > CONDITIONAL > PASS > null
}

/**
 * Static mapping: welder_id → panel assignment.
 * Sessions not in this map fall back to welder_id as panel_id.
 * Update this map as the backend eventually surfaces real panel data.
 */
const WELDER_PANEL_MAP: Record<string, { panel_id: string; panel_name: string }> = {
  // Populated with welder_ids from the running backend.
  // Example:
  // "expert-welder-001": { panel_id: "PANEL-A01", panel_name: "Deck Panel A-01" },
  // "novice-welder-002": { panel_id: "PANEL-B02", panel_name: "Hull Panel B-02" },
};

export function groupSessionsByPanel(sessions: MockSession[]): WeldPanel[] {
  // 1. Enrich each session with panel data from WELDER_PANEL_MAP (or fallback)
  // 2. Group by panel_id
  // 3. Sort panels alphabetically by panel_id
  // 4. Sort sessions within each panel by started_at descending
  // 5. Compute panel_disposition as worst-case across sessions
  // 6. Derive welder_names as distinct welder_name values
}
```

**State shape change in `page.tsx`**:
```typescript
// Before:
selectedSession: MockSession | null

// After:
selectedPanel: WeldPanel | null
selectedSession: MockSession | null  // retained; drives AnalysisTimeline
```

### Implementation Notes by File

#### `my-app/src/lib/panel-mapping.ts` (NEW)

Create this file with `WeldPanel` interface, `WELDER_PANEL_MAP` constant, and `groupSessionsByPanel()` function. Initially populate `WELDER_PANEL_MAP` with the actual `welder_id` values returned by the running backend — inspect the network response from `/api/warp/mock-sessions` to get real IDs. Fall back to `{ panel_id: session.welder_id, panel_name: session.welder_name }` for unmapped welders.

#### `my-app/src/components/analysis/PanelList.tsx` (NEW)

```
Props:
  panels: WeldPanel[]
  selectedPanelId: string | null
  selectedSessionId: string | null
  onPanelSelect: (panel: WeldPanel) => void
  onSessionSelect: (session: MockSession) => void
  isAnalysing: boolean
  onAnalyseAll: () => void
  loading: boolean         ← passed from page.tsx while sessions are loading

Rendering:
  - Loading: skeleton rows (same pattern as SessionList SkeletonRows)
  - Each panel entry: panel_name (bold), welder_names joined comma-separated (muted, small), disposition badge
  - Clicking a collapsed panel: expands it + onPanelSelect fires (auto-selects first session in parent)
  - Clicking an already-expanded panel header: no collapse (stay open)
  - Each session row within expanded panel: formatted timestamp, arc_type tag, disposition badge
  - Clicking a session row: onSessionSelect fires
  - Selected session row: highlighted (amber left-border, surface-2 bg)
  - "Analyse All" button at top (disabled while isAnalysing or all sessions analysed)
  - Disposition border colours on panel entries: red REWORK_REQUIRED, amber CONDITIONAL, green PASS, grey null
```

#### `my-app/src/app/(app)/analysis/page.tsx`

```
Import changes:
  + import { groupSessionsByPanel, WeldPanel } from "@/lib/panel-mapping"
  + import { PanelList } from "@/components/analysis/PanelList"
  - import { SessionList } from "@/components/analysis/SessionList"

State changes:
  + selectedPanel: WeldPanel | null  (initialized null)
  Keep: selectedSession: MockSession | null
  Add derived: panels = groupSessionsByPanel(allSessions)  (useMemo over allSessions)

Handler changes:
  handlePanelSelect: (panel: WeldPanel) => {
    setSelectedPanel(panel)
    const first = panel.sessions[0] ?? null
    setSelectedSession(first)
    if (first) startStream(first.session_id)
  }

  handleSessionSelect (renamed from existing): operates the same as before but
    also updates selectedPanel if the session belongs to a different panel

Replace SessionList JSX with PanelList:
  <PanelList
    panels={panels}
    selectedPanelId={selectedPanel?.panel_id ?? null}
    selectedSessionId={selectedSession?.session_id ?? null}
    onPanelSelect={handlePanelSelect}
    onSessionSelect={handleSessionSelect}
    isAnalysing={isAnalysing}
    onAnalyseAll={handleAnalyseAll}
    loading={loading}     ← existing loading state from allSessions fetch
  />

AnalysisTimeline prop update:
  welderDisplayName={selectedSession?.welder_name ?? null}  →  displayContext={selectedPanel?.panel_name ?? null}
  + panelId={selectedPanel?.panel_id ?? null}
  + panelName={selectedPanel?.panel_name ?? null}

WelderTrendChart: stays wired to selectedSession?.welder_id (no change needed)

Empty state text: "Select a panel to begin analysis"
```

#### `my-app/src/components/analysis/AnalysisTimeline.tsx`

```
Prop interface changes:
  - welderDisplayName: string | null
  + displayContext: string | null   (receives panel_name)
  + panelId: string | null
  + panelName: string | null

Internal: pass panelId + panelName down to QualityReportCard.
Header shows displayContext (panel_name) where welderDisplayName was shown.
No changes to SSE logic, agent cards, or progress bar.
```

#### `my-app/src/components/analysis/QualityReportCard.tsx`

```
Prop interface changes:
  - welderDisplayName?: string | null
  + welderDisplayName?: string | null  (RETAIN — still shows "Welder: X" in card header)
  + panelId?: string | null
  + panelName?: string | null

handleExportPdf changes:
  1. Build panel field:
     panel: { id: panelId ?? report.session_id, name: panelName ?? "Panel" }

  2. Build welder_attribution:
     welder_attribution: welderDisplayName ?? null

  3. Add lookup constants (PascalCase keys):

     const CONSEQUENCE_BY_AGENT: Record<string, string> = {
       ThermalAgent:
         "Excessive or deficient heat input can cause grain coarsening in the heat-affected zone, reducing toughness and increasing the risk of HAZ cracking or underbead cracking under service loads.",
       GeometryAgent:
         "Geometric deviations such as undercut, overlap, or incorrect weld profile reduce the effective throat thickness, which can lead to premature fatigue failure or brittle fracture at the joint.",
       ProcessStabilityAgent:
         "Process instability — including arc interruptions, voltage fluctuations, or incorrect wire feed — can introduce porosity, lack of fusion, or incomplete penetration, compromising joint structural integrity.",
     };

     const RATIONALE_BY_AGENT: Record<string, string> = {
       ThermalAgent:
         "This heat excursion places the heat-affected zone outside WPS-specified bounds, indicating insufficient travel speed or pre-heat temperature control.",
       GeometryAgent:
         "The geometric deviation suggests torch angle drift or inconsistent standoff distance, resulting in a weld profile that does not meet dimensional acceptance criteria.",
       ProcessStabilityAgent:
         "The process anomaly reflects inconsistent arc behaviour, typically from parameter drift, contact tip wear, or shielding gas fluctuation.",
     };

     const REJECT_LABEL_BY_AGENT: Record<string, string> = {
       ThermalAgent:   "HEAT EXCEEDANCE",
       GeometryAgent:  "GEOMETRY DEVIATION",
       ProcessStabilityAgent: "PROCESS INSTABILITY",
     };

  4. Enrich specialistRows for PDF payload:
     agentInsights: (specialistRows ?? []).map(row => ({
       ...row,
       disposition_rationale: row.disposition !== "PASS"
         ? RATIONALE_BY_AGENT[row.agent_name] ?? null
         : null,
       consequence: row.disposition !== "PASS"
         ? CONSEQUENCE_BY_AGENT[row.agent_name] ?? null
         : null,
       reject_label: row.disposition !== "PASS"
         ? REJECT_LABEL_BY_AGENT[row.agent_name] ?? null
         : null,
     }))

  5. Score: keep existing hardcoded disposition-based mapping (known limitation; replace
     when WarpReport exposes quality_score from backend)

  6. Keep sending `feedback` (required by route — no change to this field)

  7. Add panel and welder_attribution to payload, remove welder: { name: ... }
```

#### `my-app/src/app/api/welder-report-pdf/route.ts`

```
PDFRequestBody interface changes:
  - welder?: { name?: unknown }
  + panel?: { id?: unknown; name?: unknown }     (required; return 400 if absent)
  + welder_attribution?: string | null

agentInsights item — extend with new optional fields:
  disposition_rationale?: string;
  consequence?: string;
  reject_label?: string;

Validation change:
  - if (!body.welder || typeof body.welder !== "object") → 400
  + if (!body.panel || typeof body.panel !== "object") → 400
  + panelId = String(body.panel.id ?? "").slice(0, 64) || "panel"
  + panelName = String(body.panel.name ?? "").slice(0, 128) || "Panel"
  + welderAttribution = typeof body.welder_attribution === "string"
      ? body.welder_attribution.slice(0, 256)
      : null

feedback stays required — NO change to that validation block.

agentInsights mapping — add passthrough for new fields:
  disposition_rationale: typeof obj.disposition_rationale === "string"
    ? obj.disposition_rationale.slice(0, 500) : undefined,
  consequence: typeof obj.consequence === "string"
    ? obj.consequence.slice(0, 500) : undefined,
  reject_label: typeof obj.reject_label === "string"
    ? obj.reject_label.slice(0, 64) : undefined,

React.createElement call:
  Replace welder prop with panelId, panelName, welderAttribution.

Filename: `${sanitizeFilename(panelId)}-warp-report.pdf`
```

#### `my-app/src/components/pdf/WelderReportPDF.tsx`

```
Props interface changes:
  - welder: { name: string }
  + panelId: string
  + panelName: string
  + welderAttribution: string | null

  agentInsights item — extend with:
    disposition_rationale?: string | null
    consequence?: string | null
    reject_label?: string | null

Layout changes:

TOP BAR (modified):
  - Large panel name where welderName was
  - "Worked by: {welderAttribution}" in small muted text below panel name
  - Score circle stays top-right (unchanged structure)
  - Disposition badge below score circle (unchanged)
  - Rework cost: REMOVE from the standalone hero block; instead render inline beneath the
    disposition badge as small muted text: "Est. Rework: {formatCost(cost)}"
    Cost colour still applied but font size 9 (not 64)

HERO BLOCK (remove):
  The large standalone rework cost hero block (padding 28, font 64) is removed entirely.

REJECTION SUMMARY panel (remove):
  The generic root_cause + narrative panel is removed. Per-agent sections replace it.

AGENT FINDINGS (redesign from side-by-side cards to stacked narrative blocks):
  For each agent in AGENT_ORDER:
    if agent disposition === PASS:
      Compact row: green badge "PASS" + agent display label. No body.
    else (rejected):
      Full narrative block:
        1. Reject badge: View with red background, white Text = reject_label ?? "REJECTED"
           followed by agent display label
        2. "What happened:" label + root_cause text
        3. "In the analysis:" label + disposition_rationale text
        4. "Potential weld risk:" label + consequence text
        5. "Corrective Actions:" label + bullet list from corrective_actions[]

CORRECTIVE ACTIONS global section (remove):
  The global `feedback.feedback_items` corrective actions section is removed.
  Actions now appear per-agent within the narrative blocks above.

FOOTER: unchanged.
```

---

## Quickstart

See [quickstart.md](./quickstart.md) for local development setup and testing steps.

> **Note**: Update `WELDER_PANEL_MAP` in `panel-mapping.ts` with real `welder_id` values from the running backend before testing panel grouping. Run `GET /api/warp/mock-sessions` from the browser network tab to see actual IDs.
