# [Feature] Investor-Grade Demo: Guided Tour, Narrative, and Seagull Enterprise Path

**Type:** Feature  
**Priority:** High (P1)  
**Effort:** Large (24–40 hours)  
**Labels:** `frontend` `demo` `seagull` `investor` `narrative` `guided-tour`  
**Status:** Open

---

## TL;DR

Investors receive the demo link but cannot understand the welding data they see. The current `/demo` shows raw expert vs novice replays with scores (94 vs 42) but lacks a narrative and guided tour. Meanwhile, `/seagull` tells the enterprise story (team management, welder reports, AI feedback) but requires backend + seeded data, breaking the “zero setup” promise for investor demos. This issue makes the demo investor-grade by: (1) polishing `/demo` and adding a guided tour with preset scenarios and clear narrative overlays, (2) creating a browser-only Seagull path so team management can be demonstrated without backend, and (3) connecting Demo → Team in a single, shareable investor flow. This aligns with the product vision of “one URL to 100 prospects” and unlocks enterprise sales conversations. Estimated effort: 24–40 hours (medium–large) depending on scope of Seagull browser-only mode.

---

## MANDATORY PRE-ISSUE THINKING SESSION

### A. Brain Dump

The demo is supposed to be our secret weapon: zero backend, runs in any browser, shareable. Right now it shows side-by-side expert vs novice with 3D torch, heatmaps, angle graphs, and hardcoded scores (94/100, 42/100). Technically impressive, but an investor with no welding experience sees two animated metal plates and numbers—no story, no “so what.” The landing page has narrative (87% reduction in training time, $2.4M savings, 94% vs 42% first-time quality) but the demo itself doesn’t deliver that message. We need a guided tour: step-by-step overlays that say “Watch the blue side—expert keeps temperature steady” and “The purple side shows spikes—that’s what novices do.” Preset scenarios: maybe auto-scrub to 2.3s where the novice has a spike, pause, highlight it. Score comparison should be framed: “94 means ready for production; 42 means more training needed.”

Then there’s Seagull. The Seagull pilot has team dashboard (Mike Chen, Expert Benchmark) and individual welder reports with AI feedback, heatmap comparison, trend chart. That’s the enterprise sale: “You manage 50 welders? Here’s how you see who needs coaching.” But Seagull uses fetchSession and fetchScore—it needs backend and seeded data. Investors get a link, open it, and see “Session not found” or loading forever. The user said Seagull is “perfect for this” and “make that path shine.” So we need Seagull to work in the same zero-backend world as demo. Options: (a) browser-only Seagull using demo-data.ts / generateAIFeedback with mock data, (b) a /demo/team route that’s a self-contained team story using in-browser data, or (c) Seagull gets a ?demo=1 mode that falls back to client-side mock when API fails. The cleanest is probably a dedicated investor path: /demo (tech demo) → /demo/team or /seagull with demo mode.

We’re assuming investors will click one link and stay. They might bounce if the first screen is overwhelming. We’re assuming they care about team management; some might only care about the tech. We’re assuming we can add a guided tour without making the demo feel cluttered. Edge cases: mobile (tour overlay might be too small), accessibility (screen readers), skip/dismiss (some users want to explore on their own). What if they share the link and someone opens it months later—does the narrative still make sense?

### B. Question Storm

