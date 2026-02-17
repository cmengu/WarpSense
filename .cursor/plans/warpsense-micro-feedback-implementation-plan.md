# WarpSense Micro-Feedback — Implementation Blueprint (Phase 1)

**Date:** 2025-02-17  
**Issue:** `.cursor/issues/warpsense-micro-feedback-feature.md`  
**Exploration:** `.cursor/explore/warpsense-micro-feedback-exploration.md`  
**Time Budget:** 90–120 minutes minimum for plan creation  
**Implementation Estimate:** 14–18 hours (Phase 1)

### Quick Reference

| Phase | Steps | Est. Hours | Key deliverable |
|-------|-------|------------|-----------------|
| 1. Foundation | 7 | 5.5 | types + lib + migrated tests |
| 2. FeedbackPanel | 7 | 4 | critical styling, onClick, frameIndex |
| 3. Replay | 14 | 8.5 | FeedbackPanel + markers + click-to-scrub + SSR verification |
| **Total** | **28** | **~18** | Full Phase 1 feature |

**Critical path:** 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 → 3.1 → 3.2 → 3.3

---

## Phase 0: Understand Your Role

**This is Step 3 of 3:**
1. **Create Issue** (COMPLETE — the WHAT and WHY)
2. **Explore Feature** (COMPLETE — the HOW)
3. **Create Plan** ← You are here (step-by-step EXECUTION)

**Your job:**
- Break exploration into atomic steps
- Write verification tests for EVERY step
- Identify critical steps needing code review
- Order steps by dependencies
- Estimate effort realistically
- Document failure modes
- Create quality gates

**NOT your job:**
- Implement the feature
- Question architectural decisions
- Research alternatives

---

## MANDATORY PRE-PLANNING THINKING SESSION (30 minutes minimum)

### A. Exploration Review and Synthesis (10 minutes)

#### 1. Core approach (one sentence)

Convert session-level aggregates into frame-anchored, actionable feedback items that welders can click to jump to the exact moment during replay — computed on the client from existing frame data, using angle drift and thermal symmetry generators.

#### 2. Key decisions

- **Client-side compute:** generateMicroFeedback runs in the browser after fetchSession; no new API.
- **Extend FeedbackItem:** Add optional `frameIndex` and `type` for backward compatibility; **MicroFeedbackItem requires both** (frameIndex: number, type: MicroFeedbackType). Single panel for session + micro.
- **Thresholds:** 45° target, ±5° warning, ±15° critical for angle; max(|N-S|,|E-W|) ≥ 20°C for thermal.
- **Cap:** 50 items per type (angle, thermal).
- **No 3D overlay Phase 1:** WebGL limit (2 Canvas already); use FeedbackPanel + timeline markers only.

#### 3. Why this approach

Client-side avoids new backend endpoints, keeps latency low (frames already in memory), and reuses FeedbackPanel. Extending FeedbackItem preserves WelderReport compatibility (items without frameIndex behave as today). **MicroFeedbackItem enforces frameIndex and type** — optionality here breaks click-to-scrub; it is a ticking time bomb. Hardcoded thresholds and caps reduce scope; Phase 4 can add configurability.

#### 4. Major components

| Component | Purpose |
|----------|---------|
| **micro-feedback.ts types** | MicroFeedbackItem (frameIndex required, type required), MicroFeedbackType, MicroFeedbackSeverity — canonical shape for frame-level items. **Never optional.** |
| **lib/micro-feedback.ts** | generateMicroFeedback(frames) — pure function: angle drift + thermal symmetry generators. **Robust null/NaN guards; explicit missing-sensor checks; try-catch wrapper.** |
| **ai-feedback.ts (extended)** | FeedbackItem gains optional frameIndex, type — unified contract for session and micro |
| **FeedbackPanel** | Renders session + micro items; when frameIndex **and type** present → clickable; severity styling from constants; **explicit handling when type is missing** → never treat as clickable |
| **Replay page** | useMemo generateMicroFeedback; FeedbackPanel; timeline markers overlay; onFrameSelect → setCurrentTimestamp |

#### 5. Data flow

```
Input: Session.frames (from fetchSession)
  ↓
Transform: generateMicroFeedback(frames) → MicroFeedbackItem[]
  - angle generator: |angle_degrees - 45| > 5° → warning; >15° → critical
  - thermal generator: max(|N-S|,|E-W|) ≥ 20°C on frames with has_thermal_data AND all 4 cardinal sensors present
  ↓
Process: useMemo([session?.frames]) — precompute once on load
  ↓
Output: FeedbackPanel(items) + TimelineMarkers(items)
  - click item/marker → setCurrentTimestamp(frames[frameIndex].timestamp_ms)
```

#### 6. Biggest risks

- **Risk #1 (Exploration):** Precompute blocks UI for >3s on 50k frames — mitigation: benchmark; web worker if needed; cap or chunk.
- **Risk #2:** Alert fatigue — too many items — mitigation: 50 per type cap; severity filter later.
- **Risk #3:** FeedbackPanel + WelderReport collision — mitigation: optional frameIndex/onFrameSelect; WelderReport never passes them.
- **Risk #4:** Timeline marker overlap — mitigation: cluster or show count on hover.
- **Risk #5:** Null sensor data crash — mitigation: guards in every generator; try-catch in generateMicroFeedback; **thermal generator skips frames with missing N/S/E/W readings** (do not use DEFAULT_AMBIENT for variance — false positives).
- **Risk #6:** Optional frameIndex/type breaks click — mitigation: **MicroFeedbackItem requires both**; session items omit both; FeedbackPanel: **only treat as clickable when BOTH frameIndex AND type are present and valid**; defaults are dangerous.

#### 7. What exploration did NOT answer

