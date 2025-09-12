import { PrismaClient } from '@prisma/client';
import { Redis } from 'ioredis';
import axios from 'axios';
import { getNotificationService } from './notifications';

export interface HealthCheck {
  name: string;
  description: string;
  check: () => Promise<HealthCheckResult>;
  timeout: number; // milliseconds
  critical: boolean; // If true, failure makes entire service unhealthy
}

export interface HealthCheckResult {
  status: 'healthy' | 'degraded' | 'unhealthy';
  responseTime: number; // milliseconds
  message: string;
  details?: Record<string, any>;
  timestamp: Date;
}

export interface ServiceHealth {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: Record<string, HealthCheckResult>;
  uptime: number; // seconds
  version: string;
  environment: string;
  timestamp: Date;
}

export interface HealthCheckConfig {
  intervalMs: number; // How often to run checks
  timeoutMs: number; // Default timeout for checks
  retryCount: number; // Number of retries for failed checks
  notifyOnStatusChange: boolean; // Send notifications when status changes
  service: string; // Service name
  version: string; // Service version
}

/**
 * Health check system for monitoring service dependencies
 */
export class HealthCheckService {
  private checks: Map<string, HealthCheck> = new Map();
  private lastResults: Map<string, HealthCheckResult> = new Map();
  private config: HealthCheckConfig;
  private intervalId: NodeJS.Timeout | null = null;
  private startTime: Date = new Date();
  private lastStatus: ServiceHealth['status'] = 'healthy';

  constructor(config: HealthCheckConfig) {
    this.config = config;
  }

  /**
   * Register a health check
   */
  register(check: HealthCheck): void {
    this.checks.set(check.name, check);
  }

  /**
   * Start periodic health checks
   */
  start(): void {
    if (this.intervalId) {
      this.stop();
    }

    // Run checks immediately
    this.runAllChecks();

    // Schedule periodic checks
    this.intervalId = setInterval(() => {
      this.runAllChecks();
    }, this.config.intervalMs);

    console.log(`Health checks started for ${this.config.service} (interval: ${this.config.intervalMs}ms)`);
  }

  /**
   * Stop periodic health checks
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      console.log(`Health checks stopped for ${this.config.service}`);
    }
  }

  /**
   * Run all registered health checks
   */
  async runAllChecks(): Promise<ServiceHealth> {
    const results: Record<string, HealthCheckResult> = {};
    
    for (const [name, check] of this.checks) {
      try {
        const result = await this.runSingleCheck(check);
        results[name] = result;
        this.lastResults.set(name, result);
      } catch (error) {
        const result: HealthCheckResult = {
          status: 'unhealthy',
          responseTime: this.config.timeoutMs,
          message: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date()
        };
        results[name] = result;
        this.lastResults.set(name, result);
      }
    }

    const serviceHealth = this.calculateServiceHealth(results);
    
    // Send notification if status changed
    if (this.config.notifyOnStatusChange && serviceHealth.status !== this.lastStatus) {
      this.notifyStatusChange(this.lastStatus, serviceHealth.status, serviceHealth);
      this.lastStatus = serviceHealth.status;
    }

    return serviceHealth;
  }

