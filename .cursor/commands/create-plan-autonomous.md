# Create Plan (Implementation Blueprint) - ENHANCED VERSION

**Time Budget:** 90-120 minutes MINIMUM for comprehensive plan creation.
**If you finish in less than 90 minutes, your plan is too shallow.**

**Context:** You have a complete issue specification and deep exploration. Now you create the step-by-step implementation blueprint.

**Your Mission:** Transform exploration insights into an exhaustive, bulletproof implementation plan that another developer (or an AI agent) could follow WITHOUT asking clarifying questions.

---

## Phase 0: Understand Your Role in the Workflow

**This is Step 3 of 3:**
1. **Create Issue** (COMPLETE - the WHAT and WHY)
2. **Explore Feature** (COMPLETE - the HOW)
3. **Create Plan** ← You are here (step-by-step EXECUTION)

**Your job right now:**
- Break exploration into atomic steps
- Write verification tests for EVERY step
- Identify critical steps needing code review
- Order steps by dependencies
- Estimate effort realistically
- Document failure modes
- Create quality gates
- Make it impossible to get stuck

**NOT your job right now:**
- Implement the feature (that's after planning)
- Question the architectural decisions (those were made in exploration)
- Research alternatives (that was exploration)

---

## MANDATORY PRE-PLANNING THINKING SESSION (30 minutes minimum)

**🛑 STOP. Before writing any plan, spend 30 minutes thinking deeply.**

### A. Exploration Review and Synthesis (10 minutes)

**Read the entire exploration document. Then answer:**

1. **What's the core approach we're taking?**
   - In one sentence: _____
   - Key decisions: _____
   - Why this approach: _____

2. **What are the major components?**
   - Component #1: _____ (purpose: _____)
   - Component #2: _____ (purpose: _____)
   - Component #3: _____ (purpose: _____)
   [List all]

3. **What's the data flow?**
```
   Input: _____
     ↓
   Transform: _____
     ↓
   Process: _____
     ↓
   Output: _____
```

4. **What are the biggest risks?**
   - Risk #1: _____ (from exploration)
   - Risk #2: _____ (from exploration)
   - Risk #3: _____ (from exploration)

5. **What did exploration NOT answer?**
   - Gap #1: _____
   - Gap #2: _____
   - Gap #3: _____

**Write at least 400 words:**
```
[Your synthesis]
```

### B. Dependency Brainstorm (10 minutes)

**Think about what depends on what BEFORE ordering steps.**

**Major work items (before ordering):**
1. _____
2. _____
3. _____
4. _____
5. _____
[List at least 20]

**For each item, what does it depend on?**
- Item #1 depends on: _____, _____, _____
- Item #2 depends on: _____, _____, _____
- Item #3 depends on: _____, _____, _____
[All items]

**Draw rough dependency graph:**
```
Item A
  ↓
Item B ──→ Item D
  ↓         ↓
Item C ──→ Item E
  ↓
Item F
```

**Critical path (longest dependency chain):**
1. _____
2. _____
3. _____
4. _____
5. _____

**Bottlenecks (items blocking many others):**
- _____
- _____
- _____

**Parallelizable work (can be done simultaneously):**
- _____ and _____ (no dependencies)
- _____ and _____ (no dependencies)

**Write at least 400 words:**
```
[Your dependency analysis]
```

### C. Risk-Based Planning (10 minutes)

**Plan around risks, not just features.**

**From exploration, top 5 risks:**
1. Risk: _____ (probability: ___%, impact: _____)
2. Risk: _____ (probability: ___%, impact: _____)
3. Risk: _____ (probability: ___%, impact: _____)
4. Risk: _____ (probability: ___%, impact: _____)
5. Risk: _____ (probability: ___%, impact: _____)

**For each risk, planning implications:**

**Risk #1:**
- **How to address in plan:**
  - Step to mitigate: _____
  - Step to detect early: _____
  - Contingency step: _____
- **Where in plan:** Phase ___, Step ___
- **Verification needed:** _____

**Risk #2:** [Same]
**Risk #3:** [Same]
**Risk #4:** [Same]
**Risk #5:** [Same]

**Failure modes to plan for:**
1. **If _____ fails:**
   - Detection: _____
   - Response: _____
   - Recovery: _____

2. **If _____ fails:**
   [Same]

[At least 10 failure modes]

**Write at least 400 words:**
```
[Your risk planning]
```

**Quality gate:** Cannot start planning until you've spent 30+ minutes here and written 1200+ words.

---

## What Makes a Plan 5X Better

**A 5X plan has:**

### 1. Atomic Steps
- ❌ **BAD:** "Add the export feature"
- ✅ **GOOD:** "Create ExportButton component in src/components/ExportButton.tsx with dropdown that shows 3 format options (CSV, JSON, XLSX)"

### 2. Verification Tests for EVERY Step
- ❌ **BAD:** "Test that it works"
- ✅ **GOOD:** "Navigate to /session/123 → Click Export → Expect: Dropdown opens below button showing 3 options → Verify: Console has no errors, dropdown has aria-label"

### 3. Code Examples for Critical Steps
- ❌ **BAD:** "Add error handling"
- ✅ **GOOD:** 
```typescript
  try {
    const result = await exportSession(sessionId);
  } catch (error) {
    if (error instanceof NetworkError) {
      showToast("Connection failed. Check internet.");
    } else if (error instanceof ValidationError) {
      showToast("Invalid session data.");
    } else {
      showToast("Export failed. Contact support.");
    }
  }
```

### 4. Failure Mode Documentation
- ❌ **BAD:** Nothing
- ✅ **GOOD:** "If modal doesn't appear: Component likely not imported in parent - check import statement in SessionView.tsx line 12"

### 5. Effort Estimates with Reasoning
- ❌ **BAD:** "2 hours"
- ✅ **GOOD:** "2.5 hours (30 min component, 45 min logic, 30 min styling, 45 min testing + debugging)"

---

## Planning Structure

**You will create plan in this order:**
1. Pre-planning analysis (30 min) ← Just completed
2. Phase breakdown (15 min)
3. Step definition (60+ min)
4. Verification test writing (45+ min)
5. Risk mapping (15 min)
6. Quality review (15 min)

**Total minimum: 180 minutes (3 hours) of planning**

---

## 1. Phase Breakdown Strategy (15 minutes minimum)

**Don't create one giant phase. Break into logical, deliverable chunks.**

### A. Identify Natural Breaking Points

**Where can we deliver incremental value?**

**Possible phase boundaries:**
1. After _____ (user can: _____)
2. After _____ (user can: _____)
3. After _____ (user can: _____)
4. After _____ (user can: _____)
5. After _____ (user can: _____)

**For each boundary, ask:**
- Can we ship this alone? Yes/No
- Does it provide user value? Yes/No
- Is it independently testable? Yes/No
- Is it a logical stopping point? Yes/No

**Valid phase boundaries (all answered Yes):**
- _____
- _____
- _____

### B. Phase Design Principles

**Good phase = delivers value + independently testable + 1-3 days max**

**Phase template:**
```
Phase N: [User-facing value delivered]

Goal: User can now _____

Includes:
- Backend: _____
- Frontend: _____
- Integration: _____
- Testing: _____

After this phase:
- User can: _____
- System can: _____
- Developer can: _____
```

**Design your phases:**

**Phase 1: [Name]**
- **Goal:** _____
- **User value:** _____
- **Why first:** _____
- **Estimated effort:** _____ hours
- **Risk level:** 🟢/🟡/🔴
- **Major steps (high-level):**
  1. _____
  2. _____
  3. _____
  [5-10 steps]

**Phase 2: [Name]**
[Same structure]

**Phase 3: [Name]**
[Same structure]

**Phase 4: [Name]**
[Same structure]

**Quality requirements:**
- [ ] At least 3 phases (more for complex features)
- [ ] Each phase delivers user value
- [ ] Each phase is 1-3 days (8-24 hours)
- [ ] Phases have clear order (dependencies)
- [ ] No phase is too large (> 30 hours)

### C. Phase Dependency Graph

**Map phase dependencies:**
```
Phase 1 (Foundation)
  ↓
Phase 2 (Core Feature) ──→ Phase 4 (Polish)
  ↓
Phase 3 (Extensions)
```

**Critical path:**
- Phase 1 → Phase 2 → Phase 4 (_____ total hours)

**Can Phase 3 be done in parallel with Phase 4?**
- Yes/No
- If Yes: Saves _____ hours

### D. Phase Success Criteria

**For each phase, define "done":**

**Phase 1 Done When:**
- [ ] Criterion 1: _____
- [ ] Criterion 2: _____
- [ ] Criterion 3: _____
- [ ] All Phase 1 step verification tests pass
- [ ] No blockers for Phase 2

**Phase 2 Done When:**
[Same]

**Phase 3 Done When:**
[Same]

**Quality gate for this section:**
- [ ] At least 3 phases defined
- [ ] Each phase has clear goal
- [ ] Each phase has 5-10 high-level steps
- [ ] Dependencies mapped
- [ ] Success criteria defined
- [ ] Spent at least 15 minutes
- [ ] Written at least 600 words

**Your phase breakdown (minimum 600 words):**
```
[Complete phase documentation]
```

---

## 🧠 THINKING CHECKPOINT #1 (10 minutes minimum)

**Stop. Review your phases.**

### Phase Sanity Check

1. **Can someone else understand the phases?**
   - Read them out loud
   - Any confusion? _____
   - Fix: _____

2. **Is each phase independently valuable?**
   - Phase 1: Value = _____
   - Phase 2: Value = _____
   - Phase 3: Value = _____
   - Any phase with no value? _____

3. **Are phases right-sized?**
   - Too large (> 30 hours): _____
   - Too small (< 4 hours): _____
   - Adjust: _____

4. **Do dependencies make sense?**
   - Any circular dependencies? _____
   - Any unnecessary dependencies? _____
   - Can simplify? _____

5. **What's the riskiest phase?**
   - Phase: _____
   - Why risky: _____
   - Mitigation: _____

**Quality gate:** Spend 10+ minutes, write 300+ words.

---

## 2. Step Definition (60+ minutes minimum)

**Now break each phase into atomic steps.**

### A. Step Definition Principles

**Every step must be:**
1. **Atomic:** One clear action
2. **Specific:** No vague descriptions
3. **Verifiable:** Has test that proves it works
4. **Ordered:** Dependencies clear
5. **Estimated:** Realistic time
6. **Documented:** Files, code, rationale

**Step size:**
- **Too large:** "Implement export feature" (what exactly?)
- **Too small:** "Add comma on line 45" (too granular)
- **Just right:** "Create ExportButton component that renders dropdown with 3 format options when clicked"

**Aim for: 15-30 steps per phase**

### B. Step Template (Critical Steps)

**For CRITICAL steps (need code review), use this template:**
```markdown
#### 🟥 Step X.Y: [Specific, actionable step name] — *Critical: [Why]*

**Why this is critical:** [1-2 sentences explaining architectural/security/state impact]

**Context (minimum 200 words):**
```
[Explain:]
- How this fits into the larger system
- What data flows through here
- Why this approach vs alternatives
- What this enables downstream
- What assumptions we're making
- What could go wrong

// FULL, ACTUAL, WORKING code
// Not pseudocode - real implementation
// Include:
// - All imports
// - Type definitions
// - Full function/component implementation
// - Error handling
// - Edge case handling
// - Comments explaining non-obvious logic

// Example:
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { db } from '@/lib/db';

// Schema for request validation
const exportRequestSchema = z.object({
  sessionId: z.string().uuid(),
  format: z.enum(['csv', 'json', 'xlsx']),
  includeMetadata: z.boolean().optional().default(false),
});

// Type for validated request
type ExportRequest = z.infer<typeof exportRequestSchema>;

/**
 * POST /api/export/session
 * Exports a session in the requested format
 */
export async function POST(request: Request) {
  try {
    // Parse and validate
    const body = await request.json();
    const validated = exportRequestSchema.parse(body);
    
    // Fetch session data
    const session = await db.session.findUnique({
      where: { id: validated.sessionId },
      include: {
        frames: true,
        metadata: validated.includeMetadata,
      },
    });
    
    // 404 if not found
    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      );
    }
    
    // Generate export (delegated to utility)
    const exportData = await generateExport(
      session,
      validated.format
    );
    
    // Return success
    return NextResponse.json({
      downloadUrl: exportData.url,
      expiresAt: exportData.expiresAt,
      fileSize: exportData.size,
    });
    
  } catch (error) {
    // Validation errors
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          error: 'Invalid request',
          details: error.errors,
        },
        { status: 400 }
      );
    }
    
    // Server errors
    console.error('Export API error:', error);
    return NextResponse.json(
      { error: 'Export failed' },
      { status: 500 }
    );
  }
}

