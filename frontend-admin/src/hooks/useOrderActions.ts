import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { OrderFormData } from '../components/molecules/OrderCreationModal'

const API_BASE_URL = 'http://localhost:8000/api/v1'

// Types
interface CreateOrderResponse {
  success: boolean
  order_id?: string
  message?: string
  error?: string
}

interface ClosePositionRequest {
  positionId: string
  percentage?: number  // 1-100, default 100
}

interface ModifyOrderRequest {
  orderId: string
  stopLoss?: number
  takeProfit?: number
  trailingStop?: boolean
  trailingDelta?: number
  trailingDeltaType?: 'amount' | 'percent'
}

// Create Order Hook
export const useCreateOrder = () => {
  const queryClient = useQueryClient()

  return useMutation<CreateOrderResponse, Error, OrderFormData>({
    mutationFn: async (orderData: OrderFormData) => {
      const payload = {
        exchange_account_id: orderData.accountId,
        symbol: orderData.symbol,
        side: orderData.side,
        order_type: orderData.orderType,
        operation_type: orderData.operationType,
        quantity: orderData.quantity,
        ...(orderData.price && { price: orderData.price }),
        ...(orderData.stopPrice && { stop_price: orderData.stopPrice }),
        ...(orderData.leverage && { leverage: orderData.leverage }),
        ...(orderData.stopLoss && { stop_loss: orderData.stopLoss }),
        ...(orderData.takeProfit && { take_profit: orderData.takeProfit }),
        ...(orderData.trailingStop && {
          trailing_stop: true,
          trailing_delta: orderData.trailingDelta,
          trailing_delta_type: orderData.trailingDeltaType
        })
      }

      const response = await fetch(`${API_BASE_URL}/orders/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Erro ao criar ordem')
      }

      return response.json()
    },
    onSuccess: () => {
      // Invalidate queries to refetch positions and orders
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['balances'] })
    }
  })
}

// Close Position Hook
export const useClosePosition = () => {
  const queryClient = useQueryClient()

  return useMutation<CreateOrderResponse, Error, ClosePositionRequest>({
    mutationFn: async (closeData: ClosePositionRequest) => {
      const payload = {
        position_id: closeData.positionId,
        percentage: closeData.percentage || 100
      }

      console.log('🔵 useClosePosition: Sending request:', payload)

      const response = await fetch(`${API_BASE_URL}/orders/close`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const error = await response.json()
        console.error('❌ useClosePosition: Error response:', error)
        throw new Error(error.detail || 'Erro ao fechar posição')
      }

      const result = await response.json()
      console.log('✅ useClosePosition: Success:', result)
      return result
    },
    onSuccess: (data) => {
      console.log('✅ useClosePosition: onSuccess, invalidating queries')
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['balances'] })
    },
    onError: (error) => {
      console.error('❌ useClosePosition: onError:', error)
    }
  })
}

// Modify Order Hook
export const useModifyOrder = () => {
  const queryClient = useQueryClient()

  return useMutation<CreateOrderResponse, Error, ModifyOrderRequest>({
    mutationFn: async (modifyData: ModifyOrderRequest) => {
      const payload = {
        ...(modifyData.stopLoss !== undefined && { stop_loss: modifyData.stopLoss }),
        ...(modifyData.takeProfit !== undefined && { take_profit: modifyData.takeProfit }),
        ...(modifyData.trailingStop !== undefined && { trailing_stop: modifyData.trailingStop }),
        ...(modifyData.trailingDelta !== undefined && { trailing_delta: modifyData.trailingDelta }),
        ...(modifyData.trailingDeltaType && { trailing_delta_type: modifyData.trailingDeltaType })
      }

      const response = await fetch(`${API_BASE_URL}/orders/${modifyData.orderId}/modify`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Erro ao modificar ordem')
      }

      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    }
  })
}