- **Gap #1:** Exact layout when session-level + micro items together — single sorted list vs separate sections. Plan assumes: single list sorted by frameIndex (micro) then session items; session items have no frameIndex.
- **Gap #2:** Timeline marker clustering UX when >15 markers — Plan: simple overlay; cluster in Phase 4 if needed.
- **Gap #3:** Whether WelderReport should eventually show micro-feedback — Out of scope Phase 1; replay only.

---

### B. Dependency Brainstorm (10 minutes)

**Major work items (before ordering):**

1. Create `types/micro-feedback.ts` — MicroFeedbackItem (frameIndex required, type required), MicroFeedbackType, MicroFeedbackSeverity
2. Extend `types/ai-feedback.ts` — FeedbackItem optional frameIndex, type
3. Create `lib/micro-feedback.ts` — generateMicroFeedback, angle + thermal generators, robust guards, try-catch, **explicit missing-sensor check for thermal**
4. Migrate prototype tests to lib (replace inline with imports)
5. Add "critical" severity to FeedbackSeverity in ai-feedback
6. Update FeedbackPanel — severity styling from constants, **explicit handling: type missing → not clickable**, frameIndex key, onClick when frameIndex+type present, onFrameSelect guarded
7. Add onFrameSelect prop to FeedbackPanel
8. Replay page — useMemo generateMicroFeedback
9. Replay page — render FeedbackPanel with micro items
10. Replay page — timeline markers overlay
11. Replay page — jump handler (setCurrentTimestamp)
12. Integrate firstTimestamp/lastTimestamp for marker positions
13. Update FeedbackPanel tests for critical, frameIndex, type, onClick, WelderReport regression
14. Update/remove prototype test (use lib directly)
15. E2E or integration test for replay + micro-feedback
16. WelderReport regression test (unchanged behavior)
17. Performance benchmark (10k frames <200ms)
18. Accessibility: keyboard nav, aria-live, jest-axe
19. Documentation: CONTEXT.md or similar
20. Changelog entry

**Dependency graph:** (unchanged from original)

---

### C. Risk-Based Planning (10 minutes)

| Risk | Prob | Impact | Plan implication |
|------|------|--------|-------------------|
| Precompute >3s on 50k frames | 25% | High | Step: Add perf test; if fail → web worker or cap |
| Alert fatigue | 40% | Medium | Already mitigated: 50 cap per type |
| FeedbackPanel collision | 30% | Low | Optional fields; WelderReport regression test |
| Timeline marker overlap | 50% | Medium | Simple overlay first; cluster Phase 4 |
| Null sensor crash | 10% | High | Guards in generators; **thermal: skip frames with missing cardinal readings**; try-catch |
| Optional frameIndex/type crash | 15% | High | MicroFeedbackItem requires both; FeedbackPanel: **only clickable when BOTH present**; validate before use |
| Scope creep to Phase 2 | 30% | Medium | Phase doc; resist voltage/speed in Phase 1 |
| SSR/hydration error | 20% | High | Replay is 'use client'; generateMicroFeedback in useMemo only; verify no SSR |
| Key collision in FeedbackPanel | 30% | Medium | Key format: frameIndex+type for micro; severity+i for session |
| onFrameSelect undefined crash | 20% | High | Guard: never call onFrameSelect without typeof check |
| Severity exhaustivity | 25% | High | **grep all usages; every switch/if-else must handle info|warning|critical; no default fallback without explicit docs** |

---

## 2. Step Definition (60+ minutes)

---

## Phase 1 — Foundation: Types and Micro-Feedback Engine

**Goal:** Canonical types and `generateMicroFeedback(frames)` producing correct angle + thermal items. **MicroFeedbackItem enforces frameIndex and type — never optional.** Robust null/NaN handling; **explicit missing-thermal-sensor check**; try-catch; **exhaustivity for severity everywhere downstream**.

**Time Estimate:** 5 hours  
**Risk Level:** 🟢 Low (10%)  
**Delivered value:** Enables Phases 2–3

---

### Step 1.1: Create `types/micro-feedback.ts` — *Non-Critical*

**What:** Create the canonical type definitions for micro-feedback items. **MicroFeedbackItem must require frameIndex and type** — optionality here breaks click-to-scrub; it is a ticking time bomb.

**Why:** Single source of truth for MicroFeedbackItem shape; lib and components import from here.

**Files:**
- **Create:** `my-app/src/types/micro-feedback.ts`
- **Depends on:** None (first step)

**Subtasks:**
- [ ] Create file with MicroFeedbackType = "angle" | "thermal" (**required** for micro items — no optional)
- [ ] Add MicroFeedbackSeverity = "info" | "warning" | "critical"
- [ ] Add MicroFeedbackItem interface: **frameIndex: number** (required), **type: MicroFeedbackType** (required), severity, message, suggestion?
- [ ] Add JSDoc: "frameIndex and type are REQUIRED for micro-feedback; omit only for session-level FeedbackItem. Never use optional here."
- [ ] Export all types

**Implementation note:** MicroFeedbackItem passed to FeedbackPanel does **not** require `timestamp_ms`. The timestamp is derived at click time from `frames[frameIndex].timestamp_ms` inside FeedbackPanel. Do not add redundant `timestamp_ms` to MicroFeedbackItem.

**Severity exhaustivity (MANDATORY):** After Step 1.2, run:
```bash
grep -r 'FeedbackSeverity\|MicroFeedbackSeverity' my-app/src --include='*.ts' --include='*.tsx'
```
For every usage found: ensure switch/if-else explicitly handles `"info"` | `"warning"` | `"critical"`. **Defaults are dangerous** — if you add a default branch, document exactly what happens for unknown values. No silent fallback.

**✓ Verification Test:**

**Setup:** Open `my-app/src/types/micro-feedback.ts`

**Action:** Import in a test file and construct a MicroFeedbackItem.

