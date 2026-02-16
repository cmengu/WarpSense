# [Improvement] WarpSense Rebrand — Name Change and Blue/Purple-Only Dark Color Palette

## Phase 0: Understand the Workflow Position

**This is Step 1 of 3:**
1. **Create Issue** ← This document (capture the WHAT and WHY)
2. **Explore Feature** (deep dive into HOW)
3. **Create Plan** (step-by-step implementation)

---

## MANDATORY PRE-ISSUE THINKING SESSION

### A. Brain Dump (5 minutes minimum)

The product is mid-development with a mix of branding: the monorepo and CONTEXT.md already reference "WarpSense," but user-facing pages (demo, layouts, deploy scripts) still say "Shipyard Welding." The user wants a clean, consistent rebrand to WarpSense. Additionally, the color scheme is currently rainbow-like—blue, cyan, green, yellow, orange, red, purple, pink, amber, emerald appear across landing, demo, 3D components, charts, and thermal visualizations. The user explicitly wants only blue and purple shades, and specifically dark shades. No rainbow colors.

What exactly needs to change:
- Every occurrence of "Shipyard Welding" must become "WarpSense" in titles, headings, metadata, and docs.
- All non-blue, non-purple colors must be removed or replaced. This includes cyan (which is blue-green—arguably borderline), green, yellow, amber, orange, red, pink, emerald, teal, lime. The thermal heatmap is a special case: industry convention uses blue (cold) → red (hot). Replacing that with a blue→purple gradient would preserve the cold→hot semantics while staying within the palette.

Who is affected: All users viewing the app—investors on landing, prospects on demo, operators on dashboard/replay/compare. Internal developers see the name in docs, scripts, docker.

Why this matters: Brand consistency and visual identity. A professional product should have a coherent look. Rainbow colors can feel unprofessional or toy-like for enterprise/industrial software. Blue and purple evoke technology, precision, and premium feel.

What prompted this: User request during development—likely brand decision or investor/design preference.

