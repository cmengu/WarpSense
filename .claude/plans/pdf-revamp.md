# PDF Report Revamp — Supervisor/Investor-Grade Rejection Document

**Overall Progress:** `0%` (0/3 steps done)

---

## TLDR

The existing `WelderReportPDF` is a generic coaching document (compliance table, score trend chart, coach feedback). Supervisors and investors need to see immediately: **why this weld was rejected**, **what it costs**, and **what each AI agent found**. This plan replaces the PDF layout with a hero rework-cost block, a rejection summary, 3 agent findings panels, and a corrective actions list. The Export PDF button and all surrounding infrastructure (route, component, API) stay identical — only the visual content changes.

---

## Architecture Overview

**The problem this plan solves:**
- `WelderReportPDF.tsx` shows compliance badges, a coach narrative, and a score trend chart — none of which communicate the rejection reason or business cost to a supervisor or investor at a glance.
- `handleExportPdf` in `QualityReportCard.tsx` does not send `disposition`, `rework_cost_usd`, or `agentInsights` (the parsed 3-agent LLM findings) to the PDF route.
- `route.ts` does not accept or validate those three fields.

**Pattern applied:** DTO pass-through. `QualityReportCard` (caller) assembles the DTO from its already-computed state (`specialistRows`, `report`); the route validates and forwards; `WelderReportPDF` renders. Each layer owns exactly one concern — no logic shared across layers.

**What stays unchanged:**
- The Export PDF button location and `onClick` handler (`QualityReportCard.tsx` line 468)
- `captureChartToBase64` import is removed (chart no longer in PDF) but the rest of `QualityReportCard.tsx` is untouched
- `/api/welder-report-pdf` route path, method, and response contract (still returns `application/pdf`)
- All other props accepted by `route.ts` and `WelderReportPDF` (welder, score, feedback, narrative, sessionDate, etc.) remain — new fields are additive

**What this plan changes:**
- `WelderReportPDF.tsx` — completely new layout (same file, new function body + extended props interface). Removes: compliance, chart, certifications, coach feedback. Adds: hero cost, rejection summary, agent findings, corrective actions.
- `route.ts` — 3 new optional fields in `PDFRequestBody`; corresponding extraction + pass-through to `React.createElement`.
- `QualityReportCard.tsx` — `handleExportPdf` sends `rework_cost_usd`, `disposition`, `agentInsights`; removes `chartDataUrl` (no longer rendered); updates `score.total` to a meaningful 85/55/30 mapping; adds `specialistRows` to callback deps.

**Critical decisions:**

| Decision | Alternative | Why rejected |
|---|---|---|
| Complete replacement of `WelderReportPDF` function body | Incremental section adds | The dropped sections (compliance, chart, certifications) are deeply nested — surgical removal produces more diff than a clean rewrite |
| `agentInsights` sourced from `specialistRows` (already parsed in component) | Re-parse `llm_raw_response` in route | `specialistRows` is already validated and typed; parsing twice is wasteful and the route should not contain business logic |
| Fallback agent panel shows "—" when `agentInsights` is null | Hide panel entirely | Supervisors must know all 3 agents ran; a "—" cell signals missing data, not a missing agent |
| Remove `captureChartToBase64` call entirely | Keep it, just stop sending `chartDataUrl` | The async DOM capture is the only slow step in PDF export (~200ms); removing it makes export instant |
| `AGENT_ORDER` uses `"ThermalAgent"`, `"GeometryAgent"`, `"ProcessStabilityAgent"` | Use snake_case `"thermal_agent"` etc. | Confirmed from `backend/agent/specialists.py` line 729: `for agent_name in ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"]` — `llm_raw_response` is `json.dumps([asdict(r) for r in specialist_results])` where `r.agent_name` is one of those three PascalCase values |

**Known limitations:**

| Limitation | Why acceptable | Upgrade path |
|---|---|---|
| `score.total` is mapped heuristically (85/55/30) | `WarpReport` has no numeric WQI field; this approximation is honest | Add `score_total` to `WarpReport` from backend and pass the real value |
| Agent `root_cause` truncated at 120 chars per panel | 3-column PDF layout has ~120px per panel at 8pt | When backend adds short summaries, use those instead |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
(1) grep -n "agentInsights\|rework_cost_usd\|disposition.*string" \
      my-app/src/components/pdf/WelderReportPDF.tsx \
      my-app/src/app/api/welder-report-pdf/route.ts
    → must return 0 matches (confirms new fields not yet added)

(2) grep -n "export interface WelderReportPDFProps" my-app/src/components/pdf/WelderReportPDF.tsx
    → must return exactly 1 match

(3) grep -n "const pdfReact = React.createElement" my-app/src/app/api/welder-report-pdf/route.ts
    → must return exactly 1 match

(4) grep -n "const payload = {" my-app/src/components/analysis/QualityReportCard.tsx
    → must return exactly 1 match inside handleExportPdf

