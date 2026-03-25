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

**The nine failure modes this template prevents:**

| Failure Mode | How It Happens | How This Template Prevents It |
|---|---|---|
| **Assumed structure** | Agent edits a file based on what it expects to exist | Pre-Read Gate confirms actual structure before any edit |
| **Ambiguous anchor** | "Insert after `x = y`" exists in 3 places | Anchor Uniqueness Check requires exactly 1 match in correct scope |
| **Cross-step inference** | "See Step 3 for the implementation" | Self-Contained Rule: all code is written verbatim in the step that uses it |
| **Assumed variable names** | Agent uses `passed_count` when codebase uses `num_passed` | Variable Confirmation grep before any code that references existing names |
| **Irreversible continuation** | Agent runs migration A then immediately writes migration B | Human Gate with exact termination language stops execution at checkpoints |
| **Scope creep on replace** | "Replace the `total =` line" when two exist | Uniqueness-Before-Replace check confirms single target |
| **Invented values** | "Add with placeholder values" — agent invents numbers | No-Placeholder Rule: code blocks never contain `<VALUE>` tokens |
| **Non-idempotent re-runs** | Step partially fails, agent reruns it, breaks state | Idempotency declaration on every step |
| **Lost state on stop** | Agent stops mid-step, no record of what it changed | State Preservation Protocol: agent dumps modified file state before stopping |

---

## AGENT FAILURE PROTOCOL

> Copy this verbatim into every plan. Do not summarize or shorten it.

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping:
   - Output the full current contents of every file modified in this step.
   - Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) exact state of each modified file, (e) why you cannot proceed.
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

## CLARIFICATION GATE — Fill Before Writing Any Steps

> Surface every unknown upfront. Most plan iteration cycles are caused by unknowns discovered reactively mid-execution. Complete this section before touching Pre-Flight or Steps.

```
Unknown: [what is unclear]
Required: [exact value or decision needed to resolve it]
Source: [who/what provides it — codebase read, human input, previous step output]
Blocking: [which steps cannot start without this resolved]
```

**If any Unknown has Source = "human input" and has not been resolved → do not begin the plan. Output:**
`"[CLARIFICATION NEEDED: list all unresolved unknowns]"` and stop.

---

## PRE-FLIGHT (Run Before Any Code Changes)

> Every plan must begin with a pre-flight section. The agent reads the codebase and confirms it matches plan assumptions BEFORE touching anything. The output of this section becomes the **baseline snapshot** used to verify that only intended changes occurred.

```
Read [primary file(s) this plan touches] in full. Capture and output:
(1) Every [constant / field / function] currently defined, in order
(2) The exact current signature of [function this plan modifies]
(3) The exact line(s) where [key anchor] appears
(4) Every file that imports from [module being changed]
(5) Current test count: run [test command] and record the number of passing tests
(6) Line count of [primary files]: wc -l [file] — record for post-plan diff

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills this in during pre-flight — do not pre-fill):**
```
Test count before plan: ____
Line count [file A]: ____
Line count [file B]: ____
Functions in [module]: ____
```

**Required pre-flight checks (adapt per project):**
- [ ] All existing tests pass before any edits begin. Document the test count.
- [ ] Confirm all functions/classes named in the plan exist and have the expected signatures.
- [ ] Confirm all anchor lines (insertion points) exist exactly once in the correct scope.
- [ ] Confirm no in-progress migrations or uncommitted schema changes exist.

---

## ARCHITECTURE THINKING BLOCK — Fill Once Per Plan

> This section captures the high-level design reasoning for the entire plan before any step is written. It explains WHY this approach was chosen, what patterns are being applied, and what alternatives were rejected. It is written once at the plan level, then each step gets its own focused **Step Architecture Thinking** subsection.
>
> An agent that understands *why* a design was chosen makes better micro-decisions when the code doesn't perfectly match the plan. This block prevents the agent from silently substituting a simpler pattern when it encounters ambiguity.

```
## Architecture Overview

**The problem this plan solves:**
[What is currently wrong or missing in the codebase. Be specific — name the file and the limitation.]

**The pattern applied:**
[Name the design pattern(s) explicitly: Coordinator, Template Method, DTO, Open/Closed, Facade, DRY, etc.
For each pattern, state: what it is, why it was chosen over the alternative, and what breaks if it is violated.]

**What stays unchanged:**
[Every file this plan intentionally does NOT touch, and why it is safe to leave it unchanged.]

**What this plan adds:**
[Every new file or class, and the single responsibility each one owns.]

**Critical decisions (with alternatives rejected):**
[For each major decision, state the decision, the alternative considered, and why the alternative was rejected.
Format: Decision → Alternative → Why rejected]

