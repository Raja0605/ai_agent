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

# Where the browser should reach the API. Defaults to the same-origin path
# served by the nginx reverse proxy in stage 2, so the built page works from
# any device that can load it — not only from the Docker host, which is what
# a baked-in http://localhost:8000 limited it to.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build production bundle (runs `tsc --noEmit` first — see package.json)
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

# Health check to ensure server is responsive.
#
# 127.0.0.1, not "localhost": busybox wget resolves localhost to ::1 first and
# nginx's `listen 80` binds IPv4 only, so the probe got "connection refused"
# and the container sat permanently unhealthy while serving traffic perfectly.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
