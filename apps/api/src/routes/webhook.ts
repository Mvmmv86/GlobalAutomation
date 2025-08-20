import { FastifyPluginAsync } from 'fastify';
import { TradingViewWebhookSchema, verifyHMAC } from '@tradingview-gateway/shared';
import { AccountSelectionService } from '../services/account-selection';

const webhookRoutes: FastifyPluginAsync = async (fastify) => {
  const TV_WEBHOOK_SECRET = process.env.TV_WEBHOOK_SECRET;
  
  if (!TV_WEBHOOK_SECRET) {
    throw new Error('TV_WEBHOOK_SECRET environment variable is required');
  }

  // Public webhook (no authentication)
  fastify.post('/tv', {
    config: {
      rateLimit: {
        max: 200,
        timeWindow: '1 minute',
      },
    },
    preHandler: async (request, reply) => {
      // Verify HMAC signature
      const signature = request.headers['x-tradingview-signature'] as string;
      const body = JSON.stringify(request.body);
      
      if (!signature || !verifyHMAC(body, signature, TV_WEBHOOK_SECRET)) {
        reply.status(401).send({ error: 'Invalid signature' });
        return;
      }
    },
  }, async (request, reply) => {
    try {
      // Validate payload
      const webhook = TradingViewWebhookSchema.parse(request.body);
      
      // Check for duplicate alert (idempotency)
      const existingJob = await fastify.prisma.job.findUnique({
        where: { alertId: webhook.alert_id },
      });
      
      if (existingJob) {
        fastify.log.info(`Duplicate alert ignored: ${webhook.alert_id}`);
        return reply.status(200).send({ 
          message: 'Alert already processed',
          jobId: existingJob.id,
        });
      }
      
      // Smart account selection with multiple strategies
      const accountSelection = new AccountSelectionService(fastify.prisma);
      const selectionResult = await accountSelection.selectAccount({
        webhook
        // Note: For public webhooks, we don't have userId
        // User-specific webhooks would need authentication
      });
      
      if (!selectionResult.success || !selectionResult.account) {
        fastify.log.error('Account selection failed', {
          webhook: webhook.alert_id,
          exchange: webhook.exchange,
          reason: selectionResult.reason
        });
        
        return reply.status(400).send({ 
          error: 'No suitable account found',
          exchange: webhook.exchange,
          reason: selectionResult.reason,
          accountId: webhook.account_id
        });
      }

      const account = selectionResult.account;
      
      fastify.log.info('Account selected successfully', {
        accountId: account.id,
        accountName: account.name,
        selectionReason: account.selectionReason,
        alertId: webhook.alert_id
      });
      
      // Create job record
      const job = await fastify.prisma.job.create({
        data: {
          alertId: webhook.alert_id,
          accountId: account.id,
          userId: account.userId,
          webhook: webhook as any,
          status: 'pending',
        },
      });
      
      // Add to execution queue
      await fastify.queueService.addExecJob({
        alertId: webhook.alert_id,
        accountId: account.id,
        webhook,
        retryCount: 0,
      });
      
      fastify.log.info(`Webhook processed: ${webhook.alert_id}`);
      
      return reply.status(200).send({
        message: 'Webhook received and queued',
        jobId: job.id,
        alertId: webhook.alert_id,
      });
      
    } catch (error) {
      fastify.log.error('Webhook processing error:', error);
      
      if (error instanceof Error && error.message.includes('Validation')) {
        return reply.status(400).send({
          error: 'Invalid webhook payload',
          details: error.message,
        });
      }
      
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // Authenticated webhook (user-specific)
  fastify.post('/tv/user', {
    preHandler: [fastify.authenticate],
    config: {
      rateLimit: {
        max: 500, // Higher limit for authenticated users
        timeWindow: '1 minute',
      },
    },
  }, async (request, reply) => {
    try {
      // No HMAC verification needed for authenticated routes
      const webhook = TradingViewWebhookSchema.parse(request.body);
      const userId = (request as any).userId;
      
      // Check for duplicate alert (idempotency)
      const existingJob = await fastify.prisma.job.findUnique({
        where: { alertId: webhook.alert_id },
      });
      
      if (existingJob) {
        fastify.log.info(`Duplicate alert ignored: ${webhook.alert_id}`);
        return reply.status(200).send({ 
          message: 'Alert already processed',
          jobId: existingJob.id,
        });
      }
      
      // Smart account selection with user context
      const accountSelection = new AccountSelectionService(fastify.prisma);
      const selectionResult = await accountSelection.selectAccount({
        webhook,
        userId // This enables user-specific account selection
      });
      
      if (!selectionResult.success || !selectionResult.account) {
        fastify.log.error('Account selection failed for authenticated user', {
          webhook: webhook.alert_id,
          exchange: webhook.exchange,
          userId,
          reason: selectionResult.reason
        });
        
        return reply.status(400).send({ 
          error: 'No suitable account found',
          exchange: webhook.exchange,
          reason: selectionResult.reason,
          accountId: webhook.account_id
        });
      }

      const account = selectionResult.account;
      
      // Verify account ownership (additional security)
      if (account.userId !== userId) {
        return reply.status(403).send({
          error: 'Account does not belong to authenticated user'
        });
      }
      
      fastify.log.info('Account selected successfully for authenticated user', {
        accountId: account.id,
        accountName: account.name,
        selectionReason: account.selectionReason,
        alertId: webhook.alert_id,
        userId
      });
      
      // Create job record
      const job = await fastify.prisma.job.create({
        data: {
          alertId: webhook.alert_id,
          accountId: account.id,
          userId: account.userId,
          webhook: webhook as any,
          status: 'pending',
        },
      });
      
      // Add to execution queue
      await fastify.queueService.addExecJob({
        alertId: webhook.alert_id,
        accountId: account.id,
        webhook,
        retryCount: 0,
      });
      
      fastify.log.info(`Authenticated webhook processed: ${webhook.alert_id}`);
      
      return reply.status(200).send({
        message: 'Webhook received and queued',
        jobId: job.id,
        alertId: webhook.alert_id,
        selectedAccount: {
          id: account.id,
          name: account.name,
          selectionReason: account.selectionReason
        }
      });
      
    } catch (error) {
      fastify.log.error('Authenticated webhook processing error:', error);
      
      if (error instanceof Error && error.message.includes('Validation')) {
        return reply.status(400).send({
          error: 'Invalid webhook payload',
          details: error.message,
        });
      }
      
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });
};

export { webhookRoutes };