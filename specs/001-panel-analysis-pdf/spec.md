# Feature Specification: Panel-Centric Analysis & PDF Revamp

**Feature Branch**: `001-panel-analysis-pdf`
**Created**: 2026-03-26
**Status**: Draft
**Input**: User description: "Revamp the Analysis page to show weld panels instead of welders in the sidebar. Revamp PDF report to be panel-centric with a 1-100 weld score, compact rework cost, humanised agent rejection summaries (what happened / what it means / how it may cause a faulty weld), quick visual reject indicators, and corrective actions. Improve overall visual appeal."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Analysis by Panel (Priority: P1)

A quality supervisor opens the Analysis page and sees a list of weld panels in the sidebar rather than a list of welders. Each panel entry shows which senior welder(s) worked on it. Clicking a panel opens its full analysis — heat profile, torch profile, arc stability — with no change to the content of those sub-sections.

**Why this priority**: The panel is the unit of quality accountability. Showing welders as the primary axis made it hard to trace defects to specific physical work pieces. This is the core structural change the rest of the feature depends on.

**Independent Test**: Navigate to the Analysis page. Confirm the sidebar lists panel identifiers. Confirm each panel entry displays the name(s) of the senior welder(s) who worked it. Click a panel and confirm the heat, torch, and arc analysis sections load exactly as before.

**Acceptance Scenarios**:

1. **Given** the Analysis page is open, **When** the sidebar renders, **Then** each item represents a weld panel (not a welder session), and each item shows the senior welder name(s) associated with that panel.
2. **Given** a panel is selected in the sidebar, **When** the analysis view loads, **Then** heat profile, torch profile, and arc stability data are displayed with no change to layout or content compared to the previous welder-centric view.
3. **Given** a panel has been worked on by multiple senior welders, **When** the panel entry is shown, **Then** all contributing welder names are visible.

---

### User Story 2 - Download a Panel-Centric PDF Report (Priority: P2)

A quality manager downloads a PDF report for a specific weld panel. The PDF shows the panel identifier as the primary subject, the overall weld quality score out of 100, a compact estimated rework cost, and — if any agent flagged a rejection — a humanised rejection narrative for each flagging agent.

**Why this priority**: The PDF is the deliverable shared with clients and auditors. It must reflect the new panel-centric model and be professional enough for external review.

**Independent Test**: Download a PDF for a panel with at least one agent rejection. Confirm the PDF header identifies the panel, shows a score out of 100, shows rework cost in a compact secondary position, and contains a three-part rejection narrative per flagging agent.

**Acceptance Scenarios**:

1. **Given** a panel PDF is downloaded, **When** it is opened, **Then** the primary identifier is the panel name/ID, and the welder name(s) appear as attribution (e.g., "Worked by: [Name]").
2. **Given** the PDF renders, **When** the weld quality score is displayed, **Then** it appears as a score out of 100 (e.g., "82 / 100") in a visually prominent position on the first page.
3. **Given** the PDF renders, **When** the estimated rework cost section is present, **Then** it is compact and secondary in visual hierarchy — not the dominant element.
4. **Given** an agent flagged a rejection, **When** the rejection summary renders, **Then** for each flagging agent there is a narrative block containing: (a) what happened, (b) what this means in the analysis, (c) how this may result in a faulty weld.
5. **Given** no agent flagged a rejection, **When** the PDF renders, **Then** no rejection summary section appears and the report communicates a clear pass in plain language.

---

### User Story 3 - Understand Agent Rejection at a Glance (Priority: P3)

A trainee welder or site supervisor reads the rejection summary for a panel and can immediately understand what went wrong, why it matters, and what could happen to the weld if left uncorrected. A quick visual indicator per agent conveys the rejection reason before they read the full narrative. Corrective actions follow the narrative unchanged.

**Why this priority**: Humanising the rejection output makes the report actionable for a wider, non-expert audience without changing the underlying agent findings or corrective action content.

**Independent Test**: Open a PDF for a rejected panel. For each flagging agent, confirm there is a plain-language narrative covering all three parts, a visual reject indicator, and the corrective actions list.

**Acceptance Scenarios**:

