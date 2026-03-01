# PDF Report Full Layout — Exploration & Mock Execution Plan

**Issue:** [docs/ISSUE_PDF_REPORT_LETTER_LAYOUT.md](../docs/ISSUE_PDF_REPORT_LETTER_LAYOUT.md)  
**Goal:** Update `WelderReportPDF` to letter size and full reference design. No implementation yet — exploration only.

---

## 1. Codebase Analysis

### Current Stack
| Layer | Tech | Location |
|-------|------|----------|
| PDF component | `@react-pdf/renderer` | `WelderReportPDF.tsx` |
| API route | Next.js POST handler | `app/api/welder-report-pdf/route.ts` |
| Trigger | Client `handleDownloadPDF` | `app/seagull/welder/[id]/page.tsx` |
| Chart capture | `html-to-image` → base64 PNG | `lib/pdf-chart-capture.ts` |

### Current Data Flow
```
Page loads → fetch session, score, historicalScores, reportSummary, narrative
User clicks "Download PDF" →
  1. captureChartToBase64("trend-chart") — DOM element to PNG
  2. fetchNarrative(sessionId) — optional
  3. POST /api/welder-report-pdf { welder, score, feedback, chartDataUrl, narrative, reportSummary }
  4. API validates, creates WelderReportPDF React element, renderToBuffer()
  5. Blob returned, client triggers download
```

### Existing Props / Data Available
| Prop | Source | Notes |
|------|--------|------|
| `welder.name` | `displayName` from page | WELDER_DISPLAY_NAMES |
| `score.total` | `fetchScore(sessionId)` | SessionScore |
| `feedback.summary` | `generateAIFeedback()` | In-memory |
| `feedback.feedback_items` | `generateAIFeedback()` | message, severity, suggestion |
| `chartDataUrl` | `captureChartToBase64("trend-chart")` | PNG of LineChart |
| `narrative` | `fetchNarrative(sessionId)` | AI Coach text |
| `reportSummary` | `useReportSummary(sessionId)` | Backend `/sessions/{id}/report-summary` |
| `certifications` | Not passed today | CertificationCard fetches separately |

### What’s Missing for Reference Design
| Reference element | Current state | Gap |
|-------------------|---------------|-----|
| Session date | `session.start_time` | Available; not passed to API |
| Duration | Derived from frames | Not computed/passed |
| Station | Mock "Station 4" in reference | No real data — placeholder |
| Compliance PASS/FAIL badges | reportSummary exists | Layout/style differs — need badge UI |
| Score trend chart | chartDataUrl exists | Keep image embed; no native SVG |
| Key Areas color coding | feedback_items by severity | Map severity→color (warning→amber, critical→red, info→green) |

---

## 2. Reference Design Breakdown

### Reference Layout (top to bottom)
1. **Full-page BG** — `#0d0f1a`
2. **Top bar (88pt)** — `#141728`, border below
   - Logo: "WARPSENSE" (accent), "Quality Intelligence Platform" (secondary)
   - Operator name (large)
   - Meta: "Session Report · 2/27/2026 · Station 4 · Duration: 4 min 12 sec"
   - Score circle (right): ring + "96" + "/ 100"
3. **Section: COMPLIANCE** — Rounded panel, rows with PASS/FAIL badges
4. **Section: COACH FEEDBACK** — 2-line narrative
5. **Section: SCORE TREND** — Chart (gradient under line, dots, labels)
6. **Section: KEY AREAS FOR IMPROVEMENT** — Color dots (amber/accent/green) + title + detail
7. **Footer** — Divider, "WarpSense Quality Intelligence" | "CONFIDENTIAL — Internal use only"

### Color Palette (reference)
```
BG        #0d0f1a
PANEL     #141728
BORDER    #1e2236
ACCENT    #4d7cfe
TEXT_PRI  #e8eaf0
TEXT_SEC  #8b91a8
GREEN     #22c55e
RED       #ef4444
AMBER     #f59e0b
```

### Current vs Reference
- **Current page:** `size="A4"` → change to `size="LETTER"`
- **Current theme:** `#0a0a0a` bg, `#1a1a2e` panels → align to reference palette
- **Current header:** Simple row (name + score circle) → full top bar with branding
- **Current compliance:** Inline text + ✓/✗ → badge components (green/red pill)
- **Current chart:** Image of LineChart → keep Image (no native SVG gradient in React-PDF)
- **Current Key Areas:** Bullets from feedback_items → add severity→color mapping
- **Current footer:** "CONFIDENTIAL" only → add "WarpSense Quality Intelligence" left

