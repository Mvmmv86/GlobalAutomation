import { api } from '@/lib/api'

export interface WebhookData {
  id?: string
  name: string
  url_path: string
  secret?: string
  status: 'active' | 'paused' | 'disabled' | 'error'
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
  user_id?: string
  created_at?: string
  updated_at?: string
}

export interface WebhookCreateData {
  name: string
  url_path: string
  secret?: string
  status?: 'active' | 'paused'
  is_public?: boolean
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  max_retries?: number
  retry_delay_seconds?: number
}

export interface WebhookUpdateData {
  name?: string
  status?: 'active' | 'paused' | 'disabled' | 'error'
  is_public?: boolean
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  max_retries?: number
  retry_delay_seconds?: number
  auto_pause_on_errors?: boolean
  error_threshold?: number
}

class WebhookService {
  /**
   * Buscar todos os webhooks
   * GET /api/v1/webhooks
   */
  async getWebhooks(status?: string): Promise<WebhookData[]> {
    const params = status ? { status } : {}
    const response = await api.get('/api/v1/webhooks', { params })

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
    const response = await api.get(`/api/v1/webhooks/${webhookId}`)

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
    const response = await api.post('/api/v1/webhooks', data)

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
    await api.put(`/api/v1/webhooks/${webhookId}`, data)
  }

  /**
   * Deletar webhook
   * DELETE /api/v1/webhooks/{webhook_id}
   */
  async deleteWebhook(webhookId: string): Promise<void> {
    await api.delete(`/api/v1/webhooks/${webhookId}`)
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
}

export const webhookService = new WebhookService()