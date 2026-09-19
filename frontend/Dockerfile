# ==============================================================================
# NowCast Fusion — React 19 GIS Command Center
# Multi-stage production build (Node 20 -> Nginx Alpine)
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# ── Production Server ─────────────────────────────────────────────────────────
FROM nginx:alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
