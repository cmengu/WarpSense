# WarpSense — Shipyard Welding Platform

Vertical AI for shipyard welding: real-time feedback, post-session replay, and AI-generated coach reports. Built to replace floor QC inspection and post-shift reporting with always-on, data-driven analysis.

## What This Does

- **Real-time feedback** — Alerts when torch angle, heat, or electrical parameters drift out of spec
- **Post-session analysis** — Exact replay with thermal heatmaps, torch angle graphs, expert vs novice comparison
- **AI coach reports** — Session narratives and warp-risk prediction, ready to forward or PDF

See [.cursor/product/vision.md](.cursor/product/vision.md) for the full product vision, build order, and dual-audience filter.

## Quick Start

| Step | Action |
|------|--------|
| 1 | **STARTME.md** — run backend, frontend, seed/wipe |
| 2 | **QUICK_START.md** — first-time setup (database, .env, troubleshooting) |

```bash
./start-all.sh   # Backend + frontend (or see STARTME.md for manual)
```

## Project Structure

```
├── esp32_firmware/    # ESP32 Arduino firmware (sensor capture)
├── ipad_app/          # React Native/Expo iPad app
├── my-app/            # Next.js frontend dashboard
├── backend/           # FastAPI backend API
├── ai_models/         # AI/ML models (warp prediction ONNX, etc.)
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
| `./start-all.sh` | Backend + frontend (concurrent) |
| `npm run dev` | Same via npm |
| `npm run dev:backend` | Backend only (port 8000) |
| `npm run dev:frontend` | Frontend only (port 3000) |

Port in use? See **STARTME.md**.
