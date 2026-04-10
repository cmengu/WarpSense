# Quickstart: Panel-Centric Analysis & PDF Revamp

**Branch**: `001-panel-analysis-pdf` | **Date**: 2026-03-26

---

## Prerequisites

- Node.js 18+ installed
- Repo cloned and on branch `001-panel-analysis-pdf`
- Back-end services running (WARP analysis API, SSE endpoint)

---

## Local Development

```bash
cd my-app
npm install          # no new dependencies required
npm run dev          # starts Next.js dev server at localhost:3000
```

Navigate to `http://localhost:3000/analysis` to see the Analysis page.

---

## Testing the Analysis Page Changes

1. Open `http://localhost:3000/analysis`
2. Confirm the sidebar shows **panel names** (not welder names at the top level)
3. Confirm each panel entry shows the welder name(s) beneath the panel name
4. Click a panel — confirm it expands to show sessions, and the first session is auto-selected for analysis
5. Click a session within the panel — confirm AnalysisTimeline loads for that session
6. Verify heat profile, torch profile, and arc stability content is unchanged

---

## Testing the PDF Report

1. Run an analysis on any session (or use a session with a pre-existing report)
2. Click **Download PDF** in the QualityReportCard
3. Open the downloaded PDF and verify:
   - **Header**: Panel name/ID is the primary label; welder name appears as "Worked by: ..." attribution
   - **Score**: Displayed as "X / 100" in a large, prominent position on page 1
   - **Rework cost**: Appears as a small, compact inline element — not the dominant block
   - **Agent findings** (if any agent rejected):
     - Visual reject badge above the agent section (e.g., "HEAT EXCEEDANCE")
     - Three-part narrative: "What happened:", "In the analysis:", "Potential weld risk:"
     - Corrective actions listed after the narrative
   - **Passing agents**: Shown as a compact green "PASS" badge — no narrative

---

## Adding Panel Data to Mock Sessions

To test multi-session panels, update the mock sessions array in:
```
my-app/src/lib/mock-sessions.ts   (or wherever MOCK_SESSIONS is defined)
```

Add `panel_id` and `panel_name` to each session. Example:
```typescript
{ session_id: "s-001", panel_id: "PANEL-A01", panel_name: "Deck Panel A-01", welder_name: "Ahmad Razif", ... },
{ session_id: "s-002", panel_id: "PANEL-A01", panel_name: "Deck Panel A-01", welder_name: "Ahmad Razif", ... },
{ session_id: "s-003", panel_id: "PANEL-B02", panel_name: "Hull Panel B-02", welder_name: "Lee Wei", ... },
```

---

## Testing PDF Generation via API (optional)

```bash
curl -X POST http://localhost:3000/api/welder-report-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "panel": { "id": "PANEL-A01", "name": "Deck Panel A-01" },
    "welder_attribution": "Ahmad Razif",
    "score": { "total": 78 },
    "disposition": "REWORK_REQUIRED",
    "rework_cost_usd": 1250,
    "agentInsights": [{
      "agent_name": "thermal_agent",
      "disposition": "REWORK_REQUIRED",
      "root_cause": "Heat input spiked to 2.4 kJ/mm at 4m12s.",
      "disposition_rationale": "The thermal excursion places the HAZ outside safe bounds.",
      "consequence": "Excessive heat input can cause grain coarsening and HAZ cracking.",
      "reject_label": "HEAT EXCEEDANCE",
      "corrective_actions": ["Reduce travel speed", "Verify pre-heat temperature"]
    }]
  }' \
  --output test-report.pdf
open test-report.pdf
```
