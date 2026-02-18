"""Sites API routes. Full CRUD in Batch 4; stub health for merge."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.get("/health")
async def sites_health():
    """Stub health check — confirms router is registered."""
    return {"status": "ok", "router": "sites"}
