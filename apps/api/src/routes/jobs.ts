import { FastifyPluginAsync } from 'fastify';

const jobRoutes: FastifyPluginAsync = async (fastify) => {
  // Get jobs for user
  fastify.get('/', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { page = 1, limit = 20, status } = request.query as any;
      
      const skip = (page - 1) * limit;
      const where: any = { userId };
      
      if (status) {
        where.status = status;
      }
      
      const [jobs, total] = await Promise.all([
        fastify.prisma.job.findMany({
          where,
          include: {
            account: {
              select: {
                name: true,
                exchange: true,
              },
            },
          },
          orderBy: { createdAt: 'desc' },
          skip,
          take: limit,
        }),
        fastify.prisma.job.count({ where }),
      ]);
      
      return reply.send({
        jobs,
        pagination: {
          page,
          limit,
          total,
          pages: Math.ceil(total / limit),
        },
      });
      
    } catch (error) {
      fastify.log.error('Get jobs error:', error);
      return reply.status(500).send({ error: 'Failed to fetch jobs' });
    }
  });

  // Get job by ID
  fastify.get('/:id', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { id } = request.params as { id: string };
      
      const job = await fastify.prisma.job.findFirst({
        where: { id, userId },
        include: {
          account: {
            select: {
              name: true,
              exchange: true,
            },
          },
        },
      });
      
      if (!job) {
        return reply.status(404).send({ error: 'Job not found' });
      }
      
      return reply.send({ job });
      
    } catch (error) {
      fastify.log.error('Get job error:', error);
      return reply.status(500).send({ error: 'Failed to fetch job' });
    }
  });

  // Get job statistics
  fastify.get('/stats', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      
      const [total, pending, processing, completed, failed] = await Promise.all([
        fastify.prisma.job.count({ where: { userId } }),
        fastify.prisma.job.count({ where: { userId, status: 'pending' } }),
        fastify.prisma.job.count({ where: { userId, status: 'processing' } }),
        fastify.prisma.job.count({ where: { userId, status: 'completed' } }),
        fastify.prisma.job.count({ where: { userId, status: 'failed' } }),
      ]);
      
      return reply.send({
        stats: {
          total,
          pending,
          processing,
          completed,
          failed,
        },
      });
      
    } catch (error) {
      fastify.log.error('Get job stats error:', error);
      return reply.status(500).send({ error: 'Failed to fetch job stats' });
    }
  });
};

export { jobRoutes };