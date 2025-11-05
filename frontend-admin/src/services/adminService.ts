/**
 * Admin Service
 * Service for admin operations: dashboard stats, users, bots management
 */
import { apiClient } from '@/lib/api'

// ============================================================================
// Types & Interfaces
// ============================================================================

export interface DashboardStats {
  overview: {
    total_users: number
    total_exchanges: number
    total_bots: number
    active_bots: number
    total_webhooks: number
    active_webhooks: number
    total_subscriptions: number
    active_subscriptions: number
    total_signals_sent: number
    total_orders_executed: number
    total_pnl_usd: number
  }
  recent_activity: {
    new_users_7d: number
    new_subscriptions_7d: number
    signals_sent_7d: number
  }
  top_bots: TopBot[]
}

export interface TopBot {
  id: string
  name: string
  total_subscribers: number
  total_signals_sent: number
  avg_win_rate: number | null
  avg_pnl_pct: number | null
}

export interface User {
  id: string
  email: string
  name: string
  created_at: string
  last_login: string | null
  total_exchanges: number
  total_subscriptions: number
  total_webhooks: number
}

export interface UserDetails extends User {
  is_admin: boolean
  exchanges: ExchangeAccount[]
  subscriptions: UserSubscription[]
  webhooks: UserWebhook[]
}

export interface ExchangeAccount {
  id: string
  name: string
  exchange: string
  status: string
  created_at: string
}

export interface UserSubscription {
  id: string
  status: string
  created_at: string
  bot_name: string
  total_signals_received: number
  total_pnl_usd: number
}

export interface UserWebhook {
  id: string
  name: string
  status: string
  total_deliveries: number
  created_at: string
}

export interface Bot {
  id: string
  name: string
  description: string
  market_type: 'spot' | 'futures'
  status: 'active' | 'paused' | 'archived'
  master_webhook_path: string
  default_leverage: number
  default_margin_usd: number
  default_stop_loss_pct: number
  default_take_profit_pct: number
  total_subscribers: number
  total_signals_sent: number
  avg_win_rate: number | null
  avg_pnl_pct: number | null
  created_at: string
  updated_at: string
}

export interface BotCreateData {
  name: string
  description: string
  market_type: 'spot' | 'futures'
  allowed_directions?: 'buy_only' | 'sell_only' | 'both'
  status?: 'active' | 'paused' | 'archived'
  master_webhook_path: string
  master_secret?: string  // Optional now - authentication via webhook_path
  default_leverage: number
  default_margin_usd: number
  default_stop_loss_pct: number
  default_take_profit_pct: number
}

export interface BotUpdateData {
  name?: string
  description?: string
  status?: 'active' | 'paused' | 'archived'
  default_leverage?: number
  default_margin_usd?: number
  default_stop_loss_pct?: number
  default_take_profit_pct?: number
}

export interface BotStats {
  bot: Bot
  subscription_stats: {
    total_subscriptions: number
    active_subscriptions: number
    total_signals_received: number
    total_orders_executed: number
    total_pnl: number
  }
  recent_signals: BotSignal[]
}

export interface BotSignal {
  id: string
  ticker: string
  action: string
  successful_executions: number
  failed_executions: number
  created_at: string
}

// ============================================================================
// Admin Service Class
// ============================================================================

class AdminService {
  private adminUserId: string | null = null

  setAdminUserId(userId: string) {
    this.adminUserId = userId
  }

  getAdminUserId(): string {
    if (!this.adminUserId) {
      // Try to get from auth context or localStorage
      const stored = localStorage.getItem('admin_user_id')
      if (stored) {
        this.adminUserId = stored
        return stored
      }
      throw new Error('Admin user ID not set')
    }
    return this.adminUserId
  }

  /**
   * Get dashboard statistics
   */
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await apiClient.instance.get('/admin/dashboard/stats', {
      params: { admin_user_id: this.getAdminUserId() }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error('Failed to fetch dashboard stats')
  }

  /**
   * Get all users with pagination
   */
  async getUsers(params?: {
    limit?: number
    offset?: number
    search?: string
  }): Promise<{ users: User[]; total: number; limit: number; offset: number }> {
    const response = await apiClient.instance.get('/admin/users', {
      params: {
        ...params,
        admin_user_id: this.getAdminUserId()
      }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return { users: [], total: 0, limit: 50, offset: 0 }
  }

  /**
   * Get user details by ID
   */
  async getUserDetails(userId: string): Promise<UserDetails> {
    const response = await apiClient.instance.get(`/admin/users/${userId}`, {
      params: { admin_user_id: this.getAdminUserId() }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error('User not found')
  }

  /**
   * Get all bots
   */
  async getAllBots(status?: string): Promise<Bot[]> {
    const params: any = {}
    if (status) params.status = status

    const response = await apiClient.instance.get('/bots', { params })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Create new bot
   */
  async createBot(data: BotCreateData): Promise<{ bot_id: string; webhook_url: string }> {
    console.log('🔍 adminService.createBot called with:', data)
    console.log('🔍 Admin user ID:', this.getAdminUserId())

    // Remove campos que o backend não aceita
    const { status, master_secret, ...cleanData } = data
    console.log('📤 Sending to backend:', cleanData)

    try {
      const response = await apiClient.instance.post('/admin/bots', cleanData, {
        params: { admin_user_id: this.getAdminUserId() }
      })

      console.log('✅ Response received:', response.data)

      if (response.data?.success && response.data?.data) {
        return response.data.data
      }

      throw new Error(response.data?.message || 'Failed to create bot')
    } catch (error: any) {
      console.error('❌ Error in createBot:', error)
      console.error('❌ Error response:', error.response?.data)
      console.error('❌ Error details:', JSON.stringify(error.response?.data, null, 2))
      throw error
    }
  }

  /**
   * Update bot
   */
  async updateBot(botId: string, data: BotUpdateData): Promise<void> {
    await apiClient.instance.put(`/admin/bots/${botId}`, data, {
      params: { admin_user_id: this.getAdminUserId() }
    })
  }

  /**
   * Delete (archive) bot
   */
  async deleteBot(botId: string): Promise<void> {
    await apiClient.instance.delete(`/admin/bots/${botId}`, {
      params: { admin_user_id: this.getAdminUserId() }
    })
  }

  /**
   * Get bot statistics
   */
  async getBotStats(botId: string): Promise<BotStats> {
    const response = await apiClient.instance.get(`/admin/bots/${botId}/stats`, {
      params: { admin_user_id: this.getAdminUserId() }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error('Failed to fetch bot stats')
  }
}

export const adminService = new AdminService()
