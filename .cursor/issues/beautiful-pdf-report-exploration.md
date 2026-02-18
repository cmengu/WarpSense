# Beautiful PDF Report — Technical Exploration

**Issue:** `.cursor/issues/beautiful-pdf-report.md`  
**Date:** 2026-02-18

---

## 1. Complexity Classification

**Moderate.** PDF layout and API route are straightforward; chart capture (html-to-image on Recharts SVG) introduces browser-dependent behavior and a fallback path. Single-page PDF, explicit data shapes, no frame/3D coupling.

---

## 2. Risk Profile

| Axis | Level | Reason |
|------|-------|--------|
| Data loss risk | **Low** | PDF is generated on-demand; no persistence. Raw session data untouched. |
| Service disruption risk | **Low** | New API route; no changes to existing fetch paths. |
| Security risk | **Low** | POST body validated; no user uploads stored. Filename sanitized. |
| Dependency risk | **Medium** | `@react-pdf/renderer` and `html-to-image` are new; React 19 / Next 16 compatibility unproven. |
| Rollback complexity | **Low** | Revert route + component; button handler returns to stub. |

---

## 3. Codebase Findings

### Files and Patterns

| File | Purpose | Pattern | Reuse | Avoid |
|------|---------|---------|-------|-------|
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Welder report page; stub Download PDF | `useEffect` + `Promise.all` fetch; `generateAIFeedback`; `report`, `score`, `displayName` | Use same data flow for PDF payload; add `id="trend-chart"` to LineChart wrapper | Don't fetch again for PDF — data already in state |
| `my-app/src/components/charts/LineChart.tsx` | Recharts LineChart | `ResponsiveContainer width="100%"`; SVG render | Wrap in fixed-size div for capture | `ResponsiveContainer` with 100% needs parent with explicit dimensions for consistent capture |
| `my-app/src/lib/export.ts` | CSV export for supervisor | `generateCSV`, `downloadCSV` — blob → `URL.createObjectURL` → anchor click | Same download pattern: blob → `createObjectURL` → `a.click()` | `downloadCSV` anchor not appended to DOM (per review) — ensure anchor is used or appended |
| `my-app/src/app/(app)/supervisor/page.tsx` | Export CSV button | `exporting` state; `disabled={loading \|\| exporting}`; `setExportError` on catch | Reuse loading/disable/error pattern | — |
| `my-app/src/types/ai-feedback.ts` | `AIFeedbackResult`, `FeedbackItem` | `feedback_items`, `summary`, `severity`, `suggestion` | Pass `report` (AIFeedbackResult) as `feedback` to API | — |
| `my-app/src/lib/api.ts` | `SessionScore`, `fetchScore` | `total`, `rules` | Pass `score` (SessionScore) to API; API expects same shape | — |
| `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` | Tests stub alert | `fireEvent.click`; `expect(alertSpy).toHaveBeenCalledWith` | Replace with fetch mock; assert POST and download | — |

### Similar Implementations (3+)

1. **Supervisor Export CSV** (`supervisor/page.tsx` + `lib/export.ts`) — Client-side generation (generateCSV) → blob → download. Pattern: `exporting` state, disable button, `downloadCSV(filename, csv)`. **Reuse:** loading state, error display, download trigger.
2. **downloadCSV** (`lib/export.ts`) — `Blob` → `URL.createObjectURL` → `<a href, download>` → `click()`. **Reuse:** identical pattern for PDF blob.
3. **FeedbackPanel** (`components/welding/FeedbackPanel.tsx`) — Renders `feedback_items` with severity icons. **Reuse:** Severity mapping (⚠ for warning, • for info) matches spec; PDF layout can mirror structure.
4. **LineChart** (`components/charts/LineChart.tsx`) — Recharts `ResponsiveContainer`; no wrapper `id`. **Gap:** Need wrapper with `id="trend-chart"` and fixed dimensions for html-to-image.

**Closest gap:** No API routes exist in `my-app/src/app/`. The project uses App Router; API routes go in `app/api/` (Next.js convention). First API route will establish the pattern.

---

## 4. Known Constraints

