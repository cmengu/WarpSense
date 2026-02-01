# Quick Start Guide

## ⚠️ Current Issue: No Internet Connection

The setup requires internet connectivity to install Python packages. 

**Current Status:**
- ✅ Virtual environment created
- ❌ Dependencies need to be installed (requires internet)

## When You Have Internet:

### Step 1: Install Dependencies
```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Start Backend Server
```bash
# Make sure you're in the backend directory and venv is activated
uvicorn main:app --reload
```

### Step 3: Verify It's Working
Open in browser:
- Health: http://localhost:8000/health
- Dashboard: http://localhost:8000/api/dashboard  
- Docs: http://localhost:8000/docs

### Step 4: Start Frontend
In a new terminal:
```bash
cd /Users/ngchenmeng/test/my-app
npm run dev
```

Then visit: http://localhost:3000

## Alternative: Use Setup Script

```bash
cd /Users/ngchenmeng/test/backend
./setup.sh
```

This will automatically:
1. Create venv (if needed)
2. Install all dependencies
3. Verify installation

Then start with:
```bash
./start.sh
```
