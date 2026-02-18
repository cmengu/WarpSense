# Beautiful PDF Report

## 1. Title
`[Feature] Welder report PDF export via @react-pdf/renderer`

---

## 2. TL;DR

Users on the welder report page (`/seagull/welder/[id]`) cannot export a professional PDF. The "Download PDF" button currently shows an alert. This blocks supervisors and welders from sharing session reports with managers or for records. Implement PDF generation using `@react-pdf/renderer` — a PDF-native layout (no DOM screenshots). Pre-render the Recharts trend chart to base64 PNG client-side via `html-to-image`, POST to a Next.js API route, return a downloadable PDF. Effort: ~12–16h.

---

## 3. Root Cause Analysis

1. **Surface:** "Download PDF" button shows alert instead of downloading a PDF.
2. **Why:** The button was a stub; no PDF generation logic was implemented.
3. **Why stub:** Seagull pilot prioritized in-app UI over export; export was deferred.
4. **Why deferred:** Recharts cannot render in PDF (no DOM); chart capture adds complexity.
5. **Root cause:** No first-class PDF export path existed; chart-in-PDF required a separate capture pipeline that was never built.

---

## 4. Current State

**What exists today:**

| File / component | Description |
|------------------|-------------|
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Welder report page; displays score, AI summary, heatmaps, FeedbackPanel, LineChart, and stub Download PDF button |
| `my-app/src/components/charts/LineChart.tsx` | Recharts-based line chart; no wrapper `id` for DOM capture |
| `my-app/src/components/welding/FeedbackPanel.tsx` | Renders `feedback_items` from `AIFeedbackResult` |
| `my-app/src/lib/ai-feedback.ts` | `generateAIFeedback(session, score, historical)` → `AIFeedbackResult` |
| `my-app/src/types/ai-feedback.ts` | `AIFeedbackResult`, `FeedbackItem` types |
| `my-app/src/lib/api.ts` | `SessionScore` interface, `fetchScore` |
| `my-app/src/lib/export.ts` | `generateCSV`, `downloadCSV` (supervisor export) |
| `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` | Tests Download PDF button shows alert |
| `my-app/package.json` | No `@react-pdf/renderer`, no `html-to-image` |

**What's broken or missing:**

| Gap | User wants | Current behavior | Why it fails |
|-----|------------|------------------|--------------|
| PDF export | Click "Download PDF" and get a report file | Alert "Download PDF — coming soon" | No handler; no API route; no PDF component |
| Chart in PDF | Trend chart visible in exported PDF | N/A | Recharts is DOM-only; @react-pdf/renderer cannot render Recharts |
| PDF layout | Professional, shareable report | N/A | No PDF layout component |
| API route | Server-side PDF generation | N/A | No `app/api/` route exists |

**Workarounds:** Users manually screenshot the page (low fidelity, inconsistent layout).

---

## 5. Desired Outcome

**User flow after fix:**

1. **Primary flow:** User opens `/seagull/welder/mike-chen` → report loads (score, AI summary, heatmaps, feedback, trend chart) → clicks "Download PDF" → chart div is captured to base64 PNG via `html-to-image` → client POSTs `{ welder, score, feedback, chartDataUrl }` to `/api/welder-report-pdf` → API renders `WelderReportPDF` with `renderToBuffer` → returns PDF → browser downloads `{welder.name}-warp-report.pdf`.
2. **Chart absent:** If chart element is missing or capture fails → PDF still generates; chart section omitted or shows "Chart unavailable."
3. **Error state:** If API returns 4xx/5xx → user sees inline error message; no silent failure.

**Acceptance criteria:**

