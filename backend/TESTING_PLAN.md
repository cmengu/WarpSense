# Manual Testing Plan - Steps 6 & 9

**Current Progress:** 78% (Steps 1-5, 7-8 complete)  
**Remaining:** Steps 6 & 9 (Backend Testing & End-to-End Testing)

---

## Prerequisites

Before starting, ensure:
- ✅ Internet connection (to install dependencies if not already installed)
- ✅ Python 3.12+ installed
- ✅ Node.js and npm installed (for frontend)
- ✅ Two terminal windows/tabs available

---

## Step 6: Backend Testing

### 6.1 Install Dependencies (if not done)
```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate
pip install -r requirements.txt
```

### 6.2 Start Backend Server
```bash
# Make sure you're in backend directory
cd /Users/ngchenmeng/test/backend

# Activate virtual environment
source venv/bin/activate

# Start the server with auto-reload
uvicorn main:app --reload
```

**Expected Output:**
```
INFO:     Will watch for changes in these directories: ['/Users/ngchenmeng/test/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Keep this terminal open** - the server needs to keep running.

---

### 6.3 Test Health Check Endpoint

Open a **new terminal** (keep backend server running) and run:

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"ok","message":"Dashboard API is running"}
```

**OR** open in browser: http://localhost:8000/health

**✅ Success Criteria:** Returns JSON with status "ok"

---

### 6.4 Test Dashboard Endpoint

In the same terminal (or browser):

```bash
curl http://localhost:8000/api/dashboard
```

**OR** open in browser: http://localhost:8000/api/dashboard

**Expected Response:** JSON object with:
- `metrics` array (4 items)
- `charts` array (3 items)

**Verify Structure:**
- Each metric has: `id`, `title`, `value`, `change`, `trend`
- Each chart has: `id`, `type`, `title`, `data`, `color`
- Chart types: "line", "bar", "pie"

**✅ Success Criteria:** Returns valid JSON matching DashboardData structure

---

### 6.5 Verify CORS Headers

Check CORS headers in response:

```bash
curl -I -H "Origin: http://localhost:3000" http://localhost:8000/api/dashboard
```

**Look for these headers:**
- `access-control-allow-origin: http://localhost:3000`
- `access-control-allow-credentials: true`
- `access-control-allow-methods: *`

**OR** use browser DevTools:
1. Open http://localhost:8000/api/dashboard
2. Open Network tab → Click on request → Headers
3. Check Response Headers for CORS headers

**✅ Success Criteria:** CORS headers present and allow localhost:3000

---

### 6.6 Test Data Updates

1. **Edit mock data** (in a new terminal or editor):
   ```bash
   # Open backend/data/mock_data.py
   # Change one value, e.g.:
   # "value": 12543 → "value": 99999
   ```

2. **Save the file**

3. **Check backend terminal** - should see:
   ```
   INFO:     Detected file change in 'data/mock_data.py'. Reloading...
   INFO:     Application startup complete.
   ```

4. **Test endpoint again:**
   ```bash
   curl http://localhost:8000/api/dashboard | grep 99999
   ```

   **OR** refresh browser: http://localhost:8000/api/dashboard

**✅ Success Criteria:** 
- Backend auto-reloads when file changes
- API returns updated data

---

## Step 9: End-to-End Testing

### 9.1 Start Both Servers

**Terminal 1 - Backend (if not already running):**
```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd /Users/ngchenmeng/test/my-app
npm run dev
```

**Expected Output (Frontend):**
```
  ▲ Next.js 16.1.6
  - Local:        http://localhost:3000
  - Ready in X ms
```

**Keep both terminals open.**

---

### 9.2 Verify Frontend Loads Data from Backend

1. **Open browser:** http://localhost:3000

2. **Expected Behavior:**
   - Shows "Loading dashboard..." briefly
   - Then displays dashboard with:
     - 4 metric cards (Total Users, Revenue, Active Sessions, Conversion Rate)
     - 3 charts (User Growth line chart, Revenue by Category bar chart, User Distribution pie chart)

3. **Check Browser Console** (F12 → Console tab):
   - Should see no errors
   - Should see successful API call to `http://localhost:8000/api/dashboard`

