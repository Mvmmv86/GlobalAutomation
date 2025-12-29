import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api/v1'

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

      // Filtrar ordens ativas de SL/TP para o símbolo
      // Status válidos: 'submitted', 'open', 'pending' (não 'new' que causava bug)
      const activeOrders = orders.filter(
        order => ['submitted', 'open', 'pending'].includes(order.status) &&
                 (!symbol || order.symbol === symbol)
      )

      // Encontrar Stop Loss (ordem de venda para posição LONG, compra para SHORT)
      const stopLossOrder = activeOrders.find(order =>
        order.order_type.toLowerCase().includes('stop')
      )

      // Encontrar Take Profit
      const takeProfitOrders = activeOrders.filter(order =>
        order.order_type.toLowerCase().includes('take_profit') ||
        order.order_type.toLowerCase().includes('takeprofit')
      )

      // Pegar o TP mais próximo (menor preço para LONG, maior para SHORT)
      const takeProfitOrder = takeProfitOrders.length > 0
        ? takeProfitOrders[0]
        : undefined

      // ✅ Filtrar TPs válidos (> 0 e não undefined)
      const validTakeProfits = takeProfitOrders
        .map(o => o.price)
        .filter(price => price && price > 0)

      return {
        stopLoss: stopLossOrder?.price,
        takeProfit: takeProfitOrder?.price,
        orders: activeOrders,
        allTakeProfits: validTakeProfits
      }
    },
    enabled: !!exchangeAccountId,
    // 🚀 PERFORMANCE: Increased from 5s to 10s to reduce API calls
    // refetchInterval removido // Atualizar a cada 10 segundos
    staleTime: 5000, // Cache de 5 segundos para evitar refetch durante optimistic update
    gcTime: 20000 // Garbage collection após 20 segundos
  })
}
