# Quick Start — First-Time Setup

## Step 0: Backend `.env` (required once)

```bash
cp backend/.env.example backend/.env
# Edit: DATABASE_URL=postgresql://user:pass@localhost:5432/welding_sessions
```

See `backend/ENV_SETUP.md` for details.

## Step 1–4: Run the app

→ See **STARTME.md** for backend/frontend start, seed/wipe, and port-kill commands.

## Verify

```bash
curl http://localhost:8000/health   # → {"status":"ok",...}
```

Open http://localhost:3000

## npm scripts (from repo root)

```bash
npm run dev:backend   # Backend (includes ENV=development for seed/wipe)
npm run dev:frontend  # Frontend
npm run dev           # Both at once
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port in use | See STARTME.md |
| `command not found: python` | Use `python3 -m uvicorn main:app --reload` |
| Failed to fetch | Backend running? `curl http://localhost:8000/health` |
| Seed/wipe 403 | Start backend with `ENV=development` (see STARTME.md) |

## Notes

- Backend must run from `backend/` (imports depend on it)
- Keep both terminals open when using manual start
