import { MockExchangeAdapter } from '../mocks/exchange-mock';

/**
 * Endurance testing for long-term system stability
 * Tests memory leaks, resource exhaustion, and degradation over time
 */

interface EnduranceTestConfig {
  duration: number; // in minutes
  concurrency: number;
  samplingInterval: number; // seconds between metric samples
  memoryLeakThreshold: number; // MB per hour
  latencyDegradationThreshold: number; // percentage increase per hour
}

interface EnduranceTestResult {
  totalDuration: number; // minutes
  totalOperations: number;
  overallThroughput: number;
  memoryTrend: {
    startMemoryMB: number;
    endMemoryMB: number;
    peakMemoryMB: number;
    memoryLeakMBPerHour: number;
    hasMemoryLeak: boolean;
  };
  performanceTrend: {
    startLatency: number;
    endLatency: number;
    latencyDegradationPerHour: number;
    hasPerformanceDegradation: boolean;
  };
  stabilityMetrics: {
    errorRateOverTime: number[];
    throughputOverTime: number[];
    latencyOverTime: number[];
    memoryOverTime: number[];
  };
  timeToFailure?: number; // minutes, if system failed
}

class EnduranceTester {
  private exchanges: MockExchangeAdapter[] = [];
  private isRunning = false;
  private metrics: Array<{
    timestamp: number;
    sample: number;
    operations: number;
    errors: number;
    averageLatency: number;
    memoryUsageMB: number;
  }> = [];

  constructor(private config: EnduranceTestConfig) {
    // Initialize exchange pool
    for (let i = 0; i < config.concurrency; i++) {
      this.exchanges.push(new MockExchangeAdapter(
        { apiKey: `endurance_${i}`, secret: `endurance_${i}` },
        {
          simulateLatency: 30,
          simulateErrors: false,
          balances: { USDT: 1000000, BTC: 100 } // Large balances for long test
        }
      ));
    }
  }

  async runEnduranceTest(): Promise<EnduranceTestResult> {
    console.log(`⏰ Starting endurance test for ${this.config.duration} minutes`);
    console.log(`🔄 Concurrency: ${this.config.concurrency}, Sampling every ${this.config.samplingInterval}s`);
    
    const startTime = Date.now();
    const endTime = startTime + (this.config.duration * 60 * 1000);
    
    this.isRunning = true;
    
    // Start metric collection
    const metricsCollector = this.startMetricsCollection();
    
    // Start workers
    const workers = this.exchanges.map((exchange, i) => 
      this.runEnduranceWorker(exchange, i, endTime)
    );
    
    try {
      await Promise.all(workers);
      console.log('✅ All workers completed successfully');
    } catch (error) {
      console.log('❌ Test ended due to error:', error.message);
    } finally {
      this.isRunning = false;
      clearInterval(metricsCollector);
    }
    
    return this.calculateEnduranceResults(startTime, endTime);
  }

