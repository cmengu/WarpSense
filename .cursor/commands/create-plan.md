# Plan Creation Stage

Based on our full exchange, produce a markdown plan document.

Requirements for the plan:

- Include clear, minimal, concise steps.
- Track the status of each step using these emojis:
  - 🟩 Done
  - 🟨 In Progress
  - 🟥 To Do
- Include dynamic tracking of overall progress percentage (at top).
- Do NOT add extra scope or unnecessary complexity beyond explicitly clarified details.
- Steps should be modular, elegant, minimal, and integrate seamlessly within the existing codebase.

## CRITICAL CODE REVIEW APPROACH

**High-level summary only at top** - architectural decisions, not code snippets.

**Code review lives IN each step** - for steps that touch critical infrastructure:
- API integrations (new endpoints, auth changes)
- State management (context, global state, data flow)
- Database operations (schema, migrations, queries)
- Security-sensitive code (validation, encryption, auth)
- New architectural patterns
- Breaking changes to existing code

For each critical step, include:
- **Context:** Why this step matters to the larger system
- **Code snippet:** The actual implementation (not pseudo-code)
- **What it does:** Brief explanation
- **Why this approach:** Rationale/trade-offs
- **Assumptions:** What we're assuming is true
- **Risks:** What could go wrong
- **Verification Test:** Environment-agnostic test that describes WHAT to verify, not exact commands

For non-critical steps: Still include verification test, but skip code review.

---

## VERIFICATION TEST GUIDELINES

## Example Verification Tests (Reference)

### Frontend Component Test
**Action:** Load [page], click [button]  
**Expected:** Modal opens with [form fields]  
**Observe:** Visual modal element appears, form has [field1], [field2], [field3]  
**Pass:** Modal is visible, all fields render, no console errors  
**Fail:** Modal missing → check [component] is imported; Fields missing → check [props/data]

### Backend API Test
**Action:** Send POST request to [endpoint] with `{ field: value }`  
**Expected:** 201 status, response `{ id, created_at }`  
**Observe:** Network response in browser/API tool, database [table] has new row  
**Pass:** Success status, response has `id` field, database count increased by 1  
**Fail:** 400 error → payload validation failed - check [schema]; 500 error → check logs for exception

### State Management Test
**Action:** Trigger [user action] that updates [state]  
**Expected:** [State variable] changes from [old value] to [new value]  
**Observe:** Use browser DevTools to inspect component state/store  
**Pass:** State updates correctly, UI reflects new state  
**Fail:** State unchanged → action not dispatched; State wrong value → reducer logic error

### Integration Test
**Action:** Complete user flow: [step1] → [step2] → [step3]  
**Expected:** User sees [final screen] with [data], database has [records]  
**Observe:** Final UI state, database query shows expected records  
**Pass:** Complete flow works end-to-end without errors  
**Fail:** Breaks at [step] → check [component/API] in that step
**Structure each test as:**
1. **Action:** What to do (load page, click button, call function)
2. **Expected:** What should happen (visible behavior, data shape, state change)
3. **How to observe:** Where to look (UI, browser console, network tab, database query tool)
4. **Common failures:** What usually breaks + conceptual fix (not exact commands)

---

## Steps Analysis

##Example Steps Analysis (Reference)

Step 1 (fetchSession) — Critical (API integration); full code review.
Step 2 (HeatMap) — Non-critical; verification test only.
Step 3 (TorchAngleGraph) — Non-critical; verification test only.
Step 4 (State + slider) — Non-critical.
Step 5 (Playback loop) — Critical (state management); full code review.
Step 6 (Keyboard shortcuts) — Non-critical.
Step 7 (Validate frame fields) — Non-critical.
Step 8 (extract_features) — Critical (backend); full code review.
Step 9 (score_session) — Non-critical.
Step 10 (GET /score + ScorePanel) — Critical (new API); full code review.
Steps 11–13 — Non-critical.

## Markdown Template:

# Feature Implementation Plan

**Overall Progress:** `0%`

## TLDR
Short summary of what we're building and why.

---

## Critical Decisions

Key architectural/implementation choices made during exploration (NO CODE HERE - just decisions):
- **Decision 1:** [choice] - [brief rationale]
- **Decision 2:** [choice] - [brief rationale]
- **Decision 3:** [choice] - [brief rationale]

---

## Tasks

### Phase 1 — [Phase Name]

**Goal:** [What users can do after this phase]

