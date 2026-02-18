
Here’s the refined task list:

---

**How the critique failure was handled**

The critique returned `"JSON parse failed"` because the critique model’s output wasn’t valid JSON. The 5.0 scores are fallbacks, not real ratings. The refine pass:

1. Clarifies how tasks are interpreted so a future critique run can evaluate them.
2. Tightens execution details (exact paths, observable outcomes) to improve execution quality scores.
3. Keeps the same 3 tasks (Deploy, PDF, Share) and scope.

---

Refined task list written to `.cursor/taskspace/20260218_093109/tasks_refined.md`. Summary of changes:

| Area | Change |
|------|--------|
| **Critique note** | Short note added about the parse failure so it’s clear tasks weren’t downgraded for content reasons. |
| **Task 1** | Command updated to explicit steps: `cd my-app && vercel deploy --prod` and documenting the URL in DEPLOY.md. |
| **Task 2** | File paths made explicit: `demo-config.ts`, `page.tsx`, `export.ts`; acceptance criteria aligned with 94/42. |
| **Task 3** | Same scope and format as before; no structural changes. |
| **Cut list** | Shortened to be more direct while still citing the filters. |

The strategic rationale (specific human, obstacle, leverage, pre-mortem) is unchanged. No new scope was introduced; the three tasks still pass Real Human, 48hr Demo, Reversible, and 10x, and stay in the same priority order.
s localhost, (b) nothing is forwardable (PDF or share), (c) tasks are internal. These tasks directly address (a) and (b).
════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════
🧠 CTO TASK PRIORITIZATION — TOP 3
════════════════════════════════════════════════════════════════
Primary Goal: Raise a seed round from investors
Time Constraint: 5 days until next hard deadline
Specific Human: Seed investors
Context Type: general
Average Priority: 9.0/10

**Note on critique:** The prior critique returned "JSON parse failed" (pipeline failure). Tasks below are tightened for execution clarity and strategic alignment so a re-run can evaluate correctly.

---

## 🔥 Task 1 — Deploy Demo + Landing to Public URL

**Priority:** 9.5/10 | **Effort:** 2–4hrs | **Risk:** Low

**Passes filters:** Real Human ✅ | 48hr Demo ✅ | Reversible ✅ | 10x ✅

**Demo line:**
> Investor opens https://[your-app].vercel.app/demo on their phone. Sees expert vs novice replay, scores (94/42), guided tour. No backend, no setup. Shareable link works.

**Why this is 10x not 1x:**
Without a live URL, everything else is internal. The vision says "one URL to 100 prospects." Localhost demos do not close the investor conversation. A public URL is the prerequisite for any forwardability.

**Karpathy check:**
Demo and landing are 100% client-side (my-app/src/lib/demo-data.ts, no fetchSession). Next.js can deploy to Vercel with `vercel --prod` or GitHub → Vercel. Reuse existing my-app/ build; no schema changes. DEPLOY.md covers Docker; add frontend-only path for investor demos.

**Acceptance criteria:**
- [ ] Investor can open https://[domain]/demo on any device without running Docker or backend
- [ ] Landing at / and demo at /demo render correctly; guided tour appears
- [ ] URL is stable and shareable (e.g. Vercel preview or production)

**Command:**
./agent "Deploy the Next.js frontend (my-app) to a public URL so /demo and / work without backend. Use Vercel: cd my-app && vercel deploy --prod. Ensure NEXT_PUBLIC_API_URL is not required for /demo (browser-only, demo-data.ts). Add a section 'Investor Demo URL' to DEPLOY.md with the resulting URL. Verify: open /demo on mobile or laptop, confirm expert vs novice replay loads and DemoTour shows."

---

## 🔥 Task 2 — Demo Page: Print/Save-as-PDF Report

**Priority:** 9.0/10 | **Effort:** 4–6hrs | **Risk:** Low

**Passes filters:** Real Human ✅ | 48hr Demo ✅ | Reversible ✅ | 10x ✅

**Demo line:**
> Investor clicks 'Download report' on /demo. Print dialog opens with a clean layout (scores 94/42, expert vs novice summary, 1–2 sentence value prop). They choose 'Save as PDF' and email it to their partner.

