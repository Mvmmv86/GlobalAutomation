import { apiClient } from '@/lib/api'
import { Order } from '@/types/trading'

class OrderService {
  async getOrders(params?: {
    limit?: number
    exchangeAccountId?: string
    dateFrom?: string
    dateTo?: string
  }): Promise<Order[]> {
    try {
      // Construir query parameters
      const searchParams = new URLSearchParams()
      if (params?.limit) searchParams.append('limit', params.limit.toString())
      if (params?.exchangeAccountId && params.exchangeAccountId !== 'all') {
        searchParams.append('exchange_account_id', params.exchangeAccountId)
      }
      if (params?.dateFrom) searchParams.append('date_from', params.dateFrom)
      if (params?.dateTo) searchParams.append('date_to', params.dateTo)

      const queryString = searchParams.toString()
      const endpoint = `/orders${queryString ? `?${queryString}` : ''}`

      console.log('🔍 OrderService: Fetching orders with filters:', params)
      console.log('🔗 OrderService: Endpoint:', endpoint)

      const response = await apiClient.get<{
        success: boolean;
        data: any[];
        total: number;
      }>(endpoint)

      console.log('📊 OrderService: Response received:', response)

      // FASE 1: Our API returns {success, data: [...], total} format
      console.log('🔍 OrderService: Full response structure:', JSON.stringify(response, null, 2))

      // Check if response is the actual API response or wrapped by axios
      const apiResponse = response.data ? response : { data: response, success: true }

      if (!apiResponse.data || !apiResponse.success) {
        console.error('❌ API Error or invalid response:', apiResponse)
        return []
      }

      const orders = apiResponse.data || []
      if (!Array.isArray(orders)) {
        console.error('❌ Data is not an array:', orders)
        return []
      }

      console.log(`✅ Processing ${orders.length} orders from API`)

      // Transform Python API data to match frontend Order type - FASE 1
      const transformedOrders = orders.map((order: any) => ({
        id: order.id.toString(),
        clientOrderId: order.exchange_order_id || `order_${order.id}`,
        symbol: order.symbol,
        side: order.side,
        type: order.order_type,
        status: order.status,
        quantity: order.quantity,
        price: order.price,
        filledQuantity: order.filled_quantity || 0,
        averageFillPrice: order.average_price,
        feesPaid: 0, // FASE 1: Not implemented yet
        feeCurrency: null,
        source: 'binance',
        exchangeAccountId: order.exchange || 'binance',
        createdAt: order.created_at,
        updatedAt: order.updated_at,

        // FASE 1: Campos adicionais que implementamos
        operation_type: order.operation_type || 'spot',
        entry_exit: order.entry_exit || (order.side === 'buy' ? 'entrada' : 'saida'),
        margin_usdt: order.margin_usdt || 0,
        profit_loss: order.profit_loss || 0,
        order_id: order.order_id || null,  // Order ID para agrupamento
      }))
      
      return transformedOrders
    } catch (error) {
      console.error('Error fetching orders from Python API:', error)
      throw error
    }
  }

  async getOrder(id: string): Promise<Order> {
    try {
      const response = await apiClient.get<{
        success: boolean;
        data: any;
      }>(`/orders/${id}`)
      
      const order = response.data
      return {
        id: order.id.toString(),
        clientOrderId: order.exchange_order_id || `order_${order.id}`,
        symbol: order.symbol,
        side: order.side,
        type: order.order_type,
        status: order.status === 'FILLED' ? 'filled' : 
                order.status === 'pending' ? 'open' : 
                order.status.toLowerCase(),
        quantity: order.quantity,
        price: order.price,
        filledQuantity: order.filled_quantity || 0,
        averageFillPrice: order.average_price,
        feesPaid: 0,
        feeCurrency: null,
        source: 'tradingview',
        exchangeAccountId: order.exchange || 'binance',
        createdAt: order.created_at,
        updatedAt: order.updated_at,
      }
    } catch (error) {
      console.error('Error fetching order details from Python API:', error)
      throw error
    }
  }

  async createOrder(data: {
    symbol: string
    side: string
    type: string
    quantity: number
    price?: number
    stopPrice?: number
    exchangeAccountId: string
  }): Promise<Order> {
    return apiClient.post<Order>('/orders', data)
  }

  async createTestOrder(): Promise<any> {
    try {
      const response = await apiClient.post<{
        success: boolean;
        message: string;
        data: any;
      }>('/orders/test')
      
      return response
    } catch (error) {
      console.error('Error creating test order:', error)
      throw error
    }
  }

  async getOrderStats(): Promise<{
    total_orders: number;
    filled_orders: number;
    pending_orders: number;
    failed_orders: number;
    success_rate: number;
    total_volume: number;
  }> {
    try {
      const response = await apiClient.get<{
        success: boolean;
        data: any;
      }>('/orders/stats')
      
      return response.data
    } catch (error) {
      console.error('Error fetching order stats:', error)
      throw error
    }
  }

  async cancelOrder(id: string): Promise<void> {
    return apiClient.delete(`/orders/${id}`)
  }

  async getOrderHistory(filters?: {
    symbol?: string
    status?: string
    startDate?: string
    endDate?: string
  }): Promise<Order[]> {
    const params = new URLSearchParams()
    if (filters?.symbol) params.append('symbol', filters.symbol)
    if (filters?.status) params.append('status', filters.status)
    if (filters?.startDate) params.append('start_date', filters.startDate)
    if (filters?.endDate) params.append('end_date', filters.endDate)
    
    return apiClient.get<Order[]>(`/orders/history?${params.toString()}`)
  }
}

export const orderService = new OrderService()