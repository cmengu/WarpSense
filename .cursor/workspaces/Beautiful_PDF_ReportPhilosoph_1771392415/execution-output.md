
All planned steps are implemented. Summary:

---

# Implementation Complete

Summary of what was implemented:

---

## Step 1: Install Dependencies

### What Was Done
- **File:** `my-app/package.json`
  - **Updated:** Added `@react-pdf/renderer@3.4.0` and `html-to-image@1.11.11` (exact versions)
  - **Rationale:** Plan requires exact pinning; no `^` used

### Verification
Run `cd my-app && npm install` to install the new packages. `package-lock.json` must be committed before Phase 2 as described in the plan.

---

## Step 2: PDF Component, Chart Capture, and API Base

### Implementation Details

**Created:** `my-app/src/components/pdf/WelderReportPDF.tsx`
- Uses @react-pdf/renderer (Document, Page, View, Text, Image, StyleSheet)
- Dark theme (#0a0a0a)
- Props: `welder`, `score`, `feedback`, `chartDataUrl`
- `sanitizeText()` – strips control chars, zero-width, RTL override
- `toWelderName()` – coerces `welder.name`; non-string/whitespace → `"Unknown"`
- `isPngDataUrl()` – accepts only `data:image/png`
- Defensive filtering for `feedback_items`; only top 3 rendered

**Created:** `my-app/src/lib/pdf-chart-capture.ts`
- `captureChartToBase64(elementId)` with 10s timeout
- `.catch(() => {})` on `toPng` to avoid unhandledrejection on timeout

**Created:** `my-app/src/lib/api-base.ts`
- `getApiBase()` for basePath when `NEXT_PUBLIC_BASE_PATH` is set

---

## Step 3: PDF API Route

### Implementation Details

**Created:** `my-app/src/app/api/welder-report-pdf/route.ts`
- Content-Length: 400 on invalid, 413 when > 5MB
- 411 when Transfer-Encoding chunked without Content-Length
- Body validation for welder, score, feedback
- `feedback_items` validated and filtered
- `chartDataUrl` only `data:image/png`, max 2MB
- `toWelderName` for welder name
- `sanitizeFilename` for filename
- Renders PDF via `renderToBuffer(WelderReportPDF)`
- Returns `application/pdf` with `Content-Disposition: attachment`

---

## Step 4: Prototype Smoke Test

### Implementation Details

**Updated:** `my-app/prototype/pdf-route.mts`
- Replaced minimal PDF with `WelderReportPDF`
- Sample props (Mike Chen, 75, Good work, PNG chart)
- Header `%PDF-`
- Content check for name, score, summary
- Malformed `feedback_items` still renders valid items
- `welder.name` as object → `"Unknown"`, no `[object Object]`

---

## Step 5: Client Integration

### Implementation Details

**Updated:** `my-app/src/app/seagull/welder/[id]/page.tsx`
- Chart wrapper: `id="trend-chart"`, `style={{ width: 600, height: 200 }}`, `data-testid="trend-chart"`
- `handleDownloadPDF`:
  - `captureChartToBase64("trend-chart")`
  - POST to `getApiBase() + '/api/welder-report-pdf'`
  - Uses `toWelderName(displayName)` and `sanitizeDownloadFilename`
  - Download via blob + `URL.createObjectURL`
  - Error handling with `logError`
- `pdfLoading`, `pdfError` state
- Button disabled when loading or `pdfLoading`
- PDF error message shown inline

---

## Step 6: Tests

### Implementation Details

**Created:** `my-app/src/__tests__/lib/api-base.node.test.ts`
- Node: `getApiBase()` returns `""` when `window` is undefined

**Created:** `my-app/src/__tests__/lib/api-base.jsdom.test.ts`
- jsdom: base path with/without trailing slash, unset

**Created:** `my-app/src/__tests__/api/welder-report-pdf.test.ts`
- 200 PDF with valid payload
- 400: missing welder, `score.total` string, oversized `chartDataUrl`, invalid Content-Length
- 411: chunked without Content-Length
- 413: body > 5MB (skipped when `CI_LOW_MEM=1` and `CI=true`/`CI=1`)
- `welder.name` object → `"Unknown"`, no `[object Object]`
- toWelderName invariant for null/undefined/array

**Updated:** `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx`
- Mock `html-to-image` `toPng`
- Download PDF: POST with correct payload, button disabled while generating
- Chart capture fail: `chartDataUrl: null`
- `trend-chart` wrapper with 600×200
- Restore `fetch` and `toPng` in `afterEach` / `finally`

---

## Implementation Summary

### Files Created

1. `my-app/src/components/pdf/WelderReportPDF.tsx` – PDF layout component  
2. `my-app/src/lib/pdf-chart-capture.ts` – Chart capture helper  
3. `my-app/src/lib/api-base.ts` – API base path helper  
4. `my-app/src/app/api/welder-report-pdf/route.ts` – PDF API route  
5. `my-app/src/__tests__/lib/api-base.node.test.ts` – Node tests for `getApiBase`  
6. `my-app/src/__tests__/lib/api-base.jsdom.test.ts` – jsdom tests for `getApiBase`  
7. `my-app/src/__tests__/api/welder-report-pdf.test.ts` – API route tests  

### Files Modified

1. `my-app/package.json` – Added `@react-pdf/renderer` and `html-to-image`  
2. `my-app/prototype/pdf-route.mts` – Uses `WelderReportPDF`  
3. `my-app/src/app/seagull/welder/[id]/page.tsx` – Chart wrapper, `handleDownloadPDF`, state  
4. `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` – Download PDF tests, mocks  

### Feature Completeness Checklist

- [x] All steps from plan implemented (6 phases)  
- [x] Edge cases handled (invalid welder/score/feedback, chart limits)  
- [x] Error handling and validation on API route  
- [x] Types and interfaces added  
- [x] No TODO/placeholder comments  
- [x] Matches existing code style  
- [x] Integrated with existing welder page and API  

### Manual Verification

1. `cd my-app && npm install`
2. `npm run dev` and open `http://localhost:3000/seagull`
3. Click a welder (e.g. Mike Chen)
4. Click "Download PDF" – verify download and content
5. Run prototype: `npx tsx prototype/pdf-route.mts` – expect exit 0 and "Content check: OK"
6. Run tests: `npm test -- --testPathPattern="welder/\[id\]/page|api-base|welder-report-pdf"`

### Known Limitations

- **html-to-image:** Can fail on Recharts in some browsers; PDF is still generated without the chart.
- **basePath:** Set `NEXT_PUBLIC_BASE_PATH` at build if `next.config` uses a basePath.
- **CI OOM:** If the 413 test OOMs in CI, set `CI_LOW_MEM=1` and `CI=true` (or `CI=1`).

---

# Implementation Status: COMPLETE

All steps from the plan are implemented. Ready for `npm install`, manual testing, and review.