1. User can click "Download PDF" on `/seagull/welder/[id]` and receive a PDF file.
2. PDF contains welder name, session date, total score (e.g. 75/100), and skill level + trend.
3. PDF contains AI coach summary (`feedback.summary`).
4. PDF contains up to 3 key feedback items with severity indicator (⚠ or •), message, and suggestion when present.
5. PDF contains "Score Trend (Last 5 Sessions)" section with embedded chart image when `chartDataUrl` is provided.
6. PDF footer shows "WarpSense Quality Intelligence" and "CONFIDENTIAL."
7. Filename is `{welder.name}-warp-report.pdf` (sanitized for filesystem).
8. LineChart wrapper has `id="trend-chart"` for capture; capture runs before POST.
9. API route validates required fields; returns 400 with descriptive error when `welder`, `score`, or `feedback` missing.
10. Download PDF button shows loading state during generation; disables to prevent double-click.
11. Existing unit test updated: Download PDF no longer shows alert; test asserts fetch to `/api/welder-report-pdf` with correct payload shape (or mocks and asserts download flow).

**Out of scope:**

1. **Heatmap in PDF** — Task spec mentions `heatmapUrl` in layout; capturing HeatMap (canvas/SVG) is more complex. Ship without heatmap; add in follow-up if needed.
2. **Email report** — Email Report button remains stub; separate feature.
3. **Demo team page PDF** — `/demo/team/[welderId]` has no PDF button; only Seagull welder report in scope.

---

## 6. Constraints

- **Tech stack:** Must use `@react-pdf/renderer` (PDF-native layout; no Puppeteer, no canvas capture of full page).
- **Chart capture:** Start with Option A — `html-to-image` `toPng` on client; no `chartjs-node-canvas` for Phase 1.
- **Performance:** API response time target < 3s for single-page PDF; bundle impact: add `html-to-image` (~15KB gzipped) and `@react-pdf/renderer` (server-only in API route).
- **Environment:** Next.js 16; API route runs server-side; `@react-pdf/renderer` requires Node (no Edge runtime for PDF render).
- **Verification:** Per `.cursorrules` — add and run automated tests; no manual browser checks only.
- **Blocked by:** None.
- **Blocks:** Email report (different feature).

---

## 7. Risks

| Risk | Prob | Impact | Mitigation |
|------|------|--------|------------|
| `html-to-image` fails on Recharts (SVG/canvas quirks) | Med | High | Fallback: omit chart in PDF; add placeholder "Chart unavailable"; document known browser differences |
| `@react-pdf/renderer` SSR/compatibility with Next.js 16 | Low | High | Use dynamic import in API route; test in CI; fallback to renderToBuffer in Node |
| Large base64 chart bloats POST body | Low | Med | Resize/crop chart div before capture; cap dimensions (e.g. 600×200px) |
| Welder name contains special chars → invalid filename | Low | Low | Sanitize: `welder.name.replace(/[^a-zA-Z0-9_-]/g, '-')` |
| API route timeout on slow renders | Low | Med | Set reasonable timeout; return 503 with retry hint |
| LineChart hidden/not rendered when user clicks before load | Med | Low | Disable button until report loaded; ensure trend section is visible |
| `renderToBuffer` memory spike for large feedback | Low | Low | Single page; cap feedback_items to 3; acceptable for MVP |

---

## 8. Open Questions

| Question | Assumption | Confidence | Resolver |
|----------|------------|------------|----------|
| Should PDF use dark theme (#0a0a0a) as in task spec? | Yes — match spec; dark layout is acceptable for industrial context | Med | PM/design |
| Include heatmap in PDF in Phase 1? | No — task says start with Option A for chart only | High | — |
| Use `renderToBuffer` vs `renderToStream`? | `renderToBuffer` — simpler; single-page PDF is small | High | — |
| Support demo team page (`/demo/team/[welderId]`)? | Out of scope | High | — |

---

## 9. Classification

- **Type:** feature
- **Priority:** P2 (standard — improves shareability; not production-blocking)
- **Effort:** M (8–16h)
- **Effort breakdown:** Frontend 4h + Backend 4h + Testing 2h + Review 2h = Total 12h
