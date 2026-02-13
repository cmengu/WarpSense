# Backend API

FastAPI server for the welding dashboard. Runs on port 8000.

## Setup

→ See **SETUP.md** in this folder (venv, deps, .env).

→ See **../STARTME.md** for how to run.

## Key endpoints

- `GET /health` — Health check
- `GET /api/dashboard` — Dashboard metrics + charts
- `GET /api/sessions/{id}` — Session replay data
- `POST /api/dev/seed-mock-sessions` — Seed mock data (ENV=development)
- `POST /api/dev/wipe-mock-sessions` — Wipe mock data (ENV=development)

Docs: http://localhost:8000/docs
