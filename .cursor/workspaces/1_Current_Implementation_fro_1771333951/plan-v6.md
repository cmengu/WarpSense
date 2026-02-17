
Refinements from the critique are applied to the implementation plan. Summary:

**Backend (Phase 2)**  
- **Step 2.2 & 2.3:** Documented UTC and inclusive `date_end` (Query param descriptions and route docstring).  
- **Step 2.7 & 2.8:** Added `db.rollback()` in fixtures, `try/finally` for `app.dependency_overrides.clear()`, and notes on pytest-xdist.  
- **Step 2.8:** Mentioned optional integration test with seeded DB for response-shape validation.

**Frontend (Phase 3)**  
- **Step 3.1:** Noted runtime checks in Step 3.4 and display of "—" for nulls.  
- **Step 3.3:** Made `weeksToShow` configurable (default 12), added `role="img"` and `aria-label` for cells.  
- **Step 3.4:** Added guards for missing `kpis`, null `session_count`, and trend with all-zero values.  
- **Step 3.5:** Added `console.error` when fetch fails.

**Date Filter & Export (Phase 4)**  
- **Step 4.2:** Debounce (300ms) for preset buttons and date picker, 0ms on initial load; added timezone guidance for date strings.  
- **Step 4.3:** UI alert when export is truncated (1000 sessions or 90 days).  
- **Step 4.7:** Screen reader announcements via `aria-live` for export success/error.

**Risk Heatmap**  
- Added risks for React hydration mismatch and Tailwind dark mode issues.

**Common Failures**  
- Expanded timezone off-by-one handling with concrete conversion examples.

The full refined plan is in `.cursor/plans/wwad-macro-analytics-implementation-plan.md`.
