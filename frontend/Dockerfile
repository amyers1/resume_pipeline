# frontend/Dockerfile

# 1. Build Stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first to leverage caching
COPY package.json package-lock.json ./

# Install dependencies (use --frozen-lockfile for consistency)
# We also forcefully install the correct linux binary for esbuild to avoid platform errors
RUN npm ci && npm rebuild esbuild

# Copy source code
COPY . .

# ARGS for build time (These must be defined to bake them in)
# We default to empty so it uses the relative path logic we set up in nginx
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Build the app
RUN npm run build

# 2. Serve Stage
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