What this code does:

Creates POST endpoint at /api/export/session
Validates request with Zod schema (sessionId must be UUID, format must be enum)
Fetches session from database with optional metadata
Generates export file using utility function
Returns download URL with expiry
Handles validation errors (400), not found (404), server errors (500)

Why this approach:

Zod validation: Runtime type safety, clear error messages for invalid input
Database include: Conditional metadata loading saves bandwidth when not needed
Utility delegation: generateExport is separate for testability and reuse
Error separation: Different status codes for client errors (400) vs server errors (500)
Explicit 404: Clear when session doesn't exist vs other failures

Assumptions:

Session data structure matches Prisma schema in prisma/schema.prisma
generateExport utility exists (created in Step X.Y)
Database connection available via db import from @/lib/db
Export files stored temporarily (handled by generateExport)

Risks:

Large sessions: If session has 50k+ frames, generation might timeout

Probability: 30% (10% of sessions are 20k+)
Impact: High (user sees 500 error, no export)
Mitigation: Add size check, show warning in UI, implement streaming in future
Detection: Monitor response times, alert if >10s


Concurrent exports: User clicks export button rapidly

Probability: 20% (frustrated users)
Impact: Medium (multiple identical exports generated)
Mitigation: Disable button during export (handled in UI), API is idempotent
Detection: Check for duplicate exports in logs


