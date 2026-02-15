
Here’s the exploration and high-level plan for adding a small button on the session replay page.

---

# Exploration: Small Button on Session Replay Page

## 1. Codebase Analysis Summary

### Session Replay Page

- **File**: `my-app/src/app/replay/[sessionId]/page.tsx` (~504 lines)
- **Route**: `/replay/[sessionId]` (e.g. `/replay/sess_expert_001`)
- **Structure**:
  - `ReplayPage` → `ReplayPageWithAsyncParams` (Next.js 15 async params) or `ReplayPageInner` (sync)
  - `ReplayPageInner` owns all state and UI

### Existing Layout & Buttons

```
┌─────────────────────────────────────────────────────────────────┐
│ Session Replay: {sessionId}                                      │
├─────────────────────────────────────────────────────────────────┤
│ metadata bar: weld_type • duration • frames  [Compare link] [Hide/Show Comparison]   ← existing small button
├─────────────────────────────────────────────────────────────────┤
│ [Play] [Pause] | Timeline slider | X.XX s                        │
├─────────────────────────────────────────────────────────────────┤
│ 3D Torch Viz (side-by-side: Current Session | Comparison)        │
├─────────────────────────────────────────────────────────────────┤
│ HeatMap | TorchAngleGraph                                        │
├─────────────────────────────────────────────────────────────────┤
│ ScorePanel                                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Existing Button Patterns

1. **Small button** (Hide/Show Comparison):
   - `px-3 py-1 text-xs rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700`
2. **Primary button** (Play/Pause):
   - `px-4 py-2 rounded-md bg-blue-500 text-white text-sm font-medium`

### Tests

- `my-app/src/__tests__/app/replay/[sessionId]/page.test.tsx`
- Uses `screen.getByRole('button', { name: /hide.*comparison/i })` to find buttons

---

## 2. Integration Points & Dependencies

- **State**: All in `ReplayPageInner`; no external store
- **Data**: `sessionId` from route params; data from `fetchSession` / `fetchScore`
- **Styling**: Tailwind, matches existing UI
- **Tests**: Jest + React Testing Library; should add coverage for the new button

---

## 3. High-Level Mock Execution Plan

### Data Flow

```
User clicks button
       → onClick handler runs
       → (depends on button behavior)
       
// If toggle: local state update → re-render
// If navigation: router.push() or Link
// If API action: optional loading/error state → re-render
```

### Component Structure

```
ReplayPageInner (existing)
  └── metadata bar (existing div)
        ├── span (metadata text)
        ├── Link (Compare with another session)
        ├── button (Hide/Show Comparison)  ← existing
        └── button (NEW small button)      ← add here
```

No new component for a single button; inline like the existing comparison toggle.

### State Management

- **If stateless**: no state; onClick does something (e.g. navigate, call API)
- **If toggle**: `useState` in `ReplayPageInner` (same pattern as `showComparison`)

Example for a toggle:

```js
const [someFlag, setSomeFlag] = useState(false);
// Button: onClick={() => setSomeFlag(p => !p)}
```

### Side Effects (useEffect)

- Most likely none. Existing buttons do not use `useEffect`.
- Only if the button triggers something async (e.g. API call) would there be a dedicated effect or callback; that’s behavior-dependent.

### Edge Cases

| Scenario        | Approach                                                                 |
|----------------|------------|-------------------------------------------------------------|
| Loading        | Button in metadata bar; metadata shows only when loaded → button only when session loaded |
| Error          | Page shows error UI; button not rendered                                 |
| Empty session  | Same as loading/error; no metadata bar                                   |

---

## 4. Implementation Approach

```
my-app/src/
  app/
    replay/
      [sessionId]/
        page.tsx          (MODIFY) — add the new button in metadata bar
  __tests__/
    app/
      replay/
        [sessionId]/
          page.test.tsx   (MODIFY) — add test for new button render and behavior
```

**Why this structure**

- Single button, local behavior → inline in page, no new component
- Placement next to “Compare” and “Hide/Show Comparison” is consistent
- Tests live in the existing replay page tests

**Alternatives**

1. **Extract shared metadata bar**  
   - Would need a component used only here; adds abstraction without clear benefit.
2. **Create `SmallButton` component**  
   - Overkill for one usage; existing buttons are inline.
3. **Place button elsewhere**  
   - e.g. near Play or after ScorePanel. Metadata bar is the clearest unless you want a different primary action.

---

## 5. Pseudocode / Skeleton

```js
// In ReplayPageInner, inside the metadata div (around line 335–356):
{metadata && (
  <div className="... flex flex-wrap items-center gap-3">
    <span>...</span>
    <Link href={...}>Compare with another session</Link>
    <button type="button" onClick={() => setShowComparison(...)}>
      {showComparison ? 'Hide' : 'Show'} Comparison
    </button>
    {/* NEW: Small button — behavior TBD */}
    <button
      type="button"
      onClick={() => { /* TODO: what does it do? */ }}
      className="px-3 py-1 text-xs rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700"
    >
      Button Label TBD
    </button>
  </div>
)}
```

### Test Skeleton

```js
it('renders the new small button when session loads', async () => {
  render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
  await waitFor(() => expect(screen.getByText(/session replay/i)).toBeInTheDocument());
  expect(screen.getByRole('button', { name: /button label tbd/i })).toBeInTheDocument();
});

// Plus a test for onClick behavior once defined
```

---

## 6. Questions to Clarify

These must be answered before implementation:

1. **What should the button do?**
   - Navigate (where?)  
   - Toggle something (e.g. show/hide comparison)  
   - Trigger an action (e.g. download, share)  
   - Open a modal or drawer  

2. **Where should it appear?**
   - In the metadata bar with Compare and Hide/Show Comparison (assumed)  
   - Or elsewhere (e.g. near Play, after ScorePanel, floating)  

3. **Exact label?**
   - Short label for a small button (e.g. 1–3 words).

4. **Visual style?**
   - Same as “Hide/Show Comparison” (secondary, `text-xs`), or stronger (primary blue, larger) to indicate more important action?

5. **Conditional visibility?**
   - Always visible once session loads, or only in certain cases (e.g. when comparison is shown)?

6. **Demo page?**
   - Should the same button be added to `my-app/src/app/demo/page.tsx` for the browser-only demo?

Once these are clarified, the implementation can follow this plan closely, with minimal code changes.
