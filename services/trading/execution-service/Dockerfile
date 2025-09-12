FROM node:20-alpine AS base
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY packages/shared/package.json ./packages/shared/
COPY apps/worker-exec/package.json ./apps/worker-exec/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY packages/shared ./packages/shared
COPY apps/worker-exec ./apps/worker-exec
COPY tsconfig.base.json ./

# Build shared package
RUN pnpm --filter @tradingview-gateway/shared build

# Build worker-exec
RUN pnpm --filter @tradingview-gateway/worker-exec build

FROM node:20-alpine AS runner
RUN apk add --no-cache libc6-compat
WORKDIR /app

RUN npm install -g pnpm

# Copy built application
COPY --from=base /app/node_modules ./node_modules
COPY --from=base /app/packages ./packages
COPY --from=base /app/apps/worker-exec/dist ./apps/worker-exec/dist
COPY --from=base /app/apps/worker-exec/package.json ./apps/worker-exec/

WORKDIR /app/apps/worker-exec

CMD ["node", "dist/index.js"]