Database connection pool exhaustion: Many simultaneous exports

Probability: 10% (only under heavy load)
Impact: High (all API calls fail)
Mitigation: Monitor connection pool usage, add rate limiting if needed
Detection: Database connection errors in logs



Trade-offs:

Accept: Synchronous export (blocks request)
To gain: Simpler implementation, faster to market
Worth it because: 90% of sessions export in <3s, can add async later

Downstream impact:

Enables: UI components can call this endpoint
Requires: generateExport utility (next step)
Affects: None (new endpoint, no breaking changes)

Subtasks:

 🟥 Create file app/api/export/session/route.ts
 🟥 Add Zod import and schema definition
 🟥 Implement POST handler with try-catch
 🟥 Add database query with conditional include
 🟥 Add error handling for validation, not found, server errors
 🟥 Add response type definition to types/api.ts

Files:

Create: app/api/export/session/route.ts (this endpoint)
Modify: types/api.ts (add ExportResponse type)
Depends on: lib/db.ts (database connection exists)
Required by: Step X.Y (UI component needs this endpoint)

✓ Verification Test:
Setup prerequisites:

 Database is running (docker-compose up or npm run db:start)
 Database has test data (run seed: npm run db:seed)
 Dev server running (npm run dev)
 Have valid session ID (get from: SELECT id FROM Session LIMIT 1)

Action:

Open API testing tool

Use: Postman / Thunder Client / curl
Alternative: Write quick test script


Send POST request to endpoint

URL: http://localhost:3000/api/export/session
Method: POST
Headers: Content-Type: application/json
Body:



json     {
       "sessionId": "replace-with-valid-uuid",
       "format": "csv",
       "includeMetadata": true
     }

Send invalid request (test validation)

Body:



json     {
       "sessionId": "not-a-uuid",
       "format": "invalid-format"
     }

Send request with non-existent session

Body:



json     {
       "sessionId": "00000000-0000-0000-0000-000000000000",
       "format": "csv"
     }
Expected Result:
Test 1 (Valid request):

Status: 200 OK
Response body:

json  {
    "downloadUrl": "https://...", // or /api/download/...
    "expiresAt": "2024-12-31T23:59:59Z", // ISO date string
    "fileSize": 12345 // positive integer
  }

Response time: < 5 seconds for typical session
Server logs: No errors

Test 2 (Invalid request):

Status: 400 Bad Request
Response body:

json  {
    "error": "Invalid request",
    "details": [
      {
        "path": ["sessionId"],
        "message": "Invalid uuid"
      },
      {
        "path": ["format"],
        "message": "Invalid enum value..."
      }
    ]
  }
Test 3 (Not found):

Status: 404 Not Found
Response body:

json  {
    "error": "Session not found"
  }
```

**How to Observe:**

**Visual (API tool):**
- Response status code shown in tool
- Response body formatted as JSON
- Response time displayed

**Server Logs (Terminal):**
- Look for:
```
  POST /api/export/session 200 1234ms
```
- Should NOT see:
```
  Error: ...
  Unhandled rejection: ...
Database (Query tool):

Run: SELECT id, frames FROM Session WHERE id = 'your-uuid'
Verify: Session exists with frames
Check: Frame count matches expected export size

Network Tab (if testing from browser):

Open DevTools → Network
See POST request to /api/export/session
Status: 200
Response: JSON object
Timing: Response time shown

Pass Criteria:

 Valid request returns 200 with all 3 fields (downloadUrl, expiresAt, fileSize)
 downloadUrl is string (not null/undefined)
 expiresAt is valid ISO date string
 fileSize is positive integer
 Invalid sessionId returns 400 with validation details
 Invalid format returns 400 with validation details
 Non-existent session returns 404
 Server logs show no errors
 Response time < 5 seconds for typical session
 No console errors or unhandled rejections

Common Failures & Fixes:
If API returns 500 "Export failed":

Check #1: Server logs for error details

Look for: Stack trace in terminal
Common cause: Database connection error
Fix: Verify DATABASE_URL in .env.local, restart dev server


Check #2: Database connection

Test: npx prisma db push should succeed
If fails: Database not running or wrong credentials
Fix: Start database: docker-compose up db or check connection string


Check #3: generateExport function exists

Look for: Cannot find module or undefined is not a function
Cause: Next step not completed yet
Fix: Either create mock or complete next step first



If API returns 404 but session should exist:

Check #1: Session ID is correct UUID format

Test: Should match pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Fix: Get valid ID from database


Check #2: Session actually exists in database

Query: SELECT * FROM Session WHERE id = 'your-uuid'
If empty: Use different ID or seed data
Fix: Run npm run db:seed to populate test data


Check #3: Database schema is up to date

Test: npx prisma migrate status
If pending: Run npx prisma migrate dev
Fix: Apply migrations



If API returns 400 but request looks valid:

Check #1: JSON body is valid

Use: JSON validator (jsonlint.com)
Common: Trailing comma, missing quote
Fix: Copy example body exactly


Check #2: Field types match schema

sessionId: Must be string with UUID format
format: Must be exactly "csv", "json", or "xlsx" (case-sensitive)
includeMetadata: Must be boolean (true/false, not "true"/"false")
Fix: Match types exactly


