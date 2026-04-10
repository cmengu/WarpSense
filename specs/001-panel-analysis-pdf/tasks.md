# Tasks: Panel-Centric Analysis & PDF Revamp

**Input**: Design documents from `/specs/001-panel-analysis-pdf/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/pdf-api.md ✓, quickstart.md ✓

**Tests**: Not requested in spec — no test tasks generated.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

> **Conflicts resolved**: 7 conflicts between original plan and actual codebase were corrected in plan.md.
> Key changes: sessions from API (no static constant to edit), panel enrichment via client-side mapping,
> agent names are PascalCase, `feedback` stays required in route, score stays hardcoded,
> per-agent rationale uses a template, panel context threaded as props.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P]-marked tasks (different files, no blocking dependency)
- **[Story]**: Which user story this task belongs to ([US1], [US2], [US3])

---

## Phase 1: Setup

**Purpose**: Confirm project is ready; discover real welder_id values for panel mapping.

- [ ] T001 Confirm branch `001-panel-analysis-pdf` is checked out and `npm run dev` starts in `my-app/`; open browser DevTools Network tab, load `/analysis`, and record the actual `welder_id` values returned by `GET /api/warp/mock-sessions` — these are needed for T002

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Panel mapping and grouping logic that all three user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Create `my-app/src/lib/panel-mapping.ts` with: (a) `WeldPanel` interface (`panel_id`, `panel_name`, `welder_names: string[]`, `sessions: MockSession[]`, `panel_disposition: WarpDisposition | null`); (b) `WELDER_PANEL_MAP` constant keyed by the real `welder_id` values found in T001 — assign at least 3 distinct panels across the available welders (e.g., expert welder_ids get `"PANEL-A01"/"Deck Panel A-01"`, novice welder_ids get `"PANEL-B02"/"Hull Panel B-02"`, etc.); (c) `groupSessionsByPanel(sessions: MockSession[]): WeldPanel[]` — for each session, look up `WELDER_PANEL_MAP[session.welder_id]` and fall back to `{ panel_id: session.welder_id, panel_name: session.welder_name }` if not found, then group by `panel_id`, sort panels alphabetically by `panel_id`, sort sessions within each panel by `started_at` descending, compute `panel_disposition` as worst-case (`REWORK_REQUIRED` > `CONDITIONAL` > `PASS` > null), derive `welder_names` as distinct welder_name values; import `MockSession` and `WarpDisposition` from `@/types/warp-analysis`

**Checkpoint**: `groupSessionsByPanel([])` returns `[]` and `groupSessionsByPanel(sessions)` returns WeldPanel[] with correct grouping. TypeScript compiles.

---

## Phase 3: User Story 1 — Browse Analysis by Panel (Priority: P1) 🎯 MVP

**Goal**: Sidebar shows weld panels as the primary navigation; each panel entry displays contributing welder name(s); clicking a panel auto-selects its first session for analysis; heat/torch/arc analysis content unchanged.

**Independent Test**: Open `/analysis`. Sidebar shows panel names with welder attribution. Click a panel — AnalysisTimeline loads for the first session. Click a different session within the panel — AnalysisTimeline loads for that session.

### Implementation for User Story 1

- [x] T003 [US1] Create `my-app/src/components/analysis/PanelList.tsx` — props: `panels: WeldPanel[]`, `selectedPanelId: string | null`, `selectedSessionId: string | null`, `onPanelSelect: (panel: WeldPanel) => void`, `onSessionSelect: (session: MockSession) => void`, `isAnalysing: boolean`, `onAnalyseAll: () => void`, `loading: boolean`; while loading render 5 skeleton rows (same pulse pattern as SessionList); each panel entry shows `panel_name` in bold + `panel_name` left-border colour by `panel_disposition` + welder_names comma-joined in muted small text + disposition badge; clicking a panel header calls `onPanelSelect` and expands session list; within expanded panel render each session as a button row showing formatted timestamp, `arc_type` tag, disposition badge; selected session gets amber left-border + surface-2 bg; "Analyse All" button at top (disabled while `isAnalysing`); import `WeldPanel` from `@/lib/panel-mapping` and `MockSession`, `WarpDisposition` from `@/types/warp-analysis` (depends on T002)
- [x] T004 [US1] Update `my-app/src/app/(app)/analysis/page.tsx` — add imports for `groupSessionsByPanel`, `WeldPanel` from `@/lib/panel-mapping` and `PanelList` from `@/components/analysis/PanelList`; remove `SessionList` import; add `selectedPanel: WeldPanel | null` state; derive `panels` via `useMemo(() => groupSessionsByPanel(allSessions), [allSessions])`; add `handlePanelSelect(panel: WeldPanel)` — sets `selectedPanel`, sets `selectedSession` to `panel.sessions[0] ?? null`, then calls the **existing** `handleSessionSelect(panel.sessions[0])` so the `fetchWarpReport` pre-check still runs (do NOT call `startStream` directly — the pre-check that fetches a cached report before streaming must be preserved for all session activations including panel clicks); the existing `handleSessionSelect` is wired to `onSessionSelect` in PanelList unchanged — session row clicks within an expanded panel also run the full pre-check; replace `<SessionList .../>` with `<PanelList panels={panels} selectedPanelId={selectedPanel?.panel_id ?? null} selectedSessionId={selectedSession?.session_id ?? null} onPanelSelect={handlePanelSelect} onSessionSelect={handleSessionSelect} isAnalysing={isAnalysing} onAnalyseAll={handleAnalyseAll} loading={loading} />`; update `AnalysisTimeline` props: rename `welderDisplayName` → `displayContext` (pass `selectedPanel?.panel_name ?? null`), add `panelId={selectedPanel?.panel_id ?? null}`, add `panelName={selectedPanel?.panel_name ?? null}`; update empty state text to "Select a panel to begin analysis"; **WelderTrendChart**: stays wired to `selectedSession?.welder_id` — add a small caption label beneath the chart div (e.g., `<span className="font-mono text-[8px] text-[var(--warp-text-dim)] px-2">Trend: {selectedSession?.welder_name}</span>`) so the chart is contextually labelled when a panel has multiple welders; **known limitation — Analyse All queue**: `handleAnalyseAll` fetches sessions as a flat list from the API and queues them in API order, not panel order — this is pre-existing behaviour; do not change it, just ensure `setSelectedPanel` is updated when `handleStreamComplete` advances the queue by finding the panel that contains the newly-selected session (use `panels.find(p => p.sessions.some(s => s.session_id === nextSession.session_id)) ?? null`) (depends on T003)
- [x] T005 [US1] Update `my-app/src/components/analysis/AnalysisTimeline.tsx` — rename prop `welderDisplayName: string | null` to `displayContext: string | null`; add props `panelId: string | null` and `panelName: string | null`; pass `panelId` and `panelName` down to `QualityReportCard`; update `AnalysisTimelineProps` interface accordingly; in JSX replace `welderDisplayName={welderDisplayName}` on `QualityReportCard` with the new props; update the header subtitle to use `displayContext` where `welderDisplayName` appeared; fix the call site in page.tsx (already done in T004) (depends on T004)
- [x] T006 [US1] Update `my-app/src/components/analysis/QualityReportCard.tsx` — add props `panelId?: string | null` and `panelName?: string | null` to `QualityReportCardProps` interface; keep `welderDisplayName` prop unchanged (still shows "Welder: X" in card header); no other changes in this task — PDF payload changes are in US2/US3 (depends on T005)

**Checkpoint**: Sidebar shows panels. Clicking a panel loads AnalysisTimeline. US1 fully functional and independently testable.

---

## Phase 4: User Story 2 — Download Panel-Centric PDF Report (Priority: P2)

**Goal**: PDF identifies weld panel as primary subject; welder name shown as attribution; score displayed as "X / 100" prominently; rework cost compact and inline; no large hero rework block; overall professional layout.

**Independent Test**: Click "Export PDF" on a completed report. PDF header shows panel name/ID, welder attribution, large score "X / 100", compact inline rework cost, clean layout.

### Implementation for User Story 2

- [x] T007 [P] [US2] Update `my-app/src/app/api/welder-report-pdf/route.ts` — in `PDFRequestBody`: replace `welder?: { name?: unknown }` with `panel?: { id?: unknown; name?: unknown }` and add `welder_attribution?: string | null`; validate `body.panel` present (return 400 if absent); extract `panelId = String(body.panel?.id ?? "").slice(0, 64) || "panel"` and `panelName = String(body.panel?.name ?? "").slice(0, 128) || "Panel"`; extract `welderAttribution = typeof body.welder_attribution === "string" ? body.welder_attribution.slice(0, 256) : null`; extend `agentInsights` item schema to also accept `disposition_rationale?: string`, `consequence?: string`, `reject_label?: string` — pass these through in the `.map()` with same 500-char truncation; **dead code cleanup**: delete the `toWelderName` function defined in `route.ts` (lines ~68–72) — it was only used to extract `welderName` from `body.welder.name`, which no longer exists; also delete the `const welder = { name: welderName }` line and the `welderName` variable entirely; `WelderReportPDF.tsx` exports its own `toWelderName` separately and is unaffected; update `React.createElement(WelderReportPDF, {...})` call to pass `panelId`, `panelName`, `welderAttribution` instead of `welder`; update filename to `${sanitizeFilename(panelId)}-warp-report.pdf`; keep `feedback` validation unchanged (still required)
- [x] T008 [P] [US2] Update `my-app/src/components/pdf/WelderReportPDF.tsx` props and layout — (a) Props: replace `welder: { name: string }` with `panelId: string`, `panelName: string`, `welderAttribution: string | null`; extend `agentInsights` item type with `disposition_rationale?: string | null`, `consequence?: string | null`, `reject_label?: string | null`; (b) Top bar: replace `welderName` with `panelName` (same large font, same style), add `welderAttribution` as a small muted line "Worked by: {welderAttribution}" below; (c) Rework cost hero block: remove the large standalone hero (`paddingVertical: 28, fontSize: 64`); instead render rework cost as a compact inline text beneath the disposition badge in the top bar area (fontSize 9, muted colour); (d) Keep score circle and disposition badge in top-right unchanged; (e) Generic "Rejection Summary" panel block: remove entirely; (f) `AGENT_ORDER` and `agentDisplayLabel` are unchanged; note: agent narrative (US3) is the next task — for now leave the agent findings section layout as-is (side-by-side cards) so US2 is independently testable; (g) Remove global corrective actions section (`feedback.feedback_items` block) — actions will move per-agent in US3
- [x] T009 [US2] Update `my-app/src/components/analysis/QualityReportCard.tsx` `handleExportPdf` — at the start of `handleExportPdf`, add a guard: `if (!panelId || !panelName) { logWarn("[QualityReportCard]", "PDF export called without panel context — panelId or panelName is null; this is a prop threading bug", { sessionId: report.session_id }); }` (use the existing `logWarn` import); change payload: replace `welder: { name: welderDisplayName ?? "Unknown" }` with `panel: { id: panelId ?? report.session_id, name: panelName ?? "Panel" }` — the `?? report.session_id` and `?? "Panel"` fallbacks are last-resort only and should never fire if prop threading is correct; add `welder_attribution: welderDisplayName ?? null`; keep `feedback` field unchanged (route still requires it); keep `score`, `narrative`, `rework_cost_usd`, `disposition`, `agentInsights`, `sessionDate` unchanged for now (US3 enriches agentInsights); update download filename to `${panelId ?? report.session_id}-report.pdf` (depends on T007, T008, T006)

**Checkpoint**: Export PDF → panel name is primary, score "X / 100" prominent, rework cost compact, attribution visible, no large orange hero block. US2 fully functional.

---

## Phase 5: User Story 3 — Agent Rejection at a Glance (Priority: P3)

**Goal**: Each rejecting agent's section in the PDF shows a visual reject badge + three-part narrative (what happened / in the analysis / potential weld risk) + corrective actions. Passing agents show only a compact PASS badge.

**Independent Test**: Export PDF for a session with at least one agent rejection. Confirm: red reject badge with label above agent section, three labelled narrative parts, corrective actions list. Passing agents show only green PASS badge.

### Implementation for User Story 3

- [x] T010 [P] [US3] Update `my-app/src/components/analysis/QualityReportCard.tsx` — add three lookup constants at module scope (PascalCase keys to match backend agent names): `CONSEQUENCE_BY_AGENT` (one consequence string per agent: ThermalAgent, GeometryAgent, ProcessStabilityAgent — use prose from plan.md), `RATIONALE_BY_AGENT` (one rationale template per agent — use prose from plan.md), `REJECT_LABEL_BY_AGENT` (`ThermalAgent → "HEAT EXCEEDANCE"`, `GeometryAgent → "GEOMETRY DEVIATION"`, `ProcessStabilityAgent → "PROCESS INSTABILITY"`); in `handleExportPdf` enrich the `agentInsights` payload: for each `specialistRows` entry, add `disposition_rationale: row.disposition !== "PASS" ? RATIONALE_BY_AGENT[row.agent_name] ?? null : null`, `consequence: row.disposition !== "PASS" ? CONSEQUENCE_BY_AGENT[row.agent_name] ?? null : null`, `reject_label: row.disposition !== "PASS" ? REJECT_LABEL_BY_AGENT[row.agent_name] ?? null : null`; also include `corrective_actions: row.corrective_actions` in the agentInsights entry (depends on T009 being in place)
- [x] T011 [P] [US3] Update `my-app/src/components/pdf/WelderReportPDF.tsx` agent findings section — **REPLACE (not extend) the `insightMap` type and population loop entirely**. Current code to delete (lines ~207–213): `const insightMap: Record<string, { disposition?: string; root_cause?: string }> = {}; for (const row of agentInsights ?? []) { insightMap[row.agent_name] = { disposition: row.disposition, root_cause: row.root_cause }; }`. Replace with: `interface AgentInsight { disposition?: string; root_cause?: string; disposition_rationale?: string | null; consequence?: string | null; reject_label?: string | null; corrective_actions?: string[]; } const insightMap: Record<string, AgentInsight> = {}; for (const row of agentInsights ?? []) { insightMap[row.agent_name] = { disposition: row.disposition, root_cause: row.root_cause, disposition_rationale: row.disposition_rationale, consequence: row.consequence, reject_label: row.reject_label, corrective_actions: row.corrective_actions }; }`. Then replace the agent findings `<View style={{ flexDirection: "row" }}>` side-by-side card layout with stacked narrative blocks (remove the `flexDirection: "row"` wrapper and `flex: 1 / marginRight` per-card styles): for each agent in `AGENT_ORDER`: if insight absent or disposition is PASS, render a compact single row: green badge View (`backgroundColor: COLORS.GREEN, paddingH: 6, paddingV: 2, borderRadius: 3, alignSelf: "flex-start"`) + agent display label Text beside it; if disposition is not PASS, render a full block with `marginBottom: 12, backgroundColor: COLORS.PANEL, borderRadius: 6, borderWidth: 1, borderColor: COLORS.BORDER, padding: 10` containing: (1) View row with red badge (`backgroundColor: COLORS.RED`) Text = `sanitizeText(insight.reject_label ?? "REJECTED")` + agent display label Text beside it; (2) Text "WHAT HAPPENED" muted uppercase + paragraph Text `sanitizeText(insight.root_cause ?? "")` with `lineHeight: 1.4, fontSize: 9`; (3) Text "IN THE ANALYSIS" muted uppercase + paragraph Text `sanitizeText(insight.disposition_rationale ?? "")`; (4) Text "POTENTIAL WELD RISK" muted uppercase + paragraph Text `sanitizeText(insight.consequence ?? "")`; (5) if `insight.corrective_actions?.length > 0`: Text "CORRECTIVE ACTIONS" muted uppercase + map over actions as numbered rows (same style as existing corrective actions section); also **remove the exported `toWelderName` function** from `WelderReportPDF.tsx` if it is no longer referenced anywhere after the `welder` prop is removed — check usages with grep before deleting (depends on T008)

**Checkpoint**: PDF shows stacked per-agent narrative blocks with badges for rejected agents, PASS badge for passing agents. US3 fully functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Visual refinement; final validation.

- [x] T012 [P] Visual polish pass on `my-app/src/components/analysis/PanelList.tsx` — review spacing, font weights, colour tokens, hover/selected states; ensure the panel sidebar feels professional and consistent with the existing app design language (Tailwind CSS only)
- [x] T013 [P] Visual polish pass on `my-app/src/components/pdf/WelderReportPDF.tsx` — review section spacing, typography scale, colour use, and visual hierarchy across the redesigned layout; confirm the PDF is presentation-ready on LETTER page dimensions with no content overflow or cramped sections
- [x] T014 Validate end-to-end flow using `specs/001-panel-analysis-pdf/quickstart.md` test scenarios — run through every scenario, confirm all acceptance criteria from spec.md are met; also confirm `feedback` field is still accepted by the route (regression check for C3)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (needs real welder_id values) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2
- **US2 (Phase 4)**: Depends on Phase 2 (also benefits from US1 prop threading for panelId/panelName context, so implement after US1)
- **US3 (Phase 5)**: Depends on US2 (extends the PDF layout established in US2)
- **Polish (Phase 6)**: Depends on US1, US2, US3

### Within Each Phase

- T007 and T008 are [P] — different files (route.ts vs WelderReportPDF.tsx)
- T010 and T011 are [P] — different files (QualityReportCard.tsx vs WelderReportPDF.tsx)
- T012 and T013 are [P] — different files

### Key Sequential Dependency

T005 (AnalysisTimeline prop change) → T006 (QualityReportCard new props) → T009 (PDF payload update) → T010 (enrichment lookups)
These must run in order as each adds props/data that the next task consumes.

---

## Parallel Execution Examples

### Phase 4 (US2)
```
T007 (route.ts)           ──┐
                            ├──→ T009 (QualityReportCard payload)
