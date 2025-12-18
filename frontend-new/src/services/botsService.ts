/**
 * Bots Service
 * Service for managing copy-trading bots and subscriptions
 */
import { apiClient } from '@/lib/api'

// ============================================================================
// Types & Interfaces
// ============================================================================

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

// Exchange-specific subscription data (for multi-exchange support)
export interface ExchangeSubscription {
  subscription_id: string
  exchange_account_id: string
  exchange: string
  account_name: string
  status: 'active' | 'paused' | 'cancelled'
  config_group_id: string | null
  custom_leverage: number | null
  custom_margin_usd: number | null
  custom_stop_loss_pct: number | null
  custom_take_profit_pct: number | null
  max_daily_loss_usd: number | null
  max_concurrent_positions: number | null
  current_daily_loss_usd: number
  current_positions: number
  total_signals_received: number
  total_orders_executed: number
  total_orders_failed: number
  total_pnl_usd: number
  win_count: number
  loss_count: number
  created_at: string | null
  last_signal_at: string | null
}

// Bot subscription with multi-exchange support
export interface BotSubscription {
  // Bot info
  bot_id: string
  bot_name: string
  bot_description: string
  market_type: 'spot' | 'futures'
  default_leverage: number
  default_margin_usd: number | null
  default_stop_loss_pct: number | null
  default_take_profit_pct: number | null
  // Multi-exchange data
  exchanges: ExchangeSubscription[]
  exchanges_count: number
  // Aggregated totals
  status: 'active' | 'paused' | 'cancelled'
  total_pnl_usd: number
  total_win_count: number
  total_loss_count: number
  total_signals_received: number
  total_orders_executed: number
  // Backwards compatibility (for single exchange)
  id?: string  // subscription_id of first exchange
  exchange?: string
  account_name?: string
  // Additional fields used in UI
  last_signal_at?: string | null
  created_at?: string | null
  win_count?: number  // deprecated, use total_win_count
  loss_count?: number  // deprecated, use total_loss_count
}

export interface BotSignalExecution {
  id: string
  status: 'pending' | 'success' | 'failed' | 'skipped'
  exchange_order_id: string | null
  executed_price: number | null
  executed_quantity: number | null
  error_message: string | null
  execution_time_ms: number | null
  created_at: string
  ticker: string
  action: string
}

export interface CreateSubscriptionData {
  bot_id: string
  exchange_account_id: string
  custom_leverage?: number
  custom_margin_usd?: number
  custom_stop_loss_pct?: number
  custom_take_profit_pct?: number
  max_daily_loss_usd: number
  max_concurrent_positions: number
}

// Config per exchange (for multi-exchange with individual configs)
export interface ExchangeConfig {
  exchange_account_id: string
  custom_leverage?: number
  custom_margin_usd?: number
  custom_stop_loss_pct?: number
  custom_take_profit_pct?: number
  max_daily_loss_usd: number
  max_concurrent_positions: number
}

// Multi-exchange subscription data (up to 3 exchanges)
export interface CreateMultiExchangeSubscriptionData {
  bot_id: string
  exchange_account_ids: string[]  // max 3
  use_same_config: boolean
  // Shared config (when use_same_config=true)
  custom_leverage?: number
  custom_margin_usd?: number
  custom_stop_loss_pct?: number
  custom_take_profit_pct?: number
  max_daily_loss_usd: number
  max_concurrent_positions: number
  // Individual configs (when use_same_config=false)
  individual_configs?: ExchangeConfig[]
}

export interface UpdateSubscriptionData {
  status?: 'active' | 'paused' | 'cancelled'
  custom_leverage?: number
  custom_margin_usd?: number
  custom_stop_loss_pct?: number
  custom_take_profit_pct?: number
  max_daily_loss_usd?: number
  max_concurrent_positions?: number
}

export interface PnLHistoryPoint {
  date: string
  daily_pnl: number
  cumulative_pnl: number
  daily_wins: number
  daily_losses: number
  cumulative_wins: number
  cumulative_losses: number
  win_rate: number
}

export interface PerformanceSummary {
  total_pnl_usd: number
  win_rate: number
  total_wins: number
  total_losses: number
  total_trades: number  // All trades (open + closed)
  closed_trades?: number  // Only closed trades
  open_trades?: number  // Currently open trades
  total_signals: number
  total_orders_executed: number
  period_label?: string
  subscribed_at?: string | null
}

export interface PositionData {
  symbol: string
  side: string
  entry_price: number
  size: number
  unrealized_pnl: number
  entry_time: string | null
}

