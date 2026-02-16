# Premium Apple-Inspired Landing Page — Implementation Plan (REVISED v2)

**Overall Progress:** 0% (0/20 steps completed)

---

## TLDR

Build a premium, Apple-inspired investor landing page that **replaces the home page at `/`** using Next.js route groups. Marketing layout (`(marketing)`) has no AppNav; app layout (`(app)`) has AppNav for dashboard/demo. Landing: black bg, blue/purple/cyan gradients, glass morphism, Framer Motion (parallax hero, staggered stats, smooth scroll). Sections: Hero, Stats (87%, $2.4M, 94%), Technology (4 cards), Demo (placeholder + "Try Full Demo →" link), Social Proof (generic placeholders until permissions), CTA (Schedule Demo → Calendly/env, Download Deck → PDF/env). AppNav never renders on landing—route groups handle it. yoursite.com/ = pitch; yoursite.com/dashboard = app.

---

## Critical Architectural Decisions

### Decision 1: Route Groups — Landing at `/`, Dashboard at `/dashboard`

**Choice:** Use Next.js route groups. `(marketing)/page.tsx` → `/` (landing). `(app)/dashboard/page.tsx` → `/dashboard`. Remove `/landing` path.

**Rationale:** Sharing yoursite.com/landing looks unprofessional. Investors expect yoursite.com to be the pitch. Two separate entry points (landing vs dashboard) confuse users. Route groups give clean separation: marketing = no AppNav, app = AppNav.

**Trade-offs:** All internal links to `/` (dashboard) must change to `/dashboard`. One-time migration.

**Impact:** AppNav shows "Home" → `/` (landing for visitors), "Dashboard" → `/dashboard`. Root layout has NO AppNav; (app) layout adds AppNav. No pathname checks anywhere.

---

### Decision 2: AppNav Only in (app) Layout — No Conditional Hiding

**Choice:** Root `layout.tsx` renders only `html`, `body`, `{children}`. `(app)/layout.tsx` wraps children with `<AppNav />`. `(marketing)/layout.tsx` wraps with nothing (or metadata only).

**Rationale:** Landing is self-contained. AppNav knowing about landing route creates tight coupling. What if you add `/about`, `/contact`? Route groups scale: marketing routes = no AppNav, app routes = AppNav.

**Trade-offs:** None. Cleaner architecture.

**Impact:** Remove `isLanding` and `if (isLanding) return null` from AppNav. Remove `usePathname` check for landing. AppNav always renders when in (app) tree.

---

### Decision 3: Demo Section — Placeholder + "Try Full Demo →" Button

**Choice:** Demo section shows placeholder (video icon, metrics strip). Primary CTA inside section: "Try Full Demo →" linking to `/demo`. Do NOT wrap entire placeholder as clickable link to /demo (confusing—users expect demo on-page).

**Rationale:** Clicking "Interactive Demo" and being redirected feels broken. Either embed TorchViz3D (1 instance, per WEBGL_CONTEXT_LOSS.md) OR make it clear: "Try Full Demo →" = navigate away. We use the latter to keep landing lightweight.

**Trade-offs:** Less visual impact than embedded 3D. Optional Phase 5: Add 1 TorchViz3D if stakeholder prefers.

**Impact:** Placeholder card is NOT a link. Add explicit "Try Full Demo →" button below it linking to `/demo`.

---

### Decision 4: CTA Buttons — Real Destinations with Safe Env Fallbacks

**Choice:** "Schedule a Demo" → external Calendly/Cal.com URL (env var `NEXT_PUBLIC_DEMO_BOOKING_URL` or fallback `/demo`). "Download Deck" → `/investor-deck.pdf` (static file in `public/`) or env var `NEXT_PUBLIC_INVESTOR_DECK_URL`. Handle empty string env vars: `?.trim() || fallback`.

**Rationale:** `"" || "/demo"` yields `"/demo"`, but `process.env.NEXT_PUBLIC_X` can be `""` when defined but empty. `.trim()` ensures empty/whitespace triggers fallback.

**Impact:** `DEMO_BOOKING_URL = process.env.NEXT_PUBLIC_DEMO_BOOKING_URL?.trim() || '/demo'`.

---

### Decision 5: Social Proof — Generic Placeholders

**Choice:** Replace company names with: "Major US Shipyards", "Defense Contractors", "Fortune 500 Manufacturing", "Heavy Industry Leaders" — until signed agreements for logo/name use.

**Rationale:** Using company names without permission risks legal issues, especially defense contractors.

**Impact:** Update copy and tests to match new placeholders.

---

### Decision 6: Smooth Scroll — Global CSS

