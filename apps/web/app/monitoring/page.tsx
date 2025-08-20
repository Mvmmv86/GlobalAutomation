'use client';

import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  BarChart3, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  DollarSign,
  Users,
  Zap,
  RefreshCw
} from 'lucide-react';
import HealthStatus from '../components/HealthStatus';

interface BusinessMetrics {
  tradesExecuted: number;
  tradingVolume: number;
  successRate: number;
  avgExecutionTime: number;
  activeAccounts: number;
  webhooksReceived: number;
  errorsCount: number;
  revenueUSDT: number;
  totalRevenue: number;
  avgVolumePerTrade: number;
  errorRate: number;
  webhooksPerMinute: number;
  activeAccountsPercentage: number;
}

interface MetricsData {
  timestamp: string;
  uptime: number;
  business: BusinessMetrics;
  service: string;
  environment: string;
}

export default function MonitoringPage() {
  const [metricsData, setMetricsData] = useState<MetricsData | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      setError(null);
      
      // Try to fetch from API, fallback to mock data
      try {
        const response = await fetch('/api/metrics');
        if (response.ok) {
          const data: MetricsData = await response.json();
          setMetricsData(data);
          setLoading(false);
          return;
        }
      } catch (apiError) {
        // API not available, use mock data
        console.log('API not available, using mock data');
      }
      
      // Mock data when API is not available
      const mockMetrics: MetricsData = {
        timestamp: new Date().toISOString(),
        uptime: 7234, // 2 hours
        business: {
          tradesExecuted: 1847,
          tradingVolume: 285670.45,
          successRate: 96.8,
          avgExecutionTime: 245,
          activeAccounts: 12,
          webhooksReceived: 2156,
          errorsCount: 59,
          revenueUSDT: 285670.45,
          totalRevenue: 285670.45,
          avgVolumePerTrade: 154.7,
          errorRate: 3.2,
          webhooksPerMinute: 17.8,
          activeAccountsPercentage: 85.7
        },
        service: 'api-mock',
        environment: 'development'
      };
      
      setMetricsData(mockMetrics);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  };

  const toggleLiveUpdates = () => {
    setIsLive(!isLive);
  };

  useEffect(() => {
    fetchMetrics();
    
    let interval: NodeJS.Timeout;
    
    if (isLive) {
      // Update every 5 seconds when live
      interval = setInterval(fetchMetrics, 5000);
    } else {
      // Update every 30 seconds when not live
      interval = setInterval(fetchMetrics, 30000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLive]);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(2) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(2) + 'K';
    }
    return num.toFixed(2);
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
      return `${days}d ${hours}h`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-2 text-lg text-gray-600">Loading monitoring data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            <h2 className="ml-2 text-lg font-semibold text-red-800">Monitoring Error</h2>
          </div>
          <p className="mt-2 text-red-700">{error}</p>
          <button
            onClick={fetchMetrics}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Monitoring</h1>
          <p className="text-gray-600">Real-time metrics and health status</p>
        </div>
        
        <div className="flex items-center space-x-4">
          <button
            onClick={toggleLiveUpdates}
            className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${
              isLive 
                ? 'bg-green-100 text-green-800 border border-green-200' 
                : 'bg-gray-100 text-gray-800 border border-gray-200'
            }`}
          >
            <Activity className={`w-4 h-4 mr-2 ${isLive ? 'animate-pulse' : ''}`} />
            {isLive ? 'Live Updates' : 'Enable Live'}
          </button>
          
          <button
            onClick={fetchMetrics}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* System Overview */}
      {metricsData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center">
              <Clock className="w-8 h-8 text-blue-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Uptime</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatUptime(metricsData.uptime)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center">
              <BarChart3 className="w-8 h-8 text-green-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Trades</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatNumber(metricsData.business.tradesExecuted)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center">
              <TrendingUp className="w-8 h-8 text-purple-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900">
                  {metricsData.business.successRate.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center">
              <DollarSign className="w-8 h-8 text-emerald-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Trading Volume</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(metricsData.business.tradingVolume)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Business Metrics Grid */}
      {metricsData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Avg Execution Time</span>
                <span className="font-medium">{metricsData.business.avgExecutionTime.toFixed(0)}ms</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Webhooks/min</span>
                <span className="font-medium">{metricsData.business.webhooksPerMinute.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Error Rate</span>
                <span className={`font-medium ${metricsData.business.errorRate > 5 ? 'text-red-600' : 'text-green-600'}`}>
                  {metricsData.business.errorRate.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Activity</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Webhooks Received</span>
                <span className="font-medium">{formatNumber(metricsData.business.webhooksReceived)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total Errors</span>
                <span className="font-medium text-red-600">{metricsData.business.errorsCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Avg Volume/Trade</span>
                <span className="font-medium">{formatCurrency(metricsData.business.avgVolumePerTrade)}</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Accounts</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Active Accounts</span>
                <span className="font-medium">{metricsData.business.activeAccounts}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Active %</span>
                <span className="font-medium">{metricsData.business.activeAccountsPercentage.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Revenue</span>
                <span className="font-medium text-green-600">{formatCurrency(metricsData.business.totalRevenue)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Health Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Health Status</h2>
        <HealthStatus />
      </div>

      {/* System Info */}
      {metricsData && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">System Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-600">Service:</span>
              <p className="text-gray-900">{metricsData.service}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Environment:</span>
              <p className="text-gray-900">{metricsData.environment}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Last Updated:</span>
              <p className="text-gray-900">{new Date(metricsData.timestamp).toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}