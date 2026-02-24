# Plan Creation Stage

Based on our full exchange, produce a markdown plan document that an AI agent can execute without ambiguity.

Requirements for the plan:

- Include clear, minimal, concise steps.
- Track the status of each step using these emojis:
  - 🟩 Done
  - 🟨 In Progress
  - 🟥 To Do
- Include dynamic tracking of overall progress percentage (at top).
- Do NOT add extra scope or unnecessary complexity beyond explicitly clarified details.
- Steps should be modular, elegant, minimal, and integrate seamlessly within the existing codebase.

---

## THE AGENT EXECUTION MENTAL MODEL

> This template is designed for **AI agent execution**, not human reading. The critical difference: humans infer context from prior knowledge. Agents hallucinate when forced to infer. Every field below exists to eliminate a specific class of agent error identified through repeated failure analysis.

**The seven failure modes this template prevents:**

| Failure Mode | How It Happens | How This Template Prevents It |
|---|---|---|
| **Assumed structure** | Agent edits a file based on what it expects to exist | Pre-Read Gate confirms actual structure before any edit |
| **Ambiguous anchor** | "Insert after `x = y`" exists in 3 places | Anchor Uniqueness Check requires exactly 1 match in correct scope |
| **Cross-step inference** | "See Step 3 for the implementation" | Self-Contained Rule: all code is written verbatim in the step that uses it |
| **Assumed variable names** | Agent uses `passed_count` when codebase uses `num_passed` | Variable Confirmation grep before any code that references existing names |
| **Irreversible continuation** | Agent runs migration A then immediately writes migration B | Human Gate with exact termination language stops execution at checkpoints |
| **Scope creep on replace** | "Replace the `total =` line" when two exist | Uniqueness-Before-Replace check confirms single target |
| **Invented values** | "Add with placeholder values" — agent invents numbers | No-Placeholder Rule: code blocks never contain `<VALUE>` tokens |

---

## AGENT FAILURE PROTOCOL

> Copy this verbatim into every plan. Do not summarize or shorten it.

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## HUMAN GATE PROTOCOL

> Use this pattern whenever execution must pause for human input. Copy the exact language.

```
Output "[WAITING: describe what you are waiting for]" as the final line of your response.
Do not write any code after this line.
Do not call any tools after this line.
End your response here.
```

Human gates are **mandatory** before:
- Any destructive or irreversible operation (database migrations, schema drops, data overwrites)
- Any operation that requires values produced by a previous step (calibration outputs, generated IDs, revision strings)
- Any file-system change that cannot be undone by a single rollback command

---

## PRE-FLIGHT (Run Before Any Code Changes)

> Every plan must begin with a pre-flight section. The agent reads the codebase and confirms it matches plan assumptions BEFORE touching anything.

```
Read [primary file(s) this plan touches] in full. List:
(1) Every [constant / field / function] currently defined, in order
(2) The exact current signature of [function this plan modifies]
(3) The exact line(s) where [key anchor] appears
(4) Every file that imports from [module being changed]
Do not change anything. Show output and wait.
```

**Required pre-flight checks (adapt per project):**
- All existing tests pass before any edits begin. Document the test count.
- Confirm all functions/classes named in the plan exist and have the expected signatures.
- Confirm all anchor lines (insertion points) exist exactly once in the correct scope.

---

## CRITICAL CODE REVIEW APPROACH

**High-level summary only at top** — architectural decisions, not code snippets.

**Code review lives IN each step** — for steps that touch critical infrastructure:
- API integrations (new endpoints, auth changes)
- State management (context, global state, data flow)
- Database operations (schema, migrations, queries)
- Security-sensitive code (validation, encryption, auth)
- New architectural patterns
- Breaking changes to existing code

For each critical step, include all fields in the Code Review Block below.

For non-critical steps: include Verification Test only.

---

## CODE REVIEW BLOCK (for critical steps)