- **Locked dependencies:** Next.js 16.1.6, React 19.2.3. `@react-pdf/renderer` must be compatible; no Edge runtime (PDF render needs Node).
- **Framework rules:** API route must be `app/api/welder-report-pdf/route.ts` (Next.js App Router). `renderToBuffer` is async; use in route handler.
- **Performance:** Single-page PDF target < 3s; base64 chart can be ~50–200 KB.
- **Reference stability:** N/A for this feature; no parent array reference issues.
- **Environment:** `html-to-image` runs in browser only; `@react-pdf/renderer` runs in Node (API route). No SSR of PDF component.
- **WebGL:** Not applicable; LineChart is SVG. No extra Canvas/WebGL context.
- **Verification:** `.cursorrules` — add automated tests; no manual browser-only checks.

---

## 5. Approach Options

### Option A: @react-pdf/renderer + html-to-image (Client chart capture) — RECOMMENDED
**Description:** Build PDF with `@react-pdf/renderer` in a Next.js API route. Client captures LineChart div via `html-to-image` `toPng`, sends base64 in POST body. API renders PDF with embedded Image.

**Pros:** Matches spec; no Puppeteer; chart matches UI; fast to implement; single-page PDF.

**Cons:** html-to-image can fail on some SVG/canvas combos; base64 bloats POST; client must have chart rendered before click.

**Key risk:** html-to-image fails on Recharts (e.g. CORS, filters).

**Complexity:** Medium.

---

### Option B: @react-pdf/renderer + chartjs-node-canvas (Server chart)
**Description:** Same PDF route; render chart on server with `chartjs-node-canvas` instead of client capture.

**Pros:** No client capture; consistent output; no base64 in body.

**Cons:** Requires charting logic duplication; different library than Recharts; more implementation work.

**Key risk:** Chart styling divergence from UI.

**Complexity:** High.

---

### Option C: Puppeteer / Playwright (Full-page screenshot)
**Description:** Navigate to welder report, screenshot full page, convert to PDF.

**Pros:** Pixel-perfect match to UI.

**Cons:** Spec explicitly disallows; heavy dependency; slow; overkill for single-page report.

**Key risk:** Spec violation; maintenance burden.

**Complexity:** High.

---

### Option D: PDF without chart
**Description:** Ship PDF with score, summary, feedback only. Add chart later.

**Pros:** Zero chart complexity; unblocks export quickly.

**Cons:** Incomplete report; chart is in acceptance criteria.

**Complexity:** Low.

---

## 6. Prototype Results

### Prototype 1: html-to-image capture utility

**What was tested:** `toPng` on a div containing Recharts SVG; need for fixed dimensions.

**Code:** `my-app/prototype/pdf-chart-capture.ts`

```typescript
import { toPng } from "html-to-image";

export async function captureChartToBase64(elementId: string): Promise<string | null> {
  const el = document.getElementById(elementId);
  if (!el) return null;
  try {
    return await toPng(el, { cacheBust: true, pixelRatio: 2 });
  } catch {
    return null;
  }
}
```

**Result:** Code structure validated. Actual execution requires `npm install html-to-image` and a browser. html-to-image supports SVG; Recharts renders SVG. Known risk: ResponsiveContainer with 100% width needs parent with explicit width/height (e.g. 600×200px) for consistent capture.

**Decision:** Proceed. Fallback: if `toPng` fails or element missing → pass `chartDataUrl: null`; PDF omits chart section per spec.

---

### Prototype 2: @react-pdf/renderer renderToBuffer

**What was tested:** `renderToBuffer` in Node; React PDF Document/Page/Text.

**Code:** `my-app/prototype/pdf-route.mts`

```typescript
import { Document, Page, View, Text, StyleSheet, renderToBuffer } from "@react-pdf/renderer";
// ... minimal Document with Text
const buffer = await renderToBuffer(React.createElement(Doc));
```

**Result:** Prototype written. Execution requires `npm install @react-pdf/renderer`. Library docs and community usage show `renderToBuffer` works in Node. Next.js API route runs in Node; no Edge runtime.

**Decision:** Proceed. If Next.js 16 / React 19 cause issues, isolate PDF render in a helper and test separately.

---

### Prototype 3: downloadCSV pattern for PDF

**What was tested:** Reuse of blob → createObjectURL → download pattern.

**Existing code:** `lib/export.ts` `downloadCSV`. Supervisor uses `downloadCSV(filename, csv)` after `generateCSV`.

**Result:** PDF download: `const blob = await res.blob(); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);` — identical pattern. No prototype needed.