**Expected:**
- Types compile without error
- MicroFeedbackItem has **frameIndex: number** (required), **type: MicroFeedbackType** (required), severity, message, suggestion?
- Cannot assign `{ severity: "warning", message: "x" }` without frameIndex and type — TypeScript must error
- Cannot assign `{ frameIndex: 0, severity: "warning", message: "x" }` without type — TypeScript must error
- Can assign `{ frameIndex: 0, severity: "warning", message: "x", type: "angle" }` to MicroFeedbackItem

**Pass criteria:**
- [ ] File exists and exports MicroFeedbackItem, MicroFeedbackType, MicroFeedbackSeverity
- [ ] No TypeScript errors
- [ ] frameIndex and type are required (not optional)
- [ ] Can assign `{ frameIndex: 0, severity: "warning", message: "x", type: "angle" }` to MicroFeedbackItem

**Time estimate:** 0.5 hours

---

### Step 1.2: Extend FeedbackItem in ai-feedback.ts — *Critical: Type contract change*

**Why critical:** Affects FeedbackPanel, WelderReport, and all consumers. Must remain backward compatible.

**Context:** FeedbackItem today has severity, message, timestamp_ms, suggestion. WelderReport passes items with timestamp_ms: null. We add **optional** frameIndex?: number and type?: MicroFeedbackType for backward compatibility. Session-level items omit both. **Micro items (from generateMicroFeedback) always have both** — they satisfy MicroFeedbackItem which requires them. **Explicit handling:** When type is missing, the item is session-level — never treat as clickable.

**Files:**
- **Modify:** `my-app/src/types/ai-feedback.ts`
- **Depends on:** Step 1.1

**Subtasks:**
- [ ] Add FeedbackSeverity "critical" to the union
- [ ] Add optional frameIndex?: number to FeedbackItem
- [ ] Add optional type?: MicroFeedbackType to FeedbackItem
- [ ] Ensure existing FeedbackItem usages still valid (timestamp_ms: null, no frameIndex, no type)
- [ ] **Exhaustivity check:** After changes, run `grep -r 'FeedbackSeverity' my-app/src --include='*.ts' --include='*.tsx'`; for each match, ensure switch/if-else handles "info" | "warning" | "critical". Document any default.

**✓ Verification Test:**

**Setup:** Open WelderReport page and ai-feedback tests.

**Action:** Run `npm test -- ai-feedback` and load WelderReport in dev.

**Expected:**
- All ai-feedback tests pass
- WelderReport renders without error
- FeedbackItem with only severity, message, timestamp_ms, suggestion still valid
- FeedbackItem with frameIndex and type also valid

**Pass criteria:**
- [ ] FeedbackSeverity includes "critical"
- [ ] FeedbackItem has optional frameIndex and type
- [ ] ai-feedback.test.ts passes
- [ ] No TypeScript errors in WelderReport
- [ ] Existing mock FeedbackItems (no frameIndex, no type) still work

**Post-Step Verification (ai-feedback.test.ts):**

Add explicit assertion for the new "critical" value:

```typescript
it("FeedbackSeverity accepts info, warning, and critical", () => {
  const info: FeedbackSeverity = "info";
  const warning: FeedbackSeverity = "warning";
  const critical: FeedbackSeverity = "critical";
  expect(info).toBe("info");
  expect(warning).toBe("warning");
  expect(critical).toBe("critical");
});
```

**Post-Step Checklist:**
- [ ] Run `grep -r 'FeedbackSeverity' my-app/src --include='*.ts' --include='*.tsx'`; ensure no switch/if-else exhaustivity breaks (all branches handle "critical")

**Rollback:** Revert changes; WelderReport should work as before.

**Time estimate:** 0.5 hours

---

### Step 1.3: Create `lib/micro-feedback.ts` with generateMicroFeedback — *Critical: Core engine*

**Why critical:** This is the core feature logic. Bugs here produce wrong or no feedback. **Real sensor data is messy** — null frames, missing thermal sensors, malformed data. Wrap in try-catch; guard every risky operation.

**Context:** Pure function. Input: Frame[]. Output: MicroFeedbackItem[] sorted by frameIndex. Uses extractFivePointFromFrame from frameUtils. **CRITICAL:** extractFivePointFromFrame returns DEFAULT_AMBIENT_CELSIUS (20) for missing readings — **do NOT use that for thermal symmetry**. Missing sensor + real reading = false positive (e.g. north=200, south=missing→20 → delta 180°C). **You must skip frames where any of N/S/E/W readings are absent.**

**Angle generator:** |angle_degrees - 45| > 5 → warning; >15° → critical. **Guard:** target (ANGLE_TARGET_DEG) is constant — always exists. **Guard angle:** null, undefined, NaN → skip frame.

**Thermal generator:** max(|N-S|,|E-W|) ≥ 20°C. **Guard:** has_thermal_data. **Guard:** extractFivePointFromFrame return. **Guard:** **ALL four cardinal directions must have actual readings** — check frame.thermal_snapshots[0]?.readings for north, south, east, west. If any direction has no reading with numeric temp_celsius, skip frame. Do not use DEFAULT_AMBIENT fallback for variance calculation.

**Required guards:**
1. **Input validation:** `if (!Array.isArray(frames) || frames.length === 0) return [];`
2. **Frame iteration:** Skip frames that are null, undefined, or malformed (missing required structure)
3. **Angle generator:** Validate target (ANGLE_TARGET_DEG constant — exists). **Guard angle:** `if (a == null || typeof a !== 'number' || Number.isNaN(a)) continue;`
4. **Thermal generator:** Guard has_thermal_data; guard extractFivePointFromFrame return; **guard: verify all 4 cardinal directions have readings before computing variance** (see implementation below)
5. **Outer wrapper:** Wrap entire generateMicroFeedback body in try-catch; on error return [] and log; never throw to caller

**Implementation (full code with guards):**