Check #3: No extra fields

Zod schema is strict
Extra fields cause validation error
Fix: Remove any fields not in schema



If request hangs/times out:

Check #1: Dev server is running

Terminal should show: "Ready on http://localhost:3000"
Fix: Run npm run dev


Check #2: Session has reasonable size

Query: SELECT COUNT(*) FROM Frame WHERE sessionId = 'your-uuid'
If > 50k: Will be slow, might timeout
Fix: Use session with fewer frames for testing


Check #3: Database query is slow

Enable query logging in Prisma
Check: Query duration in logs
Fix: Add database index if needed (future optimization)



If Network tab shows CORS error:

Should not happen: API and frontend are same domain

If it does: Server configuration issue
Fix: Check Next.js version, restart dev server



If downloadUrl is returned but file doesn't exist:

This step only: Returns URL, doesn't verify file

This is expected at this stage
File creation happens in generateExport (next step)
Verification: Full end-to-end test after next step



Debugging tips:

Add detailed logging:

typescript   console.log('Request body:', body);
   console.log('Validated:', validated);
   console.log('Session found:', !!session);
   console.log('Export result:', exportData);

Test with curl (eliminates tool issues):

bash   curl -X POST http://localhost:3000/api/export/session \
     -H "Content-Type: application/json" \
     -d '{"sessionId":"your-uuid","format":"csv","includeMetadata":true}'

Check Prisma Client generated:

bash   npx prisma generate

Reset database if schema mismatch:

npx prisma migrate reset
   npx prisma db seed
```

**Time estimate for this step:** 2.5 hours
- Code writing: 45 minutes
- Initial testing: 30 minutes
- Debugging issues: 45 minutes
- Documentation: 30 minutes
```

---

### C. Step Template (Non-Critical Steps)

**For NON-CRITICAL steps (no code review needed), use simpler template:**
```markdown
#### 🟥 Step X.Y: [Specific, actionable step name]

**What:** [One sentence: what we're building/changing]

**Why:** [One sentence: why this is needed]

**Files:**
- **Create/Modify:** `path/to/file.tsx`
- **Depends on:** Step X.Y (must complete first)

**Subtasks:**
- [ ] 🟥 Subtask 1: _____
- [ ] 🟥 Subtask 2: _____
- [ ] 🟥 Subtask 3: _____
- [ ] 🟥 Subtask 4: _____
- [ ] 🟥 Subtask 5: _____

[At least 3-5 subtasks that are concrete and specific]

**✓ Verification Test:**

[Full verification test with same structure as critical steps]
- Setup prerequisites
- Actions to take
- Expected results
- How to observe
- Pass criteria (5+ checkboxes)
- Common failures & fixes (3+ scenarios)

**Time estimate:** _____ hours (_____ min per subtask × ___ subtasks + ___ min buffer)
```

---

### D. Critical vs Non-Critical Decision Framework

**Determine which steps need full code review:**

**CRITICAL steps (need code review WITH code):**
- ✅ New API endpoints
- ✅ Database schema changes
- ✅ Authentication/authorization logic
- ✅ State management setup (Context, Redux)
- ✅ Security-sensitive code (validation, sanitization)
- ✅ Complex algorithms or business logic
- ✅ Third-party API integrations
- ✅ New architectural patterns
- ✅ Performance-critical code
- ✅ Breaking changes to existing APIs

**NON-CRITICAL steps (verification test only):**
- ❌ Simple UI components (buttons, cards)
- ❌ Styling/CSS changes
- ❌ Adding imports
- ❌ Copy-pasting existing patterns
- ❌ Console logs or comments
- ❌ Simple utility functions (< 10 lines)
- ❌ Type definitions (unless complex)
- ❌ Test file creation (until you write tests)

**For your feature, classify each step:**

| Step | Type | Critical? | Reason |
|------|------|-----------|--------|
| 1.1: Create API endpoint | Backend | ✅ Yes | New API, needs review for security/patterns |
| 1.2: Create types | Types | ❌ No | Simple interface definitions |
| 1.3: Create Button component | UI | ❌ No | Standard React component pattern |
| 1.4: Add state management | State | ✅ Yes | New Context affects data flow |
| 1.5: Style the modal | CSS | ❌ No | Just styling, no logic |
[All steps classified]

**Summary:**
- Critical steps: _____ (need full code + explanation)
- Non-critical steps: _____ (need verification test only)

---

### E. Write All Steps for All Phases

**Now write every single step following the templates above.**

---

## Phase 1 — [Phase Name]

**Goal:** [What users can do after this phase]

**Why this phase first:** [Rationale for ordering]

**Time Estimate:** _____ hours (sum of all step estimates)

**Risk Level:** 🟢/🟡/🔴 (___%)

**Risk reasoning:** _____

**Delivered value:** _____

---

#### 🟥 Step 1.1: [Name] — *Critical: [Reason]*

[Full critical step template if critical]
[Full non-critical template if not critical]

**Time estimate:** _____ hours

---

#### 🟥 Step 1.2: [Name] — *Critical: [Reason]*

[Template]

**Time estimate:** _____ hours

---

[Continue for ALL steps in Phase 1]

---

#### 🟥 Step 1.N: [Name]

[Template]

**Time estimate:** _____ hours

---

**Phase 1 Total Time:** _____ hours (sum of all steps)

**Phase 1 Completion Criteria:**
- [ ] All steps 1.1 through 1.N completed
- [ ] All verification tests pass
- [ ] No blocking issues
- [ ] Ready for Phase 2

---

## Phase 2 — [Phase Name]

**Goal:** [What users can do after this phase]

**Why this phase second:** [Rationale]

**Time Estimate:** _____ hours

**Risk Level:** 🟢/🟡/🔴 (___%)

---

#### 🟥 Step 2.1: [Name]

[Template]

**Time estimate:** _____ hours

---

[Continue for ALL steps in Phase 2]

---

## Phase 3 — [Phase Name]

[Same structure]

---

## Phase N — [Phase Name]

[Same structure]

---

**Quality gate for step definition:**
- [ ] Every phase has 10-30 steps
- [ ] Every step is atomic and specific
- [ ] Every step has verification test
- [ ] Critical steps have full code examples
- [ ] Critical steps have risk analysis
- [ ] Critical steps have failure modes documented
- [ ] Non-critical steps have subtasks and verification
- [ ] Time estimates for every step
- [ ] Dependencies clear
- [ ] Spent at least 60 minutes
- [ ] Written at least 5000 words + extensive code

