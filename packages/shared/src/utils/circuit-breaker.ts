import { TradingError, ErrorCategory, TradingErrorHandler } from './error-handling';

export interface CircuitBreakerConfig {
  failureThreshold: number;     // Number of failures to trip the circuit
  successThreshold: number;     // Number of successes to close the circuit
  timeout: number;             // Time to wait before attempting to close circuit (ms)
  monitoringPeriod: number;    // Time window for tracking failures (ms)
  name: string;                // Identifier for the circuit breaker
}

export enum CircuitState {
  CLOSED = 'CLOSED',     // Normal operation
  OPEN = 'OPEN',         // Circuit is open, rejecting requests
  HALF_OPEN = 'HALF_OPEN' // Testing if service recovered
}

export interface CircuitBreakerStats {
  state: CircuitState;
  failureCount: number;
  successCount: number;
  lastFailureTime: Date | null;
  lastSuccessTime: Date | null;
  lastStateChange: Date;
  requestCount: number;
  rejectedCount: number;
}

export class CircuitBreakerError extends Error {
  constructor(
    message: string,
    public circuitName: string,
    public state: CircuitState
  ) {
    super(message);
    this.name = 'CircuitBreakerError';
  }
}

/**
 * Circuit Breaker implementation for external API calls
 * Prevents cascading failures by temporarily blocking requests to failing services
 */
export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount: number = 0;
  private successCount: number = 0;
  private lastFailureTime: Date | null = null;
  private lastSuccessTime: Date | null = null;
  private lastStateChange: Date = new Date();
  private requestCount: number = 0;
  private rejectedCount: number = 0;
  private failures: Date[] = []; // Track failures in monitoring window

  constructor(private config: CircuitBreakerConfig) {
    this.validateConfig();
  }

  /**
   * Execute function with circuit breaker protection
   */
  async execute<T>(operation: () => Promise<T>): Promise<T> {
    this.requestCount++;
    this.cleanupOldFailures();

    // Check if circuit should be opened
    if (this.shouldOpen()) {
      this.openCircuit();
    }

    // Check if circuit should transition to half-open
    if (this.shouldAttemptReset()) {
      this.halfOpenCircuit();
    }

    // Reject if circuit is open
    if (this.state === CircuitState.OPEN) {
      this.rejectedCount++;
      throw new CircuitBreakerError(
        `Circuit breaker "${this.config.name}" is OPEN - rejecting request`,
        this.config.name,
        this.state
      );
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure(error as Error);
      throw error;
    }
  }

  /**
   * Handle successful operation
   */
  private onSuccess(): void {
    this.successCount++;
    this.lastSuccessTime = new Date();

    if (this.state === CircuitState.HALF_OPEN) {
      // Check if we have enough successes to close the circuit
      if (this.successCount >= this.config.successThreshold) {
        this.closeCircuit();
      }
    }
  }

  /**
   * Handle failed operation
   */
  private onFailure(error: Error): void {
    const now = new Date();
    this.failureCount++;
    this.lastFailureTime = now;
    this.failures.push(now);

    // Classify error to determine if it should count towards circuit breaking
    const tradingError = TradingErrorHandler.classifyError(error);
    const classification = TradingErrorHandler.getClassification(tradingError.category);

    // Only count failures that should trigger circuit breaking
    if (!classification.shouldCircuitBreak) {
      return;
    }

    // If in half-open state, go back to open on any qualifying failure
    if (this.state === CircuitState.HALF_OPEN) {
      this.openCircuit();
    }
  }

  /**
   * Check if circuit should be opened
   */
  private shouldOpen(): boolean {
    if (this.state !== CircuitState.CLOSED) {
      return false;
    }

    const recentFailures = this.failures.filter(
      failure => Date.now() - failure.getTime() <= this.config.monitoringPeriod
    );

    return recentFailures.length >= this.config.failureThreshold;
  }

  /**
   * Check if circuit should attempt to reset (transition to half-open)
   */
  private shouldAttemptReset(): boolean {
    if (this.state !== CircuitState.OPEN) {
      return false;
    }

    const timeSinceLastFailure = this.lastFailureTime 
      ? Date.now() - this.lastFailureTime.getTime()
      : Number.MAX_SAFE_INTEGER;

    return timeSinceLastFailure >= this.config.timeout;
  }

  /**
   * Open the circuit
   */
  private openCircuit(): void {
    if (this.state !== CircuitState.OPEN) {
      this.state = CircuitState.OPEN;
      this.lastStateChange = new Date();
      this.successCount = 0; // Reset success count
    }
  }

  /**
   * Close the circuit
   */
  private closeCircuit(): void {
    this.state = CircuitState.CLOSED;
    this.lastStateChange = new Date();
    this.failureCount = 0;
    this.successCount = 0;
    this.failures = [];
  }

  /**
   * Set circuit to half-open state
   */
  private halfOpenCircuit(): void {
    this.state = CircuitState.HALF_OPEN;
    this.lastStateChange = new Date();
    this.successCount = 0; // Reset to count successes in half-open state
  }

  /**
   * Remove failures outside monitoring window
   */
  private cleanupOldFailures(): void {
    const cutoff = Date.now() - this.config.monitoringPeriod;
    this.failures = this.failures.filter(failure => failure.getTime() > cutoff);
  }

  /**
   * Get current circuit breaker statistics
   */
  getStats(): CircuitBreakerStats {
    return {
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      lastFailureTime: this.lastFailureTime,
      lastSuccessTime: this.lastSuccessTime,
      lastStateChange: this.lastStateChange,
      requestCount: this.requestCount,
      rejectedCount: this.rejectedCount
    };
  }

  /**
   * Reset circuit breaker to initial state
   */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = null;
    this.lastSuccessTime = null;
    this.lastStateChange = new Date();
    this.requestCount = 0;
    this.rejectedCount = 0;
    this.failures = [];
  }

  /**
   * Force circuit to open state (for testing or manual intervention)
   */
  forceOpen(): void {
    this.openCircuit();
  }

  /**
   * Force circuit to closed state (for testing or manual intervention)
   */
  forceClose(): void {
    this.closeCircuit();
  }

  /**
   * Validate circuit breaker configuration
   */
  private validateConfig(): void {
    if (this.config.failureThreshold <= 0) {
      throw new Error('failureThreshold must be greater than 0');
    }
    if (this.config.successThreshold <= 0) {
      throw new Error('successThreshold must be greater than 0');
    }
    if (this.config.timeout <= 0) {
      throw new Error('timeout must be greater than 0');
    }
    if (this.config.monitoringPeriod <= 0) {
      throw new Error('monitoringPeriod must be greater than 0');
    }
    if (!this.config.name || this.config.name.trim() === '') {
      throw new Error('name is required');
    }
  }
}

