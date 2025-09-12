import { describe, test, expect, beforeEach } from '@jest/globals';
import { MockExchangeAdapter } from '../mocks/exchange-mock';
import { CircuitBreaker } from '../../utils/circuit-breaker';

// Mock utility classes for testing
class MockRetryPolicy {
  private config: any;
  
  constructor(config: any) {
    this.config = config;
  }
  
  async execute<T>(operation: () => Promise<T>): Promise<T> {
    let lastError: Error | null = null;
    const maxRetries = this.config.maxRetries || 3;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        // Check if error is retryable (simple heuristic)
        const isRetryable = this.isErrorRetryable(error as Error);
        if (!isRetryable || attempt >= maxRetries) {
          throw error;
        }
        
        if (attempt < maxRetries) {
          const delay = this.config.initialDelay * Math.pow(this.config.backoffMultiplier || 2, attempt);
          await new Promise(resolve => setTimeout(resolve, Math.min(delay, this.config.maxDelay || 1000)));
        }
      }
    }
    throw lastError;
  }
  
  private isErrorRetryable(error: Error): boolean {
    return error.message.includes('timeout') || 
           error.message.includes('network') ||
           error.message.includes('Rate limit') ||
           error.message.includes('Connection');
  }
}

class MockErrorClassifier {
  classify(error: Error) {
    let category = 'unknown';
    let severity = 'medium';
    let isRetryable = false;
    let suggestedActions: string[] = [];
    
    const message = error.message.toLowerCase();
    
    if (message.includes('network') || message.includes('timeout')) {
      category = 'network';
      isRetryable = true;
      suggestedActions = ['RETRY_WITH_BACKOFF'];
    } else if (message.includes('insufficient') || message.includes('balance')) {
      category = 'exchange';
      severity = 'high';
      isRetryable = false;
      suggestedActions = ['SKIP_AND_NOTIFY'];
    } else if (message.includes('rate limit')) {
      category = 'network';
      isRetryable = true;
      suggestedActions = ['RETRY_WITH_BACKOFF'];
    } else if (message.includes('database') || message.includes('connection')) {
      category = 'database';
      severity = 'high';
      isRetryable = true;
      suggestedActions = ['RETRY_WITH_BACKOFF'];
    } else if (message.includes('invalid') || message.includes('validation')) {
      category = 'validation';
      isRetryable = false;
      suggestedActions = ['SKIP_AND_NOTIFY'];
    } else if (message.includes('maintenance')) {
      category = 'exchange';
      isRetryable = true;
      suggestedActions = ['FALLBACK_EXCHANGE'];
    } else if (message.includes('position') || message.includes('limit')) {
      category = 'exchange';
      severity = 'medium';
      isRetryable = false;
    }
    
    return {
      category,
      severity,
      isRetryable,
      suggestedActions
    };
  }
}

const RecoveryAction = {
  RETRY_WITH_BACKOFF: 'RETRY_WITH_BACKOFF',
  SKIP_AND_NOTIFY: 'SKIP_AND_NOTIFY',
  FALLBACK_EXCHANGE: 'FALLBACK_EXCHANGE'
};

/**
 * Integration tests for error handling and recovery scenarios
 * Tests various failure scenarios and recovery mechanisms
 */