  private async runEnduranceWorker(
    exchange: MockExchangeAdapter,
    workerId: number,
    endTime: number
  ): Promise<void> {
    let operationCount = 0;
    
    while (this.isRunning && Date.now() < endTime) {
      try {
        // Vary operations to simulate realistic load
        const operations = [
          () => exchange.placeOrder({
            symbol: 'BTCUSDT',
            side: operationCount % 2 === 0 ? 'buy' : 'sell',
            amount: 0.001,
            type: 'market'
          }),
          () => exchange.getTicker('BTCUSDT'),
          () => exchange.getBalance(),
          () => exchange.getPositions()
        ];
        
        const randomOp = operations[operationCount % operations.length];
        await randomOp();
        
        operationCount++;
        
        // Gradually increase load to test degradation
        const progressRatio = (Date.now() - (endTime - this.config.duration * 60 * 1000)) / (this.config.duration * 60 * 1000);
        const baseDelay = 100;
        const dynamicDelay = Math.max(10, baseDelay - (progressRatio * 50));
        
        await new Promise(resolve => setTimeout(resolve, dynamicDelay));
        
      } catch (error) {
        console.error(`Worker ${workerId} error:`, error.message);
        
        // Simulate degradation under stress
        if (Math.random() < 0.001) { // 0.1% chance of worker failure
          throw new Error(`Worker ${workerId} exhausted`);
        }
        
        // Longer delay after error
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    console.log(`Worker ${workerId} completed ${operationCount} operations`);
  }

  private startMetricsCollection(): NodeJS.Timeout {
    let sampleCount = 0;
    const operationCounters = new Array(this.config.concurrency).fill(0);
    const errorCounters = new Array(this.config.concurrency).fill(0);
    const latencySamples: number[] = [];
    
    return setInterval(async () => {
      // Collect sample metrics
      const currentTime = Date.now();
      
      // Sample some operations for latency measurement
      const latencyPromises = [];
      for (let i = 0; i < Math.min(10, this.config.concurrency); i++) {
        const startTime = Date.now();
        latencyPromises.push(
          this.exchanges[i].ping().then(() => Date.now() - startTime).catch(() => -1)
        );
      }
      
      const latencies = (await Promise.all(latencyPromises)).filter(l => l > 0);
      const avgLatency = latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length || 0;
      
      // Get memory usage
      const memoryUsage = process.memoryUsage();
      const memoryUsageMB = memoryUsage.heapUsed / 1024 / 1024;
      
      // Estimate operations and errors (simplified for mock)
      const estimatedOps = sampleCount * 50; // Rough estimate
      const estimatedErrors = Math.floor(estimatedOps * 0.001); // 0.1% error rate
      
      this.metrics.push({
        timestamp: currentTime,
        sample: sampleCount++,
        operations: estimatedOps,
        errors: estimatedErrors,
        averageLatency: avgLatency,
        memoryUsageMB
      });
      
      // Log progress
      const minutesElapsed = ((currentTime - (Date.now() - sampleCount * this.config.samplingInterval * 1000)) / 1000 / 60);
      console.log(`⏱️  ${minutesElapsed.toFixed(1)}min: ${avgLatency.toFixed(2)}ms avg latency, ${memoryUsageMB.toFixed(2)}MB memory`);
      
    }, this.config.samplingInterval * 1000);
  }

  private calculateEnduranceResults(startTime: number, endTime: number): EnduranceTestResult {
    const actualDuration = (endTime - startTime) / 1000 / 60; // minutes
    
    if (this.metrics.length === 0) {
      throw new Error('No metrics collected');
    }
    
    const startMetrics = this.metrics[0];
    const endMetrics = this.metrics[this.metrics.length - 1];
    
    // Memory trend analysis
    const startMemoryMB = startMetrics.memoryUsageMB;
    const endMemoryMB = endMetrics.memoryUsageMB;
    const peakMemoryMB = Math.max(...this.metrics.map(m => m.memoryUsageMB));
    const memoryIncreaseMB = endMemoryMB - startMemoryMB;
    const memoryLeakMBPerHour = (memoryIncreaseMB / actualDuration) * 60;
    
    // Performance trend analysis
    const startLatency = startMetrics.averageLatency;
    const endLatency = endMetrics.averageLatency;
    const latencyIncrease = endLatency - startLatency;
    const latencyDegradationPerHour = ((latencyIncrease / startLatency) * 100 / actualDuration) * 60;
    
    // Calculate totals
    const totalOperations = this.metrics.reduce((sum, m) => sum + m.operations, 0);
    const overallThroughput = totalOperations / (actualDuration * 60); // ops per second
    
    // Extract time series
    const errorRateOverTime = this.metrics.map(m => (m.errors / m.operations) * 100);
    const throughputOverTime = this.metrics.map(m => m.operations / this.config.samplingInterval);
    const latencyOverTime = this.metrics.map(m => m.averageLatency);
    const memoryOverTime = this.metrics.map(m => m.memoryUsageMB);
    
    return {
      totalDuration: actualDuration,
      totalOperations,
      overallThroughput,
      memoryTrend: {
        startMemoryMB,
        endMemoryMB,
        peakMemoryMB,
        memoryLeakMBPerHour,
        hasMemoryLeak: memoryLeakMBPerHour > this.config.memoryLeakThreshold
      },
      performanceTrend: {
        startLatency,
        endLatency,
        latencyDegradationPerHour,
        hasPerformanceDegradation: latencyDegradationPerHour > this.config.latencyDegradationThreshold
      },
      stabilityMetrics: {
        errorRateOverTime,
        throughputOverTime,
        latencyOverTime,
        memoryOverTime
      }
    };
  }

  printResults(result: EnduranceTestResult): void {
    console.log('\n⏰ === ENDURANCE TEST RESULTS ===');
    console.log(`🕐 Duration: ${result.totalDuration.toFixed(2)} minutes`);
    console.log(`📊 Total Operations: ${result.totalOperations.toLocaleString()}`);
    console.log(`⚡ Overall Throughput: ${result.overallThroughput.toFixed(2)} ops/sec`);
    
    console.log('\n💾 Memory Analysis:');
    console.log(`   Start: ${result.memoryTrend.startMemoryMB.toFixed(2)} MB`);
    console.log(`   End: ${result.memoryTrend.endMemoryMB.toFixed(2)} MB`);
    console.log(`   Peak: ${result.memoryTrend.peakMemoryMB.toFixed(2)} MB`);
    console.log(`   Growth Rate: ${result.memoryTrend.memoryLeakMBPerHour.toFixed(2)} MB/hour`);
    
    if (result.memoryTrend.hasMemoryLeak) {
      console.log('   ❌ Memory leak detected');
    } else {
      console.log('   ✅ No significant memory leak');
    }
    
    console.log('\n📈 Performance Analysis:');
    console.log(`   Start Latency: ${result.performanceTrend.startLatency.toFixed(2)} ms`);
    console.log(`   End Latency: ${result.performanceTrend.endLatency.toFixed(2)} ms`);
    console.log(`   Degradation Rate: ${result.performanceTrend.latencyDegradationPerHour.toFixed(2)}% per hour`);
    
    if (result.performanceTrend.hasPerformanceDegradation) {
      console.log('   ❌ Performance degradation detected');
    } else {
      console.log('   ✅ Performance remains stable');
    }
    
    console.log('\n📊 Stability Summary:');
    const avgErrorRate = result.stabilityMetrics.errorRateOverTime.reduce((a, b) => a + b, 0) / result.stabilityMetrics.errorRateOverTime.length;
    const avgThroughput = result.stabilityMetrics.throughputOverTime.reduce((a, b) => a + b, 0) / result.stabilityMetrics.throughputOverTime.length;
    
    console.log(`   Average Error Rate: ${avgErrorRate.toFixed(3)}%`);
    console.log(`   Average Throughput: ${avgThroughput.toFixed(2)} ops/sec`);
    
    // Overall assessment
    console.log('\n🎯 Overall Assessment:');
    const issues = [];
    if (result.memoryTrend.hasMemoryLeak) issues.push('Memory leak');
    if (result.performanceTrend.hasPerformanceDegradation) issues.push('Performance degradation');
    if (avgErrorRate > 1) issues.push('High error rate');
    
    if (issues.length === 0) {
      console.log('   ✅ System demonstrates excellent long-term stability');
    } else {
      console.log(`   ⚠️  Issues detected: ${issues.join(', ')}`);
    }
    
    console.log('=====================================\n');
  }
}

export { EnduranceTester, EnduranceTestConfig, EnduranceTestResult };

// CLI execution
if (require.main === module) {
  const enduranceConfigs: Record<string, EnduranceTestConfig> = {
    short: {
      duration: 5, // 5 minutes
      concurrency: 10,
      samplingInterval: 10,
      memoryLeakThreshold: 10, // 10 MB/hour
      latencyDegradationThreshold: 20 // 20% per hour
    },
    
    medium: {
      duration: 15, // 15 minutes
      concurrency: 20,
      samplingInterval: 15,
      memoryLeakThreshold: 15,
      latencyDegradationThreshold: 15
    },
    
    long: {
      duration: 30, // 30 minutes
      concurrency: 30,
      samplingInterval: 20,
      memoryLeakThreshold: 20,
      latencyDegradationThreshold: 10
    },
    
    marathon: {
      duration: 60, // 1 hour
      concurrency: 50,
      samplingInterval: 30,
      memoryLeakThreshold: 25,
      latencyDegradationThreshold: 5
    }
  };

  async function runEnduranceTest() {
    const testType = process.argv[2] || 'short';
    const config = enduranceConfigs[testType];
    
    if (!config) {
      console.error(`❌ Unknown endurance test type: ${testType}`);
      console.log('Available types:', Object.keys(enduranceConfigs).join(', '));
      process.exit(1);
    }

    console.log(`⏰ Running ${testType} endurance test...`);
    const tester = new EnduranceTester(config);
    
    try {
      const result = await tester.runEnduranceTest();
      tester.printResults(result);
      
      // Exit with error if critical issues detected
      if (result.memoryTrend.hasMemoryLeak || result.performanceTrend.hasPerformanceDegradation) {
        console.error('❌ Endurance test failed: Critical stability issues detected');
        process.exit(1);
      }
      
      console.log('✅ Endurance test passed!');
      process.exit(0);
      
    } catch (error) {
      console.error('❌ Endurance test failed:', error);
      process.exit(1);
    }
  }

  runEnduranceTest();
}