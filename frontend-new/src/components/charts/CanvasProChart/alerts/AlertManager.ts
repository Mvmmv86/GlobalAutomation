/**
 * AlertManager - Gerenciador Central de Alertas
 * FASE 12: Sistema profissional de alertas e notificações
 */

import {
  AnyAlert,
  AlertType,
  AlertCondition,
  AlertStatus,
  AlertFrequency,
  NotificationType,
  AlertNotification,
  AlertManagerState,
  PriceAlert,
  IndicatorValueAlert,
  IndicatorCrossingAlert,
  VolumeAlert,
  generateAlertId,
  generateAlertMessage,
  isAlertExpired,
  canAlertTriggerAgain
} from './types'

export interface AlertManagerConfig {
  soundEnabled?: boolean
  soundVolume?: number
  maxNotifications?: number    // Máximo de notificações armazenadas
}

const DEFAULT_CONFIG: AlertManagerConfig = {
  soundEnabled: true,
  soundVolume: 0.5,
  maxNotifications: 100
}

export class AlertManager {
  private state: AlertManagerState
  private config: AlertManagerConfig
  private listeners: Map<string, Set<Function>>
  private lastCandleTimestamp: number | null = null
  private previousValues: Map<string, number> = new Map() // Para detectar cruzamentos

  constructor(config: Partial<AlertManagerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config }
    this.state = {
      alerts: [],
      notifications: [],
      soundEnabled: this.config.soundEnabled || true,
      soundVolume: this.config.soundVolume || 0.5
    }
    this.listeners = new Map()
  }

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  getState(): AlertManagerState {
    return { ...this.state }
  }

  getAlerts(): AnyAlert[] {
    return [...this.state.alerts]
  }

  getActiveAlerts(): AnyAlert[] {
    return this.state.alerts.filter(a => a.status === AlertStatus.ACTIVE && !isAlertExpired(a))
  }

  getNotifications(): AlertNotification[] {
    return [...this.state.notifications]
  }

  getUnreadNotifications(): AlertNotification[] {
    return this.state.notifications.filter(n => !n.read)
  }

  // ============================================================================
  // ALERT CRUD
  // ============================================================================

  /**
   * Adiciona um novo alerta
   */
  addAlert(alert: Omit<AnyAlert, 'id' | 'createdAt' | 'triggeredAt' | 'status'>): AnyAlert {
    const newAlert: AnyAlert = {
      ...alert,
      id: generateAlertId(alert.type),
      status: AlertStatus.ACTIVE,
      createdAt: Date.now(),
      triggeredAt: null
    } as AnyAlert

    this.state.alerts.push(newAlert)
    console.log(`✅ [AlertManager] Added alert: ${newAlert.type} (${newAlert.id})`)
    this.emit('alertAdded', newAlert)
    return newAlert
  }

  /**
   * Remove um alerta
   */
  removeAlert(id: string): boolean {
    const index = this.state.alerts.findIndex(a => a.id === id)
    if (index === -1) return false

    const alert = this.state.alerts[index]
    this.state.alerts.splice(index, 1)
    console.log(`🗑️ [AlertManager] Removed alert: ${id}`)
    this.emit('alertRemoved', alert)
    return true
  }

  /**
   * Atualiza um alerta
   */
  updateAlert(id: string, updates: Partial<AnyAlert>): boolean {
    const index = this.state.alerts.findIndex(a => a.id === id)
    if (index === -1) return false

    this.state.alerts[index] = {
      ...this.state.alerts[index],
      ...updates
    }

    console.log(`🔄 [AlertManager] Updated alert: ${id}`)
    this.emit('alertUpdated', this.state.alerts[index])
    return true
  }

  /**
   * Limpa todos os alertas
   */
  clearAlerts(): void {
    const count = this.state.alerts.length
    this.state.alerts = []
    console.log(`🧹 [AlertManager] Cleared ${count} alerts`)
    this.emit('alertsCleared')
  }

  /**
   * Habilita/desabilita um alerta
   */
  toggleAlert(id: string, enabled: boolean): boolean {
    const status = enabled ? AlertStatus.ACTIVE : AlertStatus.DISABLED
    return this.updateAlert(id, { status })
  }

  // ============================================================================
  // ALERT MONITORING
  // ============================================================================

  /**
   * Verifica todos os alertas ativos com os dados atuais
   */
  checkAlerts(data: {
    candles: any[]
    price: number
    indicators?: Map<string, number[]>
    drawings?: any[]
  }): void {
    if (data.candles.length === 0) return

    const latestCandle = data.candles[data.candles.length - 1]
    const currentTimestamp = latestCandle.openTime || latestCandle.timestamp || Date.now()

    // Detectar novo candle para ONCE_PER_BAR
    const isNewCandle = this.lastCandleTimestamp !== currentTimestamp
    if (isNewCandle) {
      this.lastCandleTimestamp = currentTimestamp
    }

    const activeAlerts = this.getActiveAlerts()

    for (const alert of activeAlerts) {
      // Verificar se pode disparar
      if (!canAlertTriggerAgain(alert)) continue

      // Verificar se é novo candle para ONCE_PER_BAR
      if (alert.frequency === AlertFrequency.ONCE_PER_BAR && !isNewCandle) continue

      // Verificar condição específica do alerta
      const shouldTrigger = this.evaluateAlert(alert, data)

      if (shouldTrigger) {
        this.triggerAlert(alert, data.price, latestCandle)
      }
    }
  }

  /**
   * Avalia se um alerta deve ser disparado
   */
  private evaluateAlert(alert: AnyAlert, data: {
    candles: any[]
    price: number
    indicators?: Map<string, number[]>
    drawings?: any[]
  }): boolean {
    switch (alert.type) {
      case AlertType.PRICE:
        return this.evaluatePriceAlert(alert as PriceAlert, data.price)

      case AlertType.INDICATOR_VALUE:
        return this.evaluateIndicatorValueAlert(alert as IndicatorValueAlert, data.indicators)

      case AlertType.INDICATOR_CROSSING:
        return this.evaluateIndicatorCrossingAlert(alert as IndicatorCrossingAlert, data.indicators)

      case AlertType.VOLUME:
        return this.evaluateVolumeAlert(alert as VolumeAlert, data.candles)

      // TODO: Implementar outros tipos de alertas
      default:
        console.warn(`⚠️ [AlertManager] Alert type ${alert.type} not implemented yet`)
        return false
    }
  }

  /**
   * Avalia alerta de preço
   */
  private evaluatePriceAlert(alert: PriceAlert, currentPrice: number): boolean {
    switch (alert.condition) {
      case AlertCondition.ABOVE:
        return currentPrice > alert.targetPrice

      case AlertCondition.BELOW:
        return currentPrice < alert.targetPrice

      default:
        return false
    }
  }

  /**
   * Avalia alerta de valor de indicador
   */
  private evaluateIndicatorValueAlert(
    alert: IndicatorValueAlert,
    indicators?: Map<string, number[]>
  ): boolean {
    if (!indicators) return false

    const values = indicators.get(alert.indicatorId)
    if (!values || values.length === 0) return false

    const currentValue = values[values.length - 1]
    if (isNaN(currentValue)) return false

    const tolerance = alert.tolerance || 0

    switch (alert.condition) {
      case AlertCondition.ABOVE:
        return currentValue > alert.targetValue

      case AlertCondition.BELOW:
        return currentValue < alert.targetValue

      case AlertCondition.EQUALS:
        return Math.abs(currentValue - alert.targetValue) <= tolerance

      default:
        return false
    }
  }

  /**
   * Avalia cruzamento entre indicadores
   */
  private evaluateIndicatorCrossingAlert(
    alert: IndicatorCrossingAlert,
    indicators?: Map<string, number[]>
  ): boolean {
    if (!indicators) return false

    const values1 = indicators.get(alert.indicator1Id)
    const values2 = indicators.get(alert.indicator2Id)

    if (!values1 || !values2 || values1.length < 2 || values2.length < 2) return false

    const current1 = values1[values1.length - 1]
    const previous1 = values1[values1.length - 2]
    const current2 = values2[values2.length - 1]
    const previous2 = values2[values2.length - 2]

    if (isNaN(current1) || isNaN(previous1) || isNaN(current2) || isNaN(previous2)) return false

    const crossedUp = previous1 <= previous2 && current1 > current2
    const crossedDown = previous1 >= previous2 && current1 < current2

    switch (alert.condition) {
      case AlertCondition.CROSSES_UP:
        return crossedUp

      case AlertCondition.CROSSES_DOWN:
        return crossedDown

      default:
        return false
    }
  }

  /**
   * Avalia alerta de volume
   */
  private evaluateVolumeAlert(alert: VolumeAlert, candles: any[]): boolean {
    if (candles.length === 0) return false

    const latestCandle = candles[candles.length - 1]
    const currentVolume = parseFloat(latestCandle.volume || latestCandle.v || 0)

    switch (alert.condition) {
      case AlertCondition.ABOVE:
        return currentVolume > alert.targetValue

      case AlertCondition.BELOW:
        return currentVolume < alert.targetValue

      case AlertCondition.PERCENT_CHANGE: {
        // Calcular média de volume
        const lookback = alert.lookbackPeriod || 20
        if (candles.length < lookback) return false

        let sumVolume = 0
        for (let i = candles.length - lookback - 1; i < candles.length - 1; i++) {
          const vol = parseFloat(candles[i].volume || candles[i].v || 0)
          sumVolume += vol
        }
        const avgVolume = sumVolume / lookback

        const percentChange = ((currentVolume - avgVolume) / avgVolume) * 100
        return percentChange >= alert.targetValue
      }

      default:
        return false
    }
  }

  /**
   * Dispara um alerta
   */
  private triggerAlert(alert: AnyAlert, price?: number, candle?: any): void {
    console.log(`🚨 [AlertManager] Alert triggered: ${alert.type} (${alert.id})`)

    // Atualizar status do alerta
    this.updateAlert(alert.id, {
      triggeredAt: Date.now(),
      status: alert.frequency === AlertFrequency.ONCE ? AlertStatus.TRIGGERED : AlertStatus.ACTIVE
    })

    // Criar notificação
    const notification: AlertNotification = {
      id: `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      alertId: alert.id,
      alert,
      triggeredAt: Date.now(),
      message: generateAlertMessage(alert, price),
      type: alert.notificationTypes[0] || NotificationType.VISUAL,
      read: false,
      price,
      candle
    }

    // Adicionar notificação
    this.state.notifications.push(notification)

    // Limitar número de notificações
    if (this.state.notifications.length > (this.config.maxNotifications || 100)) {
      this.state.notifications.shift()
    }

    // Emitir eventos
    this.emit('alertTriggered', { alert, notification })

    // Processar notificações
    for (const type of alert.notificationTypes) {
      this.processNotification(notification, type)
    }
  }

  /**
   * Processa uma notificação específica
   */
  private processNotification(notification: AlertNotification, type: NotificationType): void {
    switch (type) {
      case NotificationType.VISUAL:
        this.emit('visualNotification', notification)
        break

      case NotificationType.SOUND:
        if (this.state.soundEnabled) {
          this.playAlertSound()
        }
        break

      case NotificationType.POPUP:
        this.emit('popupNotification', notification)
        break

      case NotificationType.EMAIL:
        console.log(`📧 [AlertManager] Email notification not implemented yet`)
        break

      case NotificationType.WEBHOOK:
        console.log(`🔗 [AlertManager] Webhook notification not implemented yet`)
        break
    }
  }

  /**
   * Toca som de alerta
   */
  private playAlertSound(): void {
    try {
      // Criar áudio context
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      // Configurar som
      oscillator.type = 'sine'
      oscillator.frequency.value = 800 // Hz
      gainNode.gain.value = this.state.soundVolume

      // Tocar por 200ms
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.2)
    } catch (error) {
      console.error('❌ [AlertManager] Error playing sound:', error)
    }
  }

  // ============================================================================
  // NOTIFICATION MANAGEMENT
  // ============================================================================

  /**
   * Marca notificação como lida
   */
  markAsRead(notificationId: string): boolean {
    const notif = this.state.notifications.find(n => n.id === notificationId)
    if (!notif) return false

    notif.read = true
    this.emit('notificationRead', notif)
    return true
  }

  /**
   * Marca todas as notificações como lidas
   */
  markAllAsRead(): void {
    this.state.notifications.forEach(n => n.read = true)
    this.emit('allNotificationsRead')
  }

  /**
   * Remove notificação
   */
  removeNotification(notificationId: string): boolean {
    const index = this.state.notifications.findIndex(n => n.id === notificationId)
    if (index === -1) return false

    this.state.notifications.splice(index, 1)
    this.emit('notificationRemoved', notificationId)
    return true
  }

  /**
   * Limpa todas as notificações
   */
  clearNotifications(): void {
    const count = this.state.notifications.length
    this.state.notifications = []
    console.log(`🧹 [AlertManager] Cleared ${count} notifications`)
    this.emit('notificationsCleared')
  }

  // ============================================================================
  // SETTINGS
  // ============================================================================

  setSoundEnabled(enabled: boolean): void {
    this.state.soundEnabled = enabled
    this.emit('soundSettingChanged', enabled)
  }

  setSoundVolume(volume: number): void {
    this.state.soundVolume = Math.max(0, Math.min(1, volume))
    this.emit('volumeChanged', this.state.soundVolume)
  }

  // ============================================================================
  // SERIALIZATION
  // ============================================================================

  exportAlerts(): string {
    return JSON.stringify({
      version: '1.0',
      alerts: this.state.alerts,
      timestamp: Date.now()
    })
  }

  importAlerts(json: string): boolean {
    try {
      const data = JSON.parse(json)
      if (!data.alerts || !Array.isArray(data.alerts)) {
        console.error('❌ [AlertManager] Invalid import data')
        return false
      }

      this.state.alerts = data.alerts
      console.log(`📥 [AlertManager] Imported ${data.alerts.length} alerts`)
      this.emit('alertsImported', data.alerts)
      return true
    } catch (error) {
      console.error('❌ [AlertManager] Import failed:', error)
      return false
    }
  }

  // ============================================================================
  // EVENT SYSTEM
  // ============================================================================

  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)
  }

  off(event: string, callback: Function): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.delete(callback)
    }
  }

  private emit(event: string, ...args: any[]): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(cb => cb(...args))
    }
  }
}