(5) grep -n "specialistRows" my-app/src/components/analysis/QualityReportCard.tsx
    → must return matches (confirms it is already computed and in scope)

(6) Confirm actual agent_name values in llm_raw_response:
    grep -n '"ThermalAgent"\|"GeometryAgent"\|"ProcessStabilityAgent"' backend/agent/specialists.py
    → must confirm PascalCase values are the canonical agent_name strings
```

**Baseline Snapshot (agent fills during pre-flight):**
```
WelderReportPDF.tsx line count:   498
route.ts line count:              309
QualityReportCard.tsx line count: 504
agentInsights present:            0 matches (not yet added)
agent_name PascalCase confirmed:  ThermalAgent / GeometryAgent / ProcessStabilityAgent
```

---

## Step 1: Revamp `WelderReportPDF.tsx` — new props + new layout

**Step Architecture Thinking:**

**Pattern applied:** Single Responsibility. This file owns only the PDF visual contract. By rewriting the props interface first, Steps 2 and 3 can rely on a known interface when they update the caller and the route.

**Why this step is first:** The props interface is the contract between all three layers. Defining it here first means Step 2 (route) and Step 3 (caller) have a concrete type to match.

**Why this file:** This is the only file that renders the PDF. All content decisions live here; no other file needs to know about `@react-pdf/renderer`.

**Alternative rejected:** Keeping the old props interface and adding new props on top. Rejected because the old `chartDataUrl`, `certifications`, `reportSummary` props become dead code — confusing and misleading.

**What breaks if deviated:** If `agentInsights` prop is missing from the interface, Step 2's TypeScript will error when passing it to `React.createElement`. If `rework_cost_usd` is not in props, the hero section renders `$0` even for defective welds. If `AGENT_ORDER` uses snake_case instead of PascalCase, `insightMap` lookups miss every row and all 3 agent panels show "—".

---

**Idempotent:** Yes — full file replacement is safe to re-run.

**Pre-Read Gate:**
- `grep -n "export interface WelderReportPDFProps" my-app/src/components/pdf/WelderReportPDF.tsx` → exactly 1 match. If 0 → STOP.
- `grep -n "agentInsights" my-app/src/components/pdf/WelderReportPDF.tsx` → must return 0 matches. If 1+ → already patched, skip this step.

**Self-Contained Rule:** The complete new file is below — nothing omitted.

**No-Placeholder Rule:** No `<VALUE>` tokens anywhere in the code block.

Replace the entire contents of `my-app/src/components/pdf/WelderReportPDF.tsx` with:

```tsx
/**
 * PDF layout component for welder session report.
 * Supervisor/investor-grade rejection document.
 *
 * Uses @react-pdf/renderer — PDF-native components, no DOM or canvas capture.
 * Renders on server in Next.js API route.
 */

import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
} from "@react-pdf/renderer";

const COLORS = {
  BG: "#0d0f1a",
  PANEL: "#141728",
  BORDER: "#1e2236",
  ACCENT: "#4d7cfe",
  TEXT_PRI: "#e8eaf0",
  TEXT_SEC: "#8b91a8",
  GREEN: "#22c55e",
  RED: "#ef4444",
  AMBER: "#f59e0b",
} as const;

/** Sanitize text for PDF rendering. Strips control chars, zero-width, RTL-override. */
function sanitizeText(str: string): string {
  if (typeof str !== "string") return "";
  return str
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "")
    .replace(/[\u200b-\u200d\u2060\ufeff]/g, "")
    .replace(/[\u202a-\u202e\u2066-\u2069]/g, "")
    .replace(/</g, "‹")
    .replace(/>/g, "›");
}

