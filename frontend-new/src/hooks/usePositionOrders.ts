import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:3001'}/api/v1`

interface Order {
  id: string
  symbol: string
  side: string
  order_type: string
  quantity: number
  price: number
  status: string
  exchange: string
  exchange_order_id: string
  operation_type: string
}

interface OrdersResponse {
  success: boolean
  data: Order[]
}

export const usePositionOrders = (exchangeAccountId?: string, symbol?: string) => {
  return useQuery({
    queryKey: ['position-orders', exchangeAccountId, symbol],
    queryFn: async () => {
      if (!exchangeAccountId) {
        return { stopLoss: undefined, takeProfit: undefined, orders: [] }
      }

      const params = new URLSearchParams({
        exchange_account_id: exchangeAccountId,
        ...(symbol && { symbol })
      })

      const response = await axios.get<OrdersResponse>(
        `${API_BASE_URL}/orders?${params.toString()}`,
        { withCredentials: true }
      )

      if (!response.data.success) {
        throw new Error('Failed to fetch orders')
      }

      const orders = response.data.data

      // CRITICAL FIX: Filtrar ordens PENDENTES de SL/TP para o símbolo
      // Status 'pending' = ordem criada na exchange mas ainda não executada
      // Backend agora retorna 'pending' para ordens vindas da API
      const activeOrders = orders.filter(
        order => order.status === 'pending' && (!symbol || order.symbol === symbol)
      )

      console.log('🔍 usePositionOrders DEBUG:', {
        totalOrders: orders.length,
        activeOrders: activeOrders.length,
        orderTypes: activeOrders.map(o => o.order_type)
      })

      // Encontrar Stop Loss (ordem com 'stop' no tipo)
      const stopLossOrder = activeOrders.find(order =>
        order.order_type.toLowerCase().includes('stop')
      )

      // Encontrar Take Profit (ordem com 'take_profit' no tipo)
      const takeProfitOrders = activeOrders.filter(order =>
        order.order_type.toLowerCase().includes('take_profit') ||
        order.order_type.toLowerCase().includes('takeprofit')
      )

      // Pegar o TP mais próximo (menor preço para LONG, maior para SHORT)
      const takeProfitOrder = takeProfitOrders.length > 0
        ? takeProfitOrders[0]
        : undefined

      // Para SL/TP, usar stop_price se price não estiver disponível
      const stopLossPrice = stopLossOrder?.stop_price || stopLossOrder?.price
      const takeProfitPrice = takeProfitOrder?.stop_price || takeProfitOrder?.price

      // ✅ Filtrar TPs válidos (> 0 e não undefined)
      const validTakeProfits = takeProfitOrders
        .map(o => o.stop_price || o.price)
        .filter(price => price && price > 0)

      console.log('✅ usePositionOrders RESULT:', {
        stopLoss: stopLossPrice,
        takeProfit: takeProfitPrice,
        allTakeProfits: validTakeProfits
      })

      return {
        stopLoss: stopLossPrice,
        takeProfit: takeProfitPrice,
        orders: activeOrders,
        allTakeProfits: validTakeProfits
      }
    },
    enabled: !!exchangeAccountId,
    // 🚀 PERFORMANCE: Increased from 5s to 10s to reduce API calls
    refetchInterval: 10000, // Atualizar a cada 10 segundos
    staleTime: 5000, // Cache de 5 segundos para evitar refetch durante optimistic update
    gcTime: 20000 // Garbage collection após 20 segundos
  })
}