```typescript
/**
 * WarpSense Micro-Feedback — frame-level actionable guidance.
 *
 * Generates MicroFeedbackItem[] from frames for angle drift and thermal symmetry.
 * Client-side only; called after fetchSession. Precompute once per session.
 *
 * API: v1 — exported types and generateMicroFeedback. Changes are documented in CHANGELOG.
 *
 * @see .cursor/issues/warpsense-micro-feedback-feature.md
 * @see .cursor/explore/warpsense-micro-feedback-exploration.md
 */

import type { Frame } from "@/types/frame";
import { extractFivePointFromFrame } from "@/utils/frameUtils";
import type {
  MicroFeedbackItem,
  MicroFeedbackSeverity,
} from "@/types/micro-feedback";

const ANGLE_TARGET_DEG = 45;
const ANGLE_WARNING_THRESHOLD_DEG = 5;
const ANGLE_CRITICAL_THRESHOLD_DEG = 15;
const THERMAL_VARIANCE_THRESHOLD_CELSIUS = 20;
const CAP_PER_TYPE = 50;

const CARDINAL_DIRECTIONS = ["north", "south", "east", "west"] as const;

/** Returns true only if all 4 cardinal directions have a numeric reading. */
function hasAllCardinalReadings(frame: Frame): boolean {
  const readings = frame.thermal_snapshots?.[0]?.readings ?? [];
  return CARDINAL_DIRECTIONS.every((dir) =>
    readings.some((r) => r.direction === dir && typeof r.temp_celsius === "number" && !Number.isNaN(r.temp_celsius))
  );
}

function generateAngleDriftFeedback(frames: Frame[]): MicroFeedbackItem[] {
  const items: MicroFeedbackItem[] = [];
  for (let i = 0; i < frames.length && items.length < CAP_PER_TYPE; i++) {
    const frame = frames[i];
    if (!frame) continue;
    const a = frame.angle_degrees;
    if (a == null || typeof a !== "number" || Number.isNaN(a)) continue;
    const dev = Math.abs(a - ANGLE_TARGET_DEG);
    if (dev <= ANGLE_WARNING_THRESHOLD_DEG) continue;
    const severity: MicroFeedbackSeverity =
      dev >= ANGLE_CRITICAL_THRESHOLD_DEG ? "critical" : "warning";
    items.push({
      frameIndex: i,
      severity,
      message: `Torch angle drifted ${dev.toFixed(1)}° at frame ${i} — keep within ±${ANGLE_WARNING_THRESHOLD_DEG}°`,
      suggestion: "Maintain consistent work angle for uniform penetration.",
      type: "angle",
    });
  }
  return items;
}

function generateThermalSymmetryFeedback(frames: Frame[]): MicroFeedbackItem[] {
  const items: MicroFeedbackItem[] = [];
  for (let i = 0; i < frames.length && items.length < CAP_PER_TYPE; i++) {
    const frame = frames[i];
    if (!frame || !frame.has_thermal_data) continue;
    if (!hasAllCardinalReadings(frame)) continue;
    const five = extractFivePointFromFrame(frame);
    if (!five) continue;
    const { north, south, east, west } = five;
    if (
      north == null || south == null || east == null || west == null ||
      Number.isNaN(north) || Number.isNaN(south) || Number.isNaN(east) || Number.isNaN(west)
    ) continue;
    const maxDelta = Math.max(
      Math.abs(north - south),
      Math.abs(east - west)
    );
    if (maxDelta <= THERMAL_VARIANCE_THRESHOLD_CELSIUS) continue;
    items.push({
      frameIndex: i,
      severity: "warning",
      message: `Thermal asymmetry detected at frame ${i} (Δ${maxDelta.toFixed(0)}°C) — aim for uniform heating`,
      suggestion: "Check torch position and travel direction.",
      type: "thermal",
    });
  }
  return items;
}

/**
 * Generate micro-feedback from session frames.
 *
 * Runs angle drift and thermal symmetry generators. Returns combined,
 * sorted-by-frameIndex items. Caps at CAP_PER_TYPE per type.
 *
 * Defensive: wraps in try-catch; never throws. Malformed frames skipped.
 * Thermal: skips frames with missing cardinal sensor readings.
 *
 * @param frames - Session frames (from Session.frames).
 * @returns MicroFeedbackItem[] sorted by frameIndex.
 */
export function generateMicroFeedback(frames: Frame[]): MicroFeedbackItem[] {
  try {
    if (!Array.isArray(frames) || frames.length === 0) return [];
    const angle = generateAngleDriftFeedback(frames);
    const thermal = generateThermalSymmetryFeedback(frames);
    return [...angle, ...thermal].sort((a, b) => a.frameIndex - b.frameIndex);
  } catch (err) {
    console.warn("Micro-feedback generation failed:", err);
    return [];
  }
}
```

**Files:**
- **Create:** `my-app/src/lib/micro-feedback.ts`
- **Depends on:** Step 1.1, frameUtils.extractFivePointFromFrame (exists)

**Subtasks:**
- [ ] Create file with constants
- [ ] Implement hasAllCardinalReadings — skip thermal frame if any N/S/E/W missing
- [ ] Implement generateAngleDriftFeedback with null/NaN guards
- [ ] Implement generateThermalSymmetryFeedback with hasAllCardinalReadings + null/NaN guards
- [ ] Implement generateMicroFeedback with try-catch and input validation
- [ ] Add JSDoc @module for API stability note

**✓ Verification Test:**