**Decision:** Proceed; pattern is established.

---

## 7. Recommended Approach

**Chosen approach:** Option A — @react-pdf/renderer + html-to-image (client chart capture)

**Justification (min. 150 words):** Option A aligns with the spec, uses PDF-native layout instead of screenshots, and keeps the chart in sync with the UI. The supervisor CSV export pattern (client-side generation, blob download) already exists; we extend it to a POST → blob flow for PDF. html-to-image is widely used with Recharts; the main risk is SVG capture in some browsers — mitigated by omitting the chart when capture fails. chartjs-node-canvas (Option B) would duplicate chart logic and stray from Recharts; Puppeteer (Option C) is ruled out by the spec. The implementation is moderate in complexity: add `id="trend-chart"` to a fixed-size LineChart wrapper, call `toPng` before POST, validate payload in the API route, and render a single-page PDF. `@react-pdf/renderer` stays server-side; `html-to-image` stays client-side, so bundle impact is limited to html-to-image (~15KB gzipped). Performance is acceptable for a single-page report; base64 chart size is bounded by the fixed div dimensions we use for capture.

**Trade-offs accepted:**
- Chart may be omitted when html-to-image fails → PDF still usable.
- Base64 chart in POST body (~50–200 KB) vs. smaller payload with server-side chart.
- Heatmap not in PDF (Phase 1); follow-up if needed.

**Fallback approach:** Option D — Ship PDF without chart. Trigger: html-to-image proves unreliable across target browsers. Mitigation: placeholder text "Chart unavailable" in PDF.

---

## 8. Architecture Decisions

**Decision: Chart capture strategy**
- Options considered: html-to-image (client), chartjs-node-canvas (server), omit chart
- Chosen: html-to-image on client
- Reason: Spec mandates Option A; fastest path; fallback to omit chart.
- Reversibility: Easy — swap to server chart later.
- Downstream impact: Client needs `id="trend-chart"` wrapper; API accepts `chartDataUrl` as optional.

**Decision: API route structure**
- Options considered: `app/api/.../route.ts`, `pages/api/...`
- Chosen: `app/api/welder-report-pdf/route.ts`
- Reason: App Router is used; no `pages/api` in project.
- Reversibility: Easy.
- Downstream impact: First API route; establishes convention.

**Decision: PDF render target**
- Options considered: renderToBuffer, renderToStream
- Chosen: renderToBuffer
- Reason: Single-page PDF; buffer is small; simpler handler.
- Reversibility: Easy — switch to stream if memory becomes an issue.
- Downstream impact: Route returns `new Response(buffer, { headers })`.

**Decision: State management for download**
- Options considered: Local state (useState), no state
- Chosen: Local state (`pdfLoading`, `pdfError`)
- Reason: Same pattern as supervisor `exporting`, `exportError`.
- Reversibility: Easy.
- Downstream impact: Button disabled during generation; error message shown inline.

**Decision: PDF component location**
- Options considered: `components/pdf/`, `app/api/...` inline
- Chosen: `components/pdf/WelderReportPDF.tsx`
- Reason: Reusable; testable; keeps route thin.
- Reversibility: Easy.
- Downstream impact: Route imports component; component receives welder, score, feedback, chartDataUrl.

---

## 9. Edge Cases

### Empty / null / missing data
| Scenario | Handling | Graceful? |
|----------|----------|-----------|
| `feedback.feedback_items` empty | PDF shows empty Key Areas; no crash | Yes |
| `feedback.summary` empty | Render empty string or "-" | Yes |
| `chartDataUrl` null | Omit chart section; show nothing | Yes |
| `welder.name` null/undefined | Use "Unknown" or sanitized fallback | Yes |
| `score.total` undefined | Use 0 or "-" | Yes |

### Maximum scale
| Scenario | Handling | Graceful? |
|----------|----------|-----------|
| feedback_items length > 3 | Slice to 3 per spec | Yes |
| Base64 chart > 500 KB | Accept; single page; acceptable | Yes |
| Very long summary text | PDF may overflow; consider truncation | Partial |

### Concurrent or rapid user actions
| Scenario | Handling | Graceful? |
|----------|----------|-----------|
| Double-click Download PDF | Button disabled; `pdfLoading` true | Yes |
| Click PDF while page still loading | Button should be disabled until report loaded | Yes |
| Navigate away during generation | Fetch may abort; no state update on unmounted component | Yes |

