/**
 * Realtime Module - Exporta todos os componentes de dados em tempo real
 */

export { WebSocketManager } from './WebSocketManager'
export type {
  WebSocketConfig,
  TradeData,
  DepthData,
  TickerData
} from './WebSocketManager'

export { TimeframeManager } from './TimeframeManager'
export type {
  Timeframe,
  TimeframeConfig
} from './TimeframeManager'

export { HistoricalLoader } from './HistoricalLoader'
export type {
  HistoricalConfig
} from './HistoricalLoader'

export { RealtimeManager } from './RealtimeManager'
export type {
  RealtimeConfig,
  RealtimeStatus
} from './RealtimeManager'