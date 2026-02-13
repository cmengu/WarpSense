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

## Environment Setup

**Location**: `backend/.env` (relative to project root). From inside `backend/`, the file is `.env`.

Create it from the template:

```bash
cd backend
cp .env.example .env
# Edit .env: set DATABASE_URL=postgresql://user:password@localhost:5432/welding_sessions
```

Without this, the server will fail with `ValueError: DATABASE_URL is not set`.  
See `backend/ENV_SETUP.md` for rationale and path details.

## Verify Installation

After installation, verify everything works:

```bash
# Test imports
python3 -c "from fastapi import FastAPI; print('FastAPI OK')"
python3 -c "from pydantic import BaseModel; print('Pydantic OK')"
python3 -c "import uvicorn; print('Uvicorn OK')"
```

## Start the Server

→ See **../STARTME.md** for run commands (includes ENV=development for seed/wipe).

```bash
cd backend
source venv/bin/activate
export ENV=development
uvicorn main:app --reload --host 0.0.0.0 --port 8000
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
→ See **../STARTME.md** for kill commands. Or use a different port:
```bash
uvicorn main:app --reload --port 8001
```
Then update `NEXT_PUBLIC_API_URL` in `my-app/.env.local`:
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

### Python Path for Mock Data & Tests
The backend uses `models`, `data`, `database` as top-level imports. These resolve when:
- **Running the server**: Start from `backend/` so `uvicorn main:app` has backend as the working directory.
- **Running tests**: Use `PYTHONPATH=.` from `backend/`, e.g. `PYTHONPATH=. pytest tests/`
- **Running mock_sessions**: From `backend/`, `python -c "from data.mock_sessions import generate_expert_session"` works.
