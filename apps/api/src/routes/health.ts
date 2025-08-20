import { FastifyPluginAsync } from 'fastify';
import { HealthCheckService, CommonHealthChecks } from '@tradingview-gateway/shared';

const healthRoutes: FastifyPluginAsync = async (fastify) => {
  // Initialize health check service
  const healthService = new HealthCheckService({
    intervalMs: 30000, // Check every 30 seconds
    timeoutMs: 5000,   // 5 second timeout
    retryCount: 2,     // Retry failed checks twice
    notifyOnStatusChange: true,
    service: 'api',
    version: process.env.npm_package_version || '1.0.0'
  });

  // Register health checks
  healthService.register(CommonHealthChecks.database(fastify.prisma));
  
  if (fastify.redis) {
    healthService.register(CommonHealthChecks.redis(fastify.redis));
  }

  // Exchange API health checks
  healthService.register(CommonHealthChecks.exchangeApi('binance', 'https://api.binance.com/api/v3/ping'));
  healthService.register(CommonHealthChecks.exchangeApi('bybit', 'https://api.bybit.com/v5/market/time'));

  // System health checks
  healthService.register(CommonHealthChecks.memoryUsage(80));
  healthService.register(CommonHealthChecks.diskSpace('/', 85));

  // Start health checks
  healthService.start();

  // Graceful shutdown
  fastify.addHook('onClose', async () => {
    healthService.stop();
  });

  // Health check endpoint (detailed)
  fastify.get('/', async (request, reply) => {
    try {
      const health = await healthService.getHealth();
      
      const statusCode = health.status === 'healthy' ? 200 : 
                        health.status === 'degraded' ? 200 : 503;
      
      return reply.status(statusCode).send(health);
    } catch (error) {
      fastify.log.error('Health check failed:', error);
      return reply.status(500).send({
        service: 'api',
        status: 'unhealthy',
        error: 'Health check service error',
        timestamp: new Date()
      });
    }
  });

  // Simple health check endpoint (for load balancers)
  fastify.get('/ready', async (request, reply) => {
    try {
      const health = await healthService.getHealth();
      
      if (health.status === 'unhealthy') {
        return reply.status(503).send({ status: 'not ready' });
      }
      
      return reply.status(200).send({ status: 'ready' });
    } catch (error) {
      return reply.status(503).send({ status: 'not ready' });
    }
  });

  // Liveness probe (for Kubernetes)
  fastify.get('/live', async (request, reply) => {
    // Simple check - if the service can respond, it's alive
    return reply.status(200).send({ 
      status: 'alive',
      timestamp: new Date(),
      uptime: process.uptime()
    });
  });

  // Individual check endpoint
  fastify.get('/check/:checkName', async (request, reply) => {
    const { checkName } = request.params as { checkName: string };
    
    const result = healthService.getCheckHealth(checkName);
    
    if (!result) {
      return reply.status(404).send({
        error: `Health check '${checkName}' not found`
      });
    }
    
    const statusCode = result.status === 'healthy' ? 200 : 
                      result.status === 'degraded' ? 200 : 503;
    
    return reply.status(statusCode).send({
      check: checkName,
      ...result
    });
  });

  // Force run all health checks
  fastify.post('/check', {
    preHandler: [fastify.authenticate], // Require authentication
  }, async (request, reply) => {
    try {
      const health = await healthService.runAllChecks();
      return reply.status(200).send(health);
    } catch (error) {
      fastify.log.error('Manual health check failed:', error);
      return reply.status(500).send({
        error: 'Failed to run health checks'
      });
    }
  });
};

export { healthRoutes };