Assumptions we might be wrong about:
1. "Cyan" might be acceptable (it's blue-adjacent). User said "blue and purple only"—strict interpretation excludes cyan.
2. Error states (red) might need to stay for universal "danger" semantics. User said "no rainbow" so we assume red→purple/violet for errors.
3. Expert vs Novice (currently green/red) needs a new semantic: perhaps blue vs purple, or two shades of blue.
4. Thermal visualization: changing blue→red to blue→purple changes industry convention; we assume user wants it changed but will document as open question.

What could go wrong:
- Changing thermal gradient might confuse users used to blue=cold, red=hot. We'd need clear legend.
- Many tests assert specific hex colors (e.g., heatmapData.test.ts expects #3b82f6, #eab308, #ef4444 at anchors). All must be updated.
- PieChart, BarChart, mockData use multi-color palettes; switching to blue/purple variants only may reduce distinguishability of segments.

What we don't know:
- Exact hex values for the new blue/purple dark palette (design decision).
- Whether "WarpSense" should appear with tagline (e.g., "WarpSense — Welding Analytics") or standalone.
- Whether docker container names (shipyard_postgres, shipyard_backend) should change—they're internal but might matter for consistency.

---

### B. Question Storm (20+)

1. What triggers this rebrand—user request, investor feedback, or design system decision?
2. When should this be complete—any deadline?
3. Who experiences the old branding—all visitors or specific routes?
4. How often do users see "Shipyard Welding" vs "WarpSense" today?
5. What's the impact if we don't fix it—brand confusion, unprofessional appearance?
6. What's the impact if we do—consistent, polished product identity?
7. Are we assuming users prefer blue/purple over rainbow—or is this stakeholder preference?
8. Are we assuming the thermal gradient can change from blue→red to blue→purple?
9. What similar rebrands have we done—none documented.
10. What did we learn from the premium landing work—color usage was blue/purple/cyan originally, but landing added green, orange, pink, etc.
11. Should error/warning states use purple instead of red for semantic "danger"?
12. Should Expert vs Novice use blue vs purple, or two blues?
13. Should cyan be treated as "blue" (acceptable) or "rainbow" (excluded)?
14. Are there design mockups or brand guidelines to follow?
15. Should docker-compose service names change from shipyard_* to warpsense_*?
16. Should my-app package.json "name" stay "my-app" or become "warpsense-frontend"?
17. What about CONTEXT.md—it already says "WarpSense (Shipyard Welding MVP)"; do we drop "Shipyard Welding" entirely?
18. Should the compare page delta heatmap (red=A hotter, blue=B hotter) stay or change to purple vs blue?
19. Are there external links (README, DEPLOY.md) that reference "shipyard-welding" repo names?
20. How do we handle charts (PieChart, BarChart) that need multiple distinct colors for data series—use only blue/purple shades with varying lightness?
21. What about the HeatMap active-column outline (currently green)—acceptable or change to blue?
22. Should the landing page "Request Demo" white button stay or become dark blue/purple?

---

### C. Five Whys Analysis

**Problem:** App shows inconsistent branding (Shipyard Welding) and rainbow color scheme instead of WarpSense with blue/purple-only dark palette.

**Why #1:** Why is inconsistent branding a problem?
- Answer: Users and investors see mixed names; looks unprofessional and confuses product identity.

**Why #2:** Why is that a problem?
- Answer: Reduces trust and clarity; prospects may not know what product they're evaluating.

**Why #3:** Why is that a problem?
- Answer: Conversion and adoption suffer; enterprise buyers expect coherent branding.

**Why #4:** Why is that a problem?
- Answer: Business goals (demos, pitches, adoption) depend on clear, professional presentation.

**Why #5:** Why is that the real problem?
- Answer: We lack a single, consistent product identity that supports sales and credibility. The root cause is historical naming (Shipyard Welding) and design choices (rainbow palette) that no longer align with the desired brand (WarpSense, blue/purple).

**Root cause identified:** Product evolved with legacy naming and a varied color palette; stakeholder now wants unified WarpSense branding and a constrained blue/purple dark palette for a cohesive, professional identity.

---

## Required Information Gathering

### 1. Understand the Request — Documented Conversation

**User's initial request:**
> Change the name to WarpSense, make sure the entire color scheme is blue and purple shades only those dark shades no rainbow colors

**Clarifications obtained:**
- Name: "WarpSense" everywhere user-facing (no "Shipyard Welding").
- Colors: Blue and purple shades only, dark shades, no rainbow (no red, orange, yellow, green, cyan, pink, amber, emerald, teal, lime).
- Scope: "Entire" color scheme—implies all pages, components, charts, thermal viz.

**Remaining ambiguities:**
- Exact hex values for the new palette (to be defined in exploration).
- Whether semantic colors (error/danger, success) should use purple variants or be exempt.
- Whether thermal heatmap gradient (cold→hot) should be blue→purple or stay blue→red for industry convention.

---

### 2. Search for Context — Documented Findings

#### Codebase Search Results

**Branding / Name:**
- `my-app/src/app/demo/page.tsx` (line 209): "Shipyard Welding — Live Quality Analysis"
- `my-app/src/app/demo/layout.tsx` (lines 17, 21): `title: 'Live Demo — Shipyard Welding'`
- `.env.example`: "Shipyard Welding — Environment variables"
- `deploy.sh`: "Shipyard Welding Platform - Deploy Script"
- `docker-compose.yml`: container names `shipyard_postgres`, `shipyard_backend`, `shipyard_frontend`, `shipyard_network`
- `my-app/Dockerfile`, `backend/Dockerfile`: "Shipyard Welding Frontend/Backend"
- `DEPLOY.md`: "Shipyard Welding — One-Click Docker Deploy", clone path `shipyard-welding`
- `my-app/src/__tests__/app/demo/page.test.tsx`: expects "Shipyard Welding"
- `CONTEXT.md`: "WarpSense (Shipyard Welding MVP)" — partial rebrand
- Root `package.json`: "warpsense-monorepo", "WarpSense welding MVP monorepo" — already WarpSense

**Rainbow / Non-Blue-Purple Colors:**
- `my-app/src/app/(marketing)/page.tsx`: blue, cyan, purple, pink, green, emerald, orange, red gradients
- `my-app/src/app/demo/page.tsx`: cyan accents, green (expert), red (novice), red error states
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx`: cyan-400, green-500 (status), amber (warning), blue→cyan→amber gradient on scale
- `my-app/src/components/welding/TorchViz3D.tsx`: cyan theme
- `my-app/src/components/welding/HeatmapPlate3D.tsx`: cyan, amber
- `my-app/src/utils/heatmapData.ts`: TEMP_COLOR_ANCHORS blue→sky→cyan→teal→green→lime→yellow→amber→orange→red
- `my-app/src/utils/heatmapShaderUtils.ts`: dark blue→cyan→teal→green→lime→orange→red
- `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts`: same rainbow gradient
- `my-app/src/components/charts/PieChart.tsx`: DEFAULT_COLORS includes green, amber, red, pink
- `my-app/src/components/charts/BarChart.tsx`: default green (#10b981)
- `my-app/src/data/mockData.ts`: blue, green, purple, amber
- `my-app/src/components/welding/TorchAngleGraph.tsx`: green target line, blue stroke
- `my-app/src/components/welding/HeatMap.tsx`: active column outline rgb(34 197 94) — green
- Error states: red (demo, replay, compare, dashboard, DemoLayoutClient)

**Similar existing patterns:**
1. Landing page design doc (`.cursor/issues/premium-apple-inspired-landing-investors.md`) — specifies "black bg, blue/purple/cyan gradients"; current landing diverged with rainbow.
2. `globals.css` — uses neutral background/foreground; no rainbow in base theme.
3. `constants/thermal.ts` — thermal constants; color logic lives in heatmapData and shaders.

---

### 3. Web Research (if applicable)

**Re: Thermal color palettes**
- Industry standard: blue (cold) → red (hot) is ubiquitous (thermal cameras, heatmaps). Changing to blue→purple keeps both in palette; semantics (cold=blue, hot=purple) remain interpretable with clear legend.
- Dark blue/purple palettes: Tailwind blue-900/950, indigo-900, violet-900, purple-900 provide dark shades. For gradients, from-blue-900 via-purple-900 to-indigo-950 works.

**Re: Accessibility**
- Blue/purple only: Ensure sufficient contrast (WCAG 2.1). Dark blue (#1e3a5f) on dark bg may fail; use lighter blue/purple for text on dark, or ensure 4.5:1 contrast.

---

## THINKING CHECKPOINT #1

### 1. Assumptions That Might Be Wrong

1. **Assumption:** User wants cyan excluded (strict "blue and purple only").
   - **If wrong:** We remove cyan and app feels less vibrant; user may have meant "blues and purples" including cyan.
   - **How to verify:** Confirm with stakeholder; default to strict (no cyan).
   - **Likelihood:** Medium | **Impact if wrong:** Low (can add cyan back)

2. **Assumption:** Error states should change from red to purple/violet.
   - **If wrong:** Purple "danger" is less universally recognized; some users expect red for errors.
   - **How to verify:** UX research; default to purple/violet-600 for danger to stay in palette.
   - **Likelihood:** Medium | **Impact if wrong:** Medium (accessibility/recognition)

3. **Assumption:** Thermal gradient blue→red should become blue→purple.
   - **If wrong:** Users trained on thermal viz expect red=hot; purple may confuse.
   - **How to verify:** User confirmation; provide legend. If user objects, document as exception.
   - **Likelihood:** Low | **Impact if wrong:** Medium

4. **Assumption:** Docker container names (shipyard_*) should change to warpsense_*.
   - **If wrong:** Breaks existing deploy scripts, docs, and any external references to container names.
   - **How to verify:** Check deploy.sh, DEPLOY.md, docker-compose for references; migration path if changed.
   - **Likelihood:** High that we'd change | **Impact if wrong:** High (breaking change)

5. **Assumption:** "Shipyard Welding" in CONTEXT.md should be removed entirely; product is "WarpSense" only.
   - **If wrong:** Some internal docs may need "(formerly Shipyard Welding)" for context.
   - **How to verify:** Update CONTEXT to "WarpSense" and drop Shipyard; add one-line history if needed.
   - **Likelihood:** Low | **Impact if wrong:** Low

### 2. Questions a Skeptical Engineer Would Ask

1. **Q:** Do we have a design spec with exact hex values? **A:** No; exploration phase will define palette.
2. **Q:** Will this break existing Docker deployments? **A:** If we rename containers, yes; we'll document migration.
3. **Q:** Are there screenshots or assets with old branding? **A:** Not documented; assume code-only.
4. **Q:** Do tests need wholesale rewrite for color assertions? **A:** Yes; heatmapData, HeatMap, heatmapShaderUtils tests assert specific colors.
5. **Q:** What about third-party Recharts default colors? **A:** We override via props; BarChart, LineChart, PieChart use our palette.
6. **Q:** Is there a design system or Figma? **A:** Not referenced; we derive from Tailwind blue/purple dark shades.
7. **Q:** Will the compare page delta (red/blue for A hotter / B hotter) work with blue/purple only? **A:** Yes; use blue for "B hotter" and purple for "A hotter" or similar.
8. **Q:** What about the landing page "Major US Shipyards" — is that branding or industry term? **A:** Industry term; no change.
9. **Q:** Should we add a `constants/theme.ts` for centralized palette? **A:** Good idea; exploration can propose.
10. **Q:** How do we handle multiple chart series (PieChart) with only blue/purple? **A:** Use varying shades (blue-400, blue-600, purple-400, purple-600, indigo-500, etc.).

### 3. Edge Cases / Failure Modes / Dependencies

**Edge cases:**  
- User has custom CSS overrides.  
- `prefers-color-scheme: light` — ensure light mode also uses blue/purple, not rainbow.  
- External links to "shipyard-welding" repo.  
- Cached assets with old branding.  

**Failure modes:**  
- Color contrast fails a11y.  
- Thermal viz becomes harder to read.  
- Chart segments indistinguishable.  

**Dependencies:**  
- Tailwind blue/purple palette.  
- No new npm deps expected.  

### 4. Explain to a Junior Developer

Imagine you're explaining this to someone who just joined the team:

We're rebranding the product from "Shipyard Welding" to "WarpSense." Right now, the app uses "Shipyard Welding" in the demo page title, layout metadata, deploy scripts, Docker, and some docs. We need to replace all of that with "WarpSense."

At the same time, we're changing the entire color scheme. Today, the app uses a rainbow of colors: blue, cyan, green, yellow, orange, red, purple, pink, amber. The stakeholder wants only blue and purple shades, and specifically dark shades. No rainbow colors. So we have to find every place that uses non-blue, non-purple colors and replace them. That includes the landing page (which has green, orange, red gradients), the demo page (green for "expert" and red for "novice"), the thermal heatmaps (which go from blue to red for cold to hot), chart default colors, 3D component accents, error states, and more. We'll define a dark blue/purple palette and apply it everywhere. Some special cases: thermal viz traditionally uses blue→red; we'll switch to blue→purple. Error states use red; we'll switch to purple. Expert vs novice currently uses green vs red; we'll use two different shades (e.g., blue vs purple). Tests that assert specific hex colors will need updates. The goal is a cohesive, professional look that matches the WarpSense brand.

### 5. Red Team

**Problem 1:** Thermal gradient change may reduce readability for domain experts.
- **Impact:** Medium.  
- **Mitigation:** Use high-contrast blue→purple steps; add/improve legend.

**Problem 2:** Blue/purple-only charts may have low distinguishability.
- **Impact:** Low–medium.  
- **Mitigation:** Use enough shade variation; consider patterns for critical segments.

**Problem 3:** Purple for "danger" may be less intuitive.
- **Impact:** Low.  
- **Mitigation:** Use violet/purple-600 with clear iconography and text.

**Problem 4:** Scope creep — "entire" could include favicon, PWA manifest, etc.
- **Impact:** Low.  
- **Mitigation:** Explicitly list in-scope items; defer favicon if not specified.

**Problem 5:** Docker renames break existing deployments.
- **Impact:** High.  
- **Mitigation:** Document migration; consider keeping container names for backward compat or versioning.

---

## Issue Structure

### 1. Title

```
[Improvement] WarpSense Rebrand — Name Change and Blue/Purple-Only Dark Color Palette
```

- [x] Starts with type tag
- [x] Specific
- [x] Under 100 characters
- [x] Action-oriented

---

### 2. TL;DR

The product uses mixed branding ("Shipyard Welding" in many user-facing places) and a rainbow color scheme (blue, cyan, green, yellow, orange, red, purple, pink) across landing, demo, 3D components, charts, and thermal visualizations. Stakeholders want a unified "WarpSense" identity and a constrained palette: blue and purple shades only, in dark tones, with no rainbow colors. The core problem is inconsistent branding and a color scheme that does not match the desired professional, technology-focused aesthetic. Currently, the monorepo root and CONTEXT.md partially use "WarpSense," but demo titles, layout metadata, deploy scripts, Docker, and tests still reference "Shipyard Welding." Color usage is scattered and includes red (errors, novice, thermal hot), green (expert, success, active states), amber (warnings), cyan (accents), and rainbow gradients on the landing page. The desired outcome is: (1) all user-facing text and metadata say "WarpSense"; (2) a single dark blue/purple palette applied everywhere (replacing red, green, yellow, orange, cyan, pink, amber); and (3) thermal visualizations using a blue→purple gradient instead of blue→red. This aligns with a professional, cohesive product identity for investor demos and enterprise adoption. Effort is medium (estimated 12–20 hours) spanning ~25+ files.

---

### 3. Current State (What Exists Today)

#### A. What's Already Built

**UI Components with Branding/Color:**
1. `my-app/src/app/demo/page.tsx` — "Shipyard Welding — Live Quality Analysis" (line 209); cyan accents; green (expert) / red (novice); red error UI
2. `my-app/src/app/(marketing)/page.tsx` — Landing; gradients blue→cyan, purple→pink, green→emerald, orange→red; cards with green, orange, purple, blue, pink
3. `my-app/src/app/demo/layout.tsx` — metadata `title: 'Live Demo — Shipyard Welding'`
4. `my-app/src/components/AppNav.tsx` — cyan for Demo link; zinc elsewhere
5. `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — cyan-400 borders, green-500 status, amber warning, blue→cyan→amber scale gradient
6. `my-app/src/components/welding/TorchViz3D.tsx` — cyan theme
7. `my-app/src/components/welding/HeatmapPlate3D.tsx` — cyan, amber
8. `my-app/src/components/welding/HeatMap.tsx` — active column outline `rgb(34 197 94)` (green)
9. `my-app/src/components/welding/TorchAngleGraph.tsx` — green target line (#22c55e), blue stroke (#3b82f6)
10. `my-app/src/components/charts/PieChart.tsx` — DEFAULT_COLORS `['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899']`
11. `my-app/src/components/charts/BarChart.tsx` — default `#10b981` (green)
12. `my-app/src/components/charts/LineChart.tsx` — default `#3b82f6` (blue)

**Data/Utilities:**
- `my-app/src/utils/heatmapData.ts` — TEMP_COLOR_ANCHORS blue→sky→cyan→teal→green→lime→yellow→amber→orange→red (13 steps)
- `my-app/src/utils/heatmapShaderUtils.ts` — ANCHOR_COLORS same rainbow
- `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts` — GLSL anchors match
- `my-app/src/lib/demo-data.ts` — N/A for colors (mock data)
- `my-app/src/data/mockData.ts` — chart colors blue, green, purple, amber

**Error/Backend-offline UI:**
- `my-app/src/app/demo/DemoLayoutClient.tsx` — red error panel
- `my-app/src/app/replay/[sessionId]/page.tsx` — red error/empty states
- `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` — red error, amber warning
- `my-app/src/app/(app)/dashboard/page.tsx` — red error, cyan CTA

**Infrastructure/Docs:**
- `deploy.sh` — "Shipyard Welding Platform"
- `docker-compose.yml` — shipyard_postgres, shipyard_backend, shipyard_frontend, shipyard_network
- `my-app/Dockerfile`, `backend/Dockerfile` — "Shipyard Welding"
- `.env.example` — "Shipyard Welding"
- `DEPLOY.md` — "Shipyard Welding", shipyard-welding clone path
- `CONTEXT.md` — "WarpSense (Shipyard Welding MVP)"
- `README.md` — "WarpSense - Welding MVP"

**Tests:**
- `my-app/src/__tests__/app/demo/page.test.tsx` — expects "Shipyard Welding"
- `my-app/src/__tests__/utils/heatmapData.test.ts` — asserts #3b82f6, #eab308, #ef4444, etc.
- `my-app/src/__tests__/components/welding/HeatMap.test.tsx` — asserts #3b82f6, #eab308, #ef4444

#### B. Current User Flows

**Flow 1: Investor visits landing**
- User opens `/` → sees "The Future of Industrial Training" with rainbow stats (87% blue-cyan, $2.4M purple-pink, 94% green-emerald), feature cards (blue, purple, green, orange) → **Current limitation:** Rainbow palette.

**Flow 2: Prospect visits demo**
- User opens `/demo` → sees "Shipyard Welding — Live Quality Analysis", expert (green) vs novice (red), cyan accents → **Current limitation:** Wrong name; green/red outside palette.

**Flow 3: Operator views replay**
- User opens `/replay/[id]` → 3D torch (cyan), heatmap (blue→red gradient) → **Current limitation:** Cyan and red outside palette.

#### C. Broken/Incomplete Flows

1. **Flow:** User expects consistent "WarpSense" branding everywhere.
   - **Current:** Demo says "Shipyard Welding"; deploy says "Shipyard Welding Platform."
   - **Why it fails:** Mixed naming.

2. **Flow:** User expects blue/purple-only color scheme.
   - **Current:** Rainbow colors throughout.
   - **Why it fails:** Design not aligned with requirement.

3. **Flow:** Thermal heatmap follows user-requested palette.
   - **Current:** Blue→red gradient.
   - **Why it fails:** Red outside palette.

#### D. Technical Gaps

- No centralized theme/palette constants for blue/purple dark shades.
- No single source of truth for WarpSense branding strings.
- Thermal shader, heatmapData, and heatmapShaderUtils duplicate color logic—all must stay in sync.

#### E. Evidence

- `heatmapData.ts` TEMP_COLOR_ANCHORS (lines 59–71): explicit rainbow RGB values.
- `(marketing)/page.tsx` lines 358, 372, 386: `from-blue-400 to-cyan-400`, `from-purple-400 to-pink-400`, `from-green-400 to-emerald-400`.
- `demo/page.tsx` line 209: `Shipyard Welding — Live Quality Analysis`.

---

### 4. Desired Outcome (What Should Happen)

#### A. User-Facing Changes

**Primary:**
1. All titles, headings, metadata: "WarpSense" (no "Shipyard Welding").
2. Color palette: dark blue and purple shades only (e.g., blue-800/900/950, indigo-800/900, violet-800/900, purple-800/900/950).
3. Landing: stats, cards, gradients—blue/purple only.
4. Demo: Expert vs novice distinguished by two blue/purple shades (e.g., blue vs purple); accents blue/purple.
5. Thermal viz: Cold→hot = blue→purple (dark blue → lighter blue → purple).
6. Error/danger: Purple/violet instead of red.
7. Charts: Blue/purple palette for series.
8. 3D components: Blue/purple accents; no cyan, green, amber.

**UI Changes:**
- Demo header: "WarpSense — Live Quality Analysis"
- Layout metadata: "Live Demo — WarpSense"
- Landing gradients: `from-blue-900 to-purple-900`, `from-indigo-900 to-violet-900`, etc.
- Expert/Novice: e.g., `text-blue-400` vs `text-purple-400`
- Error panels: `border-purple-800`, `text-purple-400`

#### B. Technical Changes

**Files to modify:**
- `my-app/src/app/demo/page.tsx` — branding + colors
- `my-app/src/app/demo/layout.tsx` — metadata
- `my-app/src/app/(marketing)/page.tsx` — all gradients, cards, stats
- `my-app/src/app/demo/DemoLayoutClient.tsx` — error colors
- `my-app/src/app/replay/[sessionId]/page.tsx` — error/empty colors
- `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` — error, warning, delta colors
- `my-app/src/app/(app)/dashboard/page.tsx` — error, CTA colors
- `my-app/src/components/AppNav.tsx` — Demo link color (cyan→blue/purple)
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — accents, scale, thermal colors
- `my-app/src/components/welding/TorchViz3D.tsx` — theme
- `my-app/src/components/welding/HeatmapPlate3D.tsx` — accents
- `my-app/src/components/welding/HeatMap.tsx` — active outline
- `my-app/src/components/welding/TorchAngleGraph.tsx` — target/stroke colors
- `my-app/src/components/charts/PieChart.tsx` — DEFAULT_COLORS
- `my-app/src/components/charts/BarChart.tsx` — default color
- `my-app/src/utils/heatmapData.ts` — TEMP_COLOR_ANCHORS
- `my-app/src/utils/heatmapShaderUtils.ts` — ANCHOR_COLORS
- `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts` — anchor colors
- `my-app/src/data/mockData.ts` — chart colors
- `my-app/src/app/globals.css` — if accent vars used
- `deploy.sh` — "WarpSense Platform" (or similar)
- `docker-compose.yml` — optionally warpsense_* (see scope)
- `my-app/Dockerfile`, `backend/Dockerfile` — "WarpSense"
- `.env.example` — "WarpSense"
- `DEPLOY.md` — WarpSense, warpsense-* if containers renamed
- `CONTEXT.md` — "WarpSense" (drop Shipyard Welding)
- All relevant tests

**New file (optional):**
- `my-app/src/constants/theme.ts` — palette constants (e.g., ACCENT_BLUE, ACCENT_PURPLE, THERMAL_COLD, THERMAL_HOT)

#### C. Success Criteria (12+)

1. **[ ]** User sees "WarpSense" (not "Shipyard Welding") in demo header.
2. **[ ]** User sees "WarpSense" in demo layout metadata/title.
3. **[ ]** Landing page uses only blue/purple gradients and accents.
4. **[ ]** Demo expert/novice panels use blue/purple shades (no green/red).
5. **[ ]** Thermal heatmap/CSS heatmap uses blue→purple gradient.
6. **[ ]** 3D thermal metal uses blue→purple gradient.
7. **[ ]** Error/danger UI uses purple/violet (no red).
8. **[ ]** PieChart default colors are blue/purple shades only.
9. **[ ]** BarChart/LineChart defaults are blue/purple.
10. **[ ]** HeatMap active column outline is blue or purple (not green).
11. **[ ]** TorchAngleGraph target/stroke use blue/purple.
12. **[ ]** AppNav Demo link uses blue/purple (not cyan).
13. **[ ]** deploy.sh and docs reference WarpSense (not Shipyard Welding).
14. **[ ]** All tests pass with updated color/string assertions.
15. **[ ]** No Tailwind/hex colors outside blue, indigo, violet, purple, slate (for neutrals).

#### D. Detailed Verification (Top 5)

**Criterion 1: Demo header shows "WarpSense"**
- Visible: YES — "WarpSense — Live Quality Analysis" in main heading.
- Location: Same as current Shipyard line.
- Test: `expect(screen.getByText(/WarpSense/)).toBeInTheDocument()`.

**Criterion 2: Landing stats use blue/purple only**
- Stats 87%, $2.4M, 94%: gradients like `from-blue-600 to-blue-400`, `from-purple-600 to-purple-400`, `from-indigo-600 to-violet-400`. No green, orange, pink.
- Verification: Inspect classes; no green-*, orange-*, pink-*, cyan-*.

**Criterion 3: Thermal heatmap blue→purple**
- heatmapData.ts TEMP_COLOR_ANCHORS: low temp = dark blue, high temp = purple/violet. No yellow, orange, red.
- Test: tempToColor(20) returns blue hex; tempToColor(600) returns purple hex.

**Criterion 4: Error state purple**
- DemoLayoutClient, replay, compare, dashboard error panels: border/text use purple/violet. No red-*.
- Verification: grep for `red-` in error components; expect zero.

**Criterion 5: PieChart blue/purple palette**
- DEFAULT_COLORS: only blue, indigo, violet, purple hex values. No green, amber, red, pink.
- Verification: Assert array; run PieChart with multiple series; visually confirm.

---

### 5. Scope Boundaries

#### In Scope

1. **[ ]** Replace "Shipyard Welding" with "WarpSense" in demo page, layouts, tests.
2. **[ ]** Replace "Shipyard Welding" in deploy.sh, .env.example.
3. **[ ]** Update Dockerfile comments to "WarpSense".
4. **[ ]** Update CONTEXT.md, DEPLOY.md to WarpSense.
5. **[ ]** Landing page: convert all gradients and card colors to blue/purple dark shades.
6. **[ ]** Demo page: expert/novice to blue/purple; accents to blue/purple.
7. **[ ]** heatmapData, heatmapShaderUtils, heatmapFragment.glsl: blue→purple thermal gradient.
8. **[ ]** TorchWithHeatmap3D, TorchViz3D, HeatmapPlate3D: blue/purple accents.
9. **[ ]** HeatMap active outline, TorchAngleGraph: blue/purple.
10. **[ ]** PieChart, BarChart, mockData: blue/purple palette.
11. **[ ]** Error/danger UI: purple/violet.
12. **[ ]** AppNav: blue/purple for Demo link.
13. **[ ]** All color-related tests updated.
14. **[ ]** globals.css if needed for theme vars.

**Total effort:** ~12–20 hours.

#### Out of Scope

1. **[ ]** Docker container renames (shipyard_* → warpsense_*) — defer; breaking change.
2. **[ ]** Favicon / PWA manifest branding — unless explicitly requested.
3. **[ ]** GitHub repo rename (WarpSense already) — no change.
4. **[ ]** my-app package.json "name" — keep "my-app" unless requested.
5. **[ ]** "Major US Shipyards" social proof text — industry term, not product name.
6. **[ ]** Backend API response branding — no user-facing strings there.
7. **[ ]** iPad/ESP32 app branding — separate codebase.

#### Scope Justification

- Prioritizing user-facing name and color changes; Docker renames are high-impact and can be Phase 2.
- Optimizing for: brand consistency, visual coherence, stakeholder requirements.
- Deferring: container renames, favicon, non-frontend surfaces.

---

### 6. Known Constraints & Context

**Technical:**
- Tailwind: use blue-*, indigo-*, violet-*, purple-*, slate-* for neutrals.
- Thermal shader: GLSL must match heatmapShaderUtils and heatmapData for consistency.
- Tests: heatmapData, HeatMap, demo page assert specific values—all must update.

**Design:**
- Dark shades: blue-800/900/950, indigo-800/900, violet-800/900, purple-800/900/950.
- No cyan, green, yellow, orange, red, pink, amber, emerald, teal, lime.

**Project:**
- `.cursorrules`: Prefer determinism, explicit naming, no randomness.
- `documentation/WEBGL_CONTEXT_LOSS.md`: Max 2 Canvas per page; unchanged.
- LEARNING_LOG: No new WebGL contexts.

---

### 7. Related Context

**Similar features:**
- Premium landing (`.cursor/issues/premium-apple-inspired-landing-investors.md`) — originally blue/purple/cyan; current landing added rainbow.
- Unified torch heatmap (`.cursor/plans/unified-torch-heatmap-replay-plan.md`) — thermal color logic.

**Related issues:**
- None blocking this.

**Past attempts:**
- Partial WarpSense adoption in package.json, CONTEXT; Shipyard persisted in UI and scripts.

---

### 8. Open Questions & Ambiguities

1. **Exact hex values for dark blue/purple palette?**
   - Impact: Drives all color replacements.
   - Who: Design/stakeholder.
   - Assumption: Tailwind blue-800/900, purple-800/900, indigo-900.

2. **Should Docker containers be renamed?**
   - Impact: Breaking for existing deploys.
   - Assumption: Out of scope for v1.

3. **Cyan acceptable or excluded?**
   - Assumption: Excluded (strict blue+purple).

4. **Thermal blue→purple: which purple shade for "hot"?**
   - Assumption: purple-500 or violet-500.

5. **Expert vs novice: blue vs purple, or two blues?**
   - Assumption: Blue vs purple for clear contrast.

6. **Centralized theme constants file?**
   - Assumption: Yes; exploration can add `constants/theme.ts`.

7. **Delta heatmap (A hotter vs B hotter): blue vs purple mapping?**
   - Assumption: Purple = A hotter, blue = B hotter.

8. **Light mode: same palette or different?**
   - Assumption: Same blue/purple, adjusted for contrast.

9. **Chart segment count > 6: enough blue/purple shades?**
   - Assumption: Use blue-400/600/800, purple-400/600/800.

10. **Deploy script output message: "WarpSense Platform" or "WarpSense Welding Platform"?**
    - Assumption: "WarpSense Platform".

**Blockers:** None.
**Important:** Q1 (palette), Q4 (thermal hot), Q5 (expert/novice).

---

### 9. Initial Risk Assessment

**Risk 1: Thermal gradient readability**
- Probability: 30%. Impact: Medium.
- Mitigation: Clear legend; sufficient contrast in steps.

**Risk 2: Chart segment distinguishability**
- Probability: 40%. Impact: Low.
- Mitigation: Use 6+ blue/purple shades; test with real data.

**Risk 3: Purple danger less recognizable**
- Probability: 25%. Impact: Low.
- Mitigation: Strong violet; clear text and icons.

**Risk 4: Test brittleness**
- Probability: 80%. Impact: Low.
- Mitigation: Update all color assertions in one pass.

**Risk 5: Missed color usage**
- Probability: 50%. Impact: Medium.
- Mitigation: Grep for color keywords; systematic file sweep.

**Risk 6: Contrast / a11y**
- Probability: 20%. Impact: Medium.
- Mitigation: Verify contrast for text and focus states.

**Risk 7: Scope creep**
- Probability: 30%. Impact: Low.
- Mitigation: Strict in/out scope; defer Docker renames.

**Risk 8: Inconsistent palette application**
- Probability: 40%. Impact: Medium.
- Mitigation: Centralized theme constants; single PR.

---

### 10. Classification & Metadata

**Type:** Improvement

**Priority:** P2 (Normal)
- Rebrand and palette are important for polish and stakeholder alignment, but not blocking core welding functionality. No production outage or security impact.

**Effort:** Medium (12–20 hours)
- Frontend: ~8 h (pages, components, charts)
- Utils/shaders: ~3 h (heatmapData, shader, heatmapShaderUtils)
- Docs/scripts: ~2 h
- Tests: ~3 h
- Review: ~2 h

**Confidence:** Medium — palette definition and thermal UX may add time.

**Category:** Frontend (primary), fullstack (docs/scripts)

**Tags:** user-facing, high-impact

---

### 11. Strategic Context

- Aligns with premium, professional product identity for investor demos.
- Enables consistent WarpSense brand across all touchpoints.
- Reduces visual noise; blue/purple conveys technology and trust.
- No direct revenue metric; supports credibility and adoption.

---

## THINKING CHECKPOINT #2 — Self-Critique

**Unclear points:** Palette hex values; Docker rename decision.
**Quantification:** ~25 files, ~12–20 hours, 12+ criteria.
**Evidence:** File paths, line refs, grep results documented.
**Assumptions:** 5 documented with verification.
**Depth:** 3000+ words; checkpoints completed.

---

## Quality Metrics

| Metric                      | Minimum | Status |
|----------------------------|---------|--------|
| Total words                | 3,000   | ✓      |
| Pre-thinking words        | 500     | ✓      |
| Acceptance criteria        | 12      | ✓      |
| Open questions             | 10      | ✓      |
| Risks identified           | 8       | ✓      |
| Similar features           | 3       | ✓      |
| Assumptions documented     | 5       | ✓      |
| Thinking checkpoint words  | 800     | ✓      |

---

## After Issue Creation

1. [ ] Validate scope with stakeholder.
2. [ ] Resolve palette hex values (or confirm Tailwind defaults).
3. [ ] Proceed to Phase 2: Explore Feature (technical deep dive).
4. [ ] Create implementation plan with file-level changes.
