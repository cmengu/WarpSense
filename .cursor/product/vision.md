# Product Vision — Shipyard Welding Platform

> **Last updated:** 2026-02-17
> **Stability:** IMMUTABLE — changes require explicit documentation in `/decisions/`

---

## Why This Product Exists

Modern shipyards need **real-time welding process control** at scale. Current systems are manual (operators guess) or retrospective (analysis after the fact). This creates defects discovered too late, training bottlenecks, and repeated mistakes across entire shifts.

This platform provides:
1. **Real-time feedback** — live alerts when torch angle, heat, or electrical parameters drift out of spec
2. **Post-session analysis** — immutable replay with thermal heatmaps, torch angle graphs, session comparison
3. **Closed-loop control** (future) — automated parameter adjustment
4. **Fleet scale** (future) — thousands of concurrent stations across shipyards

---

## The Honest Stage We're At

We do not have paying operators yet. We are closing investors and pilots.

This matters because it determines the right build order:

**Investors unlock the runway that lets us serve operators.**
**Operators validate the product that gives investors confidence.**

These are sequential dependencies, not parallel ones. Right now, the investor conversation has to happen first — not because investors matter more, but because without that conversation, there's no product left to build.

**The right framing is not 50/50. It is:**
> Build things operators would genuinely use. Optimize the *presentation* of those things for investors.

If a feature would help an operator but looks like nothing to an investor, defer the presentation layer, not the feature. If a feature would impress an investor but no operator would ever use it, cut it — it's a demo prop, not a product.

---

## Who We're Building For

### Right Now — Investors & Pilot Customers
The people whose yes unlocks the next stage.

**What they need to see:**
- A live product, not a mockup — real data, real outputs, real URLs
- The story told visually — expert vs novice comparison that makes the value self-evident
- Technical credibility — system handles 3000-frame sessions without lag or placeholder text
- Something they can forward — a PDF report, a link, a screenshot that travels on its own

**The test:** Can they send something to someone else after the meeting?
If yes: the demo worked.
If no: we shipped a local prototype, not a product.

### Next — Welding Operators (Novice to Expert)
The people who validate that the product actually works in the real world.

**What they need:**
- Alerts that catch real technique deviations before they become defects
- Replay that loads in <2 seconds and is navigable without training
- Comparison that makes expert technique legible, not just visualized
- Feedback that is actionable ("angle too steep at timestamp 00:47") not abstract ("quality: 72%")

**The test:** Do they ask for access again, without being told to?
If yes: the product worked.
If no: we shipped a dashboard, not a tool.

---

## The Build Order Rule

When two features compete for the same time slot, use this order:

1. **Does one close a gap that's blocking the investor/pilot conversation?** Ship that first.
2. **Does one produce something a real human can hold or send?** Ship that next.
3. **Does one make an operator's job materially better?** Ship that after.
4. **Does one improve something internally?** Defer until the above are done.

This is not a permanent hierarchy. It reflects where we are. Update it in `/decisions/` when the stage changes.

---

## Dual-Audience Filter (Apply to Every Feature)

Before building, answer both:
- Would an **investor** notice this in a demo? (Visible, credible, story-advancing)
- Would an **operator** use this on shift? (Actionable, fast, reduces rework)

| Feature | Investor | Operator | Decision |
|---|---|---|---|
| 3D torch viz with smooth animation | ✅ Visual wow | ✅ Reads angle intuitively | Build |
| Real-time angle alert | ✅ Live demo moment | ✅ Catches mistakes live | Build |
| Expert vs novice comparison | ✅ Tells the story | ✅ Operators learn from it | Build |
| PDF/email session report | ✅ Something to forward | ✅ Manager wants the data | Build |
| Real historical trend data | ✅ Stops feeling like mockup | ✅ Operators trust it more | Build |
| Backend ingestion optimization | ❌ Invisible | ✅ Prevents lag at scale | Defer unless blocking demo |
| 5 export formats | ❌ Nobody asks | ❌ Operators rarely export | Cut |
| Context file updates | ❌ Invisible | ❌ Invisible | Hygiene — never first |

---

## Core Values (Non-Negotiable, Always)

These apply regardless of stage, audience, or deadline:

1. **Raw data is append-only** — sensor readings are never edited after ingestion
2. **Exact replay** — visualization shows what happened, never interpolated or synthesized
3. **Single source of truth** — backend calculates derived metrics once; frontend consumes, never recomputes
4. **Type safety** — units in field names (`timestamp_ms`, `temp_celsius`); explicit null handling
5. **Fail loudly** — bad data rejected at ingestion with clear error messages, never silently swallowed

Violating any of these makes the product untrustworthy. An untrustworthy product cannot close a pilot.

---

## Current Technical Boundaries

Hardware and architecture constraints — not product decisions. Will expand with funding.

- **Sensor set:** `amps`, `volts`, `angle_degrees`, `thermal_snapshots`
- **Frame rate:** 100 Hz (10ms intervals)
- **Thermal sampling:** 5 Hz, 5 readings per snapshot (center + 4 cardinal)
- **Session length:** ≤ 5 minutes / 30,000 frames
- **Session start/stop:** Manual trigger
- **Scale:** <50 sessions/day, single PostgreSQL instance

---

## What This Is Not

**Never (any stage):**
- Consumer or hobbyist welding
- Underwater or aerospace welding
- Metal fabrication beyond welding

**Not yet (after pilot validation):**
- Closed-loop automated control
- Fleet-wide multi-shipyard dashboard
- ERP/MES integration
- Cross-type weld comparisons
- Multi-sensor fusion beyond current set

---

## Success Right Now

**Investor says:** "Can you send me the link? I want to show my partner."
**Pilot customer says:** "When can we run this on the floor?"
**Operator says:** "I caught something I would have missed."

All three in the same week = we're on track.
Zero of three = we're building for ourselves.

---

## For AI Agents Reading This

The current primary goal is closing investors and pilot customers.
Every feature decision should pass this test first: **does this move that conversation forward?**

If a proposed feature doesn't clearly pass the dual-audience filter AND the build order rule above, flag it for human review before proceeding. Do not build internal improvements when external-facing gaps exist.