  /**
   * Run a single health check with timeout and retry logic
   */
  async runSingleCheck(check: HealthCheck): Promise<HealthCheckResult> {
    const startTime = Date.now();
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.config.retryCount; attempt++) {
      try {
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('Health check timeout')), check.timeout);
        });

        const result = await Promise.race([
          check.check(),
          timeoutPromise
        ]);

        result.responseTime = Date.now() - startTime;
        result.timestamp = new Date();
        
        return result;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error');
        
        // Don't retry on timeout
        if (lastError.message.includes('timeout')) {
          break;
        }

        // Wait before retry (except on last attempt)
        if (attempt < this.config.retryCount) {
          await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
        }
      }
    }

    // All attempts failed
    return {
      status: 'unhealthy',
      responseTime: Date.now() - startTime,
      message: `Check failed after ${this.config.retryCount + 1} attempts: ${lastError?.message}`,
      timestamp: new Date()
    };
  }

  /**
   * Get current service health status
   */
  async getHealth(): Promise<ServiceHealth> {
    // If no checks registered, assume healthy
    if (this.checks.size === 0) {
      return {
        service: this.config.service,
        status: 'healthy',
        checks: {},
        uptime: this.getUptimeSeconds(),
        version: this.config.version,
        environment: process.env.NODE_ENV || 'development',
        timestamp: new Date()
      };
    }

    // Use last results if available, otherwise run checks
    if (this.lastResults.size > 0) {
      const results: Record<string, HealthCheckResult> = {};
      for (const [name, result] of this.lastResults) {
        results[name] = result;
      }
      return this.calculateServiceHealth(results);
    }

    return this.runAllChecks();
  }

  /**
   * Get health for specific check
   */
  getCheckHealth(checkName: string): HealthCheckResult | null {
    return this.lastResults.get(checkName) || null;
  }

  /**
   * Calculate overall service health from check results
   */
  private calculateServiceHealth(results: Record<string, HealthCheckResult>): ServiceHealth {
    let status: ServiceHealth['status'] = 'healthy';
    
    for (const [checkName, result] of Object.entries(results)) {
      const check = this.checks.get(checkName);
      
      if (result.status === 'unhealthy') {
        if (check?.critical) {
          status = 'unhealthy';
          break; // Critical check failed, service is unhealthy
        } else if (status === 'healthy') {
          status = 'degraded'; // Non-critical check failed
        }
      } else if (result.status === 'degraded' && status === 'healthy') {
        status = 'degraded';
      }
    }

    return {
      service: this.config.service,
      status,
      checks: results,
      uptime: this.getUptimeSeconds(),
      version: this.config.version,
      environment: process.env.NODE_ENV || 'development',
      timestamp: new Date()
    };
  }

  /**
   * Get service uptime in seconds
   */
  private getUptimeSeconds(): number {
    return Math.floor((Date.now() - this.startTime.getTime()) / 1000);
  }

  /**
   * Send notification when service status changes
   */
  private async notifyStatusChange(
    oldStatus: ServiceHealth['status'],
    newStatus: ServiceHealth['status'],
    health: ServiceHealth
  ): Promise<void> {
    try {
      const notification = getNotificationService();
      const alert = notification.createHealthAlert(
        'service-status',
        newStatus,
        {
          oldStatus,
          newStatus,
          checks: Object.keys(health.checks).length,
          failedChecks: Object.values(health.checks).filter(c => c.status !== 'healthy').length
        },
        this.config.service
      );
      
      await notification.sendAlert(alert);
    } catch (error) {
      console.error('Failed to send health status notification:', error);
    }
  }
}

/**
 * Predefined health checks for common dependencies
 */
export class CommonHealthChecks {
  /**
   * Database health check using Prisma
   */
  static database(prisma: PrismaClient): HealthCheck {
    return {
      name: 'database',
      description: 'PostgreSQL database connectivity',
      timeout: 5000,
      critical: true,
      check: async (): Promise<HealthCheckResult> => {
        const startTime = Date.now();
        
        try {
          // Simple query to test connectivity
          await prisma.$queryRaw`SELECT 1`;
          
          return {
            status: 'healthy',
            responseTime: Date.now() - startTime,
            message: 'Database connection successful',
            timestamp: new Date()
          };
        } catch (error) {
          return {
            status: 'unhealthy',
            responseTime: Date.now() - startTime,
            message: `Database connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
            timestamp: new Date()
          };
        }
      }
    };
  }

  /**
   * Redis health check
   */
  static redis(redis: Redis): HealthCheck {
    return {
      name: 'redis',
      description: 'Redis cache connectivity',
      timeout: 3000,
      critical: false,
      check: async (): Promise<HealthCheckResult> => {
        const startTime = Date.now();
        
        try {
          const result = await redis.ping();
          
          if (result === 'PONG') {
            return {
              status: 'healthy',
              responseTime: Date.now() - startTime,
              message: 'Redis connection successful',
              timestamp: new Date()
            };
          } else {
            return {
              status: 'degraded',
              responseTime: Date.now() - startTime,
              message: `Redis ping returned unexpected result: ${result}`,
              timestamp: new Date()
            };
          }
        } catch (error) {
          return {
            status: 'unhealthy',
            responseTime: Date.now() - startTime,
            message: `Redis connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
            timestamp: new Date()
          };
        }
      }
    };
  }

