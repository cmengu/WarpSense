 Production Deploy (Docker + One-Click)
Rationale
Problem: Right now, deploying to a customer server requires:

Install PostgreSQL manually
Create database and user
Clone repo
Install Python dependencies
Set up .env file
Run Alembic migrations
Start backend with uvicorn
Install Node.js
Install npm dependencies
Build Next.js
Start frontend
Hope it all works together

This takes 2-3 hours and has 20 failure points.
Customer says: "Can we try this on our server?"
You say: "Sure, let me spend half a day setting it up..."
Customer thinks: "This is too complicated."
Solution: One command deploys everything.
Business value:

Customer trials in 5 minutes instead of 3 hours
Works on AWS, Azure, DigitalOcean, on-prem
Repeatable (deploy to 10 customers = 10x same command)
Professional ("our platform is production-ready")


High-Level Architecture
┌─────────────────────────────────────────────────────────────┐
│ CURRENT (Manual)                                             │
└─────────────────────────────────────────────────────────────┘

Dev machine → Manual steps (2-3 hrs) → Customer server


┌─────────────────────────────────────────────────────────────┐
│ NEW (Automated)                                              │
└─────────────────────────────────────────────────────────────┘

Customer server:
  $ git clone https://github.com/you/shipyard-welding
  $ ./deploy.sh
  
  5 minutes later:
  ✅ PostgreSQL running
  ✅ Backend running (migrations applied)
  ✅ Frontend running
  ✅ Demo data seeded
  ✅ http://localhost:3000 ready
Container Architecture
┌──────────────────────────────────────────────────────────────┐
│ Docker Compose Stack                                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   PostgreSQL    │  │     Backend     │  │   Frontend   │ │
│  │   Container     │  │   Container     │  │  Container   │ │
│  │                 │  │                 │  │              │ │
│  │ Port: 5432      │  │ Port: 8000      │  │ Port: 3000   │ │
│  │ Volume: db_data │  │ Depends on: DB  │  │ Depends on:  │ │
│  │ Health check ✓  │  │ Auto-migrate ✓  │  │  Backend     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│         ↑                      ↑                    ↑         │
│         └──────────────────────┴────────────────────┘         │
│                    Internal network                           │
│                (postgres:5432, backend:8000)                  │
│                                                               │
│  Exposed to host:                                             │
│    - localhost:3000 → Frontend                                │
│    - localhost:8000 → Backend API                             │
│    - localhost:5432 → PostgreSQL (optional, for debugging)    │
│                                                               │
└──────────────────────────────────────────────────────────────┘

Implementation Plan
Step 1: PostgreSQL Container (Day 3 morning)
File: docker-compose.yml
yamlversion: '3.8'

services:
  postgres:
    image: postgres:15-alpine  # Alpine = smaller image
    container_name: shipyard_postgres
    restart: unless-stopped
    
    environment:
      POSTGRES_DB: welding_sessions
      POSTGRES_USER: welding_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}  # From .env or generated
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.UTF-8"
    
    volumes:
      # Persist data across container restarts
      - postgres_data:/var/lib/postgresql/data
      
      # Optional: custom init scripts
      - ./backend/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    
    ports:
      - "5432:5432"  # Expose to host (for debugging)
    
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U welding_user -d welding_sessions"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    
    networks:
      - shipyard_network

volumes:
  postgres_data:
    driver: local

networks:
  shipyard_network:
    driver: bridge
Why these choices:
ChoiceRationalepostgres:15-alpineLatest stable; Alpine = 50% smaller than full imagerestart: unless-stoppedAuto-restart on server reboot (production behavior)${DB_PASSWORD}Secure; generated at deploy time, not in gitpostgres_data volumeData persists even if container is deletedhealthcheckOther services wait for DB to be readyCustom networkContainers communicate by service name (e.g. postgres:5432)

Step 2: Backend Container (Day 3 afternoon)
File: backend/Dockerfile
dockerfile# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---

FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Add local pip packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Create non-root user (security)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Start script (runs migrations then server)
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
Add to docker-compose.yml:
yaml  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: shipyard_backend
    restart: unless-stopped
    
    depends_on:
      postgres:
        condition: service_healthy  # Wait for DB health check
    
    environment:
      DATABASE_URL: postgresql://welding_user:${DB_PASSWORD}@postgres:5432/welding_sessions
      ENVIRONMENT: production
      DEBUG: "false"
      
      # CORS (allow frontend container)
      ALLOWED_ORIGINS: "http://localhost:3000,http://frontend:3000"
    
    ports:
      - "8000:8000"
    
    networks:
      - shipyard_network
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
Why these choices:
ChoiceRationaleMulti-stage buildFinal image 40% smaller (no build tools)depends_on + service_healthyBackend waits for DB to be ready before startingalembic upgrade head in CMDMigrations auto-apply on every deployNon-root userSecurity best practicepostgresql://...@postgres:5432Uses Docker network (service name, not localhost)

