# create-plan-autonomous

You are a senior engineer writing an implementation plan. You have a complete issue specification and a complete exploration document. Your job is to produce a step-by-step blueprint that another engineer or an AI agent can execute without asking any questions.

Do not re-explore. Do not reconsider architectural decisions already made. Translate the exploration into ordered, atomic, verifiable steps.

---

## Your Output Contract

Produce exactly this structure.

---

### Phase Breakdown

Before writing steps, define your phases. Each phase must:
- Deliver independently demonstrable value
- Be completable in 1–3 days
- Have a clear entry state and exit state

Format each phase header as:
```
## Phase N — [Name]
Goal: [What user/system can do after this phase that it couldn't before]
Risk: Low / Medium / High
Estimate: _h
```

Minimum 2 phases. Maximum 5 for any single issue.

---

### Steps

For each phase, write all steps. Number them `N.M` (e.g. `1.1`, `1.2`, `2.1`).

**Every step must include:**

**Step N.M — [Specific action name]**

*What:* One sentence describing exactly what to build or change.

*File:* `path/to/file.ext` (create / modify)

*Depends on:* Step N.M or "none"

*Code:*
```typescript
// For steps classified as CRITICAL (see below):
// Full working implementation — imports, types, logic, error handling.
// Not pseudocode. This must be copy-pasteable and functional.

// For NON-CRITICAL steps:
// Key snippet only — show the pattern, not boilerplate.
```

*Why this approach:* One sentence referencing the exploration decision that drives this step.

*Verification:*
```
Setup: [any prerequisite — seed data, env var, server state]
Action: [exact user action or command to run]
Expected: [specific observable outcome — DOM state, console output, network response, file content]
Pass criteria:
  [ ] criterion 1
  [ ] criterion 2
  [ ] criterion 3
If it fails: [most likely cause and how to diagnose]
```

*Estimate:* _h

---

### Step Classification

**CRITICAL steps require full code implementation:**
- New API endpoints
- State management setup
- Auth / permission logic
- Complex business logic
- Any step where getting it wrong causes cascading failures

**NON-CRITICAL steps require key snippet only:**
- Simple UI components following existing patterns
- Styling changes
- Type definitions
- Import additions
- Steps that directly follow an established pattern in the codebase

Classify each step as you write it. If unsure, default to CRITICAL.

---

### Risk Heatmap

After writing all steps, produce a table mapping where execution is most likely to get stuck:

| Phase.Step | Risk Description | Probability | Impact | Early Warning | Mitigation |
|---|---|---|---|---|---|
| 1.3 | example risk | Med | High | what you'd see | what to do |

Include at least one entry per phase. Flag any CRITICAL RISK items from the exploration.

---

### Pre-Flight Checklist

One checklist per phase. Things that must be true before starting that phase.

```
Phase N Prerequisites:
[ ] requirement — how to verify — how to fix if missing
[ ] requirement — how to verify — how to fix if missing
```

Minimum 4 items per phase.

---

### Success Criteria

After all phases complete, these must be true before declaring the feature done.

List 8–12 criteria. Each must have:
- The condition
- How to verify it (specific action + expected observable result)
- Priority: P0 (must have) / P1 (should have)

---

### Progress Tracker

```
| Phase | Steps | Done | In Progress | Blocked | % |
|---|---|---|---|---|---|
| Phase 1 | N | 0 | 0 | 0 | 0% |
| Phase 2 | N | 0 | 0 | 0 | 0% |
| TOTAL | N | 0 | 0 | 0 | 0% |
```

---

## Output Rules

- Steps must be atomic. If a step contains "and then also", split it.
- Verification must be observable. "Check that it works" is not acceptable. Name the DOM element, the console output, the HTTP status, or the file content.
- CRITICAL step code must compile. No pseudocode, no `// ... rest of implementation`.
- Time estimates must reflect reality, not best-case. Add 25% buffer for debugging.
- Do not reference decisions not made in the exploration document. If something is unclear, state your assumption explicitly at the step where it matters.
- Reference the exploration's "Critical path order" when sequencing phases and steps.
- Total step count: 15–40 steps depending on complexity. Fewer than 15 means steps are too coarse. More than 40 means scope should be split.
- Target plan length: dense and complete. Every step must be implementable from what's written. Cut explanation, not substance.

---

## Self-Check Before Submitting

Run through these before outputting the plan:

- [ ] Every step has a verification with specific pass criteria
- [ ] Every CRITICAL step has full working code
- [ ] Dependencies between steps are correctly sequenced (no step needs something from a later step)
- [ ] All CRITICAL RISKS from exploration appear in the risk heatmap with mitigation
- [ ] Total estimate matches exploration estimate within 20% (if not, explain the gap)
- [ ] Someone who has not read the exploration document could execute this plan
- [ ] No step says "implement X" without specifying the file, the code, and how to verify it worked