**Required test cases (non-negotiable):**
- [ ] Empty frames `[]` → []
- [ ] null/undefined frames → [] (caller passes null → use `?? []` at call site; lib receives [] if guarded)
- [ ] Angle drift at 51° → warning; at 60° → critical
- [ ] Null/undefined angle_degrees → skip frame, no crash
- [ ] NaN angle_degrees → skip frame
- [ ] Thermal N-S 40°C delta → item (when all 4 cardinals present)
- [ ] has_thermal_data false → skip thermal
- [ ] extractFivePointFromFrame returns null → skip
- [ ] Thermal with **missing north reading** (no reading with direction="north") → skip, no crash
- [ ] Thermal with **missing south/east/west** → skip
- [ ] Thermal with null north/south/east/west in five → skip
- [ ] Combined sorted by frameIndex
- [ ] Cap 50 per type
- [ ] **10k frames < 200ms** — profile; if >200ms, memoize or use map instead of reduce
- [ ] **Angle-only session** — frames with no thermal data → only angle items
- [ ] **Thermal-only session** — frames with no angle data → only thermal items
- [ ] **Large array** — 10k+ frames doesn't crash or hang

**Pass criteria:** All tests pass; 10k-frame perf test passes.

**Time estimate:** 1.5 hours

---

### Step 1.4: Migrate prototype tests to lib/micro-feedback — *Non-Critical*

**What:** Replace inline prototype in `__tests__/lib/micro-feedback-prototype.test.ts` with imports from `@/lib/micro-feedback` and `@/types/micro-feedback`. Keep same test cases **plus** add edge-case tests from Step 1.3.

**Why:** Prototype validated logic; now lib is source of truth; tests must use lib.

**Ordering note:** Step 1.7 can be done *before* Step 1.4 to have `frameFixtures` (makeFrame, makeThermalSnapshot) ready for migration.

**Files:**
- **Modify:** `my-app/src/__tests__/lib/micro-feedback-prototype.test.ts`
- **Create or modify:** `my-app/src/__tests__/lib/micro-feedback.test.ts`
- **Depends on:** Step 1.3

**Subtasks:**
- [ ] Change test file to import generateMicroFeedback from @/lib/micro-feedback
- [ ] Import MicroFeedbackItem, Frame from types
- [ ] Remove inline prototype
- [ ] Keep makeFrame and makeThermalSnapshot helpers (or move to frameFixtures)
- [ ] **Add:** angle-only test; thermal-only test; **missing cardinal reading test** (e.g. frame with only center, no north); NaN angle test
- [ ] Run `npm test -- micro-feedback` — all pass
- [ ] Optionally rename file to micro-feedback.test.ts

**✓ Verification Test:** All tests pass including new edge cases.

**Time estimate:** 1 hour

---

### Step 1.5: Add WelderReport regression safeguard — *Non-Critical*

(Same as original plan — unchanged)

**Time estimate:** 0.5 hours

---

### Step 1.6: Add JSDoc export tags to lib/micro-feedback — *Non-Critical*

(Same as original — add @module with API stability note)

**Time estimate:** 0.25 hours

---

### Step 1.7: Create frame test helpers — *Non-Critical*

(Same as original plan)

**Time estimate:** 0.5 hours

---

**Phase 1 Total Time:** 5.5 hours

---

## Phase 2 — FeedbackPanel Extension

**Goal:** FeedbackPanel renders micro items with critical severity, frameIndex, type, and click-to-scrub. **Styling from constants** (no hardcoded strings per severity). **onFrameSelect guarded** — never assume it exists. **Explicit handling when type is missing:** never treat as clickable. **Keys include frameIndex and type** — no collisions. **Severity exhaustivity:** use SEVERITY_STYLES with fallback only when unknown — document behavior.

**Time Estimate:** 3 hours  
**Risk Level:** 🟡 Medium (WelderReport compatibility)  
**Delivered value:** Component ready for replay

---

### Step 2.1: Add "critical" severity styling to FeedbackPanel — *Non-Critical*

**What:** Extend FeedbackPanel to handle severity "critical" with distinct styling. **Use a SEVERITY_STYLES constant** — do not hardcode classes per severity inline. **Exhaustivity:** Every severity value ("info" | "warning" | "critical") must have an explicit entry. If unknown severity (malformed data), fall back to "info" and log a warning — document this.

**Why:** Micro-feedback uses critical for severe angle drift (>15°); FeedbackPanel currently only has info and warning.

**Files:**
- **Modify:** `my-app/src/components/welding/FeedbackPanel.tsx`
- **Depends on:** Step 1.2

**Implementation:**

```typescript
// At top of file or in constants
const SEVERITY_STYLES: Record<FeedbackSeverity, { bg: string; border: string; icon: string }> = {
  info: {
    bg: "bg-blue-50 dark:bg-blue-950/20",
    border: "border-blue-500",
    icon: "ℹ️",
  },
  warning: {
    bg: "bg-violet-50 dark:bg-violet-950/20",
    border: "border-violet-500",
    icon: "⚠️",
  },
  critical: {
    bg: "bg-amber-50 dark:bg-amber-950/20",
    border: "border-amber-500",
    icon: "⛔",
  },
};

// Usage - with explicit fallback for unknown severity
function getSeverityStyle(severity: FeedbackSeverity) {
  if (severity in SEVERITY_STYLES) {
    return SEVERITY_STYLES[severity as keyof typeof SEVERITY_STYLES];
  }
  console.warn(`Unknown FeedbackSeverity: ${severity}, falling back to info`);
  return SEVERITY_STYLES.info;
}
```

**Subtasks:**
- [ ] Add SEVERITY_STYLES constant with all three values
- [ ] Use getSeverityStyle or equivalent for styling (explicit fallback with warn)
- [ ] Add data-testid per severity: `data-testid={\`feedback-item-${item.severity}\`}`

**✓ Verification Test:** Render with critical item; distinct styling; no hardcoded strings per severity. Render with invalid severity string → falls back to info, console.warn.

**Time estimate:** 0.5 hours

---

### Step 2.2: Add onFrameSelect prop and click handler to FeedbackPanel — *Critical: UX contract*