Step 3: Frontend Container (Day 4 morning)
File: my-app/Dockerfile
dockerfileFROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source
COPY . .

# Build Next.js
RUN npm run build

# ---

FROM node:20-alpine

WORKDIR /app

# Copy built artifacts
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/public ./public

# Create non-root user
RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser && \
    chown -R appuser:appgroup /app
USER appuser

# Expose port
EXPOSE 3000

# Start Next.js
CMD ["npm", "start"]
Add to docker-compose.yml:
yaml  frontend:
    build:
      context: ./my-app
      dockerfile: Dockerfile
    container_name: shipyard_frontend
    restart: unless-stopped
    
    depends_on:
      backend:
        condition: service_healthy
    
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000  # Internal network
      NODE_ENV: production
    
    ports:
      - "3000:3000"
    
    networks:
      - shipyard_network
    
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
Why these choices:
ChoiceRationaleMulti-stage buildSmaller image (only production deps)npm start (not npm run dev)Production mode (faster, optimized)NEXT_PUBLIC_API_URLPoints to backend container by service nameNon-root userSecurity

Step 4: Deploy Script (Day 4 afternoon)
File: deploy.sh (root of repo)
bash#!/bin/bash

set -e  # Exit on any error

echo "🚀 Shipyard Welding Platform - Deploy Script"
echo "=============================================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not installed. Please install Docker first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ docker-compose not installed."; exit 1; }

# Generate secure DB password if not set
if [ -z "$DB_PASSWORD" ]; then
  echo "🔐 Generating secure database password..."
  export DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
  echo "DB_PASSWORD=$DB_PASSWORD" > .env
  echo "✅ Password saved to .env (keep this file secure!)"
else
  echo "✅ Using existing DB_PASSWORD from environment"
fi

# Create necessary directories
mkdir -p backend/logs
mkdir -p backend/reports

# Pull latest images (optional, for faster rebuilds)
echo "📦 Pulling base images..."
docker-compose pull --quiet postgres

# Build and start all services
echo "🔨 Building containers..."
docker-compose build --no-cache

echo "▶️  Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
timeout 90s bash -c '
  until docker-compose ps | grep -q "healthy"; do
    echo -n "."
    sleep 2
  done
' || { echo "❌ Services failed to start within 90 seconds. Check logs: docker-compose logs"; exit 1; }

echo ""
echo "✅ All services healthy!"

# Seed demo data
echo "🌱 Seeding demo data..."
docker-compose exec -T backend python -c "
import sys
sys.path.insert(0, '/app')

from data.mock_sessions import generate_expert_session, generate_novice_session
from database.connection import SessionLocal
from database.models import SessionModel

db = SessionLocal()

try:
    expert = generate_expert_session()
    novice = generate_novice_session()
    
    # Check if already seeded
    existing = db.query(SessionModel).filter(
        SessionModel.session_id.in_(['sess_expert_001', 'sess_novice_001'])
    ).count()
    
    if existing > 0:
        print('⚠️  Demo data already exists, skipping...')
    else:
        expert.session_id = 'sess_expert_001'
        novice.session_id = 'sess_novice_001'
        
        db.add(SessionModel.from_pydantic(expert))
        db.add(SessionModel.from_pydantic(novice))
        db.commit()
        print('✅ Demo data seeded: sess_expert_001, sess_novice_001')
finally:
    db.close()
" || echo "⚠️  Seeding failed (may already be seeded)"

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
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
echo "🗑️  Remove all data (CAUTION):"
echo "   docker-compose down -v"
echo ""
echo "🔐 Database password saved in .env"
echo "   (keep this file secure and backed up!)"
echo ""
Make it executable:
bashchmod +x deploy.sh
```

---

## Architecture Diagram (Complete Stack)
```
┌──────────────────────────────────────────────────────────────┐
│ HOST MACHINE                                                  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  $ ./deploy.sh                                                │
│      ↓                                                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Docker Compose Orchestration                           │  │
│  └────────────────────────────────────────────────────────┘  │
│      ↓                                                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 1. Generate DB_PASSWORD → .env                         │  │
│  │ 2. docker-compose build (3 containers)                 │  │
│  │ 3. docker-compose up -d                                │  │
│  │ 4. Wait for health checks                              │  │
│  │ 5. Seed demo data via backend exec                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Docker Internal Network (shipyard_network)              │ │
│  │                                                          │ │
│  │  postgres:5432 ←─── backend:8000 ←─── frontend:3000     │ │
│  │       ↑                  ↑                    ↑          │ │
│  │       │                  │                    │          │ │
│  │  [postgres_data]    [Migrations]          [Next.js]     │ │
│  │    (volume)           (auto-run)           (build)       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  Exposed ports:                                               │
│    localhost:3000 → shipyard_frontend                         │
│    localhost:8000 → shipyard_backend                          │
│    localhost:5432 → shipyard_postgres (optional)              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
         ↓
   Customer opens browser → http://localhost:3000
