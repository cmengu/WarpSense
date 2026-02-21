# AGENT 2 ADDITIONS — paste into backend/main.py
# Insert AFTER this exact line: app.include_router(dev_router, prefix="/api/dev", tags=["dev"])
# Insert BEFORE: @app.get("/health")
# Registers warp-risk endpoint: GET /api/sessions/{session_id}/warp-risk

from routes.predictions import router as predictions_router

app.include_router(predictions_router)
