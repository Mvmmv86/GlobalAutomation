import { MockExchangeAdapter } from '../mocks/exchange-mock';

/**
 * Performance and load testing for the trading system
 * Tests system behavior under high load and concurrent operations
 */
describe('Performance and Load Integration Tests', () => {
  let mockExchange: MockExchangeAdapter;
  
  beforeEach(() => {
    mockExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test' },
      {
        simulateLatency: 50, // More realistic latency
        balances: { USDT: 100000, BTC: 10, ETH: 100 }
      }
    );
  });

  test('should handle concurrent order placement', async () => {
    const orderCount = 50;
    const orderPromises = [];

    const startTime = Date.now();
    
    // Create multiple concurrent orders
    for (let i = 0; i < orderCount; i++) {
      const promise = mockExchange.placeOrder({
        symbol: 'BTCUSDT',
        side: i % 2 === 0 ? 'buy' : 'sell',
        amount: 0.001,
        type: 'market',
        clientOrderId: `test_order_${i}`
      });
      orderPromises.push(promise);
    }

    const orders = await Promise.all(orderPromises);
    const endTime = Date.now();
    const totalTime = endTime - startTime;
    
    expect(orders).toHaveLength(orderCount);
    expect(totalTime).toBeLessThan(orderCount * 100); // Should be faster than sequential
    
    // Verify all orders have unique IDs
    const orderIds = orders.map(o => o.id);
    const uniqueIds = new Set(orderIds);
    expect(uniqueIds.size).toBe(orderCount);
  });

  test('should handle high-frequency ticker requests', async () => {
    const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT'];
    const requestCount = 100;
    const requests = [];

    const startTime = Date.now();
    
    for (let i = 0; i < requestCount; i++) {
      const symbol = symbols[i % symbols.length];
      requests.push(mockExchange.getTicker(symbol));
    }

    const tickers = await Promise.all(requests);
    const endTime = Date.now();
    const totalTime = endTime - startTime;
    
    expect(tickers).toHaveLength(requestCount);
    expect(totalTime).toBeLessThan(requestCount * 30); // Average < 30ms per request
    
    // Verify all tickers have valid data
    tickers.forEach(ticker => {
      expect(ticker.price).toBeGreaterThan(0);
      expect(ticker.timestamp).toBeInstanceOf(Date);
    });
  });

  test('should handle rapid balance checks', async () => {
    const balanceCheckCount = 200;
    const promises = [];

    const startTime = Date.now();
    
    for (let i = 0; i < balanceCheckCount; i++) {
      promises.push(mockExchange.getBalance());
    }

    const balances = await Promise.all(promises);
    const endTime = Date.now();
    const avgTime = (endTime - startTime) / balanceCheckCount;
    
    expect(balances).toHaveLength(balanceCheckCount);
    expect(avgTime).toBeLessThan(25); // Average < 25ms per request
    
    // All balances should be consistent
    balances.forEach(balance => {
      expect(balance.USDT).toBeGreaterThan(0);
    });
  });

  test('should handle burst trading scenarios', async () => {
    const burstSize = 20;
    const burstCount = 5;
    const allOrders = [];

    for (let burst = 0; burst < burstCount; burst++) {
      const burstStartTime = Date.now();
      const burstPromises = [];

      // Create burst of orders
      for (let i = 0; i < burstSize; i++) {
        burstPromises.push(
          mockExchange.placeOrder({
            symbol: 'BTCUSDT',
            side: i % 2 === 0 ? 'buy' : 'sell',
            amount: 0.001,
            type: 'market',
            clientOrderId: `burst_${burst}_order_${i}`
          })
        );
      }

      const burstOrders = await Promise.all(burstPromises);
      const burstEndTime = Date.now();
      const burstTime = burstEndTime - burstStartTime;
      
      expect(burstOrders).toHaveLength(burstSize);
      expect(burstTime).toBeLessThan(burstSize * 75); // Allow more time for bursts
      
      allOrders.push(...burstOrders);
      
      // Small delay between bursts
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    expect(allOrders).toHaveLength(burstSize * burstCount);
    
    // Verify system state consistency
    const finalState = mockExchange.getMockState();
    expect(finalState.orders).toHaveLength(burstSize * burstCount);
  });

  test('should handle mixed operation load', async () => {
    const operations = [];
    const operationCount = 100;

    // Mix different types of operations
    for (let i = 0; i < operationCount; i++) {
      const rand = Math.random();
      
      if (rand < 0.4) {
        // 40% - Place orders
        operations.push(
          mockExchange.placeOrder({
            symbol: 'BTCUSDT',
            side: i % 2 === 0 ? 'buy' : 'sell',
            amount: 0.001,
            type: 'market'
          })
        );
      } else if (rand < 0.6) {
        // 20% - Get ticker
        operations.push(mockExchange.getTicker('BTCUSDT'));
      } else if (rand < 0.8) {
        // 20% - Get balance
        operations.push(mockExchange.getBalance());
      } else {
        // 20% - Get positions
        operations.push(mockExchange.getPositions());
      }
    }

    const startTime = Date.now();
    const results = await Promise.all(operations);
    const endTime = Date.now();
    const totalTime = endTime - startTime;
    
    expect(results).toHaveLength(operationCount);
    expect(totalTime).toBeLessThan(operationCount * 100); // Average < 100ms per operation
  });

  test('should handle memory usage during heavy load', async () => {
    const initialMemory = process.memoryUsage();
    
    // Perform heavy operations
    const heavyOperations = [];
    for (let i = 0; i < 1000; i++) {
      heavyOperations.push(
        mockExchange.placeOrder({
          symbol: 'BTCUSDT',
          side: 'buy',
          amount: 0.001,
          type: 'market'
        })
      );
    }

    await Promise.all(heavyOperations);
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
    
    const finalMemory = process.memoryUsage();
    const memoryIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
    
    // Memory increase should be reasonable (< 50MB for 1000 operations)
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
  });

  test('should maintain accuracy under load', async () => {
    const orderCount = 100;
    const orderAmount = 0.001;
    const expectedTotalVolume = orderCount * orderAmount;
    
    const orders = [];
    for (let i = 0; i < orderCount; i++) {
      orders.push(
        mockExchange.placeOrder({
          symbol: 'BTCUSDT',
          side: 'buy',
          amount: orderAmount,
          type: 'market'
        })
      );
    }

    const results = await Promise.all(orders);
    
    // Calculate total filled amount
    const totalFilled = results.reduce((sum, order) => sum + order.filled, 0);
    
    // Should be accurate to 8 decimal places
    expect(Math.abs(totalFilled - expectedTotalVolume)).toBeLessThan(1e-8);
    
    // All orders should be fully filled
    results.forEach(order => {
      expect(order.filled).toBe(orderAmount);
      expect(order.remaining).toBe(0);
    });
  });

  test('should handle latency spikes gracefully', async () => {
    const highLatencyExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test' },
      {
        simulateLatency: 500, // High latency
        balances: { USDT: 10000 }
      }
    );

    const operationCount = 10;
    const promises = [];
    
    // Execute operations sequentially to ensure latency is reflected
    const startTime = Date.now();
    
    for (let i = 0; i < operationCount; i++) {
      const result = await highLatencyExchange.ping();
      expect(result).toBe(true);
    }

    const endTime = Date.now();
    const totalTime = endTime - startTime;
    const avgTime = totalTime / operationCount;
    
    expect(avgTime).toBeGreaterThan(400); // Should reflect high latency
    expect(avgTime).toBeLessThan(600); // But not much higher
  });

  test('should handle connection pooling simulation', async () => {
    const poolSize = 5;
    const requestsPerConnection = 20;
    const totalRequests = poolSize * requestsPerConnection;
    
    const connectionPools = [];
    
    // Create multiple exchange connections
    for (let i = 0; i < poolSize; i++) {
      connectionPools.push(
        new MockExchangeAdapter(
          { apiKey: `test_${i}`, secret: `test_${i}` },
          {
            simulateLatency: 30,
            balances: { USDT: 10000 }
          }
        )
      );
    }

    const allPromises = [];
    
    // Distribute requests across pool
    for (let i = 0; i < totalRequests; i++) {
      const poolIndex = i % poolSize;
      allPromises.push(
        connectionPools[poolIndex].getTicker('BTCUSDT')
      );
    }

    const startTime = Date.now();
    const results = await Promise.all(allPromises);
    const endTime = Date.now();
    const totalTime = endTime - startTime;
    
    expect(results).toHaveLength(totalRequests);
    expect(totalTime).toBeLessThan(totalRequests * 50); // Efficient with pooling
  });
});