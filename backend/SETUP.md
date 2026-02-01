# Backend Setup Guide

## Current Status
✅ Virtual environment created  
❌ Dependencies not installed (requires internet connection)

## Quick Start (When Online)

### Option 1: Automated Setup Script
```bash
cd /Users/ngchenmeng/test/backend
./setup.sh
```

### Option 2: Manual Setup
```bash
# 1. Navigate to backend directory
cd /Users/ngchenmeng/test/backend

# 2. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn main:app --reload
```

## Verify Installation

After installation, verify everything works:

```bash
# Test imports
python3 -c "from fastapi import FastAPI; print('FastAPI OK')"
python3 -c "from pydantic import BaseModel; print('Pydantic OK')"
python3 -c "import uvicorn; print('Uvicorn OK')"
```

## Start the Server

Once dependencies are installed:

```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate
uvicorn main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Test the Backend

1. **Health Check**: http://localhost:8000/health
2. **Dashboard Data**: http://localhost:8000/api/dashboard
3. **API Docs**: http://localhost:8000/docs

## Troubleshooting

### Network Issues
If you see "nodename nor servname provided, or not known":
- Check your internet connection
- Verify DNS is working: `ping google.com`
- Try using a different network

### Port Already in Use
If port 8000 is busy:
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or use a different port
uvicorn main:app --reload --port 8001
```

Then update `.env.local` in `my-app/`:
```
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### Import Errors
If you see import errors:
```bash
# Make sure you're in the backend directory
cd /Users/ngchenmeng/test/backend

# Activate virtual environment
source venv/bin/activate

# Verify you're using the venv Python
which python  # Should show: .../backend/venv/bin/python
```
