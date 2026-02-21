# AGENT 1 ADDITIONS — paste into backend/main.py
#
# PASTE LOCATION (anchor-based; survives line drift):
#   PASTE AFTER:  the last line containing  app.include_router(
#   PASTE BEFORE: the line containing  @app.get("/health")
#
# Find lines: grep -n "include_router\|@app.get" backend/main.py
# Paste the two lines below immediately after the last include_router line (e.g. dev_router), before @app.get.
#
# Result: sites_router registered with other routers; before health route.

from routes.sites import router as sites_router

app.include_router(sites_router)