---

## 3. Dependencies & Constraints

### Dependencies
- **reportSummary:** Optional. If absent, Compliance section hidden (already implemented).
- **chartDataUrl:** Optional. If null, Score Trend section hidden or shows "No trend data".
- **narrative:** Optional. Coach Feedback can use `feedback.summary` as fallback.
- **Session metadata:** Need `sessionDate`, `duration` — page has `session` but does not pass to PDF.

### Constraints
- **React-PDF:** No DOM, no css-in-js at runtime. StyleSheet only. Limited layout (flexbox).
- **Rounded rects:** React-PDF has `borderRadius` on View. No `rr()`-style path — use View + borderRadius.
- **Chart:** Gradient fill under line — complex in React-PDF Svg. Keep `Image` from capture.
- **Badge:** Use View with borderRadius, Text centered. Green/red fill.
- **Body size:** 5MB limit on route. chartDataUrl 2MB. Sufficient for typical PNG.

### Edge Cases
| Case | Handling |
|------|----------|
| reportSummary absent | Omit Compliance section (existing) |
| chartDataUrl null | Omit or show "No trend data" placeholder |
| feedback_items empty | Key Areas section empty or "No key areas" |
| narrative + feedback.summary both empty | Coach Feedback shows "—" |
| Very long narrative | Truncate or wrap (narrative max 2000 chars in API) |
| Session < 5 scores | chartData shows available (e.g. 3 points) |

---

## 4. Data Flow (Updated)

```
Page (welder report)
  ├─ session, score, report, chartData, reportSummary, narrative
  ├─ handleDownloadPDF:
  │    ├─ captureChartToBase64("trend-chart")
  │    ├─ fetchNarrative(sessionId)
  │    └─ Build payload with NEW optional fields:
  │         sessionDate?: string    // session.start_time → toLocaleDateString()
  │         duration?: string       // "4 min 12 sec" from frame timestamps
  │         station?: string        // optional, e.g. "Station 4" (placeholder)
  └─ POST /api/welder-report-pdf
       └─ Validate, pass to WelderReportPDF
```

**Route changes:** Extend `PDFRequestBody` with optional `sessionDate`, `duration`, `station`. Pass to component.

**Component:** New optional props `sessionDate`, `duration`, `station` for top-bar meta.

---

## 5. Component Structure (High-Level)

### WelderReportPDF.tsx — Layout Sections

```
Document
  Page (size="LETTER", style=page)
    ├─ [1] TopBar (full width, 88pt from top)
    │     Logo | Operator + Meta | ScoreCircle
    ├─ [2] CompliancePanel (if reportSummary)
    │     Section label + rows with Badge(PASS|FAIL)
    ├─ [3] CoachFeedbackSection
    │     Section label + narrative or feedback.summary
    ├─ [4] ScoreTrendSection (if chartDataUrl)
    │     Section label + Image(chartDataUrl)
    ├─ [5] KeyAreasSection
    │     Section label + items (dot + title + detail, severity→color)
    ├─ [6] CertificationsSection (if certifications)
    └─ [7] Footer (position absolute bottom)
          "WarpSense Quality Intelligence" | "CONFIDENTIAL — Internal use only"
```

### Internal “subcomponents” (inline View/Text, not separate files)

```
TopBar:
  - View (flex row, space-between)
    - View (left): logo text, tagline, operator name, meta line
    - View (right): score circle (border + arc or simplified ring + number)

Badge:
  - View (borderRadius:4, fill green|red, small)
    - Text centered "PASS"|"FAIL" (white, bold)

ComplianceRow:
  - View (flex row)
    - Text label (secondary)
    - Text detail (primary)
    - Badge(passed)
```

### Style constants (reference palette)

```ts
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
```

---

## 6. State / Side Effects

- **No React state.** Component is pure: props in → PDF out.
- **No useEffect.** No data fetching in the component.
- **Side effects:** All in page (`handleDownloadPDF`) and API route (validation, render).

---

## 7. Implementation Approach

### Files to Modify

| File | Changes |
|------|---------|
| `WelderReportPDF.tsx` | Full restructure: Page size=LETTER, new palette, TopBar, CompliancePanel with badges, CoachFeedback, ScoreTrend, KeyAreas with color mapping, Footer. Add optional props sessionDate, duration, station. |
| `welder-report-pdf/route.ts` | Extend PDFRequestBody with sessionDate?, duration?, station?. Validate strings, pass to component. |
| `welder/[id]/page.tsx` | In handleDownloadPDF payload: add sessionDate (from session.start_time), duration (derived from frames), station (optional placeholder). |

