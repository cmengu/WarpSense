#!/bin/bash
# WarpSense Platform — One-Click Deploy
# Usage: ./deploy.sh
# Prerequisites: Docker, Docker Compose (or Docker Compose V2 plugin)

set -e

# Load .env if present (for DB_PASSWORD on re-runs)
[ -f .env ] && set -a && . .env && set +a

echo "🚀 WarpSense Platform - Deploy Script"
echo "=============================================="

# Resolve docker-compose command (V2: docker compose, V1: docker-compose)
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "❌ Docker Compose not found. Install Docker and the Compose plugin, or docker-compose."
  exit 1
fi

# Check Docker
command -v docker >/dev/null 2>&1 || {
  echo "❌ Docker not installed. Please install Docker first."
  exit 1
}

# Exit if ports 3000/8000 are in use (containers will fail to bind)
check_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "❌ Port $port is in use. Free the port or stop the conflicting process before deploying."
      exit 1
    fi
  fi
}
check_port 3000
check_port 8000

# Require Docker 20.0+ (plan requirement; older versions may fail with service_healthy)
DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null | cut -d. -f1)
if [ -n "$DOCKER_VER" ] && [ "$DOCKER_VER" -lt 20 ] 2>/dev/null; then
  echo "⚠️  Docker $DOCKER_VER detected. Docker 20.0+ recommended. Proceed? [y/N]"
  read -r r
  [ "$r" = "y" ] || [ "$r" = "Y" ] || exit 1
fi

# Treat placeholder passwords as unset (user may have copied .env.example)
if [ "$DB_PASSWORD" = "CHANGE_ME_ON_DEPLOY" ] || [ "$DB_PASSWORD" = "CHANGE_ME" ]; then
  echo "⚠️  DB_PASSWORD is still the placeholder. Generating secure password..."
  export DB_PASSWORD=""
fi

# Generate secure DB password if not set; merge into .env (never overwrite other vars)
if [ -z "$DB_PASSWORD" ]; then
  echo "🔐 Generating secure database password..."
  export DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
  # Merge DB_PASSWORD into .env; preserve NEXT_PUBLIC_API_URL and other vars
  if [ -f .env ]; then
    (umask 077; grep -v '^DB_PASSWORD=' .env > .env.tmp 2>/dev/null || true; echo "DB_PASSWORD=$DB_PASSWORD" >> .env.tmp; mv .env.tmp .env)
  else
    (umask 077; echo "DB_PASSWORD=$DB_PASSWORD" > .env)
  fi
  echo "✅ Password saved to .env (keep this file secure!)"
else
  echo "✅ Using existing DB_PASSWORD from environment"
  # Ensure .env exists and has correct permissions; update DB_PASSWORD line only
  if [ -f .env ]; then
    (umask 077; grep -v '^DB_PASSWORD=' .env > .env.tmp 2>/dev/null || true; echo "DB_PASSWORD=$DB_PASSWORD" >> .env.tmp; mv .env.tmp .env)
  else
    (umask 077; echo "DB_PASSWORD=$DB_PASSWORD" > .env)
  fi
fi

# Create necessary directories
mkdir -p backend/logs
mkdir -p backend/reports

# Ensure DB_PASSWORD is set before starting containers
[ -z "$DB_PASSWORD" ] && { echo "❌ DB_PASSWORD not set. Check .env."; exit 1; }

# Pull base images (optional, for faster rebuilds)
echo "📦 Pulling base images..."
$COMPOSE pull postgres 2>/dev/null || true

# Build and start all services (use DEPLOY_CLEAN=1 for full rebuild)
echo "🔨 Building containers..."
if [ "$DEPLOY_CLEAN" = "1" ]; then
  $COMPOSE build --no-cache
else
  $COMPOSE build
fi

echo "▶️  Starting services..."
$COMPOSE up -d

# Wait for ALL services to be healthy (not just any one) — max 60 attempts × 2s = 120s
wait_for_health() {
  local max=60
  for i in $(seq 1 $max); do
    local pg=$($COMPOSE ps postgres --format '{{.Health}}' 2>/dev/null || true)
    local be=$($COMPOSE ps backend --format '{{.Health}}' 2>/dev/null || true)
    local fe=$($COMPOSE ps frontend --format '{{.Health}}' 2>/dev/null || true)
    if [ "$pg" = "healthy" ] && [ "$be" = "healthy" ] && [ "$fe" = "healthy" ]; then
      return 0
    fi
    echo -n "."
    sleep 2
  done
  return 1
}
echo "⏳ Waiting for services to start (up to 120 seconds)..."
if ! wait_for_health; then
  echo ""
  echo "❌ Services failed to start within 120 seconds. Check logs:"
  echo "   $COMPOSE logs"
  exit 1
fi
echo ""
echo "✅ All services healthy!"

# Seed demo data (capture stderr so user sees real errors on failure)
echo "🌱 Seeding demo data..."
SEED_ERR=$(mktemp 2>/dev/null || echo /tmp/seed_err_$$)
if $COMPOSE exec -T backend python scripts/seed_demo_data.py 2>"$SEED_ERR"; then
  echo "✅ Demo data seeded (or already present)"
  rm -f "$SEED_ERR"
else
  echo "⚠️  Seeding failed:"
  cat "$SEED_ERR" 2>/dev/null || true
  rm -f "$SEED_ERR"
  echo "   Continuing without demo data."
fi

# Display status
echo ""
echo "=============================================="
echo "✅ Deployment Complete!"
echo "=============================================="
echo ""
echo "🌐 Access the platform:"
echo "   Frontend:  http://localhost:3000"
echo "   Demo:      http://localhost:3000/demo"
echo "   Backend:   http://localhost:8000/docs"
echo ""
echo "📊 View logs:"
echo "   $COMPOSE logs -f"
echo ""
echo "🛑 Stop services:"
echo "   $COMPOSE down"
echo ""
echo "🗑️  Remove all data (CAUTION):"
echo "   $COMPOSE down -v"
echo ""
echo "🔐 Database password saved in .env"
echo "   (keep this file secure and backed up!)"
echo ""
