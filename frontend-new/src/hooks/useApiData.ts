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
    // 🚀 PERFORMANCE: Reduced refetch interval to minimize API calls
    // Backend cache: 3s TTL, so we can refetch less frequently
    staleTime: 10 * 1000, // 10 seconds
    gcTime: 30 * 1000, // 30 seconds garbage collection
    refetchInterval: 15 * 1000, // refetch every 15 seconds (reduced from 5s)
    refetchIntervalInBackground: true,
    retry: 1,
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
      const response = await apiClient.get(`/dashboard/balances/${accountId}`)
      console.log('💰 useAccountBalance: Response received:', response)

      if (response.success && response.data) {
        return {
          futures_balance_usdt: response.data.futures_balance_usdt || 0,
          spot_balance_usdt: response.data.spot_balance_usdt || 0,
          total_balance_usdt: response.data.total_balance_usdt || 0
        }
      }

      return null
    },
    enabled: !!accountId,
    // 🚀 PERFORMANCE: Increased intervals to reduce API calls
    staleTime: 20 * 1000, // 20 seconds
    refetchInterval: 30 * 1000, // refresh every 30 seconds (reduced from 15s)
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