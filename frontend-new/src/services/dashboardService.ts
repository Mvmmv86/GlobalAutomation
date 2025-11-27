import api from '@/lib/api'
import { logger } from '@/utils/logger'

export interface BalanceAsset {
  asset: string
  free: number
  locked: number
  total: number
  usd_value: number
  exchange: string
}

export interface SpotAsset {
  asset: string
  free: number
  locked: number
  total: number
  in_order: number
  usd_value: number
}

export interface SpotBalancesData {
  exchange_account_id: string
  assets: SpotAsset[]
  total_assets: number
  total_usd_value: number
}

export interface BalanceData {
  futures: {
    total_balance_usd: number
    unrealized_pnl: number
    net_balance: number
    assets: BalanceAsset[]
  }
  spot: {
    total_balance_usd: number
    unrealized_pnl: number
    net_balance: number
    assets: BalanceAsset[]
  }
  total: {
    balance_usd: number
    pnl: number
    net_worth: number
  }
}

export interface DashboardMetrics {
  period: {
    start_date: string
    end_date: string
    days: number
  }
  pnl_summary: {
    total_pnl_7d: number
    unrealized_pnl: number
    realized_pnl: number
    total_fees_paid: number
    net_pnl: number
  }
  positions_summary: {
    open_positions: number
    closed_positions: number
    total_positions: number
  }
  orders_summary: {
    total_orders: number
    executed_orders: number
    canceled_orders: number
    execution_rate: number
  }
  accounts_summary: {
    total_accounts: number
    active_accounts: number
  }
  top_performers: Array<{
    symbol: string
    side: string
    pnl: number
    exchange: string
  }>
  worst_performers: Array<{
    symbol: string
    side: string
    pnl: number
    exchange: string
  }>
}

// Dashboard Stats (posições ativas, ordens hoje, ordens 3 meses)
export interface DashboardStats {
  active_positions: number
  orders_today: number
  orders_3_months: number
}

// Recent Orders from exchange
export interface RecentOrder {
  id: string
  symbol: string
  side: string
  type: string
  status: string
  quantity: number
  price: number
  volume_usdt: number
  margin_usdt: number
  pnl: number
  operation_type: string
  created_at: string
  exchange: string
}

// Active Position from exchange
export interface ActivePosition {
  id: string
  symbol: string
  side: string
  position_side: string
  size: number
  entry_price: number
  mark_price: number
  unrealized_pnl: number
  pnl_percentage: number
  margin: number
  leverage: number
  liquidation_price: number
  notional: number
  operation_type: string
  exchange: string
  exchange_account_id: string
}

export const dashboardService = {
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    return await api.get<DashboardMetrics>('/dashboard/metrics')
  },

  // NEW: Get dashboard stats (positions count, orders today, orders 3 months)
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const data = await api.get<DashboardStats>('/dashboard/stats')
      return data
    } catch (error) {
      logger.error('getDashboardStats error:', error)
      throw error
    }
  },

  // NEW: Get recent orders from exchange (last 7 days by default)
  async getRecentOrders(days: number = 7): Promise<RecentOrder[]> {
    try {
      const orders = await api.get<RecentOrder[]>(`/dashboard/recent-orders?days=${days}`)
      return Array.isArray(orders) ? orders : []
    } catch (error) {
      logger.error('getRecentOrders error:', error)
      throw error
    }
  },

  // NEW: Get active positions from exchange in real-time
  async getActivePositions(): Promise<ActivePosition[]> {
    try {
      const positions = await api.get<ActivePosition[]>('/dashboard/active-positions')
      return Array.isArray(positions) ? positions : []
    } catch (error) {
      logger.error('getActivePositions error:', error)
      throw error
    }
  },

  // NEW: Close position via market order
  async closePosition(params: {
    symbol: string
    side: string
    size: number
    exchange_account_id?: string
  }): Promise<{ success: boolean; message: string; data?: any }> {
    try {
      const response = await api.post<{ success: boolean; message: string; data?: any }>(
        '/dashboard/close-position',
        params
      )
      return response
    } catch (error) {
      logger.error('closePosition error:', error)
      throw error
    }
  },

  async getBalancesSummary(): Promise<BalanceData> {
    try {
      const data = await api.get<BalanceData>('/dashboard/balances')
      if (!data) {
        throw new Error('No data received from API')
      }
      return data
    } catch (error) {
      logger.error('getBalancesSummary error:', error)
      throw error
    }
  },

  async getPnlChart(days: number = 7): Promise<Array<{ date: string; pnl: number; positions: number }>> {
    return await api.get<Array<{ date: string; pnl: number; positions: number }>>(`/dashboard/pnl-chart?days=${days}`)
  },

  async getSpotBalances(exchangeAccountId: string): Promise<SpotBalancesData> {
    try {
      const data = await api.get<SpotBalancesData>(`/dashboard/spot-balances/${exchangeAccountId}`)
      return data
    } catch (error) {
      logger.error('getSpotBalances error:', error)
      throw error
    }
  }
}