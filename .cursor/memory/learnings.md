# Learnings — CTO Workflow Memory

> **Append-only.** Never overwrite. Max 50 lines — compress duplicates when approaching limit.
> **Written by:** CTO agent at end of each session (suggested) + human (manual)
> **Read by:** cto_pm.md at start of every task generation session
> **Last updated:** 2026-02-17

---

## How to Read This File

Each line is a compressed lesson. Format:
`- [YYYY-MM-DD] context_type: lesson learned`

Context types: `demo` | `scale` | `feature` | `fix` | `general` | `any`

The CTO agent reads this before generating tasks and uses it to bias toward task types and approaches that have worked before for this project and this user.

---

## Learnings

<!-- Append new learnings below this line. Do not edit existing lines. -->

- [2026-02-17] any: tasks with specific file paths or component names in the ./agent command score higher than vague descriptions
- [2026-02-17] any: dual-audience tasks (visible to investors AND useful to operators) consistently score 8.5+
- [2026-02-17] demo: UI polish and visual differentiation tasks score highest in demo context
- [2026-02-17] demo: backend or infrastructure tasks score low in demo context unless they directly unblock a visible demo feature
- [2026-02-17] general: tasks under 2 hours (quick wins) are more likely to be accepted when included as task 3 of 3

---

## Append Instructions for CTO Agent

At the end of each task generation session, if a clear pattern emerged, append one line here.

Only append if:
- A task scored 9.0+ AND was accepted by the user
- A task type was rejected multiple times (suggest a new rule)
- A principle application was unusually clear and repeatable
- The user gave explicit feedback that reveals a preference pattern

Do NOT append:
- One-off context-specific observations
- Anything already covered by an existing line
- Lines that duplicate rejection memory (that lives in user-feedback.jsonl)

To append, the CTO agent should output the suggested line at the bottom of its task list output under "LEARNING UPDATE." A human or post-processing step copies it here.
