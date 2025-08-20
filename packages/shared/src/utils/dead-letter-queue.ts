import { Queue, Job, Worker, QueueEvents } from 'bullmq';
import { Redis } from 'ioredis';
import { TradingError, ErrorCategory, TradingErrorHandler } from './error-handling';
import { RetryPolicyManager } from './retry-policies';

export interface DeadLetterConfig {
  redis: Redis;
  queueName: string;
  deadLetterQueueName?: string;
  maxRetries?: number;
  retentionDays?: number;
  alertThreshold?: number; // Alert when DLQ reaches this size
}

export interface DeadLetterJobData {
  originalJobData: any;
  originalQueue: string;
  failureReason: string;
  errorCategory: ErrorCategory;
  attemptsMade: number;
  firstFailedAt: Date;
  lastFailedAt: Date;
  errors: Array<{
    error: string;
    timestamp: Date;
    attempt: number;
  }>;
}

export interface DeadLetterStats {
  totalJobs: number;
  jobsByCategory: Record<ErrorCategory, number>;
  oldestJob: Date | null;
  newestJob: Date | null;
  avgTimeInDLQ: number;
  reprocessableJobs: number;
}

/**
 * Dead Letter Queue implementation for handling failed jobs
 * Jobs that fail repeatedly are moved here for manual inspection/reprocessing
 */
export class DeadLetterQueue {
  private deadLetterQueue: Queue;
  private queueEvents: QueueEvents;
  private worker: Worker;
  private config: Required<DeadLetterConfig>;

  constructor(config: DeadLetterConfig) {
    this.config = {
      deadLetterQueueName: `${config.queueName}:dlq`,
      maxRetries: 3,
      retentionDays: 30,
      alertThreshold: 100,
      ...config
    };

    this.deadLetterQueue = new Queue(this.config.deadLetterQueueName, {
      connection: this.config.redis,
      defaultJobOptions: {
        removeOnComplete: false, // Keep completed jobs for analysis
        removeOnFail: false,     // Keep failed jobs for analysis
        attempts: 1,             // DLQ jobs don't retry
      }
    });

    this.queueEvents = new QueueEvents(this.config.deadLetterQueueName, {
      connection: this.config.redis
    });

    this.setupWorker();
    this.setupEventHandlers();
    this.setupCleanup();
  }

  /**
   * Add a failed job to the dead letter queue
   */
  async addFailedJob(
    originalJob: Job,
    finalError: Error,
    attemptsMade: number
  ): Promise<void> {
    const tradingError = TradingErrorHandler.classifyError(finalError);
    
    const dlqJobData: DeadLetterJobData = {
      originalJobData: originalJob.data,
      originalQueue: originalJob.queueName,
      failureReason: finalError.message,
      errorCategory: tradingError.category,
      attemptsMade,
      firstFailedAt: new Date(originalJob.processedOn || Date.now()),
      lastFailedAt: new Date(),
      errors: this.extractErrorHistory(originalJob, finalError, attemptsMade)
    };

    await this.deadLetterQueue.add(
      'dead-letter-job',
      dlqJobData,
      {
        jobId: `dlq:${originalJob.id}`,
        priority: this.calculatePriority(tradingError.category),
        delay: 0
      }
    );

    // Check if we should send an alert
    await this.checkAlertThreshold();
  }

  /**
   * Reprocess a job from the dead letter queue
   */
  async reprocessJob(
    jobId: string,
    targetQueue: Queue,
    options?: {
      resetRetryCount?: boolean;
      newJobOptions?: any;
    }
  ): Promise<string | null> {
    const dlqJob = await this.deadLetterQueue.getJob(jobId);
    
    if (!dlqJob) {
      throw new Error(`Dead letter job not found: ${jobId}`);
    }

    const dlqData = dlqJob.data as DeadLetterJobData;
    
    // Determine if job should be reprocessed based on error category
    if (!this.canReprocess(dlqData.errorCategory)) {
      throw new Error(
        `Job cannot be reprocessed due to error category: ${dlqData.errorCategory}`
      );
    }

    // Add job back to original queue
    const newJobData = {
      ...dlqData.originalJobData,
      reprocessedFrom: jobId,
      reprocessedAt: new Date()
    };

    const jobOptions = {
      ...options?.newJobOptions,
      attempts: options?.resetRetryCount ? 
        RetryPolicyManager.getPolicy(dlqData.errorCategory).maxAttempts + 1 : 1
    };

    const newJob = await targetQueue.add(
      dlqData.originalJobData.jobType || 'reprocessed-job',
      newJobData,
      jobOptions
    );

    // Mark DLQ job as reprocessed
    await dlqJob.update({
      ...dlqData,
      reprocessedAt: new Date(),
      reprocessedJobId: newJob.id
    });

    await dlqJob.remove();

    return newJob.id;
  }

