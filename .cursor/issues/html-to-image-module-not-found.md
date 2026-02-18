# Module not found: Can't resolve 'html-to-image'

**Type:** bug  
**Priority:** high  
**Effort:** low

---

## TL;DR

`pdf-chart-capture.ts` imports `html-to-image` for chart→PNG capture. Build/runtime fails with "Module not found" even though the package is listed in `package.json`.

---

## Current vs Expected

| Current | Expected |
|---------|----------|
| `import { toPng } from "html-to-image"` fails at build/SSR | Chart capture works; PDF download includes trend chart |

---

## Relevant Files

- `my-app/src/lib/pdf-chart-capture.ts` — imports `toPng` from `html-to-image`
- `my-app/package.json` — has `"html-to-image": "1.11.11"` in dependencies
- `my-app/src/app/seagull/welder/[id]/page.tsx` — uses `captureChartToBase64`

---

## Likely Causes

1. **Dependencies not installed** — `npm install` not run after adding the package
2. **Next.js bundling** — `html-to-image` may need `transpilePackages` or dynamic import if it has CJS/ESM issues
3. **SSR** — `pdf-chart-capture` is imported by a client component; `html-to-image` is browser-only; if it gets pulled into SSR, it can fail

---

## Risk / Notes

- PDF download still works without chart (chartDataUrl is optional); `captureChartToBase64` returns null on failure
- Tests mock `html-to-image`; the issue is in real build/runtime

---

## Suggested Fix

1. Run `npm install` in `my-app/`; ensure `node_modules/html-to-image` exists
2. If still failing: ensure `html-to-image` is only used client-side. Consider dynamic import:
   ```ts
   const { toPng } = await import("html-to-image");
   ```
   inside `captureChartToBase64` (which runs only in browser)
3. If Next.js bundling issue: add `html-to-image` to `transpilePackages` in `next.config.js` if needed

---

## Vision

PDF welder report with embedded score trend chart improves coach feedback and shareability. Fixing this unblocks the full PDF beautification flow.
