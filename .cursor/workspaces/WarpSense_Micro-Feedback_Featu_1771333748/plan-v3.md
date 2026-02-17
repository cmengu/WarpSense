
All five minor refinements from the critique are in place. Summary:

**1. Step 3.1 test example** – Test uses `fetchSession` mock and `waitFor` (ReplayPage fetches internally via `sessionId`). Added example with `mockFetchSession.mockResolvedValue(session)` and `await waitFor(() => expect(mockGenerate).toHaveBeenCalledWith(frames))`.

**2. Step 3.1 Jest mock** – Clarified ESM vs CJS: use `import { generateMicroFeedback }` and `(generateMicroFeedback as jest.Mock)` for ESM, or `require()` for CJS, based on Jest/config.

**3. Step 1.5 resilience** – Removed brittle `closest('.border-blue-500')`. Test now checks presence and `queryByRole('button', { name: /Angle within target/ })` to ensure session-level items are not buttons. Step 2.1 adds `data-testid="feedback-item-info"`, `feedback-item-warning`, and `feedback-item-critical`.

**4. Step 3.5 frameFixtures import** – Added explicit import:
```typescript
import { makeFrame, makeThermalSnapshot } from '@/__tests__/utils/frameFixtures';
```

**5. Phase 3.8 loading state** – Documented handling when `sessionData` is null: avoid rendering FeedbackPanel with `items={[]}`; either defer until `sessionData` exists or show a loading placeholder. Added a cross-reference in Step 3.2.
