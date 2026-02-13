# Environment Variables — Where & Why

## TL;DR

**Backend `.env` lives at: `backend/.env`**

```bash
# From project root:
cp backend/.env.example backend/.env
# Edit backend/.env and set DATABASE_URL

# OR from backend/:
cd backend
cp .env.example .env
# Edit .env and set DATABASE_URL
```

---

## Why `.env` Is Hard to Find

| Reason | Explanation |
|--------|-------------|
| **Gitignored** | `.env` is in `.gitignore` — it never exists in the repo. You must create it. |
| **Multiple apps** | Backend uses `backend/.env`; frontend uses `my-app/.env.local`. Different paths. |
| **Path confusion** | From `backend/`, use `./.env` or `.env`. From project root, use `backend/.env`. `backend/backend/.env` is wrong. |

---

## Rationale

- **Security**: `.env` holds secrets (DB passwords, API keys). Committing it would expose them.
- **Local config**: Each dev has different DATABASE_URL (local Postgres vs Docker vs cloud).
- **Standard practice**: Never commit `.env`; commit `.env.example` as a template.

---

## File Locations

| App | File | Purpose |
|-----|------|---------|
| Backend | `backend/.env` | DATABASE_URL, ENV, CORS_ORIGINS |
| Frontend | `my-app/.env.local` | NEXT_PUBLIC_API_URL, NEXT_PUBLIC_ALERT_WEBHOOK_URL (optional) |

---

## Frontend: Replay Failure Alerts

Set `NEXT_PUBLIC_ALERT_WEBHOOK_URL` to receive immediate alerts when a replay fails to load:

```
NEXT_PUBLIC_ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

The logger POSTs JSON: `{ event: "replay_load_failed", sessionId, error, timestamp }`.
Supports Slack incoming webhooks, PagerDuty, or any HTTP endpoint.

---

## How Backend Loads It

`database/connection.py` resolves the path as:

```
Path(__file__).resolve().parent.parent / ".env"
= backend/.env  (regardless of current working directory)
```

So the file **must** be at `backend/.env` — not project root, not `backend/config/.env`.