**Why critical:** Defines the contract for replay integration. **onFrameSelect is optional** — if optional, **never assume it exists**. Guard before calling: `if (typeof onFrameSelect === 'function' && timestamp_ms != null) { onFrameSelect(timestamp_ms); }`. **frameIndex and type must BOTH be validated** before treating as clickable: **only when BOTH frameIndex AND type are present and valid** do we allow click. Session-level items have neither — never treat as clickable. **Malformed data:** if frameIndex present but type missing (or invalid) → do NOT treat as clickable; render non-interactive.

**What:** FeedbackPanel accepts optional `onFrameSelect?: (timestamp_ms: number) => void`. When item has **both** frameIndex and type (MicroFeedbackItem), resolve timestamp from frames[frameIndex].**timestamp_ms** only if frames exists and frameIndex is valid. **Guard:** Never call onFrameSelect when it's undefined. Never access frames[frameIndex] when frames is undefined or frameIndex is invalid. **Explicit rule:** Clickable only when `hasFrameIndex && hasValidType` — type must be "angle" or "thermal".

**Context:** Replay will pass `frames`, `items`, `onFrameSelect`. WelderReport passes `items` only (no frames, no onFrameSelect); items have no frameIndex, no type.

**Implementation sketch:**

```typescript
interface FeedbackPanelProps {
  items: (FeedbackItem | MicroFeedbackItem)[];
  frames?: Frame[];
  onFrameSelect?: (timestamp_ms: number) => void;
}

const VALID_MICRO_TYPES = ["angle", "thermal"] as const;

// For each item:
const hasFrameIndex = "frameIndex" in item && typeof item.frameIndex === "number" && Number.isInteger(item.frameIndex) && item.frameIndex >= 0;
const hasValidType = "type" in item && item.type != null && VALID_MICRO_TYPES.includes(item.type as typeof VALID_MICRO_TYPES[number]);
const isMicroItem = hasFrameIndex && hasValidType;
const isValidFrameIndex = isMicroItem && frames && Array.isArray(frames) && item.frameIndex! < frames.length;
const timestamp_ms = isValidFrameIndex ? frames![item.frameIndex!]?.timestamp_ms : null;
const isClickable = isMicroItem && isValidFrameIndex && timestamp_ms != null && typeof onFrameSelect === "function";

// onClick handler:
const handleClick = () => {
  if (isClickable && onFrameSelect && timestamp_ms != null) {
    onFrameSelect(timestamp_ms);
  }
};
// If !isClickable: render as div (non-interactive). Never call onFrameSelect otherwise.
```

**Subtasks:**
- [ ] Add frames?: Frame[] and onFrameSelect?: (timestamp_ms: number) => void
- [ ] Validate frameIndex before use
- [ ] **Validate type:** Only treat as clickable when type is "angle" or "thermal"
- [ ] **Guard onFrameSelect:** Only call when typeof onFrameSelect === 'function'
- [ ] When not clickable: render non-interactive div
- [ ] Add aria-label for clickable items
- [ ] Optional: keyboard support (Enter when focused)

**✓ Verification Test:**
- [ ] Items without frameIndex not clickable
- [ ] Items with frameIndex but no type → not clickable
- [ ] Items with frameIndex and type but no frames → not clickable
- [ ] Items with frameIndex but no onFrameSelect → not clickable
- [ ] Session-level item with frameIndex (invalid) + click → no crash (guard)
- [ ] Full props: click triggers callback with correct timestamp_ms

**Time estimate:** 1 hour

---

### Step 2.3: Fix FeedbackPanel key to include frameIndex and type — *Non-Critical*

**What:** Key format must **always include frameIndex and type when BOTH present** to avoid collisions and React warnings. For session items (no frameIndex or no type), use session key. **Never use fb- format when type is missing** — that would produce `fb-0-undefined`.

**Correct key format:**
```typescript
const key = hasFrameIndex && hasValidType
  ? `fb-${item.frameIndex}-${item.type}`
  : `session-${item.severity}-${i}`;
```

**Subtasks:**
- [ ] Use frameIndex + type for micro items (only when both present and valid)
- [ ] Use session-severity-index for session-only items
- [ ] No duplicate keys; no React key warnings

**Time estimate:** 0.25 hours

---

### Step 2.4: Update FeedbackPanel tests — *Non-Critical*

(Same as original, plus: test that session-level item without frameIndex never triggers onFrameSelect even if accidentally passed; test that item with frameIndex but no type is not clickable)

**Time estimate:** 0.75 hours

---

### Step 2.5: Verify WelderReport still works — *Non-Critical*

(Same as original — explicit test: FeedbackPanel with session-only items, no frames, no onFrameSelect; WelderReport must not pass frames to session-level items; if someone passes frames to session-level items without frameIndex/type, guard ensures no crash)

**Time estimate:** 0.5 hours

---

### Step 2.6: Add aria-live to FeedbackPanel — *Non-Critical*

(Same as original)

**Time estimate:** 0.25 hours

---

### Step 2.7: Add mixed session + micro FeedbackPanel test — *Non-Critical*

(Same as original)

**Time estimate:** 0.5 hours

---

**Phase 2 Total Time:** 4 hours

---

## Phase 3 — Replay Integration

**Goal:** Replay page shows micro-feedback, timeline markers, and click-to-scrub. **useMemo deps correct** — no recompute on every frame tick. **try-catch** around generateMicroFeedback. **Timeline markers** handle single-frame sessions and identical timestamps (no division by zero). **Centralized frame select handler**. **Edge cases:** empty session → "No feedback"; single frame → markers hide gracefully; missing sensor data → no throw. **SSR/hydration:** Replay must be client-only — verify.

**Time Estimate:** 6 hours  
**Risk Level:** 🟡 Medium  
**Delivered value:** Full feature for welders

---

