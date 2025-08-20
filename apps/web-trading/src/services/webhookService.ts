import { apiClient } from '@/lib/api'
import { Webhook } from '@/types/trading'

class WebhookService {
  async getWebhooks(): Promise<Webhook[]> {
    return apiClient.get<Webhook[]>('/webhooks')
  }

  async createWebhook(data: {
    name: string
    isPublic?: boolean
    rateLimitPerMinute?: number
    rateLimitPerHour?: number
    allowedIps?: string
    requiredHeaders?: string
  }): Promise<Webhook> {
    return apiClient.post<Webhook>('/webhooks', data)
  }

  async updateWebhook(id: string, data: Partial<Webhook>): Promise<Webhook> {
    return apiClient.put<Webhook>(`/webhooks/${id}`, data)
  }

  async deleteWebhook(id: string): Promise<void> {
    return apiClient.delete(`/webhooks/${id}`)
  }

  async pauseWebhook(id: string): Promise<void> {
    return apiClient.post(`/webhooks/${id}/pause`)
  }

  async resumeWebhook(id: string): Promise<void> {
    return apiClient.post(`/webhooks/${id}/resume`)
  }

  async getWebhookStats(id: string, days: number = 30): Promise<any> {
    return apiClient.get(`/webhooks/${id}/stats?days=${days}`)
  }

  async getWebhookDeliveries(id: string): Promise<any[]> {
    return apiClient.get(`/webhooks/${id}/deliveries`)
  }
}

export const webhookService = new WebhookService()