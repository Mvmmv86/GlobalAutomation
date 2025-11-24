/**
 * Alert System Types - Sistema Profissional de Alertas
 * FASE 12: Price Alerts, Indicator Alerts, Visual/Audio Notifications
 */

// ============================================================================
// ENUMS
// ============================================================================

export enum AlertType {
  PRICE = 'PRICE',                           // Alerta de preço (acima/abaixo)
  PRICE_CROSSING = 'PRICE_CROSSING',         // Preço cruzando linha (H-Line, Trendline)
  INDICATOR_VALUE = 'INDICATOR_VALUE',       // Indicador atingindo valor específico
  INDICATOR_CROSSING = 'INDICATOR_CROSSING', // Indicadores se cruzando
  CANDLE_PATTERN = 'CANDLE_PATTERN',         // Padrões de candle
  VOLUME = 'VOLUME'                          // Volume anormal
}

export enum AlertCondition {
  ABOVE = 'ABOVE',             // Acima de
  BELOW = 'BELOW',             // Abaixo de
  CROSSES_UP = 'CROSSES_UP',   // Cruza para cima
  CROSSES_DOWN = 'CROSSES_DOWN', // Cruza para baixo
  EQUALS = 'EQUALS',           // Igual a (com tolerância)
  PERCENT_CHANGE = 'PERCENT_CHANGE' // Mudança percentual
}

export enum AlertFrequency {
  ONCE = 'ONCE',               // Dispara apenas uma vez
  ONCE_PER_BAR = 'ONCE_PER_BAR', // Uma vez por candle
  EVERY_TIME = 'EVERY_TIME'    // Toda vez que condição for verdadeira
}

export enum AlertStatus {
  ACTIVE = 'ACTIVE',           // Alerta ativo, monitorando
  TRIGGERED = 'TRIGGERED',     // Alerta disparado
  EXPIRED = 'EXPIRED',         // Alerta expirado
  DISABLED = 'DISABLED'        // Alerta desabilitado
}

export enum NotificationType {
  VISUAL = 'VISUAL',           // Notificação visual no gráfico
  SOUND = 'SOUND',             // Som/beep
  POPUP = 'POPUP',             // Pop-up modal
  EMAIL = 'EMAIL',             // Email (futuro)
  WEBHOOK = 'WEBHOOK'          // Webhook (futuro)
}

// ============================================================================
// BASE INTERFACES
// ============================================================================

/**
 * Interface base para todos os alertas
 */
export interface BaseAlert {
  id: string
  type: AlertType
  name: string
  description?: string
  symbol: string               // Par de moedas (ex: BTCUSDT)
  interval: string             // Intervalo (ex: 1h, 5m)
  status: AlertStatus
  frequency: AlertFrequency
  notificationTypes: NotificationType[]
  createdAt: number
  triggeredAt: number | null
  expiresAt: number | null     // Timestamp de expiração (null = sem expiração)
  metadata?: Record<string, any>
}

// ============================================================================
// SPECIFIC ALERT INTERFACES
// ============================================================================

/**
 * Alerta de preço simples (acima/abaixo)
 */
export interface PriceAlert extends BaseAlert {
  type: AlertType.PRICE
  condition: AlertCondition.ABOVE | AlertCondition.BELOW
  targetPrice: number
}

/**
 * Alerta de preço cruzando uma linha de desenho
 */
export interface PriceCrossingAlert extends BaseAlert {
  type: AlertType.PRICE_CROSSING
  condition: AlertCondition.CROSSES_UP | AlertCondition.CROSSES_DOWN
  drawingId: string            // ID do desenho (HLine, TrendLine, etc)
}

/**
 * Alerta de valor de indicador
 */
export interface IndicatorValueAlert extends BaseAlert {
  type: AlertType.INDICATOR_VALUE
  condition: AlertCondition
  indicatorId: string          // ID do indicador
  targetValue: number
  tolerance?: number           // Tolerância para EQUALS
}

/**
 * Alerta de cruzamento entre indicadores
 */
export interface IndicatorCrossingAlert extends BaseAlert {
  type: AlertType.INDICATOR_CROSSING
  condition: AlertCondition.CROSSES_UP | AlertCondition.CROSSES_DOWN
  indicator1Id: string
  indicator2Id: string
}

/**
 * Alerta de padrão de candle
 */
