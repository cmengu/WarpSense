# Research: Panel-Centric Analysis & PDF Revamp

**Branch**: `001-panel-analysis-pdf` | **Phase**: 0 — Research | **Date**: 2026-03-26

---

## Decision 1: Panel Concept — Where Does It Live?

**Question**: `MockSession` has no `panel_id` field. How should panels be introduced?

**Decision**: Add `panel_id` (string) and `panel_name` (string) to `MockSession` in the mock data layer. Group sessions by `panel_id` in the sidebar. No new back-end entity or database table is required because sessions already represent discrete welds; a panel is simply a logical grouping of sessions sharing the same physical work-piece.

**Rationale**: The mock data is the current source of truth for sessions. Adding two fields to `MockSession` is the minimum change that supports panel grouping in the sidebar and panel attribution in the PDF without touching back-end services or the SSE pipeline. The analysis per-session (heat, torch, arc) remains unchanged — the panel is the navigation entry point, not a new analysis unit.

**Alternatives considered**:
- Create a separate `Panel` entity managed via API — rejected because it requires a new endpoint and back-end work that is out of scope for a UI/PDF revamp.
- Derive panels from `welder_id` (i.e., one panel per welder) — rejected because it conflates the physical weld panel with the person, which is exactly the problem being solved.

---

## Decision 2: Weld Quality Score (1–100) — Source and Format

**Question**: Where does the 1–100 score come from, and is it already available?

**Decision**: Use `score.total` already sent to the PDF route (and `quality_score` in `WelderTrendPoint`). Display it as `"X / 100"` in a prominent hero position. No new scoring computation is needed.

**Rationale**: `WarpReport.confidence` is a 0–1 float (AI model confidence), not a quality score. The `quality_score` field in `WelderTrendPoint` and the `score.total` field in the PDF request body are the existing quality-on-100 values. The spec explicitly states "no new scoring model is required."

**Alternatives considered**:
- Derive score from `confidence * 100` — rejected because confidence and quality score measure different things (model certainty vs. weld quality).
- Compute score from threshold violation counts — rejected as out of scope; existing score is sufficient.

---

## Decision 3: Humanised Rejection Narrative — Generation Strategy

**Question**: How is the three-part narrative (what happened / what it means / how it may cause a faulty weld) generated? Does it need a new LLM call?

**Decision**: The narrative is assembled from existing agent fields using a deterministic template, not a new LLM call. The three parts map as follows:
- **Part 1 – What happened**: `agentInsights[n].root_cause` (already a plain-English string from the LLM)
- **Part 2 – What this means in the analysis**: `WarpReport.disposition_rationale` (already describes the analytical significance)
- **Part 3 – How this may cause a faulty weld**: Constructed from `primary_defect_categories` + `threshold_violations` — e.g., "Excessive heat input can cause HAZ cracking and reduced joint tensile strength."

The PDF route accepts these as structured fields. The PDF component renders them in the three-part layout. No new streaming step or LLM invocation is needed.

**Rationale**: All three narrative parts are derivable from existing `WarpReport` and `agentInsights` data. The `root_cause` and `disposition_rationale` are already humanised LLM outputs. Only Part 3 requires a mapping from defect category to consequence prose, which is a small deterministic lookup (e.g., heat → HAZ cracking; geometry → porosity; process → lack-of-fusion).

**Alternatives considered**:
- Add a new `/api/humanise-rejection` LLM endpoint — rejected as out of scope and latency-adding for PDF generation.
- Show raw `root_cause` + `disposition_rationale` unchanged — rejected because the spec requires the specific three-part structure for non-expert readability.

---

## Decision 4: Analysis Sidebar Refactor — Component Strategy

**Question**: Should `SessionList.tsx` be modified in-place, or should a new `PanelList.tsx` be created?

**Decision**: Create a new `PanelList.tsx` component. `SessionList.tsx` is retained for any views that still need session-level listing (e.g., internal debug views). `PanelList` replaces `SessionList` in `analysis/page.tsx`.

**Rationale**: The data shape and interaction model of a panel list differs enough from a session list (grouped entries, welder attribution, expand/collapse per panel) that in-place modification would make `SessionList` overly complex. A new component keeps concerns separated and avoids regressions in other views that may reference `SessionList`.

**Alternatives considered**:
- Modify `SessionList` with a `groupByPanel` prop — rejected because the rendering logic diverges significantly; a prop flag would create a conditional-heavy component.

---

## Decision 5: PDF Component — Rename or Modify In-Place?

**Question**: Should `WelderReportPDF.tsx` be renamed to `PanelReportPDF.tsx`?

**Decision**: Modify `WelderReportPDF.tsx` in-place. The file path is an implementation detail not exposed to users. Renaming requires updating all import paths and the API route, adding churn for no user-visible benefit. The component's props interface is updated to accept `panel` as the primary subject (replacing the `welder` hero).

**Rationale**: In-place modification minimises refactor scope. The component already has the structural sections needed (top bar, hero, agent insights, corrective actions); only the layout and data shape change.

**Alternatives considered**:
- Rename to `PanelReportPDF.tsx` — rejected to minimise diff scope.

---

## Decision 6: Quick Visual Reject Indicator — Approach

**Question**: How is the "quick visual indicator" for agent rejection implemented in the PDF?

**Decision**: Use a coloured icon/badge row above each agent narrative section in the PDF. Since `@react-pdf/renderer` does not support SVG icons natively, use Unicode characters or a small coloured rectangle with a label (e.g., `🔴 HEAT EXCEEDANCE`, `⚠ GEOMETRY DEVIATION`, `⚡ PROCESS INSTABILITY`) rendered as a styled `View` + `Text` block.

**Rationale**: `@react-pdf/renderer` renders to PDF primitives (no DOM, no SVG). Styled `View` blocks with background colour + bold `Text` label are the most reliable visual indicators in this constraint. Colours mirror the existing app palette (red for rejection, amber for conditional).

**Alternatives considered**:
- Embed an SVG icon as a data URI image — rejected because SVG-to-PNG conversion is not available server-side in this stack without additional dependencies.
- Use emoji in PDF text — acceptable as a fallback; PDF renderers may substitute glyphs but this is lower-risk than added dependencies.
