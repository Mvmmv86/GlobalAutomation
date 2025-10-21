import { apiClient } from '@/lib/api'

export interface WebhookData {
  id?: string
  name: string
  url_path: string
  secret?: string
  status: 'active' | 'paused' | 'disabled' | 'error'
  market_type?: 'spot' | 'futures'
  is_public?: boolean
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  max_retries?: number
  retry_delay_seconds?: number
  total_deliveries?: number
  successful_deliveries?: number
  failed_deliveries?: number
  success_rate?: number
  last_delivery_at?: string | null
  last_success_at?: string | null
  auto_pause_on_errors?: boolean
  error_threshold?: number
  consecutive_errors?: number
  // Trading parameters
  default_margin_usd?: number
  default_leverage?: number
  default_stop_loss_pct?: number
  default_take_profit_pct?: number
  user_id?: string
  created_at?: string
  updated_at?: string
}

export interface WebhookCreateData {
  name: string
  url_path: string
  secret?: string
  status?: 'active' | 'paused'
  market_type?: 'spot' | 'futures'
  is_public?: boolean
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  max_retries?: number
  retry_delay_seconds?: number
  // Trading parameters
  default_margin_usd?: number
  default_leverage?: number
  default_stop_loss_pct?: number
  default_take_profit_pct?: number
}

export interface WebhookUpdateData {
  name?: string
  status?: 'active' | 'paused' | 'disabled' | 'error'
  market_type?: 'spot' | 'futures'
  is_public?: boolean
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  max_retries?: number
  retry_delay_seconds?: number
  auto_pause_on_errors?: boolean
  error_threshold?: number
  // Trading parameters
  default_margin_usd?: number
  default_leverage?: number
  default_stop_loss_pct?: number
  default_take_profit_pct?: number
}

class WebhookService {
  /**
   * Buscar todos os webhooks
   * GET /api/v1/webhooks
   */
  async getWebhooks(status?: string): Promise<WebhookData[]> {
    const params = status ? { status } : {}
    const response = await apiClient.instance.get('/webhooks', { params })

    // Backend retorna { success: true, data: [...] }
    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    // Fallback se retornar array direto
    if (Array.isArray(response.data)) {
      return response.data
    }

    return []
  }

  /**
   * Buscar webhook específico
   * GET /api/v1/webhooks/{webhook_id}
   */
  async getWebhook(webhookId: string): Promise<WebhookData> {
    const response = await apiClient.instance.get(`/webhooks/${webhookId}`)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }

  /**
   * Criar novo webhook
   * POST /api/v1/webhooks
   */
  async createWebhook(data: WebhookCreateData): Promise<WebhookData> {
    const response = await apiClient.instance.post('/webhooks', data)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }

  /**
   * Atualizar webhook existente
   * PUT /api/v1/webhooks/{webhook_id}
   */
  async updateWebhook(webhookId: string, data: WebhookUpdateData): Promise<void> {
    await apiClient.instance.put(`/webhooks/${webhookId}`, data)
  }

  /**
   * Deletar webhook
   * DELETE /api/v1/webhooks/{webhook_id}
   */
  async deleteWebhook(webhookId: string): Promise<void> {
    await apiClient.instance.delete(`/webhooks/${webhookId}`)
  }

  /**
   * Pausar webhook (atalho para update status)
   */
  async pauseWebhook(webhookId: string): Promise<void> {
    await this.updateWebhook(webhookId, { status: 'paused' })
  }

  /**
   * Reativar webhook (atalho para update status)
   */
  async activateWebhook(webhookId: string): Promise<void> {
    await this.updateWebhook(webhookId, { status: 'active' })
  }

  /**
   * Desabilitar webhook (atalho para update status)
   */
  async disableWebhook(webhookId: string): Promise<void> {
    await this.updateWebhook(webhookId, { status: 'disabled' })
  }

  /**
   * Buscar trades executados por um webhook específico
   * GET /api/v1/webhooks/{webhook_id}/trades
   */
  async getWebhookTrades(webhookId: string, limit: number = 50): Promise<WebhookTradeData> {
    const response = await apiClient.instance.get(`/webhooks/${webhookId}/trades`, {
      params: { limit }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }
}

export interface WebhookTradeData {
  webhook_name: string
  trades: TradeItem[]
  total: number
}

export interface TradeItem {
  id: number
  date: string
  symbol: string
  side: string
  price: number
  quantity: number
  filled_quantity: number
  leverage: number
  margin_usd: number  // ✅ NEW: Margin in USDT
  status: 'open' | 'closed'
  order_status: string
  pnl: number
  exchange_order_id: string | null
  error: string | null
}

export const webhookService = new WebhookService()