/**
 * Circuit Breaker Manager for managing multiple circuit breakers
 */
export class CircuitBreakerManager {
  private breakers: Map<string, CircuitBreaker> = new Map();

  /**
   * Get or create a circuit breaker
   */
  getBreaker(name: string, config?: CircuitBreakerConfig): CircuitBreaker {
    if (!this.breakers.has(name)) {
      if (!config) {
        throw new Error(`Circuit breaker "${name}" not found and no config provided`);
      }
      this.breakers.set(name, new CircuitBreaker({ ...config, name }));
    }
    return this.breakers.get(name)!;
  }

  /**
   * Execute operation with named circuit breaker
   */
  async execute<T>(
    breakerName: string, 
    operation: () => Promise<T>,
    config?: CircuitBreakerConfig
  ): Promise<T> {
    const breaker = this.getBreaker(breakerName, config);
    return breaker.execute(operation);
  }

  /**
   * Get stats for all circuit breakers
   */
  getAllStats(): Record<string, CircuitBreakerStats> {
    const stats: Record<string, CircuitBreakerStats> = {};
    for (const [name, breaker] of this.breakers) {
      stats[name] = breaker.getStats();
    }
    return stats;
  }

  /**
   * Reset all circuit breakers
   */
  resetAll(): void {
    for (const breaker of this.breakers.values()) {
      breaker.reset();
    }
  }

  /**
   * Remove a circuit breaker
   */
  removeBreaker(name: string): boolean {
    return this.breakers.delete(name);
  }

  /**
   * Get all circuit breaker names
   */
  getBreakerNames(): string[] {
    return Array.from(this.breakers.keys());
  }
}

/**
 * Predefined circuit breaker configurations for common scenarios
 */
export const CircuitBreakerConfigs = {
  // Fast-failing services (e.g., price feeds)
  FAST_FAIL: {
    failureThreshold: 3,
    successThreshold: 2,
    timeout: 10000,        // 10 seconds
    monitoringPeriod: 60000, // 1 minute
    name: 'fast-fail'
  } as CircuitBreakerConfig,

  // Exchange APIs (more tolerant)
  EXCHANGE_API: {
    failureThreshold: 5,
    successThreshold: 3,
    timeout: 30000,         // 30 seconds
    monitoringPeriod: 300000, // 5 minutes
    name: 'exchange-api'
  } as CircuitBreakerConfig,

  // Database connections
  DATABASE: {
    failureThreshold: 3,
    successThreshold: 2,
    timeout: 5000,          // 5 seconds
    monitoringPeriod: 120000, // 2 minutes
    name: 'database'
  } as CircuitBreakerConfig,

  // External services (conservative)
  EXTERNAL_SERVICE: {
    failureThreshold: 2,
    successThreshold: 1,
    timeout: 60000,         // 1 minute
    monitoringPeriod: 600000, // 10 minutes
    name: 'external-service'
  } as CircuitBreakerConfig
};

// Global circuit breaker manager instance
export const circuitBreakerManager = new CircuitBreakerManager();