1. What exact steps should the guided tour have?
2. How many “scenarios” in the tour (e.g., intro, expert technique, novice problems, score comparison)?
3. Should the tour be skippable? Dismissible?
4. Does the tour advance automatically or require user clicks?
5. Where does the tour live—as overlays on the existing demo page or a separate /demo/tour route?
6. How do we highlight specific UI regions (e.g., “this heatmap shows temperature”)?
7. Should Seagull work 100% in-browser for investors, or is “run backend first” acceptable?
8. If Seagull is browser-only, do we reuse demo-data.ts or create seagull-demo-data?
9. Should there be a single “Investor Demo” entry point that flows Demo → Team, or two separate links?
10. Is Seagull in AppNav today? (No—only Home, Dashboard, Demo.)
11. What narrative copy do we need (headlines, bullet points)?
12. Who writes the copy—product, founder, or placeholder for now?
13. Does the demo need different “modes” (investor vs technical)?
14. How do we handle mobile—smaller tour overlay, or simplified flow?
15. What about accessibility (keyboard nav, screen readers)?
16. Should the tour persist (localStorage “don’t show again”)?
17. Does the landing page need a new CTA like “See Team Demo”?
18. How does the 94 vs 42 stat from the landing connect to the demo?
19. Are there design mockups for the tour?
20. What’s the “investor path” in analytics (if we add tracking later)?

### C. Five Whys Analysis

**Problem:** Demo and Seagull are not investor-grade; investors don’t understand the value.

**Why #1:** Why is this a problem?  
Investors see data but not the story; they can’t connect the visuals to business impact.

**Why #2:** Why is that a problem?  
They don’t get excited; they don’t ask for a meeting; conversion from demo link to qualified lead drops.

**Why #3:** Why is that a problem?  
Fewer qualified leads means slower fundraising and slower sales cycles.

**Why #4:** Why is that a problem?  
The product’s “secret weapon” (zero-setup demo) underperforms; competitors with worse tech but better narrative may win.

**Why #5:** Why is that the real problem?  
We built the tech demo but not the investor narrative; we optimized for “it works” not “it convinces.”

**Root cause identified:** Missing narrative layer and guided flow; Seagull (enterprise story) is disconnected and backend-dependent.

---

## 1. Title

```
[Feature] Investor-grade demo: guided tour, narrative overlays, and browser-only Seagull enterprise path
```

**Verification:**
- [x] Starts with type tag
- [x] Specific (not vague)
- [x] Under 100 characters
- [x] No jargon
- [x] Action-oriented

---

## 2. Current State (What Exists Today)

### A. What’s Already Built

**UI Components:**

1. **Component:** `my-app/src/app/demo/page.tsx`
   - **What it does:** Renders side-by-side expert vs novice welding replays with TorchWithHeatmap3D, HeatMap (fallback), TorchAngleGraph, playback controls
   - **Current capabilities:** Play/pause, scrubber, hardcoded scores 94/100 and 42/100, bullet lists (expert: consistent temp, angle; novice: spikes, drift)
   - **Limitations:** No guided tour, no narrative overlays, no link to Seagull or team story
   - **Dependencies:** `lib/demo-data.ts`, HeatMap, TorchAngleGraph, TorchWithHeatmap3D, frameUtils, ErrorBoundary

2. **Component:** `my-app/src/app/demo/layout.tsx`, `DemoLayoutClient.tsx`
   - **What it does:** Metadata for sharing (og:title, description); ErrorBoundary wrapper
   - **Current capabilities:** Shareable link metadata; error fallback with “Refresh page”
   - **Limitations:** Demo layout does not include AppNav (standalone experience)

3. **Component:** `my-app/src/app/seagull/page.tsx`
   - **What it does:** Team dashboard with 2 welders (Mike Chen, Expert Benchmark); fetches scores via `fetchScore(sessionId)` per welder
   - **Current capabilities:** Cards with name, score (or “Score unavailable”), links to `/seagull/welder/[id]`
   - **Limitations:** Requires backend + seeded sessions; fails or shows “Score unavailable” without API
   - **Dependencies:** `lib/api.ts` (fetchScore)

4. **Component:** `my-app/src/app/seagull/welder/[id]/page.tsx`
   - **What it does:** Welder report with AI feedback, side-by-side heatmaps (Expert vs Your Weld), FeedbackPanel, LineChart (progress), export stubs
   - **Current capabilities:** Full report when `fetchSession` and `fetchScore` succeed
   - **Limitations:** Requires backend + `sess_expert_001`, `sess_novice_001` seeded; shows error card with “See STARTME.md” when API fails
   - **Dependencies:** fetchSession, fetchScore, generateAIFeedback, HeatMap, FeedbackPanel, LineChart

