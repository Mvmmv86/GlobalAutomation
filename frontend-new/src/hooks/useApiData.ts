import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { exchangeAccountService } from '@/services/exchangeAccountService'
import { webhookService } from '@/services/webhookService'
import { orderService } from '@/services/orderService'
import { positionService } from '@/services/positionService'
import { dashboardService } from '@/services/dashboardService'
import { apiClient } from '@/lib/api'

// Exchange Accounts hooks
export const useExchangeAccounts = () => {
  return useQuery({
    queryKey: ['exchange-accounts'],
    queryFn: exchangeAccountService.getExchangeAccounts,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false, // Evita refetch ao focar na janela
    refetchOnReconnect: false, // Evita refetch ao reconectar
    refetchInterval: false, // Desabilita refetch automático
  })
}

export const useCreateExchangeAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: exchangeAccountService.createExchangeAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exchange-accounts'] })
    },
  })
}

export const useDeleteExchangeAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: exchangeAccountService.deleteExchangeAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exchange-accounts'] })
    },
  })
}

// Webhooks hooks
export const useWebhooks = () => {
  return useQuery({
    queryKey: ['webhooks'],
    queryFn: webhookService.getWebhooks,
    staleTime: 5 * 60 * 1000,
  })
}

export const useCreateWebhook = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: webhookService.createWebhook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

// Orders hooks
export const useOrders = (params?: {
  limit?: number
  exchangeAccountId?: string
  dateFrom?: string
  dateTo?: string
}) => {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => orderService.getOrders(params),
    staleTime: 1 * 60 * 1000, // 1 minute for orders
    enabled: !!params?.exchangeAccountId && params.exchangeAccountId !== 'all', // Só executa com exchange específica
  })
}

export const useRecentOrders = () => {
  return useOrders({ limit: 1000 }) // Increased limit to get all orders for 6 months
}

export const useCreateOrder = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: orderService.createOrder,
    onSuccess: async () => {
      // Invalidate frontend cache
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['balances-summary-v2'] })

      // Invalidate backend cache via API
      try {
        await apiClient.post('/dashboard/cache/invalidate')
        console.log('✅ Backend cache invalidated after order creation')
      } catch (error) {
        console.warn('⚠️ Failed to invalidate backend cache:', error)
      }
    },
  })
}

export const useCreateTestOrder = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: orderService.createTestOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['order-stats'] })
    },
  })
}

export const useOrderStats = () => {
  return useQuery({
    queryKey: ['order-stats'],
    queryFn: orderService.getOrderStats,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

// Positions hooks
export const usePositions = (params?: {
  status?: string
  exchangeAccountId?: string
  dateFrom?: string
  dateTo?: string
  symbol?: string
  operationType?: string
  limit?: number
  includeClosedFromApi?: boolean  // NOVO: buscar fechadas da API
}) => {
  // Configurar polling mais rápido para posições abertas
  const isOpenPositions = params?.status === 'open'
  const isClosedPositions = params?.status === 'closed'

  return useQuery({
    queryKey: ['positions', params],
    queryFn: () => positionService.getPositions(params),
    staleTime: isOpenPositions ? 3 * 1000 : 30 * 1000, // 3s para abertas, 30s para outras
    refetchInterval: isOpenPositions ? 5 * 1000 : undefined, // 5s polling para abertas
    refetchIntervalInBackground: isOpenPositions,
    enabled: !!params?.exchangeAccountId || isClosedPositions, // Só funciona com conta selecionada ou fechadas
  })
}

export const useActivePositions = (params?: {
  exchangeAccountId?: string
  operationType?: string
}) => {
  return usePositions({
    status: 'open',
    ...params
  })
}

export const useSpotBalances = (exchangeAccountId?: string) => {
  return useQuery({
    queryKey: ['spot-balances', exchangeAccountId],
    queryFn: () => dashboardService.getSpotBalances(exchangeAccountId!),
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 30 * 1000, // Refetch every 30s
    enabled: !!exchangeAccountId, // Only fetch when account is selected
  })
}

export const useClosedPositions = (params?: {
  exchangeAccountId?: string
  operationType?: string
  dateFrom?: string
}) => {
  // Se não foi especificado dateFrom, usar automaticamente últimos 30 dias
  const defaultDateFrom = !params?.dateFrom ? (() => {
    const date = new Date()
    date.setDate(date.getDate() - 30) // 30 dias atrás
    return date.toISOString().split('T')[0] // formato YYYY-MM-DD
  })() : params.dateFrom

  return usePositions({
    status: 'closed',
    // Remover limite para puxar todas as posições do período
    dateFrom: defaultDateFrom,
    ...params
  })
}

export const usePositionMetrics = () => {
  return useQuery({
    queryKey: ['position-metrics'],
    queryFn: positionService.getPositionMetrics,
    staleTime: 1 * 60 * 1000,
  })
}

export const useClosePosition = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: positionService.closePosition,
    onSuccess: async () => {
      // Invalidate frontend cache
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['position-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['balances-summary-v2'] })

      // Invalidate backend cache via API
      try {
        await apiClient.post('/dashboard/cache/invalidate')
        console.log('✅ Backend cache invalidated after position close')
      } catch (error) {
        console.warn('⚠️ Failed to invalidate backend cache:', error)
      }
    },
  })
}

// Dashboard Cards Hook - DADOS REAIS DO BANCO
export const useDashboardCards = () => {
  return useQuery({
    queryKey: ['dashboard-cards'],
    queryFn: async () => {
      console.log('🔍 Dashboard Cards: Fazendo chamada para API...')
      try {
        const response = await apiClient.get('/dashboard/cards')
        console.log('✅ Dashboard Cards: Resposta recebida:', response)
        return response
      } catch (error) {
        console.error('❌ Dashboard Cards: Erro na API:', error)
        throw error
      }
    },
    // 🚀 PERFORMANCE: Reduced from 10s to 30s to minimize API calls
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 15000,
  })
}

// Dashboard hooks
export const useDashboardMetrics = () => {
  return useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: dashboardService.getDashboardMetrics,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export const useBalancesSummary = () => {
  return useQuery({
    queryKey: ['balances-summary-v2'],
    queryFn: dashboardService.getBalancesSummary,
    // 🚀 PERFORMANCE OPTIMIZATION: Aligned with backend 30s cache TTL
    // Backend cache: 30s TTL, refetch just before cache expires
    staleTime: 25 * 1000, // 25 seconds - consider stale just before cache expires
    gcTime: 60 * 1000, // 60 seconds garbage collection
    refetchInterval: 30 * 1000, // refetch every 30 seconds (aligned with backend TTL)
    refetchIntervalInBackground: true,
    retry: 1,
  })
}

// NEW: Dashboard Stats Hook (positions count, orders today, orders 3 months)
export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardService.getDashboardStats,
    staleTime: 15 * 1000, // 15 seconds
    refetchInterval: 30 * 1000, // 30 seconds
    refetchIntervalInBackground: true,
  })
}

