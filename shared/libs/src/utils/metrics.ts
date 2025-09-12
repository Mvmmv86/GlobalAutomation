import { EventEmitter } from 'events';

export interface MetricValue {
  timestamp: Date;
  value: number;
  labels?: Record<string, string>;
}

export interface TimerResult {
  duration: number;
  labels?: Record<string, string>;
}

export interface HistogramBucket {
  le: number; // Less than or equal to
  count: number;
}

export interface MetricSummary {
  count: number;
  sum: number;
  min: number;
  max: number;
  avg: number;
  p50: number;
  p95: number;
  p99: number;
}

export interface BusinessMetrics {
  tradesExecuted: number;
  tradingVolume: number;
  successRate: number;
  avgExecutionTime: number;
  activeAccounts: number;
  webhooksReceived: number;
  errorsCount: number;
  revenueUSDT: number;
}

/**
 * Simple in-memory metrics collection system
 * In production, this would integrate with Prometheus or similar
 */
export class MetricsCollector extends EventEmitter {
  private counters: Map<string, number> = new Map();
  private gauges: Map<string, number> = new Map();
  private histograms: Map<string, MetricValue[]> = new Map();
  private timers: Map<string, Date> = new Map();
  private businessMetrics: BusinessMetrics;
  private startTime: Date = new Date();

  constructor() {
    super();
    this.businessMetrics = {
      tradesExecuted: 0,
      tradingVolume: 0,
      successRate: 0,
      avgExecutionTime: 0,
      activeAccounts: 0,
      webhooksReceived: 0,
      errorsCount: 0,
      revenueUSDT: 0
    };

    // Emit metrics every 30 seconds
    setInterval(() => {
      this.emit('metrics', this.getAllMetrics());
    }, 30000);
  }

  /**
   * Increment a counter
   */
  incrementCounter(name: string, value: number = 1, labels?: Record<string, string>): void {
    const key = this.buildKey(name, labels);
    const current = this.counters.get(key) || 0;
    this.counters.set(key, current + value);
    
    this.emit('counter', { name, value: current + value, labels });
  }

  /**
   * Set a gauge value
   */
  setGauge(name: string, value: number, labels?: Record<string, string>): void {
    const key = this.buildKey(name, labels);
    this.gauges.set(key, value);
    
    this.emit('gauge', { name, value, labels });
  }

  /**
   * Record a histogram value
   */
  recordHistogram(name: string, value: number, labels?: Record<string, string>): void {
    const key = this.buildKey(name, labels);
    const values = this.histograms.get(key) || [];
    
    values.push({
      timestamp: new Date(),
      value,
      labels
    });

    // Keep only last 1000 values to prevent memory issues
    if (values.length > 1000) {
      values.shift();
    }

    this.histograms.set(key, values);
    
    this.emit('histogram', { name, value, labels });
  }

  /**
   * Start a timer
   */
  startTimer(name: string, labels?: Record<string, string>): void {
    const key = this.buildKey(name, labels);
    this.timers.set(key, new Date());
  }

  /**
   * End a timer and record the duration
   */
  endTimer(name: string, labels?: Record<string, string>): TimerResult {
    const key = this.buildKey(name, labels);
    const startTime = this.timers.get(key);
    
    if (!startTime) {
      throw new Error(`Timer '${name}' was not started`);
    }

    const duration = Date.now() - startTime.getTime();
    this.timers.delete(key);
    
    // Record as histogram
    this.recordHistogram(`${name}_duration_ms`, duration, labels);
    
    const result: TimerResult = { duration, labels };
    this.emit('timer', { name, ...result });
    
    return result;
  }

  /**
   * Time a function execution
   */
  async timeFunction<T>(
    name: string,
    fn: () => Promise<T>,
    labels?: Record<string, string>
  ): Promise<T> {
    this.startTimer(name, labels);
    
    try {
      const result = await fn();
      this.endTimer(name, labels);
      return result;
    } catch (error) {
      this.endTimer(name, { ...labels, error: 'true' });
      throw error;
    }
  }