```
**Context:** [How this fits into the larger system. What breaks if this step is wrong.]

**Pre-Read Gate:** Before editing, confirm:
- [ ] `grep -n '[target function/class]' [file]` returns exactly 1 match
- [ ] The insertion anchor `[exact anchor string]` exists exactly once inside `[function/class scope]`
      grep must confirm: 1 match, correct scope. If 0 or 2+ matches → STOP and report.
- [ ] Variable names referenced in the new code (`[var1]`, `[var2]`) already exist in scope
      grep must confirm each. If any are missing → STOP and report.

**Anchor Uniqueness Check:** (for insert/replace operations)
- Target line: `[exact string]`
- Must appear exactly 1 time in `[file]`, inside `[function/class]`
- If outside correct scope: STOP regardless of match count

**Uniqueness-Before-Replace:** (for replacement operations)
- Before replacing `[variable] =`: confirm grep returns exactly the line(s) you intend
- If multiple matches: identify correct line by function/class scope, not by content alone

**Self-Contained Rule:** Every code block below is complete and runnable as written.
No references to other steps. If code from another step is needed here, it is copied in full.

**No-Placeholder Rule:** No `<VALUE>`, `<INSERT_HERE>`, or `[REPLACE_ME]` tokens appear in
any code block. If a value is not yet known, a Human Gate must precede this step.

---

[code block — verbatim, complete, immediately runnable]

---

**What it does:** [brief explanation]

**Why this approach:** [rationale and trade-offs]

**Assumptions:**
- [assumption 1 — what must be true in the codebase for this to work]
- [assumption 2]

**Risks:**
- [risk 1] → mitigation: [specific mitigation]
- [risk 2] → mitigation: [specific mitigation]

**Human Gate:** (if applicable)
Output `"[GATE MESSAGE]"` as the final line of your response.
Do not write any code or call any tools after this line.
```

---

## VERIFICATION TEST GUIDELINES

Every step — critical or not — ends with a verification test. Tests must be:

- **Executable** without modification (no `[REPLACE_WITH_ACTUAL]` tokens)
- **Scoped** — tests one thing and fails with a clear message if wrong
- **Non-destructive** — running the test does not change state
- **Self-diagnosing** — failure message tells you what to check, not just that it failed

**Test anatomy:**

```
Action:    [Exact thing to do — command, request, user interaction]
Expected:  [Exact output, status code, UI state, or value]
Observe:   [Where to look — log, response body, UI element, DB query]
Pass:      [Specific observable that confirms success]
Fail:      [Symptom] → [Likely cause] → [Specific file/function to check]
```

**For replacement/insertion tests:** include an assertion that the OLD content no longer exists, not just that the NEW content does.

---

## SPLIT OPERATIONS (for risky multi-part changes)

> Any operation with two phases where Phase 1 succeeding but Phase 2 failing produces a silent broken state must be split into two separate steps with a human gate between them.

**Common examples:**
- Schema migration (add columns) + Data migration (populate columns) → split into Migration A and Migration B
- File creation + reference update → confirm file exists before adding reference
- Dependency install + code that uses dependency → confirm install before writing code

**Pattern:**
```
Step N — Phase A (safe, reversible)
  → Verification confirms Phase A succeeded
  → Human Gate: output "[PHASE A COMPLETE — WAITING FOR HUMAN TO CONFIRM PHASE B VALUES]"

Step N — Phase B (data-dependent, uses values from calibration/previous output)
  → Agent substitutes ACTUAL values provided by human. Never invents values.
  → Verification confirms Phase B result is non-null/non-empty
```

---

## STEPS ANALYSIS (fill this in before writing the plan)

> For each step, classify it before writing it. This prevents under-specifying critical steps and over-specifying simple ones.

```
Step 1 ([name]) — [Critical / Non-critical] ([reason]) — [full code review / verification only]
Step 2 ([name]) — [Critical / Non-critical] ([reason]) — [full code review / verification only]
...
```

**A step is Critical if it:**
- Modifies a function used by more than one consumer
- Changes a database schema or data
- Adds or changes an API contract
- Inserts code that other steps depend on
- Is irreversible without a rollback procedure

---

---

# Feature Implementation Plan

