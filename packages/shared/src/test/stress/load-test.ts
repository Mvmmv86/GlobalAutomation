import { MockExchangeAdapter } from '../mocks/exchange-mock';

/**
 * Comprehensive stress testing for the trading system
 * Tests system limits and behavior under extreme conditions
 */

interface LoadTestConfig {
  concurrency: number;
  duration: number; // in seconds
  rampUpTime: number; // in seconds
  operations: {
    placeOrder: number; // percentage
    getTicker: number;
    getBalance: number;
    getPositions: number;
  };
}

interface LoadTestResult {
  totalOperations: number;
  successfulOperations: number;
  failedOperations: number;
  averageLatency: number;
  maxLatency: number;
  minLatency: number;
  operationsPerSecond: number;
  errorRate: number;
  memoryUsage: {
    start: NodeJS.MemoryUsage;
    end: NodeJS.MemoryUsage;
    peak: NodeJS.MemoryUsage;
  };
  latencyDistribution: {
    p50: number;
    p75: number;
    p90: number;
    p95: number;
    p99: number;
  };
}

class LoadTester {
  private exchanges: MockExchangeAdapter[] = [];
  private metrics: {
    operations: Array<{ timestamp: number; latency: number; success: boolean; operation: string }>;
    memorySnapshots: Array<{ timestamp: number; memory: NodeJS.MemoryUsage }>;
  } = {
    operations: [],
    memorySnapshots: []
  };

  constructor(private config: LoadTestConfig) {
    // Create pool of exchange connections
    for (let i = 0; i < config.concurrency; i++) {
      this.exchanges.push(new MockExchangeAdapter(
        { apiKey: `test_${i}`, secret: `test_${i}` },
        {
          simulateLatency: 10, // Low latency for stress testing
          simulateErrors: false,
          balances: { 
            USDT: 100000,
            BTC: 10,
            ETH: 100
          }
        }
      ));
    }
  }

  async runLoadTest(): Promise<LoadTestResult> {
    console.log(`🚀 Starting load test with ${this.config.concurrency} concurrent connections`);
    console.log(`📊 Duration: ${this.config.duration}s, Ramp-up: ${this.config.rampUpTime}s`);
    
    const startTime = Date.now();
    const endTime = startTime + (this.config.duration * 1000);
    
    // Start memory monitoring
    const memoryMonitor = this.startMemoryMonitoring();
    
    // Start workers with ramp-up
    const workers = [];
    for (let i = 0; i < this.config.concurrency; i++) {
      const delay = (this.config.rampUpTime * 1000 * i) / this.config.concurrency;
      workers.push(this.startWorker(i, startTime + delay, endTime));
    }
    
    // Wait for all workers to complete
    await Promise.all(workers);
    
    // Stop memory monitoring
    clearInterval(memoryMonitor);
    
    return this.calculateResults(startTime, endTime);
  }

  private async startWorker(workerId: number, startTime: number, endTime: number): Promise<void> {
    const exchange = this.exchanges[workerId];
    
    // Wait for ramp-up time
    const currentTime = Date.now();
    if (currentTime < startTime) {
      await new Promise(resolve => setTimeout(resolve, startTime - currentTime));
    }
    
    while (Date.now() < endTime) {
      const operation = this.selectRandomOperation();
      const operationStartTime = Date.now();
      
      try {
        await this.executeOperation(exchange, operation, workerId);
        
        const latency = Date.now() - operationStartTime;
        this.metrics.operations.push({
          timestamp: operationStartTime,
          latency,
          success: true,
          operation
        });
        
      } catch (error) {
        const latency = Date.now() - operationStartTime;
        this.metrics.operations.push({
          timestamp: operationStartTime,
          latency,
          success: false,
          operation
        });
        
        console.error(`❌ Worker ${workerId} failed ${operation}:`, error.message);
      }
      
      // Small pause to prevent overwhelming
      await new Promise(resolve => setTimeout(resolve, 1));
    }
  }

  private selectRandomOperation(): string {
    const rand = Math.random() * 100;
    let cumulative = 0;
    
    for (const [operation, percentage] of Object.entries(this.config.operations)) {
      cumulative += percentage;
      if (rand <= cumulative) {
        return operation;
      }
    }
    
    return 'placeOrder'; // fallback
  }

  private async executeOperation(exchange: MockExchangeAdapter, operation: string, workerId: number): Promise<any> {
    switch (operation) {
      case 'placeOrder':
        return await exchange.placeOrder({
          symbol: 'BTCUSDT',
          side: Math.random() > 0.5 ? 'buy' : 'sell',
          amount: 0.001,
          type: 'market',
          clientOrderId: `stress_test_${workerId}_${Date.now()}`
        });
        
      case 'getTicker':
        const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'];
        const randomSymbol = symbols[Math.floor(Math.random() * symbols.length)];
        return await exchange.getTicker(randomSymbol);
        
      case 'getBalance':
        return await exchange.getBalance();
        
      case 'getPositions':
        return await exchange.getPositions();
        
      default:
        throw new Error(`Unknown operation: ${operation}`);
    }
  }

  private startMemoryMonitoring(): NodeJS.Timeout {
    return setInterval(() => {
      this.metrics.memorySnapshots.push({
        timestamp: Date.now(),
        memory: process.memoryUsage()
      });
    }, 1000);
  }

