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
  })
}

export const useRecentOrders = () => {
  return useOrders({ limit: 10 }) // Last 10 orders
}

export const useCreateOrder = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: orderService.createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
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
export const usePositions = (status?: string) => {
  return useQuery({
    queryKey: ['positions', status],
    queryFn: () => positionService.getPositions(status),
    staleTime: 30 * 1000, // 30 seconds for positions
  })
}

export const useActivePositions = () => {
  return usePositions('open')
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['position-metrics'] })
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
    refetchInterval: 10000, // Refresh every 10 seconds
    staleTime: 5000,
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
    queryKey: ['balances-summary-v2'], // Changed key to force refresh
    queryFn: dashboardService.getBalancesSummary,
    staleTime: 0, // No cache
    gcTime: 0, // No cache
    refetchInterval: 10 * 1000, // refetch every 10 seconds
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