**Why this is 10x not 1x:**
The vision: "Can they send something to someone else after the meeting?" A PDF is forwardable. Dual-audience: investors share with partners; operators/managers get factual reports.

**Karpathy check:**
Reuse my-app/src/lib/demo-config.ts (MOCK_EXPERT_SCORE_VALUE, MOCK_NOVICE_SCORE_VALUE), layout from my-app/src/app/demo/page.tsx. Add a "Download report" button in the header div (near "See Team Management") that triggers window.print(). Add @media print CSS that hides nav, 3D canvas, controls; shows scores, labels, value prop. No new deps. Follow my-app/src/lib/export.ts pattern.

**Acceptance criteria:**
- [ ] Button "Download report" visible on /demo header
- [ ] Click opens print dialog; preview shows expert 94, novice 42, labels, value-prop text
- [ ] User can "Save as PDF" from browser; resulting PDF is readable and shareable

**Command:**
./agent "Add a 'Download report' button to my-app/src/app/demo/page.tsx in the header (next to 'See Team Management'). On click call window.print(). Add @media print styles that: hide nav, playback controls, 3D canvases; show expert score 94 and novice score 42, labels 'Expert Welder' and 'Novice Welder', and a 2-sentence value prop ('WarpSense compares expert vs novice welding technique in real time. Scores come from 5 quality rules.'). Ensure print layout is readable when saved as PDF. Add a test in my-app/src/app/demo that the button exists and is clickable."

---

## ⚡ Task 3 — Demo Share Button (Copy Link + Email)

**Priority:** 8.5/10 | **Effort:** 1–2hrs | **Risk:** Low

**Passes filters:** Real Human ✅ | 48hr Demo ✅ | Reversible ✅ | 10x ✅

**Demo line:**
> Investor clicks "Share with partner." URL copies to clipboard. Toast or inline message: "Link copied." Optional: "Email" opens mailto with subject and demo URL in body.

**Why this is 10x not 1x:**
Removes friction. One tap instead of copy-paste. Amplifies Task 1 (public URL) and Task 2 (PDF) by making sharing intentional and obvious.

**Karpathy check:**
Reuse demo page header in my-app/src/app/demo/page.tsx. Use navigator.clipboard.writeText(window.location.href). Add simple "Copied!" feedback for 2 seconds. Optional mailto: mailto:?subject=WarpSense+demo&body=[URL]. No third-party lib. Follow existing Tailwind patterns in AppNav or demo header.

**Acceptance criteria:**
- [ ] "Share with partner" button visible on /demo header
- [ ] Click copies current page URL to clipboard; user sees "Link copied" feedback
- [ ] (Optional) "Email" link opens mailto with pre-filled subject and demo URL in body

**Command:**
./agent "Add a 'Share with partner' button to my-app/src/app/demo/page.tsx header (next to 'See Team Management'). On click: navigator.clipboard.writeText(window.location.href), then show 'Link copied' for 2 seconds. Optionally add 'Email' button that opens mailto:?subject=WarpSense+demo&body= with current demo URL. Use existing Tailwind patterns. Add a test that the share button exists and copies the URL on click."

---

════════════════════════════════════════════════════════════════
🗑️ EXPLICITLY CUT (and why)
════════════════════════════════════════════════════════════════

- Refactor session comparison component — cut at Filter 1: no specific investor sees it
- Update CONTEXT.md or learnings.md — cut at Filter 4: 1x work; external before internal
- Backend pagination for sessions — cut at Filter 2: cannot demo in 48hrs; investor does not browse sessions
- Add Sentry/LogRocket — cut at Filter 1: investors do not see observability; defer until after pilot
- Polish landing page copy — cut at Filter 4: landing exists; PDF and public URL are higher leverage

════════════════════════════════════════════════════════════════
📝 LEARNING UPDATE
════════════════════════════════════════════════════════════════

- [2026-02-18] general: When blocker is "good plan," prioritize deploy-to-URL plus forwardable artifact (PDF/share) over internal work. Deploy unlocks share; both require public URL.
════════════════════════════════════════════════════════════════