**Known limitations acknowledged in this plan:**
[Explicit list of shortcuts, stubs, or imperfect solutions that are intentional.
Each must state: what it is, why it is acceptable now, and what the upgrade path is.]
```

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

For non-critical steps: include Step Architecture Thinking + Verification only.

---

## CODE REVIEW BLOCK (for critical steps)

> Every critical step includes a **Step Architecture Thinking** subsection before the Pre-Read Gate. This is the per-step design rationale — more focused than the plan-level Architecture Overview. It answers: what OOP principle or pattern is being applied here, why this file is the right place for this change, and what would break if the implementation deviated from the described approach.

```
**Step Architecture Thinking:**

**Pattern applied:** [Name the specific OOP pattern or principle: Template Method, SRP, Facade, DRY, DTO, Open/Closed, Dependency Inversion, etc.]

**Why this step exists here in the sequence:**
[What must be true before this step runs, and what becomes possible after it completes that was not possible before.]

**Why this file / class is the right location:**
[Not just "it makes sense" — name the specific reason. E.g. "models.py is the contract layer; defining the shape here means every downstream file imports from one source of truth rather than inferring the shape from usage."]

**Alternative approach considered and rejected:**
[One specific alternative. State what it would have looked like and exactly why it was worse.]

**What breaks if this step deviates from the described pattern:**
[Concrete failure mode — not abstract. E.g. "If token_count is not 0 by default, SummaryAgent cannot construct a SpecialistResult in the GREEN path where no LLM call is made."]

---

**Context:** [How this fits into the larger system. What breaks if this step is wrong.]

**Idempotent:** Yes / No — [reason. If No: describe what breaks on re-run and how to detect it.]

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

**Git Checkpoint:**
```bash
git add [files modified in this step only]
git commit -m "[step N] [imperative description of exactly what changed]"
```
Commit after verification passes. Do not batch multiple steps into one commit.

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
- **Tagged by confidence level** — Unit / Integration / E2E so the reader knows what "pass" actually guarantees

**Test anatomy:**

```
Type:      [Unit / Integration / E2E]
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

**Pattern:**
```
Step N — Phase A (safe, reversible)
  → Verification confirms Phase A succeeded
  → State Manifest: output [specific values / structures produced by Phase A]
  → Human Gate: output "[PHASE A COMPLETE — WAITING FOR HUMAN TO CONFIRM PHASE B VALUES]"

Step N — Phase B (data-dependent, uses values from calibration/previous output)
  → Agent substitutes ACTUAL values provided by human. Never invents values.
  → Verification confirms Phase B result is non-null/non-empty
```

---

## STATE MANIFEST (use at every Human Gate)

```
STATE MANIFEST — [Step N] — [timestamp or session ID if available]

Files modified so far:
  [file A]: [brief description of what changed]
  [file B]: [brief description of what changed]

Values produced:
  [variable / output name]: [actual value]

Verifications passed:
  Step 1: ✅ [what was confirmed]
  Step 2: ✅ [what was confirmed]

Next step on resume:
  Step [N+1]: [name] — requires [specific human input or value]

[WAITING: describe exactly what the human must provide]
```

---

## STEPS ANALYSIS (fill this in before writing the plan)

> For each step, classify it before writing it. This prevents under-specifying critical steps and over-specifying simple ones.

```
Step 1 ([name]) — [Critical / Non-critical] ([reason]) — [full code review / verification only] — Idempotent: [Yes/No]
Step 2 ([name]) — [Critical / Non-critical] ([reason]) — [full code review / verification only] — Idempotent: [Yes/No]
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

## Architecture Overview

> Fill this section completely before writing any steps. An agent that understands the design makes better decisions when code doesn't perfectly match the plan.

**The problem this plan solves:**
[What is currently wrong or missing. Name the file and the specific limitation.]

**The pattern(s) applied:**
[Name each design pattern explicitly. For each: what it is, why it was chosen, what breaks if violated.]

**What stays unchanged:**
[Every file intentionally NOT touched, and why it is safe to leave it unchanged.]

**What this plan adds:**
[Every new file or class, and the single responsibility each one owns.]

**Critical decisions:**

| Decision | Alternative considered | Why alternative rejected |
|----------|----------------------|--------------------------|
| [choice made] | [what else was considered] | [specific reason rejected] |
| [choice made] | [what else was considered] | [specific reason rejected] |

**Known limitations acknowledged:**

| Limitation | Why acceptable now | Upgrade path |
|-----------|-------------------|--------------|
| [shortcut or stub] | [reason] | [future fix] |

---

