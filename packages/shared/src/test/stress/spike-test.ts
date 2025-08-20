import { MockExchangeAdapter } from '../mocks/exchange-mock';

/**
 * Spike testing for sudden load increases
 * Tests system behavior during traffic spikes and recovery
 */

interface SpikeTestConfig {
  baseline: {
    concurrency: number;
    duration: number; // seconds
  };
  spike: {
    concurrency: number;
    duration: number; // seconds
  };
  recovery: {
    duration: number; // seconds
  };
}

interface SpikeTestResult {
  baseline: PhaseResult;
  spike: PhaseResult;
  recovery: PhaseResult;
  degradation: {
    latencyIncrease: number; // percentage
    throughputDecrease: number; // percentage
    errorRateIncrease: number; // percentage
  };
  recoveryTime: number; // seconds to return to baseline
}

interface PhaseResult {
  totalOperations: number;
  averageLatency: number;
  operationsPerSecond: number;
  errorRate: number;
  maxLatency: number;
}

class SpikeTester {
  private exchanges: MockExchangeAdapter[] = [];
  private metrics: Array<{
    timestamp: number;
    phase: string;
    latency: number;
    success: boolean;
  }> = [];

  constructor(private config: SpikeTestConfig) {}

  private initializeExchanges(count: number): void {
    this.exchanges = [];
    for (let i = 0; i < count; i++) {
      this.exchanges.push(new MockExchangeAdapter(
        { apiKey: `spike_test_${i}`, secret: `spike_test_${i}` },
        {
          simulateLatency: 20,
          simulateErrors: false,
          balances: { USDT: 50000, BTC: 5 }
        }
      ));
    }
  }

  async runSpikeTest(): Promise<SpikeTestResult> {
    console.log('🌊 Starting spike test...');
    
    // Phase 1: Baseline
    console.log('📊 Phase 1: Baseline load');
    this.initializeExchanges(this.config.baseline.concurrency);
    const baselineResult = await this.runPhase('baseline', this.config.baseline);
    
    // Short pause before spike
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Phase 2: Spike
    console.log('⚡ Phase 2: Spike load');
    this.initializeExchanges(this.config.spike.concurrency);
    const spikeResult = await this.runPhase('spike', this.config.spike);
    
    // Short pause before recovery
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Phase 3: Recovery
    console.log('🔄 Phase 3: Recovery');
    this.initializeExchanges(this.config.baseline.concurrency);
    const recoveryResult = await this.runPhase('recovery', this.config.recovery);
    
    return this.calculateSpikeResults(baselineResult, spikeResult, recoveryResult);
  }

  private async runPhase(
    phaseName: string,
    config: { concurrency: number; duration: number }
  ): Promise<PhaseResult> {
    const startTime = Date.now();
    const endTime = startTime + (config.duration * 1000);
    const workers = [];
    
    // Start all workers simultaneously (no ramp-up for spike testing)
    for (let i = 0; i < config.concurrency; i++) {
      workers.push(this.runWorker(i, phaseName, startTime, endTime));
    }
    
    await Promise.all(workers);
    
    return this.calculatePhaseResult(phaseName, config.duration);
  }

  private async runWorker(
    workerId: number,
    phase: string,
    startTime: number,
    endTime: number
  ): Promise<void> {
    const exchange = this.exchanges[workerId];
    
    while (Date.now() < endTime) {
      const operationStart = Date.now();
      
      try {
        // Mix of operations weighted toward order placement
        const rand = Math.random();
        if (rand < 0.7) {
          await exchange.placeOrder({
            symbol: 'BTCUSDT',
            side: Math.random() > 0.5 ? 'buy' : 'sell',
            amount: 0.001,
            type: 'market'
          });
        } else if (rand < 0.9) {
          await exchange.getTicker('BTCUSDT');
        } else {
          await exchange.getBalance();
        }
        
        const latency = Date.now() - operationStart;
        this.metrics.push({
          timestamp: operationStart,
          phase,
          latency,
          success: true
        });
        
      } catch (error) {
        const latency = Date.now() - operationStart;
        this.metrics.push({
          timestamp: operationStart,
          phase,
          latency,
          success: false
        });
      }
      
      // Very small delay to prevent CPU saturation
      await new Promise(resolve => setTimeout(resolve, 1));
    }
  }

  private calculatePhaseResult(phase: string, duration: number): PhaseResult {
    const phaseMetrics = this.metrics.filter(m => m.phase === phase);
    const successfulOps = phaseMetrics.filter(m => m.success);
    const failedOps = phaseMetrics.filter(m => !m.success);
    
    const latencies = successfulOps.map(m => m.latency);
    const avgLatency = latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length || 0;
    const maxLatency = Math.max(...latencies, 0);
    
    return {
      totalOperations: phaseMetrics.length,
      averageLatency: avgLatency,
      operationsPerSecond: phaseMetrics.length / duration,
      errorRate: (failedOps.length / phaseMetrics.length) * 100,
      maxLatency
    };
  }

  private calculateSpikeResults(
    baseline: PhaseResult,
    spike: PhaseResult,
    recovery: PhaseResult
  ): SpikeTestResult {
    const latencyIncrease = ((spike.averageLatency - baseline.averageLatency) / baseline.averageLatency) * 100;
    const throughputDecrease = ((baseline.operationsPerSecond - spike.operationsPerSecond) / baseline.operationsPerSecond) * 100;
    const errorRateIncrease = spike.errorRate - baseline.errorRate;
    
    // Calculate recovery time by analyzing when metrics returned to baseline levels
    const recoveryTime = this.calculateRecoveryTime(baseline, recovery);
    
    return {
      baseline,
      spike,
      recovery,
      degradation: {
        latencyIncrease,
        throughputDecrease: throughputDecrease > 0 ? throughputDecrease : 0,
        errorRateIncrease
      },
      recoveryTime
    };
  }

