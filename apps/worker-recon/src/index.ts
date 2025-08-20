import { Worker, Job } from 'bullmq';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import { logger } from '@tradingview-gateway/shared';
import * as Sentry from '@sentry/node';

import { ReconciliationService } from './services/reconciliation';

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

  // Initialize reconciliation service
  const reconService = new ReconciliationService(prisma, redis);

  // Create worker
  const worker = new Worker(
    'recon',
    async (job: Job<{ accountId: string }>) => {
      logger.info(`Processing reconciliation job ${job.id} for account ${job.data.accountId}`);
      
      try {
        await reconService.reconcileAccount(job.data.accountId);
        logger.info(`Reconciliation completed for account: ${job.data.accountId}`);
        
      } catch (error) {
        logger.error(`Reconciliation failed for account ${job.data.accountId}:`, error);
        
        if (process.env.SENTRY_DSN) {
          Sentry.captureException(error, {
            tags: {
              accountId: job.data.accountId,
            },
          });
        }
        
        throw error; // Re-throw to trigger BullMQ retry logic
      }
    },
    {
      connection: redis,
      concurrency: parseInt(process.env.RECON_WORKER_CONCURRENCY || '3', 10),
    }
  );

  // Add recurring reconciliation jobs
  await reconService.scheduleRecurringRecon(worker);

  // Worker event handlers
  worker.on('completed', (job) => {
    logger.info(`Reconciliation job completed: ${job.id}`);
  });

  worker.on('failed', (job, err) => {
    logger.error(`Reconciliation job failed: ${job?.id}`, err);
  });

  worker.on('error', (err) => {
    logger.error('Reconciliation worker error:', err);
  });

  // Graceful shutdown
  const gracefulShutdown = async () => {
    logger.info('Shutting down reconciliation worker gracefully...');
    
    try {
      await reconService.cleanup();
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

  logger.info('Reconciliation worker started and waiting for jobs...');
}

startWorker().catch((error) => {
  logger.error('Failed to start reconciliation worker:', error);
  process.exit(1);
});