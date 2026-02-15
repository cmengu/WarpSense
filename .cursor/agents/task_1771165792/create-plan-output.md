
Created a plan at `.cursor/plans/session-replay-small-button-plan.md` for adding a small button to the session replay page. Summary:

## Plan Overview

**Overall progress:** 0%

**Scope:** Add a small “Copy Session ID” button in the replay metadata bar (next to “Compare with another session” and “Hide/Show Comparison”).

**Decisions:**
- Use the Clipboard API to copy `sessionId` on click (no API/state changes)
- Place the button in the metadata row for consistency
- Reuse the compact style of “Hide/Show Comparison” (`text-xs px-3 py-1`)

**Phase 1 — single step**
- Add the button, handler, styling, and `aria-label`
- Non-critical UI change (no API, state, or DB work)

**Verification:** Load `/replay/sess_expert_001`, click the button, paste elsewhere, and confirm the session ID is copied.

**Risks:** Low (around 5–10%) — mainly Clipboard API availability and layout wrapping.

If you want a different label or behavior for the button, that can be updated in the plan.
