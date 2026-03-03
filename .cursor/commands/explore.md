# Initial Exploration Stage

Your task is NOT to implement this yet, but to fully understand and prepare with a high-level mock execution plan.

Your responsibilities:

- Analyze and understand the existing codebase thoroughly.
- Determine exactly how this feature integrates, including dependencies, structure, edge cases (within reason, don't go overboard), and constraints.
- Clearly identify anything unclear or ambiguous in my description or the current implementation.
- List clearly all questions or ambiguities you need clarified.

---

## Context Inventory (NEW — complete before mock execution)

Before producing the mock, output a structured inventory of everything the plan will depend on:

```
Function contracts:
  - [function name]: file path, exact signature, return shape, known edge cases

API response shapes:
  - [endpoint or hook]: exact fields returned, nullable fields, fields that may be missing in list vs detail responses

Existing components referenced:
  - [component name]: file path, props interface, what it expects from parent

Constants and config:
  - [constant name]: file path, current value, where it is consumed

Ambiguities requiring human decision:
  - [what is unclear]: why it matters, what the two options are, which steps are blocked until resolved
```

Do not proceed to mock execution until this inventory is complete.
If any ambiguity has no answer from the codebase alone — surface it here and wait for human input before continuing.

---

## High-Level Mock Execution (NOT Full Implementation)

After completing the inventory, provide a walk-through showing HOW you'd implement this:

- **Data Flow**: How does data move through the system? (user input → state → API → UI)
- **Component Structure**: What components would you create and how do they talk to each other?
- **State Management**: Where does state live? What triggers state changes?
- **Side Effects**: What useEffect hooks would you need? When would they run?
- **Edge Cases**: How would you handle loading, errors, empty states?

Show this with:
- Pseudocode or high-level JavaScript (not production code)
- ASCII diagrams or flow charts if helpful
- Code snippets (5-10 lines max) to illustrate key patterns
- NOT full implementations — just the skeleton/pattern

Example of what I mean:
```
// NOT THIS (full implementation):
function UserCard({ userId }) {
  const [user, setUser] = useState(null);
  ...
}

// DO THIS (high-level mock):
UserCard component:
  - State: user (null), loading (true), error (null)
  - useEffect: on mount, fetch user by ID, set state
  - Render logic:
    * If loading: show skeleton
    * If error: show error message
    * If data: show user details

Data flow: userId prop → useEffect triggers → API call → setUser updates state → re-render
```

---

## Implementation Approach

Suggest the best way forward with:
- **Which existing files/components would be modified** (and why)
- **What new files/components would be created** (and why)
- **Why this structure makes sense** given the codebase
- **Alternatives you considered and why you rejected them**

Show this as a simple list or tree, not as code:
```
src/
  components/
    UserCard.tsx (NEW) - receives userId prop, manages fetch + state
    UserList.tsx (MODIFY) - pass userId to UserCard, handle list logic
```

Then explain WHY each decision.

---

## Questions to Clarify

List all questions or ambiguities that need human confirmation before proceeding.
Separate into two tiers:

**Blocking — plan cannot be written without these:**
- [question] — [which steps are blocked]

**Non-blocking — can proceed with assumption, but flag:**
- [question] — [what assumption you are making, what breaks if assumption is wrong]

---

Remember: your job is NOT to implement yet. Complete the Context Inventory first, then the mock. We go back and forth until ambiguities are resolved and the approach is confirmed.

Please confirm that you fully understand and I will describe the problem.