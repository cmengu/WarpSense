# Quick Start Guide - Get Both Servers Running

## 🚀 Fastest Way (2 Terminal Windows)

### Step 1: Open Terminal 1 (Backend)
```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate
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

### Step 3: Open Browser
Go to: **http://localhost:3000**

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