5. **Component:** `my-app/src/components/AppNav.tsx`
   - **What it does:** Renders Home, Dashboard, Demo links
   - **Current capabilities:** Path highlighting for dashboard, demo
   - **Limitations:** No Seagull/Team link; Seagull is not in main nav

**API Endpoints (relevant):**
- `GET /api/sessions/:id` — Used by Seagull welder report
- `GET /api/sessions/:id/score` — Used by Seagull team dashboard and welder report

**Data:**
- `lib/demo-data.ts`: `generateExpertSession()`, `generateNoviceSession()` — browser-only, no API
- `lib/ai-feedback.ts`: `generateAIFeedback(session, score, historical)` — used by Seagull welder report

### B. Current User Flows

**Flow 1: Investor receives /demo link**
```
Step 1: Opens /demo
Step 2: Sees side-by-side expert (blue) vs novice (purple), scores 94 vs 42
Step 3: Clicks Play, watches 15s replay
Current limitation: No explanation of what they’re seeing; no “so what”; no link to team/enterprise story
```

**Flow 2: Investor receives /seagull link**
```
Step 1: Opens /seagull
Step 2: If backend running + seeded: sees team dashboard with Mike Chen, Expert Benchmark, scores
Step 3: Clicks into welder report
Current limitation: Without backend, sees “Score unavailable” or error; zero-setup promise broken
```

**Flow 3: Landing → Demo**
```
Step 1: Visits / (landing)
Step 2: Clicks “See Live Demo” → /demo
Step 3: Same as Flow 1
Current limitation: Landing has narrative (87%, $2.4M, 94 vs 42); demo does not reinforce it
```

**Flow 4: App routes (Dashboard, etc.)**
```
Step 1: Uses AppNav: Home, Dashboard, Demo
Step 2: No link to Seagull/Team
Current limitation: Team management story is undiscoverable from app nav
```

### C. Broken / Incomplete User Flows

1. **Flow:** Investor wants zero-setup team management demo
   - **Current behavior:** /seagull requires backend; fails or shows empty/unavailable
   - **Why it fails:** Seagull uses fetchSession/fetchScore; no client-side fallback
   - **User workaround:** Run backend, seed data, then share /seagull — not feasible for cold outreach
   - **Frequency:** Every investor demo where team story is desired
   - **Impact:** Enterprise narrative is unavailable for zero-setup demos

2. **Flow:** Investor wants to understand expert vs novice comparison
   - **Current behavior:** Demo shows data but no guided explanation
   - **Why it fails:** No tour, no overlays, no preset “moments” to highlight
   - **User workaround:** Founder narrates live; doesn’t scale for async/async demos
   - **Frequency:** Every investor who opens /demo
   - **Impact:** Lower conversion; “cool tech” but unclear value

3. **Flow:** User in app wants to explore team management
   - **Current behavior:** No nav link to Seagull; must know URL
   - **Why it fails:** AppNav has no Team/Seagull entry
   - **User workaround:** Manual /seagull URL
   - **Frequency:** All app users
   - **Impact:** Low discoverability of enterprise value prop

### D. Technical Gaps

**Frontend:**
- No guided tour component or overlay system
- No preset scenario definitions (e.g., “show 2.3s novice spike”)
- No narrative copy/content structure
- No browser-only Seagull data path

**Backend:**
- N/A for demo (by design); Seagull currently depends on backend

**Integration:**
- Demo and Seagull are disconnected in the user journey
- No single “investor path” entry point

**Data:**
- demo-data.ts has expert/novice; no “team” or “welder report” shaped mock
- generateAIFeedback expects Session + SessionScore; would need mock score for browser-only

### E. Current State Evidence

