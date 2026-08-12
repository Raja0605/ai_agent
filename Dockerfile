# ==========================================
# Stage 1: Build Phase
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package descriptors
COPY package*.json ./

# Install dependencies cleanly
RUN npm ci

# Copy source code and config
COPY . .

# Build production bundle
RUN npm run build

# ==========================================
# Stage 2: Production Nginx Server Phase
# ==========================================
FROM nginx:alpine AS runner

# Copy custom Nginx SPA configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Health check to ensure server is responsive
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
