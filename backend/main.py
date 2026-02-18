"""
FastAPI application entry point
Configures CORS, registers routes, and starts the server
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from database.connection import check_db_connectivity
from routes.aggregate import router as aggregate_router
from routes.dashboard import router as dashboard_router
from routes.dev import router as dev_router
from routes.sessions import router as sessions_router
from routes.thresholds import router as thresholds_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate DB connectivity at startup. Fail fast if unreachable."""
    if not check_db_connectivity():
        raise RuntimeError(
            "Database connectivity check failed at startup. "
            "Verify DATABASE_URL and that PostgreSQL is running."
        )
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
app.include_router(sessions_router, prefix="/api")
app.include_router(thresholds_router, prefix="/api")
# Dev seed route: POST /api/dev/seed-mock-sessions (only when ENV=development or DEBUG=1)
app.include_router(dev_router, prefix="/api/dev", tags=["dev"])


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