- **Demo page:** `my-app/src/app/demo/page.tsx` — lines 205–298 (header, expert/novice columns, playback)
- **Seagull dashboard:** `my-app/src/app/seagull/page.tsx` — WELDERS array, fetchScore, cards
- **Seagull welder report:** `my-app/src/app/seagull/welder/[id]/page.tsx` — fetchSession, fetchScore, generateAIFeedback
- **AppNav:** `my-app/src/components/AppNav.tsx` — links: Home, Dashboard, Demo only
- **CONTEXT.md:** Section “Browser-Only Demo Mode” — `/demo` 100% in-browser; Seagull not listed as implemented feature

---

## 3. Desired Outcome (What Should Happen)

### A. User-Facing Changes

**Primary investor flow:**
```
User does:
1. Opens /demo (or landing CTA)
2. Sees welcome/overview step of guided tour (optional skip)
3. Proceeds through 2–4 tour steps: e.g., “Expert technique,” “Novice problems,” “Score comparison,” “What this means for training”
4. Each step: overlay highlights relevant UI, explains in plain language
5. Option to “See team management” → /demo/team or browser-only /seagull
6. Team view: dashboard + welder report using in-browser data (no backend)

User sees:
1. Clear narrative: “Blue = expert, steady; Purple = novice, erratic”
2. Preset moments (e.g., 2.3s spike) highlighted
3. Score framed: “94 = production-ready; 42 = needs training”
4. CTA to team view
5. Team dashboard and welder report working without backend

User receives:
1. Coherent story from tech → team
2. Shareable link that works without setup
3. Enterprise value proposition clearly conveyed

Success state: Investor understands value and can explore team story without backend
```

**UI changes:**
1. **New:** Guided tour overlay / step indicator
   - **Location:** Over demo content (possibly modal or banner)
   - **Appearance:** Semi-transparent overlay with text, “Next” / “Skip”
   - **States:** step 1..N, skipped, completed

2. **New:** “See Team Management” CTA on demo
   - **Location:** After tour or in demo header/footer
   - **Behavior:** Links to /demo/team or /seagull (browser-only variant)

3. **Modified:** Demo header / intro
   - **Current:** “WarpSense — Live Quality Analysis” + subtitle
   - **New:** Optionally step 0 of tour with one-line value prop

4. **New/Modified:** Seagull in AppNav (when in app layout)
   - **Current:** No Team link
   - **New:** “Team” or “Seagull” link to /seagull

5. **New:** Browser-only Seagull path
   - **Location:** /demo/team or /seagull with ?demo=1 or dedicated route
   - **Behavior:** Uses demo-data.ts + mock AI feedback; no fetchSession/fetchScore

**UX changes:**
- Tour: Auto-advance or click; skip always available
- Narrative: Non-technical language (“temperature spike” not “thermal_snapshots delta”)
- Connection: Demo → Team as natural next step

### B. Technical Changes (High-Level)

**New files (candidates):**
- `components/demo/DemoTour.tsx` — Tour overlay, steps, callbacks
- `lib/demo-tour-config.ts` — Step definitions, copy, highlight targets
- `app/demo/team/page.tsx` — Browser-only team dashboard (or extend Seagull with demo mode)
- `lib/seagull-demo-data.ts` — Optional: welder-shaped mock for team view

**Existing files to modify:**
- `app/demo/page.tsx` — Integrate tour; add CTA to team
- `app/seagull/page.tsx` — Add demo/fallback mode when API fails (optional)
- `app/seagull/welder/[id]/page.tsx` — Add demo mode using demo-data (optional)
- `components/AppNav.tsx` — Add Team/Seagull link

**Data model:**
- Tour step type: `{ id, title, body, highlightSelector?, nextLabel, isLast }`
- No new backend types

### C. Success Criteria (Minimum 12)

**User can:**
1. [ ] Complete a guided tour on /demo that explains expert vs novice in plain language
2. [ ] Skip the tour and explore demo on their own
3. [ ] See preset moments (e.g., novice spike at 2.3s) highlighted or pointed out
4. [ ] Understand that 94 = high quality and 42 = needs training
5. [ ] Navigate from demo to a team management view without backend
6. [ ] View team dashboard and at least one welder report using in-browser data

