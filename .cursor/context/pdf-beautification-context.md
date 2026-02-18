# PDF Beautification — Context

> **For AI:** Use when working on welder report PDF, chart capture, or /api/welder-report-pdf. Do not reimplement; extend existing patterns.

---

## What Exists

**Beautiful PDF welder report** — dark theme, score circle, coach feedback, optional score-trend chart (client-captured PNG), key areas with severity bullets. Generated server-side via @react-pdf/renderer.

---

## Key Files

| File | Purpose |
|------|---------|
| `my-app/src/app/api/welder-report-pdf/route.ts` | POST handler — validates body, renders WelderReportPDF, returns application/pdf |
| `my-app/src/components/pdf/WelderReportPDF.tsx` | PDF layout — Document, Page, View, Text, Image; sanitizeText for control chars |
| `my-app/src/lib/pdf-chart-capture.ts` | captureChartToBase64(elementId) — html-to-image toPng, 10s timeout |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Download PDF button, handleDownloadPDF, trend-chart id for capture |

---

## API Contract

**POST /api/welder-report-pdf**

- **Body:** `{ welder: { name }, score: { total, rules }, feedback: { summary, feedback_items }, chartDataUrl? }`
- **chartDataUrl:** Optional; must be `data:image/png;base64,...`; max 2MB.
- **Limits:** Body 5MB; chunked encoding not supported (411).
- **Response:** `application/pdf` with `Content-Disposition: attachment; filename="{name}-warp-report.pdf"`
- **Validation:** welder required; score.total number; feedback_items array with message+severity per item.

---

## Flow

1. User clicks "Download PDF" on welder report.
2. `captureChartToBase64("trend-chart")` captures LineChart DOM to base64 PNG (or null if failed/timeout).
3. POST to `/api/welder-report-pdf` with welder, score, feedback, chartDataUrl.
4. Route validates, renders WelderReportPDF, returns PDF buffer.

---

## WelderReportPDF Props

```ts
welder: { name: string }
score: { total: number }
feedback: { summary: string; feedback_items: Array<{ message, severity, suggestion? }> }
chartDataUrl?: string | null  // data:image/png;base64,... only
```

---

## Constraints

- **Server-only render:** @react-pdf/renderer runs in Node; no DOM/canvas in component.
- **Text sanitization:** sanitizeText() strips control chars, zero-width, RTL override; replaces < > with ‹ ›.
- **Chart capture:** Client-side only; element must have id="trend-chart"; 10s timeout; null on failure.

---

## Logging

- Use `logError` from `@/lib/logger` for PDF generation failures (not console.error).
