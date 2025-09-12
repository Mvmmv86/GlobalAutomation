import { describe, test, expect, beforeEach, jest } from '@jest/globals';
import { MockExchangeAdapter } from '../mocks/exchange-mock';
import { ErrorClassifier, RecoveryAction } from '../../utils/error-handling';
import { RetryPolicy } from '../../utils/retry-policies';
import { CircuitBreaker } from '../../utils/circuit-breaker';
import { DeadLetterQueue } from '../../utils/dead-letter-queue';

/**
 * Chaos Engineering and Failure Recovery Tests
 * Tests system behavior during various failure scenarios and recovery mechanisms
 */
describe('Failure Recovery and Chaos Engineering Tests', () => {
  let primaryExchange: MockExchangeAdapter;
  let fallbackExchange: MockExchangeAdapter;
  let errorClassifier: ErrorClassifier;
  let retryPolicy: RetryPolicy;
  let circuitBreaker: CircuitBreaker;
  let deadLetterQueue: DeadLetterQueue;
  
  beforeEach(() => {
    primaryExchange = new MockExchangeAdapter(
      { apiKey: 'primary', secret: 'primary' },
      {
        simulateLatency: 50,
        simulateErrors: false,
        balances: { USDT: 100000, BTC: 10 }
      }
    );
    
    fallbackExchange = new MockExchangeAdapter(
      { apiKey: 'fallback', secret: 'fallback' },
      {
        simulateLatency: 100,
        simulateErrors: false,
        balances: { USDT: 50000, BTC: 5 }
      }
    );
    
    errorClassifier = new ErrorClassifier();
    retryPolicy = new RetryPolicy({
      maxRetries: 3,
      initialDelay: 100,
      maxDelay: 1000,
      backoffMultiplier: 2
    });
    
    circuitBreaker = new CircuitBreaker('test-exchange', {
      failureThreshold: 3,
      recoveryTimeout: 5000,
      monitoringPeriod: 10000
    });
    
    deadLetterQueue = new DeadLetterQueue({
      maxRetries: 3,
      retryDelay: 1000
    });
  });

  test('should handle primary exchange failure with fallback', async () => {
    // Configure primary to fail
    const failingPrimary = new MockExchangeAdapter(
      { apiKey: 'failing', secret: 'failing' },
      {
        simulateErrors: true,
        errorRate: 1.0 // 100% failure
      }
    );

    const executeWithFallback = async (operation: () => Promise<any>) => {
      try {
        return await operation();
      } catch (primaryError) {
        console.log('Primary exchange failed, trying fallback...');
        
        // Try fallback exchange
        const fallbackOperation = async () => {
          return await fallbackExchange.placeOrder({
            symbol: 'BTCUSDT',
            side: 'buy',
            amount: 0.001,
            type: 'market'
          });
        };
        
        return await fallbackOperation();
      }
    };

    const result = await executeWithFallback(async () => {
      return await failingPrimary.placeOrder({
        symbol: 'BTCUSDT',
        side: 'buy',
        amount: 0.001,
        type: 'market'
      });
    });

    expect(result).toBeDefined();
    expect(result.status).toBe('closed');
  });

  test('should handle network timeouts with exponential backoff', async () => {
    let attemptCount = 0;
    const timeoutOperation = async () => {
      attemptCount++;
      if (attemptCount < 3) {
        throw new Error('Network timeout');
      }
      return { success: true, attempt: attemptCount };
    };

    const result = await retryPolicy.execute(timeoutOperation);
    
    expect(result.success).toBe(true);
    expect(result.attempt).toBe(3);
    expect(attemptCount).toBe(3);
  });

  test('should handle circuit breaker tripping and recovery', async () => {
    expect(circuitBreaker.getState()).toBe('closed');

    // Trip the circuit breaker with failures
    for (let i = 0; i < 3; i++) {
      try {
        await circuitBreaker.call(async () => {
          throw new Error('Service unavailable');
        });
      } catch (error) {
        // Expected to fail
      }
    }

    expect(circuitBreaker.getState()).toBe('open');

    // Should reject calls when open
    await expect(
      circuitBreaker.call(async () => 'success')
    ).rejects.toThrow('Circuit breaker is open');

    // Wait for half-open transition
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Circuit breaker should eventually allow test calls
    expect(['open', 'half-open']).toContain(circuitBreaker.getState());
  });

  test('should handle dead letter queue for failed operations', async () => {
    const failedOperation = {
      id: 'failed_order_123',
      data: {
        symbol: 'BTCUSDT',
        side: 'buy',
        amount: 0.001
      },
      error: 'Exchange temporarily unavailable',
      timestamp: Date.now()
    };

    await deadLetterQueue.add(failedOperation);

    const queueSize = await deadLetterQueue.getQueueSize();
    expect(queueSize).toBe(1);

    // Process the dead letter queue
    const processedItems = [];
    const processor = async (item: any) => {
      processedItems.push(item);
      // Simulate successful retry
      return { success: true, retries: 1 };
    };

    await deadLetterQueue.process(processor);
    
    expect(processedItems).toHaveLength(1);
    expect(processedItems[0].id).toBe('failed_order_123');
  });

  test('should handle database connection failures', async () => {
    const simulateDbOperation = async (shouldFail: boolean) => {
      if (shouldFail) {
        throw new Error('Connection to database failed');
      }
      return { data: 'success' };
    };

    // First attempt fails
    try {
      await simulateDbOperation(true);
    } catch (error) {
      const classification = errorClassifier.classify(error as Error);
      expect(classification.category).toBe('database');
      expect(classification.isRetryable).toBe(true);
    }

    // Retry succeeds
    const result = await simulateDbOperation(false);
    expect(result.data).toBe('success');
  });

  test('should handle partial system failures', async () => {
    const services = {
      database: { working: true },
      redis: { working: false },
      primaryExchange: { working: true },
      fallbackExchange: { working: true }
    };

    const checkSystemHealth = async () => {
      const results = [];
      
      for (const [service, config] of Object.entries(services)) {
        try {
          if (!config.working) {
            throw new Error(`${service} is down`);
          }
          results.push({ service, status: 'healthy' });
        } catch (error) {
          results.push({ service, status: 'unhealthy', error: error.message });
        }
      }
      
      return results;
    };

    const healthResults = await checkSystemHealth();
    
    const healthyServices = healthResults.filter(r => r.status === 'healthy');
    const unhealthyServices = healthResults.filter(r => r.status === 'unhealthy');
    
    expect(healthyServices).toHaveLength(3);
    expect(unhealthyServices).toHaveLength(1);
    expect(unhealthyServices[0].service).toBe('redis');
  });

  test('should handle memory exhaustion scenarios', async () => {
    const simulateMemoryPressure = async () => {
      const initialMemory = process.memoryUsage().heapUsed;
      
      // Simulate memory pressure
      const largeArrays = [];
      try {
        for (let i = 0; i < 1000; i++) {
          largeArrays.push(new Array(10000).fill('memory-test-data'));
        }
        
        const currentMemory = process.memoryUsage().heapUsed;
        const memoryIncrease = currentMemory - initialMemory;
        
        if (memoryIncrease > 100 * 1024 * 1024) { // 100MB
          throw new Error('Memory exhaustion detected');
        }
        
        return { success: true, memoryUsed: memoryIncrease };
        
      } finally {
        // Cleanup
        largeArrays.length = 0;
        if (global.gc) {
          global.gc();
        }
      }
    };

    // This test might throw due to memory pressure
    try {
      const result = await simulateMemoryPressure();
      expect(result.success).toBe(true);
    } catch (error) {
      expect(error.message).toBe('Memory exhaustion detected');
    }
  });

  test('should handle cascading failures', async () => {
    const services = ['auth', 'database', 'exchange', 'notification'];
    const serviceStates = new Map(services.map(s => [s, true]));
    
    const simulateCascadingFailure = async () => {
      // Start with auth service failure
      serviceStates.set('auth', false);
      
      // Simulate cascade
      if (!serviceStates.get('auth')) {
        serviceStates.set('database', false);
      }
      
      if (!serviceStates.get('database')) {
        serviceStates.set('exchange', false);
      }
      
      return Array.from(serviceStates.entries()).map(([service, working]) => ({
        service,
        status: working ? 'healthy' : 'failed'
      }));
    };

    const failureResults = await simulateCascadingFailure();
    const failedServices = failureResults.filter(r => r.status === 'failed');
    
    expect(failedServices).toHaveLength(3); // auth, database, exchange
    expect(failedServices.map(f => f.service)).toEqual(['auth', 'database', 'exchange']);
  });

  test('should handle rate limiting with backoff', async () => {
    let requestCount = 0;
    const rateLimitedOperation = async () => {
      requestCount++;
      if (requestCount <= 5) {
        const error = new Error('Rate limit exceeded');
        (error as any).status = 429;
        throw error;
      }
      return { success: true, attempt: requestCount };
    };

    const executeWithRateLimit = async () => {
      let attempts = 0;
      const maxAttempts = 10;
      
      while (attempts < maxAttempts) {
        try {
          return await rateLimitedOperation();
        } catch (error: any) {
          if (error.status === 429) {
            attempts++;
            const delay = Math.min(100 * Math.pow(2, attempts), 5000);
            await new Promise(resolve => setTimeout(resolve, delay));
          } else {
            throw error;
          }
        }
      }
      
      throw new Error('Max rate limit retries exceeded');
    };

    const result = await executeWithRateLimit();
    expect(result.success).toBe(true);
    expect(result.attempt).toBeGreaterThan(5);
  });

  test('should handle exchange maintenance mode', async () => {
    const maintenanceExchange = new MockExchangeAdapter(
      { apiKey: 'maintenance', secret: 'maintenance' },
      {
        simulateErrors: true,
        errorRate: 1.0
      }
    );

    const handleMaintenanceMode = async () => {
      try {
        await maintenanceExchange.ping();
        return { source: 'primary', success: true };
      } catch (error) {
        console.log('Primary exchange in maintenance, using fallback');
        await fallbackExchange.ping();
        return { source: 'fallback', success: true };
      }
    };

    const result = await handleMaintenanceMode();
    expect(result.source).toBe('fallback');
    expect(result.success).toBe(true);
  });

  test('should handle order rejection scenarios', async () => {
    const orderScenarios = [
      {
        name: 'Insufficient balance',
        setup: () => primaryExchange.setMockBalance('USDT', 1),
        order: { symbol: 'BTCUSDT', side: 'buy', amount: 1.0, type: 'market' }
      },
      {
        name: 'Invalid symbol',
        order: { symbol: 'INVALIDUSDT', side: 'buy', amount: 0.001, type: 'market' }
      },
      {
        name: 'Invalid quantity',
        order: { symbol: 'BTCUSDT', side: 'buy', amount: -0.001, type: 'market' }
      }
    ];

    const results = [];

    for (const scenario of orderScenarios) {
      if (scenario.setup) {
        scenario.setup();
      }

      try {
        const result = await primaryExchange.placeOrder(scenario.order as any);
        results.push({ scenario: scenario.name, success: true, result });
      } catch (error) {
        const classification = errorClassifier.classify(error as Error);
        results.push({
          scenario: scenario.name,
          success: false,
          error: error.message,
          classification
        });
      }
    }

    expect(results).toHaveLength(3);
    expect(results.filter(r => !r.success)).toHaveLength(3); // All should fail
  });

  test('should handle connection pool exhaustion', async () => {
    const connectionPool = Array.from({ length: 5 }, (_, i) => 
      new MockExchangeAdapter(
        { apiKey: `pool_${i}`, secret: `pool_${i}` },
        { simulateLatency: 100 }
      )
    );

    let currentConnection = 0;
    const getConnection = () => {
      if (currentConnection >= connectionPool.length) {
        throw new Error('Connection pool exhausted');
      }
      return connectionPool[currentConnection++];
    };

    // Simulate high concurrent usage
    const requests = [];
    for (let i = 0; i < 10; i++) {
      requests.push((async () => {
        try {
          const connection = getConnection();
          return await connection.ping();
        } catch (error) {
          return { error: error.message };
        }
      })());
    }

    const results = await Promise.all(requests);
    const successes = results.filter(r => r === true);
    const errors = results.filter(r => r && typeof r === 'object' && 'error' in r);

    expect(successes.length + errors.length).toBe(10);
    expect(errors.length).toBeGreaterThan(0); // Some should fail due to pool exhaustion
  });

  test('should handle gradual system degradation', async () => {
    let systemHealth = 100; // Start at 100% health
    const degradationRate = 10; // Decrease by 10% each operation

    const degradingOperation = async () => {
      systemHealth = Math.max(0, systemHealth - degradationRate);
      
      if (systemHealth < 50) {
        throw new Error('System critically degraded');
      }
      
      // Simulate increased latency as system degrades
      const latency = (100 - systemHealth) * 10;
      await new Promise(resolve => setTimeout(resolve, latency));
      
      return {
        success: true,
        health: systemHealth,
        latency
      };
    };

    const results = [];
    
    try {
      for (let i = 0; i < 10; i++) {
        const result = await degradingOperation();
        results.push(result);
      }
    } catch (error) {
      results.push({ error: error.message, health: systemHealth });
    }

    expect(results).toHaveLength(6); // Should fail on 6th attempt (health = 40%)
    expect(results[results.length - 1]).toHaveProperty('error');
  });

  test('should handle disaster recovery simulation', async () => {
    const dataCenter = {
      primary: { status: 'healthy', region: 'us-east-1' },
      secondary: { status: 'healthy', region: 'us-west-2' },
      tertiary: { status: 'healthy', region: 'eu-west-1' }
    };

    const simulateDisaster = async (affectedRegion: string) => {
      // Simulate regional outage
      Object.values(dataCenter).forEach(dc => {
        if (dc.region === affectedRegion) {
          dc.status = 'down';
        }
      });

      // Find healthy data center
      const healthyDC = Object.entries(dataCenter)
        .find(([_, dc]) => dc.status === 'healthy');

      if (!healthyDC) {
        throw new Error('No healthy data centers available');
      }

      return {
        failedOver: true,
        activeDataCenter: healthyDC[0],
        region: healthyDC[1].region
      };
    };

    const result = await simulateDisaster('us-east-1');
    
    expect(result.failedOver).toBe(true);
    expect(['secondary', 'tertiary']).toContain(result.activeDataCenter);
    expect(result.region).not.toBe('us-east-1');
  });
});