  /**
   * Record business metrics
   */
  recordTrade(volume: number, executionTimeMs: number, success: boolean): void {
    this.businessMetrics.tradesExecuted++;
    this.businessMetrics.tradingVolume += volume;
    
    if (!success) {
      this.businessMetrics.errorsCount++;
    }

    // Update success rate
    this.businessMetrics.successRate = 
      ((this.businessMetrics.tradesExecuted - this.businessMetrics.errorsCount) / 
       this.businessMetrics.tradesExecuted) * 100;

    // Update average execution time (rolling average)
    this.businessMetrics.avgExecutionTime = 
      (this.businessMetrics.avgExecutionTime + executionTimeMs) / 2;

    // Record individual metrics
    this.incrementCounter('trades_total', 1, { success: String(success) });
    this.incrementCounter('trading_volume_usdt', volume);
    this.recordHistogram('trade_execution_time_ms', executionTimeMs);
    this.setGauge('success_rate_percent', this.businessMetrics.successRate);
  }

  /**
   * Record webhook received
   */
  recordWebhook(exchange: string, action: string): void {
    this.businessMetrics.webhooksReceived++;
    this.incrementCounter('webhooks_received_total', 1, { exchange, action });
  }

  /**
   * Record error
   */
  recordError(category: string, service: string): void {
    this.businessMetrics.errorsCount++;
    this.incrementCounter('errors_total', 1, { category, service });
  }

  /**
   * Update active accounts count
   */
  updateActiveAccounts(count: number): void {
    this.businessMetrics.activeAccounts = count;
    this.setGauge('active_accounts', count);
  }

  /**
   * Get counter value
   */
  getCounter(name: string, labels?: Record<string, string>): number {
    const key = this.buildKey(name, labels);
    return this.counters.get(key) || 0;
  }

  /**
   * Get gauge value
   */
  getGauge(name: string, labels?: Record<string, string>): number | undefined {
    const key = this.buildKey(name, labels);
    return this.gauges.get(key);
  }

  /**
   * Get histogram summary
   */
  getHistogramSummary(name: string, labels?: Record<string, string>): MetricSummary | null {
    const key = this.buildKey(name, labels);
    const values = this.histograms.get(key);
    
    if (!values || values.length === 0) {
      return null;
    }

    const nums = values.map(v => v.value).sort((a, b) => a - b);
    const sum = nums.reduce((a, b) => a + b, 0);
    const count = nums.length;

    return {
      count,
      sum,
      min: nums[0],
      max: nums[nums.length - 1],
      avg: sum / count,
      p50: this.percentile(nums, 0.5),
      p95: this.percentile(nums, 0.95),
      p99: this.percentile(nums, 0.99)
    };
  }

  /**
   * Get business metrics
   */
  getBusinessMetrics(): BusinessMetrics {
    return { ...this.businessMetrics };
  }

  /**
   * Get all metrics for export
   */
  getAllMetrics() {
    const uptime = Math.floor((Date.now() - this.startTime.getTime()) / 1000);
    
    return {
      timestamp: new Date(),
      uptime,
      counters: Object.fromEntries(this.counters),
      gauges: Object.fromEntries(this.gauges),
      histograms: this.getHistogramSummaries(),
      business: this.businessMetrics
    };
  }

  /**
   * Reset all metrics
   */
  reset(): void {
    this.counters.clear();
    this.gauges.clear();
    this.histograms.clear();
    this.timers.clear();
    
    this.businessMetrics = {
      tradesExecuted: 0,
      tradingVolume: 0,
      successRate: 0,
      avgExecutionTime: 0,
      activeAccounts: 0,
      webhooksReceived: 0,
      errorsCount: 0,
      revenueUSDT: 0
    };
    
    this.startTime = new Date();
    
    this.emit('reset');
  }

  /**
   * Export metrics in Prometheus format
   */
  exportPrometheus(): string {
    const lines: string[] = [];
    
    // Export counters
    for (const [key, value] of this.counters) {
      const { name, labels } = this.parseKey(key);
      const labelStr = labels ? this.formatPrometheusLabels(labels) : '';
      lines.push(`${name}${labelStr} ${value}`);
    }
    
    // Export gauges
    for (const [key, value] of this.gauges) {
      const { name, labels } = this.parseKey(key);
      const labelStr = labels ? this.formatPrometheusLabels(labels) : '';
      lines.push(`${name}${labelStr} ${value}`);
    }
    
    // Export histogram summaries
    for (const [key, values] of this.histograms) {
      const { name, labels } = this.parseKey(key);
      const summary = this.getHistogramSummary(name, labels);
      
      if (summary) {
        const labelStr = labels ? this.formatPrometheusLabels(labels) : '';
        lines.push(`${name}_count${labelStr} ${summary.count}`);
        lines.push(`${name}_sum${labelStr} ${summary.sum}`);
        lines.push(`${name}_avg${labelStr} ${summary.avg}`);
      }
    }
    
    return lines.join('\n');
  }