  private calculateResults(startTime: number, endTime: number): LoadTestResult {
    const totalDuration = (endTime - startTime) / 1000;
    const operations = this.metrics.operations;
    const successfulOps = operations.filter(op => op.success);
    const failedOps = operations.filter(op => !op.success);
    
    // Latency calculations
    const latencies = successfulOps.map(op => op.latency).sort((a, b) => a - b);
    const avgLatency = latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length || 0;
    
    // Memory usage
    const memorySnapshots = this.metrics.memorySnapshots;
    const startMemory = memorySnapshots[0]?.memory || process.memoryUsage();
    const endMemory = memorySnapshots[memorySnapshots.length - 1]?.memory || process.memoryUsage();
    const peakMemory = memorySnapshots.reduce((peak, snapshot) => 
      snapshot.memory.heapUsed > peak.heapUsed ? snapshot.memory : peak, startMemory);
    
    // Latency percentiles
    const getPercentile = (arr: number[], percentile: number): number => {
      const index = Math.ceil((percentile / 100) * arr.length) - 1;
      return arr[index] || 0;
    };

    return {
      totalOperations: operations.length,
      successfulOperations: successfulOps.length,
      failedOperations: failedOps.length,
      averageLatency: avgLatency,
      maxLatency: Math.max(...latencies, 0),
      minLatency: Math.min(...latencies, 0),
      operationsPerSecond: operations.length / totalDuration,
      errorRate: (failedOps.length / operations.length) * 100,
      memoryUsage: {
        start: startMemory,
        end: endMemory,
        peak: peakMemory
      },
      latencyDistribution: {
        p50: getPercentile(latencies, 50),
        p75: getPercentile(latencies, 75),
        p90: getPercentile(latencies, 90),
        p95: getPercentile(latencies, 95),
        p99: getPercentile(latencies, 99)
      }
    };
  }

  printResults(result: LoadTestResult): void {
    console.log('\n🎯 === LOAD TEST RESULTS ===');
    console.log(`📈 Operations: ${result.totalOperations} total, ${result.successfulOperations} success, ${result.failedOperations} failed`);
    console.log(`⚡ Throughput: ${result.operationsPerSecond.toFixed(2)} ops/sec`);
    console.log(`⏱️  Average Latency: ${result.averageLatency.toFixed(2)}ms`);
    console.log(`📊 Latency Distribution:`);
    console.log(`   P50: ${result.latencyDistribution.p50.toFixed(2)}ms`);
    console.log(`   P90: ${result.latencyDistribution.p90.toFixed(2)}ms`);
    console.log(`   P95: ${result.latencyDistribution.p95.toFixed(2)}ms`);
    console.log(`   P99: ${result.latencyDistribution.p99.toFixed(2)}ms`);
    console.log(`   Max: ${result.maxLatency.toFixed(2)}ms`);
    console.log(`❌ Error Rate: ${result.errorRate.toFixed(2)}%`);
    
    const memoryUsedMB = (result.memoryUsage.end.heapUsed - result.memoryUsage.start.heapUsed) / 1024 / 1024;
    const peakMemoryMB = result.memoryUsage.peak.heapUsed / 1024 / 1024;
    console.log(`💾 Memory Usage: ${memoryUsedMB.toFixed(2)}MB increase, ${peakMemoryMB.toFixed(2)}MB peak`);
    console.log('==============================\n');
  }
}

// Export for testing
export { LoadTester, LoadTestConfig, LoadTestResult };

// CLI execution
if (require.main === module) {
  const testConfigs: Record<string, LoadTestConfig> = {
    light: {
      concurrency: 10,
      duration: 30,
      rampUpTime: 5,
      operations: {
        placeOrder: 40,
        getTicker: 30,
        getBalance: 20,
        getPositions: 10
      }
    },
    
    medium: {
      concurrency: 50,
      duration: 60,
      rampUpTime: 10,
      operations: {
        placeOrder: 50,
        getTicker: 25,
        getBalance: 15,
        getPositions: 10
      }
    },
    
    heavy: {
      concurrency: 100,
      duration: 120,
      rampUpTime: 20,
      operations: {
        placeOrder: 60,
        getTicker: 25,
        getBalance: 10,
        getPositions: 5
      }
    },
    
    burst: {
      concurrency: 200,
      duration: 30,
      rampUpTime: 2,
      operations: {
        placeOrder: 80,
        getTicker: 15,
        getBalance: 3,
        getPositions: 2
      }
    }
  };

  async function runStressTest() {
    const testType = process.argv[2] || 'light';
    const config = testConfigs[testType];
    
    if (!config) {
      console.error(`❌ Unknown test type: ${testType}`);
      console.log('Available types:', Object.keys(testConfigs).join(', '));
      process.exit(1);
    }

    console.log(`🧪 Running ${testType} load test...`);
    const tester = new LoadTester(config);
    
    try {
      const result = await tester.runLoadTest();
      tester.printResults(result);
      
      // Exit with error code if results are poor
      if (result.errorRate > 5) {
        console.error('❌ Test failed: Error rate too high');
        process.exit(1);
      }
      
      if (result.averageLatency > 200) {
        console.error('❌ Test failed: Average latency too high');
        process.exit(1);
      }
      
      console.log('✅ Load test passed!');
      process.exit(0);
      
    } catch (error) {
      console.error('❌ Load test failed:', error);
      process.exit(1);
    }
  }

  runStressTest();
}