/**
 * Indicator Alerts Service
 * Service for managing indicator signal alerts
 */
import { apiClient } from '@/lib/api'

// ============================================================================
// Types & Interfaces
// ============================================================================

export type IndicatorType =
  | 'nadaraya_watson'
  | 'tpo'
  | 'rsi'
  | 'macd'
  | 'bollinger'
  | 'ema_cross'
  | 'volume_profile'
  | 'custom'

export type SignalType = 'buy' | 'sell' | 'both'

export type AlertTimeframe =
  | '1m' | '3m' | '5m' | '15m' | '30m'
  | '1h' | '2h' | '4h' | '6h' | '8h' | '12h'
  | '1d' | '3d' | '1w' | '1M'

export type AlertSoundType =
  | 'default'
  | 'bell'
  | 'chime'
  | 'alert'
  | 'alarm'
  | 'cash'
  | 'success'
  | 'notification'
  | 'none'

export interface IndicatorAlert {
  id: string
  indicator_type: IndicatorType
  symbol: string
  timeframe: AlertTimeframe
  signal_type: SignalType
  indicator_params: Record<string, unknown> | null
  message_template: string
  push_enabled: boolean
  email_enabled: boolean
  sound_type: AlertSoundType
  is_active: boolean
  last_triggered_at: string | null
  trigger_count: number
  cooldown_seconds: number
  created_at: string
  updated_at: string
}

export interface CreateAlertData {
  indicator_type: IndicatorType
  symbol: string
  timeframe: AlertTimeframe
  signal_type?: SignalType
  indicator_params?: Record<string, unknown>
  message_template?: string
  push_enabled?: boolean
  email_enabled?: boolean
  sound_type?: AlertSoundType
  cooldown_seconds?: number
}

export interface UpdateAlertData {
  signal_type?: SignalType
  indicator_params?: Record<string, unknown>
  message_template?: string
  push_enabled?: boolean
  email_enabled?: boolean
  sound_type?: AlertSoundType
  cooldown_seconds?: number
  is_active?: boolean
}

export interface AlertHistoryEntry {
  id: string
  signal_type: string
  signal_price: number | null
  push_sent: boolean
  email_sent: boolean
  metadata: Record<string, unknown> | null
  triggered_at: string
}

export interface IndicatorMeta {
  type: IndicatorType
  name: string
  description: string
  has_signals: boolean
  params: Record<string, {
    type: string
    default: number
    min?: number
    max?: number
  }>
}

export interface TimeframeMeta {
  value: AlertTimeframe
  label: string
}

export interface SoundMeta {
  value: AlertSoundType
  label: string
}

export interface AvailableIndicators {
  indicators: IndicatorMeta[]
  timeframes: TimeframeMeta[]
  sounds: SoundMeta[]
}

// ============================================================================
// Indicator Alerts Service Class
// ============================================================================

class IndicatorAlertsService {
  /**
   * Get all indicator alerts for the user
   */
  async getAlerts(filters?: {
    indicator_type?: IndicatorType
    symbol?: string
    active_only?: boolean
  }): Promise<IndicatorAlert[]> {
    const params: Record<string, string | boolean> = {}

    if (filters?.indicator_type) params.indicator_type = filters.indicator_type
    if (filters?.symbol) params.symbol = filters.symbol
    if (filters?.active_only) params.active_only = true

    const response = await apiClient.getAxiosInstance().get('/indicator-alerts', {
      params
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Get a specific alert by ID
   */
  async getAlertById(alertId: string): Promise<IndicatorAlert | null> {
    try {
      const response = await apiClient.getAxiosInstance().get(`/indicator-alerts/${alertId}`)

      if (response.data?.success && response.data?.data) {
        return response.data.data
      }

      return null
    } catch (error) {
      console.error('Error fetching alert:', error)
      return null
    }
  }

  /**
   * Create a new indicator alert
   */
  async createAlert(data: CreateAlertData): Promise<{ id: string }> {
    const response = await apiClient.getAxiosInstance().post('/indicator-alerts', data)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error(response.data?.message || 'Failed to create alert')
  }

  /**
   * Update an existing alert
   */
  async updateAlert(alertId: string, data: UpdateAlertData): Promise<void> {
    await apiClient.getAxiosInstance().put(`/indicator-alerts/${alertId}`, data)
  }

  /**
   * Delete an alert
   */
  async deleteAlert(alertId: string): Promise<void> {
    await apiClient.getAxiosInstance().delete(`/indicator-alerts/${alertId}`)
  }

  /**
   * Toggle alert active state
   */
  async toggleAlert(alertId: string): Promise<{ is_active: boolean }> {
    const response = await apiClient.getAxiosInstance().post(`/indicator-alerts/${alertId}/toggle`)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error(response.data?.message || 'Failed to toggle alert')
  }

  /**
   * Get alert trigger history
   */
  async getAlertHistory(alertId: string, limit: number = 50): Promise<AlertHistoryEntry[]> {
    const response = await apiClient.getAxiosInstance().get(
      `/indicator-alerts/${alertId}/history`,
      { params: { limit } }
    )

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Get available indicators metadata
   */
  async getAvailableIndicators(): Promise<AvailableIndicators> {
    const response = await apiClient.getAxiosInstance().get('/indicator-alerts/meta/available-indicators')

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    // Return defaults if API fails
    return {
      indicators: [],
      timeframes: [],
      sounds: []
    }
  }
}

export const indicatorAlertsService = new IndicatorAlertsService()