- [ ] 🟥 **Step 1: [Name]**
  
  **Subtasks:**
  - [ ] 🟥 Subtask 1
  - [ ] 🟥 Subtask 2
  
  **✓ Verification Test:**
  
  **Action:** 
  - Start development server
  - Navigate to the [specific page/route]
  - [Specific user action like click, type, scroll]
  
  **Expected Result:**
  - UI should show [specific element/text/color]
  - [Specific state] should contain [expected value/shape]
  - No console errors related to [component/feature]
  
  **How to Observe:**
  - **Visual:** Look for [specific UI element] in [location on page]
  - **Console:** Open browser DevTools → Console tab → check for [expected log or absence of errors]
  - **State:** Use React DevTools / Vue DevTools to inspect [component name] state
  
  **Pass Criteria:** 
  - [Observable behavior 1] is visible/present
  - [Observable behavior 2] matches expected pattern
  - No errors in console related to this feature
  
  **Common Failures & Fixes:**
  - **If [element] doesn't render:** Check component is imported and route is configured
  - **If console shows [error type]:** Verify [data dependency] is loaded before render
  - **If state is undefined:** Ensure [parent component/context] is wrapped correctly

---

- [ ] 🟥 **Step 2: [Name]** — *Why it matters: [critical infrastructure reason]*
  
  **Context:** [How this fits into the larger system/data flow]
```typescript
  // The actual code snippet
```
  
  **What it does:** [brief explanation]
  
  **Why this approach:** [rationale/trade-offs]
  
  **Assumptions:** 
  - [assumption 1]
  - [assumption 2]
  
  **Risks:** 
  - [risk 1 and mitigation]
  - [risk 2 and mitigation]
  
  ---
  
  **Subtasks:**
  - [ ] 🟥 Subtask 1
  - [ ] 🟥 Subtask 2
  
  **✓ Verification Test:**
  
  **Action:**
  - Make API request to [endpoint] with [payload structure]
  - Or: Run backend test suite for [feature]
  - Or: Use API testing tool (Postman/Thunder Client/curl equivalent)
  
  **Expected Result:**
  - Response status: [2xx success code]
  - Response body shape: `{ field1: type, field2: type, ... }`
  - Database contains new/updated record with [key fields]
  - [Side effect] occurred (email sent, cache updated, etc.)
  
  **How to Observe:**
  - **API response:** Check network tab in DevTools or API client response
  - **Database:** Query your database tool for [table] WHERE [condition] → should return [expected row count]
  - **Logs:** Backend logs should show [success message] without [error pattern]
  - **Side effects:** Check [external system/file/queue] for [expected change]
  
  **Pass Criteria:**
  - API returns success status code (200/201/204)
  - Response matches expected data shape
  - Database record exists with correct [field1], [field2] values
  - No error logs related to this operation
  
  **Common Failures & Fixes:**
  - **If API returns 4xx error:** Request payload doesn't match validation schema - check [model/validator file]
  - **If API returns 5xx error:** Backend exception occurred - check error logs for stack trace, likely [common issue]
  - **If database record missing:** Transaction may have rolled back - check for validation errors or constraint violations
  - **If response has wrong shape:** Serialization mismatch - verify [serializer/model] includes all required fields

---

- [ ] 🟥 **Step 3: [Name]** (non-critical - no code review)
  
  **Subtasks:**
  - [ ] 🟥 Subtask 1
  - [ ] 🟥 Subtask 2
  
  **✓ Verification Test:**
  
  **Action:**
  - [User interaction or system trigger]
  
  **Expected Result:**
  - [Observable outcome]
  
  **How to Observe:**
  - [Where to look for the result]
  
  **Pass Criteria:**
  - [Specific success indicator]
  
  **Common Failures & Fixes:**
  - **If [failure symptom]:** [Conceptual cause] - check [component/file/config type]

---

### Phase 2 — [Phase Name]

[Same structure]

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | [Package/library] installed | Check package.json has [package] OR import works without error | ⬜ |
| | [Service] running | [Service] responds to health check OR UI loads without connection errors | ⬜ |
| | [Data] exists | Sample data returns from [API/database] OR mock data generates successfully | ⬜ |
| **Phase 2** | [Dependency] | [Verification method] | ⬜ |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟡 **40%** | [Specific technical risk] | [Behavior you'd observe if this is happening] |
| Phase 2 | 🔴 **70%** | [Specific technical risk] | [Test that would catch this before it breaks production] |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|----------------|---------------------|
| [Feature 1] | User can [action] and see [result] | **Test:** [Action steps] → **Expect:** [Observable outcome] → **Location:** [Where to observe] |
| [Feature 2] | System [behavior] when [condition] | **Test:** [Trigger condition] → **Expect:** [System response] → **Location:** [Logs/UI/DB] |

---

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**