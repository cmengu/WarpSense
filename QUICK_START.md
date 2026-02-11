# Quick Start Guide - Get Both Servers Running

## 🚀 Fastest Way (2 Terminal Windows)

### Step 1: Open Terminal 1 (Backend)
```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate
# Enable dev seed route (required for Step 3)
export ENV=development
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Wait until you see:**
```
INFO:     Application startup complete.
```

### Step 2: Open Terminal 2 (Frontend)
```bash
cd /Users/ngchenmeng/test
npm run dev
```

**Wait until you see:**
```
✓ Ready in [time]
- Local: http://localhost:3000
```

### Step 3: Seed Mock Sessions (for Replay)
To view session replays, seed mock data into the database (backend must be started with `ENV=development`):
```bash
curl -X POST http://localhost:8000/api/dev/seed-mock-sessions
```

Response: `{"seeded":["sess_expert_001","sess_novice_001"]}`

### Step 4: Open Browser
Go to: **http://localhost:3000**
- Dashboard: http://localhost:3000
- Replay expert: http://localhost:3000/replay/sess_expert_001
- Replay novice: http://localhost:3000/replay/sess_novice_001

---

## ✅ Verify Everything Works

**Test Backend:**
```bash
curl http://localhost:8000/health
```
Should return: `{"status":"ok","message":"Dashboard API is running"}`

**Test Frontend:**
Open browser to: http://localhost:3000

---

## 🔧 Using npm Scripts (Alternative)

**Terminal 1:**
```bash
cd /Users/ngchenmeng/test
npm run dev:backend
```

**Terminal 2:**
```bash
cd /Users/ngchenmeng/test
npm run dev
```

---

## 📝 Important Notes

1. **Keep both terminals open** - Don't close them or press Ctrl+C
2. **Backend runs on port 8000** - Don't change this
3. **Frontend runs on port 3000** - May use 3001 if 3000 is busy
4. **Virtual environment must be activated** for backend to work
5. **Run backend from `backend/`** - Imports (`models`, `data`) require the backend directory as the working directory

---

## 🛠️ Troubleshooting

**"command not found: python"**
```bash
# Use python3 instead
python3 -m uvicorn main:app --reload
```

**"Port already in use"**
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Kill process on port 8000  
lsof -ti:8000 | xargs kill -9
```

**"Failed to fetch" in browser**
- Make sure backend is running (check Terminal 1)
- Verify: `curl http://localhost:8000/health`
- Check browser console for errors

---

## 🎯 URLs

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Seed Mock Data:** POST http://localhost:8000/api/dev/seed-mock-sessions (ENV=development or DEBUG=1)
