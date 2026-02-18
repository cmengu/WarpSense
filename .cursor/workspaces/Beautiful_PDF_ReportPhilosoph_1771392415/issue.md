
Created the issue specification at `.cursor/issues/beautiful-pdf-report.md`.

**Summary of the issue:**

- **Title:** `[Feature] Welder report PDF export via @react-pdf/renderer`
- **Scope:** Replace the stub "Download PDF" button on `/seagull/welder/[id]` with real export logic.
- **Approach:** PDF-native layout with `@react-pdf/renderer`; chart via `html-to-image` (client) → base64 PNG → POST to `/api/welder-report-pdf`.

**Findings from codebase:**

1. **Welder report page** at `my-app/src/app/seagull/welder/[id]/page.tsx` has the stub button and all needed data: `report`, `score`, `welder`, `LineChart`.
2. **`LineChart`** has no `id="trend-chart"`; the wrapper needs this for capture.
3. **No `/app/api` routes** exist yet; the PDF route will be new.
4. **Dependencies:** `@react-pdf/renderer` and `html-to-image` must be added.
5. **Tests:** `page.test.tsx` asserts the alert; it must be updated to cover the real download flow (or a mocked fetch).

**Out of scope in the spec:** Heatmap in PDF, Email report, demo team page export. Heatmap is left for a follow-up because the spec says to start with Option A (chart only).