**Your complete step definitions (minimum 5000 words + code):**
```
[Write all phases and steps]
```

---

## 🧠 THINKING CHECKPOINT #2 (15 minutes minimum)

**Stop. Review all your steps.**

### Step Quality Check

**For 5 random steps, check:**

**Step #___:**
- [ ] Is it atomic? (one clear action)
- [ ] Is it specific? (no vagueness)
- [ ] Has verification test? (with pass criteria)
- [ ] Has time estimate? (realistic)
- [ ] Dependencies clear? (can do now or blocked)
- If critical: Has code example?
- If critical: Has risk analysis?

**Repeat for 4 more steps.**

### Completeness Check

**Count your outputs:**
- Total phases: _____
- Total steps: _____
- Steps per phase: _____ (should be 10-30)
- Critical steps: _____
- Non-critical steps: _____
- Code examples: _____ (should equal critical steps)
- Verification tests: _____ (should equal total steps)

**If any number seems off, investigate.**

### Dependency Validation

**Pick 3 steps and trace backward:**

**Step X.Y:**
- Depends on: Step _____
- Which depends on: Step _____
- Which depends on: Step _____
- Chain makes sense? Yes/No

**Do any steps have circular dependencies?**
- Step ___ depends on Step ___ which depends on Step ___

### Time Sanity Check

**Add up all step estimates:**
- Phase 1: _____ hours
- Phase 2: _____ hours
- Phase 3: _____ hours
- **Total: _____ hours**

**Reality check:**
- Best case (0.8x): _____ hours
- Realistic (1.0x): _____ hours
- Worst case (1.5x): _____ hours

**Does this match issue estimate?**
- Issue estimated: _____ hours
- Plan totals: _____ hours
- Difference: _____ hours
- Acceptable? Yes/No
- If No, what to adjust: _____

### Implementation Preview

**Imagine implementing this plan:**

1. **What's the first thing you'd do?**
   - Step: _____
   - Clear what to do? Yes/No
   - Have all info needed? Yes/No

2. **What's the scariest step?**
   - Step: _____
   - Why scary: _____
   - Prepared for it? Yes/No

3. **Where might you get stuck?**
   - Step: _____
   - Why stuck: _____
   - Is this documented? Yes/No

**Quality gate:** Spend 15+ minutes, write 500+ words.

---

## 3. Pre-Flight Checklist (15 minutes minimum)

**Create environment setup checklist for each phase.**

### Phase 1 Prerequisites

**Before starting Phase 1, verify:**

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Node.js v18+ | Run `node --version` → should show v18.x.x or higher | Install from nodejs.org |
| npm v9+ | Run `npm --version` → should show v9.x.x or higher | Comes with Node 18+ |
| Dependencies installed | Run `npm list --depth=0` → no missing | Run `npm install` |
| Database running | Run `npx prisma db pull` OR check localhost:5432 | Start with `docker-compose up db` |
| Database schema applied | Run `npx prisma migrate status` → "No pending migrations" | Run `npx prisma migrate dev` |
| Environment variables set | Check `.env.local` has: DATABASE_URL, API_KEY, etc. | Copy from `.env.example`, fill values |
| Sample data exists | Query: `SELECT COUNT(*) FROM Session` → > 0 | Run `npm run db:seed` |
| Dev server starts | Run `npm run dev` → "Ready on http://localhost:3000" | Check for errors, install dependencies |
| Browser DevTools | Open localhost:3000 → F12 opens DevTools | Install Chrome/Firefox |
| API testing tool | Postman/Thunder Client/curl installed | Install tool of choice |
| Code editor | VS Code or similar with TypeScript support | Install VS Code |
| Git configured | Run `git config user.name` → returns name | Configure git |

**Checkpoint:** ⬜ All Phase 1 prerequisites met

### Phase 2 Prerequisites

**Before starting Phase 2:**

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1 complete | All Phase 1 verification tests pass | Complete Phase 1 |
| Phase 1 code committed | Run `git status` → working tree clean | Commit Phase 1 work |
| [Specific dependency] | [How to check] | [How to install] |
| [Specific dependency] | [How to check] | [How to install] |

**Checkpoint:** ⬜ All Phase 2 prerequisites met

### Phase 3 Prerequisites

[Same structure]

### Phase N Prerequisites

[Same structure]

**Quality gate for this section:**
- [ ] Checklist for every phase
- [ ] At least 5 items per phase
- [ ] Each item has verification method
- [ ] Each item has fix if missing
- [ ] Spent at least 15 minutes

**Your pre-flight checklists:**
```
[Complete checklists for all phases]
```

---

## 4. Risk Heatmap (10 minutes minimum)

**Map where implementation will likely get stuck.**

### Risk Assessment Table

**For EACH phase, identify top risks:**

| Phase | Step | Risk Description | Probability | Impact | Detection Signal | Mitigation |
|-------|------|------------------|-------------|--------|------------------|------------|
| 1 | 1.2 | Database query timeout on large sessions | 🟡 40% | High | Query takes >5s in dev | Add pagination, limit query scope |
| 1 | 1.5 | SSR hydration error using window object | 🔴 70% | High | Console: "Hydration failed" | Use dynamic import with ssr: false |
| 2 | 2.3 | Race condition on rapid clicks | 🟡 50% | Medium | Multiple API calls in Network tab | Add debounce and loading state |
| 2 | 2.7 | Browser blocks large file download | 🟡 45% | High | File doesn't download, no error | Stream download, show progress |
| 3 | 3.2 | Styling breaks on mobile < 375px | 🟡 30% | Low | Layout overflow on iPhone SE | Test responsive at 320px |

**Continue for ALL phases...**

**Risk color coding:**
- 🔴 High (> 60% probability or Critical impact)
- 🟡 Medium (30-60% probability or High impact)
- 🟢 Low (< 30% probability or Medium/Low impact)

### Risk Priority

**Top 5 risks to address proactively:**

1. **Risk:** [Most critical risk]
   - **Phase.Step:** X.Y
   - **Why critical:** _____
   - **Proactive mitigation:** _____
   - **Backup plan:** _____

2. **Risk:** [Second critical]
   [Same]

3. **Risk:** [Third critical]
   [Same]

4. **Risk:** [Fourth critical]
   [Same]

5. **Risk:** [Fifth critical]
   [Same]

### Early Warning System

**How to detect problems early:**