// NEW: Recent Orders from Exchange Hook (last 7 days)
export const useRecentOrdersFromExchange = (days: number = 7) => {
  return useQuery({
    queryKey: ['recent-orders-exchange', days],
    queryFn: () => dashboardService.getRecentOrders(days),
    staleTime: 15 * 1000, // 15 seconds
    refetchInterval: 30 * 1000, // 30 seconds
  })
}

// NEW: Active Positions from Exchange Hook (real-time)
export const useActivePositionsFromExchange = () => {
  return useQuery({
    queryKey: ['active-positions-exchange'],
    queryFn: dashboardService.getActivePositions,
    staleTime: 5 * 1000, // 5 seconds - positions need real-time updates
    refetchInterval: 10 * 1000, // 10 seconds polling
    refetchIntervalInBackground: true,
  })
}

// NEW: Close Position Mutation
export const useClosePositionFromDashboard = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: dashboardService.closePosition,
    onSuccess: async () => {
      // Invalidate all related caches
      queryClient.invalidateQueries({ queryKey: ['active-positions-exchange'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
      queryClient.invalidateQueries({ queryKey: ['balances-summary-v2'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['position-metrics'] })

      // Invalidate backend cache via API
      try {
        await apiClient.post('/dashboard/cache/invalidate')
        console.log('✅ Backend cache invalidated after position close')
      } catch (error) {
        console.warn('⚠️ Failed to invalidate backend cache:', error)
      }
    },
  })
}

export const usePnlChart = (days: number = 7) => {
  return useQuery({
    queryKey: ['pnl-chart', days],
    queryFn: () => dashboardService.getPnlChart(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Account Balance Hook - for specific account (works with all exchanges)
export const useAccountBalance = (accountId?: string) => {
  return useQuery({
    queryKey: ['account-balance', accountId],
    queryFn: async () => {
      if (!accountId) return null
      console.log('🔍 useAccountBalance: Fetching balance for account:', accountId)

      // Use new multi-exchange endpoint
      const response = await apiClient.get<any>(`/dashboard/balances/${accountId}`)
      console.log('💰 useAccountBalance: Response received:', response)

      // apiClient.get() already extracts data from {success, data} response
      if (response && typeof response === 'object') {
        return {
          futures_balance_usdt: response.futures_balance_usdt || 0,
          spot_balance_usdt: response.spot_balance_usdt || 0,
          total_balance_usdt: response.total_balance_usdt || 0
        }
      }

      return null
    },
    enabled: !!accountId,
    // 🚀 PERFORMANCE OPTIMIZATION: Aligned with backend 30s cache TTL
    // Backend cache: 30s TTL, balance data doesn't change that rapidly
    staleTime: 25 * 1000, // 25 seconds
    gcTime: 60 * 1000, // 60 seconds
    refetchInterval: 30 * 1000, // Refetch every 30 seconds (aligned with backend TTL)
    refetchIntervalInBackground: true,
  })
}

// Symbol Discovery Hooks
export const useSymbolDiscovery = () => {
  return useQuery({
    queryKey: ['symbol-discovery'],
    queryFn: async () => {
      const { symbolDiscoveryService } = await import('@/services/symbolDiscoveryService')
      return symbolDiscoveryService.discoverSymbols()
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 60 * 1000, // refresh every minute
  })
}

export const useSymbolSearch = (query: string) => {
  return useQuery({
    queryKey: ['symbol-search', query],
    queryFn: async () => {
      const { symbolDiscoveryService } = await import('@/services/symbolDiscoveryService')
      return symbolDiscoveryService.searchSymbol(query)
    },
    enabled: query.length >= 2,
    staleTime: 30 * 1000, // 30 seconds
  })
}