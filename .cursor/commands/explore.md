# Initial Exploration Stage

Your task is NOT to implement this yet, but to fully understand and prepare with a high-level mock execution plan.

Your responsibilities:

- Analyze and understand the existing codebase thoroughly.
- Determine exactly how this feature integrates, including dependencies, structure, edge cases (within reason, don't go overboard), and constraints.
- Clearly identify anything unclear or ambiguous in my description or the current implementation.
- List clearly all questions or ambiguities you need clarified.

## High-Level Mock Execution (NOT Full Implementation)

**After full exploration**, provide a "walk-through" showing HOW you'd implement this:

- **Data Flow**: How does data move through the system? (user input → state → API → UI)
- **Component Structure**: What components would you create and how do they talk to each other?
- **State Management**: Where does state live? What triggers state changes?
- **Side Effects**: What useEffect hooks would you need? When would they run?
- **Edge Cases**: How would you handle loading, errors, empty states?

**Show this with:**
- Pseudocode or high-level JavaScript (not production code)
- ASCII diagrams or flow charts if helpful
- Code snippets (5-10 lines max) to illustrate key patterns
- NOT full implementations—just the skeleton/pattern

**Example of what I mean:**
```
// NOT THIS (full implementation):
function UserCard({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetchUser(userId)...
  }, [userId]);
  if (loading) return <Skeleton />;
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

Data flow: userId prop → useEffect triggers → API call → setUser updates state → re-render with user data
```

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
  hooks/
    useUserData.ts (NEW) - custom hook for fetch logic (or inline in component?)
  types/
    user.ts (MODIFY) - add UserCardProps interface
```

Then explain WHY each decision:
- "UserCard is its own component because it's reusable across pages"
- "I'd keep the fetch logic IN the component (not a custom hook) because it's simple and only used once"
- "I'd modify UserList to handle the list state, not UserCard"

## Questions to Clarify

List all questions or ambiguities that need YOUR confirmation before proceeding:
- Is this supposed to fetch real data or use mock data?
- Should loading/error states be skeletons or spinners?
- Is this a single user or a list?
- Any performance concerns if fetching 100 users?

Remember, your job is NOT to implement yet. Just walk me through HOW you'd think about building this. We go back and forth until you fully understand the requirements and confirm the approach.

Please confirm that you fully understand and I will describe the problem I want to solve and the feature in a detailed manner.