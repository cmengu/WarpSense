# AGENT 3 ADDITIONS — paste into backend/main.py
#
# 1. Add import (with other route imports, e.g. after routes.sites):
#    from routes import narratives
#
# 2. Add router registration BEFORE app.include_router(sessions_router, ...):
#    app.include_router(narratives.router)
#
# Full snippet to insert before sessions_router line:
from routes import narratives
app.include_router(narratives.router)
