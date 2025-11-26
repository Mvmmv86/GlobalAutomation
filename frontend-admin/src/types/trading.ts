export enum ExchangeType {
  BINANCE = 'binance',
  BYBIT = 'bybit'
}

export enum OrderSide {
  BUY = 'buy',
  SELL = 'sell'
}

export enum OrderType {
  MARKET = 'market',
  LIMIT = 'limit',
  STOP_LOSS = 'stop_loss',
  TAKE_PROFIT = 'take_profit',
  STOP_LIMIT = 'stop_limit'
}

export enum OrderStatus {
  PENDING = 'pending',
  SUBMITTED = 'submitted',
  OPEN = 'open',
  PARTIALLY_FILLED = 'partially_filled',
  FILLED = 'filled',
  CANCELED = 'canceled',
  REJECTED = 'rejected',
  EXPIRED = 'expired',
  FAILED = 'failed'
}

export enum PositionSide {
  LONG = 'long',
  SHORT = 'short'
}

export enum PositionStatus {
  OPEN = 'open',
  CLOSED = 'closed',
  CLOSING = 'closing',
  LIQUIDATED = 'liquidated'
}

export enum WebhookStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  DISABLED = 'disabled',
  ERROR = 'error'
}

export interface ExchangeAccount {
  id: string
  name: string
  exchange: ExchangeType
  testnet: boolean
  isActive: boolean
  isMain?: boolean  // Nova propriedade para conta principal
  createdAt: string
  updatedAt: string
}

export interface Order {
  id: string
  clientOrderId: string
  symbol: string
  side: OrderSide
  type: OrderType
  status: OrderStatus
  quantity: number
  price?: number
  stopPrice?: number
  filledQuantity: number
  averageFillPrice?: number
  feesPaid: number
  feeCurrency?: string | null
  source: string
  exchangeAccountId: string
  createdAt: string
  updatedAt: string

  // Campos adicionais do backend
  operation_type?: string
  entry_exit?: string
  margin_usdt?: number
  profit_loss?: number
  order_id?: string | null
}

export interface Position {
  id: string
  symbol: string
  side: PositionSide
  status: PositionStatus
  size: number
  entryPrice: number
  markPrice?: number
  unrealizedPnl: number
  realizedPnl: number
  initialMargin: number
  maintenanceMargin: number
  leverage: number
  liquidationPrice?: number
  exchangeAccountId: string
  openedAt: string
  closedAt?: string
  createdAt: string
  updatedAt: string

  operation_type?: string
}

export interface Webhook {
  id: string
  name: string
  urlPath: string
  status: WebhookStatus
  isPublic: boolean
  rateLimitPerMinute: number
  rateLimitPerHour: number
  totalDeliveries: number
  successfulDeliveries: number
  failedDeliveries: number
  lastDeliveryAt?: string
  lastSuccessAt?: string
  createdAt: string
  updatedAt: string
}