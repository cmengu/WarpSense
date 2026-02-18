# Design Principles — Shipyard Welding Platform

> **Purpose:** Resolve ambiguity when vision.md doesn't give a clear answer
> **Use:** Ordered tiebreakers — Principle 1 beats Principle 2, and so on
> **Last updated:** 2026-02-17

---

## How to Use This Document

When vision.md is clear, follow it. When two valid approaches exist and neither violates non-goals, apply these principles as ordered tiebreakers.

**Before reaching for these principles**, run the decision through the 5-filter tree in `cto_pm.md`:
1. Does a real human (investor, pilot, operator) see this directly?
2. Can it be demonstrated within 48 hours?
3. Is it reversible?
4. Is it 10x or 1x work?
5. Is it past the embarrassment line?

If the 5-filter tree gives a clear answer, use it. These principles handle the cases the filter tree doesn't resolve — usually implementation-level decisions where both paths pass all 5 filters.

---

## Principle 1: Ship the External Thing Before the Internal Thing

**What it means:**
Any work a real human can see, click, or forward takes priority over any work that only improves the internal system. This is not about phases or stakeholder tiers — it applies always, at every stage.

**Why this is Principle 1:**
We do not have paying users yet. Every hour spent on internal improvement is an hour not spent closing the gap between now and the first real customer. Internal work earns its place only after the external-facing gap is closed.

**Examples:**
- ✅ Wire the trend graph to real session history → investor stops seeing a mockup
- ✅ Make the PDF report actually generate → pilot customer can forward it to their manager
- ✅ Deploy a live URL with a guest account → demo can happen asynchronously
- ❌ Refactor the session comparison component → no human sees this
- ❌ Update .cursor/context/project-context.md → no human sees this
- ❌ Add pagination to the session list API → investors don't browse sessions

**Test:** Will a specific human notice this in the next 48 hours?
If no: defer until the yes-answers are done.

---

## Principle 2: A Working Slice Beats a Complete Layer

**What it means:**
Ship one complete feature end-to-end — from sensor data to visible output — before building horizontal infrastructure. A rough vertical slice in front of a real human beats three polished layers no one has seen.

**Examples:**
- ✅ One working expert vs novice comparison, hardcoded if needed → investor sees the story
- ❌ Generic comparison framework supporting all weld types → no one asked for this yet
- ✅ Email report that works for one session type → pilot customer gets something real
- ❌ Configurable report template engine → over-engineered for one customer

**Test:** Does this produce a demo-able artifact — something a human can see, hold, or click?
If no: scope down until it does.

---

## Principle 3: Correct > Fast

**What it means:**
Never sacrifice data integrity for speed. A calculation that takes 500ms but is provably correct beats a 50ms calculation that silently drops edge cases. "Correct" does not mean perfect — 95% accuracy with documented edge cases is fine.

**Examples:**
- ✅ Reject frame batches with timestamp gaps → prevents corrupt sessions
- ❌ Silently skip bad frames to avoid slowing ingestion → silent data loss
- ✅ Calculate heat dissipation at ingestion with defensive null checks → correct, slow
- ❌ Calculate on-demand in frontend without null guards → fast until it crashes

**Test:** Could this silently produce wrong results? If yes, slow it down and add validation.

---

## Principle 4: Explicit > Implicit

**What it means:**
Prefer code that states its intent directly. No magic conventions, no implicit defaults, no behavior that requires reading the whole codebase to understand.

**Examples:**
- ✅ `timestamp_ms`, `temp_celsius`, `distance_mm` → units explicit in field names
- ❌ `time`, `temp`, `distance` → units guessed
- ✅ Return `null` when sensor data is missing
- ❌ Return `0` or an average when data is missing → implicit fabrication
- ✅ Snake_case everywhere (backend + frontend) → no conversion layer

**Test:** If a new contributor asks "how do I know what this means?" and you have to explain context — it's implicit.

---

## Principle 5: Fail Loudly > Fail Silently

**What it means:**
When something goes wrong, make it obvious immediately. Throw descriptive errors. Log failures. Never swallow exceptions or return success after a partial failure.

**Examples:**
- ✅ `ValidationError` with the specific field and constraint
- ❌ `except Exception: pass` that logs nothing
- ✅ API returns `{ "status": "failed", "failed_frames": [...], "error": "..." }`
- ❌ API returns `{ "status": "success" }` after partial failure
- ✅ Frontend shows "No thermal data for this session" when frames are empty
- ❌ Frontend renders a blank heatmap with no message

