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

# Strategic Addendum — Vertical AI Integration
> **Filed:** 2026-02-18
> **Amends:** Product Vision — Shipyard Welding Platform
> **Status:** ACTIVE — extends the IMMUTABLE vision doc without modifying it
> **Decision log:** /decisions/2026-02-18-vertical-ai-positioning.md

---

## What This Adds

The core vision document defines *what* we build and *for whom*. This addendum adds three strategic layers that define *why we become defensible* as the market matures:

1. The Data Moat — why our sensor data is a strategic asset, not just a technical constraint
2. Labor Replacement Framing — what job we are actually eliminating
3. Model-Agnostic Architecture — how we stay ahead of model commoditization

These are not product decisions. They are strategic positioning decisions that should inform every product decision.

---

## Layer 1: The Data Moat

### What We're Accumulating

Every session we ingest — 100 Hz, six channels, up to 30,000 frames — is a labeled record of what a welder of a specific skill level did at a specific moment, and what happened as a result. This is not commodity data. No model provider has it. No competitor who starts later will have our session history.

The sensor schema is deliberately narrow right now (`amps`, `volts`, `angle_degrees`, `thermal_snapshots`). That narrowness is an advantage: it means every session we collect is structurally identical, and a corpus of 10,000 sessions is directly usable for fine-tuning.

### The Compounding Asset

| Stage | Data volume | What it unlocks |
|---|---|---|
| Pre-pilot (<100 sessions) | Sparse | Demo credibility |
| Pilot (100–500 sessions) | Meaningful | Real pattern detection, real alerts |
| Post-pilot (500–5,000 sessions) | Dense | Fine-tune a domain-specific model that outperforms generic LLMs on weld quality prediction |
| Scale (5,000+ sessions) | Moat | No latecomer can replicate this without years of deployment |

**The implication for build order:** Features that generate sessions (onboarding, replay, alerts) are more strategically valuable than features that analyze sessions we already have. Every pilot station we add is compounding the asset. Every week we delay a pilot deployment is a week of session data we never get back.

### What This Changes in Practice

The PDF report, the real-time alert, the comparison view — these are not just investor demo features. They are the reason operators keep the hardware connected and generating sessions. Session volume is the real metric underneath all others. Design every operator-facing feature with the question: *does this make operators more likely to run another session?*

---

## Layer 2: Labor Replacement, Not SaaS

### The Headache We're Eliminating

The current vision says "real-time welding process control." That is accurate but undersells it. More precisely, we are replacing three specific jobs that shipyards currently perform with expensive human labor:

**1. The Floor QC Inspector**
Walks the floor during welding. Spots technique deviations by eye. Catches maybe 30% of problems because they cannot watch every station. Their replacement is our real-time alert system — always watching, never tired, zero walk time.

**2. The Senior Welder as Teacher**
After a session, a senior welder reviews a novice's work and explains what went wrong. This requires scheduling, availability, and the senior welder's willingness to articulate tacit knowledge. Their replacement is our expert vs. novice comparison — the diff is always available, always consistent, always on demand.

**3. The Shift Manager Writing Reports**
After every shift, someone compiles session notes, defect tallies, and operator performance into a report for the yard superintendent. Their replacement is our PDF session report — generated automatically, factual, forwardable.

### Why This Framing Matters to Investors

"SaaS for welding" prices at $X/seat/month. "Labor replacement" prices at a fraction of the salary line it eliminates. A QC inspector in a US shipyard costs $65,000–$90,000/year fully loaded. Our entire annual contract can be $40,000 and still represent a 50%+ cost reduction — which also means our pricing floor is much higher than a SaaS comp set would suggest.

**In investor conversations:** Lead with the labor line, not the feature list. "We eliminate the need for a dedicated QC inspector at each welding station" is a $65k/year savings statement. "Real-time angle alerts" is a feature. One of these justifies a contract; the other justifies a trial.