export interface CandlePatternAlert extends BaseAlert {
  type: AlertType.CANDLE_PATTERN
  pattern: CandlePattern
}

export enum CandlePattern {
  DOJI = 'DOJI',
  HAMMER = 'HAMMER',
  INVERTED_HAMMER = 'INVERTED_HAMMER',
  BULLISH_ENGULFING = 'BULLISH_ENGULFING',
  BEARISH_ENGULFING = 'BEARISH_ENGULFING',
  MORNING_STAR = 'MORNING_STAR',
  EVENING_STAR = 'EVENING_STAR',
  SHOOTING_STAR = 'SHOOTING_STAR'
}

/**
 * Alerta de volume
 */
export interface VolumeAlert extends BaseAlert {
  type: AlertType.VOLUME
  condition: AlertCondition.ABOVE | AlertCondition.BELOW | AlertCondition.PERCENT_CHANGE
  targetValue: number          // Volume absoluto ou % acima da média
  lookbackPeriod?: number      // Períodos para calcular média (se PERCENT_CHANGE)
}

// ============================================================================
// UNION TYPE FOR ALL ALERTS
// ============================================================================

export type AnyAlert =
  | PriceAlert
  | PriceCrossingAlert
  | IndicatorValueAlert
  | IndicatorCrossingAlert
  | CandlePatternAlert
  | VolumeAlert

// ============================================================================
// NOTIFICATION INTERFACES
// ============================================================================

/**
 * Notificação disparada quando um alerta é acionado
 */
export interface AlertNotification {
  id: string
  alertId: string
  alert: AnyAlert
  triggeredAt: number
  message: string
  type: NotificationType
  read: boolean
  candle?: any                 // Candle que disparou o alerta
  price?: number               // Preço no momento do disparo
}

/**
 * Estado do sistema de notificações
 */
export interface NotificationState {
  notifications: AlertNotification[]
  unreadCount: number
  soundEnabled: boolean
  soundVolume: number          // 0-1
}

// ============================================================================
// ALERT MANAGER STATE
// ============================================================================

export interface AlertManagerState {
  alerts: AnyAlert[]
  notifications: AlertNotification[]
  soundEnabled: boolean
  soundVolume: number
}

// ============================================================================
// ALERT TEMPLATES / PRESETS
// ============================================================================

export interface AlertTemplate {
  name: string
  description: string
  type: AlertType
  defaultConfig: Partial<AnyAlert>
}