**Daily checks during implementation:**
- [ ] Run all verification tests daily
- [ ] Check console for new warnings
- [ ] Monitor network requests for slowness
- [ ] Review git diff for unexpected changes
- [ ] Test in multiple browsers weekly

**Red flags to watch for:**
- 🚩 Step taking 2x estimated time → Reassess approach
- 🚩 Multiple verification test failures → Something wrong with foundation
- 🚩 Constant debugging with no progress → Need help or different approach
- 🚩 Adding "TODO" or "FIXME" comments → Cutting corners
- 🚩 Skipping verification tests → Quality slipping

**Quality gate for this section:**
- [ ] Risk identified for each phase
- [ ] Top 5 risks prioritized
- [ ] Detection signals defined
- [ ] Mitigation strategies documented
- [ ] Early warning system created
- [ ] Spent at least 10 minutes

**Your risk heatmap:**
```
[Complete risk documentation]
```

---

## 5. Success Criteria (10 minutes minimum)

**Define what "done" means for the entire feature.**

### End-to-End Success Criteria

**After ALL phases complete, these must be true:**

| # | Feature Requirement | Target Behavior | Verification Method | Priority |
|---|---------------------|----------------|---------------------|----------|
| 1 | User can export session | Click export → select format → receive download | **Test:** Open /session/123 → Click "Export" → Choose "CSV" → **Expect:** File downloads with name `session-123-2024-12-31.csv` → **Pass:** File exists, contains session data in CSV format, opens in Excel | 🔴 P0 |
| 2 | Export handles large sessions | 10k+ frames export without hanging | **Test:** Export session with 15k frames → **Expect:** Progress bar shows, file downloads in <30s → **Pass:** No browser freeze, file complete and parseable | 🔴 P0 |
| 3 | Errors are user-friendly | Failed export shows clear message | **Test:** Export non-existent session → **Expect:** Toast: "Session not found" → **Pass:** Error specific, not generic "Something went wrong" | 🟡 P1 |
| 4 | Export includes correct data | CSV has all frames with timestamps | **Test:** Open CSV → **Expect:** Row count = frame count, columns: timestamp, data, metadata → **Pass:** Data matches UI, no missing fields | 🔴 P0 |
| 5 | Format selection works | User can choose CSV/JSON/XLSX | **Test:** Click format dropdown → **Expect:** 3 options visible → Select each → **Pass:** Different extensions, data format matches | 🔴 P0 |
| 6 | Keyboard navigation works | Can export using only keyboard | **Test:** Tab to Export → Enter → Tab to format → Enter → **Expect:** Export starts → **Pass:** No mouse needed | 🟡 P1 |
| 7 | Screen reader announces export | Accessible to blind users | **Test:** Enable VoiceOver/NVDA → Tab to button → **Expect:** Announces "Export session data, button" → **Pass:** Clear announcement | 🟡 P1 |
| 8 | Mobile responsive | Works on phones 375px+ | **Test:** Resize to 375px → Click export → **Expect:** Modal fits screen, touch targets 44px+ → **Pass:** No overflow, tappable | 🟡 P1 |
| 9 | Performance is acceptable | Export completes in <10s for typical session | **Test:** Export session with 5k frames → **Expect:** Complete in 5-7s → **Pass:** No perceived lag | 🔴 P0 |
| 10 | No console errors | Clean DevTools console | **Test:** Complete full export flow → **Expect:** Console has no errors/warnings → **Pass:** Clean console | 🔴 P0 |
| 11 | Works in all supported browsers | Chrome, Firefox, Safari | **Test:** Export in each browser → **Expect:** Same behavior → **Pass:** Consistent across browsers | 🟡 P1 |
| 12 | Handles network failures gracefully | Shows error, allows retry | **Test:** Simulate offline (DevTools) → Export → **Expect:** Error: "Connection failed. Try again." → **Pass:** Retry button works | 🟡 P1 |

**Continue for all acceptance criteria from issue...**

### Success Criteria by Priority

**Must have (P0) - Cannot ship without:**
1. _____
2. _____
3. _____
[All P0 criteria]

**Should have (P1) - Can ship without but should fix soon:**
1. _____
2. _____
3. _____
[All P1 criteria]

**Nice to have (P2) - Can defer to later:**
1. _____
2. _____
3. _____
[All P2 criteria]

### Definition of Done Checklist

**Feature is DONE when:**
- [ ] All P0 success criteria pass
- [ ] All P1 success criteria pass (or explicitly deferred with reason)
- [ ] All verification tests from all steps pass
- [ ] Code reviewed and approved
- [ ] No critical or high severity bugs
- [ ] Documentation updated (user-facing and developer-facing)
- [ ] Changelog entry written
- [ ] Deployed to staging and tested
- [ ] Performance benchmarks met
- [ ] Accessibility audit passed
- [ ] Security review passed (if applicable)
- [ ] Product owner accepts feature
- [ ] Analytics/monitoring in place

**Quality gate for this section:**
- [ ] At least 12 success criteria defined
- [ ] Each has specific verification method
- [ ] Prioritized (P0/P1/P2)
- [ ] Definition of done checklist complete
- [ ] Spent at least 10 minutes

**Your success criteria:**
```
[Complete success criteria documentation]
```

---

## 🧠 THINKING CHECKPOINT #3 (15 minutes minimum)

**Stop. Final plan review before finishing.**

### Implementability Test

**Give this plan to an imaginary junior developer:**

**Questions they might ask:**
1. Question: _____
   - **Answered in plan:** Yes/No
   - If No, **where to add:** _____

2. Question: _____
   - **Answered in plan:** Yes/No
   - If No, **where to add:** _____

[List at least 10 questions]

**If ANY question is not answered in plan, ADD IT NOW.**

### Completeness Audit

**Count these elements:**

| Element | Required Minimum | Your Count | Pass? |
|---------|-----------------|------------|-------|
| Total phases | 3 | _____ | ⬜ |
| Total steps | 30 | _____ | ⬜ |
| Critical steps with code | 10 | _____ | ⬜ |
| Verification tests | = Total steps | _____ | ⬜ |
| Risk entries | 20 | _____ | ⬜ |
| Success criteria | 12 | _____ | ⬜ |
| Pre-flight items | 5 per phase | _____ | ⬜ |
| Common failure scenarios | 3 per verification | _____ | ⬜ |
| Time estimates | = Total steps | _____ | ⬜ |
| Total words | 10000 | _____ | ⬜ |

**If ANY count is below minimum, ADD MORE.**

### Red Team Exercise