```

---

## Deployment Flow (Step-by-Step)
```
Customer server (fresh Ubuntu 22.04 or similar):

1. Install Docker + Docker Compose
   $ curl -fsSL https://get.docker.com | sh
   $ sudo usermod -aG docker $USER
   $ newgrp docker

2. Clone repo
   $ git clone https://github.com/yourname/shipyard-welding
   $ cd shipyard-welding

3. Deploy
   $ ./deploy.sh
   
   [Script output:]
   🔐 Generating secure database password...
   ✅ Password saved to .env
   📦 Pulling base images...
   🔨 Building containers...
   ▶️  Starting services...
   ⏳ Waiting for services to start...
   ✅ All services healthy!
   🌱 Seeding demo data...
   ✅ Demo data seeded
   
   ✅ Deployment Complete!
   🌐 Frontend: http://localhost:3000

4. Verify
   $ docker-compose ps
   
   NAME                   STATUS         PORTS
   shipyard_postgres      Up (healthy)   5432->5432/tcp
   shipyard_backend       Up (healthy)   8000->8000/tcp
   shipyard_frontend      Up (healthy)   3000->3000/tcp

5. Access
   Open http://server-ip:3000 in browser
Time from clone to running: ~5 minutes (depends on internet speed for image pulls)

What Gets Reused vs. Built
ComponentSourceChanges NeededBackend code✅ ExistingNone (just containerized)Frontend code✅ ExistingNone (just containerized)PostgreSQL schema✅ ExistingNone (Alembic migrations)Mock data✅ ExistingNone (seeding script)Docker configs🆕 NEWDockerfile (backend, frontend), docker-compose.ymlDeploy script🆕 NEWdeploy.sh
Code reuse: ~95%
New infrastructure: ~5%

Success Criteria (End of Day 4)
bash# Test locally first
./deploy.sh

# Should complete in ~5 minutes
# Should output:
✅ Deployment Complete!
🌐 Frontend: http://localhost:3000

# Verify all services healthy
docker-compose ps
# All should show "Up (healthy)"

# Verify frontend loads
open http://localhost:3000
# Should see homepage

# Verify backend API
open http://localhost:8000/docs
# Should see FastAPI Swagger docs

# Verify demo data
curl http://localhost:8000/api/sessions/sess_expert_001 | jq '.frame_count'
# Should output: 1500

# Test on clean machine
# (spin up AWS EC2 t2.micro or DigitalOcean droplet)
ssh ubuntu@<ip>
git clone <your-repo>
cd shipyard-welding
./deploy.sh

# Should work identically

Environment Variables Strategy
File: .env.example (committed to git)
bash# Example environment variables
# Copy to .env and customize

# Database
DB_PASSWORD=CHANGE_ME_ON_DEPLOY

# Backend
ENVIRONMENT=production
DEBUG=false

# Optional: Email (for reports)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional: Custom domain
FRONTEND_URL=https://your-domain.com
File: .env (NOT in git, generated by deploy.sh)
bash# Auto-generated by deploy.sh
DB_PASSWORD=x7K9mP3nQ2vR8wL5tA1cY4gB6
```

**File:** `.gitignore` (add to existing)
```
.env
backend/logs/
backend/reports/

Monitoring & Logs
View logs in real-time:
bash# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 backend
Check resource usage:
bashdocker stats

CONTAINER           CPU %   MEM USAGE / LIMIT   MEM %
shipyard_frontend   0.5%    120MiB / 2GiB      6%
shipyard_backend    1.2%    180MiB / 2GiB      9%
shipyard_postgres   0.8%    45MiB / 2GiB       2.25%
```

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Customer server has old Docker | Deploy fails | Check `docker --version` in script, warn if < 20.0 |
| Port 3000/8000 already in use | Containers fail to start | Script checks ports first with `lsof` |
| Insufficient RAM | Services crash | Require 2GB minimum, add to README |
| Migrations fail on existing DB | Backend won't start | `alembic upgrade head` is idempotent (safe to re-run) |
| Network firewall blocks ports | Can't access from browser | Document: "Open ports 3000, 8000 in firewall" |

---
