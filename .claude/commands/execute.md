# Implementation Stage

Implement precisely as planned, with verification at every step.

## Implementation Requirements

- Write elegant, minimal, modular code.
- Adhere strictly to existing code patterns, conventions, and best practices.
- Include thorough, clear comments/documentation within the code.
- Follow the exact structure and decisions from the approved plan.
- Do NOT deviate from the plan without explicit approval.

## Verification Gates (Non-Negotiable)

**Before committing each step:**

1. **Code Quality Check**
   - Does it match existing code patterns in the codebase?
   - Are there any linting errors or style violations?
   - Is the code readable and self-documenting?
   - Are edge cases handled?
   - Any console errors or warnings?

2. **Integration Verification**
   - Does this step integrate correctly with existing code?
   - Did I break any existing functionality?
   - Are all imports/exports correct?
   - Do type definitions align?
   - Does this work with the rest of the plan?

3. **Plan Adherence Check**
   - Does this match the approved plan exactly?
   - Did I add any extra scope or complexity?
   - Are all decisions from "Critical Decisions" honored?
   - Did I skip any part of this step?

4. **Testing (Within Scope)**
   - Can I demonstrate this step works in isolation?
   - Can I show expected behavior with sample data?
   - Do error cases fail gracefully?
   - Did I test on target platform/browser if relevant?

5. **Documentation Check**
   - Are comments clear and useful?
   - Did I document non-obvious decisions?
   - Are function signatures and props documented?
   - Could someone else understand this code?

## For Each Step:

**Step [N]: [Name]**

### Implementation
[Write the code for this step]

### Post-Implementation Verification

**Code Quality:** ✓ / ✗
- [Specific verification details]
- [Any issues found and how they were fixed]

**Integration Check:** ✓ / ✗
- [How this integrates with existing code]
- [Any compatibility issues]
- [Modified files listed]

**Plan Adherence:** ✓ / ✗
- [Confirmation this matches approved plan]
- [Any deviations and why]

**Testing Results:** ✓ / ✗
- [How you tested this step]
- [Expected behavior demonstrated]
- [Edge cases tested]

**Documentation:** ✓ / ✗
- [Comments and documentation added]
- [Any unclear parts explained]

### Status Update
🟩 Done / 🟨 In Progress / 🟥 Blocked

**Overall Progress:** `[X]%`

---

## Stop Conditions (Do NOT Proceed if):

- ❌ Code doesn't match existing patterns
- ❌ Verification gate fails
- ❌ Integration with existing code breaks
- ❌ Plan was deviated from without approval
- ❌ Code quality issues exist
- ❌ Step is incomplete or partial
- ❌ Testing shows failures

**If any stop condition is triggered:** Explain what failed, why, and ask for guidance before continuing.

## Approval Workflow

**After each step is complete:**
1. Show me the implementation code
2. Show verification results
3. Wait for approval before proceeding to next step
4. If issues: Fix them, re-verify, re-submit
5. Only after approval: Mark as 🟩 Done and proceed

## Documentation Requirements Per Step

**In the code itself:**
- Why this code exists (if non-obvious)
- How it integrates with other parts
- Any assumptions or constraints
- Edge cases handled
- Complex logic explained

**In comments:**
- Function/component purpose
- Parameter/prop explanations
- Return value/behavior
- Usage examples if helpful
- Warnings about side effects

## Quality Checklist Per Step

- [ ] Code follows existing patterns in codebase
- [ ] No linting errors or warnings
- [ ] All imports/exports are correct
- [ ] Type definitions are accurate
- [ ] Edge cases are handled
- [ ] Comments explain non-obvious decisions
- [ ] Integration with other code verified
- [ ] Testing completed successfully
- [ ] No breaking changes to existing code
- [ ] Plan was followed exactly

## If Issues Arise During Implementation

When you encounter problems:
1. **Identify the issue clearly** - What failed and why?
2. **Determine impact** - Does this break the plan or just this step?
3. **Propose solution** - How should we fix it?
4. **Ask for guidance** - Should we proceed with fix, roll back, or revisit plan?
5. **Do NOT proceed** until issue is resolved

## Final Step

After all steps are complete and verified:

- [ ] All verification gates passed
- [ ] All code is reviewed and approved
- [ ] Testing completed successfully
- [ ] Documentation complete
- [ ] No regressions in existing functionality
- [ ] Feature works as specified in plan
- [ ] Code ready for production

**Overall Progress:** `100%`

🎉 Implementation complete. Ready for next phase (deployment/review/etc).
