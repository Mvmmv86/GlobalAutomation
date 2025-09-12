import React, { useState } from 'react'
import { BarChart3, Building2, FileText, TrendingUp, Webhook, DollarSign, Wifi } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { PriceDisplay } from '../molecules/PriceDisplay'
import { OrderCard } from '../molecules/OrderCard'
import { PositionsTable } from '../organisms/PositionsTable'
import { NotificationCenter, useNotifications } from '../organisms/NotificationCenter'
import { 
  useExchangeAccounts, 
  useWebhooks, 
  useRecentOrders, 
  useActivePositions,
  usePositionMetrics,
  useOrderStats,
  useCreateTestOrder
} from '@/hooks/useApiData'

const DashboardPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [apiResponse, setApiResponse] = useState<string>('')

  // API Data hooks
  const { data: exchangeAccounts, isLoading: loadingAccounts, error: accountsError } = useExchangeAccounts()
  const { data: webhooks, isLoading: loadingWebhooks, error: webhooksError } = useWebhooks()
  const { data: recentOrdersApi, isLoading: loadingOrders, error: ordersError } = useRecentOrders()
  const { data: activePositions, isLoading: loadingPositions, error: positionsError } = useActivePositions()
  const { data: metrics, isLoading: loadingMetrics, error: metricsError } = usePositionMetrics()
  const { data: orderStats, isLoading: loadingStats, error: statsError } = useOrderStats()
  const createTestOrderMutation = useCreateTestOrder()

  const testApiConnection = async () => {
    setApiStatus('testing')
    try {
      const response = await fetch('/api/v1/../')  // Usar proxy do Vite
      const data = await response.json()
      setApiResponse(JSON.stringify(data, null, 2))
      setApiStatus('success')
    } catch (error) {
      setApiResponse(error instanceof Error ? error.message : 'Erro desconhecido')
      setApiStatus('error')
    }
  }

  // Use real data when available, fallback to mock data
  const hasApiErrors = accountsError || webhooksError || ordersError || positionsError || metricsError || statsError
  const isLoadingData = loadingAccounts || loadingWebhooks || loadingOrders || loadingPositions || loadingMetrics || loadingStats

  // Function to create test order
  const handleCreateTestOrder = async () => {
    try {
      await createTestOrderMutation.mutateAsync()
      setApiStatus('success')
      setApiResponse('Test order created successfully!')
    } catch (error) {
      setApiStatus('error')
      setApiResponse(error instanceof Error ? error.message : 'Failed to create test order')
    }
  }

  // Computed stats from real data or fallback to mock
  const stats = {
    totalOrders: orderStats?.total_orders || recentOrdersApi?.length || 156,
    activePositions: activePositions?.length || 8,
    totalPnL: metrics?.totalPnl || 2547.83,
    activeWebhooks: webhooks?.filter(w => w.status === 'active').length || 3,
    exchangeAccounts: exchangeAccounts?.length || 2,
    todayOrders: recentOrdersApi?.filter(order => {
      const today = new Date().toDateString()
      const orderDate = new Date(order.createdAt).toDateString()
      return today === orderDate
    }).length || 12,
    successRate: orderStats?.success_rate || 84.6,
    filledOrders: orderStats?.filled_orders || 11,
    pendingOrders: orderStats?.pending_orders || 2,
  }

  // Use real data or fallback to mock data
  const recentOrdersData = recentOrdersApi || [
    {
      id: '1',
      clientOrderId: 'demo_order_001',
      symbol: 'BTCUSDT',
      side: 'buy' as const,
      type: 'limit' as const,
      status: 'filled' as const,
      quantity: 0.01,
      price: 45000,
      filledQuantity: 0.01,
      averageFillPrice: 45000,
      feesPaid: 0.45,
      feeCurrency: 'USDT',
      source: 'demo',
      exchangeAccountId: 'demo-account',
      createdAt: '2025-01-15T10:30:00Z',
      updatedAt: '2025-01-15T10:30:00Z',
    },
    {
      id: '2', 
      clientOrderId: 'demo_order_002',
      symbol: 'ETHUSDT',
      side: 'sell' as const,
      type: 'market' as const,
      status: 'open' as const,
      quantity: 0.5,
      price: 2800,
      filledQuantity: 0,
      averageFillPrice: null,
      feesPaid: 0,
      feeCurrency: null,
      source: 'demo',
      exchangeAccountId: 'demo-account',
      createdAt: '2025-01-15T09:15:00Z',
      updatedAt: '2025-01-15T09:15:00Z',
    },
  ]

  const activePositionsData = activePositions || [
    {
      id: '1',
      symbol: 'BTCUSDT',
      side: 'long' as const,
      status: 'open' as const,
      size: 0.01,
      entryPrice: 45000,
      markPrice: 46000,
      unrealizedPnl: 10.00,
      realizedPnl: 0,
      initialMargin: 45,
      maintenanceMargin: 22.5,
      leverage: 10,
      liquidationPrice: 40500,
      exchangeAccountId: 'demo-account',
      openedAt: '2025-01-15T08:30:00Z',
      createdAt: '2025-01-15T08:30:00Z',
      updatedAt: '2025-01-15T08:30:00Z',
    },
    {
      id: '2',
      symbol: 'ETHUSDT', 
      side: 'long' as const,
      status: 'open' as const,
      size: 0.1,
      entryPrice: 2800,
      markPrice: 2850,
      unrealizedPnl: 5.00,
      realizedPnl: 0,
      initialMargin: 28,
      maintenanceMargin: 14,
      leverage: 10,
      liquidationPrice: 2520,
      exchangeAccountId: 'demo-account',
      openedAt: '2025-01-15T07:15:00Z',
      createdAt: '2025-01-15T07:15:00Z',
      updatedAt: '2025-01-15T07:15:00Z',
    },
  ]

  const getOrderStatusBadge = (status: string) => {
    switch (status) {
      case 'filled':
        return <Badge variant="success">Preenchida</Badge>
      case 'open':
        return <Badge variant="warning">Aberta</Badge>
      case 'partially_filled':
        return <Badge variant="secondary">Parcial</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const getSideBadge = (side: 'buy' | 'sell' | 'long' | 'short') => {
    const isPositive = side === 'buy' || side === 'long'
    return (
      <Badge variant={isPositive ? 'success' : 'danger'}>
        {side === 'buy' ? 'Compra' : side === 'sell' ? 'Venda' : side === 'long' ? 'Long' : 'Short'}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Visão geral das suas atividades de trading
          </p>
        </div>
        <div className="flex space-x-2">
          <Button 
            onClick={testApiConnection}
            variant={apiStatus === 'success' ? 'success' : apiStatus === 'error' ? 'danger' : 'outline'}
            disabled={apiStatus === 'testing'}
          >
            <Wifi className="w-4 h-4 mr-2" />
            {apiStatus === 'testing' ? 'Testando...' : 'Testar API'}
          </Button>
          <Button 
            onClick={handleCreateTestOrder}
            variant="outline"
            disabled={createTestOrderMutation.isPending}
          >
            {createTestOrderMutation.isPending ? 'Criando...' : 'Criar Ordem Teste'}
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      {isLoadingData && (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner />
        </div>
      )}
      
      {hasApiErrors && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
          <p className="text-yellow-800 dark:text-yellow-200 text-sm">
            ⚠️ API indisponível - usando dados demo
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">
              +${stats.totalPnL.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              Lucro total acumulado
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ordens Hoje</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.todayOrders}</div>
            <p className="text-xs text-muted-foreground">
              +2 desde ontem
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Posições Ativas</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.activePositions}</div>
            <p className="text-xs text-muted-foreground">
              Posições em aberto
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Ordens</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalOrders}</div>
            <p className="text-xs text-muted-foreground">
              Todas as ordens
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Webhooks Ativos</CardTitle>
            <Webhook className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.activeWebhooks}</div>
            <p className="text-xs text-muted-foreground">
              Funcionando normalmente
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Exchange Accounts</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.exchangeAccounts}</div>
            <p className="text-xs text-muted-foreground">
              Contas conectadas
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Taxa de Sucesso</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">{stats.successRate}%</div>
            <p className="text-xs text-muted-foreground">
              {stats.filledOrders} preenchidas, {stats.pendingOrders} pendentes
            </p>
          </CardContent>
        </Card>
      </div>

      {/* API Test Result */}
      {apiStatus !== 'idle' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Wifi className="w-5 h-5 mr-2" />
              Teste de Conectividade API
            </CardTitle>
            <CardDescription>
              Resultado da conexão com o backend
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium">Status:</span>
                <Badge variant={apiStatus === 'success' ? 'success' : apiStatus === 'error' ? 'danger' : 'warning'}>
                  {apiStatus}
                </Badge>
              </div>
              {apiResponse && (
                <div>
                  <span className="text-sm font-medium">Resposta:</span>
                  <pre className="mt-1 p-3 bg-muted rounded-md text-xs overflow-auto">
                    {apiResponse}
                  </pre>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Orders */}
        <Card>
          <CardHeader>
            <CardTitle>Ordens Recentes</CardTitle>
            <CardDescription>
              Suas últimas ordens executadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingOrders ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : ordersError ? (
              <div className="text-center py-8 text-muted-foreground">
                Usando dados demo (API indisponível)
              </div>
            ) : (
              <div className="max-h-64 overflow-y-auto space-y-4">
                {recentOrdersData.map((order) => (
                <div
                  key={order.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div>
                      <p className="font-medium">{order.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(order.createdAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getSideBadge(order.side)}
                    {getOrderStatusBadge(order.status)}
                  </div>
                </div>
              ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Active Positions */}
        <Card>
          <CardHeader>
            <CardTitle>Posições Ativas</CardTitle>
            <CardDescription>
              Suas posições em aberto
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingPositions ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : positionsError ? (
              <div className="text-center py-8 text-muted-foreground">
                Usando dados demo (API indisponível)
              </div>
            ) : (
              <div className="space-y-4">
                {activePositionsData.map((position) => (
                <div
                  key={position.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div>
                      <p className="font-medium">{position.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        Size: {position.size}
                      </p>
                    </div>
                  </div>
                  <div className="text-right space-y-1">
                    {getSideBadge(position.side)}
                    <p className={`text-sm font-medium ${
                      position.unrealizedPnl >= 0 ? 'text-success' : 'text-danger'
                    }`}>
                      {position.unrealizedPnl >= 0 ? '+' : ''}${position.unrealizedPnl}
                    </p>
                  </div>
                </div>
              ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardPage