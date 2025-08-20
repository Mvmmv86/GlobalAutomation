FROM node:20-alpine AS base
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY packages/shared/package.json ./packages/shared/
COPY apps/worker-recon/package.json ./apps/worker-recon/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY packages/shared ./packages/shared
COPY apps/worker-recon ./apps/worker-recon
COPY tsconfig.base.json ./

# Build shared package
RUN pnpm --filter @tradingview-gateway/shared build

# Build worker-recon
RUN pnpm --filter @tradingview-gateway/worker-recon build

FROM node:20-alpine AS runner
RUN apk add --no-cache libc6-compat
WORKDIR /app

RUN npm install -g pnpm

# Copy built application
COPY --from=base /app/node_modules ./node_modules
COPY --from=base /app/packages ./packages
COPY --from=base /app/apps/worker-recon/dist ./apps/worker-recon/dist
COPY --from=base /app/apps/worker-recon/package.json ./apps/worker-recon/

WORKDIR /app/apps/worker-recon

CMD ["node", "dist/index.js"]