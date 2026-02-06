# WarpSense - Welding MVP

Monorepo containing ESP32 firmware, iPad app, Next.js frontend, and FastAPI backend.

## Quick Start

### Option 1: Start Both Servers (Recommended)

**Terminal 1 - Backend:**
```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /Users/ngchenmeng/test
npm run dev
```

### Option 2: Use npm scripts

**Start Backend:**
```bash
npm run dev:backend
```

**Start Frontend (in another terminal):**
```bash
npm run dev
```

## URLs

- **Frontend Dashboard:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Project Structure

```
├── esp32_firmware/    # ESP32 Arduino firmware
├── ipad_app/          # React Native/Expo iPad app
├── my-app/            # Next.js frontend dashboard
├── backend/           # FastAPI backend API
├── ai_models/         # AI/ML models
└── data/              # Mock data and fixtures
```

## Development

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd my-app
npm install --legacy-peer-deps
```

### Run Tests
```bash
npm run test              # All tests
npm run test:frontend     # Frontend only
npm run test:backend      # Backend only
npm run type-check         # TypeScript check
```

## Troubleshooting

**Port already in use:**
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

**Backend not starting:**
- Make sure virtual environment is activated: `source backend/venv/bin/activate`
- Check Python version: `python3 --version` (should be 3.11+)
- Install dependencies: `pip install -r backend/requirements.txt`

**Frontend not connecting to backend:**
- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS settings in `backend/main.py`
- Ensure backend is on port 8000 and frontend on port 3000
