'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Activity, TrendingUp, AlertCircle, CheckCircle, BarChart3, Settings, Monitor } from 'lucide-react'

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalJobs: 0,
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  })
  
  const [healthStatus, setHealthStatus] = useState({
    redis: false,
    database: false,
    queue: false,
    exchanges: {},
  })

  useEffect(() => {
    // Fetch initial data
    fetchStats()
    fetchHealth()
    
    // Set up polling
    const interval = setInterval(() => {
      fetchStats()
      fetchHealth()
    }, 30000)
    
    return () => clearInterval(interval)
  }, [])

  const fetchStats = async () => {
    try {
      // Mock data for now - replace with actual API call
      setStats({
        totalJobs: 1247,
        pending: 3,
        processing: 2,
        completed: 1235,
        failed: 7,
      })
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const fetchHealth = async () => {
    try {
      // Mock data for now - replace with actual API call
      setHealthStatus({
        redis: true,
        database: true,
        queue: true,
        exchanges: {
          binance_testnet: true,
          bybit_testnet: false,
        },
      })
    } catch (error) {
      console.error('Failed to fetch health:', error)
    }
  }

  const getStatusColor = (status: boolean) => {
    return status ? 'text-green-500' : 'text-red-500'
  }

  const getStatusIcon = (status: boolean) => {
    return status ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">TradingView Gateway Dashboard</h1>
          <p className="text-gray-600 mt-2">Production-grade webhook to exchange gateway</p>
        </div>

        {/* Quick Navigation */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Link href="/monitoring">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer border-blue-200 hover:border-blue-300">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-lg font-medium text-blue-700">System Monitoring</CardTitle>
                <Monitor className="h-6 w-6 text-blue-500" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">Real-time metrics and health status</p>
              </CardContent>
            </Card>
          </Link>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-green-200 hover:border-green-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-lg font-medium text-green-700">Analytics</CardTitle>
              <BarChart3 className="h-6 w-6 text-green-500" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">Trading performance and metrics</p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-gray-200 hover:border-gray-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-lg font-medium text-gray-700">Settings</CardTitle>
              <Settings className="h-6 w-6 text-gray-500" />
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">Configure accounts and preferences</p>
            </CardContent>
          </Card>
        </div>

        {/* Health Status Banner */}
        <div className="mb-8 p-6 bg-white border rounded-lg shadow-sm">
          <h2 className="text-lg font-semibold mb-4">System Health</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center space-x-2">
              <span className={getStatusColor(healthStatus.redis)}>
                {getStatusIcon(healthStatus.redis)}
              </span>
              <span>Redis</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={getStatusColor(healthStatus.database)}>
                {getStatusIcon(healthStatus.database)}
              </span>
              <span>Database</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={getStatusColor(healthStatus.queue)}>
                {getStatusIcon(healthStatus.queue)}
              </span>
              <span>Queue</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={getStatusColor(Object.values(healthStatus.exchanges).some(Boolean))}>
                {getStatusIcon(Object.values(healthStatus.exchanges).some(Boolean))}
              </span>
              <span>Exchanges</span>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalJobs.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Processing</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{stats.processing}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Failed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link href="/monitoring">
                <Button className="w-full justify-start" variant="outline">
                  <Monitor className="w-4 h-4 mr-2" />
                  View System Monitoring
                </Button>
              </Link>
              <Button className="w-full justify-start" variant="outline">
                <Settings className="w-4 h-4 mr-2" />
                Manage Accounts
              </Button>
              <Button className="w-full justify-start" variant="outline">
                <BarChart3 className="w-4 h-4 mr-2" />
                TradingView Templates
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center">
                  <span>BTCUSDT Buy Order</span>
                  <Badge variant="secondary">Completed</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>ETHUSDT Sell Order</span>
                  <Badge variant="secondary">Completed</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>ADAUSDT Buy Order</span>
                  <Badge variant="destructive">Failed</Badge>
                </div>
                <div className="text-center mt-4">
                  <Link href="/monitoring">
                    <Button variant="outline" size="sm">
                      View All Activity
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}