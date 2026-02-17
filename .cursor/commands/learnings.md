# Learnings — CTO Workflow Memory

> **Purpose:** Compressed, high-signal lessons that bias task generation toward what works.
> **Written by:** CTO agent (auto-appended) + human (manual override)
> **Read by:** `cto_pm.md` at the start of every session — BEFORE generating tasks
> **Last updated:** 2026-02-17

---

## How This File Works

Three tiers. Read all three. Weight them in order.

**TIER 1 — HARD RULES** (always apply, no exceptions)
**TIER 2 — STRONG PATTERNS** (apply unless context explicitly overrides)
**TIER 3 — OBSERVATIONS** (apply when relevant, compress or promote after 3 confirmations)

Schema per entry:
```
- [YYYY-MM-DD] (confirmations: N) LABEL: lesson
```

`confirmations` = number of times this pattern held. Promote to higher tier at 3+. Mark stale with `~~strikethrough~~` when contradicted — never delete.

Context labels: `demo` | `scale` | `feature` | `fix` | `infra` | `fundraise` | `general`

---

## TIER 1 — Hard Rules

> Override nothing. These are load-bearing.

- [2026-02-17] (confirmations: —) general: deploy before features. A live URL is worth more than any feature built on a localhost demo. Never generate infra/deploy tasks below rank 3 when deploy is not yet live.
- [2026-02-17] (confirmations: —) general: never generate a refactor task when there are zero real users. Refactors serve users, not codebases.
- [2026-02-17] (confirmations: —) demo: never generate a backend-only task in a demo-prep context unless it directly produces something visible in the browser within the same session.

---

## TIER 2 — Strong Patterns

> Apply by default. Override only with explicit context.

- [2026-02-17] (confirmations: 2) general: tasks with specific file paths or component names in the task description score higher acceptance than vague descriptions — always include the target file.
- [2026-02-17] (confirmations: 2) fundraise: dual-audience tasks (visible to investors AND useful to operators) consistently score 8.5+ — bias toward these in fundraise context.
- [2026-02-17] (confirmations: 2) demo: UI polish and visual differentiation tasks score highest in demo context — lead with these when goal = investor demo.
- [2026-02-17] (confirmations: 1) general: tasks framed as "quick win" (<2hr) are more likely to be accepted as task 3 of 3 — always include one scoped quick win per session.

---

## TIER 3 — Observations

> Single data points. Promote to Tier 2 after 3 confirmations. Compress aggressively.

- [2026-02-17] (confirmations: 1) demo: backend or infra tasks score low in demo context unless they unblock a visible feature — consider deferring or reframing.

---

## What Gets Appended (Rules for CTO Agent)

**Append when:**
- A task scored 9.0+ AND the user accepted it → add to Tier 3, note confirmation
- An existing Tier 3 entry is confirmed again → increment confirmations, promote at 3
- A pattern was contradicted → strikethrough the existing entry, append the contradiction
- The user gave explicit preference feedback that's clearly repeatable

**Never append:**
- One-off context observations with no generalizable signal
- Anything already covered by an existing entry at any tier
- Vague lessons like "user prefers quality" — must be actionable and specific

**Promotion logic:**
- Tier 3 → Tier 2: confirmed 3+ times across different sessions
- Tier 2 → Tier 1: confirmed 5+ times, no contradictions, applies across all contexts

**Staleness:**
- Any entry older than 60 days with 0 new confirmations: mark `[REVIEW]`
- Any entry contradicted once: strikethrough but keep (contradiction is signal)
- Never delete. Deletion hides what you unlearned.

---

## Write Path

The CTO agent outputs a `LEARNING UPDATE` block at the end of each session:

```
LEARNING UPDATE
tier: 3
label: demo
entry: tasks with X produce Y outcome
action: append | confirm [date] | contradict [date]
```

Human reviews and pastes into the correct tier. Takes 10 seconds. If it takes longer, the entry is too vague — reject it.

---

## Compression Protocol

When Tier 3 exceeds 15 entries: merge entries with the same label and pattern into one entry with combined confirmations. Keep the oldest date. Never merge entries from different tiers or different context labels.

When total file exceeds 80 lines: promote eligible entries, strikethrough stale ones, compress Tier 3. Do not touch Tier 1 or Tier 2 during compression.