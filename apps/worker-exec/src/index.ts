import { Worker, Job } from 'bullmq';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import { logger, JobPayload } from '@tradingview-gateway/shared';
import * as Sentry from '@sentry/node';

import { TradeExecutionService } from './services/execution';

const NODE_ENV = process.env.NODE_ENV || 'development';

// Initialize Sentry
if (process.env.SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: NODE_ENV,
  });
}

async function startWorker() {
  // Initialize database
  const prisma = new PrismaClient({
    log: NODE_ENV === 'development' ? ['error'] : ['error'],
  });

  // Initialize Redis
  const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
    retryDelayOnFailover: 100,
    maxRetriesPerRequest: 3,
  });

  // Initialize trade execution service
  const executionService = new TradeExecutionService(prisma);

  // Create worker
  const worker = new Worker(
    'exec',
    async (job: Job<JobPayload>) => {
      logger.info(`Processing job ${job.id} - Alert: ${job.data.alertId}`);
      
      try {
        // Update job status to processing
        await prisma.job.update({
          where: { alertId: job.data.alertId },
          data: { 
            status: 'processing',
            retryCount: job.data.retryCount || 0,
          },
        });

        // Execute trade
        await executionService.executeTradeWebhook(job.data);

        // Update job status to completed
        await prisma.job.update({
          where: { alertId: job.data.alertId },
          data: { 
            status: 'completed',
            completedAt: new Date(),
          },
        });

        logger.info(`Job completed: ${job.data.alertId}`);
        
      } catch (error) {
        logger.error(`Job failed: ${job.data.alertId}`, error);
        
        // Update job status to failed
        await prisma.job.update({
          where: { alertId: job.data.alertId },
          data: { 
            status: 'failed',
            lastError: error instanceof Error ? error.message : String(error),
            retryCount: (job.data.retryCount || 0) + 1,
          },
        });

        if (process.env.SENTRY_DSN) {
          Sentry.captureException(error, {
            tags: {
              alertId: job.data.alertId,
              accountId: job.data.accountId,
            },
          });
        }
        
        throw error; // Re-throw to trigger BullMQ retry logic
      }
    },
    {
      connection: redis,
      concurrency: parseInt(process.env.WORKER_CONCURRENCY || '5', 10),
    }
  );

  // Worker event handlers
  worker.on('completed', (job) => {
    logger.info(`Job completed: ${job.id}`);
  });

  worker.on('failed', (job, err) => {
    logger.error(`Job failed: ${job?.id}`, err);
  });

  worker.on('error', (err) => {
    logger.error('Worker error:', err);
  });

  // Graceful shutdown
  const gracefulShutdown = async () => {
    logger.info('Shutting down worker gracefully...');
    
    try {
      await worker.close();
      await prisma.$disconnect();
      redis.disconnect();
      process.exit(0);
    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  };

  process.on('SIGINT', gracefulShutdown);
  process.on('SIGTERM', gracefulShutdown);

  logger.info('Worker started and waiting for jobs...');
}

startWorker().catch((error) => {
  logger.error('Failed to start worker:', error);
  process.exit(1);
});