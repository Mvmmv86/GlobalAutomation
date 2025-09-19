import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { exchangeAccountService } from '@/services/exchangeAccountService'
import { webhookService } from '@/services/webhookService'
import { orderService } from '@/services/orderService'
import { positionService } from '@/services/positionService'

// Exchange Accounts hooks
export const useExchangeAccounts = () => {
  return useQuery({
    queryKey: ['exchange-accounts'],
    queryFn: exchangeAccountService.getExchangeAccounts,
    staleTime: 5 * 60 * 1000, // 5 minutes
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
export const useOrders = (limit?: number) => {
  return useQuery({
    queryKey: ['orders', limit],
    queryFn: () => orderService.getOrders(limit),
    staleTime: 1 * 60 * 1000, // 1 minute for orders
  })
}

export const useRecentOrders = () => {
  return useOrders(10) // Last 10 orders
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