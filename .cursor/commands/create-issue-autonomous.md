# Create Issue (Deep Capture Mode) - ENHANCED VERSION

**Time Budget:** 30-45 minutes MINIMUM for comprehensive issue capture.
**If you finish in less than 30 minutes, you rushed. Go back and add depth.**

**Context:** You're mid-development and thought of a bug/feature/improvement. This is the FIRST step in your workflow - we need to capture it thoroughly so exploration and planning can proceed without gaps.

**Your Mission:** Create a complete, detailed issue specification that provides enough context for deep exploration later. This isn't just a quick note - it's the foundation for everything that follows.

---

## Phase 0: Understand the Workflow Position

**This is Step 1 of 3:**
1. **Create Issue** ← You are here (capture the WHAT and WHY)
2. **Explore Feature** (deep dive into HOW)
3. **Create Plan** (step-by-step implementation)

**Your job right now:**
- Capture the problem/idea completely
- Provide enough context for exploration
- Document what you know (and what you don't)
- Set clear boundaries and expectations
- Think deeply about implications
- Question your own assumptions

**NOT your job right now:**
- Figure out implementation details (that's exploration)
- Write code snippets (that's planning)
- Solve edge cases (that's exploration)

---

## MANDATORY PRE-ISSUE THINKING SESSION (15 minutes minimum)

**🛑 STOP. Before writing anything, spend 15 minutes on raw thinking.**

### A. Brain Dump (5 minutes minimum)

**Write stream-of-consciousness. No filtering. Just think.**

Questions to spark thinking:
- What exactly is wrong/missing?
- Why does this matter?
- What prompted this thought?
- What are we assuming?
- What could go wrong?
- What don't we know?
- What's the simplest version?
- What's the complete version?
- Who is affected?
- What's the urgency?

**Write at least 300 words of raw thinking here:**
```
[Your brain dump - write continuously for 5 minutes]
```

**Quality gate:** If you wrote less than 300 words, you didn't think deeply enough. Keep writing.

### B. Question Storm (5 minutes minimum)

**List every question you can think of about this issue. Aim for 20+.**

Examples:
- What triggers this?
- When does it happen?
- Who experiences this?
- How often does it occur?
- What's the impact if we don't fix it?
- What's the impact if we do?
- What are we assuming about user behavior?
- What are we assuming about the system?
- What similar issues have we had?
- What did we learn from those?

**Your questions (minimum 20):**
1. _____
2. _____
3. _____
[... continue to 20+]

**Quality gate:** If you have fewer than 20 questions, keep thinking.

### C. Five Whys Analysis (5 minutes minimum)

**Dig into the root cause. Ask "why" 5 times.**

**Problem:** [State the surface problem]

**Why #1:** Why is this a problem?
- Answer: _____

**Why #2:** Why is that a problem?
- Answer: _____

**Why #3:** Why is that a problem?
- Answer: _____

**Why #4:** Why is that a problem?
- Answer: _____

**Why #5:** Why is that the real problem?
- Answer: _____ (This is likely the root cause)

**Root cause identified:** _____

---

## Required Information Gathering (15+ minutes)

### 1. Understand the Request (10+ minutes)

**Have a conversation. This is a dialogue, not a form.**

#### Core Understanding Questions

**Ask the user (conversationally):**

**About the What:**
- "Can you describe exactly what's happening (or what you want to happen)?"
- "What specific behavior are you seeing?"
- "What specific behavior do you want to see instead?"
- "Can you give me a concrete example?"
- "Walk me through a scenario where this matters"

**About the Why:**
- "Why is this important right now?"
- "What's the impact if we don't do this?"
- "Who is asking for this?"
- "What's driving the urgency?"
- "How does this align with our product goals?"

**About the Who:**
- "Who is affected by this?"
- "Is it all users, or specific types?"
- "Internal team or external customers?"
- "Power users or casual users?"

**About the When:**
- "Does this happen every time, or only sometimes?"
- "Are there specific conditions?"
- "What triggers this?"
- "When did we first notice this?"

**About the Context:**
- "How did we discover this?"
- "What are users doing as a workaround?"
- "Are there related issues?"
- "What have we tried before?"
- "Why didn't previous solutions work?"

**About the Scope:**
- "What must be included?"
- "What's explicitly out of scope?"
- "Any design requirements?"
- "Any technical constraints?"
- "Any performance requirements?"
- "Any security concerns?"

**About Success:**
- "How do we know when this is done?"
- "What can users do that they couldn't before?"
- "How do we test this?"
- "What does good look like?"

**🚩 Red flags that you need more info:**
- User says "just make it better" (better how? be specific)
- User says "you know what I mean" (no, I need specifics)
- User gives implementation before problem (ask WHY they want that solution)
- User says "it's broken" (broken how? what's the symptom?)
- User is vague about priority (force them to choose)
- User hasn't thought about edge cases (explore together)

**Document the conversation:**
```
[User's initial request]

[Your questions and their answers - write out the full dialogue]

[Clarifications obtained]

[Remaining ambiguities]
```

**Quality gate:** If the conversation feels rushed or you still have big questions, keep asking.

### 2. Search for Context (10+ minutes)

**Find relevant existing code and patterns.**

#### Codebase Search

Run these searches and document what you find:
```bash
# Find related features
grep -r "relevant_keyword" src/ --include="*.ts" --include="*.tsx" -l

# Find similar components  
find src/components -name "*Similar*" -type f

# Check for existing patterns
grep -r "export.*function.*similar" src/ -l

# Look for related types
grep -r "interface.*Related" src/types/

# Find related API routes
find src/app/api -name "*related*" -type f

# Check for related utilities
find src/utils -name "*similar*" -type f

# Look for related tests
find __tests__ -name "*related*" -type f
```

**Document findings (be specific):**

**Similar existing features found:**
1. Feature/Component: `path/to/feature.tsx`
   - What it does: _____
   - Relevant patterns: _____
   - What we can reuse: _____
   - What we should avoid: _____

2. Feature/Component: `path/to/another.tsx`
   - What it does: _____
   - Relevant patterns: _____
   - What we can reuse: _____
   - What we should avoid: _____

[List at least 3-5 similar features]

**Existing patterns to follow:**
1. Pattern: _____ (found in: _____)
   - Why it's good: _____
   - How to apply: _____

2. Pattern: _____ (found in: _____)
   - Why it's good: _____
   - How to apply: _____

**Anti-patterns to avoid:**
1. Anti-pattern: _____ (found in: _____)
   - Why it's bad: _____
   - What to do instead: _____

**Related components/utilities:**
- Component: _____ at `path` - Purpose: _____
- Utility: _____ at `path` - Purpose: _____
- Hook: _____ at `path` - Purpose: _____

**Data models/types that exist:**
- Type: _____ at `path` - Structure: _____
- Interface: _____ at `path` - Structure: _____

#### Documentation Search

Check these and document findings:

- [ ] `CONTEXT.md` - Relevant sections: _____
- [ ] `ARCHITECTURE.md` - Relevant sections: _____
- [ ] `README.md` - Relevant sections: _____
- [ ] `PRD.md` or product docs - Relevant sections: _____
- [ ] API documentation - Relevant sections: _____
- [ ] Component documentation - Relevant sections: _____

**Key insights from documentation:**
1. _____
2. _____
3. _____

**Quality gate:** If you haven't found at least 3 similar features or patterns, search more broadly.

### 3. Web Research (if applicable, 10+ minutes)

**Search for best practices when:**
- Complex technical approach (algorithms, security, performance)
- Common UI/UX pattern (accessibility, responsive design)
- Integration with external services
- You're unsure of the "standard" way to solve this

**Research queries to run:**
1. "[Feature] best practices [Year]"
2. "[Technology] [pattern name] implementation guide"
3. "[Library] [feature] examples"
4. "Common mistakes [feature type]"
5. "[Feature] accessibility requirements"
6. "[Feature] security considerations"

**Document findings:**

**Key approaches found:**
1. Approach: _____
   - Source: _____
   - Description: _____
   - Pros: _____
   - Cons: _____
   - Applicability to our case: _____

2. Approach: _____
   - Source: _____
   - Description: _____
   - Pros: _____
   - Cons: _____
   - Applicability to our case: _____

[List at least 3 approaches]

**Standards to follow:**
- Standard: _____ (e.g., WCAG 2.1, REST conventions)
  - Requirements: _____
  - How to verify compliance: _____

**Libraries commonly used:**
- Library: _____ (version: _____)
  - What it does: _____
  - Pros: _____
  - Cons: _____
  - Trade-offs: _____

**Common pitfalls found:**
1. Pitfall: _____
   - Why it happens: _____
   - How to avoid: _____

2. Pitfall: _____
   - Why it happens: _____
   - How to avoid: _____

**Quality gate:** If this is a complex feature and you haven't researched, do it now.

---

## 🧠 THINKING CHECKPOINT #1 (10 minutes minimum)

**Stop. Do not write the issue until you answer these.**

### 1. What am I assuming that might be wrong?

List at least 5 assumptions:

1. **Assumption:** _____
   - **If wrong:** _____ breaks
   - **How to verify:** _____
   - **Likelihood it's wrong:** Low/Medium/High
   - **Impact if wrong:** Low/Medium/High

2. **Assumption:** _____
   - **If wrong:** _____ breaks
   - **How to verify:** _____
   - **Likelihood it's wrong:** Low/Medium/High
   - **Impact if wrong:** Low/Medium/High

[Continue to 5+ assumptions]

### 2. What questions would a skeptical engineer ask?

List at least 10 questions:

1. _____
2. _____
3. _____
[... to 10+]

**Now answer each question:**
1. Q: _____ A: _____
2. Q: _____ A: _____
[... all 10+]

### 3. What am I not seeing?

**Edge cases I haven't considered:**
1. _____
2. _____
3. _____
[At least 5]

**Failure modes I haven't thought about:**
1. _____
2. _____
3. _____
[At least 5]

**Dependencies I might have missed:**
1. _____
2. _____
3. _____
[At least 3]

### 4. Explain this to a junior developer

**Rewrite your understanding in simple terms (200+ words):**
```
Imagine you're explaining this to someone who just joined the team...

[Write explanation]
```

**Quality gate:** If your explanation is less than 200 words or uses jargon, simplify it.

### 5. Red team this issue

**Try to break your own thinking. Find problems.**

**Problem 1:** _____
- Why it's a problem: _____
- Impact: _____
- Mitigation: _____

**Problem 2:** _____
- Why it's a problem: _____
- Impact: _____
- Mitigation: _____

[Find at least 5 problems]

**Quality gate:** You must spend at least 10 minutes on this checkpoint and write at least 500 words total.

---

## Issue Structure (Complete ALL Sections)

### 1. Title (Clear and Specific)

**Format:** `[Type] Brief, specific description (not more than 100 chars)`

**Types:**
- `[Bug]` - Something broken that should work
- `[Feature]` - New functionality
- `[Improvement]` - Enhancement to existing feature
- `[Refactor]` - Code cleanup/restructuring without user-facing changes
- `[Docs]` - Documentation updates
- `[Performance]` - Speed/efficiency improvements
- `[Security]` - Security fixes/enhancements
- `[A11y]` - Accessibility improvements

**Title Quality Checklist:**
- [ ] Starts with type tag
- [ ] Specific (not vague like "fix export")
- [ ] Under 100 characters
- [ ] No jargon (understandable to non-technical stakeholders)
- [ ] Action-oriented (describes what will change)

**Examples:**
- ✅ `[Feature] Add CSV export for session replay data with format selection`
- ✅ `[Bug] Export button crashes when session has 10k+ frames`
- ✅ `[Improvement] Add progress indicator to export modal for large files`
- ✅ `[Performance] Optimize frame serialization to handle 50k+ frame sessions`
- ❌ `[Feature] Export feature` (too vague - what kind of export?)
- ❌ `Fix the export` (no type tag, not specific)
- ❌ `[Bug] Export doesn't work` (too vague - what's broken?)

**Your title:**
```
[Type] _______________________________________________
```

**Title verification:**
- [ ] I checked all boxes above
- [ ] Someone unfamiliar with the project would understand this
- [ ] It's specific enough that I couldn't confuse it with another issue

### 2. TL;DR (Executive Summary)

**5-7 sentences covering:**
1. **What is this?** (one sentence describing the issue/feature)
2. **Why does it matter?** (user impact, business value)
3. **What's the core problem?** (root cause or gap)
4. **What's the current situation?** (what exists now)
5. **What should happen instead?** (desired outcome)
6. **How does this advance our product vision?** (strategic fit)
7. **What's the effort level?** (rough estimate: small/medium/large)

**Quality requirements:**
- [ ] 5-7 sentences (not more, not less)
- [ ] No jargon or technical terms (explain it to a business stakeholder)
- [ ] States the problem before the solution
- [ ] Quantifies impact where possible (X% of users, $Y cost, Z hours saved)
- [ ] Clear prioritization signal (why now vs later)

**Example (GOOD):**
```
Users cannot export their session replay data for offline analysis or 
sharing with team members who don't have accounts (affects 40% of users 
based on survey data). This limits the utility of our replay feature 
for debugging workflows, creating reports, and collaborating with external 
consultants. The core problem is that data is only viewable in our web 
interface, requiring recipients to have accounts and login access, which 
creates friction in enterprise workflows. Currently, users are resorting 
to manual screenshots or screen recordings, which loses the interactive 
frame-by-frame data. We need to add export functionality that generates 
downloadable files (CSV, JSON, or XLSX) containing all session frame data, 
timestamps, and metadata. This aligns with our Q2 vision of making replay 
data portable and integrable with users' existing analysis tools like Excel, 
Tableau, and custom scripts. This is a medium-effort feature (estimated 
12-16 hours) with high user impact (addresses our #1 enterprise feature request).
```

**Example (BAD):**
```
Users want to export data. We should add an export button. This will make 
users happy. It's important because data portability matters. We'll build 
an API endpoint and UI component. Should take a week or so.
```

**Why the bad example is bad:**
- Vague ("users want" - which users? how many?)
- No specifics (what format? what data?)
- No root cause (why can't they export now?)
- No quantifiable impact
- No strategic context
- Vague effort estimate

**Your TL;DR (write 5-7 sentences, minimum 150 words):**
```
[Write your executive summary here]
```

**TL;DR verification:**
- [ ] 5-7 sentences
- [ ] At least 150 words
- [ ] No jargon
- [ ] States problem before solution
- [ ] Quantifies impact
- [ ] Explains strategic fit
- [ ] I could present this to leadership as-is

### 3. Current State (What Exists Today)

**Be exhaustively specific. This section should be a complete audit.**

#### A. What's Already Built

**List every related component, file, and system:**

**UI Components:**
1. Component: `path/to/component.tsx`
   - **What it does:** _____
   - **Current capabilities:** _____
   - **Limitations:** _____
   - **Dependencies:** _____
   - **Last modified:** _____

2. Component: `path/to/another.tsx`
   - **What it does:** _____
   - **Current capabilities:** _____
   - **Limitations:** _____
   - **Dependencies:** _____
   - **Last modified:** _____

[List all relevant components]

**API Endpoints:**
1. Endpoint: `GET /api/path`
   - **What it does:** _____
   - **Request shape:** _____
   - **Response shape:** _____
   - **Auth required:** Yes/No
   - **Rate limited:** Yes/No
   - **Missing:** _____

2. Endpoint: `POST /api/other`
   - **What it does:** _____
   - **Request shape:** _____
   - **Response shape:** _____
   - **Auth required:** Yes/No
   - **Rate limited:** Yes/No
   - **Missing:** _____

[List all relevant endpoints]

**Data Models:**
1. Type/Interface: `InterfaceName` at `path/to/types.ts`
```typescript
   // Show the actual type definition
   interface InterfaceName {
     field1: type;
     field2: type;
   }
```
   - **Purpose:** _____
   - **Used by:** _____
   - **Limitations:** _____

[List all relevant types]

**Utilities/Helpers:**
1. Function: `functionName` at `path/to/utils.ts`
   - **What it does:** _____
   - **Signature:** `(params) => returnType`
   - **Used by:** _____
   - **Relevant for this issue:** _____

[List all relevant utilities]

#### B. Current User Flows

**Document existing flows that are relevant:**

**Flow 1: [Name]**
```
Step 1: User does _____
  ↓
Step 2: System does _____
  ↓
Step 3: User sees _____
  ↓
Current limitation: [What can't happen]
```

**Flow 2: [Name]**
[Same structure]

[Document at least 3 relevant flows]

#### C. Broken/Incomplete User Flows

**List flows that should work but don't:**

1. **Flow:** User wants to _____
   - **Current behavior:** _____
   - **Why it fails:** _____
   - **User workaround:** _____
   - **Frequency:** How often does this happen?
   - **Impact:** What does this cost users?

2. **Flow:** User wants to _____
   - **Current behavior:** _____
   - **Why it fails:** _____
   - **User workaround:** _____
   - **Frequency:** How often does this happen?
   - **Impact:** What does this cost users?

[List at least 3 broken flows]

#### D. Technical Gaps Inventory

**What's missing at a technical level:**

**Frontend gaps:**
- No _____ component
- No _____ hook
- No _____ utility function
- Missing _____ types

**Backend gaps:**
- No _____ endpoint
- No _____ database table/field
- No _____ service/utility
- Missing _____ validation

**Integration gaps:**
- Can't integrate with _____
- Missing _____ library
- No _____ configuration

**Data gaps:**
- Session data not serializable to _____
- Missing _____ metadata
- No _____ tracking

#### E. Current State Evidence

**Provide proof of current state:**
- [ ] Screenshot of current UI: [attach or describe]
- [ ] Example API response: [paste actual JSON]
- [ ] Current database schema: [show relevant parts]
- [ ] Current code snippets: [show key parts]

**Quality gate for this section:**
- [ ] I've listed at least 5 existing components/files with paths
- [ ] I've documented at least 3 user flows
- [ ] I've identified at least 5 technical gaps
- [ ] I've provided evidence (screenshots, code, data)
- [ ] Someone else could understand the current state without asking questions

**Your current state (write at least 500 words):**
```
[Complete audit of current state]
```

### 4. Desired Outcome (What Should Happen)

**Be explicit and exhaustive about the end state.**

#### A. User-Facing Changes

**Primary User Flow:**
```
User does:
1. _____
2. _____
3. _____

User sees:
1. _____
2. _____
3. _____

User receives:
1. _____
2. _____
3. _____

Success state: _____
```

**Secondary User Flows:**
[Document any other affected flows]

**UI Changes:**
1. **New element:** _____
   - **Location:** _____
   - **Appearance:** _____
   - **Behavior:** _____
   - **States:** (default, hover, active, loading, error, disabled)

2. **Modified element:** _____
   - **Current:** _____
   - **New:** _____
   - **Rationale:** _____

[List all UI changes]

**UX Changes:**
1. **Interaction pattern:** _____
   - **Before:** _____
   - **After:** _____
   - **Why:** _____

[List all UX changes]

#### B. Technical Changes

**New files to create:**
1. `path/to/new/file.tsx`
   - **Type:** Component/Utility/API/Type
   - **Purpose:** _____
   - **Key responsibilities:** _____
   - **Dependencies:** _____
   - **Exported:** _____

2. `path/to/another/file.ts`
   [Same structure]

[List all new files]

**Existing files to modify:**
1. `path/to/existing/file.tsx`
   - **Current state:** _____
   - **Changes needed:** _____
   - **Lines affected:** Approximate range
   - **Risk level:** Low/Medium/High
   - **Why risky:** _____

2. `path/to/another/file.ts`
   [Same structure]

[List all file modifications]

**New API endpoints:**
1. `POST /api/endpoint/path`
   - **Purpose:** _____
   - **Request shape:**
```typescript
     {
       field1: type;
       field2: type;
     }
```
   - **Response shape:**
```typescript
     {
       field1: type;
       field2: type;
     }
```
   - **Auth required:** Yes/No
   - **Rate limits:** _____
   - **Error codes:** 400 (___), 401 (___), 500 (___)

[List all API endpoints]

**Data model changes:**
1. **New type:** `TypeName`
```typescript
   interface TypeName {
     field1: type;
     field2: type;
   }
```
   - **Purpose:** _____
   - **Used by:** _____

2. **Modified type:** `ExistingType`
   - **Current:**
```typescript
     interface ExistingType {
       field1: type;
     }
```
   - **New:**
```typescript
     interface ExistingType {
       field1: type;
       field2: type; // NEW
     }
```
   - **Breaking change:** Yes/No
   - **Migration needed:** Yes/No

[List all data model changes]

#### C. Success Criteria (Minimum 12 Acceptance Criteria)

**User can criteria (behavioral):**
1. **[ ]** User can _____
   - **Verification:** _____
   - **Expected behavior:** _____

2. **[ ]** User can _____
   - **Verification:** _____
   - **Expected behavior:** _____

[List at least 6 "user can" criteria]

**System does criteria (technical):**
7. **[ ]** System does _____
   - **Verification:** _____
   - **Expected behavior:** _____

8. **[ ]** System does _____
   - **Verification:** _____
   - **Expected behavior:** _____

[List at least 6 "system does" criteria]

**Quality criteria (non-functional):**
- **[ ]** Performance: _____
  - **Target:** _____
  - **How to measure:** _____

- **[ ]** Accessibility: _____
  - **Standard:** WCAG 2.1 Level AA
  - **Key requirements:** _____

- **[ ]** Browser compatibility: _____
  - **Supported:** Chrome 90+, Firefox 88+, Safari 14+
  - **Testing method:** _____

- **[ ]** Mobile responsiveness: _____
  - **Breakpoints:** _____
  - **Touch targets:** _____

- **[ ]** Error handling: _____
  - **All errors have user-friendly messages:** Yes
  - **No console errors:** Yes

- **[ ]** Security: _____
  - **Auth checks:** _____
  - **Input validation:** _____
  - **XSS prevention:** _____

#### D. Detailed Acceptance Criteria

**For EACH criterion above, provide detailed verification:**

**Example:**
```
✓ Criterion 1: User can click "Export" button in session view toolbar

Detailed verification:
- Button visible: YES
  - Location: Right side of SessionToolbar, next to "Share" button
  - Z-index: Same as other buttons
  - CSS class: Uses existing button-secondary style

- Button accessible: YES
  - Keyboard: Tab reaches button, Enter activates
  - Screen reader: Announces "Export session data, button"
  - Focus visible: Blue outline on focus

- Button states: ALL IMPLEMENTED
  - Default: Gray background, black text
  - Hover: Darker gray background
  - Active: Even darker gray (same as "pressed" state on other buttons)
  - Loading: Spinner icon, "Exporting..." text, disabled
  - Error: Red background, "Export failed" text, re-enabled after 3s
  - Disabled: When user lacks permission, grayed out, cursor: not-allowed

- Button behavior: CORRECT
  - Click: Opens dropdown menu below button
  - Double-click: Doesn't trigger twice (prevented with state flag)
  - Click while loading: No effect (button disabled)
  - Click without permission: Shows toast "You don't have permission to export"

- Edge cases handled:
  - Narrow viewport: Button text truncates to "Export" only
  - Mobile: Touch target is 44x44px minimum
  - Dropdown off-screen: Repositions to stay visible
```

**Write detailed verification for your top 5 most critical acceptance criteria:**
1. [Criterion with full verification]
2. [Criterion with full verification]
3. [Criterion with full verification]
4. [Criterion with full verification]
5. [Criterion with full verification]

**Quality gate for this section:**
- [ ] I have at least 12 acceptance criteria
- [ ] Each criterion is specific and testable
- [ ] I have detailed verification for the 5 most critical
- [ ] I've covered user behavior, system behavior, and quality
- [ ] Someone could test this without asking clarifying questions

**Your desired outcome (write at least 800 words):**
```
[Complete specification of desired outcome]
```

### 5. Scope Boundaries (What's In/Out)

**Explicitly define what we're doing and what we're NOT doing.**

#### In Scope (What WILL Be Done)

List specific features/changes:

1. **[ ]** _____
   - **Why in scope:** _____
   - **User value:** _____
   - **Effort:** _____ hours

2. **[ ]** _____
   - **Why in scope:** _____
   - **User value:** _____
   - **Effort:** _____ hours

[List at least 5 in-scope items]

**Total effort for in-scope: _____ hours**

#### Out of Scope (What Will NOT Be Done)

List specific features/changes we're explicitly excluding:

1. **[ ]** _____
   - **Why out of scope:** _____
   - **When might we do this:** _____
   - **Workaround for now:** _____

2. **[ ]** _____
   - **Why out of scope:** _____
   - **When might we do this:** _____
   - **Workaround for now:** _____

[List at least 5 out-of-scope items]

#### Scope Justification

**Why this scope makes sense:**
1. _____
2. _____
3. _____

**What we're optimizing for:**
- [ ] Speed to market
- [ ] User impact
- [ ] Technical simplicity
- [ ] Resource constraints
- [ ] Risk minimization
- Other: _____

**What we're deferring and why:**
- Deferred: _____
  - Reason: _____
  - Future phase: _____

#### Examples (to clarify scope):

**Example 1:**
- ✅ **In scope:** CSV export for single session with manual download
- ❌ **Out of scope:** Scheduled/automated exports (requires cron jobs, adds complexity)
- **Why:** 90% of use case covered by manual export, automation can be Phase 2

**Example 2:**
- ✅ **In scope:** Export up to 50k frames (covers 95% of sessions per analytics)
- ❌ **Out of scope:** Handling 500k+ frame sessions (requires server-side processing, streaming)
- **Why:** Only 2% of sessions are this large, not blocking MVP, adds significant complexity

**Your scope examples:**
1. In scope: _____ Out of scope: _____ Why: _____
2. In scope: _____ Out of scope: _____ Why: _____
3. In scope: _____ Out of scope: _____ Why: _____

**Quality gate for this section:**
- [ ] At least 5 in-scope items
- [ ] At least 5 out-of-scope items
- [ ] Each has clear justification
- [ ] Scope is realistic for stated effort
- [ ] Scope addresses user's core need

**Your scope boundaries (write at least 400 words):**
```
[Complete scope definition]
```

### 6. Known Constraints & Context

**Document everything that limits our options.**

#### Technical Constraints

**Must use (required technology/patterns):**
1. _____
   - **Why required:** _____
   - **Version:** _____
   - **Documentation:** _____

2. _____
   - **Why required:** _____
   - **Version:** _____
   - **Documentation:** _____

[List all required tech]

**Must work with (integration requirements):**
1. System: _____
   - **Integration point:** _____
   - **Version:** _____
   - **Contract/API:** _____
   - **Owner:** _____

[List all integrations]

**Cannot change (locked dependencies):**
1. _____
   - **Why locked:** _____
   - **Workaround:** _____

[List all locked dependencies]

**Must support (environments):**
- **Browsers:** _____
- **Devices:** _____
- **Screen sizes:** _____
- **Operating systems:** _____
- **Node version:** _____
- **Database version:** _____

**Performance constraints:**
- **Load time:** < _____ seconds
- **API response:** < _____ ms
- **Bundle size:** < _____ KB
- **Memory usage:** < _____ MB
- **Database queries:** < _____ per request

#### Business Constraints

**Timeline:**
- **Hard deadline:** _____ (if any)
- **Soft deadline:** _____
- **Why this timeline:** _____
- **Consequences of missing:** _____

**Resources:**
- **Who's available:** _____
- **Time budget:** _____ hours
- **Skills available:** _____
- **Skills missing:** _____

**Dependencies:**
- **Blocked by:** Issue #___ (must complete first)
  - **What we're waiting for:** _____
  - **ETA:** _____
  
- **Blocks:** Issue #___ (they're waiting for this)
  - **What they need:** _____
  - **Their timeline:** _____

**Budget constraints:**
- **Can spend:** $_____ (if any external costs)
- **Cannot exceed:** $_____
- **What we're buying:** _____

#### Design Constraints

**Must match (existing patterns):**
1. Pattern: _____
   - **Location:** _____
   - **Why:** _____
   - **Reference:** _____

**Must follow (standards):**
- **Accessibility:** WCAG 2.1 Level AA
- **Design system:** _____
- **Brand guidelines:** _____
- **Code style:** _____

**User expectations:**
- Based on: _____ (similar feature in product)
- Users expect: _____
- We must: _____

#### Organizational Constraints

**Approval needed from:**
- [ ] Product owner: _____ (for: _____)
- [ ] Design team: _____ (for: _____)
- [ ] Security team: _____ (for: _____)
- [ ] Legal/compliance: _____ (for: _____)

**Communication requirements:**
- **Update frequency:** _____
- **Stakeholders:** _____
- **Demo required:** Yes/No

**Documentation requirements:**
- [ ] User-facing: _____
- [ ] Developer-facing: _____
- [ ] API documentation: _____
- [ ] Changelog entry: _____

**Quality gate for this section:**
- [ ] All constraint categories addressed
- [ ] Each constraint has clear reasoning
- [ ] Approval paths identified
- [ ] Timeline is realistic given constraints

**Your constraints (write at least 500 words):**
```
[Complete constraints documentation]
```

### 7. Related Context (Prior Art & Dependencies)

**Connect this issue to the larger ecosystem.**

#### Similar Features in Codebase

**Feature 1:**
- **Location:** `path/to/feature`
- **What it does:** _____
- **Similar because:** _____
- **Patterns we can reuse:**
  - Pattern: _____ (describe)
  - Pattern: _____ (describe)
- **Mistakes they made we should avoid:**
  - Mistake: _____ (describe)
  - Why it was a mistake: _____
  - What we'll do instead: _____
- **Code we can copy/adapt:**
```typescript
  // Show relevant snippet
```

**Feature 2:**
[Same structure]

[Document at least 3 similar features]

#### Related Issues/Tickets

**Issue #___: [Title]**
- **Relationship:** Depends on / Blocks / Related to
- **Status:** Open / In Progress / Done
- **Relevant because:** _____
- **Key learnings:** _____
- **Link:** _____

[Document all related issues]

#### Past Attempts

**Previous attempt #1:**
- **When:** _____
- **Who:** _____
- **What was tried:** _____
- **Why it failed:** _____
- **What we learned:** _____
- **What we'll do differently:** _____

[Document any previous attempts]

#### External References

**Design mockups:**
- [ ] Figma link: _____
- [ ] Key screens: _____
- [ ] Design decisions: _____

**User research:**
- [ ] User requests: Support ticket #___, #___, #___
- [ ] Survey data: _____
- [ ] User interviews: _____
- [ ] Analytics: _____

**Technical references:**
- [ ] Library docs: _____
- [ ] Blog posts: _____
- [ ] Stack Overflow: _____
- [ ] RFCs/specs: _____

#### Dependency Tree

**Draw the dependency graph:**
```
This Issue (ID: ___)
  ↑
  Depends on: Issue #___ (Status: ___)
  Depends on: Issue #___ (Status: ___)
  ↓
  Blocks: Issue #___ (waiting for: _____)
  Blocks: Issue #___ (waiting for: _____)

Related (not blocking):
  - Issue #___ (similar domain)
  - Issue #___ (shares code)
```

**Critical path analysis:**
- **Longest path:** _____
- **Bottleneck:** _____
- **Risk:** _____

**Quality gate for this section:**
- [ ] At least 3 similar features documented
- [ ] All related issues linked
- [ ] Dependencies mapped
- [ ] External references provided
- [ ] Past attempts documented (if any)

**Your related context (write at least 400 words):**
```
[Complete context documentation]
```

### 8. Open Questions & Ambiguities

**List everything that's still unclear.**

**Format for each question:**

**Question #1:** _____

- **Why unclear:** _____
- **Impact if we guess wrong:** _____
- **Who can answer:** _____
- **When we need answer:** _____
- **Current assumption:** _____
- **Confidence in assumption:** Low/Medium/High
- **Risk if assumption is wrong:** Low/Medium/High

**Question #2:** _____
[Same structure]

[List at least 10 open questions]

**Questions by category:**

**Functional questions:**
1. Should _____ do _____ or _____?
2. When _____ happens, should we _____?
[At least 3]

**Technical questions:**
1. Should we use _____ or _____?
2. How should we handle _____?
[At least 3]

**UX questions:**
1. Should the user see _____ or _____?
2. What should happen when _____?
[At least 2]

**Data questions:**
1. What format should _____ be?
2. Should we include _____?
[At least 2]

**Priority Questions (need answers before starting):**

Mark the questions that MUST be answered:

- [ ] 🔴 **BLOCKER:** Question #___ - Cannot start without answer
- [ ] 🔴 **BLOCKER:** Question #___ - Cannot start without answer
- [ ] 🟡 **IMPORTANT:** Question #___ - Should answer early
- [ ] 🟡 **IMPORTANT:** Question #___ - Should answer early
- [ ] 🟢 **NICE TO KNOW:** Question #___ - Can decide during implementation

**Quality gate for this section:**
- [ ] At least 10 open questions
- [ ] Each has clear impact analysis
- [ ] Blockers are marked
- [ ] Current assumptions documented
- [ ] Risk levels assigned

**Your open questions (write at least 400 words):**
```
[Complete questions documentation]
```

### 9. Initial Risk Assessment (High-Level)

**Identify potential problems before they happen.**

**Risk format:**

**Risk #1: [Category] - [Specific concern]**
- **Description:** _____
- **Why risky:** _____
- **Probability:** ___% (Low: <20%, Medium: 20-60%, High: >60%)
- **Impact if occurs:** Low/Medium/High/Critical
- **Consequence:** _____
- **Early warning signs:**
  1. _____
  2. _____
- **Mitigation strategy:**
  - **Prevention:** _____
  - **Detection:** _____
  - **Response:** _____
- **Contingency plan:** _____
- **Owner:** _____

**Risk #2:** _____
[Same structure]

[Document at least 8 risks]

**Risk categories to consider:**

**Technical risks:**
1. Performance: _____
2. Scalability: _____
3. Integration: _____
4. Browser compatibility: _____

**Execution risks:**
1. Timeline: _____
2. Resource availability: _____
3. Skill gaps: _____
4. Dependencies: _____

**User risks:**
1. Adoption: _____
2. Confusion: _____
3. Friction: _____
4. Edge cases: _____

**Business risks:**
1. Priority changes: _____
2. Scope creep: _____
3. Stakeholder alignment: _____

**Risk Matrix:**

| Risk | Probability | Impact | Priority | Owner | Status |
|------|------------|--------|----------|-------|--------|
| Risk #1 | 40% | High | 🔴 P0 | Name | Not Started |
| Risk #2 | 60% | Medium | 🟡 P1 | Name | Not Started |
| Risk #3 | 20% | Critical | 🔴 P0 | Name | Not Started |
[All risks]

**Top 3 Risks (highest priority × impact):**
1. Risk #___ - Plan: _____
2. Risk #___ - Plan: _____
3. Risk #___ - Plan: _____

**Quality gate for this section:**
- [ ] At least 8 risks identified
- [ ] Each has probability and impact
- [ ] Early warning signs defined
- [ ] Mitigation strategies documented
- [ ] Contingency plans exist
- [ ] Top risks prioritized

**Your risk assessment (write at least 600 words):**
```
[Complete risk documentation]
```

### 10. Classification & Metadata

**Type:** [bug | feature | improvement | refactor | docs | performance | security | a11y]

**Priority:**
- **Critical (P0):** Production broken, users blocked, data loss risk, security vulnerability
  - Response time: Immediate
  - Examples: Total outage, data corruption, security breach

- **High (P1):** Major feature, significant user impact, deadline-driven, blocking other work
  - Response time: Within 1 week
  - Examples: Key feature missing, major bug affecting 30%+ users

- **Normal (P2):** Standard feature/fix, moderate user impact, no urgent deadline
  - Response time: Within 1 month
  - Examples: Quality of life improvements, minor bugs

- **Low (P3):** Nice-to-have, minimal impact, no deadline, polish
  - Response time: When capacity available
  - Examples: Minor UI tweaks, edge case fixes

**Your priority:** _____ (P0/P1/P2/P3)

**Priority justification (minimum 100 words):**
```
[Explain why this priority level]
```

**Effort Estimate:**

**Rough sizing:**
- **XS (< 4 hours):** Trivial change, clear path, no unknowns, no risk
  - Examples: Copy change, simple styling, logging addition

- **Small (4-8 hours):** Simple change, mostly clear path, minimal risk
  - Examples: Simple component, basic API endpoint

- **Medium (8-16 hours):** Standard complexity, some unknowns, manageable risk
  - Examples: Feature with UI + API, moderate integration

- **Large (16-40 hours):** High complexity, significant unknowns, notable risk
  - Examples: Complex feature spanning multiple systems

- **XL (40-80 hours):** Very complex, many unknowns, high risk, needs breaking down
  - Examples: Major architectural change, new subsystem

- **Epic (> 80 hours):** Too large, must be broken into smaller issues
  - Action: Split this issue into multiple issues

**Your effort:** _____ (XS/S/M/L/XL/Epic)

**Effort justification:**

**Complexity breakdown:**
- Frontend work: _____ hours
- Backend work: _____ hours
- Integration work: _____ hours
- Testing work: _____ hours
- Documentation: _____ hours
- Review/iterations: _____ hours (multiply above by 1.25)
- **Total:** _____ hours

**Confidence:** Low/Medium/High
- **If Low:** What unknowns affect estimate?
- **If Medium:** What could increase effort?
- **If High:** What assumptions are we confident about?

**Category:**
- [ ] Frontend: UI components, client-side logic
- [ ] Backend: API, database, server logic
- [ ] Fullstack: Both frontend and backend changes
- [ ] Infrastructure: DevOps, deployment, tooling, config
- [ ] Design: UI/UX, mockups, style guide
- [ ] Data: Database migrations, data transformations
- [ ] Integration: Third-party APIs, external systems
- [ ] Testing: Test infrastructure, test coverage
- [ ] Documentation: User docs, developer docs

**Tags (select all that apply):**
- [ ] user-facing
- [ ] breaking-change
- [ ] needs-migration
- [ ] needs-feature-flag
- [ ] experimental
- [ ] technical-debt
- [ ] quick-win
- [ ] high-impact
- [ ] low-effort
- [ ] needs-design
- [ ] needs-research
- [ ] needs-approval

**Quality gate for this section:**
- [ ] Type selected with clear reasoning
- [ ] Priority justified (100+ words)
- [ ] Effort broken down by category
- [ ] Confidence level stated
- [ ] Category selected
- [ ] Tags selected

**Your classification (write at least 200 words):**
```
[Complete classification with justifications]
```

### 11. Strategic Context (Product Vision Alignment)

**Connect this to the bigger picture.**

#### Product Roadmap Fit

**How this aligns with current strategy:**
- **Q___ Goal:** _____
  - **This issue supports goal by:** _____
  - **Contribution:** ___% toward goal
  - **Metric impact:** _____

- **Product vision:** _____
  - **This issue advances vision by:** _____
  - **Strategic importance:** Low/Medium/High

#### Capabilities Unlocked

**What this enables:**
1. **Future capability:** _____
   - **How this issue enables it:** _____
   - **When we might build it:** _____

2. **Future capability:** _____
   - **How this issue enables it:** _____
   - **When we might build it:** _____

[List at least 3]

**What this blocks:**
1. **Future capability:** _____
   - **Why this is blocking:** _____
   - **Impact of not doing this issue:** _____

#### User Feedback Themes

**This addresses feedback about:**
- **Theme #1:** _____ (from: _____)
  - **Frequency:** _____ requests
  - **User quote:** "_____"
  - **How this resolves:** _____

- **Theme #2:** _____ (from: _____)
  - **Frequency:** _____ requests
  - **User quote:** "_____"
  - **How this resolves:** _____

[List all relevant themes]

#### User Impact Analysis

**Who benefits:**
- **User segment:** _____
  - **Size:** _____ users (___% of base)
  - **Benefit:** _____
  - **Value:** _____

- **User segment:** _____
  - **Size:** _____ users (___% of base)
  - **Benefit:** _____
  - **Value:** _____

**Impact metrics:**
- **Frequency of use:** _____
  - **Per user:** _____ times/day|week|month
  - **Total:** _____ uses/day|week|month

- **Time saved:** _____
  - **Per use:** _____ minutes
  - **Total:** _____ hours/week across all users

- **Satisfaction impact:**
  - **Current NPS for this area:** _____
  - **Expected improvement:** +_____ points
  - **Based on:** _____

- **Adoption impact:**
  - **Expected adoption:** ___% of users
  - **Based on:** _____

- **Revenue impact:**
  - **Direct:** $_____
  - **Indirect:** $_____
  - **Timeline:** _____

#### Technical Impact Analysis

**Code health:**
- **Improves:** _____
- **Maintains:** _____
- **Degrades:** _____ (acceptable because: _____)

**Team velocity:**
- **Speeds up:** _____ (how: _____)
- **Slows down:** _____ (how: _____)
- **Net impact:** Positive/Neutral/Negative

**Technical debt:**
- **Reduces:** _____ (by: _____)
- **Adds:** _____ (acceptable because: _____)
- **Net impact:** Reduces/Neutral/Increases

**Maintainability:**
- **Makes easier:** _____
- **Makes harder:** _____
- **Net impact:** Better/Same/Worse

#### Decision Framework

**Trade-offs we're accepting:**
1. **Accepting:** _____
   - **To gain:** _____
   - **Worth it because:** _____

2. **Accepting:** _____
   - **To gain:** _____
   - **Worth it because:** _____

**Alternative approaches considered:**
1. **Approach:** _____
   - **Why not chosen:** _____
   - **Trade-off:** _____

2. **Approach:** _____
   - **Why not chosen:** _____
   - **Trade-off:** _____

**Quality gate for this section:**
- [ ] Roadmap alignment explained
- [ ] Future capabilities documented
- [ ] User feedback themes linked
- [ ] Impact quantified (users, time, satisfaction)
- [ ] Technical impact assessed
- [ ] Trade-offs acknowledged
- [ ] Written at least 500 words

**Your strategic context (write at least 500 words):**
```
[Complete strategic context]
```

---

## 🧠 THINKING CHECKPOINT #2 (10 minutes minimum)

**Before finalizing, review your work critically.**

### Self-Critique Questions

1. **Would a new team member understand this?**
   - Read your issue as if you know nothing about the project
   - List 5 things that are unclear: _____

2. **Can someone explore this deeply without asking questions?**
   - What questions might they still have? _____
   - Answer those questions now in the issue

3. **Did I quantify impact?**
   - Count how many times you used numbers: _____
   - If < 10, add more quantification

4. **Did I provide evidence?**
   - List your evidence: _____
   - If < 5 pieces, add more

5. **Did I think about failure?**
   - Count your risks: _____
   - If < 8, think of more

6. **Did I connect to the bigger picture?**
   - How many strategic connections: _____
   - If < 3, add more context

7. **Is this detailed enough?**
   - Word count: _____
   - If < 3000 words, add depth

8. **Did I challenge my assumptions?**
   - Assumptions listed: _____
   - If < 5, think deeper

**Quality gate:** Spend at least 10 minutes on self-critique and add at least 300 words based on what you find.

---

## Self-Review Checklist (Before Finalizing)

**Content completeness:**
- [ ] Pre-issue thinking session completed (15+ minutes, 500+ words)
- [ ] Title is specific and under 100 characters
- [ ] TL;DR is 5-7 sentences, 150+ words
- [ ] Current state documented exhaustively (500+ words)
- [ ] Desired outcome is explicit (800+ words)
- [ ] Scope boundaries are clear (400+ words)
- [ ] Constraints documented (500+ words)
- [ ] Related context provided (400+ words)
- [ ] Open questions listed (10+, 400+ words)
- [ ] Risk assessment complete (8+ risks, 600+ words)
- [ ] Classification justified (200+ words)
- [ ] Strategic context explained (500+ words)

**Quality verification:**
- [ ] At least 12 acceptance criteria
- [ ] At least 5 similar features/patterns documented
- [ ] At least 10 open questions
- [ ] At least 8 risks identified
- [ ] At least 3000 total words
- [ ] Quantified impact (users, time, revenue)
- [ ] Evidence provided (screenshots, code, data)
- [ ] All assumptions documented
- [ ] Thinking checkpoints completed

**Usability check:**
- [ ] Someone unfamiliar could understand this
- [ ] All jargon explained
- [ ] All acronyms spelled out
- [ ] Examples provided for abstract concepts
- [ ] Links to relevant docs/code
- [ ] Clear next steps

**Time check:**
- [ ] Time spent: _____ minutes (minimum: 45)
- [ ] If < 45 minutes, go back and add depth

**Self-critique:**
- [ ] Thinking checkpoint #1 completed (10+ minutes, 500+ words)
- [ ] Thinking checkpoint #2 completed (10+ minutes, 300+ words added)
- [ ] Found and fixed at least 5 unclear points
- [ ] Added quantification where missing
- [ ] Challenged my own assumptions

**Final verification:**
- [ ] Read the entire issue out loud
- [ ] Every section has substance (no placeholder text)
- [ ] No vague language ("probably", "maybe", "sort of")
- [ ] Specific file paths, numbers, names, dates
- [ ] Someone could explore this deeply without questions

**If ANY checkbox is unchecked, improve the issue before moving to exploration.**

---

## Quality Metrics (Must Meet Before Submitting)

**Quantifiable requirements:**

| Metric | Minimum | Your Count | Pass? |
|--------|---------|------------|-------|
| Total words | 3,000 | _____ | ⬜ |
| Pre-thinking words | 500 | _____ | ⬜ |
| Acceptance criteria | 12 | _____ | ⬜ |
| Open questions | 10 | _____ | ⬜ |
| Risks identified | 8 | _____ | ⬜ |
| Similar features documented | 3 | _____ | ⬜ |
| Related issues linked | 2 | _____ | ⬜ |
| Assumptions documented | 5 | _____ | ⬜ |
| Time spent (minutes) | 45 | _____ | ⬜ |
| Thinking checkpoint words | 800 | _____ | ⬜ |
| Evidence pieces | 5 | _____ | ⬜ |
| Quantified impacts | 10 | _____ | ⬜ |

**HARD RULE:** If ANY metric is below minimum, the issue is INCOMPLETE. Go back and add depth.

---

## After Issue Creation

**Immediate next steps:**
1. [ ] Share issue with stakeholder for 5-minute validation
2. [ ] Get answers to blocker questions (marked 🔴)
3. [ ] Schedule exploration session
4. [ ] Assign to explorer (could be same person)

**Then move to:**
- **Phase 2: Explore Feature** (deep dive into implementation approach)
  - Time budget: 45-90 minutes
  - Output: Detailed technical exploration document

**This issue becomes the foundation.**
- Exploration references it
- Planning builds on it
- Implementation follows it

---

## Example: Issue Quality Comparison

### ❌ INSUFFICIENT (Rushed, Vague, Useless)
```
# [Feature] Export

Users want to export sessions.

**Priority:** Normal
**Effort:** Medium

**Acceptance Criteria:**
- Add export button
- Export sessions to file
- Make sure it works

**Out of scope:** Bulk export

Let me know if you have questions.
```

**Why this fails:**
- Total words: ~40 (need 3000+)
- No time investment (< 5 minutes)
- Vague title
- No TL;DR
- No current state
- No technical details
- Generic acceptance criteria
- No risks, no questions, no context
- Zero quantification
- No evidence
- Can't explore or plan from this

### ✅ SUFFICIENT (Thorough, Specific, Actionable)

**See the full example template above for what a good issue looks like. Key markers:**
- 3000+ words of detailed content
- 45+ minutes of thinking time
- Specific file paths and code references
- Quantified impact (users, time, revenue)
- 12+ detailed acceptance criteria
- 10+ open questions with analysis
- 8+ risks with mitigation plans
- Evidence (screenshots, code snippets)
- Strategic context
- Deep thinking checkpoints
- Self-critique completed

---

⚠️ **FINAL REMINDER**

**Don't rush this step.**

Time spent here: **Saves 3x time later**
- Rushed issue → Confused exploration → Multiple planning revisions → Blocked implementation
- Thorough issue → Clear exploration → Solid plan → Smooth implementation

**Quality gate:**
- [ ] I spent at least 45 minutes on this
- [ ] I wrote at least 3000 words
- [ ] I completed both thinking checkpoints
- [ ] I met all quality metrics
- [ ] Someone else could explore this without asking questions

**If any checkbox is unchecked, STOP and add more depth.**

Remember: You're setting up the entire workflow for success. Be complete, be specific, be thoughtful.