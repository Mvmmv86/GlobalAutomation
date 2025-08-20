import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import { logger } from '@tradingview-gateway/shared';
import * as Sentry from '@sentry/node';

import { webhookRoutes } from './routes/webhook';
import { healthRoutes } from './routes/health';
import { authRoutes } from './routes/auth';
import { accountRoutes } from './routes/accounts';
import { jobRoutes } from './routes/jobs';
import { strategyMappingRoutes } from './routes/strategy-mappings';
import { QueueService } from './services/queue';
import { authenticate } from './middleware/auth';

const PORT = parseInt(process.env.PORT || '3001', 10);
const NODE_ENV = process.env.NODE_ENV || 'development';

// Initialize Sentry
if (process.env.SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: NODE_ENV,
  });
}

async function buildServer() {
  const server = Fastify({
    logger: NODE_ENV === 'production' ? true : {
      transport: {
        target: 'pino-pretty',
        options: {
          colorize: true,
        },
      },
    },
  });

  // Initialize database
  const prisma = new PrismaClient({
    log: NODE_ENV === 'development' ? ['query', 'info', 'warn', 'error'] : ['error'],
  });

  // Initialize Redis
  const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
    retryDelayOnFailover: 100,
    maxRetriesPerRequest: 3,
  });

  // Initialize queue service
  const queueService = new QueueService(redis);

  // Make services available to routes
  server.decorate('prisma', prisma);
  server.decorate('redis', redis);
  server.decorate('queueService', queueService);
  server.decorate('authenticate', authenticate);

  // Register plugins
  await server.register(helmet, {
    crossOriginEmbedderPolicy: false,
  });

  await server.register(cors, {
    origin: NODE_ENV === 'production' 
      ? ['https://yourdomain.com'] 
      : true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    credentials: true,
  });

  await server.register(rateLimit, {
    max: 100,
    timeWindow: '1 minute',
    errorResponseBuilder: (req, context) => ({
      code: 429,
      error: 'Rate limit exceeded',
      message: `Too many requests, retry after ${Math.round(context.after)} seconds`,
    }),
  });

  // Register routes
  await server.register(healthRoutes, { prefix: '/health' });
  await server.register(webhookRoutes, { prefix: '/webhook' });
  await server.register(authRoutes, { prefix: '/auth' });
  await server.register(accountRoutes, { prefix: '/accounts' });
  await server.register(jobRoutes, { prefix: '/jobs' });
  await server.register(strategyMappingRoutes, { prefix: '/strategy-mappings' });

  // Error handler
  server.setErrorHandler((error, request, reply) => {
    if (process.env.SENTRY_DSN) {
      Sentry.captureException(error);
    }
    
    server.log.error(error);
    
    const statusCode = error.statusCode || 500;
    reply.status(statusCode).send({
      error: 'Internal Server Error',
      message: NODE_ENV === 'development' ? error.message : 'Something went wrong',
    });
  });

  // Graceful shutdown
  const gracefulShutdown = async () => {
    server.log.info('Shutting down gracefully...');
    
    try {
      await server.close();
      await prisma.$disconnect();
      redis.disconnect();
      process.exit(0);
    } catch (error) {
      server.log.error('Error during shutdown:', error);
      process.exit(1);
    }
  };

  process.on('SIGINT', gracefulShutdown);
  process.on('SIGTERM', gracefulShutdown);

  return server;
}

async function start() {
  try {
    const server = await buildServer();
    await server.listen({ port: PORT, host: '0.0.0.0' });
    logger.info(`Server listening on port ${PORT}`);
  } catch (error) {
    logger.error('Error starting server:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  start();
}

export { buildServer };