**Overall Progress:** `0%`

## TLDR
[One paragraph: what is being built, why it matters, what the system looks like after this plan executes.]

---

## Critical Decisions

Key architectural choices (NO CODE — decisions only):
- **Decision 1:** [choice] — [rationale]
- **Decision 2:** [choice] — [rationale]
- **Decision 3:** [choice] — [rationale]

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read [file] in full. List:
(1) Every [constant / method / field] defined at [module/class] level, in order
(2) Exact current signature of [function this plan modifies]
(3) Exact line where [key anchor] appears
(4) Every file that imports from [module]
Do not change anything. Show output and wait.
```

**Automated checks (all must pass before Step 1):**

- [ ] Existing test suite passes. Document test count: `____`
- [ ] `[function_name]` exists and accepts `[expected signature]`
- [ ] `[anchor_line]` appears exactly once in `[file]` inside `[scope]`
- [ ] `[variable_name]` does not exist yet (for new additions) OR does exist (for modifications)

---

## Tasks

### Phase 1 — [Phase Name]

**Goal:** [What is true after this phase that was not true before]

---

- [ ] 🟥 **Step 1: [Name]** — *[Critical / Non-critical]: [one-line reason]*

  **Context:** [How this fits into the system. What is currently wrong and why this fixes it.]

  **Pre-Read Gate:**
  Before any edit:
  - Run `grep -n '[anchor_string]' [file]`. Must return exactly 1 match inside `[function/class]`. If 0 or 2+ → STOP.
  - Run `grep -n '[variable_to_reference]' [file]`. Must exist in correct scope. If missing → STOP.
  - Run `grep -n '[line_to_replace]' [file]`. Must return exactly the line(s) to be replaced, no others. If multiple → confirm by line number before proceeding.

  **Self-Contained Rule:** All code below is complete and runnable. No "see Step N" references.

  **No-Placeholder Rule:** No `<VALUE>` tokens. If a value is unknown, a Human Gate precedes this step.

  ```[language]
  # Complete, verbatim, immediately runnable code block
  # Nothing omitted. No pseudo-code.
  ```

  **What it does:** [1–2 sentences]

  **Why this approach:** [Rationale. What alternatives were rejected and why.]

  **Assumptions:**
  - [What must already be true in the codebase]
  - [What the existing function signature looks like]

  **Risks:**
  - [Risk 1] → mitigation: [specific action]
  - [Risk 2] → mitigation: [specific action]

  **Subtasks:**
  - [ ] 🟥 [Subtask 1 — specific enough that done/not-done is unambiguous]
  - [ ] 🟥 [Subtask 2]

  **✓ Verification Test:**

  **Action:** [Exact command or interaction — no placeholders]

  **Expected:**
  - [Specific output, value, or state]
  - [Old content no longer present — for replacements]

  **Observe:** [Where to look — log line, response field, UI element, DB value]

  **Pass:** [The single observable that confirms this step is done]

  **Fail:**
  - If [symptom A] → [likely cause] → check [specific file/function]
  - If [symptom B] → [likely cause] → check [specific file/function]

---

- [ ] 🟥 **Step 2: [Name]** — *[Critical]: [reason]*

  > ⚠️ **Split Operation** — This step has two phases. Phase A must complete and verify before Phase B begins. A Human Gate separates them.

  **Context:** [Why splitting is necessary. What silent failure would occur if combined.]

  ---

  **Phase A — [Schema / Structure / Safe change]**

  **Pre-Read Gate:**
  - Run `[command]`. Show output. STOP. Do not proceed until human confirms `[specific value]`.

  ```[language]
  # Phase A code only — no data changes
  ```

  **Phase A Verification:**
  - [Specific check that Phase A succeeded and only Phase A]
  - [Confirm new structure exists]
  - [Confirm no data was changed]

  **Human Gate — Phase A complete:**
  Output `"[PHASE A COMPLETE — WAITING FOR [specific input needed for Phase B]]"` as the final line of your response.
  Do not write any code or call any tools after this line.

  ---

  **Phase B — [Data / Population / Dependent change]**

  > Only execute after human provides: [exact list of values/confirmations needed]

  **Agent instruction:** Substitute the values provided by the human. Do not invent values. If human has not confirmed, output `"WAITING FOR HUMAN CONFIRMATION"` and stop.

  ```[language]
  # Phase B code — uses actual values from human confirmation, not placeholders
  ```

  **Phase B Verification:**
  - [Check that data was actually written — not just that the command ran]
  - [Confirm non-null / non-empty / expected count]
  - [Confirm zero rows updated = visible failure, not silent success]

  **Subtasks:**
  - [ ] 🟥 Phase A complete and verified
  - [ ] 🟥 Human gate passed — values received
  - [ ] 🟥 Phase B complete and verified

  **✓ Verification Test (Phase B):**

  **Action:** [Query or check that confirms data exists with expected values]

  **Expected:** [Non-null values in specific fields]

  **Observe:** [Database query result / API response / log output]

  **Pass:** [All three fields non-null, values match Step 8 calibration output]

  **Fail:**
  - If zero rows updated → `WHERE` clause matched nothing — confirm `[field] = '[value]'` exists in table
  - If fields are null → Phase B ran but UPDATE failed silently — check transaction log

---

- [ ] 🟥 **Step 3: [Name]** — *Non-critical*

  **Subtasks:**
  - [ ] 🟥 [Subtask 1]
  - [ ] 🟥 [Subtask 2]

  **✓ Verification Test:**

  **Action:** [Exact interaction]

  **Expected:** [Observable outcome]

  **Observe:** [Where to look]

  **Pass:** [Specific success indicator]

  **Fail:**
  - If [symptom] → [cause] → check [file/component]

---

### Phase 2 — [Phase Name]

**Goal:** [What is true after this phase]

> [Same step structure as Phase 1]

---

## Regression Guard

> Every plan that touches shared infrastructure must end with a regression check confirming that previously-working behavior still works.

**Systems at risk from this plan:**
- [System 1] — [why it could be affected]
- [System 2] — [why it could be affected]

**Regression verification:**

| System | Pre-change behavior | Post-change verification |
|--------|---------------------|--------------------------|
| [System 1] | [What it did before] | [Exact check that confirms it still does] |
| [System 2] | [What it did before] | [Exact check that confirms it still does] |

---

## Rollback Procedure

> Must be documented and tested before any irreversible step executes.

```bash
# Step-by-step rollback in reverse order
# [Step N rollback]
# [Step N-1 rollback]
# Confirm system is back to pre-plan state: [specific check]
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| **Phase 1** | [Dependency] installed/available | [Import or version check] | ⬜ |
| | [Service] running | [Health check or import] | ⬜ |
| | [Anchor line] exists once in correct scope | grep returns exactly 1 match | ⬜ |
| | Existing tests pass | Test count matches pre-flight baseline | ⬜ |
| **Phase 2** | [Phase 1 complete] | All Phase 1 verifications passed | ⬜ |
| | [Human gate value] received | Human confirmed [specific value] | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection |
|------|-----------|---------------------|-----------------|
| Step 1 | 🟢 **Low** | [Risk] | [How you'd know early] |
| Step 2 Phase A | 🟡 **Medium** | [Risk] | [How you'd know early] |
| Step 2 Phase B | 🔴 **High** | Silent failure if Phase A verified but Phase B skipped | Check non-null fields immediately after Migration B |
| Step N | 🔴 **High** | [Risk] | [How you'd know early] |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| [Feature 1] | [Specific measurable behavior] | **Do:** [action] → **Expect:** [output] → **Look:** [location] |
| [Feature 2] | [Specific measurable behavior] | **Do:** [action] → **Expect:** [output] → **Look:** [location] |
| [Regression: Feature X] | Unchanged from pre-plan | **Do:** [existing test] → **Expect:** [same result as before] |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not proceed past a Human Gate without explicit human input.**
⚠️ **If blocked, mark 🟨 In Progress and document: (a) what failed, (b) what was tried, (c) why you cannot continue.**