T008 (WelderReportPDF.tsx) ─┘
```

### Phase 5 (US3)
```
T010 (QualityReportCard lookups) ──┐
                                   ├──→ (validate together)
T011 (WelderReportPDF narrative)  ─┘
```

### Phase 6 (Polish)
```
T012 (PanelList polish) ──┐
                          ├──→ T014 (validation)
T013 (PDF polish)        ──┘
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 — discover welder_id values
2. T002 — create panel-mapping.ts
3. T003–T006 — panel sidebar
4. **STOP and VALIDATE** — panel navigation works
5. Demo panel-centric sidebar to stakeholders

### Incremental Delivery

1. Setup + Foundational (T001–T002) → mapping ready
2. US1 (T003–T006) → panel sidebar MVP, demo-able
3. US2 (T007–T009) → professional panel PDF, shareable externally
4. US3 (T010–T011) → humanised narratives, full feature complete
5. Polish (T012–T014) → visual refinement and validation sign-off

---

## Notes

- Do NOT add `panel_id`/`panel_name` to `MockSession` type — sessions come from the backend API. Use the panel-mapping.ts approach instead.
- Agent names are PascalCase (`ThermalAgent`, `GeometryAgent`, `ProcessStabilityAgent`) — not snake_case.
- `feedback` field in route.ts stays required — do not remove its validation.
- Score (1–100) is hardcoded by disposition in `QualityReportCard` — this is a known limitation, not a bug to fix.
- `handleSessionSelect` pre-check (`fetchWarpReport` before `startStream`) must run for ALL session activations — panel header click, session row click, and Analyse All queue advancement. Do not bypass it.
- `handleAnalyseAll` queues sessions in flat API order, not panel order — known limitation; do not refactor.
- `WelderTrendChart` shows one welder's trend at a time (the selected session's welder) — add a name label so it stays contextual when a panel has multiple welders.
- `toWelderName` is defined in both `route.ts` and exported from `WelderReportPDF.tsx`. After T007 removes `welder` from the route, delete `route.ts`'s local copy. After T011 removes `welder` from the PDF props, grep for usages of `WelderReportPDF.toWelderName` before deleting the export.
- `panelId`/`panelName` should never be null at PDF export time — if they are, it indicates a prop threading bug (C6). The `logWarn` guard in T009 makes this visible in the console.
- `[P]` tasks = different files, safe to implement simultaneously.
- Commit after each phase checkpoint to preserve working increments.
