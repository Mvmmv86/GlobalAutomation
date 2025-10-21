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
  useCreateTestOrder,
  useDashboardMetrics,
  useBalancesSummary,
  // useDashboardCards  // HOOK COM ERRO - DESABILITADO
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
  const { data: balancesSummary, isLoading: loadingBalances, error: balancesError, refetch: refetchBalances } = useBalancesSummary()
  // const { data: dashboardCards, isLoading: loadingCards, error: cardsError } = useDashboardCards()  // DESABILITADO - ENDPOINT COM BUG
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
  const hasApiErrors = accountsError || webhooksError || ordersError || positionsError || metricsError || statsError || balancesError
  const isLoadingData = loadingAccounts || loadingWebhooks || loadingOrders || loadingPositions || loadingMetrics || loadingBalances

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

  // DADOS REAIS DO BANCO - SEM FALLBACKS MOCK
  const positionsData = activePositions?.data || activePositions || []

  // Debug: verificar se balancesSummary está chegando
  console.log('🔍 Balances Summary Data:', balancesSummary)
  console.log('🔍 Loading Balances:', loadingBalances)
  console.log('🔍 Balances Error:', balancesError)
  console.log('🔍 Raw JSON balancesSummary:', JSON.stringify(balancesSummary, null, 2))

  console.log('🔍 DEBUGGING: balancesSummary:', balancesSummary)
  console.log('🔍 DEBUGGING: balancesSummary?.futures:', balancesSummary?.futures)
  console.log('🔍 DEBUGGING: balancesSummary?.spot:', balancesSummary?.spot)

  const stats = {
    // Dados dos cards (banco de dados) - USANDO BALANCES QUE FUNCIONA
    futuresBalance: balancesSummary?.futures?.total_balance_usd || 0,
    futuresUnrealizedPnL: balancesSummary?.futures?.unrealized_pnl || 0,
    futuresPnL: balancesSummary?.futures?.unrealized_pnl || 0,
    spotBalance: balancesSummary?.spot?.total_balance_usd || 0,
    spotAssets: balancesSummary?.spot?.assets?.length || 0,
    spotPnL: balancesSummary?.spot?.unrealized_pnl || 0,
    totalPnL: balancesSummary?.total?.pnl || 0,
    activePositions: activePositions?.length || 0,
    totalOrders: recentOrdersApi?.length || 0,
    todayOrders: recentOrdersApi?.length || 0,

    // Dados das outras APIs (banco de dados)
    activeWebhooks: webhooks?.filter(w => w.status === 'active').length || 0,
    exchangeAccounts: exchangeAccounts?.length || 0,
    successRate: 85, // Mock temporário
    filledOrders: recentOrdersApi?.length || 0,
    pendingOrders: 0,
  }

  console.log('🔍 Stats calculados:', stats)
  console.log('💰 Futures Balance:', stats.futuresBalance)
  console.log('💰 Spot Balance:', stats.spotBalance)
  console.log('💰 Total PnL:', stats.totalPnL)

  // Use only real data from API
  const recentOrdersData = recentOrdersApi || []

  // Use only real data from API
  const activePositionsData = (activePositions?.data || activePositions || []).filter(Boolean)

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
            onClick={() => refetchBalances()}
            variant="primary"
            disabled={loadingBalances}
          >
            <TrendingUp className="w-4 h-4 mr-2" />
            {loadingBalances ? 'Atualizando...' : 'Atualizar Dados'}
          </Button>
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
      

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card Futures */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Saldo Futures</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${stats.futuresBalance.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              P&L não realizado: <span className={stats.futuresUnrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'}>
                ${stats.futuresUnrealizedPnL.toFixed(2)}
              </span>
            </p>
          </CardContent>
        </Card>

        {/* Card Spot */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Saldo Spot</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${stats.spotBalance.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.spotAssets} ativos | P&L hoje: ${stats.spotPnL.toFixed(2)}
            </p>
          </CardContent>
        </Card>

        {/* P&L Total do Dia - CONFORME SOLICITADO */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">P&L Total do Dia</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${stats.totalPnL >= 0 ? 'text-success' : 'text-danger'}`}>
              {stats.totalPnL >= 0 ? '+' : ''}${Math.abs(stats.totalPnL).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              Futures + Spot realizado hoje
            </p>
          </CardContent>
        </Card>

        {/* Posições Ativas */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Posições Ativas</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.activePositions}</div>
            <p className="text-xs text-muted-foreground">
              Posições em aberto
            </p>
          </CardContent>
        </Card>

        {/* Total de Ordens */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Ordens</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalOrders}</div>
            <p className="text-xs text-muted-foreground">
              Ordens executadas
            </p>
          </CardContent>
        </Card>

        {/* Webhooks Ativos */}
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

        {/* Exchange Accounts */}
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

        {/* Ordens Hoje */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ordens Hoje</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.todayOrders}</div>
            <p className="text-xs text-muted-foreground">
              Ordens executadas hoje
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
              Últimas operações com ativo, data, volume e margem
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingOrders ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : ordersError ? (
              <div className="text-center py-8 text-muted-foreground">
                Erro ao carregar ordens
              </div>
            ) : (
              <div className="max-h-64 overflow-y-auto space-y-3">
                {recentOrdersData.map((order) => (
                <div
                  key={order.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{order.symbol}</p>
                      {getSideBadge(order.side)}
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-xs text-muted-foreground">
                        {new Date(order.createdAt).toLocaleDateString('pt-BR')} {new Date(order.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                      {getOrderStatusBadge(order.status)}
                    </div>
                    <div className="flex items-center justify-between mt-2 text-sm">
                      <span className="text-muted-foreground">
                        Vol: {order.quantity.toLocaleString()}
                      </span>
                      <span className="font-medium">
                        ${((order.averageFillPrice || order.price) * order.quantity).toLocaleString()} USDT
                      </span>
                    </div>
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
                Erro ao carregar posições
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