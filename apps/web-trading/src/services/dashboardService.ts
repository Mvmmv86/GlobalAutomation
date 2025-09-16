import { apiClient } from '@/lib/api'

export interface DashboardAccount {
  id: string
  user_id: string
  name: string
  exchange: string
  apiKey: string
  testnet: boolean
  isDefault: boolean
  isActive: boolean
}

export interface DashboardPnL {
  total_pnl: number
  currency: string
}

export interface OrdersToday {
  count: number
  orders: any[]
  period: string
}

export interface ActivePositions {
  count: number
  positions: any[]
}

export interface WeeklyOrders {
  count: number
  period: string
}

export interface WebhooksCount {
  active_webhooks: number
  total_webhooks: number
  status: string
}

export interface AccountsCount {
  active_accounts: number
  total_accounts: number
  status: string
}

export interface SuccessRate {
  success_rate: number
  weekly_profit: number
  total_trades: number
  profitable_trades: number
  period: string
}

export interface RecentOrders {
  orders: any[]
  count: number
  period: string
}

class DashboardService {
  async getDefaultAccount(): Promise<DashboardAccount> {
    return apiClient.get<DashboardAccount>('/dashboard/default-account')
  }

  async getTotalPnL(): Promise<DashboardPnL> {
    return apiClient.get<DashboardPnL>('/dashboard/total-pnl')
  }

  async getOrdersToday(): Promise<OrdersToday> {
    return apiClient.get<OrdersToday>('/dashboard/orders-today')
  }

  async getActivePositions(): Promise<ActivePositions> {
    return apiClient.get<ActivePositions>('/dashboard/active-positions')
  }

  async getWeeklyOrders(): Promise<WeeklyOrders> {
    return apiClient.get<WeeklyOrders>('/dashboard/weekly-orders')
  }

  async getWebhooksCount(): Promise<WebhooksCount> {
    return apiClient.get<WebhooksCount>('/dashboard/webhooks-count')
  }

  async getAccountsCount(): Promise<AccountsCount> {
    return apiClient.get<AccountsCount>('/dashboard/accounts-count')
  }

  async getSuccessRate(): Promise<SuccessRate> {
    return apiClient.get<SuccessRate>('/dashboard/success-rate')
  }

  async getRecentOrders(): Promise<RecentOrders> {
    return apiClient.get<RecentOrders>('/dashboard/recent-orders')
  }
}

export const dashboardService = new DashboardService()