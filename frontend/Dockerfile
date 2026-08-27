# ==========================================
# Stage 1: Dependencies
# ==========================================

FROM node:20-alpine AS deps

RUN apk add --no-cache libc6-compat

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install --no-audit --no-fund --legacy-peer-deps


# ==========================================
# Stage 2: Builder
# ==========================================

FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Disable telemetry and font optimization during build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_FONT_GOOGLE_MOCKED=true

RUN npm run build


# ==========================================
# Stage 3: Production Runner
# ==========================================

FROM node:20-alpine AS runner

WORKDIR /app

RUN addgroup -g 1001 -S app \
    && adduser -S app -u 1001 -G app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# IMPORTANT:
# Make Next.js standalone server listen on all interfaces.
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=builder --chown=app:app /app/public ./public
COPY --from=builder --chown=app:app /app/.next/standalone ./
COPY --from=builder --chown=app:app /app/.next/static ./.next/static

USER app

EXPOSE 3000

CMD ["node", "server.js", "-H", "0.0.0.0"]