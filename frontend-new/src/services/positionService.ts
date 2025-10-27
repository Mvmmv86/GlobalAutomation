import { apiClient } from '@/lib/api'
import { Position } from '@/types/trading'

class PositionService {
  async getPositions(params?: {
    status?: string
    exchangeAccountId?: string
    dateFrom?: string
    dateTo?: string
    symbol?: string
    operationType?: string
    limit?: number
    includeClosedFromApi?: boolean  // NOVO: buscar posições fechadas da Binance API
  }): Promise<Position[]> {
    try {
      const searchParams = new URLSearchParams()

      if (params?.status) searchParams.append('status', params.status)
      if (params?.exchangeAccountId && params.exchangeAccountId !== 'all') {
        searchParams.append('exchange_account_id', params.exchangeAccountId)
      }
      if (params?.dateFrom) searchParams.append('date_from', params.dateFrom)
      if (params?.dateTo) searchParams.append('date_to', params.dateTo)
      if (params?.symbol) searchParams.append('symbol', params.symbol)
      if (params?.operationType && params.operationType !== 'all') {
        searchParams.append('operation_type', params.operationType)
      }
      if (params?.limit) searchParams.append('limit', params.limit.toString())
      // NOVO: Adicionar parâmetro para buscar posições fechadas da API
      if (params?.includeClosedFromApi) searchParams.append('include_closed_from_api', 'true')

      const queryString = searchParams.toString()
      const endpoint = `/positions${queryString ? `?${queryString}` : ''}`

      console.log('🔍 PositionService: Fetching positions with filters:', params)
      console.log('🔗 PositionService: Endpoint:', endpoint)

      const response = await apiClient.get<{
        success: boolean;
        data: any[];
      }>(endpoint)

      console.log('📊 PositionService: Response received:', response)

      const apiResponse = response.data ? response : { data: response, success: true }

      if (!apiResponse.data || !apiResponse.success) {
        console.error('❌ Positions API Error:', apiResponse)
        return []
      }

      const positions = apiResponse.data || []
      if (!Array.isArray(positions)) {
        console.error('❌ Positions data is not an array:', positions)
        return []
      }

      console.log(`✅ Processing ${positions.length} positions from API`)

      return positions.map((pos: any) => ({
        id: pos.id,
        symbol: pos.symbol,
        side: pos.side.toUpperCase(), // Garantir uppercase (LONG/SHORT)
        status: pos.status,
        size: pos.size, // Quantidade da posição (corrigido de quantity para size)
        entryPrice: pos.entry_price,
        markPrice: pos.mark_price,
        unrealizedPnl: pos.unrealized_pnl,
        realizedPnl: pos.realized_pnl,
        initialMargin: pos.initial_margin, // Corrigido de margin para initialMargin
        maintenanceMargin: pos.maintenance_margin || 0, // Adicionado maintenanceMargin
        leverage: pos.leverage,
        liquidationPrice: pos.liquidation_price, // Adicionado liquidationPrice
        exchangeAccountId: pos.exchange_account_id,
        openedAt: pos.opened_at || pos.created_at,
        closedAt: pos.closed_at,
        createdAt: pos.created_at,
        updatedAt: pos.updated_at,

        // Campos adicionais específicos
        operation_type: 'futures' // Corrigido de operationType para operation_type
      }))
    } catch (error) {
      console.error('Error fetching positions from Python API:', error)
      throw error
    }
  }

  async getPosition(id: string): Promise<Position> {
    return apiClient.get<Position>(`/positions/${id}`)
  }

  async closePosition(id: string): Promise<void> {
    return apiClient.post(`/positions/${id}/close`)
  }

  async updatePosition(id: string, data: {
    stopLoss?: number
    takeProfit?: number
  }): Promise<Position> {
    return apiClient.put<Position>(`/positions/${id}`, data)
  }

  async getPositionHistory(filters?: {
    symbol?: string
    status?: string
    startDate?: string
    endDate?: string
  }): Promise<Position[]> {
    const params = new URLSearchParams()
    if (filters?.symbol) params.append('symbol', filters.symbol)
    if (filters?.status) params.append('status', filters.status)
    if (filters?.startDate) params.append('start_date', filters.startDate)
    if (filters?.endDate) params.append('end_date', filters.endDate)
    
    return apiClient.get<Position[]>(`/positions/history?${params.toString()}`)
  }

  async getPositionMetrics(): Promise<{
    totalPnl: number
    unrealizedPnl: number
    realizedPnl: number
    openPositions: number
    totalPositions: number
  }> {
    return apiClient.get('/positions/metrics')
  }
}

export const positionService = new PositionService()