/** Format dollar amount without relying on locale — safe for Node PDF renderer. */
function formatCost(n: number): string {
  return "$" + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function dispositionColor(d: string | null | undefined): string {
  if (d === "PASS") return COLORS.GREEN;
  if (d === "CONDITIONAL") return COLORS.AMBER;
  return COLORS.RED;
}

function dispositionLabel(d: string | null | undefined): string {
  if (d === "PASS") return "PASS";
  if (d === "CONDITIONAL") return "CONDITIONAL";
  return "REWORK REQUIRED";
}

/**
 * Map backend agent_name values (PascalCase, from specialists.py) to display labels.
 * Actual values confirmed from backend/agent/specialists.py:
 *   "ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"
 */
function agentDisplayLabel(name: string): string {
  if (name === "ThermalAgent") return "Thermal Analysis";
  if (name === "GeometryAgent") return "Geometry Analysis";
  if (name === "ProcessStabilityAgent") return "Process Analysis";
  return sanitizeText(name);
}

const styles = StyleSheet.create({
  page: {
    backgroundColor: COLORS.BG,
    padding: 40,
    fontFamily: "Helvetica",
  },
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    minHeight: 80,
    backgroundColor: COLORS.PANEL,
    marginHorizontal: -40,
    marginTop: -40,
    paddingHorizontal: 40,
    paddingTop: 16,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  logo: { fontSize: 14, color: COLORS.ACCENT, fontWeight: "bold", marginBottom: 2 },
  tagline: { fontSize: 8, color: COLORS.TEXT_SEC, marginBottom: 6 },
  welderName: { fontSize: 18, color: COLORS.TEXT_PRI, fontWeight: "bold", marginBottom: 4 },
  metaLine: { fontSize: 9, color: COLORS.TEXT_SEC },
  scoreCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    borderColor: COLORS.ACCENT,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
  },
  scoreText: { fontSize: 18, color: COLORS.ACCENT, fontWeight: "bold" },
  scoreDenom: { fontSize: 7, color: COLORS.TEXT_SEC },
  sectionTitle: {
    fontSize: 9,
    color: COLORS.TEXT_SEC,
    textTransform: "uppercase",
    letterSpacing: 2,
    marginBottom: 8,
  },
  panel: {
    marginTop: 16,
    padding: 14,
    backgroundColor: COLORS.PANEL,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: COLORS.BORDER,
  },
  footer: {
    position: "absolute",
    bottom: 30,
    left: 40,
    right: 40,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER,
    paddingTop: 10,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  footerText: { fontSize: 8, color: COLORS.TEXT_SEC },
});

export interface WelderReportPDFProps {
  welder: { name: string };
  score: { total: number };
  feedback: {
    summary: string;
    feedback_items: Array<{
      message: string;
      severity: string;
      suggestion?: string | null;
    }>;
  };
  narrative?: string | null;
  rework_cost_usd?: number | null;
  disposition?: string | null;
  agentInsights?: Array<{
    agent_name: string;
    disposition?: string;
    root_cause?: string;
    corrective_actions?: string[];
  }> | null;
  sessionDate?: string | null;
  duration?: string | null;
  station?: string | null;
}

export function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

export function WelderReportPDF({
  welder,
  score,
  feedback,
  narrative,
  rework_cost_usd,
  disposition,
  agentInsights,
  sessionDate,
  duration,
  station,
}: WelderReportPDFProps) {
  const welderName = sanitizeText(toWelderName(welder?.name ?? "Unknown"));
  const totalScore = Math.round(score?.total ?? 0);
  const cost = rework_cost_usd ?? 0;
  const costColor =
    cost === 0 ? COLORS.GREEN : cost <= 1800 ? COLORS.AMBER : COLORS.RED;
  const dispColor = dispositionColor(disposition);
  const dispLabel = dispositionLabel(disposition);

  const metaParts: string[] = [];
  if (sessionDate) metaParts.push(sessionDate);
  if (station) metaParts.push(station);
  if (duration) metaParts.push(duration);
  const metaLine =
    metaParts.length > 0
      ? `Session Report · ${metaParts.join(" · ")}`
      : "Session Report";

  const rootCause = sanitizeText(feedback?.summary ?? "");
  const rawRationale = narrative ?? "";
  const rationale = sanitizeText(
    rawRationale.slice(0, 400) + (rawRationale.length > 400 ? "…" : "")
  );
  const corrective = (feedback?.feedback_items ?? []).slice(0, 5);

  /**
   * Build insight map keyed by agent_name (PascalCase).
   * AGENT_ORDER matches the canonical values from backend/agent/specialists.py:
   *   for agent_name in ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"]
   */
  const AGENT_ORDER = ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"];
  const insightMap: Record<string, { disposition?: string; root_cause?: string }> = {};
  for (const row of agentInsights ?? []) {
    insightMap[row.agent_name] = {
      disposition: row.disposition,
      root_cause: row.root_cause,
    };
  }

  return (
    <Document>
      <Page size="LETTER" style={styles.page}>
        {/* TOP BAR */}
        <View style={styles.topBar}>
          <View style={{ flex: 1 }}>
            <Text style={styles.logo}>WARPSENSE</Text>
            <Text style={styles.tagline}>Quality Intelligence Platform</Text>
            <Text style={styles.welderName}>{welderName}</Text>
            <Text style={styles.metaLine}>{metaLine}</Text>
          </View>
          <View style={{ alignItems: "center" }}>
            <View style={styles.scoreCircle}>
              <Text style={styles.scoreText}>{totalScore}</Text>
              <Text style={styles.scoreDenom}>/ 100</Text>
            </View>
            <View
              style={{
                paddingHorizontal: 8,
                paddingVertical: 3,
                borderRadius: 4,
                backgroundColor: dispColor,
                alignItems: "center",
              }}
            >
              <Text style={{ fontSize: 7, color: "#fff", fontWeight: "bold" }}>
                {dispLabel}
              </Text>
            </View>
          </View>
        </View>

        {/* HERO: REWORK COST */}
        <View
          style={{
            marginTop: 24,
            paddingVertical: 28,
            alignItems: "center",
            backgroundColor: COLORS.PANEL,
            borderRadius: 6,
            borderWidth: 2,
            borderColor: costColor,
          }}
        >
          <Text
            style={{
              fontSize: 9,
              color: COLORS.TEXT_SEC,
              textTransform: "uppercase",
              letterSpacing: 2,
              marginBottom: 10,
            }}
          >
            Estimated Rework Cost
          </Text>
          <Text
            style={{
              fontSize: 64,
              fontWeight: "bold",
              color: costColor,
              fontFamily: "Helvetica-Bold",
            }}
          >
            {formatCost(cost)}
          </Text>
        </View>

        {/* REJECTION SUMMARY */}
        <View style={styles.panel}>
          <Text style={styles.sectionTitle}>Rejection Summary</Text>
          {rootCause !== "" && (
            <Text
              style={{
                fontSize: 12,
                color: COLORS.TEXT_PRI,
                fontWeight: "bold",
                marginBottom: rationale !== "" ? 8 : 0,
              }}
            >
              {rootCause}
            </Text>
          )}
          {rationale !== "" && (
            <Text style={{ fontSize: 9, color: COLORS.TEXT_SEC, lineHeight: 1.5 }}>
              {rationale}
            </Text>
          )}
        </View>

        {/* 3 AGENT FINDINGS */}
        <View style={{ marginTop: 16 }}>
          <Text style={styles.sectionTitle}>Agent Findings</Text>
          <View style={{ flexDirection: "row" }}>
            {AGENT_ORDER.map((agentKey, idx) => {
              const insight = insightMap[agentKey];
              const agentDisp = insight?.disposition;
              const rawRoot = insight?.root_cause ?? "";
              const agentRoot =
                rawRoot !== ""
                  ? sanitizeText(
                      rawRoot.slice(0, 120) + (rawRoot.length > 120 ? "…" : "")
                    )
                  : "—";
              const agentDispColor = dispositionColor(agentDisp);
              return (
                <View
                  key={agentKey}
                  style={{
                    flex: 1,
                    backgroundColor: COLORS.PANEL,
                    borderRadius: 6,
                    borderWidth: 1,
                    borderColor: COLORS.BORDER,
                    padding: 10,
                    marginRight: idx < 2 ? 8 : 0,
                  }}
                >
                  <Text
                    style={{
                      fontSize: 8,
                      color: COLORS.TEXT_SEC,
                      textTransform: "uppercase",
                      letterSpacing: 1,
                      marginBottom: 6,
                    }}
                  >
                    {agentDisplayLabel(agentKey)}
                  </Text>
                  {agentDisp != null && (
                    <View
                      style={{
                        paddingHorizontal: 6,
                        paddingVertical: 2,
                        borderRadius: 3,
                        backgroundColor: agentDispColor,
                        alignSelf: "flex-start",
                        marginBottom: 6,
                      }}
                    >
                      <Text
                        style={{ fontSize: 7, color: "#fff", fontWeight: "bold" }}
                      >
                        {dispositionLabel(agentDisp)}
                      </Text>
                    </View>
                  )}
                  <Text
                    style={{ fontSize: 8, color: COLORS.TEXT_PRI, lineHeight: 1.4 }}
                  >
                    {agentRoot}
                  </Text>
                </View>
              );
            })}
          </View>
        </View>

        {/* CORRECTIVE ACTIONS */}
        {corrective.length > 0 && (
          <View style={styles.panel}>
            <Text style={styles.sectionTitle}>Corrective Actions</Text>
            {corrective.map((item, i) => (
              <View
                key={`ca-${i}`}
                style={{ flexDirection: "row", marginBottom: 6 }}
              >
                <Text
                  style={{
                    fontSize: 9,
                    color: COLORS.ACCENT,
                    fontWeight: "bold",
                    minWidth: 18,
                    marginRight: 6,
                  }}
                >
                  {i + 1}.
                </Text>
                <Text
                  style={{
                    fontSize: 9,
                    color: COLORS.TEXT_PRI,
                    flex: 1,
                    lineHeight: 1.4,
                  }}
                >
                  {sanitizeText(item.message)}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* FOOTER */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>WarpSense Quality Intelligence</Text>
          <Text style={styles.footerText}>CONFIDENTIAL — Internal use only</Text>
        </View>
      </Page>
    </Document>
  );
}
```

**What it does:** Replaces the old coaching PDF with a rejection document. Hero cost block is the dominant visual element. Agent findings show each specialist's verdict side-by-side using correct PascalCase agent names that match the backend. Corrective actions are a numbered list.

**Why this approach:** Complete replacement is safer than surgical section removal across 498 lines; the old sections (compliance, chart, certifications) have deeply nested JSX that is error-prone to excise incrementally.

**Assumptions:**
- `@react-pdf/renderer` is already installed (`renderToBuffer` used in route.ts)
- `Helvetica-Bold` is a built-in PDF font (it is — part of the standard 14 PDF fonts)
- `fontFamily: "Helvetica-Bold"` on a `Text` node overrides the page-level `fontFamily: "Helvetica"`
- `agent_name` values in `llm_raw_response` are `"ThermalAgent"`, `"GeometryAgent"`, `"ProcessStabilityAgent"` — confirmed from `backend/agent/specialists.py` line 729

**Risks:**
- `gap` CSS property not supported in older react-pdf versions → mitigated by using `marginRight` on panels instead of `gap`
- `toWelderName` export is used by `route.ts` — it is kept in the new file

**Git Checkpoint:**
```bash
git add "my-app/src/components/pdf/WelderReportPDF.tsx"
git commit -m "feat: revamp WelderReportPDF — hero cost, rejection summary, agent findings, corrective actions"
```

**✓ Verification:**

**Type:** Integration (grep)

1. Confirm dropped sections are gone:
   `grep -n "reportSummary\|certifications\|chartDataUrl\|Coach Feedback\|Score Trend\|Compliance" my-app/src/components/pdf/WelderReportPDF.tsx`
   → must return **0 matches**.

2. Confirm new props exist:
   `grep -n "agentInsights\|rework_cost_usd\|disposition\?:" my-app/src/components/pdf/WelderReportPDF.tsx`
   → must return **3 or more matches** (in both the interface and the function body).

3. Confirm `toWelderName` export still present (route.ts imports it):
   `grep -n "export function toWelderName" my-app/src/components/pdf/WelderReportPDF.tsx`
   → must return **exactly 1 match**.

4. Confirm correct PascalCase agent names:
   `grep -n "ThermalAgent\|GeometryAgent\|ProcessStabilityAgent" my-app/src/components/pdf/WelderReportPDF.tsx`
   → must return **at least 6 matches** (3 in `AGENT_ORDER` array + 3 in `agentDisplayLabel`).

**Pass:** All 4 checks pass.

**Fail:**
- `reportSummary` still present → old file still in place → re-apply Write
- `toWelderName` missing → accidentally removed → restore the function from this plan
- `thermal_agent` found in file → snake_case not replaced → re-apply Write with corrected code block

---

## Step 2: Update `route.ts` — accept and pass 3 new fields

**Step Architecture Thinking:**

**Pattern applied:** DTO validation at the API boundary. The route is the trust boundary; it validates all inputs before passing to the PDF renderer. New fields are optional and additive — existing callers that don't send them get `null`.

**Why this step is second:** `WelderReportPDF` now expects `agentInsights`, `rework_cost_usd`, `disposition`. Without this step, the route passes `undefined` for all three — the PDF renders but with `$0` cost and no agent insights.

**Why this file:** This is the only entry point that assembles `WelderReportPDFProps` and calls `renderToBuffer`. The validation firewall lives here.

**Alternative rejected:** Accepting the raw `WarpReport` JSON and letting `WelderReportPDF` pick fields. Rejected because the PDF component is a pure renderer — it must not contain fetch or business logic, and accepting unvalidated JSON opens injection risk.

**What breaks if deviated:** If `agentInsights` is not validated as an array of objects, a malformed request could pass `null` or a string into `WelderReportPDF`, causing a runtime crash in `renderToBuffer` (unhandled in the try/catch).

---

**Idempotent:** Yes — adding optional fields to an interface and extraction block is re-runnable.

**Pre-Read Gate:**
- `grep -n "interface PDFRequestBody" my-app/src/app/api/welder-report-pdf/route.ts` → exactly 1 match.
- `grep -n "const pdfReact = React.createElement" my-app/src/app/api/welder-report-pdf/route.ts` → exactly 1 match.
- `grep -n "agentInsights" my-app/src/app/api/welder-report-pdf/route.ts` → must return 0 matches. If 1+ → already patched, skip step.

**Change A — extend `PDFRequestBody` interface:**

Replace:
```typescript
interface PDFRequestBody {
  welder?: { name?: unknown };
  score?: SessionScore | { total: number; rules?: unknown[] };
  feedback?: { summary?: string; feedback_items?: unknown[] };
  chartDataUrl?: unknown;
  /** Optional AI Coach narrative; max 2000 chars. PDF renders without if absent. */
  narrative?: string | null;
  /** Optional report summary; PDF renders compliance section if present. Omit and log warning if absent. */
  reportSummary?: unknown;
  /** Optional certification readiness; PDF renders table section if present. */
  certifications?: Array<{
    name: string;
    status: string;
    qualifying_sessions: number;
    sessions_required: number;
  }> | null;
  /** Optional session date for top-bar meta (e.g. "2/27/2026"). */
  sessionDate?: string | null;
  /** Optional duration string (e.g. "4 min 12 sec") for top-bar meta. */
  duration?: string | null;
  /** Optional station placeholder (e.g. "Station 4") for top-bar meta. */
  station?: string | null;
}
```

With:
```typescript
interface PDFRequestBody {
  welder?: { name?: unknown };
  score?: SessionScore | { total: number; rules?: unknown[] };
  feedback?: { summary?: string; feedback_items?: unknown[] };
  chartDataUrl?: unknown;
  /** Optional AI Coach narrative; max 2000 chars. PDF renders without if absent. */
  narrative?: string | null;
  /** Optional report summary; PDF renders compliance section if present. Omit and log warning if absent. */
  reportSummary?: unknown;
  /** Optional certification readiness; PDF renders table section if present. */
  certifications?: Array<{
    name: string;
    status: string;
    qualifying_sessions: number;
    sessions_required: number;
  }> | null;
  /** Optional session date for top-bar meta (e.g. "2/27/2026"). */
  sessionDate?: string | null;
  /** Optional duration string (e.g. "4 min 12 sec") for top-bar meta. */
  duration?: string | null;
  /** Optional station placeholder (e.g. "Station 4") for top-bar meta. */
  station?: string | null;
  /** Estimated rework cost in USD — drives the hero block in the PDF. */
  rework_cost_usd?: number | null;
  /** Weld disposition — PASS | CONDITIONAL | REWORK_REQUIRED. */
  disposition?: string | null;
  /** Per-agent parsed insights from llm_raw_response. */
  agentInsights?: Array<{
    agent_name: string;
    disposition?: string;
    root_cause?: string;
    corrective_actions?: string[];
  }> | null;
}
```

**Change B — add extraction block before the `try { const pdfReact` line:**

In the `POST` handler, find the block ending with:
```typescript
  let station: string | undefined;
  if (body.station != null && typeof body.station === "string") {
    station = body.station.slice(0, 128) || undefined;
  }

  try {
    const pdfReact = React.createElement(WelderReportPDF, {
```

Replace with:
```typescript
  let station: string | undefined;
  if (body.station != null && typeof body.station === "string") {
    station = body.station.slice(0, 128) || undefined;
  }

  let rework_cost_usd: number | null = null;
  if (
    body.rework_cost_usd != null &&
    typeof body.rework_cost_usd === "number" &&
    Number.isFinite(body.rework_cost_usd) &&
    body.rework_cost_usd >= 0
  ) {
    rework_cost_usd = body.rework_cost_usd;
  }

  let disposition: string | null = null;
  if (body.disposition != null && typeof body.disposition === "string") {
    disposition = body.disposition.slice(0, 32);
  }

  let agentInsights: WelderReportPDFProps["agentInsights"] = null;
  if (Array.isArray(body.agentInsights)) {
    agentInsights = body.agentInsights
      .filter(
        (r): r is { agent_name: string } =>
          r != null &&
          typeof r === "object" &&
          typeof (r as Record<string, unknown>).agent_name === "string"
      )
      .map((r) => {
        const obj = r as Record<string, unknown>;
        return {
          agent_name: String(obj.agent_name).slice(0, 64),
          disposition:
            typeof obj.disposition === "string"
              ? obj.disposition.slice(0, 32)
              : undefined,
          root_cause:
            typeof obj.root_cause === "string"
              ? obj.root_cause.slice(0, 500)
              : undefined,
          corrective_actions: Array.isArray(obj.corrective_actions)
            ? (obj.corrective_actions as unknown[]).filter(
                (s): s is string => typeof s === "string"
              )
            : undefined,
        };
      });
  }

  try {
    const pdfReact = React.createElement(WelderReportPDF, {
```

**Change C — update `React.createElement` call:**

Find:
```typescript
    const pdfReact = React.createElement(WelderReportPDF, {
      welder,
      score,
      feedback,
      chartDataUrl,
      narrative,
      certifications,
      reportSummary: reportSummary ?? undefined,
      sessionDate: sessionDate ?? undefined,
      duration: duration ?? undefined,
      station: station ?? undefined,
    });
```

Replace with:
```typescript
    const pdfReact = React.createElement(WelderReportPDF, {
      welder,
      score,
      feedback,
      narrative,
      rework_cost_usd,
      disposition,
      agentInsights,
      sessionDate: sessionDate ?? undefined,
      duration: duration ?? undefined,
      station: station ?? undefined,
    });
```

Note: `chartDataUrl`, `certifications`, `reportSummary` are removed from the call because `WelderReportPDF` no longer accepts them. Their extraction blocks and `PDFRequestBody` fields remain for backward compatibility (old clients must not receive 400 errors). The extracted variables are unused — `noUnusedLocals` is not enabled in tsconfig.json (`strict: true` does not include it), so this does not produce a TypeScript error.

**Add import for `WelderReportPDFProps`:**

Find:
```typescript
import { WelderReportPDF } from "@/components/pdf/WelderReportPDF";
```

Replace with:
```typescript
import { WelderReportPDF, type WelderReportPDFProps } from "@/components/pdf/WelderReportPDF";
```

**Git Checkpoint:**
```bash
git add "my-app/src/app/api/welder-report-pdf/route.ts"
git commit -m "feat: welder-report-pdf route — accept rework_cost_usd, disposition, agentInsights"
```

**✓ Verification:**

**Type:** Integration (grep)

1. Confirm new fields in interface:
   `grep -n "rework_cost_usd\|disposition\?\|agentInsights" my-app/src/app/api/welder-report-pdf/route.ts`
   → must return **6 or more matches** (interface + extraction block + createElement call).

2. Confirm old props removed from createElement:
   `grep -n "certifications\|reportSummary\|chartDataUrl" my-app/src/app/api/welder-report-pdf/route.ts`
   → must return matches **only** inside `PDFRequestBody` interface and the old extraction blocks (they remain for backward compat), **NOT** inside `React.createElement(WelderReportPDF`.

3. TypeScript spot-check:
   ```bash
   npx tsc --noEmit 2>&1 | grep "welder-report-pdf"
   ```
   → must return 0 lines.

**Pass:** All 3 checks pass.

**Fail:**
- `WelderReportPDFProps` not found → import not added → add the named import
- createElement type error → a prop name mismatch with the new interface → re-read Step 1's interface and align

---

## Step 3: Update `QualityReportCard.tsx` — send new fields, remove `captureChartToBase64`

**Step Architecture Thinking:**

**Pattern applied:** DTO assembly at the caller. `QualityReportCard` already holds `report` and `specialistRows` (the parsed agent insights). This step wires those existing values into the PDF payload — no new state, no new fetches.

**Why this step is last:** Step 2 defined the route's expected fields. Step 3 is the caller satisfying that contract. If done first, the unused fields would silently be ignored.

**Why this file:** This is the only place `handleExportPdf` is defined and the only call site for `POST /api/welder-report-pdf`.

**Alternative rejected:** Adding a new `onExportPdf` prop to pass the payload from a parent component. Rejected because all the data is already in scope within `QualityReportCard` — adding a prop creates unnecessary coupling.

**What breaks if deviated:** If `specialistRows` is sent as `undefined` instead of `null`, the route's `Array.isArray(body.agentInsights)` check returns false and agent insights are omitted from the PDF. If `specialistRows` is not added to the `handleExportPdf` `useCallback` deps array and ESLint exhaustive-deps is enforced, a lint error blocks build.

---

**Idempotent:** Yes.

**Pre-Read Gate:**
- `grep -n "const payload = {" my-app/src/components/analysis/QualityReportCard.tsx` → exactly 1 match inside `handleExportPdf`. If 0 → STOP.
- `grep -n "captureChartToBase64" my-app/src/components/analysis/QualityReportCard.tsx` → must return 2 matches (import line + call site). If 0 → already removed, adjust accordingly.
- `grep -n "agentInsights" my-app/src/components/analysis/QualityReportCard.tsx` → must return 0 matches. If 1+ → already patched, skip step.

**Change A1 — update the payload object (Edit 1 of 3):**

Replace:
```typescript
      const chartDataUrl = await captureChartToBase64("welder-trend-chart");
      const scoreTotal =
        report.disposition === "PASS"         ? 1.0
        : report.disposition === "CONDITIONAL" ? 0.5
        : 0.0;
      const payload = {
        welder: { name: welderDisplayName ?? "Unknown" },
        score:  { total: scoreTotal },
        feedback: {
          summary: report.root_cause,
          feedback_items: report.corrective_actions.map((action, i) => ({
            message:  action,
            severity: i === 0 ? "high" : "medium",
          })),
        },
        narrative:   report.disposition_rationale.slice(0, 2000),
        chartDataUrl,
        sessionDate: new Date(report.report_timestamp).toLocaleDateString("en-GB"),
      };
```

With:
```typescript
      const scoreTotal =
        report.disposition === "PASS"         ? 85
        : report.disposition === "CONDITIONAL" ? 55
        : 30;
      const payload = {
        welder: { name: welderDisplayName ?? "Unknown" },
        score:  { total: scoreTotal },
        feedback: {
          summary: report.root_cause,
          feedback_items: report.corrective_actions.map((action, i) => ({
            message:  action,
            severity: i === 0 ? "high" : "medium",
          })),
        },
        narrative:     report.disposition_rationale.slice(0, 400),
        rework_cost_usd: report.rework_cost_usd ?? null,
        disposition:   report.disposition,
        agentInsights: specialistRows ?? null,
        sessionDate:   new Date(report.report_timestamp).toLocaleDateString("en-GB"),
      };
```

**Change A2 — update `useCallback` dependency array (Edit 2 of 3):**

This edit is NOT contiguous with Change A1 — it is at the end of the `handleExportPdf` callback closure, several lines below the payload block.

Replace:
```typescript
  }, [isPdfLoading, report, welderDisplayName]);
```

With:
```typescript
  }, [isPdfLoading, report, welderDisplayName, specialistRows]);
```

**Anchor uniqueness check:** `grep -n "isPdfLoading, report, welderDisplayName" my-app/src/components/analysis/QualityReportCard.tsx` → must return **exactly 1 match**. If 0 → deps line already changed or callback was refactored — re-read file before editing.

**Change B — remove the `captureChartToBase64` import (Edit 3 of 3):**

This edit is NOT contiguous with Change A1 or A2. Replace the import line AND its following line together to avoid leaving a blank line:

Replace:
```typescript
import { captureChartToBase64 } from "@/lib/pdf-chart-capture";
import { StatusBadge } from "./StatusBadge";
```

With:
```typescript
import { StatusBadge } from "./StatusBadge";
```

Note: After this edit, confirm `captureChartToBase64` is fully removed:
`grep -n "captureChartToBase64" my-app/src/components/analysis/QualityReportCard.tsx` → must return **0 matches**.

**Git Checkpoint:**
```bash
git add "my-app/src/components/analysis/QualityReportCard.tsx"
git commit -m "feat: QualityReportCard — send rework_cost_usd, disposition, agentInsights to PDF; remove chart capture"
```

**✓ Verification:**

**Type:** Integration (grep) + TypeScript + E2E

1. Confirm old payload fields gone:
   `grep -n "chartDataUrl\|scoreTotal.*0\.5\|scoreTotal.*1\.0\|slice(0, 2000)" my-app/src/components/analysis/QualityReportCard.tsx`
   → must return **0 matches**.

2. Confirm new fields present:
   `grep -n "agentInsights\|rework_cost_usd\|disposition.*report\." my-app/src/components/analysis/QualityReportCard.tsx`
   → must return **3 or more matches**.

3. TypeScript full check:
   ```bash
   npx tsc --noEmit 2>&1 | grep -E "WelderReportPDF|QualityReportCard|welder-report-pdf"
   ```
   → must return **0 lines**.

4. E2E: Run a weld analysis session (any session that produces REWORK_REQUIRED), click **Export PDF**, open the downloaded file.
   - Page 1: dollar amount in the hero block matches `rework_cost_usd` from the report
   - Page 1: 3 agent panels visible (Thermal Analysis / Geometry Analysis / Process Analysis) with content (not all "—")
   - Page 1: numbered corrective actions list
   - No compliance table, no chart image, no certifications section

**Pass:** TypeScript clean + PDF opens with correct layout + agent panels contain real content.

**Fail:**
- `agentInsights` is null in PDF (panels show "—" for all agents) → `specialistRows` is null → `report.llm_raw_response` is not valid JSON array → backend issue, not this plan's scope
- Agent panels show "—" despite `specialistRows` being non-null → `agent_name` mismatch — run `console.log(specialistRows)` in browser devtools to inspect actual `agent_name` values, then update `AGENT_ORDER` in `WelderReportPDF.tsx` to match
- `$0` shown for defective weld → `rework_cost_usd` not sent or `undefined` on report → confirm `report.rework_cost_usd` is non-null for this session (may need to re-run analysis if session was analysed before the rework cost was added in Step 7 of frolicking-weaving-kernighan plan)
- TypeScript error on `WelderReportPDFProps` → old props (`certifications`, `reportSummary`, `chartDataUrl`) still referenced in route — confirm Change C in Step 2 was applied

---

## Regression Guard

| System | Pre-change behavior | Post-change verification |
|---|---|---|
| Export PDF button | Visible at line 468, triggers download | Button still present: `grep -n "Export PDF" my-app/src/components/analysis/QualityReportCard.tsx` → 1 match |
| `/api/welder-report-pdf` route | Returns 200 application/pdf | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3000/api/welder-report-pdf -H "Content-Type: application/json" -d '{"welder":{"name":"Test"},"score":{"total":30},"feedback":{"summary":"root","feedback_items":[]}}' ` → `200` |
| Old callers without new fields | Would fail if new fields were required | All 3 new fields are optional in `PDFRequestBody` — existing callers get graceful null fallback |

---

## Success Criteria

| Feature | Target | Verification |
|---|---|---|
| Hero rework cost | Large dollar amount, red/amber/green | Open PDF → cost is the dominant visual element on page 1 |
| Rejection reason | Root cause bold + rationale body | Rejection Summary panel visible with non-empty text |
| 3 agent findings | All 3 panels present with real content | Agent Findings section has 3 side-by-side columns, each showing actual root_cause text (not "—") |
| Corrective actions | Numbered list up to 5 items | Corrective Actions panel shows numbered rows |
| Export button unchanged | Same location, same trigger | `grep -n "Export PDF" QualityReportCard.tsx` → 1 match at line ~468 |
| TypeScript clean | 0 errors | `npx tsc --noEmit` → no errors in modified files |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not batch multiple steps into one git commit.**
⚠️ **Step 1 must complete before Step 2 (route needs the new WelderReportPDFProps type).**
⚠️ **Step 2 must complete before Step 3 (caller must satisfy the updated route contract).**
⚠️ **`AGENT_ORDER` must use PascalCase: `["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"]` — confirmed from `backend/agent/specialists.py` line 729.**