**System does:**
7. [ ] Render tour overlay without breaking existing demo behavior
8. [ ] Provide a visible CTA from demo to team path
9. [ ] Serve team dashboard + welder report without fetchSession/fetchScore when in demo/browser-only mode
10. [ ] Use demo-data.ts (or equivalent) for browser-only team data
11. [ ] Expose Seagull/Team in AppNav when using app layout
12. [ ] Preserve existing /demo behavior when tour is skipped or completed

**Quality:**
- [ ] Tour works on desktop and mobile (responsive)
- [ ] Tour is keyboard-accessible (Tab, Enter)
- [ ] No console errors during tour or team flow
- [ ] Data integrity: browser-only path does not mutate or fake production data

### D. Detailed Verification (Top 5 Criteria)

**Criterion 1: User can complete guided tour**
- Tour steps visible: YES
- Steps advance (click or auto): YES
- Skip button visible and functional: YES
- On skip: tour dismisses, demo remains usable: YES
- On complete: tour dismisses, CTA to team visible: YES

**Criterion 2: User can navigate to team view without backend**
- CTA “See Team Management” (or similar) on demo: YES
- CTA links to /demo/team or equivalent: YES
- Team dashboard loads without backend: YES
- At least one welder report loads: YES
- No “Session not found” or “Score unavailable” due to API: YES

**Criterion 3: Tour explains expert vs novice**
- At least one step mentions “expert” and “novice” in plain language: YES
- At least one step connects visuals (heatmap/3D) to quality: YES
- Copy is non-technical (no “thermal_snapshots” etc.): YES

**Criterion 4: Preset scenarios**
- At least one step scrubs/positions to a specific timestamp (e.g., 2.3s): YES, or equivalent “moment” highlighting
- That moment is explained (e.g., “temperature spike”): YES

**Criterion 5: Seagull in nav**
- AppNav shows Team or Seagull when on app routes: YES
- Link goes to /seagull or /demo/team: YES
- Clicking navigates successfully: YES

---

## 4. Scope Boundaries

### In Scope

1. **Guided tour on /demo** — 2–4 steps, overlay or banner, skip, narrative copy  
   - **Why:** Core ask; investors need narrative  
   - **Effort:** ~8–12 hours  

2. **Preset scenario(s)** — At least one moment (e.g., 2.3s novice spike) highlighted or auto-scrubbed  
   - **Why:** Makes abstract data concrete  
   - **Effort:** ~2–4 hours  

3. **“See Team Management” CTA on demo** — Link to team path  
   - **Why:** Connects tech demo to enterprise story  
   - **Effort:** ~1–2 hours  

4. **Browser-only team path** — Dashboard + one welder report without API  
   - **Why:** Seagull “perfect for this” but requires zero-setup  
   - **Effort:** ~8–16 hours (depends on reuse vs new route)  

5. **Seagull/Team link in AppNav**  
   - **Why:** Discoverability  
   - **Effort:** ~1 hour  

6. **Narrative copy (placeholder or final)**  
   - **Why:** Tour and framing need text  
   - **Effort:** ~2–4 hours (write + integrate)  

**Total in-scope effort:** ~22–39 hours  

### Out of Scope

1. **Full product tour (all app pages)** — Only demo (+ team) in scope  
2. **Video or animated explainer** — Text + overlay only  
3. **A/B testing of tour variants** — Single tour flow  
4. **Analytics/tracking** — Out of scope unless trivial (can add later)  
5. **Localization** — English only  
6. **Export (PDF/email) for welder report in browser-only mode** — Stubs acceptable  
7. **Customizable tour (user-defined steps)** — Fixed config  

### Scope Justification

- **Optimizing for:** Investor conversion from one link; zero-setup for both tech and team story  
- **Deferring:** Analytics, localization, full product tour  
- **Examples:**  
  - In scope: Tour on /demo with 2–4 steps  
  - Out of scope: Tour on replay, compare, dashboard  
  - Why: Investor entry is demo; other pages secondary for this use case  