### Why This Framing Matters to Operators

Operators do not want software. They want to not get called into the superintendent's office because a weld failed inspection. The product earns its place on the floor if and only if it catches something the operator would have missed, before it becomes a problem. Every alert, every comparison, every replay timestamp should be designed around that single outcome.

---

## Layer 3: Model-Agnostic Architecture

### The Principle

We are not building a product that depends on any specific model's capabilities. We are building a product that uses models as interchangeable infrastructure — the same way we use a database engine or a cloud provider.

**Concretely:**
- No prompt or feature should be designed around capabilities unique to a single model version
- Model selection is a runtime configuration, not a product decision
- When a newer, cheaper model achieves equivalent output quality on our tasks, we switch — and our customers notice nothing except that the product got faster

### Why This Matters Now

Model costs are declining at a rate that makes model selection decisions from today irrelevant in 12 months. Our agent workflow already implements a multi-stage critique loop that uses 3–5× more tokens per task than a naive single-prompt approach. That loop is justified today because quality matters more than marginal token cost. In 12 months, the same loop costs 80% less and the quality advantage is larger. The teams that built quality-first workflows at today's costs will capture compounding returns as costs drop.

**The practical rule:** When evaluating whether to add an AI-powered feature, ask whether the feature would still work acceptably if we swapped the underlying model for one that is 60% cheaper and 20% less capable. If the answer is no, the feature is too tightly coupled to current model performance and needs to be redesigned.

### The Fine-Tuning Horizon

Once we cross 1,000 sessions, we have the data to begin evaluating fine-tuning a smaller domain-specific model on weld quality prediction. A fine-tuned 8B parameter model trained on real shipyard session data will outperform a general-purpose frontier model on our specific tasks — at a fraction of the inference cost. This is not a near-term priority, but it is a near-term horizon. The data collection architecture we build now determines whether this option is available to us later.

---

## Updated Dual-Audience Filter

The original filter asks: "Investor or Operator?" This addendum adds a third axis.

| Feature | Investor | Operator | Data Moat | Decision |
|---|---|---|---|---|
| Session replay + export | ✅ | ✅ | ✅ Generates reuse | Build |
| Real-time alert | ✅ Live demo | ✅ Catches mistakes | ✅ Labels deviations | Build — highest priority |
| Expert vs. novice comparison | ✅ Tells story | ✅ Operators learn | ✅ Labels skill levels | Build |
| PDF session report | ✅ Forwardable | ✅ Manager needs it | ⚪ Doesn't generate sessions | Build — trust-builder |
| Onboarding flow | ✅ Reduces demo friction | ✅ Reduces setup time | ✅ More sessions faster | Build — session volume |
| Closed-loop parameter control | ✅ Future vision | ⚪ Not yet | ⚪ Requires more data | Defer |
| Fine-tune domain model | ❌ Invisible | ❌ Invisible | ✅ Moat-deepening | Defer until 1,000 sessions |
| Backend ingestion optimization | ❌ Invisible | ✅ Prevents lag | ⚪ Neutral | Defer unless blocking pilot |

---

## The Strategic Summary in One Paragraph

We are building vertical AI for an analog-heavy, safety-critical industry where labor costs are high, mistakes are expensive, and data does not exist in usable form anywhere. Every session we ingest is a labeled record of ground-truth welder behavior that no competitor can buy or replicate. The product we ship to investors and operators today is the delivery vehicle for that data collection. As model costs decline, the same workflows we build now run at a fraction of the cost. As our session corpus grows, we gain the option to fine-tune domain-specific models that outperform generic frontier models on our exact use case. The companies that win in vertical AI are the ones that got the data first. Getting the data first means closing the pilot. Closing the pilot means the investor conversation has to work. Which is why the build order in the core vision document is correct — and now you know exactly why it's correct.

---

*This addendum should be read alongside the core vision document. In any conflict, the core vision document governs. In any gap, this addendum governs.*