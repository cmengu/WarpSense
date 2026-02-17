
Here’s a concise summary of the code review:

# Code Review Report - Round 1 (Summary)

## Scope
- **24 files** reviewed (~1,200 lines)
- **21 issues** found across severity levels

## Critical issues (2 – fix before deploy)

1. **Supervisor page logging** – `console.error` used in 3 places instead of `logError` from `@/lib/logger`.
2. **Aggregate service date filter** – `date_start` is compared as a string, causing timezone ambiguity. PostgreSQL may use the server timezone instead of UTC, leading to off‑by‑one day at DST boundaries.

## High-priority issues (6)

3. Missing type annotation for `db` in aggregate route  
4. `CalendarHeatmap` uses `key={i}` instead of `key={c.date}`  
5. `generateCSV` assumes all rows share the same keys/order and can produce misaligned CSV  
6. `verify_backfill.py` has no error handling around DB use  
7. `backfill_score_total.py` has no error handling around DB use  
8. E2E test uses deprecated `waitForTimeout` instead of proper waits  

## Medium-priority issues (8)

9. Loose typing in `aggregate-transform` trend mapping  
10. `data!` non-null assertion on supervisor page  
11. Redundant layout wrappers between supervisor and `DashboardLayout`  
12. Type assertions without validation in `aggregate-transform`  
13. Tests use SQLite while production uses PostgreSQL  
14. `CalendarHeatmap` cells lack keyboard focus  
15. No client-side date validation before fetch  
16. `apiFetch` success path can throw on malformed JSON  

## Low-priority issues (5)

17. Missing JSDoc on helper functions  
18. Magic numbers (90 days, 1000 sessions)  
19. No unit tests for `CalendarHeatmap`  
20. `downloadCSV` anchor not appended to DOM  
21. Redundant `r and r > 0` in verify script  

## Good practices

- Division-by-zero guard and `sessions_truncated` flag  
- Consistent UTC handling in `CalendarHeatmap`  
- `AbortController` cleanup in supervisor fetch  
- ESLint rules to avoid 3D/thermal imports  
- Solid test coverage for transform, API, and service  

Full report with code snippets and fixes: `.cursor/review/wwad-macro-analytics-round1-code-review.md`