  /**
   * Bulk reprocess jobs by error category
   */
  async reprocessByCategory(
    category: ErrorCategory,
    targetQueue: Queue,
    limit: number = 10
  ): Promise<string[]> {
    const jobs = await this.deadLetterQueue.getJobs(['waiting', 'delayed'], 0, limit - 1);
    const reprocessedJobIds: string[] = [];

    for (const job of jobs) {
      const dlqData = job.data as DeadLetterJobData;
      
      if (dlqData.errorCategory === category && this.canReprocess(category)) {
        try {
          const newJobId = await this.reprocessJob(job.id!, targetQueue);
          if (newJobId) {
            reprocessedJobIds.push(newJobId);
          }
        } catch (error) {
          console.error(`Failed to reprocess job ${job.id}:`, error);
        }
      }
    }

    return reprocessedJobIds;
  }

  /**
   * Get dead letter queue statistics
   */
  async getStats(): Promise<DeadLetterStats> {
    const waitingJobs = await this.deadLetterQueue.getWaiting();
    const completedJobs = await this.deadLetterQueue.getCompleted();
    const allJobs = [...waitingJobs, ...completedJobs];

    const stats: DeadLetterStats = {
      totalJobs: allJobs.length,
      jobsByCategory: {} as Record<ErrorCategory, number>,
      oldestJob: null,
      newestJob: null,
      avgTimeInDLQ: 0,
      reprocessableJobs: 0
    };

    if (allJobs.length === 0) {
      return stats;
    }

    let totalTimeInDLQ = 0;
    let oldestTimestamp = Number.MAX_SAFE_INTEGER;
    let newestTimestamp = 0;

    for (const job of allJobs) {
      const dlqData = job.data as DeadLetterJobData;
      
      // Count by category
      stats.jobsByCategory[dlqData.errorCategory] = 
        (stats.jobsByCategory[dlqData.errorCategory] || 0) + 1;

      // Count reprocessable jobs
      if (this.canReprocess(dlqData.errorCategory)) {
        stats.reprocessableJobs++;
      }

      // Track timestamps
      const jobTimestamp = job.timestamp || Date.now();
      oldestTimestamp = Math.min(oldestTimestamp, jobTimestamp);
      newestTimestamp = Math.max(newestTimestamp, jobTimestamp);
      
      totalTimeInDLQ += Date.now() - jobTimestamp;
    }

    stats.oldestJob = new Date(oldestTimestamp);
    stats.newestJob = new Date(newestTimestamp);
    stats.avgTimeInDLQ = Math.floor(totalTimeInDLQ / allJobs.length);

    return stats;
  }

  /**
   * Get jobs by error category
   */
  async getJobsByCategory(category: ErrorCategory, limit: number = 50): Promise<Job[]> {
    const jobs = await this.deadLetterQueue.getJobs(['waiting', 'delayed', 'completed'], 0, limit - 1);
    
    return jobs.filter(job => {
      const dlqData = job.data as DeadLetterJobData;
      return dlqData.errorCategory === category;
    });
  }

  /**
   * Purge old jobs from DLQ
   */
  async purgeOldJobs(olderThanDays: number = this.config.retentionDays): Promise<number> {
    const cutoffDate = new Date(Date.now() - (olderThanDays * 24 * 60 * 60 * 1000));
    const jobs = await this.deadLetterQueue.getJobs(['waiting', 'delayed', 'completed']);
    
    let purgedCount = 0;
    
    for (const job of jobs) {
      if (job.timestamp && job.timestamp < cutoffDate.getTime()) {
        await job.remove();
        purgedCount++;
      }
    }

    return purgedCount;
  }

  /**
   * Setup worker for DLQ processing (mainly for logging and monitoring)
   */
  private setupWorker(): void {
    this.worker = new Worker(
      this.config.deadLetterQueueName,
      async (job: Job) => {
        const dlqData = job.data as DeadLetterJobData;
        
        // Log dead letter job for monitoring
        console.log('Dead letter job processed:', {
          jobId: job.id,
          originalQueue: dlqData.originalQueue,
          errorCategory: dlqData.errorCategory,
          attemptsMade: dlqData.attemptsMade,
          failureReason: dlqData.failureReason
        });

        return { processed: true, timestamp: new Date() };
      },
      {
        connection: this.config.redis,
        concurrency: 1, // Low concurrency for DLQ processing
      }
    );
  }

  /**
   * Setup event handlers for monitoring
   */
  private setupEventHandlers(): void {
    this.queueEvents.on('added', (jobInfo) => {
      console.log(`Job added to dead letter queue: ${jobInfo.jobId}`);
    });

    this.queueEvents.on('error', (error) => {
      console.error('Dead letter queue error:', error);
    });
  }

  /**
   * Setup periodic cleanup
   */
  private setupCleanup(): void {
    // Run cleanup every 24 hours
    setInterval(async () => {
      try {
        const purgedCount = await this.purgeOldJobs();
        console.log(`Dead letter queue cleanup: purged ${purgedCount} old jobs`);
      } catch (error) {
        console.error('DLQ cleanup error:', error);
      }
    }, 24 * 60 * 60 * 1000);
  }

