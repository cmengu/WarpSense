# WarpSense Backend — multi-stage build
# Build context: repo root. Use: docker build -f backend/Dockerfile .
# psycopg2-binary bundles libpq; no apt install needed (avoids Trixie libpq5 conflict)

FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---

FROM python:3.11-slim-bookworm

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY backend/ .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
