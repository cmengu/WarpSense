"""
AI analyze endpoint. Routes welding queries on-device (Cactus) or cloud (Gemini).

POST /api/ai/analyze — sync via run_in_executor (Cactus blocks).
"""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from function_gemma import generate_hybrid, get_ai_health
from warp_tools import WARP_TOOLS

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/health")
async def get_health():
    """
    AI health: cactus, gemini (key_configured not ok), model_loaded.
    Honest about Gemini — only key presence checked.
    """
    return get_ai_health()


class AnalyzeRequest(BaseModel):
    """Request body for AI analyze."""

    query: str
    offline: bool = False


@router.post("/analyze")
async def post_analyze(body: AnalyzeRequest):
    """
    Analyze welding query. Returns {source, function_calls, text, total_time_ms, latency_ms}.
    Cloud errors: 200 with source="cloud_error", not 503.
    offline=True: zero network — cloud-bound queries return canned offline message.
    """
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: generate_hybrid(
            [{"role": "user", "content": body.query.strip()}],
            WARP_TOOLS,
            offline=body.offline,
        ),
    )
    return result