  /**
   * Extract error history from failed job
   */
  private extractErrorHistory(
    job: Job, 
    finalError: Error, 
    attemptsMade: number
  ): Array<{ error: string; timestamp: Date; attempt: number }> {
    const errors: Array<{ error: string; timestamp: Date; attempt: number }> = [];

    // Add historical errors if available
    if (job.failedReason) {
      errors.push({
        error: job.failedReason,
        timestamp: new Date(job.finishedOn || Date.now()),
        attempt: attemptsMade - 1
      });
    }

    // Add final error
    errors.push({
      error: finalError.message,
      timestamp: new Date(),
      attempt: attemptsMade
    });

    return errors;
  }

  /**
   * Calculate job priority based on error category
   */
  private calculatePriority(category: ErrorCategory): number {
    // Higher priority = lower number (processed first)
    switch (category) {
      case ErrorCategory.SYSTEM_ERROR:
      case ErrorCategory.DATABASE_ERROR:
        return 1; // Highest priority
      
      case ErrorCategory.AUTHENTICATION_ERROR:
      case ErrorCategory.ACCOUNT_NOT_FOUND:
        return 2;
      
      case ErrorCategory.INSUFFICIENT_BALANCE:
      case ErrorCategory.POSITION_SIZE_ERROR:
        return 3;
      
      case ErrorCategory.NETWORK_ERROR:
      case ErrorCategory.TIMEOUT:
        return 4;
      
      default:
        return 5; // Lowest priority
    }
  }

  /**
   * Check if job can be reprocessed based on error category
   */
  private canReprocess(category: ErrorCategory): boolean {
    const nonReprocessableCategories = [
      ErrorCategory.AUTHENTICATION_ERROR,
      ErrorCategory.ACCOUNT_NOT_FOUND,
      ErrorCategory.INVALID_CONFIGURATION,
      ErrorCategory.VALIDATION_ERROR,
      ErrorCategory.SYSTEM_ERROR
    ];

    return !nonReprocessableCategories.includes(category);
  }

  /**
   * Check if DLQ size exceeds alert threshold
   */
  private async checkAlertThreshold(): Promise<void> {
    const waitingCount = await this.deadLetterQueue.getWaiting();
    
    if (waitingCount.length >= this.config.alertThreshold) {
      // Emit alert event or send notification
      console.warn(`Dead letter queue alert: ${waitingCount.length} jobs pending`, {
        queueName: this.config.deadLetterQueueName,
        threshold: this.config.alertThreshold,
        currentSize: waitingCount.length
      });
    }
  }

  /**
   * Close the dead letter queue and cleanup resources
   */
  async close(): Promise<void> {
    await this.worker.close();
    await this.queueEvents.close();
    await this.deadLetterQueue.close();
  }
}

/**
 * Utility functions for dead letter queue management
 */
export class DeadLetterUtils {
  /**
   * Create a dead letter queue for a given queue
   */
  static createForQueue(queueName: string, redis: Redis, config?: Partial<DeadLetterConfig>): DeadLetterQueue {
    return new DeadLetterQueue({
      redis,
      queueName,
      ...config
    });
  }

  /**
   * Analyze dead letter queue patterns
   */
  static async analyzePatterns(dlq: DeadLetterQueue): Promise<{
    commonErrors: Array<{ error: string; count: number }>;
    peakHours: Array<{ hour: number; count: number }>;
    categoryDistribution: Record<ErrorCategory, number>;
  }> {
    const stats = await dlq.getStats();
    
    // This would require more detailed analysis of job data
    // For now, return basic category distribution
    return {
      commonErrors: [],
      peakHours: [],
      categoryDistribution: stats.jobsByCategory
    };
  }

  /**
   * Generate DLQ health report
   */
  static async generateHealthReport(dlq: DeadLetterQueue): Promise<{
    status: 'healthy' | 'warning' | 'critical';
    summary: string;
    recommendations: string[];
    stats: DeadLetterStats;
  }> {
    const stats = await dlq.getStats();
    
    let status: 'healthy' | 'warning' | 'critical' = 'healthy';
    let summary = 'Dead letter queue is operating normally';
    const recommendations: string[] = [];

    if (stats.totalJobs > 50) {
      status = 'warning';
      summary = 'Dead letter queue has elevated job count';
      recommendations.push('Review and reprocess recoverable jobs');
    }

    if (stats.totalJobs > 200) {
      status = 'critical';
      summary = 'Dead letter queue is overloaded';
      recommendations.push('Immediate attention required - investigate root causes');
      recommendations.push('Consider temporarily disabling problematic job types');
    }

    if (stats.reprocessableJobs > stats.totalJobs * 0.5) {
      recommendations.push('Many jobs can be reprocessed - consider bulk reprocessing');
    }

    return {
      status,
      summary,
      recommendations,
      stats
    };
  }
}