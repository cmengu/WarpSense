# WarpSense - Welding MVP

Monorepo: ESP32 firmware, iPad app, Next.js frontend, FastAPI backend.

## Quick Start

→ **STARTME.md** — run backend, frontend, seed/wipe

→ **QUICK_START.md** — first-time setup (database, .env, troubleshooting)

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

```bash
# Backend
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Frontend
cd my-app && npm install --legacy-peer-deps
```

```bash
npm run test           # All tests
npm run test:frontend  # Frontend only
npm run test:backend   # Backend only
npm run type-check     # TypeScript check
```

## Scripts (from repo root)

| Script | What it does |
|--------|--------------|
| `npm run dev` | Backend + frontend (concurrent) |
| `npm run dev:backend` | Backend only (port 8000) |
| `npm run dev:frontend` | Frontend only (port 3000) |

Port in use? See **STARTME.md**.
