import { Queue, Worker } from 'bullmq';
import Redis from 'ioredis';
import { JobPayload } from '@tradingview-gateway/shared';

export class QueueService {
  private redis: Redis;
  public execQueue: Queue;
  public reconQueue: Queue;

  constructor(redis: Redis) {
    this.redis = redis;
    
    this.execQueue = new Queue('exec', {
      connection: redis,
      defaultJobOptions: {
        removeOnComplete: 100,
        removeOnFail: 50,
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 2000,
        },
      },
    });

    this.reconQueue = new Queue('recon', {
      connection: redis,
      defaultJobOptions: {
        removeOnComplete: 50,
        removeOnFail: 20,
        attempts: 2,
        backoff: {
          type: 'exponential',
          delay: 5000,
        },
      },
    });
  }

  async addExecJob(payload: JobPayload) {
    return this.execQueue.add('execute-trade', payload, {
      delay: 0,
      jobId: payload.alertId, // Use alertId as jobId for idempotency
    });
  }

  async addReconJob(payload: { accountId: string }) {
    return this.reconQueue.add('reconcile-positions', payload, {
      delay: 0,
    });
  }

  async getQueueInfo() {
    const [execWaiting, execActive, reconWaiting, reconActive] = await Promise.all([
      this.execQueue.getWaiting(),
      this.execQueue.getActive(),
      this.reconQueue.getWaiting(),
      this.reconQueue.getActive(),
    ]);

    return {
      exec: {
        waiting: execWaiting.length,
        active: execActive.length,
      },
      recon: {
        waiting: reconWaiting.length,
        active: reconActive.length,
      },
    };
  }

  async pause() {
    await Promise.all([
      this.execQueue.pause(),
      this.reconQueue.pause(),
    ]);
  }

  async resume() {
    await Promise.all([
      this.execQueue.resume(),
      this.reconQueue.resume(),
    ]);
  }

  async close() {
    await Promise.all([
      this.execQueue.close(),
      this.reconQueue.close(),
    ]);
  }
}