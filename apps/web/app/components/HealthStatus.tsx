'use client';

import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Clock, RefreshCw } from 'lucide-react';

interface HealthCheckResult {
  status: 'healthy' | 'degraded' | 'unhealthy';
  responseTime: number;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

interface ServiceHealth {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: Record<string, HealthCheckResult>;
  uptime: number;
  version: string;
  environment: string;
  timestamp: string;
}

export default function HealthStatus() {
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchHealth = async () => {
    try {
      setError(null);
      
      // Try to fetch from API, fallback to mock data
      try {
        const response = await fetch('/api/health');
        if (response.ok) {
          const data: ServiceHealth = await response.json();
          setHealth(data);
          setLastUpdated(new Date());
          setLoading(false);
          return;
        }
      } catch (apiError) {
        // API not available, use mock data
        console.log('API not available, using mock data');
      }
      
      // Mock data when API is not available
      const mockHealth: ServiceHealth = {
        service: 'api-mock',
        status: 'healthy',
        checks: {
          database: {
            status: 'healthy',
            responseTime: 25,
            message: 'Database connection successful (mock)',
            timestamp: new Date().toISOString(),
            details: {
              host: 'localhost:5432',
              database: 'tradingview_gateway'
            }
          },
          redis: {
            status: 'healthy',
            responseTime: 12,
            message: 'Redis connection successful (mock)',
            timestamp: new Date().toISOString(),
            details: {
              host: 'localhost:6379',
              memory: '2.1MB'
            }
          },
          'exchange-binance': {
            status: 'healthy',
            responseTime: 156,
            message: 'Binance API is accessible (mock)',
            timestamp: new Date().toISOString(),
            details: {
              endpoint: 'https://api.binance.com/api/v3/ping',
              status: 200
            }
          },
          'exchange-bybit': {
            status: 'degraded',
            responseTime: 890,
            message: 'Bybit API slow response (mock)',
            timestamp: new Date().toISOString(),
            details: {
              endpoint: 'https://api.bybit.com/v5/market/time',
              status: 200
            }
          },
          'memory-usage': {
            status: 'healthy',
            responseTime: 1,
            message: 'Memory usage: 45.2%',
            timestamp: new Date().toISOString(),
            details: {
              heapUsed: 67,
              heapTotal: 128,
              usagePercent: 45.2,
              rss: 95
            }
          }
        },
        uptime: 7234,
        version: '1.0.0',
        environment: 'development',
        timestamp: new Date().toISOString()
      };
      
      setHealth(mockHealth);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'unhealthy':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'unhealthy':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600">Loading health status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <AlertCircle className="w-6 h-6 text-red-500" />
          <h3 className="ml-2 text-lg font-semibold text-red-800">Health Check Error</h3>
        </div>
        <p className="mt-2 text-red-700">{error}</p>
        <button
          onClick={fetchHealth}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <p className="text-gray-600">No health data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <div className={`border rounded-lg p-6 ${getStatusColor(health.status)}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {getStatusIcon(health.status)}
            <h2 className="ml-2 text-xl font-semibold">
              Service Status: {health.status.charAt(0).toUpperCase() + health.status.slice(1)}
              {health.service === 'api-mock' && (
                <span className="ml-2 text-sm bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full">
                  Demo Data
                </span>
              )}
            </h2>
          </div>
          <button
            onClick={fetchHealth}
            className="p-2 hover:bg-white/20 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="font-medium">Service:</span>
            <p>{health.service}</p>
          </div>
          <div>
            <span className="font-medium">Version:</span>
            <p>{health.version}</p>
          </div>
          <div>
            <span className="font-medium">Environment:</span>
            <p>{health.environment}</p>
          </div>
          <div>
            <span className="font-medium">Uptime:</span>
            <p>{formatUptime(health.uptime)}</p>
          </div>
        </div>
      </div>

      {/* Individual Checks */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Health Checks</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(health.checks).map(([checkName, result]) => (
            <div
              key={checkName}
              className={`border rounded-lg p-4 ${getStatusColor(result.status)}`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  {getStatusIcon(result.status)}
                  <h4 className="ml-2 font-medium capitalize">
                    {checkName.replace(/-/g, ' ')}
                  </h4>
                </div>
                <span className="text-xs">
                  {result.responseTime}ms
                </span>
              </div>
              
              <p className="text-sm mb-2">{result.message}</p>
              
              {result.details && (
                <div className="text-xs space-y-1">
                  {Object.entries(result.details).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="font-medium">{key}:</span>
                      <span className="truncate ml-2">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="text-xs mt-2 opacity-75">
                Last checked: {new Date(result.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Last Updated */}
      {lastUpdated && (
        <div className="text-sm text-gray-500 text-center">
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}