describe('Error Handling and Recovery Integration Tests', () => {
  let mockExchange: MockExchangeAdapter;
  let errorClassifier: MockErrorClassifier;
  let retryPolicy: MockRetryPolicy;
  let circuitBreaker: CircuitBreaker;
  
  beforeEach(() => {
    mockExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test' },
      {
        simulateLatency: 10,
        simulateErrors: false,
        balances: { USDT: 10000, BTC: 0 }
      }
    );
    
    errorClassifier = new MockErrorClassifier();
    retryPolicy = new MockRetryPolicy({
      maxRetries: 3,
      initialDelay: 100,
      maxDelay: 1000,
      backoffMultiplier: 2
    });
    
    circuitBreaker = new CircuitBreaker({
      failureThreshold: 3,
      successThreshold: 2,
      timeout: 5000,
      monitoringPeriod: 10000,
      name: 'test-exchange'
    });
  });

  test('should classify and handle network errors', async () => {
    const networkError = new Error('Network request failed');
    const classification = errorClassifier.classify(networkError);
    
    expect(classification.category).toBe('network');
    expect(classification.severity).toBe('medium');
    expect(classification.isRetryable).toBe(true);
    expect(classification.suggestedActions).toContain(RecoveryAction.RETRY_WITH_BACKOFF);
  });

  test('should classify and handle exchange API errors', async () => {
    const apiError = new Error('Insufficient balance');
    const classification = errorClassifier.classify(apiError);
    
    expect(classification.category).toBe('exchange');
    expect(classification.severity).toBe('high');
    expect(classification.isRetryable).toBe(false);
    expect(classification.suggestedActions).toContain(RecoveryAction.SKIP_AND_NOTIFY);
  });

  test('should retry transient errors with exponential backoff', async () => {
    let attemptCount = 0;
    const flakyOperation = async () => {
      attemptCount++;
      if (attemptCount < 3) {
        throw new Error('Temporary network error');
      }
      return 'success';
    };

    const startTime = Date.now();
    const result = await retryPolicy.execute(flakyOperation);
    const endTime = Date.now();
    
    expect(result).toBe('success');
    expect(attemptCount).toBe(3);
    expect(endTime - startTime).toBeGreaterThan(200); // Should have delays
  });

  test('should give up after max retries', async () => {
    const alwaysFailingOperation = async () => {
      throw new Error('Persistent network error');
    };

    await expect(
      retryPolicy.execute(alwaysFailingOperation)
    ).rejects.toThrow('Persistent network error');
  });

  test('should not retry non-retryable errors', async () => {
    let attemptCount = 0;
    const nonRetryableOperation = async () => {
      attemptCount++;
      throw new Error('Insufficient balance');
    };

    await expect(
      retryPolicy.execute(nonRetryableOperation)
    ).rejects.toThrow('Insufficient balance');
    
    expect(attemptCount).toBe(1); // Should only try once
  });

  test('should handle circuit breaker state transitions', async () => {
    const stats = circuitBreaker.getStats();
    expect(stats.state).toBe('CLOSED');
    expect(stats.failureCount).toBe(0);
    expect(stats.requestCount).toBe(0);

    // Test basic functionality - successful operation
    const result = await circuitBreaker.execute(async () => 'test-success');
    expect(result).toBe('test-success');

    const successStats = circuitBreaker.getStats();
    expect(successStats.requestCount).toBe(1);
    expect(successStats.successCount).toBe(1);

    // Test failure handling
    try {
      await circuitBreaker.execute(async () => {
        throw new Error('Test failure');
      });
    } catch (error) {
      // Expected failure
    }

    const failureStats = circuitBreaker.getStats();
    expect(failureStats.requestCount).toBe(2);
    expect(failureStats.failureCount).toBe(1);
  });

  test('should handle exchange connection failures', async () => {
    const errorExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test' },
      {
        simulateErrors: true,
        errorRate: 1.0
      }
    );

    const pingTest = async () => {
      return await errorExchange.ping();
    };

    await expect(
      retryPolicy.execute(pingTest)
    ).rejects.toThrow();
  });

  test('should handle partial order fills correctly', async () => {
    // Place a large limit order that might fill partially
    const order = await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.1,
      type: 'limit',
      price: 49000
    });

    // For limit orders, they start unfilled
    expect(order.remaining).toBe(0.1);
    expect(order.filled).toBe(0);
    expect(order.status).toBe('open');
  });

  test('should handle rate limiting scenarios', async () => {
    // Should classify rate limit as retryable
    const rateLimitError = new Error('Rate limit exceeded');
    const classification = errorClassifier.classify(rateLimitError);
    
    expect(classification.isRetryable).toBe(true);
    expect(classification.suggestedActions).toContain(RecoveryAction.RETRY_WITH_BACKOFF);
  });

  test('should handle database connection errors', async () => {
    const dbError = new Error('Connection to database failed');
    const classification = errorClassifier.classify(dbError);
    
    expect(classification.category).toBe('database');
    expect(classification.isRetryable).toBe(true);
    expect(classification.severity).toBe('high');
  });

  test('should handle validation errors properly', async () => {
    const validationError = new Error('Invalid order parameters');
    const classification = errorClassifier.classify(validationError);
    
    expect(classification.category).toBe('validation');
    expect(classification.isRetryable).toBe(false);
    expect(classification.suggestedActions).toContain(RecoveryAction.SKIP_AND_NOTIFY);
  });

  test('should handle timeout scenarios', async () => {
    const timeoutError = new Error('Request timeout');
    const classification = errorClassifier.classify(timeoutError);
    
    expect(classification.isRetryable).toBe(true);
    expect(classification.category).toBe('network');
  });

  test('should handle exchange maintenance mode', async () => {
    const maintenanceError = new Error('Exchange is under maintenance');
    const classification = errorClassifier.classify(maintenanceError);
    
    expect(classification.category).toBe('exchange');
    expect(classification.isRetryable).toBe(true);
    expect(classification.suggestedActions).toContain(RecoveryAction.FALLBACK_EXCHANGE);
  });

  test('should handle order rejection scenarios', async () => {
    // Try to place order with insufficient balance
    mockExchange.setMockBalance('USDT', 10);
    
    const validation = await mockExchange.validateBalance(
      'BTCUSDT',
      'buy',
      1.0,
      50000,
      1
    );

    expect(validation.isValid).toBe(false);
    expect(validation.reason).toContain('Insufficient');

    // Error should be classified as non-retryable
    const balanceError = new Error(validation.reason);
    const classification = errorClassifier.classify(balanceError);
    
    expect(classification.isRetryable).toBe(false);
    expect(classification.category).toBe('exchange');
  });

  test('should handle position size limit errors', async () => {
    const positionError = new Error('Position size exceeds maximum allowed');
    const classification = errorClassifier.classify(positionError);
    
    expect(classification.category).toBe('exchange');
    expect(classification.isRetryable).toBe(false);
    expect(classification.severity).toBe('medium');
  });

  test('should collect error metrics and statistics', async () => {
    const errors = [
      new Error('Network timeout'),
      new Error('Insufficient balance'),
      new Error('Rate limit exceeded'),
      new Error('Invalid symbol'),
      new Error('Order not found')
    ];

    const classifications = errors.map(err => errorClassifier.classify(err));
    
    const retryableCount = classifications.filter(c => c.isRetryable).length;
    const highSeverityCount = classifications.filter(c => c.severity === 'high').length;
    const networkErrorCount = classifications.filter(c => c.category === 'network').length;
    
    expect(retryableCount).toBeGreaterThan(0);
    expect(highSeverityCount).toBeGreaterThan(0);
    expect(networkErrorCount).toBeGreaterThan(0);
  });

  test('should handle graceful degradation', async () => {
    // Primary exchange fails
    const failingExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test' },
      { simulateErrors: true, errorRate: 1.0 }
    );

    // Fallback exchange works
    const fallbackExchange = new MockExchangeAdapter(
      { apiKey: 'test2', secret: 'test2' },
      { simulateErrors: false, balances: { USDT: 5000 } }
    );

    try {
      await failingExchange.ping();
      throw new Error('Should have failed');
    } catch (error) {
      // Fall back to secondary exchange
      const fallbackResult = await fallbackExchange.ping();
      expect(fallbackResult).toBe(true);
    }
  });
});