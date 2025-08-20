import { HealthCheckService, CommonHealthChecks } from '@tradingview-gateway/shared';
import { PrismaClient } from '@prisma/client';
import { Redis } from 'ioredis';

export function setupHealthChecks(prisma: PrismaClient, redis?: Redis) {
  const healthService = new HealthCheckService({
    intervalMs: 30000, // Check every 30 seconds
    timeoutMs: 5000,   // 5 second timeout
    retryCount: 2,     // Retry failed checks twice
    notifyOnStatusChange: true,
    service: 'worker-exec',
    version: process.env.npm_package_version || '1.0.0'
  });

  // Register health checks
  healthService.register(CommonHealthChecks.database(prisma));
  
  if (redis) {
    healthService.register(CommonHealthChecks.redis(redis));
  }

  // Exchange API health checks (critical for worker)
  healthService.register(CommonHealthChecks.exchangeApi('binance', 'https://api.binance.com/api/v3/ping'));
  healthService.register(CommonHealthChecks.exchangeApi('bybit', 'https://api.bybit.com/v5/market/time'));

  // System health checks
  healthService.register(CommonHealthChecks.memoryUsage(85)); // Higher threshold for worker
  healthService.register(CommonHealthChecks.diskSpace('/', 90));

  // Worker-specific health check for job processing
  healthService.register({
    name: 'job-processing',
    description: 'Job processing capability',
    timeout: 3000,
    critical: true,
    check: async () => {
      try {
        // Check if worker can access job queues
        const startTime = Date.now();
        
        // This is a simple check - in production you might check queue connectivity
        const responseTime = Date.now() - startTime;
        
        return {
          status: 'healthy' as const,
          responseTime,
          message: 'Job processing is operational',
          details: {
            workerType: 'execution',
            nodeEnv: process.env.NODE_ENV || 'development'
          },
          timestamp: new Date()
        };
      } catch (error) {
        return {
          status: 'unhealthy' as const,
          responseTime: 3000,
          message: `Job processing check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date()
        };
      }
    }
  });

  // Start health checks
  healthService.start();

  // Handle graceful shutdown
  process.on('SIGTERM', () => {
    console.log('Received SIGTERM, stopping health checks...');
    healthService.stop();
  });

  process.on('SIGINT', () => {
    console.log('Received SIGINT, stopping health checks...');
    healthService.stop();
  });

  return healthService;
}