  /**
   * External API health check
   */
  static externalApi(name: string, url: string, expectedStatus: number = 200): HealthCheck {
    return {
      name: `external-api-${name}`,
      description: `External API: ${name}`,
      timeout: 10000,
      critical: false,
      check: async (): Promise<HealthCheckResult> => {
        const startTime = Date.now();
        
        try {
          const response = await axios.get(url, {
            timeout: 8000,
            validateStatus: (status) => status === expectedStatus
          });
          
          return {
            status: 'healthy',
            responseTime: Date.now() - startTime,
            message: `API ${name} responded with status ${response.status}`,
            details: {
              status: response.status,
              url
            },
            timestamp: new Date()
          };
        } catch (error) {
          if (axios.isAxiosError(error)) {
            return {
              status: 'unhealthy',
              responseTime: Date.now() - startTime,
              message: `API ${name} failed: ${error.response?.status || 'No response'} - ${error.message}`,
              details: {
                status: error.response?.status,
                url,
                error: error.message
              },
              timestamp: new Date()
            };
          }
          
          return {
            status: 'unhealthy',
            responseTime: Date.now() - startTime,
            message: `API ${name} failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
            timestamp: new Date()
          };
        }
      }
    };
  }

  /**
   * Exchange API health check
   */
  static exchangeApi(exchangeName: string, testEndpoint: string): HealthCheck {
    return {
      name: `exchange-${exchangeName}`,
      description: `${exchangeName} exchange API`,
      timeout: 15000,
      critical: true, // Exchange connectivity is critical for trading
      check: async (): Promise<HealthCheckResult> => {
        const startTime = Date.now();
        
        try {
          const response = await axios.get(testEndpoint, {
            timeout: 12000
          });
          
          // Check if response looks valid (e.g., has expected structure)
          const responseTime = Date.now() - startTime;
          
          if (response.status === 200 && response.data) {
            return {
              status: 'healthy',
              responseTime,
              message: `${exchangeName} API is accessible`,
              details: {
                status: response.status,
                endpoint: testEndpoint,
                dataSize: JSON.stringify(response.data).length
              },
              timestamp: new Date()
            };
          } else {
            return {
              status: 'degraded',
              responseTime,
              message: `${exchangeName} API returned unexpected response`,
              details: {
                status: response.status,
                endpoint: testEndpoint
              },
              timestamp: new Date()
            };
          }
        } catch (error) {
          return {
            status: 'unhealthy',
            responseTime: Date.now() - startTime,
            message: `${exchangeName} API check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
            details: {
              endpoint: testEndpoint,
              error: error instanceof Error ? error.message : 'Unknown error'
            },
            timestamp: new Date()
          };
        }
      }
    };
  }

  /**
   * Memory usage health check
   */
  static memoryUsage(maxUsagePercent: number = 80): HealthCheck {
    return {
      name: 'memory-usage',
      description: 'System memory usage',
      timeout: 1000,
      critical: false,
      check: async (): Promise<HealthCheckResult> => {
        const memUsage = process.memoryUsage();
        const totalMem = memUsage.heapTotal;
        const usedMem = memUsage.heapUsed;
        const usagePercent = (usedMem / totalMem) * 100;
        
        let status: HealthCheckResult['status'] = 'healthy';
        let message = `Memory usage: ${usagePercent.toFixed(1)}%`;
        
        if (usagePercent > maxUsagePercent) {
          status = 'degraded';
          message += ` (exceeds ${maxUsagePercent}% threshold)`;
        }
        
        if (usagePercent > 95) {
          status = 'unhealthy';
          message += ' (critical memory usage)';
        }
        
        return {
          status,
          responseTime: 1,
          message,
          details: {
            heapUsed: Math.round(usedMem / 1024 / 1024), // MB
            heapTotal: Math.round(totalMem / 1024 / 1024), // MB
            usagePercent: Math.round(usagePercent * 100) / 100,
            external: Math.round(memUsage.external / 1024 / 1024), // MB
            rss: Math.round(memUsage.rss / 1024 / 1024) // MB
          },
          timestamp: new Date()
        };
      }
    };
  }

  /**
   * Disk space health check
   */
  static diskSpace(path: string = '/', maxUsagePercent: number = 80): HealthCheck {
    return {
      name: 'disk-space',
      description: `Disk space usage for ${path}`,
      timeout: 2000,
      critical: false,
      check: async (): Promise<HealthCheckResult> => {
        try {
          const fs = await import('fs/promises');
          const stats = await fs.stat(path);
          
          // This is a simplified check - in production you'd use statvfs or similar
          return {
            status: 'healthy',
            responseTime: 1,
            message: 'Disk space check completed (simplified)',
            details: {
              path,
              note: 'Full disk space checking requires additional system calls'
            },
            timestamp: new Date()
          };
        } catch (error) {
          return {
            status: 'unhealthy',
            responseTime: 1,
            message: `Disk space check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
            timestamp: new Date()
          };
        }
      }
    };
  }
}