## Critical Decisions
[Repeat the decisions table above as a bulleted list for quick reference during execution.]
- **Decision 1:** [choice] — [rationale]
- **Decision 2:** [choice] — [rationale]

---

## Clarification Gate

> Complete before Pre-Flight. If any item is unresolved and Source = "human input", stop and request clarification.

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| [what is unclear] | [exact value or decision] | [codebase / human / step output] | [step N] | ⬜ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read [file] in full. Capture and output:
(1) Every [constant / method / field] defined at [module/class] level, in order
(2) Exact current signature of [function this plan modifies]
(3) Exact line where [key anchor] appears
(4) Every file that imports from [module]
(5) Run [test command] — record passing test count
(6) Run wc -l [primary files] — record line counts

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count [file A]:    ____
Line count [file B]:    ____
```

**Automated checks (all must pass before Step 1):**

- [ ] Existing test suite passes. Document test count: `____`
- [ ] `[function_name]` exists and accepts `[expected signature]`
- [ ] `[anchor_line]` appears exactly once in `[file]` inside `[scope]`
- [ ] `[variable_name]` does not exist yet (for new additions) OR does exist (for modifications)
- [ ] No in-progress migrations or uncommitted schema changes

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| Step 1 | ✅ | ✅ | ✅ | No environment-specific changes |
| Step 2 | ✅ | ✅ | ⚠️ Manual gate | Requires prod DB credentials |

---

## Tasks

### Phase 1 — [Phase Name]

**Goal:** [What is true after this phase that was not true before]

---

- [ ] 🟥 **Step 1: [Name]** — *[Critical / Non-critical]: [one-line reason]*

  **Step Architecture Thinking:**

  **Pattern applied:** [Name the OOP pattern or principle explicitly — e.g. Template Method, Single Responsibility, Facade, DTO, Open/Closed, DRY, Dependency Inversion, Coordinator.]

  **Why this step exists here in the sequence:**
  [What must be true before this step, and what becomes possible after it that was not possible before. One concrete sentence per direction.]

  **Why this file / class is the right location:**
  [Name the specific reason. E.g. "This is the contract layer — defining the shape here means every downstream file imports from one source of truth."]

  **Alternative approach considered and rejected:**
  [One specific alternative. What it would have looked like and exactly why it was worse.]

  **What breaks if this step deviates from the described pattern:**
  [Concrete failure mode — not abstract. Name the file and function that would fail.]

  ---

  **Idempotent:** Yes / No — [reason. If No: what breaks on re-run and how to detect it.]

  **Context:** [How this fits into the system. What is currently wrong and why this fixes it.]

  **Pre-Read Gate:**
  Before any edit:
  - Run `grep -n '[anchor_string]' [file]`. Must return exactly 1 match inside `[function/class]`. If 0 or 2+ → STOP.
  - Run `grep -n '[variable_to_reference]' [file]`. Must exist in correct scope. If missing → STOP.

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

  **Risks:**
  - [Risk 1] → mitigation: [specific action]

  **Git Checkpoint:**
  ```bash
  git add [files modified in this step only]
  git commit -m "step 1: [imperative description]"
  ```

  **Subtasks:**
  - [ ] 🟥 [Subtask 1 — specific enough that done/not-done is unambiguous]
  - [ ] 🟥 [Subtask 2]

  **✓ Verification Test:**

  **Type:** [Unit / Integration / E2E]

  **Action:** [Exact command — no placeholders]

  **Expected:**
  - [Specific output or state]
  - [Old content no longer present — for replacements]

  **Pass:** [The single observable that confirms this step is done]

  **Fail:**
  - If [symptom A] → [likely cause] → check [specific file/function]
  - If [symptom B] → [likely cause] → check [specific file/function]

---

- [ ] 🟥 **Step 2: [Name]** — *[Critical]: [reason]*

  > ⚠️ **Split Operation** — Phase A must complete and verify before Phase B begins.

  **Step Architecture Thinking:**

  **Pattern applied:** [Name pattern]

  **Why this step exists here in the sequence:** [What A.1 enabled that makes this possible now]

  **Why this file / class is the right location:** [Specific reason]

  **Alternative approach considered and rejected:** [One alternative and why rejected]

  **What breaks if this step deviates:** [Concrete failure mode]

  ---

  **Idempotent:** Phase A: Yes. Phase B: No — [reason]

  **Context:** [Why splitting is necessary. What silent failure would occur if combined.]

  ---

  **Phase A — [Safe change]**

  **Pre-Read Gate:**
  - Run `[command]`. Show output. STOP. Do not proceed until human confirms `[specific value]`.

  ```[language]
  # Phase A code only
  ```

  **Phase A Verification:**
  - [Specific check that Phase A succeeded]
  - [Confirm no data was changed]

  **Git Checkpoint (Phase A):**
  ```bash
  git add [Phase A files only]
  git commit -m "step 2a: [Phase A description]"
  ```

  **State Manifest — Phase A:**
  ```
  Files modified: [list]
  Values produced: [list any outputs Phase B needs]
  Next: Step 2B requires [specific human input]
  ```

  **Human Gate:**
  Output `"[PHASE A COMPLETE — WAITING FOR [specific input needed for Phase B]]"` as the final line.
  Do not write any code or call any tools after this line.

  ---

  **Phase B — [Data-dependent change]**

  > Only execute after human provides: [exact list of values/confirmations needed]

  ```[language]
  # Phase B code — uses actual values from human confirmation, not placeholders
  ```

  **Git Checkpoint (Phase B):**
  ```bash
  git add [Phase B files only]
  git commit -m "step 2b: [Phase B description]"
  ```

  **✓ Verification Test (Phase B):**

  **Type:** [Unit / Integration / E2E]

  **Action:** [Query or check that confirms data exists]

  **Pass:** [All fields non-null, values match Phase A output]

  **Fail:**
  - If zero rows updated → WHERE clause matched nothing → confirm field exists in table
  - If fields null → UPDATE failed silently → check transaction log

---

- [ ] 🟥 **Step 3: [Name]** — *Non-critical*

  **Step Architecture Thinking:**

  **Pattern applied:** [Name pattern]

  **Why this step exists here in the sequence:** [One sentence]

  **Why this file / class is the right location:** [One sentence]

  **Alternative approach considered and rejected:** [One alternative]

  **What breaks if this step deviates:** [One sentence]

  ---

  **Idempotent:** Yes — [reason]

  **Git Checkpoint:**
  ```bash
  git add [files]
  git commit -m "step 3: [imperative description]"
  ```

  **✓ Verification Test:**

  **Type:** [Unit / Integration / E2E]

  **Action:** [Exact interaction]

  **Pass:** [Specific success indicator]

  **Fail:**
  - If [symptom] → [cause] → check [file/component]

---

### Phase 2 — [Phase Name]

**Goal:** [What is true after this phase]

> [Same step structure as Phase 1 — every step includes Step Architecture Thinking block]

---

## Regression Guard

**Systems at risk from this plan:**
- [System 1] — [why it could be affected]

**Regression verification:**

| System | Pre-change behavior | Post-change verification |
|--------|---------------------|--------------------------|
| [System 1] | [What it did before] | [Exact check that confirms it still does] |

**Test count regression check:**
- Tests before plan (from Pre-Flight baseline): `____`
- Tests after plan: run `[test command]` — must be `≥` baseline count

---

## Rollback Procedure

```bash
# Rollback Step N (reverse order)
git revert [commit hash from Step N git checkpoint]