1. **Given** an agent flagged a rejection, **When** its section renders, **Then** the narrative opens with a plain-English statement of what happened, followed by what this means in the analysis, followed by the potential weld failure consequence.
2. **Given** multiple agents flagged rejections, **When** their sections render, **Then** each follows the same three-part narrative structure independently.
3. **Given** any agent's rejection section is displayed, **When** the visual reject indicator is shown, **Then** it communicates the primary rejection reason at a glance without requiring the reader to parse the full narrative first.
4. **Given** corrective actions are available, **When** the agent section renders, **Then** they are listed after the narrative, with no changes to their content or format.

---

### Edge Cases

- What happens when a panel has no senior welder assigned — does it still appear in the sidebar, and how is attribution displayed?
- How does the system handle a panel where all three agents pass — is there a visible "no issues found" confirmation on the PDF?
- How does the PDF render if the rework cost cannot be calculated (e.g., missing cost data)?
- What happens when a panel has only trainer welder sessions and no senior welder sessions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Analysis page sidebar MUST list weld panels as the primary navigation items, replacing the current welder-centric list.
- **FR-002**: Each panel entry in the sidebar MUST display the name(s) of the senior welder(s) who worked on that panel, shown beneath or alongside the panel identifier.
- **FR-003**: Selecting a panel in the sidebar MUST open the heat profile, torch profile, and arc stability analysis content with no changes to the content or layout of those sub-sections.
- **FR-004**: The PDF report MUST identify the weld panel as the primary subject (panel name/ID in the header), with welder name(s) displayed as attribution.
- **FR-005**: The PDF MUST display a weld quality score as a value out of 100 (e.g., "78 / 100") in a visually prominent position on the first page.
- **FR-006**: The estimated rework cost MUST be presented in a compact, visually secondary position in the PDF — not the dominant element on the page.
- **FR-007**: For each AI agent that flagged a rejection, the PDF MUST include a three-part humanised narrative: (1) what happened, (2) what this means in the analysis, (3) how this may result in a faulty weld.
- **FR-008**: Each agent rejection section MUST include a quick visual indicator (e.g., icon, badge, or inline graphic) summarising the rejection reason.
- **FR-009**: Corrective actions MUST be retained and listed after the narrative in each agent rejection section, with no changes to their content.
- **FR-010**: If no agent flagged a rejection, the PDF MUST communicate a clear pass without displaying a rejection summary section.
- **FR-011**: The overall visual design of the Analysis page and the PDF report MUST be refined to appear professional and uncluttered, suitable for external stakeholder review.

### Key Entities

- **Weld Panel**: The physical unit of work — a section of structure that is welded. Has an identifier, one or more assigned welders, and one or more weld sessions. Primary subject of both the Analysis page and the PDF.
- **Senior Welder**: The operator responsible for the weld. Attributed to one or more panels. Name appears under the panel entry in the sidebar and in the PDF attribution line.
- **Weld Session**: A time-bounded welding event on a panel, containing heat, torch, and arc data. Multiple sessions may exist per panel.
- **Agent Finding**: The output of one of three AI quality agents. Contains pass/fail status, rejection reason, and corrective actions.
- **Weld Quality Score**: A numeric score from 1 to 100 representing the overall quality of the weld on a panel.
- **Estimated Rework Cost**: A monetary or effort estimate for correcting defects on a panel, derived from agent findings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A quality supervisor can identify which welder worked on a specific panel within 10 seconds of landing on the Analysis page, without opening any panel detail.
- **SC-002**: A non-technical reader (site supervisor or trainee) can understand what went wrong and its consequence by reading the rejection narrative — validated by a comprehension check or stakeholder sign-off.
- **SC-003**: The PDF report is considered presentation-ready by the project lead with no redesign requested after the first external review.
- **SC-004**: All three agent rejection sections, when present, follow the consistent three-part narrative structure with 100% coverage — no part missing from any agent's section.
- **SC-005**: The weld quality score is visible without scrolling on the first page of the PDF for all panel reports.

## Assumptions

- The three AI agents and their underlying finding data (rejection reason, corrective actions) do not change — only their presentation changes.
- The weld quality score (1–100) is already computed or can be derived from existing agent output; no new scoring model is required.
- The estimated rework cost is already calculated and stored; the change is purely presentational.
- Trainer welder sessions may still be accessible within the panel detail view, but the primary sidebar navigation is panel-first; trainer sessions are not surfaced at the top level.
- A "panel" maps to a traceable identifier already present in the data model; no new data collection is required.
- The corrective actions content and format are retained verbatim; no editorial changes to corrective action text.
- The report covers one panel per PDF download; multi-panel batch PDFs are out of scope.
