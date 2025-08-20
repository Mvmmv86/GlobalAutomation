import { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';

const CreateStrategyMappingSchema = z.object({
  strategyName: z.string().min(1),
  accountId: z.string().min(1),
  priority: z.number().int().min(0).default(0),
});

const UpdateStrategyMappingSchema = z.object({
  strategyName: z.string().min(1).optional(),
  accountId: z.string().min(1).optional(),
  priority: z.number().int().min(0).optional(),
  isActive: z.boolean().optional(),
});

const strategyMappingRoutes: FastifyPluginAsync = async (fastify) => {
  // Get all strategy mappings for authenticated user
  fastify.get('/', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      
      const mappings = await fastify.prisma.strategyMapping.findMany({
        where: { userId },
        include: {
          account: {
            select: {
              id: true,
              name: true,
              exchange: true,
              testnet: true,
              isActive: true,
            }
          }
        },
        orderBy: [
          { strategyName: 'asc' },
          { priority: 'desc' }
        ]
      });
      
      return reply.send({ mappings });
      
    } catch (error) {
      fastify.log.error('Get strategy mappings error:', error);
      return reply.status(500).send({ error: 'Failed to fetch strategy mappings' });
    }
  });

  // Create new strategy mapping
  fastify.post('/', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const mappingData = CreateStrategyMappingSchema.parse(request.body);
      
      // Verify account belongs to user
      const account = await fastify.prisma.exchangeAccount.findFirst({
        where: {
          id: mappingData.accountId,
          userId,
          isActive: true
        }
      });
      
      if (!account) {
        return reply.status(400).send({ 
          error: 'Account not found or does not belong to user' 
        });
      }

      // Check for existing mapping (unique constraint)
      const existing = await fastify.prisma.strategyMapping.findFirst({
        where: {
          userId,
          strategyName: mappingData.strategyName,
          accountId: mappingData.accountId
        }
      });

      if (existing) {
        return reply.status(400).send({ 
          error: 'Strategy mapping already exists for this account' 
        });
      }
      
      const mapping = await fastify.prisma.strategyMapping.create({
        data: {
          userId,
          strategyName: mappingData.strategyName,
          accountId: mappingData.accountId,
          priority: mappingData.priority,
        },
        include: {
          account: {
            select: {
              id: true,
              name: true,
              exchange: true,
              testnet: true,
              isActive: true,
            }
          }
        }
      });
      
      return reply.status(201).send({ mapping });
      
    } catch (error) {
      fastify.log.error('Create strategy mapping error:', error);
      return reply.status(500).send({ error: 'Failed to create strategy mapping' });
    }
  });

  // Update strategy mapping
  fastify.patch('/:id', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { id } = request.params as { id: string };
      const updateData = UpdateStrategyMappingSchema.parse(request.body);
      
      // Verify mapping belongs to user
      const existing = await fastify.prisma.strategyMapping.findFirst({
        where: { id, userId }
      });
      
      if (!existing) {
        return reply.status(404).send({ error: 'Strategy mapping not found' });
      }

      // If accountId is being updated, verify new account belongs to user
      if (updateData.accountId) {
        const account = await fastify.prisma.exchangeAccount.findFirst({
          where: {
            id: updateData.accountId,
            userId,
            isActive: true
          }
        });
        
        if (!account) {
          return reply.status(400).send({ 
            error: 'New account not found or does not belong to user' 
          });
        }
      }
      
      const mapping = await fastify.prisma.strategyMapping.update({
        where: { id },
        data: updateData,
        include: {
          account: {
            select: {
              id: true,
              name: true,
              exchange: true,
              testnet: true,
              isActive: true,
            }
          }
        }
      });
      
      return reply.send({ mapping });
      
    } catch (error) {
      fastify.log.error('Update strategy mapping error:', error);
      return reply.status(500).send({ error: 'Failed to update strategy mapping' });
    }
  });

  // Delete strategy mapping
  fastify.delete('/:id', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { id } = request.params as { id: string };
      
      const deleted = await fastify.prisma.strategyMapping.deleteMany({
        where: { id, userId }
      });
      
      if (deleted.count === 0) {
        return reply.status(404).send({ error: 'Strategy mapping not found' });
      }
      
      return reply.send({ message: 'Strategy mapping deleted successfully' });
      
    } catch (error) {
      fastify.log.error('Delete strategy mapping error:', error);
      return reply.status(500).send({ error: 'Failed to delete strategy mapping' });
    }
  });

  // Get mappings for a specific strategy
  fastify.get('/strategy/:strategyName', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { strategyName } = request.params as { strategyName: string };
      
      const mappings = await fastify.prisma.strategyMapping.findMany({
        where: {
          userId,
          strategyName,
          isActive: true
        },
        include: {
          account: {
            select: {
              id: true,
              name: true,
              exchange: true,
              testnet: true,
              isActive: true,
            }
          }
        },
        orderBy: { priority: 'desc' }
      });
      
      return reply.send({ mappings });
      
    } catch (error) {
      fastify.log.error('Get strategy mappings by name error:', error);
      return reply.status(500).send({ error: 'Failed to fetch strategy mappings' });
    }
  });

  // Bulk update priorities
  fastify.patch('/priorities', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { mappings } = request.body as { 
        mappings: Array<{ id: string; priority: number }> 
      };
      
      if (!Array.isArray(mappings)) {
        return reply.status(400).send({ error: 'Invalid mappings array' });
      }

      // Update each mapping priority
      const updates = await Promise.all(
        mappings.map(({ id, priority }) =>
          fastify.prisma.strategyMapping.updateMany({
            where: { id, userId }, // Ensure user owns the mapping
            data: { priority }
          })
        )
      );

      const totalUpdated = updates.reduce((sum, result) => sum + result.count, 0);
      
      return reply.send({ 
        message: `Updated ${totalUpdated} strategy mapping priorities` 
      });
      
    } catch (error) {
      fastify.log.error('Bulk update priorities error:', error);
      return reply.status(500).send({ error: 'Failed to update priorities' });
    }
  });
};

export { strategyMappingRoutes };