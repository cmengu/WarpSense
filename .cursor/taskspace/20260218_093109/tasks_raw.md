
Here is the CTO task generation output:

---

```markdown
════════════════════════════════════════════════════════════════
🧠 CTO REASONING — PRE-TASK
════════════════════════════════════════════════════════════════

**The specific human:** Seed investors. They must say "yes" to writing a check in the next 5 days. The test: can they send something (link, PDF, screenshot) to a partner after the meeting? If yes, the demo worked.

**Biggest obstacle:** The demo and landing exist, but there is no forwardable artifact and no confirmed public URL. Localhost-only demos are worth nothing to investors. Without a live URL and something they can email, they cannot say yes.

**Existing leverage:** 
- `/demo` is browser-only (demo-data.ts, zero backend); `/demo/team` with guided tour, expert vs novice scores (94/42)
- Landing at `/` with CTAs to `/demo`; DemoTour auto-starts
- `lib/export.ts` (generateCSV, downloadCSV) — pattern for client-side generation
- Next.js static/client pages — deployable to Vercel without backend

**Pre-mortem failure mode:** We build polish (refactor, internal docs) instead of closing the investor gap. Plan fails if: (a) demo stays localhost, (b) nothing is forwardable (PDF or share), (c) tasks are internal. These tasks directly address (a) and (b).
════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════
🧠 CTO TASK PRIORITIZATION — TOP 3
════════════════════════════════════════════════════════════════

Primary Goal: Raise a seed round from investors
Time Constraint: 5 days until next hard deadline
Specific Human: Seed investors
Context Type: general
Average Priority: 9.0/10

---

## 🔥 Task 1 — Deploy Demo + Landing to Public URL

**Priority:** 9.5/10 | **Effort:** 2–4hrs | **Risk:** Low

**Passes filters:** Real Human ✅ | 48hr Demo ✅ | Reversible ✅ | 10x ✅

**Demo line:**
> Investor opens https://[your-app].vercel.app/demo on their phone. Sees expert vs novice replay, scores, guided tour. No backend, no setup. Shareable link works.

**Why this is 10x not 1x:**
Without a live URL, everything else is internal. The vision says "one URL to 100 prospects." Localhost demos do not close the investor conversation. A public URL is the prerequisite for any forwardability.

**Karpathy check:**
Demo and landing are 100% client-side (demo-data.ts, no fetchSession). Next.js can deploy to Vercel with `vercel --prod` or GitHub → Vercel. Reuse existing `my-app/` build; no schema changes. DEPLOY.md covers Docker; this task adds or documents a frontend-only path for investor demos.

**Acceptance criteria:**
- [ ] Investor can open https://[domain]/demo on any device without running Docker or backend
- [ ] Landing at / and demo at /demo render correctly; guided tour appears
- [ ] URL is stable and shareable (e.g. Vercel preview or production)

**Command:**
```bash
./agent "Deploy the Next.js frontend (my-app) to a public URL so /demo and / work without backend. Use Vercel (vercel deploy --prod) or equivalent. Ensure NEXT_PUBLIC_API_URL is not required for /demo (browser-only). Document the resulting URL in DEPLOY.md under 'Investor Demo URL'. Verify: open /demo on mobile/laptop, confirm expert vs novice replay loads and guided tour shows."
```

---

## 🔥 Task 2 — Demo Page: Print/Save-as-PDF Report

**Priority:** 9.0/10 | **Effort:** 4–6hrs | **Risk:** Low

**Passes filters:** Real Human ✅ | 48hr Demo ✅ | Reversible ✅ | 10x ✅

**Demo line:**
> Investor clicks 'Download report' on /demo. Print dialog opens with a clean layout (scores, expert vs novice summary, 1–2 sentence value prop). They choose 'Save as PDF' and email it to their partner.

**Why this is 10x not 1x:**
The vision: "Can they send something to someone else after the meeting?" A PDF is forwardable. Dual-audience: investors share with partners; operators/managers get factual reports. This closes the gap between "I saw a demo" and "I sent you the proof."

**Karpathy check:**
Reuse demo-config (MOCK_EXPERT_SCORE_VALUE, MOCK_NOVICE_SCORE_VALUE), layout from demo page. Add a "Download report" button that triggers `window.print()`. Add print-specific CSS via `@media print` that hides nav, 3D canvas, controls; shows scores, labels, and a 2-line value prop. No new deps. Follow existing `lib/export.ts` pattern for client-side generation of a downloadable artifact.

**Acceptance criteria:**
- [ ] Button "Download report" (or "Print report") visible on /demo header area
- [ ] Click opens print dialog; print preview shows expert vs novice scores (94/42), labels, and value-prop text
- [ ] User can "Save as PDF" from browser; resulting PDF is readable and shareable

**Command:**
```bash
./agent "Add a 'Download report' button to my-app/src/app/demo/page.tsx (in the header near 'See Team Management'). On click, call window.print(). Add print styles in a @media print block (or global print stylesheet) that: hide nav, playback controls, 3D canvases; show expert/novice scores (94/42), labels 'Expert Welder' and 'Novice Welder', and a 2-sentence value prop (e.g. 'WarpSense compares expert vs novice welding technique in real time. Scores come from 5 quality rules.'). Ensure the print layout is readable when saved as PDF. Add a test that the button exists and is clickable."
```

---

## ⚡ Task 3 — Demo Share Button (Copy Link + Email)

**Priority:** 8.5/10 | **Effort:** 1–2hrs | **Risk:** Low

**Passes filters:** Real Human ✅ | 48hr Demo ✅ | Reversible ✅ | 10x ✅

**Demo line:**
> Investor clicks "Share with partner." URL copies to clipboard. Toast: "Link copied." Optional: "Email" opens mailto with subject "WarpSense demo — expert vs novice comparison" and body containing the demo URL.

**Why this is 10x not 1x:**
Removes friction. One tap instead of copy-paste. Amplifies Task 1 (public URL) and Task 2 (PDF) by making sharing intentional and obvious.

**Karpathy check:**
Reuse demo page header. `navigator.clipboard.writeText(window.location.href)`. Add a simple toast (or inline "Copied!" text) for feedback. Optional mailto: `mailto:?subject=WarpSense+demo&body=[URL]`. No third-party lib needed. Follow existing UI patterns in AppNav or demo header.

**Acceptance criteria:**
- [ ] "Share with partner" button visible on /demo header
- [ ] Click copies current page URL to clipboard; user sees "Link copied" feedback
- [ ] (Optional) "Email" link opens mailto with pre-filled subject and demo URL in body

**Command:**
```bash
./agent "Add a 'Share with partner' button to my-app/src/app/demo/page.tsx header (next to 'See Team Management'). On click: navigator.clipboard.writeText(window.location.href), then show 'Link copied' toast or inline message for 2 seconds. Optionally add an 'Email' button that opens mailto:?subject=WarpSense+demo&body= with the current demo URL. Use existing Tailwind/design patterns. Add a test that the share button exists and copies the URL on click."
```

---

════════════════════════════════════════════════════════════════
🗑️ EXPLICITLY CUT (and why)
════════════════════════════════════════════════════════════════

- **Refactor session comparison component** — cut at Filter 1: no specific investor sees it; internal improvement
- **Update CONTEXT.md or learnings.md** — cut at Filter 4: 1x work; Principle 1 says external before internal
- **Backend pagination for sessions >10k** — cut at Filter 2: cannot demo in 48hrs; investor does not browse sessions
- **Add Sentry/LogRocket for production** — cut at Filter 1: investors do not see observability; defer until after pilot
- **Polish landing page copy** — cut at Filter 4: landing already exists and works; PDF and public URL are higher leverage

════════════════════════════════════════════════════════════════
📝 LEARNING UPDATE
════════════════════════════════════════════════════════════════

- [2026-02-18] general: When blocker is "good plan," prioritize deploy-to-URL + forwardable artifact (PDF/share) over internal work. Dual-audience tasks (investor forwards + operator use) align with seed-raise goal.
════════════════════════════════════════════════════════════════
```

---

**Altman ambition check:** The deploy task is intentionally high-impact: if there is no public URL, everything else is moot. Tasks are designed so that by day 3 an investor can open a link, see the demo, download a PDF, and share it—directly addressing "Can they send something to someone else after the meeting?"
