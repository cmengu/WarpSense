# Issue: PDF Report — Letter Page Size & Layout Alignment

**Type:** Improvement  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `pdf` `report` `investor-facing` `design`

---

## TL;DR

Align the welder PDF report with the reference design: **letter page size** (8.5×11") and layout structure. Current `WelderReportPDF` uses default React-PDF sizing. Reference spec uses `reportlab.lib.pagesizes.letter` with WarpSense branding, compliance panel, coach feedback, score trend chart, and key areas.

---

## Current State vs Expected Outcome

### Current State
- **Stack:** `@react-pdf/renderer` in `WelderReportPDF.tsx` — no explicit page size set (React-PDF defaults)
- **API:** `POST /api/welder-report-pdf` renders via `WelderReportPDF`
- **Layout:** Dark theme (#0a0a0a), score circle, feedback, narrative, certifications — different structure than reference

### Expected Outcome
- **Page size:** Letter (612×792 pt / 8.5×11")
- **Layout alignment:** Match reference structure where feasible:
  - Top bar with WARPSENSE branding, operator name, session meta, score circle
  - Compliance panel (Heat Input, Torch Angle, Arc Termination with PASS/FAIL badges)
  - Coach feedback section
  - Score trend chart (last 5 sessions)
  - Key areas for improvement (color-coded bullets)
  - Footer with "CONFIDENTIAL — Internal use only"

---

## Reference Design (reportlab snippet)

The provided Python/reportlab script defines:
- `W, H = letter` (612×792 pt)
- Color palette: `BG`, `PANEL`, `BORDER`, `ACCENT`, `TEXT_PRI`, `TEXT_SEC`, `GREEN`, `RED`, `AMBER`
- `rr()` rounded-rect helper, `badge()` for PASS/FAIL
- Sections: Compliance, Coach Feedback, Score Trend, Key Areas

**Note:** Our stack is React-PDF, not reportlab. Port the design — do not introduce Python PDF generation in the Next.js flow.

---

## Relevant Files

| File | Purpose |
|------|---------|
| `my-app/src/components/pdf/WelderReportPDF.tsx` | React-PDF layout; add `Page` `size="LETTER"` and restructure sections |
| `my-app/src/app/api/welder-report-pdf/route.ts` | Pass any new props (e.g. score trend, compliance rows) to `WelderReportPDF` |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Page that triggers PDF download; may need to pass additional data |

---

## Risk / Notes

- **Data availability:** Score trend (last 5 sessions) requires fetching session history — may need new API or expand `reportSummary`. Defer if not wired.
- **Chart in PDF:** Reference uses reportlab `arc`, `line`, `circle`. React-PDF has `Svg`; gradient fill under line is more involved. Consider simplified bar/line or image embed.
- **Minimal first step:** If full redesign is deferred, at least set `size="LETTER"` on `Page` for consistent print/save.

---

## Vision Alignment

From `vision.md`:
- "Something they can forward — a PDF report, a link, a screenshot that travels on its own"
- "The test: Can they send something to someone else after the meeting? If yes: the demo worked."

PDF report quality directly supports investor demos. Letter size is standard for US/investor handouts.

---

## Acceptance Criteria

- [ ] PDF page size is letter (8.5×11")
- [ ] Layout matches reference structure (top bar, compliance, coach feedback, key areas) where data exists
- [ ] PASS/FAIL badges for compliance rows when `reportSummary` is present
- [ ] Footer includes "CONFIDENTIAL — Internal use only"
- [ ] Existing tests (`welder-report-pdf.test.ts`, `WelderReportPDF` usage) pass