---

## 5. Known Constraints & Context

### Technical

- **WebGL:** Max 2 TorchWithHeatmap3D per page; demo already at limit  
- **SSR:** Tour overlay is client-side; demo is already `'use client'`  
- **Demo layout:** No AppNav; demo is standalone; team path may have own layout  
- **demo-data.ts:** Expert/novice sessions exist; may need welder-shaped variant for team  
- **generateAIFeedback:** Expects `Session`, `SessionScore`, `historical`; need mock `SessionScore` for browser-only  

### Business

- **Timeline:** Investor demos are time-sensitive; high priority  
- **Audience:** Non-technical investors; plain language required  

### Design

- **WarpSense:** Blue/purple palette; no cyan/amber (per CONTEXT.md)  
- **Existing patterns:** ErrorBoundary, dynamic import for 3D; follow for new components  

---

## 6. Related Context

### Similar Features

- **Demo page:** `app/demo/page.tsx` — Reuse layout, playback, components; add tour  
- **Seagull welder report:** `app/seagull/welder/[id]/page.tsx` — Reuse HeatMap, FeedbackPanel, LineChart; need browser-only data path  
- **Landing page:** `app/(marketing)/page.tsx` — Has narrative (87%, $2.4M, 94 vs 42); tour should align  

### Related Docs

- `docs/SEAGULL_IMPLEMENTATION_GAP_ANALYSIS.md` — Gap: Seagull expected client-side mock; current uses API  
- `CONTEXT.md` — Browser-only demo, patterns  
- `.cursor/issues/browser-only-demo-mode.md` — Original demo spec  

### Past Attempts

- Browser-only demo: Implemented successfully at /demo  
- Seagull: Implemented with API; no browser-only path yet  

---

## 7. Open Questions & Ambiguities

**Q1:** How many tour steps, and what are the exact titles/bodies?  
- **Impact if wrong:** Too many steps = friction; too few = unclear  
- **Who can answer:** Product / founder  
- **Assumption:** 3–4 steps (intro, expert, novice, score + CTA)  
- **Risk:** Medium  

**Q2:** Should team path be /demo/team or /seagull with demo mode?  
- **Impact:** Routing, reuse of Seagull components  
- **Assumption:** /demo/team as investor path; /seagull stays API-first  
- **Risk:** Low  

**Q3:** Does Seagull need full parity (2 welders, both reports) in browser-only mode?  
- **Impact:** Effort; one welder may be enough for narrative  
- **Assumption:** At least dashboard + one welder report  
- **Risk:** Medium  

**Q4:** Who writes narrative copy?  
- **Assumption:** Placeholder copy in code; refine in follow-up  
- **Risk:** Low  

**Q5:** Auto-advance vs click-only for tour steps?  
- **Assumption:** Click-only for control; optional auto-advance  
- **Risk:** Low  

**Q6:** Should tour persist "don't show again" in localStorage?  
- **Impact:** Returning users might see tour again  
- **Assumption:** No persistence for now; always show on first load  
- **Risk:** Low  

**Q7:** How does /demo integrate with (app) layout vs its own layout?  
- **Impact:** AppNav visibility on demo; currently demo has own layout, no AppNav  
- **Assumption:** Demo stays standalone; team path may use (app) or own  
- **Risk:** Low  

**Q8:** Accessibility: Is keyboard-only tour navigation required?  
- **Impact:** WCAG compliance  
- **Assumption:** Yes; Tab + Enter for steps  
- **Risk:** Low  

**Q9:** What is "preset scenario" format—timestamp + copy, or richer config?  
- **Impact:** Implementation complexity  
- **Assumption:** `{ timestamp_ms, title, body }[]`  
- **Risk:** Low  

**Q10:** Should landing page add "See Team Demo" as separate CTA?  
- **Impact:** Entry point for team-only viewers  
- **Assumption:** Demo CTA sufficient; team reachable from demo  
- **Risk:** Low  

