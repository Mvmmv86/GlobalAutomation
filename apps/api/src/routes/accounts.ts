import { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import { encryptCredentials, decryptCredentials } from '@tradingview-gateway/shared';

const CreateAccountSchema = z.object({
  name: z.string().min(1),
  exchange: z.enum(['binance', 'bybit']),
  apiKey: z.string().min(1),
  secretKey: z.string().min(1),
  passphrase: z.string().optional(),
  testnet: z.boolean().default(true),
});

const UpdateAccountSchema = z.object({
  name: z.string().min(1).optional(),
  apiKey: z.string().min(1).optional(),
  secretKey: z.string().min(1).optional(),
  passphrase: z.string().optional(),
  testnet: z.boolean().optional(),
  isActive: z.boolean().optional(),
});

const accountRoutes: FastifyPluginAsync = async (fastify) => {
  // Get all accounts
  fastify.get('/', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      
      const accounts = await fastify.prisma.exchangeAccount.findMany({
        where: { userId },
        select: {
          id: true,
          name: true,
          exchange: true,
          testnet: true,
          isActive: true,
          createdAt: true,
          updatedAt: true,
        },
      });
      
      return reply.send({ accounts });
      
    } catch (error) {
      fastify.log.error('Get accounts error:', error);
      return reply.status(500).send({ error: 'Failed to fetch accounts' });
    }
  });

  // Create account
  fastify.post('/', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const accountData = CreateAccountSchema.parse(request.body);
      
      // Check for duplicate name
      const existing = await fastify.prisma.exchangeAccount.findUnique({
        where: {
          userId_name: {
            userId,
            name: accountData.name,
          },
        },
      });
      
      if (existing) {
        return reply.status(400).send({ error: 'Account name already exists' });
      }
      
      // Encrypt credentials
      const encryptedCreds = encryptCredentials(
        accountData.apiKey,
        accountData.secretKey,
        accountData.passphrase
      );
      
      const account = await fastify.prisma.exchangeAccount.create({
        data: {
          userId,
          name: accountData.name,
          exchange: accountData.exchange,
          encryptedApiKey: encryptedCreds.apiKey,
          encryptedSecretKey: encryptedCreds.secretKey,
          encryptedPassphrase: encryptedCreds.passphrase,
          testnet: accountData.testnet,
        },
        select: {
          id: true,
          name: true,
          exchange: true,
          testnet: true,
          isActive: true,
          createdAt: true,
        },
      });
      
      return reply.status(201).send({ account });
      
    } catch (error) {
      fastify.log.error('Create account error:', error);
      return reply.status(500).send({ error: 'Failed to create account' });
    }
  });

  // Update account
  fastify.patch('/:id', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { id } = request.params as { id: string };
      const updateData = UpdateAccountSchema.parse(request.body);
      
      // Verify ownership
      const account = await fastify.prisma.exchangeAccount.findFirst({
        where: { id, userId },
      });
      
      if (!account) {
        return reply.status(404).send({ error: 'Account not found' });
      }
      
      const updates: any = {};
      
      if (updateData.name) updates.name = updateData.name;
      if (updateData.testnet !== undefined) updates.testnet = updateData.testnet;
      if (updateData.isActive !== undefined) updates.isActive = updateData.isActive;
      
      // Handle credential updates
      if (updateData.apiKey || updateData.secretKey || updateData.passphrase !== undefined) {
        const currentCreds = decryptCredentials(
          account.encryptedApiKey,
          account.encryptedSecretKey,
          account.encryptedPassphrase || undefined
        );
        
        const newCreds = encryptCredentials(
          updateData.apiKey || currentCreds.apiKey,
          updateData.secretKey || currentCreds.secretKey,
          updateData.passphrase !== undefined ? updateData.passphrase : currentCreds.passphrase
        );
        
        updates.encryptedApiKey = newCreds.apiKey;
        updates.encryptedSecretKey = newCreds.secretKey;
        updates.encryptedPassphrase = newCreds.passphrase;
      }
      
      const updatedAccount = await fastify.prisma.exchangeAccount.update({
        where: { id },
        data: updates,
        select: {
          id: true,
          name: true,
          exchange: true,
          testnet: true,
          isActive: true,
          updatedAt: true,
        },
      });
      
      return reply.send({ account: updatedAccount });
      
    } catch (error) {
      fastify.log.error('Update account error:', error);
      return reply.status(500).send({ error: 'Failed to update account' });
    }
  });

  // Delete account
  fastify.delete('/:id', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { id } = request.params as { id: string };
      
      const deleted = await fastify.prisma.exchangeAccount.deleteMany({
        where: { id, userId },
      });
      
      if (deleted.count === 0) {
        return reply.status(404).send({ error: 'Account not found' });
      }
      
      return reply.send({ message: 'Account deleted successfully' });
      
    } catch (error) {
      fastify.log.error('Delete account error:', error);
      return reply.status(500).send({ error: 'Failed to delete account' });
    }
  });
};

export { accountRoutes };