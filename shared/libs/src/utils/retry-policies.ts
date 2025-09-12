import { ErrorCategory, TradingError, TradingErrorHandler } from './error-handling';

export interface RetryPolicy {
  maxAttempts: number;
  backoffType: 'fixed' | 'exponential' | 'linear';
  initialDelayMs: number;
  maxDelayMs: number;
  jitterFactor: number;
  shouldRetry: (error: TradingError, attempt: number) => boolean;
}

export interface RetryAttempt {
  attempt: number;
  error: TradingError;
  nextRetryAt: Date;
  delayMs: number;
}

export class RetryPolicyManager {
  private static policies: Map<ErrorCategory, RetryPolicy> = new Map([
    // Network errors - aggressive retry with exponential backoff
    [ErrorCategory.NETWORK_ERROR, {
      maxAttempts: 3,
      backoffType: 'exponential',
      initialDelayMs: 1000,
      maxDelayMs: 30000,
      jitterFactor: 0.3,
      shouldRetry: (error, attempt) => attempt < 3
    }],

    // Rate limiting - longer delays, more attempts
    [ErrorCategory.RATE_LIMIT, {
      maxAttempts: 5,
      backoffType: 'exponential',
      initialDelayMs: 60000, // Start with 1 minute
      maxDelayMs: 600000,     // Max 10 minutes
      jitterFactor: 0.2,
      shouldRetry: (error, attempt) => attempt < 5
    }],

    // Temporary unavailable - moderate retry
    [ErrorCategory.TEMPORARY_UNAVAILABLE, {
      maxAttempts: 3,
      backoffType: 'exponential',
      initialDelayMs: 5000,
      maxDelayMs: 60000,
      jitterFactor: 0.25,
      shouldRetry: (error, attempt) => attempt < 3
    }],

    // Timeout - quick retry with shorter delays
    [ErrorCategory.TIMEOUT, {
      maxAttempts: 2,
      backoffType: 'linear',
      initialDelayMs: 2000,
      maxDelayMs: 10000,
      jitterFactor: 0.1,
      shouldRetry: (error, attempt) => attempt < 2
    }],

    // Price feed errors - fast retry
    [ErrorCategory.PRICE_FEED_ERROR, {
      maxAttempts: 2,
      backoffType: 'fixed',
      initialDelayMs: 1000,
      maxDelayMs: 5000,
      jitterFactor: 0.1,
      shouldRetry: (error, attempt) => attempt < 2
    }],

    // Database errors - moderate retry
    [ErrorCategory.DATABASE_ERROR, {
      maxAttempts: 2,
      backoffType: 'exponential',
      initialDelayMs: 1000,
      maxDelayMs: 15000,
      jitterFactor: 0.2,
      shouldRetry: (error, attempt) => attempt < 2
    }],

    // Unknown errors - conservative retry
    [ErrorCategory.UNKNOWN_ERROR, {
      maxAttempts: 1,
      backoffType: 'fixed',
      initialDelayMs: 5000,
      maxDelayMs: 5000,
      jitterFactor: 0.1,
      shouldRetry: (error, attempt) => attempt < 1
    }],

    // Non-recoverable errors - no retry
    [ErrorCategory.INSUFFICIENT_BALANCE, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }],

    [ErrorCategory.AUTHENTICATION_ERROR, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }],

