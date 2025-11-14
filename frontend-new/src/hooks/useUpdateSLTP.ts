import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { toast } from 'react-toastify'

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:3001'}/api/v1`

interface UpdateSLTPRequest {
  exchange_account_id: string
  symbol: string
  position_side: 'LONG' | 'SHORT'
  order_type: 'STOP_LOSS' | 'TAKE_PROFIT'
  new_price: number
  old_order_id?: string
  quantity: number
}

interface UpdateSLTPResponse {
  success: boolean
  message: string
  data?: {
    cancelled_order_id?: string
    new_order_id: string
    symbol: string
    order_type: string
    new_price: number
  }
  error?: string
}

export const useUpdateSLTP = () => {
  const queryClient = useQueryClient()

  return useMutation<UpdateSLTPResponse, Error, UpdateSLTPRequest>({
    mutationFn: async (request: UpdateSLTPRequest) => {
      console.log('🔄 Updating SL/TP order:', request)

      const response = await axios.put<UpdateSLTPResponse>(
        `${API_BASE_URL}/orders/update-sl-tp`,
        request,
        { withCredentials: true }
      )

      if (!response.data.success) {
        throw new Error(response.data.error || 'Failed to update SL/TP')
      }

      return response.data
    },

    onSuccess: (data) => {
      console.log('✅ SL/TP updated successfully:', data)

      // Show success toast
      const orderType = data.data?.order_type === 'STOP_LOSS' ? 'Stop Loss' : 'Take Profit'
      toast.success(
        `${orderType} atualizado para $${data.data?.new_price.toFixed(2)}`,
        { position: 'bottom-right', autoClose: 3000 }
      )

      // Invalidate related queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['position-orders'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    },

    onError: (error: Error) => {
      console.error('❌ Failed to update SL/TP:', error)

      // Show error toast
      toast.error(
        `Erro ao atualizar ordem: ${error.message}`,
        { position: 'bottom-right', autoClose: 5000 }
      )
    },

    onMutate: async (request) => {
      // Optimistic update - immediately update the UI
      const queryKey = ['position-orders', request.exchange_account_id, request.symbol]

      await queryClient.cancelQueries({ queryKey })

      const previousData = queryClient.getQueryData(queryKey)

      // Update cache optimistically
      queryClient.setQueryData(queryKey, (old: any) => {
        if (!old) return old

        const newPrice = request.new_price

        if (request.order_type === 'STOP_LOSS') {
          return {
            ...old,
            stopLoss: newPrice
          }
        } else {
          return {
            ...old,
            takeProfit: newPrice
          }
        }
      })

      // Return context with previous data for rollback
      return { previousData, queryKey }
    },

    onSettled: () => {
      // Always refetch after mutation to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['position-orders'] })
    }
  })
}