### Step 3.1: Add useMemo generateMicroFeedback to Replay page — *Critical: Performance*

**Why critical:** Must precompute once; not on every render or scrub. **If dependency array is wrong, you recompute on every frame tick, freezing the UI.** Check refs, arrays — sessionData?.frames must be the only dep. **Wrap in try-catch** — real sensor data is messy; if generateMicroFeedback throws (e.g. future bug), page must not crash.

**What:** In ReplayPageInner, add useMemo. **Dependency:** `[sessionData?.frames]` — ensure sessionData.frames is not recreated unnecessarily (e.g. from fetchSession). If fetchSession returns new array ref every time, consider useRef to stabilize. **try-catch inside useMemo** — on error return [].

**Implementation:**

```typescript
const microFeedback = useMemo(() => {
  try {
    const frames = sessionData?.frames ?? [];
    return generateMicroFeedback(frames);
  } catch (err) {
    console.warn("Micro-feedback generation failed, showing empty:", err);
    return [];
  }
}, [sessionData?.frames]);
```

**Subtasks:**
- [ ] Import generateMicroFeedback
- [ ] useMemo with [sessionData?.frames]
- [ ] try-catch; never throw
- [ ] Handle empty frames
- [ ] **Verify:** useMemo does NOT run on currentTimestamp change (Profiler or test)

**Time estimate:** 0.5 hours

---

### Step 3.2: Render FeedbackPanel with micro items on Replay page — *Critical*

**What:** Add FeedbackPanel. Pass items=microFeedback, **frames={sessionData?.frames ?? []}** (guard: always array), onFrameSelect=handleFrameSelect.

**Guard:** Only render FeedbackPanel when sessionData exists. Use `sessionData != null && <FeedbackPanel items={microFeedback} frames={sessionData.frames ?? []} onFrameSelect={handleFrameSelect} />`. **Never pass undefined frames** — use `?? []` so FeedbackPanel always receives an array.

**Subtasks:**
- [ ] FeedbackPanel with items, frames, onFrameSelect
- [ ] frames={sessionData?.frames ?? []}
- [ ] Render only when sessionData exists
- [ ] handleFrameSelect: setIsPlaying(false); setCurrentTimestamp(ts)

**Time estimate:** 1 hour

---

### Step 3.3: Add timeline markers overlay — *Critical*

**What:** Render markers at positions. **Position formula must handle single-frame sessions and identical timestamps** — otherwise division by zero or markers overlap.

**Position calculation:**
```typescript
const duration = lastTimestamp - firstTimestamp;
const pct = duration > 0
  ? ((ts - firstTimestamp) / duration) * 100
  : 0; // single frame or identical timestamps → all at 0, or hide markers
```

**When lastTimestamp <= firstTimestamp or duration === 0:** Either hide markers or render all at 0. Plan: hide markers when duration <= 0 to avoid clutter.

**Clickable:** Must pause playback AND scrub. Both required.

**Subtasks:**
- [ ] Wrap timeline in relative container
- [ ] Position formula with division-by-zero guard
- [ ] Hide markers when single-frame (duration <= 0)
- [ ] onClick → pause + setCurrentTimestamp
- [ ] aria-label per marker
- [ ] Color by severity

**Time estimate:** 1.5 hours

---

### Step 3.4: Implement jump handler — *Non-Critical*

**What:** Centralize: `const handleFrameSelect = (timestamp_ms: number) => { setIsPlaying(false); setCurrentTimestamp(timestamp_ms); };` — pass to FeedbackPanel and markers. **Single handler** — do not scatter logic; avoids double-pause, double-update.

**Time estimate:** 0.25 hours

---

### Step 3.5: Add integration/verification test — *Non-Critical*

(Same as original — mock structure with session_id, operator_id, etc.; makeFrame, makeThermalSnapshot)

**Time estimate:** 1.5 hours

---

### Step 3.6: Performance verification for 10k frames — *Non-Critical*

**What:** 10k frames = real-world stress test. **Don't assume it's fast because it's 100 frames in dev.** Profile it, measure it. If >200ms, fix slow loops, memoize. No excuses.

**Time estimate:** 0.5 hours

---

### Step 3.7: Accessibility — *Non-Critical*

**What:** Keyboard + aria + live updates — non-negotiable. Clickable items: button or role="button"; tabIndex=0; Enter/Space activate. Markers: focusable with aria-label.