### Files to Create

| File | Purpose |
|------|---------|
| None | All logic stays in WelderReportPDF; no new components. |

### Alternatives Considered

| Alternative | Why not chosen |
|-------------|----------------|
| Extract TopBar, Badge, etc. to separate components | Extra files for small PDF-only pieces; keep in one file for now. |
| Use React-PDF Svg for chart | Gradient under line is non-trivial; Image capture is simpler and already works. |
| Backend PDF generation (reportlab) | Stack is React-PDF; would require new service, different deploy path. |
| Pass full session to API | Adds payload size; only need date, duration. |

---

## 8. Pseudocode / Skeleton

### TopBar (conceptual)

```
TopBar({ welderName, sessionDate, duration, station, scoreTotal }):
  meta = join non-null [sessionDate, station, duration] with "  ·  "
  return View (full width, height 88, bg PANEL, borderBottom BORDER):
    left block:
      Text "WARPSENSE" (ACCENT, bold)
      Text "Quality Intelligence Platform" (TEXT_SEC)
      Text welderName (TEXT_PRI, large)
      Text "Session Report  ·  {meta}" (TEXT_SEC)
    right block:
      ScoreCircle(scoreTotal)  // border ring, number centered, "/ 100" below
```

### Compliance rows (from reportSummary)

```
rows = [
  ( "Heat Input",   detailString(heat_input_mean, wps_min, wps_max), heat_input_compliant ),
  ( "Torch Angle", travelAngleDetail(), travel_angle_excursion_count === 0 ),
  ( "Arc Termination", arcTermDetail(), arcCompliant ),
]
for each (label, detail, passed): ComplianceRow(label, detail, passed)
```

### Badge

```
Badge(passed): 
  View(bg=passed?GREEN:RED, borderRadius 4, padding, minWidth 36)
    Text passed?"PASS":"FAIL" (white, bold, centered)
```

### Key Areas (from feedback_items)

```
severityToColor = { critical: RED, warning: AMBER, info: GREEN }
for item in top3 feedback_items:
  dotColor = severityToColor[item.severity] ?? ACCENT
  render: dot (circle) + title (item.message) + detail (item.suggestion or "")
```

---

## 9. Duration Calculation

```ts
// In page.tsx, before building payload:
function formatDuration(ms: number): string {
  const min = Math.floor(ms / 60000);
  const sec = Math.floor((ms % 60000) / 1000);
  return `${min} min ${sec} sec`;
}
// frames ordered by timestamp_ms; last - first = duration
const durationMs = session.frames?.length
  ? (session.frames[session.frames.length - 1]?.timestamp_ms ?? 0) -
    (session.frames[0]?.timestamp_ms ?? 0)
  : 0;
const duration = durationMs > 0 ? formatDuration(durationMs) : undefined;
```

---

## 10. Open Questions / Ambiguities

1. **Station:** Reference uses "Station 4". No backend field. Use placeholder "Station —" or omit when absent?
2. **Score ring (partial arc):** Reference draws 96% of circle. Implement with React-PDF Svg `<Circle>` + `<Path>` for arc, or use a full border ring for simplicity?
3. **Key Areas semantic mapping:** Reference has topic-based items (current stability, torch angle, thermal symmetry). We have feedback_items (message, severity). Use severity→color mapping only, or try to infer topic from message text?
4. **Coach Feedback vs narrative:** Reference shows "Excellent session — all compliance thresholds met...". We have `narrative` (AI) and `feedback.summary` (generated). Prefer narrative when present, else summary?
5. **Certifications:** Not currently passed to PDF. Add to this change or leave for a follow-up?

---

## 11. Verification

- Existing tests: `welder-report-pdf.test.ts` — payload shape unchanged for required fields; optional new fields.
- Snapshot / visual: Manual check of PDF output after changes.
- Letter size: Inspect PDF properties or print preview to confirm 8.5×11".

---

## 12. Effort Estimate

| Task | Effort |
|------|--------|
| Page size + palette + TopBar | Small |
| Compliance panel with badges | Small |
| Coach Feedback / Key Areas restyle | Small |
| Footer update | Trivial |
| Route + page: sessionDate, duration | Small |
| Score ring (partial arc) — if desired | Medium |
| Testing / manual verification | Small |
| **Total** | **Medium** (approx. 1–2 days) |