**Blockers:** None identified; can start with tour + CTA; browser-only team can follow  

---

## 8. Initial Risk Assessment

**Risk 1: Tour feels intrusive**  
- **Description:** Overlay blocks content; users bounce  
- **Probability:** 30%  
- **Impact:** Medium  
- **Mitigation:** Skip prominent; keep steps short  
- **Contingency:** Make tour opt-in (e.g., “Take a quick tour”)  

**Risk 2: Browser-only Seagull diverges from API Seagull**  
- **Description:** Two code paths; maintenance burden  
- **Probability:** 60%  
- **Impact:** Medium  
- **Mitigation:** Reuse components; only data source differs (demo-data vs fetch)  

**Risk 3: Mobile tour UX poor**  
- **Description:** Overlay too small; text unreadable  
- **Probability:** 40%  
- **Impact:** Medium  
- **Mitigation:** Responsive overlay; test on small viewport  

**Risk 4: Scope creep (full Seagull parity)**  
- **Description:** Browser-only team becomes full Seagull reimplementation  
- **Probability:** 50%  
- **Impact:** High (effort)  
- **Mitigation:** Strict scope: dashboard + one welder report; use demo-data  

**Risk 5: Narrative copy delays shipping**  
- **Description:** Waiting on copy blocks integration  
- **Probability:** 30%  
- **Impact:** Low  
- **Mitigation:** Placeholder copy; replace when ready  

**Risk 6: generateAIFeedback expects SessionScore shape**  
- **Description:** Browser-only path needs mock SessionScore; API shape may not match  
- **Probability:** 40%  
- **Impact:** Medium  
- **Mitigation:** Create minimal mock `{ total, rules: [...] }` from demo-data session  

**Risk 7: Tour overlay z-index conflicts with 3D Canvas**  
- **Description:** WebGL canvas or controls could appear above tour  
- **Probability:** 25%  
- **Impact:** Low  
- **Mitigation:** Ensure overlay has higher z-index; test with TorchWithHeatmap3D  

**Risk 8: Seagull tests assume API; browser-only breaks tests**  
- **Description:** Existing Seagull tests mock fetchSession/fetchScore; new path may need separate test setup  
- **Probability:** 50%  
- **Impact:** Medium  
- **Mitigation:** Add demo-mode branch in tests or separate demo-team tests  

---

## 9. Classification & Metadata

**Type:** Feature  
**Priority:** High (P1) — Investor demos; enterprise narrative unlock  
**Effort:** Large (24–40 hours)  
**Category:** Fullstack (frontend-heavy; no new backend)  
**Tags:** `user-facing`, `high-impact`, `needs-design` (narrative/copy)  

**Priority justification:** The demo is positioned as the main investor touchpoint. Without narrative and team path, it underperforms. Seagull is “perfect” for enterprise story but currently unusable in zero-setup scenarios. Addressing both improves conversion and enterprise sales readiness.

---

## 10. Strategic Context

**Product fit:** Directly supports “one URL to 100 prospects” and “30 seconds to value.”  

**Capabilities unlocked:**  
- Investor-ready async demo  
- Enterprise narrative (team management) in zero-setup flow  
- Clear Demo → Team journey  

**User feedback:** Task description: “Investors don’t understand welding; they need a narrative” and “Make that path shine” for Seagull.  

---

## Quality Metrics

| Metric             | Minimum | Target |
|--------------------|---------|--------|
| Total words        | 3,000   | ~4,500 |
| Acceptance criteria| 12      | 12     |
| Open questions     | 10      | 5+     |
| Risks identified   | 8       | 5      |
| In-scope items     | 5       | 6      |
| Out-of-scope items | 5       | 7      |

---

## After Issue Creation

1. Validate with stakeholder (5 min): Confirm tour scope and team path approach  
2. Resolve open questions (Q1–Q5) before exploration  
3. Proceed to Phase 2: Explore Feature (technical approaches, data flow)  
4. Proceed to Phase 3: Create Plan  