**Automated a11y:** Add jest-axe or @axe-core/react. Manual: VoiceOver/NVDA.

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);
it('FeedbackPanel has no accessibility violations', async () => {
  const { container } = render(<FeedbackPanel items={items} frames={frames} onFrameSelect={fn} />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Time estimate:** 0.5 hours

---

### Step 3.8: Final QA and edge-case handling — *Non-Critical*

**Edge cases:**
- [ ] Empty session → no crash; show "No feedback"
- [ ] Single frame → markers hide gracefully
- [ ] Missing sensor data → no throw (guards in lib)
- [ ] firstTimestamp === lastTimestamp → hide markers
- [ ] Loading state: don't render FeedbackPanel with empty items before sessionData loads — avoid "No feedback" flash

**Time estimate:** 0.5 hours

---

### Step 3.9: SSR / Hydration verification — *Non-Critical*

**What:** Replay component must be client-only. It has 'use client' — verify. **If you ignore this, hydration mismatch breaks the page on load.** Add verification step: ensure Replay page and any component calling generateMicroFeedback are never server-rendered. Dynamic imports for 3D are already ssr: false.

**Verification:**
- [ ] Replay page has 'use client' at top
- [ ] generateMicroFeedback is only called inside useMemo in client component
- [ ] No server component imports generateMicroFeedback
- [ ] Run build; load replay page; no hydration warning in console

**Time estimate:** 0.25 hours

---

### Step 3.10: Extract TimelineMarkers component — *Non-Critical*

**What:** Move marker rendering into `components/welding/TimelineMarkers.tsx` — props: items, frames, firstTimestamp, lastTimestamp, onFrameSelect, currentTimestamp (optional for highlight).

**Why:** Reusable; cleaner replay page; testable in isolation.

**Files:** Create `my-app/src/components/welding/TimelineMarkers.tsx`; modify replay page.

**✓ Verification:** Markers render; click works; replay page unchanged visually.

**Time estimate:** 1 hour

---

### Step 3.11: Add "No feedback" empty state — *Non-Critical*

**What:** When microFeedback.length === 0, show message e.g. "No frame-level feedback for this session" instead of empty FeedbackPanel.

**Files:** `my-app/src/app/replay/[sessionId]/page.tsx`

**✓ Verification:** Load session with no deviations; see message.

**Time estimate:** 0.25 hours

---

### Step 3.12: Add data-testid for E2E — *Non-Critical*

**What:** Add data-testid="micro-feedback-item", data-testid="timeline-marker" for E2E tests.

**Files:** FeedbackPanel.tsx, TimelineMarkers (or inline markers).

**✓ Verification:** Can query by testid in tests.

**Time estimate:** 0.25 hours

---

### Step 3.13: Document in CONTEXT.md — *Non-Critical*

**What:** Add WarpSense Micro-Feedback section: what it does, where it runs, thresholds, Phase 1 scope.

**Files:** CONTEXT.md or docs/

**✓ Verification:** New section exists; references plan/issue.

**Time estimate:** 0.5 hours

---

### Step 3.14: Changelog entry — *Non-Critical*

**What:** Add entry: "Added WarpSense Micro-Feedback (Phase 1): frame-level angle drift and thermal symmetry alerts on replay; click-to-scrub; timeline markers."

**Files:** CHANGELOG.md or similar

**✓ Verification:** Entry present.

**Time estimate:** 0.25 hours

---

**Phase 3 Total Time:** 8.5 hours

**Phase 3 Completion Criteria:**
- [ ] All steps 3.1–3.9 completed (core; 3.10–3.14 optional polish)
- [ ] Replay shows micro-feedback and markers
- [ ] Click-to-scrub works
- [ ] Integration/verification test passes
- [ ] Performance acceptable for 10k frames
- [ ] SSR/hydration verified
- [ ] Feature complete

---

## 3. Pre-Flight Checklist

(Same as original)

---

## 4. Risk Heatmap

(Same as original, plus: Optional props crash, Key collisions, SSR hydration, Severity exhaustivity)

---

## 5. Success Criteria

(Same as original)

---

## 6. Progress Tracking

| Phase | Total Steps | Completed | In Progress | Blocked | % Complete |
|-------|-------------|-----------|-------------|---------|------------|
| Phase 1 | 7 | 0 | 0 | 0 | 0% |
| Phase 2 | 7 | 0 | 0 | 0 | 0% |
| Phase 3 | 14 | 0 | 0 | 0 | 0% |
| **TOTAL** | **28** | **0** | **0** | **0** | **0%** |

**Status definitions:**
- 🟩 Completed: Verification test passed
- 🟨 In Progress: Started, not verified
- 🟥 Blocked: Dependency missing
- ⬜ Not Started

---

## 7. Red Team Exercise — Updated

1. **Optional frameIndex/type crash:** Mitigation: MicroFeedbackItem requires both; FeedbackPanel validates both before treating as clickable; type missing → never clickable.
2. **onFrameSelect undefined:** Mitigation: Guard with typeof check before calling.
3. **Key collisions:** Mitigation: frameIndex+type for micro (only when both valid); session-severity-i for session.
4. **Single-frame marker position:** Mitigation: duration <= 0 → hide markers.
5. **SSR hydration:** Mitigation: Replay has 'use client'; generateMicroFeedback only in useMemo.
6. **Missing thermal sensors:** Mitigation: hasAllCardinalReadings — skip frame if any N/S/E/W reading absent; never use DEFAULT_AMBIENT for variance.
7. **Severity exhaustivity:** Mitigation: grep all usages; every branch handles info|warning|critical; explicit fallback with warn for unknown.
8. (Original items 2–10 retained)

---

## 8. Quality Metrics Checklist

(Same as original)

---

## 9. Implementability Test

**Q:** What if onFrameSelect is undefined when user clicks? **A:** Guard in FeedbackPanel: only render as clickable when onFrameSelect is a function; otherwise render non-interactive div. Never call undefined.

**Q:** What if session has 1 frame? **A:** lastTimestamp === firstTimestamp → duration 0 → hide markers; FeedbackPanel shows "No feedback" or items if any. No division by zero.

**Q:** What if item has frameIndex but type is missing? **A:** Treat as session-level; not clickable; use session key format; never access frames[frameIndex].

**Q:** What if thermal frame has only center reading, no north/south/east/west? **A:** hasAllCardinalReadings returns false; skip frame; no thermal feedback for that frame.

---

## 10. Bus Factor Test

(Same as original)

---

## 11. Self-Critique

- **MicroFeedbackItem requires frameIndex and type:** Yes — plan updated; never optional.
- **Robust guards in lib:** Yes — null, NaN, try-catch; **hasAllCardinalReadings for thermal**.
- **FeedbackPanel guards:** Yes — onFrameSelect, frameIndex and type validation; explicit handling when type missing.
- **Key format:** Yes — frameIndex+type when both valid.
- **Styling constants:** Yes — SEVERITY_STYLES with exhaustivity.
- **Edge cases:** Yes — empty, single-frame, missing sensors, missing cardinal readings.
- **SSR:** Yes — verification step added.
- **Performance 10k:** Yes — <200ms; profile.
- **Severity exhaustivity:** Yes — grep mandate; explicit fallback with warn.

---

## 12. After Plan Creation

(Same as original)
