# WarpSense Frontend — Multi-stage build
# Builder: install deps + build. Final: production runtime only.

FROM node:20-alpine AS builder

WORKDIR /app

# Build-time API URL (baked into Next.js bundle for browser requests)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Copy package files
COPY package*.json ./

# Install all dependencies (devDeps needed for build: TypeScript, Tailwind, etc.)
RUN npm ci

# Copy source
COPY . .

# Build Next.js for production
RUN npm run build

# Prune devDependencies before final stage (smaller image, less attack surface)
RUN npm prune --omit=dev

# ---

FROM node:20-alpine

WORKDIR /app

# Copy built artifacts from builder (node_modules already pruned)
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/public ./public

# Create non-root user
RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 3000

# Production mode (optimized, no hot reload)
CMD ["npm", "start"]
