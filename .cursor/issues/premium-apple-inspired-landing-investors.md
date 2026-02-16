# [Feature] Premium Apple-Inspired Landing Page for Investor Presentations

## TL;DR

The Shipyard Welding platform lacks a dedicated marketing/investor-facing landing page. The current homepage (`/`) shows a dashboard that requires backend data and is not suitable for investor demos or prospect outreach. The demo page (`/demo`) is technical (expert vs novice comparison) and not investor-focused. We need a premium, Apple-inspired landing page with clean aesthetics, smooth scroll animations, investor-oriented messaging (ROI stats, technology highlights, social proof), and clear CTAs. This enables pitch decks, investor meetings, and prospect sharing via a single polished URL. The core problem is the absence of a first-impression page that communicates value to non-technical stakeholders. The desired outcome is a standalone marketing page at a dedicated route that showcases the product vision without requiring login or backend.

---

## Current State (What Exists Today)

### What's in place

- **Home page:** `my-app/src/app/page.tsx`
  - Dashboard-focused; requires `fetchDashboardData()` from backend
  - Loading/error states when backend unavailable
  - CTA to `/demo` as fallback
  - Shows welding sessions list (sess_expert_001, sess_novice_001)
  - Not investor-friendly; assumes technical audience

- **Demo page:** `my-app/src/app/demo/page.tsx`
  - Browser-only, zero backend; uses `lib/demo-data.ts` for synthesized sessions
  - Side-by-side expert vs novice replay with TorchViz3D, HeatMap, TorchAngleGraph
  - Technical, training-focused; removed from investor landing per task description
  - Good for product demo but not as first touch for investors

- **AppNav:** `my-app/src/components/AppNav.tsx`
  - Minimal nav: Home, Demo links
  - Uses zinc/cyan theme; fixed in layout, shown on all pages
  - Styling: `border-zinc-200 dark:border-zinc-800`

- **Layout:** `my-app/src/app/layout.tsx`
  - Renders `AppNav` + children for all routes
  - Geist + Geist Mono fonts
  - Metadata: "Dashboard" / "Data visualization dashboard"

- **3D components:** `TorchViz3D`, `HeatMap`, `TorchAngleGraph`
  - TorchViz3D uses WebGL (one context per instance)
  - Per `constants/webgl.ts` and `documentation/WEBGL_CONTEXT_LOSS.md`: max 2 TorchViz3D per page

- **Dependencies:** `package.json`
  - Next.js 16, React 19, Tailwind 4, recharts, three.js, @react-three/fiber/drei
  - **framer-motion not installed** — required for landing page animations

### What's missing

- No dedicated landing/marketing route
- No investor-focused messaging or stats (87% training reduction, $2.4M savings, 94% quality)
- No premium design system (glass morphism, gradient text, parallax)
- No scroll-based animations (hero parallax, staggered fade-in)
- No social proof section (industry leaders)
- No CTA section (Schedule Demo, Download Deck)
- framer-motion not in dependencies

### Broken / incomplete user flows

1. Investor opens link → Lands on dashboard → Sees loading/error or raw data → **Poor first impression**
2. Prospect shared a link → Expects polished marketing page → Gets technical demo → **Mismatch**
3. Pitch deck references "see it live" → No dedicated investor URL → **Unprofessional**

### Technical gaps

