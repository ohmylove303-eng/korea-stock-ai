# ============================================================
# K-Stock Frontend — Next.js Standalone
# Google Cloud Run 배포용
# ============================================================

# --- Stage 1: 의존성 설치 ---
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

# --- Stage 2: 빌드 ---
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 빌드 시점에 백엔드 URL 주입 (Cloud Run 배포 후 수정)
ARG NEXT_PUBLIC_API_URL=https://kstock-backend-XXXXX.run.app
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# --- Stage 3: 프로덕션 ---
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# standalone 빌드 결과물만 복사 (최소 이미지)
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
