import { apiClient } from '@/lib/api'
import { Position } from '@/types/trading'

class PositionService {
  async getPositions(status?: string): Promise<Position[]> {
    const params = status ? `?status=${status}` : ''
    return apiClient.get<Position[]>(`/positions${params}`)
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