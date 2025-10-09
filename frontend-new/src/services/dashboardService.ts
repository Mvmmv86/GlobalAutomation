import api from '@/lib/api'

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

export const dashboardService = {
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const response = await api.get('/dashboard/metrics')
    return response.data.data
  },

  async getBalancesSummary(): Promise<BalanceData> {
    try {
      console.log('🚀 getBalancesSummary: Making API call...')
      const data = await api.get<BalanceData>('/dashboard/balances')
      console.log('📡 getBalancesSummary: Data received:', data)

      if (!data) {
        throw new Error('No data received from API')
      }

      console.log('📊 getBalancesSummary: Returning:', data)
      return data
    } catch (error) {
      console.error('❌ getBalancesSummary: Error:', error)
      throw error
    }
  },

  async getPnlChart(days: number = 7): Promise<Array<{ date: string; pnl: number; positions: number }>> {
    const response = await api.get(`/dashboard/pnl-chart?days=${days}`)
    return response.data.data
  },

  async getSpotBalances(exchangeAccountId: string): Promise<SpotBalancesData> {
    try {
      console.log(`💰 getSpotBalances: Fetching for account ${exchangeAccountId}`)
      const data = await api.get<SpotBalancesData>(`/dashboard/spot-balances/${exchangeAccountId}`)
      console.log('✅ getSpotBalances: Data received:', data)
      return data
    } catch (error) {
      console.error('❌ getSpotBalances: Error:', error)
      throw error
    }
  }
}