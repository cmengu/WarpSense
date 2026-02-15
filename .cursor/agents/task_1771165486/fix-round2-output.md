
Here’s what was fixed from the code review:

### 1. **Range input NaN handling** (`demo/page.tsx`)
The range input `onChange` could pass `NaN` to `setCurrentTimestamp` (e.g., empty or invalid input). It now validates and clamps the value:

```typescript
const val = Number(e.target.value);
setCurrentTimestamp(
  Number.isFinite(val)
    ? Math.max(0, Math.min(DURATION_MS, val))
    : currentTimestamp
);
```

### 2. **Non-null assertion in test** (`demo-data.test.ts`)
Replaced the `thermalFrame!` non-null assertion with an explicit guard:

```typescript
expect(thermalFrame).toBeDefined();
if (!thermalFrame) throw new Error("thermalFrame not found");
// ... then use thermalFrame without !
```

### Already in place
- **Try-catch with `logError`** for session generation — already wrapped in try-catch with `logError` on failure.
- **Hardcoded scores and feedback** — kept as-is per plan (Decision 2: "Hardcode scores 94/100 and 42/100").

No linter errors were introduced. Run tests with `npm test -- demo-data` to confirm.