  /**
   * Build metric key with labels
   */
  private buildKey(name: string, labels?: Record<string, string>): string {
    if (!labels || Object.keys(labels).length === 0) {
      return name;
    }
    
    const labelPairs = Object.entries(labels)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, value]) => `${key}=${value}`);
    
    return `${name}{${labelPairs.join(',')}}`;
  }

  /**
   * Parse metric key back to name and labels
   */
  private parseKey(key: string): { name: string; labels?: Record<string, string> } {
    const match = key.match(/^([^{]+)(?:\{([^}]+)\})?$/);
    
    if (!match) {
      return { name: key };
    }
    
    const name = match[1];
    const labelStr = match[2];
    
    if (!labelStr) {
      return { name };
    }
    
    const labels: Record<string, string> = {};
    labelStr.split(',').forEach(pair => {
      const [key, value] = pair.split('=');
      labels[key] = value;
    });
    
    return { name, labels };
  }

  /**
   * Calculate percentile
   */
  private percentile(sortedArray: number[], p: number): number {
    if (sortedArray.length === 0) return 0;
    
    const index = Math.ceil(sortedArray.length * p) - 1;
    return sortedArray[Math.max(0, Math.min(index, sortedArray.length - 1))];
  }

  /**
   * Get all histogram summaries
   */
  private getHistogramSummaries(): Record<string, MetricSummary | null> {
    const summaries: Record<string, MetricSummary | null> = {};
    
    for (const key of this.histograms.keys()) {
      const { name, labels } = this.parseKey(key);
      summaries[key] = this.getHistogramSummary(name, labels);
    }
    
    return summaries;
  }

  /**
   * Format labels for Prometheus export
   */
  private formatPrometheusLabels(labels: Record<string, string>): string {
    const pairs = Object.entries(labels)
      .map(([key, value]) => `${key}="${value}"`)
      .join(',');
    
    return `{${pairs}}`;
  }
}

/**
 * Global metrics collector instance
 */
export const metrics = new MetricsCollector();

/**
 * Utility decorators and helpers
 */
export const MetricsUtils = {
  /**
   * Decorator to automatically time method execution
   */
  timed(metricName?: string) {
    return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
      const originalMethod = descriptor.value;
      const name = metricName || `${target.constructor.name}_${propertyKey}`;

      descriptor.value = async function (...args: any[]) {
        return metrics.timeFunction(name, () => originalMethod.apply(this, args));
      };

      return descriptor;
    };
  },

  /**
   * Decorator to automatically count method calls
   */
  counted(metricName?: string, labels?: Record<string, string>) {
    return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
      const originalMethod = descriptor.value;
      const name = metricName || `${target.constructor.name}_${propertyKey}_calls`;

      descriptor.value = function (...args: any[]) {
        metrics.incrementCounter(name, 1, labels);
        return originalMethod.apply(this, args);
      };

      return descriptor;
    };
  },

  /**
   * Create a middleware for measuring HTTP request metrics
   */
  httpMiddleware() {
    return async (request: any, reply: any, next: () => Promise<void>) => {
      const startTime = Date.now();
      const route = request.routerPath || request.url;

      try {
        await next();
        
        const duration = Date.now() - startTime;
        const statusCode = reply.statusCode;
        
        metrics.recordHistogram('http_request_duration_ms', duration, {
          method: request.method,
          route,
          status: String(statusCode)
        });
        
        metrics.incrementCounter('http_requests_total', 1, {
          method: request.method,
          route,
          status: String(statusCode)
        });
        
      } catch (error) {
        const duration = Date.now() - startTime;
        
        metrics.recordHistogram('http_request_duration_ms', duration, {
          method: request.method,
          route,
          status: 'error'
        });
        
        metrics.incrementCounter('http_requests_total', 1, {
          method: request.method,
          route,
          status: 'error'
        });
        
        throw error;
      }
    };
  }
};