# Confirm system is back to pre-plan state:
[test command] — must return same count as Pre-Flight baseline
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| **Pre-flight** | Clarification Gate complete | All unknowns resolved | ⬜ |
| | Architecture Overview complete | All patterns named, alternatives documented | ⬜ |
| | Baseline snapshot captured | Test count + line counts recorded | ⬜ |
| **Phase 1** | [Dependency] installed/available | [Import or version check] | ⬜ |
| | [Anchor line] exists once in correct scope | grep returns exactly 1 match | ⬜ |
| | Existing tests pass | Test count matches pre-flight baseline | ⬜ |
| **Phase 2** | [Phase 1 complete] | All Phase 1 verifications passed | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|-----------|---------------------|-----------------|------------|
| Step 1 | 🟢 **Low** | [Risk] | [How you'd know early] | Yes |
| Step 2 Phase A | 🟡 **Medium** | [Risk] | [How you'd know early] | Yes |
| Step 2 Phase B | 🔴 **High** | Silent failure if Phase A verified but Phase B skipped | Check non-null fields immediately after | No |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| [Feature 1] | [Specific measurable behavior] | **Do:** [action] → **Expect:** [output] → **Look:** [location] |
| [Regression: Feature X] | Unchanged from pre-plan | **Do:** [existing test] → **Expect:** [same result as before] |
| Test count | ≥ pre-plan baseline | Run [test command] → count must not decrease |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not proceed past a Human Gate without explicit human input.**
⚠️ **If blocked, mark 🟨 In Progress and output the State Manifest before stopping.**
⚠️ **Do not batch multiple steps into one git commit.**
⚠️ **If idempotent = No, confirm the step has not already run before executing.**
⚠️ **Architecture Overview must be complete before Pre-Flight begins.**
⚠️ **Every step must include a Step Architecture Thinking block — no exceptions.**