- No framer-motion dependency
- No landing-specific layout (AppNav may clash with landing's fixed nav)
- No integration of TorchViz3D in landing demo section (placeholder only in provided design)
- Typography/color system differs from existing pages (black + blue/purple gradients vs zinc/cyan)

---

## Desired Outcome (What Should Happen)

### User-facing changes

- User visits `/landing` (or configured route) and sees a full-screen, premium landing page
- Fixed nav: WeldVision branding, Technology / Analytics / Impact anchors, "Request Demo" CTA
- Hero: "The Future of Industrial Training" with gradient text, parallax fade on scroll, animated scroll indicator
- Stats section: 87% training reduction, $2.4M savings, 94% first-time quality — staggered fade-in
- Technology: 4 feature cards (Real-time, AI, Security, Hardware) with glass morphism
- Interactive Demo: Section with either placeholder or embedded TorchViz3D; metrics strip (300°C, 45°, 30°C/s)
- Social Proof: Newport News, BAE Systems, Huntington Ingalls, General Dynamics
- CTA: "Ready to transform your training?" with Schedule Demo + Download Deck
- Footer: Copyright, Privacy, Terms, Contact
- Smooth scroll, generous spacing (py-32), max-width 7xl
- Animations: subtle, professional (0.8s duration)

### Technical changes

- New: `my-app/src/app/landing/page.tsx` (or route TBD) — client component with Framer Motion
- New: `npm install framer-motion` — add to package.json
- Possibly: Landing-specific layout or conditional AppNav hide (see Open Questions)
- Possibly: Integrate TorchViz3D in demo section (dynamic import, ssr: false) — 1 instance within WebGL limits
- Fix typos in reference code: `durati` → `duration`, `nt-bold` → `font-bold`

### Success criteria (minimum 8 acceptance criteria)

1. **[ ]** Landing page loads at designated route (e.g. `/landing`) without backend
2. **[ ]** Hero section displays "The Future of Industrial Training" with gradient text
3. **[ ]** Stats section shows 87%, $2.4M, 94% with staggered fade-in on scroll
4. **[ ]** Technology section has 4 feature cards (Real-time, AI, Security, Hardware) with glass morphism
5. **[ ]** Interactive Demo section visible; either placeholder or working TorchViz3D
6. **[ ]** Social Proof section shows 4 industry leader names
7. **[ ]** CTA section has "Schedule a Demo" and "Download Deck" buttons
8. **[ ]** Hero parallax (content fades as user scrolls) and scroll indicator animate correctly
9. **[ ]** Navigation anchors (#technology, #analytics, #impact) scroll to correct sections
10. **[ ]** Works in Chrome, Firefox, Safari; no console errors
11. **[ ]** framer-motion animations run smoothly (no jank); page is responsive (mobile breakpoints)
12. **[ ]** "See Live Demo" and "Request Demo" link to `/demo` or configured demo URL

### Quality requirements

- Works in Chrome, Firefox, Safari (modern versions)
- Mobile responsive: nav collapses or adapts, sections stack
- Accessible: keyboard navigation, sufficient contrast, semantic HTML
- No console errors or warnings
- Performance: LCP < 2.5s on typical connection; animations < 0.8s
- WebGL: If TorchViz3D embedded, max 1 instance on landing (per WEBGL_CONTEXT_LOSS.md)

---

## Scope Boundaries (What's In/Out)

### In scope

- New landing page route (e.g. `/landing`)
- Premium Apple-inspired design: black bg, blue/purple/cyan gradients, glass morphism
- Framer Motion: parallax, staggered fade-in, scroll indicator
- Investor-focused sections: Hero, Stats, Technology, Demo, Social Proof, CTA, Footer
- Responsive layout (max-w-7xl, py-32, mobile breakpoints)
- framer-motion dependency
- Fix typos in reference implementation (durati, nt-bold)
- Navigation to demo: "See Live Demo" → `/demo` (or similar)

### Out of scope

- Replacing home (`/`) with landing (separate decision; could be env-based)
- Backend API for "Schedule Demo" / "Download Deck" (buttons can be mailto or placeholder)
- Video modal for "Watch Video" (placeholder or external link)
- Custom font beyond Geist (unless specified)
- A/B testing or analytics integration (future)
- Localization (English only)
- Expert vs novice comparison (explicitly removed as not investor-relevant)

---

## Known Constraints & Context

### Technical constraints

- Must use Next.js 16 App Router; page must be client component (`'use client'`) for Framer Motion
- TorchViz3D: dynamic import with `ssr: false`; max 2 per page (landing would use 0 or 1)
- Per `LEARNING_LOG.md` and `documentation/WEBGL_CONTEXT_LOSS.md`: avoid multiple WebGL contexts
- Tailwind 4 in use; design uses standard Tailwind classes

### Business constraints

- Purpose: investor presentations, prospect sharing, pitch support
- Timeline: not specified; assume standard sprint
- Product name in design: "WeldVision" (user-provided); project is "Shipyard Welding" — align with stakeholder preference

### Design constraints

- Apple-inspired: clean, minimalist, generous white space
- Color palette: black background, blue/purple/cyan gradients
- Typography: large bold headings (7xl–8xl), gray-400 for body
- Animations: subtle, 0.8s duration
- Layout: centered, max-width 7xl, py-32 sections

---

## Related Context (Prior Art & Dependencies)

### Similar features in codebase

- **Demo page** `my-app/src/app/demo/page.tsx` — Uses dynamic TorchViz3D, HeatMap, TorchAngleGraph; good pattern for client-only 3D
- **Dashboard** `my-app/src/app/page.tsx` — Uses ErrorBoundary, loading states; different audience
- **AppNav** `my-app/src/components/AppNav.tsx` — Nav pattern; landing has its own fixed nav

### Reference implementation

- User-provided full landing page code in `.cursor/agents/task_1771211295_premium_Apple-inspired_landing/task.txt`
- Contains: Hero, Stats, Technology (4 cards), Demo placeholder, Social Proof, CTA, Footer
- Typo: `transition={{ durati: 0.8 }}` → `duration`; `nt-bold` → `font-bold`

### Dependencies

- **Blocked by:** None
- **Blocks:** None
- **Related:** Demo page (`/demo`) — "See Live Demo" should link here

---

## Open Questions & Ambiguities

1. **Route: `/landing` vs `/` vs `/investors`?**
   - Why unclear: User did not specify
   - Impact: Affects AppNav links, redirects, SEO
   - Current assumption: Use `/landing`; can make `/` redirect in investor-facing deployments

2. **Show or hide AppNav on landing?**
   - Why unclear: Landing has its own fixed nav; AppNav may duplicate or clash
   - Impact: Layout, visual consistency
   - Current assumption: Hide AppNav on landing route (layout-level conditional) OR style AppNav to match landing

3. **Interactive Demo: placeholder vs TorchViz3D?**
   - Why unclear: Reference has placeholder; integrating real 3D adds impact
   - Impact: Bundle size, WebGL context (1 instance is safe)
   - Current assumption: Start with placeholder; add TorchViz3D if time permits and it enhances demo

4. **Product name: WeldVision vs Shipyard Welding?**
   - Why unclear: Design uses WeldVision; project/docs use Shipyard Welding
   - Impact: Branding consistency
   - Current assumption: Use WeldVision for landing (per user design); confirm with stakeholder

5. **CTA behavior: mailto, external form, placeholder?**
   - Why unclear: No backend/form specified
   - Impact: Implementation scope
   - Current assumption: "Schedule a Demo" → mailto or `/demo`; "Download Deck" → placeholder or external PDF link

---

## Initial Risk Assessment (High-Level)

1. **Bundle size — framer-motion**
   - Why risky: Adds ~30–50KB gzipped
   - Impact: Slightly slower initial load for landing
   - Likelihood: Low (acceptable for marketing page)

2. **AppNav duplication/clash**
   - Why risky: Landing has fixed nav; AppNav may show below or conflict
   - Impact: Redundant nav, poor UX
   - Likelihood: Medium — requires layout or route-group handling

3. **Animation performance on low-end devices**
   - Why risky: Multiple `useInView` + `useTransform` + parallax
   - Impact: Jank, dropped frames
   - Likelihood: Low (Framer Motion is generally performant; test on modest devices)

4. **WebGL context if TorchViz3D added**
   - Why risky: Adds 1 context; user may have other tabs with R3F
   - Impact: Context limit exceeded in edge cases
   - Likelihood: Low (1 instance is well within limit)

5. **Mobile nav**
   - Why risky: Reference uses `hidden md:flex`; no mobile menu
   - Impact: Nav links inaccessible on small screens
   - Likelihood: Medium — should add hamburger or simplified mobile nav

---

## Classification & Metadata

**Type:** feature  
**Priority:** normal  
**Effort:** medium (8–16 hours)  
**Category:** frontend

---

## Strategic Context (Product Vision Alignment)

**Product roadmap alignment:**
- Supports investor relations and fundraising readiness
- Enables prospect sharing with a single polished URL
- Differentiates from "dashboard-first" technical tools

**User impact:**
- Frequency: Used for pitch meetings, investor emails, prospect links
- User segment: Founders, sales, biz-dev
- Satisfaction impact: Professional first impression; reduces "what does this do?" friction

**Technical impact:**
- Code health: Adds new route; minimal impact on existing code
- Team velocity: Establishes marketing page pattern for future pages
- Tech debt: Low (isolated page); framer-motion is well-maintained