**Choice:** Add `html { scroll-behavior: smooth; }` to `globals.css` so anchor links (#technology, #analytics, #impact) scroll smoothly.

**Rationale:** Nav uses anchor links; native smooth scroll improves UX.

**Note:** If you later add programmatic scroll animations with Framer Motion (e.g., scrollTo), native smooth scroll can conflict. Use `scroll-behavior: auto` on those elements or disable programmatic smooth for that interaction.

---

## Dependency Ordering

| Step | Depends On | Blocks | Can Mock? |
|------|-----------|--------|-----------|
| 1.1 Add smooth scroll | Nothing | — | N/A |
| 1.2a Create route group folders + layouts | Nothing | 1.2b, 1.2c, 1.2d | N/A |
| 1.2b Move dashboard to (app)/dashboard | 1.2a | 1.4 | N/A |
| 1.2c Create landing at (marketing)/page | 1.2a | Phase 2 | N/A |
| 1.2d Move remaining routes to (app) | 1.2a | 1.4 | N/A |
| 1.3 Update AppNav | 1.2a | — | N/A |
| 1.4 Update internal links (/ → /dashboard) | 1.2b, 1.2d | — | N/A |
| 2.1 framer-motion | Nothing | 2.2* | N/A |
| 2.2a Landing skeleton + nav + empty sections | 1.2c | 2.2b | Yes |
| 2.2b Hero section with parallax | 2.2a | 2.2c | Yes |
| 2.2c Stats section | 2.2b | 2.2d | Yes |
| 2.2d Technology 4 cards | 2.2c | 2.3 | Yes |
| 2.3 Demo, Social Proof, CTA, Footer | 2.2d | 2.4 | No |
| 2.4 CTA destinations + Demo UX | 2.3 | 2.5 | No |
| 2.5 CTA env vars + empty-string handling | 2.4 | — | No |
| 3.1 Mobile nav (AnimatePresence, click-outside, Escape, stopPropagation) | 2.2a | — | No |
| 4.1 Proxy-based Framer mock (filter style) | Nothing | 4.2 | N/A |
| 4.2 Landing tests | 2.5, 4.1 | — | Yes |
| 4.3 Manual verification | 4.2 | — | No |

**Critical path:** 1.2a → 1.2b/1.2c/1.2d (can run 1.2b, 1.2c, 1.2d in sequence or partly parallel) → 1.4 → Phase 2 content → tests.

---

## Risk Heatmap

| Phase | Step | Risk | Probability | What Could Go Wrong | Early Detection | Mitigation |
|-------|------|------|-------------|---------------------|-----------------|------------|
| 1 | 1.2a | Route group structure wrong | 🟡 40% | 404 on / or /dashboard | Run dev after each step | Follow Next.js route group docs |
| 1 | 1.2d | Import paths break after move | 🟡 50% | Module not found on build | Run `npm run build` after moves | Build catches what dev masks |
| 1 | 1.2d | Move fails (folder missing) | 🟢 20% | "No such file or directory" when moving seagull/dev | Run `ls -d app/{demo,replay,compare,seagull,dev} 2>/dev/null` first | Move only existing folders per subtasks |
| 2 | 2.2b | Parallax/useTransform issues | 🟡 45% | Content doesn't fade on scroll | Scroll hero | Ensure style={{ y, opacity }} on motion.div |
| 2 | 2.2b | Safari grid perspective glitch | 🟡 30% | Grid background renders oddly | Test in Safari | Use `perspective` CSS property, not transform function |
| 3 | 3.1 | Click-outside race (hamburger) | 🟡 40% | Click bubbles, double-toggle | Open/close rapidly | Add e.stopPropagation() on hamburger click |
| 4 | 4.1 | Framer mock passes MotionValue to style | 🔴 70% | React rejects invalid style, tests fail | Run tests | Filter style prop, omit or convert MotionValues |
| 2 | 2.5 | Empty string env var | 🟢 15% | "" doesn't trigger fallback | Set NEXT_PUBLIC_X="" | Use ?.trim() before \|\| |

---

## Implementation Phases

### Phase 1 — Route Architecture (Critical Path)

**Goal:** Landing at `/`, Dashboard at `/dashboard`, AppNav only in app routes. Each move is atomic and testable.

**Why first:** Everything depends on correct route structure.

**Time Estimate:** 3–4 hours (was 2–3; split steps add verification overhead)

**Risk Level:** 🟡 40%

---

#### 🟥 Step 1.1: Add smooth scroll to globals.css

**Subtasks:**
- [ ] 🟥 Add `html { scroll-behavior: smooth; }` to `my-app/src/app/globals.css`

**Files:**
- **Modify:** `my-app/src/app/globals.css`

**✓ Verification Test:**

**Action:**
1. Add the rule to globals.css
2. Run `npm run dev`
3. Navigate to a page with anchor links (future landing at `/` or current `/landing`)
4. Click an anchor link (e.g. `#technology`)

**Expected Result:**
- Page scrolls smoothly to target section (no instant jump)

**How to Observe:**
- **Visual:** Scroll animation visible
- **DevTools:** Computed style on `html` shows `scroll-behavior: smooth`

**Pass Criteria:**
- Smooth scroll works
- No layout shift or errors

**Note:** If you later add programmatic scroll with Framer Motion, use `scroll-behavior: auto` for that element to avoid conflicts.

---

#### 🟥 Step 1.2a: Create route group folders and layouts — *Critical: Route architecture*

**Why this is critical:** Incorrect structure breaks all routes. Affects SEO, navigation, and user flows.

**Subtasks:**
- [ ] 🟥 Create `my-app/src/app/(marketing)/` folder
- [ ] 🟥 Create `my-app/src/app/(app)/` folder
- [ ] 🟥 Create `app/(marketing)/layout.tsx` (metadata only, children pass-through)
- [ ] 🟥 Create `app/(app)/layout.tsx` (with AppNav wrapping children)
- [ ] 🟥 Remove AppNav from root `layout.tsx`

**Files:**
- **Create:** `my-app/src/app/(marketing)/layout.tsx`
- **Create:** `my-app/src/app/(app)/layout.tsx`
- **Modify:** `my-app/src/app/layout.tsx`

**Code Implementation:**

```typescript
// my-app/src/app/layout.tsx — REMOVE AppNav
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

```typescript
// my-app/src/app/(app)/layout.tsx
import { AppNav } from '@/components/AppNav';
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AppNav />
      {children}
    </>
  );
}
```

```typescript
// my-app/src/app/(marketing)/layout.tsx
import type { Metadata } from 'next';
export const metadata: Metadata = {
  title: 'WeldVision — The Future of Industrial Training',
  description: 'Real-time thermal analytics and AI-powered feedback transforming skilled labor training in heavy industry. 87% training reduction, $2.4M savings per facility.',
  openGraph: { title: '...', description: '...', type: 'website' },
};
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```

**✓ Verification Test:**

**Action:**
1. Run `npm run dev`
2. App should build; 404 on `/` and `/dashboard` is OK (no pages there yet)

**Expected Result:**
- No build errors
- Dev server starts
- Root layout no longer renders AppNav

**Pass Criteria:**
- Build succeeds
- No runtime errors on startup

---

#### 🟥 Step 1.2b: Move dashboard to (app)/dashboard

**Subtasks:**
- [ ] 🟥 Create `app/(app)/dashboard/page.tsx`
- [ ] 🟥 Copy content from `app/page.tsx`
- [ ] 🟥 Test `/dashboard` loads
- [ ] 🟥 Delete `app/page.tsx` ONLY after `/dashboard` verified

**Files:**
- **Create:** `my-app/src/app/(app)/dashboard/page.tsx`
- **Delete:** `my-app/src/app/page.tsx` (after verification)

**✓ Verification Test:**

**Action:**
1. Create `(app)/dashboard/page.tsx` with content from `app/page.tsx`
2. Navigate to `http://localhost:3000/dashboard`
3. Verify dashboard renders with AppNav
4. Then delete `app/page.tsx`