### Network failures and timeouts
| Scenario | Handling | Graceful? |
|----------|----------|-----------|
| API returns 500 | Catch; set `pdfError`; show message | Yes |
| API returns 400 (validation) | Parse body.detail; show validation message | Yes |
| Request timeout | Catch; show "Request timed out" | Yes |
| Network offline | Fetch throws; catch and display | Yes |

### Browser / device / accessibility
| Scenario | Handling | Graceful? |
|----------|----------|-----------|
| html-to-image fails (e.g. Safari quirks) | Catch; pass null; PDF without chart | Yes |
| Print/PDF from browser | N/A; we return binary PDF | — |
| Screen reader on Download button | `aria-label`, `disabled` when loading | Yes |

### Permission or session
| Scenario | Handling | Graceful? |
|----------|----------|-----------|
| Welder page requires auth (future) | Not in scope; route may need auth later | — |
| CORS on API route | Same-origin; no CORS for POST from same app | Yes |

---

## 10. Risk Analysis

| Risk | Prob | Impact | Early warning | Mitigation |
|------|------|--------|---------------|------------|
| html-to-image fails on Recharts SVG | Med | High | Blank/invalid PNG or thrown error | Fallback: omit chart; try/catch; document browser matrix |
| @react-pdf/renderer + React 19 / Next 16 incompatibility | Low | High | Build or runtime error in API route | Test in CI; pin versions; isolate render in helper |
| Base64 chart bloats POST, timeout | Low | Med | Slow upload; 413 | Cap capture size (e.g. 600×200); acceptable for MVP |
| Welder name → invalid filename | Low | Low | Download fails or invalid filename | Sanitize: `replace(/[^a-zA-Z0-9_-]/g, '-')` |
| LineChart not rendered when user clicks | Med | Low | chartDataUrl null | Disable button until report loaded; trend section visible |
| API route timeout on slow render | Low | Med | 504 or hang | Set fetch timeout; return 503 with retry hint |
| renderToBuffer memory spike | Low | Low | OOM on server | Single page; small; monitor |
| downloadCSV-style anchor not in DOM | Low | Low | Download doesn't trigger (Safari) | Append anchor to body if needed; test |
| feedback_items undefined causes crash | Low | Med | PDF route 500 | Guard: `feedback?.feedback_items ?? []` |
| **CRITICAL:** html-to-image unreliable across target browsers | Med | High | Multiple user reports of missing chart | Phase 1: ship with fallback; Phase 2: chartjs-node-canvas if needed |

---

## 11. Exploration Summary

**Files to create:**
- `my-app/src/components/pdf/WelderReportPDF.tsx` — PDF layout (Document, Page, View, Text, Image)
- `my-app/src/app/api/welder-report-pdf/route.ts` — POST handler; validate body; renderToBuffer; return PDF

**Files to modify:**
- `my-app/src/app/seagull/welder/[id]/page.tsx` — Add `id="trend-chart"` wrapper around LineChart with fixed dimensions; replace stub with `handleDownloadPDF`; add `pdfLoading`, `pdfError` state; call `toPng` then POST
- `my-app/src/components/charts/LineChart.tsx` — Optional: accept wrapper props for id; or wrap at call site
- `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` — Replace alert test with fetch mock; assert POST to `/api/welder-report-pdf` with payload shape; assert download triggered or loading state

**New dependencies:** `@react-pdf/renderer` (server), `html-to-image` (client)

**Bundle impact:** ~15 KB gzipped (html-to-image); @react-pdf/renderer in API route only (not in client bundle)

**Critical path order:**
1. Install dependencies
2. Create `WelderReportPDF.tsx` with mock data; verify renderToBuffer in isolation
3. Create `app/api/welder-report-pdf/route.ts`; test with curl
4. Add `id="trend-chart"` wrapper to LineChart in welder page
5. Implement handleDownloadPDF (toPng → POST → blob download); wire button
6. Add validation (welder, score, feedback required); 400 on failure
7. Update tests

**Effort estimate:** Frontend 4h + Backend 3h + Testing 2h + Review 2h = **Total 11h**, confidence 75%

**Blockers for planning:** None. Optional: confirm `@react-pdf/renderer` compatibility with Next 16 / React 19 in CI before full implementation.