export interface SubscriptionPerformance {
  subscription_id: string
  bot_name: string
  days_filter: number
  // Filtered statistics based on date range
  filtered_summary: PerformanceSummary
  // All-time statistics
  all_time_summary: PerformanceSummary
  // Current state (REAL-TIME from exchange)
  current_state: {
    current_positions: number
    max_concurrent_positions: number
    positions_data?: PositionData[]  // Detailed position info
    today_loss_usd?: number  // Today's loss from exchange (real-time)
    max_daily_loss_usd?: number  // Max daily loss limit
  }
  pnl_history: PnLHistoryPoint[]
}

// ============================================================================
// Bots Service Class
// ============================================================================

class BotsService {
  /**
   * Get all available bots (active bots that clients can subscribe to)
   */
  async getAvailableBots(): Promise<Bot[]> {
    const response = await apiClient.getAxiosInstance().get('/bot-subscriptions/available-bots')

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Get all bots (admin view - includes all statuses)
   */
  async getAllBots(): Promise<Bot[]> {
    const response = await apiClient.getAxiosInstance().get('/bots')

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Get bot details by ID
   */
  async getBotById(botId: string): Promise<Bot | null> {
    try {
      const response = await apiClient.getAxiosInstance().get(`/bots/${botId}`)

      if (response.data?.success && response.data?.data) {
        return response.data.data
      }

      return null
    } catch (error) {
      console.error('Error fetching bot:', error)
      return null
    }
  }

  /**
   * Get user's bot subscriptions
   */
  async getMySubscriptions(userId: string): Promise<BotSubscription[]> {
    const response = await apiClient.getAxiosInstance().get('/bot-subscriptions/my-subscriptions', {
      params: { user_id: userId }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Get subscription details
   */
  async getSubscriptionById(subscriptionId: string, userId: string): Promise<any> {
    const response = await apiClient.getAxiosInstance().get(`/bot-subscriptions/${subscriptionId}`, {
      params: { user_id: userId }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return null
  }

  /**
   * Subscribe to a bot (single exchange)
   */
  async subscribeToBot(userId: string, data: CreateSubscriptionData): Promise<{ subscription_id: string }> {
    const response = await apiClient.getAxiosInstance().post('/bot-subscriptions', data, {
      params: { user_id: userId }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error(response.data?.message || 'Failed to subscribe to bot')
  }

  /**
   * Subscribe to a bot with multiple exchanges (max 3)
   */
  async subscribeToBotMultiExchange(
    userId: string,
    data: CreateMultiExchangeSubscriptionData
  ): Promise<{ subscription_ids: string[]; config_group_id: string; exchanges_count: number }> {
    const response = await apiClient.getAxiosInstance().post('/bot-subscriptions/multi', data, {
      params: { user_id: userId }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error(response.data?.message || 'Failed to subscribe to bot with multiple exchanges')
  }

  /**
   * Update subscription configuration
   */
  async updateSubscription(
    subscriptionId: string,
    userId: string,
    data: UpdateSubscriptionData
  ): Promise<void> {
    await apiClient.getAxiosInstance().patch(`/bot-subscriptions/${subscriptionId}`, data, {
      params: { user_id: userId }
    })
  }

  /**
   * Unsubscribe from bot
   */
  async unsubscribeFromBot(subscriptionId: string, userId: string): Promise<void> {
    await apiClient.getAxiosInstance().delete(`/bot-subscriptions/${subscriptionId}`, {
      params: { user_id: userId }
    })
  }

  /**
   * Pause subscription (keep subscription but stop receiving signals)
   */
  async pauseSubscription(subscriptionId: string, userId: string): Promise<void> {
    await this.updateSubscription(subscriptionId, userId, { status: 'paused' })
  }

  /**
   * Resume subscription
   */
  async resumeSubscription(subscriptionId: string, userId: string): Promise<void> {
    await this.updateSubscription(subscriptionId, userId, { status: 'active' })
  }

  /**
   * Get subscription performance metrics and P&L history
   */
  async getSubscriptionPerformance(
    subscriptionId: string,
    userId: string,
    days: number = 30
  ): Promise<SubscriptionPerformance | null> {
    try {
      const response = await apiClient.getAxiosInstance().get(
        `/bot-subscriptions/${subscriptionId}/performance`,
        {
          params: { user_id: userId, days }
        }
      )

      if (response.data?.success && response.data?.data) {
        return response.data.data
      }

      return null
    } catch (error) {
      console.error('Error fetching subscription performance:', error)
      return null
    }
  }
}

export const botsService = new BotsService()
