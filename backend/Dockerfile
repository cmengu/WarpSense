# WarpSense Backend — Multi-stage build for smaller final image
# psycopg2-binary bundles libpq; no apt install needed (avoids Trixie libpq5 conflict)

FROM python:3.11-slim AS builder

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---

FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Add local pip packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user (security)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run migrations then start server. Migrations are idempotent (safe to re-run).
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
