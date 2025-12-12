import React, { useState } from 'react'
import { BarChart3, Building2, FileText, TrendingUp, Webhook, DollarSign, Wifi, X, Calendar } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import {
  useExchangeAccounts,
  useWebhooks,
  useCreateTestOrder,
  useBalancesSummary,
  useDashboardStats,
  useRecentOrdersFromExchange,
  useActivePositionsFromExchange,
  useClosePositionFromDashboard,
} from '@/hooks/useApiData'

const DashboardPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [apiResponse, setApiResponse] = useState<string>('')
  const [closingPositionId, setClosingPositionId] = useState<string | null>(null)

  // API Data hooks
  const { data: exchangeAccounts, isLoading: loadingAccounts, error: accountsError } = useExchangeAccounts()
  const { data: webhooks, isLoading: loadingWebhooks, error: webhooksError } = useWebhooks()
  const { data: balancesSummary, isLoading: loadingBalances, error: balancesError, refetch: refetchBalances } = useBalancesSummary()

  // NEW: Dashboard Stats (positions count, orders today, orders 3 months)
  const { data: dashboardStats, isLoading: loadingStats, error: statsError } = useDashboardStats()

  // NEW: Recent Orders from Exchange (last 7 days)
  const { data: recentOrdersExchange, isLoading: loadingOrders, error: ordersError } = useRecentOrdersFromExchange(7)

  // NEW: Active Positions from Exchange (real-time)
  const { data: activePositionsExchange, isLoading: loadingPositions, error: positionsError } = useActivePositionsFromExchange()

  // NEW: Close Position Mutation
  const closePositionMutation = useClosePositionFromDashboard()

  const createTestOrderMutation = useCreateTestOrder()

  const testApiConnection = async () => {
    setApiStatus('testing')
    try {
      // Test health endpoint
      const baseUrl = import.meta.env.VITE_API_URL || ''
      const url = baseUrl ? `${baseUrl}/api/v1/health` : '/api/v1/health'

      console.log('🧪 Testing API connection to:', url)
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setApiResponse(JSON.stringify(data, null, 2))
      setApiStatus('success')
    } catch (error) {
      console.error('❌ API test failed:', error)
      setApiResponse(error instanceof Error ? error.message : 'Erro desconhecido')
      setApiStatus('error')
    }
  }

  const handleRefreshData = async () => {
    try {
      console.log('🔄 Starting data refresh...')

      // Se tiver contas, sincronizar cada uma
      if (exchangeAccounts && exchangeAccounts.length > 0) {
        const baseUrl = import.meta.env.VITE_API_URL || ''
        const token = localStorage.getItem('accessToken')

        for (const account of exchangeAccounts) {
          try {
            const syncUrl = baseUrl
              ? `${baseUrl}/api/v1/sync/balances/${account.id}`
              : `/api/v1/sync/balances/${account.id}`

            console.log('🔄 Syncing account:', account.name)
            const response = await fetch(syncUrl, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            })

            if (response.ok) {
              console.log('✅ Account synced:', account.name)
            } else {
              console.warn('⚠️ Failed to sync account:', account.name)
            }
          } catch (err) {
            console.error('❌ Error syncing account:', account.name, err)
          }
        }

        // Aguardar 1 segundo para sincronização completar
        await new Promise(resolve => setTimeout(resolve, 1000))
      }

      // Agora fazer refetch dos dados
      console.log('📡 Refetching balances...')
      await refetchBalances()
      console.log('✅ Data refresh completed')
    } catch (error) {
      console.error('❌ Error refreshing data:', error)
    }
  }

  // Use real data when available
  const hasApiErrors = accountsError || webhooksError || ordersError || positionsError || statsError || balancesError
  const isLoadingData = loadingAccounts || loadingWebhooks || loadingOrders || loadingPositions || loadingStats || loadingBalances

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

  // Function to close position
  const handleClosePosition = async (position: any) => {
    if (closingPositionId) return // Prevent double-click
    setClosingPositionId(position.id)
    try {
      await closePositionMutation.mutateAsync({
        symbol: position.symbol,
        side: position.side,
        size: position.size,
        exchange_account_id: position.exchange_account_id
      })
      setApiStatus('success')
      setApiResponse(`Position ${position.symbol} closed successfully!`)
    } catch (error) {
      setApiStatus('error')
      setApiResponse(error instanceof Error ? error.message : 'Failed to close position')
    } finally {
      setClosingPositionId(null)
    }
  }

  // Stats object with real data from exchange
  const stats = {
    // Balances from exchange
    futuresBalance: balancesSummary?.futures?.total_balance_usd || 0,
    futuresUnrealizedPnL: balancesSummary?.futures?.unrealized_pnl || 0,
    futuresRealizedPnLToday: balancesSummary?.futures?.realized_pnl_today || 0,
    spotBalance: balancesSummary?.spot?.total_balance_usd || 0,
    spotAssets: balancesSummary?.spot?.assets?.length || 0,
    spotPnL: balancesSummary?.spot?.unrealized_pnl || 0,
    totalPnL: balancesSummary?.total?.pnl || 0,
    totalRealizedPnLToday: balancesSummary?.total?.realized_pnl_today || 0,
    totalPnLToday: balancesSummary?.total?.total_pnl_today || 0,

    // Stats from exchange (NEW endpoints)
    activePositions: dashboardStats?.active_positions || 0,
    totalOrders: dashboardStats?.orders_3_months || 0,
    todayOrders: dashboardStats?.orders_today || 0,

    // Other data
    activeWebhooks: webhooks?.filter(w => w.status === 'active').length || 0,
    exchangeAccounts: exchangeAccounts?.length || 0,
  }

  // Real data from exchange
  const recentOrdersData = recentOrdersExchange || []
  // Filter to show only FUTURES positions (not SPOT)
  const activePositionsData = (activePositionsExchange || []).filter(
    (pos: any) => pos.market_type?.toUpperCase() === 'FUTURES'
  )

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

  // Badge para tipo de mercado (SPOT/FUTURES)
  const getMarketTypeBadge = (marketType: string) => {
    const isSpot = marketType?.toUpperCase() === 'SPOT'
    return (
      <Badge variant={isSpot ? 'secondary' : 'outline'} className="text-xs">
        {isSpot ? 'SPOT' : 'FUTURES'}
      </Badge>
    )
  }

  // Badge para direção do trade (ENTRADA/SAÍDA)
  const getTradeDirectionBadge = (direction: string) => {
    const isEntrada = direction?.toUpperCase() === 'ENTRADA'
    return (
      <Badge variant={isEntrada ? 'success' : 'warning'} className="text-xs">
        {isEntrada ? 'Entrada' : 'Saída'}
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
            onClick={handleRefreshData}
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
                ${stats.futuresUnrealizedPnL >= 0 ? '+' : ''}{stats.futuresUnrealizedPnL.toFixed(2)}
              </span>
            </p>
            {stats.futuresRealizedPnLToday !== 0 && (
              <p className="text-xs text-muted-foreground">
                Realizado hoje: <span className={stats.futuresRealizedPnLToday >= 0 ? 'text-green-600' : 'text-red-600'}>
                  ${stats.futuresRealizedPnLToday >= 0 ? '+' : ''}{stats.futuresRealizedPnLToday.toFixed(2)}
                </span>
              </p>
            )}
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
            <div className={`text-2xl font-bold ${stats.totalPnLToday >= 0 ? 'text-success' : 'text-danger'}`}>
              {stats.totalPnLToday >= 0 ? '+' : ''}${Math.abs(stats.totalPnLToday).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              Não realizado: <span className={stats.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}>
                ${stats.totalPnL >= 0 ? '+' : ''}{stats.totalPnL.toFixed(2)}
              </span>
              {stats.totalRealizedPnLToday !== 0 && (
                <> | Realizado: <span className={stats.totalRealizedPnLToday >= 0 ? 'text-green-600' : 'text-red-600'}>
                  ${stats.totalRealizedPnLToday >= 0 ? '+' : ''}{stats.totalRealizedPnLToday.toFixed(2)}
                </span></>
              )}
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

        {/* Total de Ordens (3 meses) */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Ordens</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalOrders}</div>
            <p className="text-xs text-muted-foreground">
              Últimos 3 meses
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
        {/* Recent Orders - Last 7 Days */}
        <Card>
          <CardHeader>
            <CardTitle>Ordens Recentes</CardTitle>
            <CardDescription>
              Últimos 7 dias: tipo, ativo, data, volume, margem, P&L
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
            ) : recentOrdersData.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                Nenhuma ordem nos últimos 7 dias
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-3">
                {recentOrdersData.map((order: any) => (
                <div
                  key={order.id}
                  className="p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 flex-wrap gap-1">
                      <p className="font-medium">{order.symbol}</p>
                      {getMarketTypeBadge(order.market_type)}
                      {getSideBadge(order.side?.toLowerCase() as any)}
                      {getTradeDirectionBadge(order.trade_direction)}
                    </div>
                    <span className={`text-sm font-medium ${order.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {order.pnl >= 0 ? '+' : ''}${order.pnl?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-sm text-muted-foreground">
                    <span>
                      {order.created_at ? new Date(order.created_at).toLocaleDateString('pt-BR') : '-'}{' '}
                      {order.created_at ? new Date(order.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                    <span>{order.type}</span>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-sm">
                    <span className="text-muted-foreground">
                      Vol: ${order.volume_usdt?.toFixed(2) || '0.00'}
                    </span>
                    <span className="text-muted-foreground">
                      Margem: ${order.margin_usdt?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                </div>
              ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Active Positions - Real-time */}
        <Card>
          <CardHeader>
            <CardTitle>Posições Ativas</CardTitle>
            <CardDescription>
              Posições em aberto em tempo real
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
            ) : activePositionsData.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                Nenhuma posição aberta
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-3">
                {activePositionsData.map((position: any) => (
                <div
                  key={position.id}
                  className="p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 flex-wrap gap-1">
                      <p className="font-medium">{position.symbol}</p>
                      {getMarketTypeBadge(position.market_type)}
                      {getSideBadge(position.side?.toLowerCase() as any)}
                      <Badge variant="outline" className="text-xs">
                        {position.leverage}x
                      </Badge>
                    </div>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleClosePosition(position)}
                      disabled={closingPositionId === position.id || position.market_type?.toUpperCase() === 'SPOT'}
                      className="h-7 px-2"
                      title={position.market_type?.toUpperCase() === 'SPOT' ? 'Não é possível fechar posições SPOT aqui' : 'Fechar posição'}
                    >
                      {closingPositionId === position.id ? (
                        <LoadingSpinner />
                      ) : (
                        <>
                          <X className="w-3 h-3 mr-1" />
                          Fechar
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-muted-foreground">
                      Size: {position.size}
                    </span>
                    <span className={`text-sm font-medium ${
                      position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl?.toFixed(2) || '0.00'}
                      <span className="text-xs ml-1">
                        ({position.pnl_percentage >= 0 ? '+' : ''}{position.pnl_percentage?.toFixed(2) || '0'}%)
                      </span>
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground">
                    <span>Entry: ${position.entry_price?.toFixed(4) || '0'}</span>
                    <span>Mark: ${position.mark_price?.toFixed(4) || '0'}</span>
                    {position.market_type?.toUpperCase() !== 'SPOT' && (
                      <span>Liq: ${position.liquidation_price?.toFixed(4) || '0'}</span>
                    )}
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