
All five minor refinements are applied:

1. **Step 3.5 mock structure** – Session mock updated to match `Session` type and `page.test.tsx`: `session_id`, `operator_id`, `start_time`, `weld_type`, `thermal_sample_interval_ms`, and related fields.
2. **Step 1.4 vs 1.7 ordering** – Notes added in 1.4 and 1.7 that Step 1.7 can be done before 1.4 to have `frameFixtures` ready and avoid a second refactor.
3. **Step 1.2 verification** – Post-step verification added to update the ai-feedback test with an explicit `const critical: FeedbackSeverity = 'critical'` assertion.
4. **Step 3.2 frames prop** – Guard updated to `frames={sessionData.frames ?? []}` so FeedbackPanel always receives an array even when the API returns undefined frames.
5. **Step 3.7 accessibility** – Section added on automated a11y checks with `jest-axe` or `@axe-core/react`, in addition to manual VoiceOver/NVDA checks.
