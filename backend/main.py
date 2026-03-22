"""
FastAPI application entry point
Configures CORS, registers routes, and starts the server
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware


def _require_project_venv_if_present() -> None:
    """
    Fail fast when `backend/venv` exists but the interpreter is not that venv
    (e.g. conda `base` `python`). Avoids opaque errors like ModuleNotFoundError: psycopg2.

    Uses sys.prefix (venv root), not Path(sys.executable).resolve(): the venv's python
    binary is often a symlink to the base interpreter, so resolving the executable
    incorrectly points outside backend/venv.
    """
    backend_root = Path(__file__).resolve().parent
    venv_root = (backend_root / "venv").resolve()
    venv_bin = venv_root / "bin"
    if not venv_bin.is_dir():
        return
    prefix = Path(sys.prefix).resolve()
    if not prefix.is_relative_to(venv_root):
        raise RuntimeError(
            "Wrong Python interpreter: backend/venv exists but you are not using it.\n"
            f"  sys.prefix: {prefix}\n"
            f"  Expected under: {venv_root}\n"
            f"  sys.executable: {sys.executable}\n"
            "  Fix:     cd backend && source venv/bin/activate && "
            "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000\n"
            "  Or from repo root: npm run dev:backend"
        ) from None


_require_project_venv_if_present()

from database.connection import check_db_connectivity
from routes.ai import router as ai_router
from routes.aggregate import router as aggregate_router
from routes.annotations import router as annotations_router
from routes.dashboard import router as dashboard_router
from routes.dev import router as dev_router
from routes import narratives
from routes.predictions import router as predictions_router
from routes.sessions import router as sessions_router
from routes.sites import router as sites_router
from routes.realtime import router as realtime_router
from routes.thresholds import router as thresholds_router
from routes.welders import router as welders_router
from routes.warp_analysis import router as warp_analysis_router
from services.warp_service import init_warp_components

from init_system import run as init_system_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate DB connectivity at startup. Fail fast if unreachable."""
    if not check_db_connectivity():
        raise RuntimeError(
            "Database connectivity check failed at startup. "
            "Verify DATABASE_URL and that PostgreSQL is running."
        )
    # KB + seed must run before init_warp_components — WarpSenseGraph loads ChromaDB on init
    try:
        init_system_run()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("[INIT] Startup init failed — %s", e)
        # Non-fatal: API still boots, manual init possible
    init_warp_components()
    yield
    # Shutdown: nothing to clean up for DB (engine manages connections)


# Initialize FastAPI app
app = FastAPI(
    title="Dashboard API",
    description="API for serving dashboard data to Next.js frontend",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS middleware
# CORS_ORIGINS: comma-separated list. Default includes common local dev ports (3000, 3001).
_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002",
).strip().split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register routes
app.include_router(dashboard_router)
# Aggregate BEFORE sessions so /api/sessions/aggregate matches aggregate route
app.include_router(aggregate_router, prefix="/api")
# Narratives BEFORE sessions so /api/sessions/{id}/narrative matches
# Annotations BEFORE sessions so /api/sessions/{id}/annotations matches
app.include_router(narratives.router)
app.include_router(annotations_router)
# WarpSense AI analysis: POST /api/sessions/{id}/analyse, GET /api/sessions/{id}/reports, GET /api/health/warp
app.include_router(warp_analysis_router)
app.include_router(sessions_router, prefix="/api")
app.include_router(thresholds_router, prefix="/api")
app.include_router(welders_router)
app.include_router(sites_router)
# Warp risk: GET /api/sessions/{session_id}/warp-risk
app.include_router(predictions_router)
# AI: POST /api/ai/analyze
app.include_router(ai_router)
# Dev seed route: POST /api/dev/seed-mock-sessions (only when ENV=development or DEBUG=1)
app.include_router(dev_router, prefix="/api/dev", tags=["dev"])
# Realtime: WebSocket + internal POST (development only)
if os.getenv("ENV") == "development" or os.getenv("DEBUG") == "1":
    app.include_router(realtime_router, tags=["realtime"])


@app.get("/health")
async def health_check(response: Response):
    """
    Health check endpoint. Verifies server and database connectivity.
    Returns 503 if database is unreachable (for load balancer / orchestrator).
    """
    if not check_db_connectivity():
        response.status_code = 503
        return {
            "status": "degraded",
            "message": "Database unreachable",
        }
    return {"status": "ok", "message": "Dashboard API is running"}


if __name__ == "__main__":
    import uvicorn

    # Run with auto-reload for development
    # In production, use: uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