**Attack your own plan. Find 10 problems:**

1. **Problem:** _____
   - **Severity:** Critical/High/Medium/Low
   - **Fix:** _____

2. **Problem:** _____
   [Same]

[Find 10 problems]

**Address each problem in the plan.**

### Time Reality Check

**Total estimated time:** _____ hours

**Realistic scenarios:**
- **Best case (everything goes perfectly):** _____ hours (0.7x)
- **Likely case (normal issues):** _____ hours (1.0x)
- **Worst case (major issues):** _____ hours (1.8x)
- **Disaster case (fundamental problems):** _____ hours (3.0x)

**If disaster case > available time:**
- **Risk:** _____
- **Mitigation:** _____

### Confidence Rating

**On a scale of 1-10:**
- **Plan quality:** ___/10
- **Completeness:** ___/10
- **Implementability:** ___/10
- **Time estimates:** ___/10
- **Risk coverage:** ___/10
- **Overall confidence:** ___/10

**If any rating < 8:**
- **What's weak:** _____
- **How to improve:** _____
- **Go improve it now.**

**Quality gate:** Spend 15+ minutes, write 600+ words, make improvements based on findings.

---

## 6. Progress Tracking System (5 minutes)

**Create tracking table for implementation.**

### Progress Dashboard

**Update this as you implement:**

| Phase | Total Steps | Completed | In Progress | Blocked | % Complete |
|-------|-------------|-----------|-------------|---------|------------|
| Phase 1 | ___ | 0 | 0 | 0 | 0% |
| Phase 2 | ___ | 0 | 0 | 0 | 0% |
| Phase 3 | ___ | 0 | 0 | 0 | 0% |
| **TOTAL** | **___** | **0** | **0** | **0** | **0%** |

### Status Definitions

- **🟩 Completed:** Verification test passed
- **🟨 In Progress:** Started but not verified
- **🟥 Blocked:** Cannot proceed, dependency missing
- **⬜ Not Started:** Hasn't been started yet

### Daily Standup Template

**Copy this for daily updates:**
```
Date: ____

Yesterday:
- Completed: Step X.Y (description)
- Completed: Step X.Z (description)

Today:
- Working on: Step A.B (description)
- Estimated completion: ___ hours

Blockers:
- [None / Blocker description]

Risks:
- [None / Risk that materialized / New risk discovered]

Notes:
- [Any learnings, issues, or observations]

Overall progress: ___% complete
On track: Yes/No
If No, plan to get back on track: _____
```

### Velocity Tracking

**After Phase 1, calculate velocity:**

- **Estimated time:** ___ hours
- **Actual time:** ___ hours
- **Velocity factor:** Actual / Estimated = ___

**Use to adjust remaining estimates:**
- **Phase 2 original estimate:** ___ hours
- **Phase 2 adjusted:** ___ hours × velocity factor = ___ hours
- **Phase 3 original estimate:** ___ hours
- **Phase 3 adjusted:** ___ hours × velocity factor = ___ hours

---

## 7. Implementation Notes Section

**Template for capturing learnings during implementation.**

### Notes Template

**Step X.Y - [Name]:**

**Date:** ____

**Time taken:** ___ hours (estimated: ___ hours, difference: ___ hours)

**What went well:**
- _____
- _____

**What went poorly:**
- _____
- _____

**Unexpected challenges:**
- Challenge: _____
  - How resolved: _____
  - Time added: ___ hours

**Technical debt introduced:**
- Debt: _____
  - Reason: _____
  - Impact: _____
  - Should fix: Yes/No, When: _____

**Lessons learned:**
- Lesson: _____
  - Apply to: Step ___, Step ___

**Ideas for future improvements:**
- Idea: _____
  - Priority: High/Medium/Low

---

## Quality Metrics (Must Meet Before Submitting Plan)

**Final quality gate - check ALL boxes:**

### Depth Metrics

| Metric | Minimum | Your Count | Pass? |
|--------|---------|------------|-------|
| Total words | 10,000 | _____ | ⬜ |
| Planning time (minutes) | 180 | _____ | ⬜ |
| Phases | 3 | _____ | ⬜ |
| Total steps | 30 | _____ | ⬜ |
| Critical steps | 10 | _____ | ⬜ |
| Code examples | = Critical steps | _____ | ⬜ |
| Verification tests | = Total steps | _____ | ⬜ |
| Common failures documented | 3 per verification | _____ | ⬜ |
| Risk entries | 20 | _____ | ⬜ |
| Success criteria | 12 | _____ | ⬜ |
| Pre-flight checklist items | 5 per phase | _____ | ⬜ |
| Thinking checkpoints completed | 3 | _____ | ⬜ |
| Thinking checkpoint words | 1400 | _____ | ⬜ |

**CRITICAL: If ANY metric below minimum, plan is INCOMPLETE. Add depth before submitting.**

### Content Quality Checklist

**Structure:**
- [ ] All phases have clear goals
- [ ] All phases have user-facing value
- [ ] All steps are atomic and specific
- [ ] All steps have time estimates
- [ ] All steps have verification tests
- [ ] Critical steps have code examples
- [ ] Critical steps have risk analysis
- [ ] Dependencies are clear
- [ ] Pre-flight checklists complete
- [ ] Risk heatmap comprehensive
- [ ] Success criteria measurable

**Verification Tests:**
- [ ] Every step has verification test
- [ ] Every test has setup prerequisites
- [ ] Every test has actions to take
- [ ] Every test has expected results
- [ ] Every test has how to observe
- [ ] Every test has 5+ pass criteria
- [ ] Every test has 3+ common failures with fixes

**Code Quality:**
- [ ] Critical steps have full code (not pseudocode)
- [ ] Code has imports, types, implementation
- [ ] Code has error handling
- [ ] Code has comments
- [ ] Code follows existing patterns
- [ ] Code is production-ready

**Risk Coverage:**
- [ ] 20+ risks identified
- [ ] Each risk has probability
- [ ] Each risk has impact
- [ ] Each risk has detection signal
- [ ] Each risk has mitigation
- [ ] Top 5 risks prioritized

**Time Estimates:**
- [ ] Every step has estimate
- [ ] Estimates have breakdown
- [ ] Estimates are realistic (not best-case)
- [ ] Total time calculated
- [ ] Matches issue estimate (or explained why different)

