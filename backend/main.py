"""
FastAPI application entry point
Configures CORS, registers routes, and starts the server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from routes.dashboard import router as dashboard_router
from routes.sessions import router as sessions_router

# Initialize FastAPI app
app = FastAPI(
    title="Dashboard API",
    description="API for serving dashboard data to Next.js frontend",
    version="1.0.0"
)

# Configure CORS middleware
# This allows the Next.js frontend (localhost:3000) to call this backend (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register routes
app.include_router(dashboard_router)
# Register sessions routes with /api prefix (routes defined as /sessions, becomes /api/sessions)
app.include_router(sessions_router, prefix="/api")


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    Useful for verifying the server is running
    """
    return {"status": "ok", "message": "Dashboard API is running"}


if __name__ == "__main__":
    import uvicorn
    # Run with auto-reload for development
    # In production, use: uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