**Test:** Could this error go unnoticed for days? If yes, you're failing silently.

---

## Principle 6: Simple > Clever

**What it means:**
Boring, well-understood solutions over cutting-edge ones. 10 lines of procedural code over 50 lines of elegant abstractions. You have to explain "how" more than "what" — it's too clever.

**Examples:**
- ✅ PostgreSQL with JSONB → boring, works, understood by everyone
- ❌ TimescaleDB or Cassandra → clever, adds operational overhead before you need it
- ✅ `setInterval` for 100 Hz playback → simple, correct
- ❌ `requestAnimationFrame` with frame-skipping logic → clever, harder to debug
- ✅ Manual timestamp alignment for session comparison → 50 lines, easy to test
- ❌ Vector embeddings for session similarity → 500 lines, opaque

**Test:** If you have to explain how before what — it's probably clever.

---

## Principle 7: Documented Decisions > Undocumented Flexibility

**What it means:**
Rigid, documented constraints beat flexible, undocumented ones. If a rule exists, enforce it strictly and document why. Update the documentation when the rule changes. Never add silent exceptions.

**Examples:**
- ✅ Enforce 1000-5000 frames per POST → documented, rejects out-of-range
- ❌ "Usually 1000-5000, but accept 1-10000 to be flexible" → undocumented, causes bugs
- ✅ Sensor continuity checks with a `disable_sensor_continuity_checks` flag → documented escape hatch
- ❌ Silently skip continuity checks when "it seems like test data" → undocumented heuristic

**Test:** If someone asks "why does this limit exist?" and there's no doc explaining it — it's undocumented flexibility.

---

## Principle 8: Optimize for Maintainability > Initial Speed

**What it means:**
Code is read 10x more often than written. If proper takes 2 days and a hack takes 1, choose proper — unless the hack is explicitly time-boxed and documented as such. "Proper" does not mean over-engineered (see Principle 6).

**Examples:**
- ✅ `extractCenterTemperature(frame)` with null guards → reused in 5 places, maintained once
- ❌ Inline `frame.thermal_snapshots[0]?.readings.find(...)` everywhere → breaks when format changes
- ✅ Validation test for every Pydantic model → catches regressions before they reach the demo

**Test:** Will this be changed or debugged within 6 months? If yes, optimize for maintainability.

---

## Principle 9: Progressive Disclosure > Upfront Perfection

**What it means:**
Build the minimum thing that works today. Document known limitations. Extend when requirements are clear and users have confirmed the value. Never anticipate requirements that haven't been reported.

**Examples:**
- ✅ Scoring rules hardcoded in `rule_based.py` → works now, easy to change
- ❌ Scoring rule engine with YAML DSL → over-engineered before anyone asked for flexibility
- ✅ Support only `"center"` thermal direction in heatmap → simplify now, extend later
- ❌ Support all 5 directions with configurable filtering → premature generalization

**Test:** Are you solving a problem that hasn't been reported yet? If yes, you're building upfront perfection.

---

## Decision Framework (When Two Options Both Pass the 5-Filter Tree)

1. Does one violate non-goals? → Reject it.
2. Does one ship the external thing before the internal thing? → Choose it. (Principle 1)
3. Does one produce a demo-able artifact sooner? → Choose it. (Principle 2)
4. Is one more correct or robust? → Choose it. (Principle 3)
5. Is one more explicit? → Choose it. (Principle 4)
6. Does one fail loudly? → Choose it. (Principle 5)
7. Is one simpler? → Choose it. (Principle 6)
8. Is one better documented? → Choose it. (Principle 7)
9. Is one more maintainable? → Choose it. (Principle 8)
10. Does one defer complexity? → Choose it. (Principle 9)
11. Still tied? → Escalate to a human.

---

## What These Principles Are Not

- ❌ "Never refactor" — pay technical debt when it blocks shipping
- ❌ "Never optimize" — slow features hurt operators; just don't optimize prematurely
- ❌ "Never use new tech" — use it when it directly solves a real problem
- ❌ "Never generalize" — generalize when you have 3+ concrete use cases, not before
- ❌ "Internal work is never valid" — it becomes valid after the external gaps are closed

---

## Revision Policy

Principles change rarely. If one needs updating:
1. Human approval required
2. Document the change in `/decisions/YYYY-MM-DD-principles-update.md`
3. Do not modify principles mid-task to justify a decision already made