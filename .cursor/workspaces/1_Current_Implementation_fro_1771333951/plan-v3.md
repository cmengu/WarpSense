
All 5 fixes from the critique are applied to the plan:

1. **Step 3.9 – Test path**  
   Updated to `my-app/src/__tests__/app/(app)/supervisor/page.test.tsx` to match the project’s page test layout.

2. **Step 3.9 – Assertions**  
   Replaced the single regex with explicit checks for each KPI: `expect(screen.getByText('78')).toBeInTheDocument()`, `expect(screen.getByText('12')).toBeInTheDocument()`, `expect(screen.getByText('2')).toBeInTheDocument()`, plus checks for the labels.

3. **Step 3.4 – Transform unit test**  
   Documented the transform unit test at `my-app/src/__tests__/lib/aggregate-transform.test.ts` and added example input and assertions.

4. **Step 2.2 – Timezone**  
   Clarified that all `start_time` is stored in UTC and noted using `s.start_time.astimezone(timezone.utc).date()` when needed.

5. **Definition of Done – Observability**  
   Added an optional observability item: log `date_start`, `date_end`, and response time for the aggregate endpoint, with an example.

The refined plan is in `.cursor/plans/wwad-macro-analytics-implementation-plan.md`.