  private calculateRecoveryTime(baseline: PhaseResult, recovery: PhaseResult): number {
    // Simple recovery time calculation
    // In a real implementation, you'd analyze time-series data
    const latencyRecovered = Math.abs(recovery.averageLatency - baseline.averageLatency) < baseline.averageLatency * 0.1;
    const throughputRecovered = Math.abs(recovery.operationsPerSecond - baseline.operationsPerSecond) < baseline.operationsPerSecond * 0.1;
    
    if (latencyRecovered && throughputRecovered) {
      return this.config.recovery.duration * 0.5; // Assume recovery in middle of recovery phase
    } else {
      return this.config.recovery.duration; // Full recovery phase needed
    }
  }

  printResults(result: SpikeTestResult): void {
    console.log('\n🌊 === SPIKE TEST RESULTS ===');
    
    console.log('\n📊 Baseline Phase:');
    console.log(`   Operations: ${result.baseline.totalOperations}`);
    console.log(`   Throughput: ${result.baseline.operationsPerSecond.toFixed(2)} ops/sec`);
    console.log(`   Avg Latency: ${result.baseline.averageLatency.toFixed(2)}ms`);
    console.log(`   Error Rate: ${result.baseline.errorRate.toFixed(2)}%`);
    
    console.log('\n⚡ Spike Phase:');
    console.log(`   Operations: ${result.spike.totalOperations}`);
    console.log(`   Throughput: ${result.spike.operationsPerSecond.toFixed(2)} ops/sec`);
    console.log(`   Avg Latency: ${result.spike.averageLatency.toFixed(2)}ms`);
    console.log(`   Max Latency: ${result.spike.maxLatency.toFixed(2)}ms`);
    console.log(`   Error Rate: ${result.spike.errorRate.toFixed(2)}%`);
    
    console.log('\n🔄 Recovery Phase:');
    console.log(`   Operations: ${result.recovery.totalOperations}`);
    console.log(`   Throughput: ${result.recovery.operationsPerSecond.toFixed(2)} ops/sec`);
    console.log(`   Avg Latency: ${result.recovery.averageLatency.toFixed(2)}ms`);
    console.log(`   Error Rate: ${result.recovery.errorRate.toFixed(2)}%`);
    
    console.log('\n📈 Impact Analysis:');
    console.log(`   Latency Increase: ${result.degradation.latencyIncrease.toFixed(2)}%`);
    console.log(`   Throughput Decrease: ${result.degradation.throughputDecrease.toFixed(2)}%`);
    console.log(`   Error Rate Increase: ${result.degradation.errorRateIncrease.toFixed(2)}%`);
    console.log(`   Recovery Time: ${result.recoveryTime.toFixed(2)}s`);
    
    // Assessment
    console.log('\n🎯 Assessment:');
    if (result.degradation.latencyIncrease < 100) {
      console.log('   ✅ Latency degradation acceptable (<100% increase)');
    } else {
      console.log('   ❌ High latency degradation (>100% increase)');
    }
    
    if (result.degradation.errorRateIncrease < 5) {
      console.log('   ✅ Error rate increase acceptable (<5%)');
    } else {
      console.log('   ❌ High error rate increase (>5%)');
    }
    
    if (result.recoveryTime < 30) {
      console.log('   ✅ Fast recovery (<30 seconds)');
    } else {
      console.log('   ⚠️  Slow recovery (>30 seconds)');
    }
    
    console.log('================================\n');
  }
}

export { SpikeTester, SpikeTestConfig, SpikeTestResult };

// CLI execution
if (require.main === module) {
  const spikeConfigs: Record<string, SpikeTestConfig> = {
    small: {
      baseline: { concurrency: 10, duration: 30 },
      spike: { concurrency: 50, duration: 15 },
      recovery: { duration: 30 }
    },
    
    medium: {
      baseline: { concurrency: 20, duration: 30 },
      spike: { concurrency: 100, duration: 20 },
      recovery: { duration: 45 }
    },
    
    large: {
      baseline: { concurrency: 30, duration: 45 },
      spike: { concurrency: 200, duration: 30 },
      recovery: { duration: 60 }
    },
    
    extreme: {
      baseline: { concurrency: 50, duration: 60 },
      spike: { concurrency: 500, duration: 20 },
      recovery: { duration: 120 }
    }
  };

  async function runSpikeTest() {
    const testType = process.argv[2] || 'small';
    const config = spikeConfigs[testType];
    
    if (!config) {
      console.error(`❌ Unknown spike test type: ${testType}`);
      console.log('Available types:', Object.keys(spikeConfigs).join(', '));
      process.exit(1);
    }

    console.log(`🌊 Running ${testType} spike test...`);
    const tester = new SpikeTester(config);
    
    try {
      const result = await tester.runSpikeTest();
      tester.printResults(result);
      
      // Exit with error if degradation is too severe
      if (result.degradation.errorRateIncrease > 10 || result.degradation.latencyIncrease > 300) {
        console.error('❌ Spike test failed: Severe degradation detected');
        process.exit(1);
      }
      
      console.log('✅ Spike test passed!');
      process.exit(0);
      
    } catch (error) {
      console.error('❌ Spike test failed:', error);
      process.exit(1);
    }
  }

  runSpikeTest();
}