4. **Check Network Tab** (F12 → Network):
   - Find request to `/api/dashboard`
   - Status: 200 OK
   - Response: JSON with dashboard data

**✅ Success Criteria:** 
- Dashboard loads successfully
- Data matches backend mock data
- No console errors
- Network request succeeds

---

### 9.3 Test Data Updates Flow

1. **Edit backend mock data:**
   ```bash
   # Edit backend/data/mock_data.py
   # Change "Total Users" value from 12543 to 50000
   ```

2. **Save the file**

3. **Check backend terminal** - should auto-reload

4. **Refresh frontend browser** (http://localhost:3000)

5. **Verify changes appear:**
   - "Total Users" metric should show 50000 instead of 12543

**✅ Success Criteria:** 
- Backend auto-reloads
- Frontend shows updated data after refresh
- Changes reflect immediately

---

### 9.4 Test Error Handling

1. **Stop backend server** (Ctrl+C in backend terminal)

2. **Refresh frontend** (http://localhost:3000)

3. **Expected Behavior:**
   - Shows error message: "Failed to load dashboard"
   - Shows message: "Make sure the FastAPI backend is running on http://localhost:8000"
   - Shows "Retry" button

4. **Click Retry button:**
   - Should still show error (backend is down)

5. **Restart backend:**
   ```bash
   cd /Users/ngchenmeng/test/backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

6. **Click Retry button again:**
   - Should load dashboard successfully

**✅ Success Criteria:**
- Error state displays correctly when backend is down
- Retry button works
- Dashboard loads after backend restarts

---

### 9.5 Test CORS (Verify No CORS Errors)

1. **Open browser DevTools** (F12)

2. **Go to Console tab**

3. **Refresh page** (http://localhost:3000)

4. **Check for CORS errors:**
   - Should see NO errors like:
     - ❌ "Access to fetch at 'http://localhost:8000/api/dashboard' from origin 'http://localhost:3000' has been blocked by CORS policy"
   - Should see successful API call

5. **Check Network tab:**
   - Request to `http://localhost:8000/api/dashboard`
   - Status: 200 OK
   - Response headers include CORS headers

**✅ Success Criteria:**
- No CORS errors in console
- API requests succeed
- CORS headers present in response

---

## Testing Checklist

### Step 6: Backend Testing
- [ ] Backend server starts successfully
- [ ] Health endpoint returns `{"status":"ok"}`
- [ ] Dashboard endpoint returns valid JSON
- [ ] JSON structure matches DashboardData (metrics + charts)
- [ ] CORS headers present and correct
- [ ] Backend auto-reloads on file changes
- [ ] API returns updated data after mock_data.py changes

### Step 9: End-to-End Testing
- [ ] Both servers start successfully
- [ ] Frontend loads dashboard from backend
- [ ] Dashboard displays all metrics and charts correctly
- [ ] No console errors
- [ ] Network requests succeed (200 OK)
- [ ] Data updates flow: edit mock_data.py → refresh frontend → changes appear
- [ ] Error handling works: stop backend → error shown → restart → retry works
- [ ] No CORS errors in browser console
- [ ] CORS headers present in network response

---

## Troubleshooting

### Backend won't start
- Check if port 8000 is already in use: `lsof -i :8000`
- Verify dependencies installed: `pip list | grep fastapi`
- Check Python version: `python3 --version` (need 3.12+)

### Frontend shows error
- Verify backend is running: `curl http://localhost:8000/health`
- Check `.env.local` has correct URL: `cat my-app/.env.local`
- Check browser console for specific error messages

### CORS errors
- Verify backend CORS config in `backend/main.py`
- Check backend is running on port 8000
- Verify frontend is on port 3000

### Data not updating
- Check backend auto-reload is working (watch terminal for reload messages)
- Verify you're editing `backend/data/mock_data.py` (not frontend mockData.ts)
- Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

---

## Completion

Once all tests pass:
- ✅ Step 6: Backend Testing - Complete
- ✅ Step 9: End-to-End Testing - Complete
- 🎉 **Overall Progress: 100%**

Update the plan file to mark Steps 6 & 9 as complete!