export const ALERT_TEMPLATES: Record<string, AlertTemplate> = {
  PRICE_ABOVE: {
    name: 'Preço Acima',
    description: 'Alerta quando o preço ficar acima de um valor',
    type: AlertType.PRICE,
    defaultConfig: {
      condition: AlertCondition.ABOVE,
      frequency: AlertFrequency.ONCE,
      notificationTypes: [NotificationType.VISUAL, NotificationType.SOUND]
    }
  },
  PRICE_BELOW: {
    name: 'Preço Abaixo',
    description: 'Alerta quando o preço ficar abaixo de um valor',
    type: AlertType.PRICE,
    defaultConfig: {
      condition: AlertCondition.BELOW,
      frequency: AlertFrequency.ONCE,
      notificationTypes: [NotificationType.VISUAL, NotificationType.SOUND]
    }
  },
  RSI_OVERBOUGHT: {
    name: 'RSI Sobrecomprado',
    description: 'Alerta quando RSI > 70',
    type: AlertType.INDICATOR_VALUE,
    defaultConfig: {
      condition: AlertCondition.ABOVE,
      targetValue: 70,
      frequency: AlertFrequency.ONCE_PER_BAR,
      notificationTypes: [NotificationType.VISUAL, NotificationType.SOUND]
    }
  },
  RSI_OVERSOLD: {
    name: 'RSI Sobrevendido',
    description: 'Alerta quando RSI < 30',
    type: AlertType.INDICATOR_VALUE,
    defaultConfig: {
      condition: AlertCondition.BELOW,
      targetValue: 30,
      frequency: AlertFrequency.ONCE_PER_BAR,
      notificationTypes: [NotificationType.VISUAL, NotificationType.SOUND]
    }
  },
  GOLDEN_CROSS: {
    name: 'Golden Cross',
    description: 'Alerta quando MA rápida cruza MA lenta para cima',
    type: AlertType.INDICATOR_CROSSING,
    defaultConfig: {
      condition: AlertCondition.CROSSES_UP,
      frequency: AlertFrequency.ONCE_PER_BAR,
      notificationTypes: [NotificationType.VISUAL, NotificationType.SOUND, NotificationType.POPUP]
    }
  },
  DEATH_CROSS: {
    name: 'Death Cross',
    description: 'Alerta quando MA rápida cruza MA lenta para baixo',
    type: AlertType.INDICATOR_CROSSING,
    defaultConfig: {
      condition: AlertCondition.CROSSES_DOWN,
      frequency: AlertFrequency.ONCE_PER_BAR,
      notificationTypes: [NotificationType.VISUAL, NotificationType.SOUND, NotificationType.POPUP]
    }
  },
  VOLUME_SPIKE: {
    name: 'Volume Anormal',
    description: 'Alerta quando volume > 2x a média',
    type: AlertType.VOLUME,
    defaultConfig: {
      condition: AlertCondition.PERCENT_CHANGE,
      targetValue: 200,         // 200% da média
      lookbackPeriod: 20,
      frequency: AlertFrequency.ONCE_PER_BAR,
      notificationTypes: [NotificationType.VISUAL]
    }
  }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Gera ID único para alerta
 */
export const generateAlertId = (type: AlertType): string => {
  return `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Gera mensagem de notificação baseado no alerta
 */
export const generateAlertMessage = (alert: AnyAlert, price?: number): string => {
  switch (alert.type) {
    case AlertType.PRICE:
      const priceAlert = alert as PriceAlert
      return `${alert.symbol}: Preço ${priceAlert.condition === AlertCondition.ABOVE ? 'acima' : 'abaixo'} de ${priceAlert.targetPrice}`

    case AlertType.PRICE_CROSSING:
      const crossingAlert = alert as PriceCrossingAlert
      return `${alert.symbol}: Preço cruzou ${crossingAlert.condition === AlertCondition.CROSSES_UP ? 'para cima' : 'para baixo'} da linha`

    case AlertType.INDICATOR_VALUE:
      const indAlert = alert as IndicatorValueAlert
      return `${alert.symbol}: Indicador ${indAlert.indicatorId} ${getConditionText(indAlert.condition)} ${indAlert.targetValue}`

    case AlertType.INDICATOR_CROSSING:
      const crossAlert = alert as IndicatorCrossingAlert
      return `${alert.symbol}: ${crossAlert.indicator1Id} cruzou ${crossAlert.indicator2Id} ${crossAlert.condition === AlertCondition.CROSSES_UP ? 'para cima' : 'para baixo'}`

    case AlertType.CANDLE_PATTERN:
      const patternAlert = alert as CandlePatternAlert
      return `${alert.symbol}: Padrão ${patternAlert.pattern} detectado`

    case AlertType.VOLUME:
      const volumeAlert = alert as VolumeAlert
      return `${alert.symbol}: Volume anormal detectado`

    default:
      return `${alert.symbol}: Alerta disparado`
  }
}

function getConditionText(condition: AlertCondition): string {
  switch (condition) {
    case AlertCondition.ABOVE: return 'acima de'
    case AlertCondition.BELOW: return 'abaixo de'
    case AlertCondition.CROSSES_UP: return 'cruzou para cima'
    case AlertCondition.CROSSES_DOWN: return 'cruzou para baixo'
    case AlertCondition.EQUALS: return 'igual a'
    case AlertCondition.PERCENT_CHANGE: return 'mudou'
    default: return ''
  }
}

/**
 * Verifica se alerta expirou
 */
export const isAlertExpired = (alert: AnyAlert): boolean => {
  if (!alert.expiresAt) return false
  return Date.now() > alert.expiresAt
}

/**
 * Verifica se alerta pode disparar novamente
 */
export const canAlertTriggerAgain = (alert: AnyAlert): boolean => {
  if (alert.status !== AlertStatus.ACTIVE) return false
  if (isAlertExpired(alert)) return false

  switch (alert.frequency) {
    case AlertFrequency.ONCE:
      return alert.triggeredAt === null

    case AlertFrequency.ONCE_PER_BAR:
      // Precisa verificar se é um novo candle desde o último disparo
      // Isso será implementado no AlertManager
      return true

    case AlertFrequency.EVERY_TIME:
      return true

    default:
      return false
  }
}