**Thinking Depth:**
- [ ] Pre-planning thinking completed (30+ min)
- [ ] Thinking checkpoint #1 completed (10+ min)
- [ ] Thinking checkpoint #2 completed (15+ min)
- [ ] Thinking checkpoint #3 completed (15+ min)
- [ ] Red team exercise completed (10 problems found)
- [ ] Implementability test completed (10 questions)

### Self-Critique Questions

**Answer honestly:**

1. **Could a junior engineer implement this plan?**
   - Yes/No
   - If No, what's missing: _____

2. **Could someone implement without asking questions?**
   - Yes/No
   - If No, what's unclear: _____

3. **Are time estimates realistic?**
   - Yes/No
   - If No, what's under-estimated: _____

4. **Are all risks identified?**
   - Yes/No
   - If No, what's missing: _____

5. **Is every step verifiable?**
   - Yes/No
   - If No, which steps lack tests: _____

6. **Did I spend 180+ minutes planning?**
   - Yes/No
   - If No, I need to add more depth

7. **Did I challenge my own plan?**
   - Yes/No
   - If No, do red team exercise now

8. **Are all code examples production-ready?**
   - Yes/No
   - If No, which need improvement: _____

9. **Would I be confident implementing this?**
   - Yes/No
   - If No, what's concerning: _____

10. **Is this 5X better than a typical plan?**
    - Yes/No
    - If No, what's missing: _____

**If ANY answer is "No", improve plan before submitting.**

### The Reality Test

**Give this plan to an imaginary experienced engineer and ask:**

"Can you implement this without asking me anything?"

**If they say No, they'd ask:**
1. Question: _____
2. Question: _____
3. Question: _____

**Add answers to plan NOW.**

### The Bus Factor Test

**If you got hit by a bus tomorrow:**

"Could someone else pick up this plan and continue?"

**What they'd need to know:**
1. _____
2. _____
3. _____

**Add to plan NOW.**

---

## Final Reminders

### 🎯 Success Criteria for This Plan

**This plan is successful if:**
- [ ] Takes 180+ minutes to create
- [ ] Contains 10,000+ words
- [ ] Has 30+ steps with verification tests
- [ ] Has 10+ critical steps with full code
- [ ] Has 20+ risks identified
- [ ] Has 12+ success criteria
- [ ] Someone else can implement without questions
- [ ] You'd be confident giving this to a junior engineer
- [ ] All quality metrics met
- [ ] All self-critique questions answered Yes

### 🚫 Warning Signs of a Bad Plan

**Your plan is too shallow if:**
- ❌ Created in < 90 minutes
- ❌ < 5000 words
- ❌ Steps like "implement feature X" (too vague)
- ❌ Verification tests like "test that it works" (not specific)
- ❌ No code examples for critical steps
- ❌ No common failure scenarios documented
- ❌ Time estimates are round numbers (10, 20, 30 hours - not realistic)
- ❌ Risks are generic ("might not work")
- ❌ Success criteria are vague ("should be good")
- ❌ You didn't do thinking checkpoints

### 📈 Comparison: Bad vs Good Plan

**❌ BAD PLAN (2000 words, 45 minutes):**
```
Phase 1: Backend
- Step 1: Create API
- Step 2: Add validation
- Step 3: Test it

Phase 2: Frontend  
- Step 4: Add button
- Step 5: Add modal
- Step 6: Test it

Success: Feature works
```

**Why it's bad:**
- Vague steps ("Create API" - which endpoint? what contract?)
- No verification tests
- No code examples
- No risk analysis
- No dependencies
- Can't implement from this

**✅ GOOD PLAN (10000 words, 180 minutes):**
- 30+ atomic, specific steps
- Every step has verification test with 5+ pass criteria
- 10+ critical steps with full code examples
- 20+ risks identified with mitigation
- 12+ success criteria with verification methods
- Pre-flight checklists
- Common failures documented
- Time estimates with breakdown
- Thinking checkpoints completed

**Why it's good:**
- Someone could implement without asking questions
- Verifiable at every step
- Risks are planned for
- Failures are anticipated
- Time is realistic

---

## After Plan Creation

### Immediate Next Steps

1. **[ ] Review plan** with stakeholder/team (30 minutes)
   - Walk through phases
   - Get buy-in on approach
   - Identify any gaps
   
2. **[ ] Set up project tracking** (15 minutes)
   - Create tickets from steps
   - Set up progress dashboard
   - Configure daily standup template
   
3. **[ ] Verify environment** (30 minutes)
   - Check all pre-flight items
   - Resolve any blockers
   - Confirm can start Phase 1
   
4. **[ ] Schedule implementation** (15 minutes)
   - Block time for focused work
   - Account for interruptions
   - Set milestone dates

### Moving to Implementation

**Before starting implementation:**
- [ ] This plan is complete (all quality gates passed)
- [ ] Plan is reviewed and approved
- [ ] Environment is set up (pre-flight complete)
- [ ] Calendar is blocked
- [ ] Ready to focus

**During implementation:**
- [ ] Follow steps in order
- [ ] Run verification test after each step
- [ ] Update progress dashboard daily
- [ ] Take notes on learnings
- [ ] Ask for help if stuck >2 hours
- [ ] Don't skip steps or verification tests

**Remember:**
- This plan is a living document
- If reality diverges, UPDATE THE PLAN
- Don't stubbornly follow a plan that's wrong
- Capture learnings as you go
- Adjust estimates based on velocity

---

## 🎯 FINAL QUALITY GATE

**Before submitting plan, verify:**

- [ ] I spent at least 180 minutes creating this plan
- [ ] I wrote at least 10,000 words
- [ ] I have at least 30 steps across 3+ phases
- [ ] Every step has a verification test
- [ ] 10+ critical steps have full code examples
- [ ] I documented 20+ risks
- [ ] I defined 12+ success criteria
- [ ] I completed all 3 thinking checkpoints
- [ ] I did red team exercise (found 10 problems)
- [ ] I did implementability test (asked 10 questions)
- [ ] All quality metrics met
- [ ] Someone else could implement without asking questions
- [ ] I would give this to a junior engineer confidently

**If ANY checkbox is unchecked:**
🛑 **STOP. Go back and improve the plan.**

**Remember:** A great plan makes implementation feel easy. If you're confused during implementation, the plan wasn't detailed enough.

---

**The 5X Difference:**

**Typical plan:** 2000 words, 45 minutes, vague steps, no verification
→ Confused implementation, constant questions, rework, frustration

**5X plan:** 10000 words, 180 minutes, atomic steps, full verification
→ Clear implementation, no questions, smooth progress, success

**The investment is worth it.**