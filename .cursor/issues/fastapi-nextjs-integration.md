# FastAPI + Next.js End-to-End Integration Verification

**Type:** Improvement  
**Priority:** Normal  
**Effort:** Medium  
**Status:** Planning

## TL;DR
Verify and complete the end-to-end integration between the FastAPI backend and Next.js frontend dashboard. Ensure both servers run correctly, data flows properly from backend to frontend, and all components render correctly with real API data.

## Current State
- ✅ FastAPI backend exists (`backend/`) with dashboard endpoint `/api/dashboard`
- ✅ Next.js frontend exists (`my-app/`) with dashboard components
- ✅ Frontend configured to fetch from backend API (`src/lib/api.ts`)
- ✅ CORS configured for localhost:3000 → localhost:8000
- ✅ Environment variable configured (`.env.local`)
- ⚠️ **End-to-end integration not yet verified** - need to test actual data flow
- ⚠️ **Backend dependencies may not be installed** - need to verify Python environment
- ⚠️ **Both servers need to run simultaneously** - need startup scripts/instructions

## Expected Outcome
- Backend server runs successfully on `http://localhost:8000`
- Frontend server runs successfully on `http://localhost:3000`
- Frontend successfully fetches dashboard data from backend API
- All metrics display correctly in `MetricCard` components
- All charts render correctly (`LineChart`, `BarChart`, `PieChart`)
- Data structure matches exactly between Python Pydantic models and TypeScript interfaces
- Changes to `backend/data/mock_data.py` automatically reflect in frontend on refresh
- Error handling works correctly when backend is unavailable
- No CORS errors in browser console
- Type safety verified (no TypeScript/Python type mismatches)

## Relevant Files
- `backend/main.py` - FastAPI app entry point (CORS config)
- `backend/routes/dashboard.py` - Dashboard API endpoint
- `backend/models.py` - Pydantic models (must match TypeScript types)
- `backend/data/mock_data.py` - Mock data (single source of truth)
- `backend/requirements.txt` - Python dependencies
- `my-app/src/app/page.tsx` - Main page component (fetches from API)
- `my-app/src/lib/api.ts` - API client utility
- `my-app/src/types/dashboard.ts` - TypeScript type definitions
- `my-app/src/components/dashboard/DashboardLayout.tsx` - Dashboard layout component
- `my-app/src/components/dashboard/MetricCard.tsx` - Metric display component
- `my-app/src/components/charts/*.tsx` - Chart components
- `my-app/.env.local` - Environment configuration (API URL)

## Implementation Notes
- **Backend Setup:**
  - Verify Python virtual environment exists or create one
  - Install dependencies: `pip install -r requirements.txt`
  - Test backend server: `uvicorn main:app --reload` (from `backend/` directory)
  - Verify `/api/dashboard` endpoint returns valid JSON
  - Verify `/health` endpoint works

- **Frontend Setup:**
  - Verify Node.js dependencies installed: `npm install`
  - Verify `.env.local` has correct `NEXT_PUBLIC_API_URL`
  - Test frontend server: `npm run dev`
  - Verify frontend loads without errors

- **Integration Testing:**
  - Start both servers simultaneously
  - Open frontend in browser (`http://localhost:3000`)
  - Verify dashboard loads with data from backend
  - Check browser console for errors (no CORS errors)
  - Verify all metrics display correctly
  - Verify all charts render correctly
  - Test error handling: stop backend, refresh frontend, verify error message shows
  - Test data sync: edit `backend/data/mock_data.py`, refresh frontend, verify changes appear

- **Data Structure Verification:**
  - Ensure Python `ChartDataPoint` model fields match TypeScript expectations:
    - Line charts: `date` field (not `category` or `name`)
    - Bar charts: `category` field (not `date` or `name`)
    - Pie charts: `name` field (not `date` or `category`)
  - Verify `MetricData` structure matches (id, title, value, change, trend)
  - Verify `DashboardData` structure matches (metrics array, charts array)

- **Type Safety:**
  - Run TypeScript compiler: `npm run build` or `tsc --noEmit`
  - Verify no type errors
  - Verify Python Pydantic validation works (invalid data should fail)

## Risks/Dependencies
- **Python Environment:** Backend requires Python 3.8+ with virtual environment
- **Port Conflicts:** Both servers need available ports (3000 for Next.js, 8000 for FastAPI)
- **Data Structure Mismatch:** Python Pydantic models must match TypeScript interfaces exactly
- **CORS Configuration:** Must allow `http://localhost:3000` origin
- **Environment Variables:** Frontend needs `NEXT_PUBLIC_API_URL` set correctly
- **Dependencies:** Both Python (`requirements.txt`) and Node.js (`package.json`) dependencies must be installed
- **Type Safety:** TypeScript types and Python models must stay in sync

## Success Criteria
- ✅ Backend server starts without errors
- ✅ Frontend server starts without errors
- ✅ Frontend successfully fetches data from backend
- ✅ Dashboard renders with all metrics and charts
- ✅ No console errors (no CORS, no type errors)
- ✅ Error handling works (shows error when backend down)
- ✅ Data sync works (backend mock data changes reflect in frontend)
- ✅ Type safety verified (no TypeScript/Python mismatches)

## Next Steps After Integration
- Add automated testing (unit tests for API, integration tests for data flow)
- Add development scripts to start both servers easily
- Consider adding API response caching
- Consider adding request retry logic
- Document API endpoints and data structures
- Set up production deployment configuration
