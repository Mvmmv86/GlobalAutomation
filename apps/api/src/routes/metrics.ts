import { FastifyPluginAsync } from 'fastify';
import { metrics } from '@tradingview-gateway/shared';

const metricsRoutes: FastifyPluginAsync = async (fastify) => {
  // Metrics endpoint (JSON format)
  fastify.get('/', async (request, reply) => {
    try {
      const allMetrics = metrics.getAllMetrics();
      
      return reply.status(200).send({
        ...allMetrics,
        service: 'api',
        environment: process.env.NODE_ENV || 'development'
      });
    } catch (error) {
      fastify.log.error('Failed to get metrics:', error);
      return reply.status(500).send({
        error: 'Failed to retrieve metrics'
      });
    }
  });

  // Prometheus format endpoint
  fastify.get('/prometheus', async (request, reply) => {
    try {
      const prometheusMetrics = metrics.exportPrometheus();
      
      return reply
        .type('text/plain; version=0.0.4; charset=utf-8')
        .status(200)
        .send(prometheusMetrics);
    } catch (error) {
      fastify.log.error('Failed to export Prometheus metrics:', error);
      return reply.status(500).send('# Failed to export metrics\n');
    }
  });

  // Business metrics endpoint
  fastify.get('/business', async (request, reply) => {
    try {
      const businessMetrics = metrics.getBusinessMetrics();
      
      // Add additional business calculations
      const additionalMetrics = {
        ...businessMetrics,
        totalRevenue: businessMetrics.revenueUSDT,
        avgVolumePerTrade: businessMetrics.tradesExecuted > 0 
          ? businessMetrics.tradingVolume / businessMetrics.tradesExecuted 
          : 0,
        errorRate: businessMetrics.tradesExecuted > 0
          ? (businessMetrics.errorsCount / businessMetrics.tradesExecuted) * 100
          : 0,
        webhooksPerMinute: await calculateWebhooksPerMinute(),
        activeAccountsPercentage: await calculateActiveAccountsPercentage(fastify.prisma)
      };
      
      return reply.status(200).send(additionalMetrics);
    } catch (error) {
      fastify.log.error('Failed to get business metrics:', error);
      return reply.status(500).send({
        error: 'Failed to retrieve business metrics'
      });
    }
  });

  // Individual metric endpoint
  fastify.get('/counter/:name', async (request, reply) => {
    const { name } = request.params as { name: string };
    const { labels } = request.query as { labels?: string };
    
    try {
      let parsedLabels: Record<string, string> | undefined;
      
      if (labels) {
        parsedLabels = JSON.parse(labels);
      }
      
      const value = metrics.getCounter(name, parsedLabels);
      
      return reply.status(200).send({
        name,
        value,
        type: 'counter',
        labels: parsedLabels
      });
    } catch (error) {
      return reply.status(400).send({
        error: 'Invalid metric name or labels'
      });
    }
  });

  fastify.get('/gauge/:name', async (request, reply) => {
    const { name } = request.params as { name: string };
    const { labels } = request.query as { labels?: string };
    
    try {
      let parsedLabels: Record<string, string> | undefined;
      
      if (labels) {
        parsedLabels = JSON.parse(labels);
      }
      
      const value = metrics.getGauge(name, parsedLabels);
      
      if (value === undefined) {
        return reply.status(404).send({
          error: `Gauge '${name}' not found`
        });
      }
      
      return reply.status(200).send({
        name,
        value,
        type: 'gauge',
        labels: parsedLabels
      });
    } catch (error) {
      return reply.status(400).send({
        error: 'Invalid metric name or labels'
      });
    }
  });

  fastify.get('/histogram/:name', async (request, reply) => {
    const { name } = request.params as { name: string };
    const { labels } = request.query as { labels?: string };
    
    try {
      let parsedLabels: Record<string, string> | undefined;
      
      if (labels) {
        parsedLabels = JSON.parse(labels);
      }
      
      const summary = metrics.getHistogramSummary(name, parsedLabels);
      
      if (!summary) {
        return reply.status(404).send({
          error: `Histogram '${name}' not found`
        });
      }
      
      return reply.status(200).send({
        name,
        summary,
        type: 'histogram',
        labels: parsedLabels
      });
    } catch (error) {
      return reply.status(400).send({
        error: 'Invalid metric name or labels'
      });
    }
  });

  // Reset metrics endpoint (admin only)
  fastify.post('/reset', {
    preHandler: [fastify.authenticate], // Require authentication
  }, async (request, reply) => {
    try {
      metrics.reset();
      
      fastify.log.warn('Metrics reset by user', { 
        userId: (request as any).userId 
      });
      
      return reply.status(200).send({
        message: 'Metrics reset successfully',
        timestamp: new Date()
      });
    } catch (error) {
      fastify.log.error('Failed to reset metrics:', error);
      return reply.status(500).send({
        error: 'Failed to reset metrics'
      });
    }
  });

  // Live metrics streaming (Server-Sent Events)
  fastify.get('/stream', async (request, reply) => {
    reply.raw.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control'
    });

    // Send initial metrics
    const initialMetrics = metrics.getAllMetrics();
    reply.raw.write(`data: ${JSON.stringify(initialMetrics)}\n\n`);

    // Set up listener for metric updates
    const metricsListener = (data: any) => {
      reply.raw.write(`data: ${JSON.stringify(data)}\n\n`);
    };

    metrics.on('metrics', metricsListener);

    // Send keepalive every 30 seconds
    const keepAlive = setInterval(() => {
      reply.raw.write(': keepalive\n\n');
    }, 30000);

    // Cleanup on connection close
    request.raw.on('close', () => {
      metrics.off('metrics', metricsListener);
      clearInterval(keepAlive);
    });
  });
};

/**
 * Helper function to calculate webhooks per minute
 */
async function calculateWebhooksPerMinute(): Promise<number> {
  const webhooksTotal = metrics.getCounter('webhooks_received_total');
  const uptime = metrics.getAllMetrics().uptime; // in seconds
  
  if (uptime === 0) return 0;
  
  const minutes = uptime / 60;
  return Math.round((webhooksTotal / minutes) * 100) / 100; // Round to 2 decimals
}

/**
 * Helper function to calculate active accounts percentage
 */
async function calculateActiveAccountsPercentage(prisma: any): Promise<number> {
  try {
    const totalAccounts = await prisma.exchangeAccount.count();
    const activeAccounts = await prisma.exchangeAccount.count({
      where: { isActive: true }
    });
    
    if (totalAccounts === 0) return 0;
    
    return Math.round((activeAccounts / totalAccounts) * 100 * 100) / 100; // Round to 2 decimals
  } catch (error) {
    console.error('Failed to calculate active accounts percentage:', error);
    return 0;
  }
}

export { metricsRoutes };