**Expected Result:**
- `/dashboard` shows dashboard (sessions list, Demo CTA, etc.)
- AppNav visible above content

**Pass Criteria:**
- Dashboard renders
- AppNav present
- No import errors

---

#### 🟥 Step 1.2c: Create landing at (marketing)/page

**Subtasks:**
- [ ] 🟥 Copy `app/landing/page.tsx` → `app/(marketing)/page.tsx`
- [ ] 🟥 Update WeldVision link: `href="/landing"` → `href="/"`
- [ ] 🟥 Test `/` loads as landing
- [ ] 🟥 Delete `app/landing/` folder

**Files:**
- **Create:** `my-app/src/app/(marketing)/page.tsx` (from landing)
- **Delete:** `my-app/src/app/landing/` (after verification)

**✓ Verification Test:**

**Action:**
1. Copy landing page to `(marketing)/page.tsx`
2. Update nav WeldVision link to `href="/"`
3. Navigate to `http://localhost:3000/`
4. Verify landing renders, no AppNav
5. Delete `app/landing/` folder

**Expected Result:**
- `/` shows landing page
- No AppNav
- Nav anchors (#technology, #analytics, #impact) work

**Pass Criteria:**
- Landing visible at `/`
- No AppNav
- No console errors

---

#### 🟥 Step 1.2d: Move remaining routes to (app)

**Subtasks:**
- [ ] 🟥 Check which folders exist: run `ls -d my-app/src/app/{demo,replay,compare,seagull,dev} 2>/dev/null` (or equivalent from project root) to list only existing directories
- [ ] 🟥 Move only existing folders to `(app)/`: `demo`, `replay`, `compare` are required; `seagull`, `dev` may not exist in all setups
- [ ] 🟥 For each existing folder: `mv app/<folder> app/(app)/<folder>` (e.g., `mv my-app/src/app/demo my-app/src/app/\(app\)/demo`)
- [ ] 🟥 Run `npm run build` (not just dev)

**Files:**
- **Move:** demo, replay, compare (always); seagull, dev (only if present under `app/`)

**✓ Verification Test:**

**Action:**
1. From `my-app/` or `my-app/src/`: check existing routes with `ls -d app/demo app/replay app/compare app/seagull app/dev 2>/dev/null` (adapt path if running from project root)
2. Move only the folders that exist to `app/(app)/`
3. Run `npm run build` ← **CRITICAL: Build, not just dev**
4. Check for "Module not found" errors
5. Run `npm run dev` and test:
   - `/demo` loads with AppNav
   - `/replay/sess_expert_001` loads
   - `/compare` loads
   - If seagull exists: `/seagull` loads
   - If dev exists: `/dev/torch-viz` loads

**Expected Result:**
- Build succeeds
- No "Module not found" or import errors
- All moved routes load

**Pass Criteria:**
- `npm run build` succeeds
- No import errors in build output
- /demo, /replay, /compare work (seagull, dev if they existed before move)

**Common Failures & Fixes:**
- **Move fails: "No such file or directory":** Folder doesn't exist (e.g., seagull, dev). Only move folders that exist. Use the `ls` check first; skip non-existent folders.
- **Module not found:** Check that moved components use `@/` imports; relative imports like `../app/X` break when paths change. Update to `@/components/X` or correct path.
- **404 on route:** Ensure folder structure matches Next.js conventions; `(app)/demo/page.tsx` → `/demo`.

---

#### 🟥 Step 1.3: Update AppNav — remove isLanding, update links

**Subtasks:**
- [ ] 🟥 Remove `isLanding` and `if (isLanding) return null`
- [ ] 🟥 "Home" → `/` (landing), "Dashboard" → `/dashboard`, "Demo" → `/demo`
- [ ] 🟥 Remove "Landing" link

**Files:**
- **Modify:** `my-app/src/components/AppNav.tsx`

**Code snippet:**

```typescript
// AppNav — no isLanding check; route groups handle it
const isDashboard = pathname === '/dashboard' || pathname.startsWith('/dashboard');
const isDemo = pathname === '/demo' || pathname.startsWith('/demo');
// Links: Home → /, Dashboard → /dashboard, Demo → /demo
```

**✓ Verification Test:**

**Action:**
1. Navigate to `/dashboard` — AppNav shows Home, Dashboard, Demo
2. Click Home → goes to `/` (landing)
3. Click Dashboard → goes to `/dashboard`
4. Navigate to `/` — no AppNav (marketing layout)

**Pass Criteria:**
- AppNav links correct
- No runtime errors

---

#### 🟥 Step 1.4: Update internal links (href="/" → href="/dashboard")

**Subtasks:**
- [ ] 🟥 Grep for `href="/"` and `href="/landing"` in `my-app/src`
- [ ] 🟥 Update compare pages: "Dashboard" / "Back" links `/` → `/dashboard`
- [ ] 🟥 Update dashboard page tests: `__tests__/app/page.test.tsx` → test `(app)/dashboard/page` and update href expectations
- [ ] 🟥 Update landing: WeldVision → `/` (already done in 1.2c)

**Files:**
- **Modify:** `my-app/src/app/(app)/compare/page.tsx` (Link href="/" → href="/dashboard")
- **Modify:** `my-app/src/app/(app)/compare/[sessionIdA]/[sessionIdB]/page.tsx` (same)
- **Modify:** `my-app/src/__tests__/app/page.test.tsx` (import from `@/app/(app)/dashboard/page`, assert href="/dashboard" where relevant)

**✓ Verification Test:**

**Action:**
1. Run `rg 'href="/"' my-app/src` — remaining `/` links should be intentional (landing home)
2. From compare page, click "Dashboard" → should go to `/dashboard`
3. From compare detail, click "Back to dashboard" → `/dashboard`
4. Run `npm test` — all tests pass

**Pass Criteria:**
- No broken "back to dashboard" flows
- Tests pass
- Grep shows no accidental `/` for dashboard

---

### Phase 2 — Landing Content & CTAs

**Goal:** Full landing page with correct CTA destinations, demo UX, social proof placeholders. Split into atomic steps so Hero (parallax) can be debugged independently.

**Time Estimate:** 6–9 hours

**Risk Level:** 🟡 45%

---

#### 🟥 Step 2.1: Ensure framer-motion installed

**Subtasks:**
- [ ] 🟥 Run `npm install framer-motion` in `my-app/` (if not already)
- [ ] 🟥 Confirm `package.json` has `framer-motion`

**✓ Verification Test:**

**Action:**
1. Run `npm ls framer-motion`
2. Run `npm run build`

**Expected Result:**
- framer-motion listed; build succeeds

**Pass Criteria:**
- Dependency present; build succeeds

---

#### 🟥 Step 2.2a: Landing skeleton + fixed nav + empty sections

**Subtasks:**
- [ ] 🟥 Create/ensure `(marketing)/page.tsx` has `'use client'`
- [ ] 🟥 Add fixed nav: WeldVision → `/`, anchors (Technology, Analytics, Impact), Request Demo button
- [ ] 🟥 Add mobile hamburger icon (no dropdown logic yet; icon only)
- [ ] 🟥 Add empty sections with IDs: `<section id="technology">`, `<section id="analytics">`, `<section id="impact">` — so nav anchors work immediately

**Context:** Nav links `#technology`, `#analytics`, `#impact` must scroll to something. Add minimal placeholder sections (e.g. 1 line of text or empty div) so clicking doesn't scroll to nothing.

**Files:**
- **Modify:** `my-app/src/app/(marketing)/page.tsx`

**✓ Verification Test:**

**Action:**
1. Navigate to `/`
2. Click "Technology" in nav → page scrolls to section with id="technology"
3. Click "Analytics" → scrolls to id="analytics"
4. Click "Impact" → scrolls to id="impact"
5. Nav renders; sections exist (can be empty placeholders)

**Pass Criteria:**
- Nav visible
- All three anchor links scroll to corresponding sections
- Mobile hamburger icon visible at <768px
- No console errors

---

#### 🟥 Step 2.2b: Hero section with parallax — *Critical: Animation*

**Why this is critical:** Parallax and useTransform can behave unexpectedly; hero is the first impression.

**Subtasks:**
- [ ] 🟥 Implement gradient text heading: "The Future of Industrial Training"
- [ ] 🟥 Add `useScroll`, `useTransform` for heroY and heroOpacity
- [ ] 🟥 Apply `style={{ y: heroY, opacity: heroOpacity }}` to hero content motion.div
- [ ] 🟥 Add scroll indicator animation (bounce)
- [ ] 🟥 Fix any typos: grep for `durati`, `nt-bold` and replace with `duration`, `font-bold`
- [ ] 🟥 Grid background: If using `transform: 'perspective(500px) rotateX(60deg)'`, test in Safari. Safari can glitch with `perspective()` in transform. Safer: use container `<div style={{ perspective: '500px' }}>` and child `transform: 'rotateX(60deg)'`, or `perspective` as CSS property.

**Files:**
- **Modify:** `my-app/src/app/(marketing)/page.tsx`

**✓ Verification Test:**

**Action:**
1. Open `/`
2. Verify hero heading "The Future of Industrial Training" with gradient
3. Scroll down slowly — hero content should fade and move up (parallax)
4. Run `rg 'durati|nt-bold' my-app/src` — should find nothing

**Pass Criteria:**
- Hero parallax works (fade on scroll)
- Scroll indicator animates
- No typos
- Optional: Test grid in Safari; use perspective workaround if glitchy

---

#### 🟥 Step 2.2c: Stats section

**Subtasks:**
- [ ] 🟥 Add Stats: 87%, $2.4M, 94% with staggered `animate` + `useInView`
- [ ] 🟥 Gradient text for numbers; gray-400 for labels
- [ ] 🟥 Subtext: industry average, savings, quality comparison

**✓ Verification Test:**

**Action:**
1. Scroll to stats section
2. Numbers animate on scroll into view (staggered)
3. All three stats visible: 87%, $2.4M, 94%

**Pass Criteria:**
- Stats render
- Staggered animation on scroll
- No layout shift

---

#### 🟥 Step 2.2d: Technology 4 cards with glass morphism

**Subtasks:**
- [ ] 🟥 Add 4 cards: Real-time Analysis, AI-Powered Insights, Enterprise Security, Plug & Play Hardware
- [ ] 🟥 Glass morphism: backdrop-blur, gradient backgrounds, border-white/10
- [ ] 🟥 Staggered slide-in (x: -30 / x: 30) with `whileInView`

**✓ Verification Test:**

**Action:**
1. Scroll to Technology section
2. Four cards render with icons, headings, descriptions
3. Cards animate on scroll (slide from sides)

**Pass Criteria:**
- 4 cards visible
- Glass morphism styling
- Animations work

---

#### 🟥 Step 2.3: Demo section — placeholder + "Try Full Demo →"

**Subtasks:**
- [ ] 🟥 Demo section: placeholder card (video icon, "Interactive Demo" text) — NOT wrapped in Link
- [ ] 🟥 Add explicit button/link "Try Full Demo →" below placeholder, `href="/demo"`
- [ ] 🟥 Metrics strip: 300°C, 45°, 30°C/s
- [ ] 🟥 Section heading: "See it in action"

**Context:** Per Decision 3, placeholder is visual only. "Try Full Demo →" is the clear CTA to navigate.

**✓ Verification Test:**

**Action:**
1. Scroll to #analytics
2. Click placeholder area — nothing should navigate (or optional: scroll to CTA)
3. Click "Try Full Demo →" — navigates to `/demo`

**Pass Criteria:**
- "Try Full Demo →" link present and works
- Placeholder is visual only (not full-card link)

---

#### 🟥 Step 2.4: Social Proof — generic placeholders

**Subtasks:**
- [ ] 🟥 Replace company names with: "Major US Shipyards", "Defense Contractors", "Fortune 500 Manufacturing", "Heavy Industry Leaders"
- [ ] 🟥 Keep staggered animation
- [ ] 🟥 Update tests to expect these strings

**✓ Verification Test:**

**Action:**
1. Scroll to social proof
2. Verify 4 placeholder items (no Newport News, BAE Systems, etc.)

**Pass Criteria:**
- Generic placeholders only
- No real company names (unless permission obtained)

---

#### 🟥 Step 2.5: CTA section — real destinations + empty-string handling — *Critical: Conversion*

**Why this is critical:** Broken CTAs kill conversions. Empty env vars must fallback correctly.

**Subtasks:**
- [ ] 🟥 Create constants or inline:
  - `DEMO_BOOKING_URL = process.env.NEXT_PUBLIC_DEMO_BOOKING_URL?.trim() || '/demo'`
  - `INVESTOR_DECK_URL = process.env.NEXT_PUBLIC_INVESTOR_DECK_URL?.trim() || '#download-deck'`
- [ ] 🟥 "Schedule a Demo" → DEMO_BOOKING_URL (target="_blank" if URL starts with http)
- [ ] 🟥 "Download Deck" → INVESTOR_DECK_URL (download attr if .pdf)
- [ ] 🟥 Add to `.env.example`: `NEXT_PUBLIC_DEMO_BOOKING_URL`, `NEXT_PUBLIC_INVESTOR_DECK_URL`

**Code snippet:**

```typescript
const DEMO_BOOKING_URL = process.env.NEXT_PUBLIC_DEMO_BOOKING_URL?.trim() || '/demo';
const INVESTOR_DECK_URL = process.env.NEXT_PUBLIC_INVESTOR_DECK_URL?.trim() || '#download-deck';
// <a href={DEMO_BOOKING_URL} target={DEMO_BOOKING_URL.startsWith('http') ? '_blank' : undefined} rel={...}>
```

**✓ Verification Test:**

**Action:**
1. With env unset: Schedule Demo → `/demo`; Download Deck → `#download-deck`
2. With `NEXT_PUBLIC_DEMO_BOOKING_URL=""`: should still fallback to `/demo` (trim)
3. With real URLs: links open correctly, new tab for external

**Pass Criteria:**
- CTAs work with and without env vars
- Empty string env triggers fallback
- External links have rel="noopener noreferrer"

---

### Phase 3 — Mobile Nav & Polish

**Goal:** Mobile hamburger with AnimatePresence, click-outside-to-close, Escape key. Fix click-outside race with stopPropagation.

**Time Estimate:** 1.5–2 hours

**Risk Level:** 🟢 25%

---

#### 🟥 Step 3.1: Mobile nav — AnimatePresence, click-outside, Escape, stopPropagation — *Critical: UX*

**Why this is critical:** Incomplete mobile nav = nav links inaccessible on small screens. Click bubbling causes double-toggle.

**Subtasks:**
- [ ] 🟥 Import `AnimatePresence` from framer-motion
- [ ] 🟥 Add `navRef` and attach to nav element
- [ ] 🟥 Add `e.stopPropagation()` to hamburger button onClick — prevents click from bubbling to document and triggering click-outside before state updates
- [ ] 🟥 Add Escape key handler (useEffect)
- [ ] 🟥 Add click-outside handler (useEffect)
- [ ] 🟥 Wrap mobile dropdown with `AnimatePresence`
- [ ] 🟥 Hamburger toggles to X when open

**Code snippet for hamburger:**

```typescript
<button
  type="button"
  onClick={(e) => {
    e.stopPropagation();
    setMobileNavOpen(!mobileNavOpen);
  }}
  aria-expanded={mobileNavOpen}
  aria-controls="mobile-nav"
  ...
>
```

**✓ Verification Test:**

**Action:**
1. Resize to <768px
2. Click hamburger — dropdown opens with animation
3. Click outside nav — dropdown closes
4. Open again; press Escape — dropdown closes
5. Rapid open/close — no double-toggle (stopPropagation prevents)
6. Open/close 5 times — no memory leaks (listeners cleaned up)

**Pass Criteria:**
- Mobile nav opens/closes
- Click-outside and Escape work
- No race condition on hamburger click
- AnimatePresence runs exit animation

---

### Phase 4 — Tests & Verification

**Goal:** Automated tests pass with Proxy-based Framer mock. Mock must filter style prop to avoid passing MotionValues to DOM.

**Time Estimate:** 2–2.5 hours

**Risk Level:** 🟡 35%

---

#### 🟥 Step 4.1: Proxy-based Framer Motion mock — filter style prop — *Critical: Test stability*

**Why this is critical:** `style={{ y: heroY, opacity: heroOpacity }}` passes MotionValue objects. React rejects these as invalid style values. Mock must omit or filter style.

**Code Implementation:**

```typescript
// my-app/src/__tests__/app/landing/page.test.tsx
// KEEP test file at __tests__/app/landing/page.test.tsx (avoid (marketing) in path)
// Import: import LandingPage from '@/app/(marketing)/page';

jest.mock('framer-motion', () => {
  const React = require('react');
  return {
    motion: new Proxy(
      {},
      {
        get: (target, prop) => {
          return React.forwardRef(
            (props: Record<string, unknown>, ref: React.Ref<unknown>) => {
              const { style, ...rest } = props;
              // Omit style in tests — MotionValues aren't valid CSS
              return React.createElement(prop as string, { ...rest, ref });
            }
          );
        },
      }
    ),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useScroll: () => ({ scrollYProgress: { get: () => 0 } }),
    useTransform: () => ({ get: () => 0 }),
    useInView: () => true,
  };
});
```

**Subtasks:**
- [ ] 🟥 Replace manual motion mock with Proxy-based mock
- [ ] 🟥 Filter/omit `style` prop in Proxy (destructure `{ style, ...rest }`, pass only `rest`)
- [ ] 🟥 Add `AnimatePresence` to mock
- [ ] 🟥 Keep test file at `__tests__/app/landing/page.test.tsx`, update import to `@/app/(marketing)/page`

**✓ Verification Test:**

**Action:**
1. Run `npm test -- landing`
2. All tests pass
3. No "Invalid DOM property" or style-related errors

**Pass Criteria:**
- Tests green
- Mock handles motion.div, motion.section, motion.button, etc.
- No style/MotionValue errors

---

#### 🟥 Step 4.2: Update landing tests for new content and links

**Subtasks:**
- [ ] 🟥 Update social proof: expect "Major US Shipyards", "Defense Contractors", etc. (not company names)
- [ ] 🟥 Add test for "Try Full Demo →" link to `/demo`
- [ ] 🟥 Update CTA assertions: Schedule Demo, Download Deck
- [ ] 🟥 Fix import path to `@/app/(marketing)/page`
- [ ] 🟥 Rename test file if needed: keep `landing/page.test.tsx`, import from (marketing)

**✓ Verification Test:**

**Action:**
1. Run `npm test -- landing`
2. Run `npm test`

**Pass Criteria:**
- All tests pass
- Social proof expects generic placeholders
- "Try Full Demo →" href="/demo"

---

#### 🟥 Step 4.3: Manual verification and accessibility

**Subtasks:**
- [ ] 🟥 Test in Chrome, Firefox, Safari — no console errors
- [ ] 🟥 Test at 375px — hamburger, stacked sections
- [ ] 🟥 Keyboard: Tab through nav, anchors, buttons; Enter activates
- [ ] 🟥 Verify Escape closes mobile nav
- [ ] 🟥 aria-label, aria-labelledby where missing
- [ ] 🟥 Smooth scroll on anchor click

**✓ Verification Test:**

**Action:**
1. Open DevTools Console; navigate entire page
2. Responsive mode 375px
3. Tab through; Enter on links
4. Open mobile nav; Escape

**Pass Criteria:**
- No console errors
- Keyboard reachable
- Mobile nav keyboard-accessible

---

## Pre-Flight Checklist

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Node.js v18+ | `node --version` → v18.x+ | ⬜ |
| | npm dependencies | `cd my-app && npm install` | ⬜ |
| | Next.js dev server | `npm run dev` → localhost:3000 | ⬜ |
| | Routes to move (Step 1.2d) | `ls -d my-app/src/app/{demo,replay,compare,seagull,dev} 2>/dev/null` → lists existing folders only | ⬜ |
| **Phase 2** | Phase 1 complete | `/` = landing, `/dashboard` = dashboard | ⬜ |
| | framer-motion | `npm ls framer-motion` | ⬜ |
| **Phase 3** | Phase 2 complete | All sections render | ⬜ |
| **Phase 4** | Phase 3 complete | Mobile nav works | ⬜ |
| | Jest | `npm test` passes | ⬜ |

---

## Success Criteria (End-to-End)

| Requirement | Target Behavior | Verification |
|-------------|-----------------|---------------|
| **Landing at /** | yoursite.com/ shows landing | Navigate to / → landing page |
| **Dashboard at /dashboard** | yoursite.com/dashboard shows app | Navigate to /dashboard → dashboard |
| **No AppNav on landing** | Landing has own nav only | Visual; no AppNav bar on / |
| **AppNav on app routes** | Dashboard, demo have AppNav | Visual on /dashboard, /demo |
| **Hero gradient + parallax** | Content fades on scroll | Scroll hero; observe |
| **Stats (87%, $2.4M, 94%)** | Staggered fade-in | Scroll to stats; observe |
| **4 technology cards** | Real-time, AI, Security, Hardware | Visual |
| **Demo section** | Placeholder + "Try Full Demo →" | Click Try Full Demo → /demo |
| **Social proof** | Generic placeholders | No real company names |
| **Schedule Demo** | Calendly or /demo fallback | Click; correct destination |
| **Download Deck** | PDF or #download-deck fallback | Click; download or anchor |
| **Mobile nav** | Hamburger, click-outside, Escape | 375px; test all |
| **Smooth scroll** | Anchor links scroll smoothly | Click #technology |
| **Keyboard nav** | Tab, Enter, Escape work | Manual test |

---

## Progress Tracking

| Phase | Steps | Completed | Percentage |
|-------|-------|-----------|------------|
| Phase 1 | 6 | 0 | 0% |
| Phase 2 | 9 | 0 | 0% |
| Phase 3 | 1 | 0 | 0% |
| Phase 4 | 3 | 0 | 0% |
| **Total** | **19** | **0** | **0%** |

---

## Notes & Learnings

[Add notes here during implementation]

---

⚠️ **IMPORTANT RULES:**

1. **Do NOT mark a step 🟩 Done until its verification test passes**
2. **If blocked, mark step 🟨 In Progress and document what failed**
3. **If a step takes 2x longer than estimated, pause and reassess**
4. **Run verification tests in order**
5. **Update "Overall Progress" after each step**
6. **Run `npm run build` after Phase 1 route moves — not just `npm run dev`**

---

## Quality Checklist

- [x] Spent 30+ minutes on plan
- [x] All steps specific and actionable
- [x] Every step has verification test
- [x] Critical steps identified with code snippets
- [x] Dependencies clear (1.2 split into 1.2a-d; 2.2 split into 2.2a-d)
- [x] Phases deliver user value
- [x] Risk heatmap realistic
- [x] Time estimates realistic
- [x] Architectural decisions documented
- [x] Verification tests explain how to observe
- [x] Common failures and fixes included
- [x] Pre-flight checklist complete
- [x] Success criteria measurable
- [x] Step 1.2 split into atomic steps (1.2a-d)
- [x] Step 2.2 split into skeleton, hero, stats, tech (2.2a-d)
- [x] npm run build in Step 1.2d
- [x] Empty sections in Step 2.2a for nav anchors
- [x] e.stopPropagation() on hamburger (Step 3.1)
- [x] Filter style prop in Framer mock (Step 4.1)
- [x] Empty-string env var handling (Step 2.5)
- [x] Safari grid note (Step 2.2b)
- [x] Smooth scroll conflict note (Step 1.1)
- [x] Test file path: keep at landing/page.test.tsx, import from (marketing)
- [x] Step 1.2d: Check folder existence before move (seagull, dev may not exist); move only existing folders