    [ErrorCategory.ACCOUNT_NOT_FOUND, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }],

    [ErrorCategory.VALIDATION_ERROR, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }],

    [ErrorCategory.EXCHANGE_REJECTED, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }],

    [ErrorCategory.INVALID_CONFIGURATION, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }],

    [ErrorCategory.POSITION_SIZE_ERROR, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }],

    [ErrorCategory.SYSTEM_ERROR, {
      maxAttempts: 0,
      backoffType: 'fixed',
      initialDelayMs: 0,
      maxDelayMs: 0,
      jitterFactor: 0,
      shouldRetry: () => false
    }]
  ]);

  /**
   * Get retry policy for error category
   */
  static getPolicy(category: ErrorCategory): RetryPolicy {
    return this.policies.get(category) || this.policies.get(ErrorCategory.UNKNOWN_ERROR)!;
  }

  /**
   * Calculate next retry delay based on policy
   */
  static calculateDelay(error: TradingError, attempt: number): number {
    const policy = this.getPolicy(error.category);
    
    if (!policy.shouldRetry(error, attempt)) {
      return 0; // No retry
    }

    let delay: number;

    switch (policy.backoffType) {
      case 'fixed':
        delay = policy.initialDelayMs;
        break;

      case 'linear':
        delay = policy.initialDelayMs * (attempt + 1);
        break;

      case 'exponential':
        delay = policy.initialDelayMs * Math.pow(2, attempt);
        break;

      default:
        delay = policy.initialDelayMs;
    }

    // Apply max delay limit
    delay = Math.min(delay, policy.maxDelayMs);

    // Add jitter to prevent thundering herd
    const jitter = delay * policy.jitterFactor * (Math.random() - 0.5);
    delay = Math.max(0, delay + jitter);

    return Math.floor(delay);
  }

  /**
   * Check if error should be retried
   */
  static shouldRetry(error: TradingError, currentAttempt: number): boolean {
    const policy = this.getPolicy(error.category);
    return policy.shouldRetry(error, currentAttempt) && currentAttempt < policy.maxAttempts;
  }

  /**
   * Get BullMQ job options for error category
   */
  static getBullMQJobOptions(category: ErrorCategory) {
    const policy = this.getPolicy(category);
    
    return {
      attempts: policy.maxAttempts + 1, // +1 because BullMQ counts initial attempt
      backoff: {
        type: 'custom',
        settings: {
          category: category
        }
      },
      removeOnComplete: 50,
      removeOnFail: 20
    };
  }

  /**
   * Custom BullMQ backoff function
   */
  static customBackoff(attemptsMade: number, type: string, err: Error, settings?: any): number {
    if (!settings?.category) {
      return 2000; // Default fallback
    }

    // Convert regular error to TradingError
    const tradingError = TradingErrorHandler.classifyError(err);
    tradingError.category = settings.category;

    return this.calculateDelay(tradingError, attemptsMade - 1);
  }

  /**
   * Create retry attempt record
   */
  static createRetryAttempt(error: TradingError, attemptNumber: number): RetryAttempt {
    const delayMs = this.calculateDelay(error, attemptNumber);
    const nextRetryAt = new Date(Date.now() + delayMs);

    return {
      attempt: attemptNumber,
      error,
      nextRetryAt,
      delayMs
    };
  }

  /**
   * Get retry statistics for monitoring
   */
  static getRetryStats(errors: TradingError[]): {
    totalErrors: number;
    retriableErrors: number;
    nonRetriableErrors: number;
    byCategory: Record<string, number>;
    averageRetryDelay: number;
  } {
    const stats = {
      totalErrors: errors.length,
      retriableErrors: 0,
      nonRetriableErrors: 0,
      byCategory: {} as Record<string, number>,
      averageRetryDelay: 0
    };

    let totalDelay = 0;
    let retriableCount = 0;

    errors.forEach(error => {
      // Count by category
      stats.byCategory[error.category] = (stats.byCategory[error.category] || 0) + 1;

      // Check if retriable
      const policy = this.getPolicy(error.category);
      if (policy.maxAttempts > 0) {
        stats.retriableErrors++;
        totalDelay += policy.initialDelayMs;
        retriableCount++;
      } else {
        stats.nonRetriableErrors++;
      }
    });

    if (retriableCount > 0) {
      stats.averageRetryDelay = Math.floor(totalDelay / retriableCount);
    }

    return stats;
  }

  /**
   * Update retry policy for specific category (runtime configuration)
   */
  static updatePolicy(category: ErrorCategory, policy: Partial<RetryPolicy>): void {
    const currentPolicy = this.getPolicy(category);
    const updatedPolicy = { ...currentPolicy, ...policy };
    this.policies.set(category, updatedPolicy);
  }

  /**
   * Reset all policies to defaults
   */
  static resetPolicies(): void {
    // Policies are already set in the static Map initialization
    // This method can be used to reload from configuration if needed
  }
}

/**
 * Utility functions for common retry scenarios
 */
export class RetryUtils {
  /**
   * Sleep for specified milliseconds
   */
  static async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Retry function with automatic policy application
   */
  static async withRetry<T>(
    operation: () => Promise<T>,
    context?: Record<string, any>
  ): Promise<T> {
    let lastError: TradingError;
    let attempt = 0;

    while (true) {
      try {
        return await operation();
      } catch (error) {
        const tradingError = TradingErrorHandler.classifyError(error as Error, context);
        lastError = tradingError;

        if (!RetryPolicyManager.shouldRetry(tradingError, attempt)) {
          throw tradingError;
        }

        const delay = RetryPolicyManager.calculateDelay(tradingError, attempt);
        
        if (delay > 0) {
          await this.sleep(delay);
        }

        attempt++;
      }
    }
  }

  /**
   * Retry with custom policy
   */
  static async withCustomRetry<T>(
    operation: () => Promise<T>,
    policy: RetryPolicy,
    context?: Record<string, any>
  ): Promise<T> {
    let lastError: TradingError;
    let attempt = 0;

    while (attempt < policy.maxAttempts) {
      try {
        return await operation();
      } catch (error) {
        const tradingError = TradingErrorHandler.classifyError(error as Error, context);
        lastError = tradingError;

        if (!policy.shouldRetry(tradingError, attempt)) {
          throw tradingError;
        }

        const delay = RetryPolicyManager.calculateDelay(tradingError, attempt);
        
        if (delay > 0) {
          await this.sleep(delay);
        }

        attempt++;
      }
    }

    throw lastError!;
  }
}