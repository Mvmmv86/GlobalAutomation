/**
 * CanvasProChart Types - Professional Trading Chart
 * Sistema completo de tipos para gráfico profissional
 */

export interface Candle {
  time: number // Unix timestamp
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface Point {
  x: number
  y: number
}

export interface Viewport {
  startIndex: number
  endIndex: number
  scale: number
  offset: Point
  width: number
  height: number
}

export interface ChartTheme {
  background: string
  grid: {
    color: string
    lineWidth: number
  }
  candle: {
    up: {
      body: string
      wick: string
      border: string
    }
    down: {
      body: string
      wick: string
      border: string
    }
  }
  volume: {
    up: string
    down: string
  }
  crosshair: {
    color: string
    lineWidth: number
    labelBackground: string
    labelText: string
  }
  text: {
    primary: string
    secondary: string
    fontSize: number
    fontFamily: string
  }
  indicators: {
    ema9: string
    ema20: string
    ema50: string
    sma20: string
    sma50: string
  }
  orders: {
    stopLoss: string
    takeProfit: string
    position: string
    dragPreview: string
  }
}

export interface DraggableLine {
  id: string
  type: 'STOP_LOSS' | 'TAKE_PROFIT' | 'POSITION'
  price: number
  quantity?: number
  isDragging?: boolean
  orderId?: string
}

export interface ChartPosition {
  symbol: string
  side: 'LONG' | 'SHORT'
  entryPrice: number
  quantity: number
  pnl: number
  pnlPercent: number
}

export interface ChartConfig {
  symbol: string
  interval: string // '1m', '5m', '15m', '30m', '1h', '4h', '1d'
  theme: 'dark' | 'light'
  showVolume: boolean
  showGrid: boolean
  showCrosshair: boolean
  enableZoom: boolean
  enablePan: boolean
  enableDragDrop: boolean
  maxCandles: number // Maximum candles to keep in memory
  cacheEnabled: boolean
}

export interface ChartCallbacks {
  onDragSLTP?: (type: 'STOP_LOSS' | 'TAKE_PROFIT', newPrice: number, orderId?: string) => void
  onZoomChange?: (scale: number) => void
  onTimeRangeChange?: (startTime: number, endTime: number) => void
  onCrosshairMove?: (price: number | null, time: number | null) => void
}

// Performance optimization types
export interface RenderLayer {
  name: string
  canvas: HTMLCanvasElement
  ctx: CanvasRenderingContext2D
  needsRedraw: boolean
}

export interface ChartLayers {
  background: RenderLayer  // Grid, background
  main: RenderLayer        // Candles, volume
  indicators: RenderLayer  // EMA, SMA, etc
  overlays: RenderLayer    // SL/TP lines, positions
  interaction: RenderLayer // Crosshair, tooltips
}

// Data management
export interface DataBuffer {
  candles: Candle[]
  maxSize: number
  startTime: number
  endTime: number
}

// Animation frame optimization
export interface AnimationState {
  frameId: number | null
  lastFrameTime: number
  targetFPS: number
  isAnimating: boolean
}

// Mouse/Touch interaction
export interface InteractionState {
  isDragging: boolean
  isPanning: boolean
  isZooming: boolean
  startPoint: Point | null
  currentPoint: Point | null
  draggedLine: DraggableLine | null
  hoveredLine: DraggableLine | null
}

// Zoom levels (like TradingView)
export interface ZoomLevel {
  label: string
  candlesVisible: number
  scale: number
}

export const ZOOM_LEVELS: ZoomLevel[] = [
  { label: '1D', candlesVisible: 288, scale: 1 },     // 1 day in 5min
  { label: '3D', candlesVisible: 864, scale: 0.5 },   // 3 days
  { label: '1W', candlesVisible: 2016, scale: 0.3 },  // 1 week
  { label: '1M', candlesVisible: 8640, scale: 0.1 },  // 1 month
  { label: '3M', candlesVisible: 25920, scale: 0.05 }, // 3 months
  { label: '1Y', candlesVisible: 105120, scale: 0.01 }, // 1 year
  { label: 'ALL', candlesVisible: 525600, scale: 0.001 } // All data
]

// Indicator calculations
export interface Indicator {
  name: string
  values: number[]
  color: string
  lineWidth: number
  visible: boolean
}

export interface IndicatorSet {
  ema9?: Indicator
  ema20?: Indicator
  ema50?: Indicator
  sma20?: Indicator
  sma50?: Indicator
  volume?: Indicator
}

// WebSocket real-time data
export interface RealtimeUpdate {
  symbol: string
  candle: Partial<Candle>
  timestamp: number
}

// Cache management
export interface CacheEntry {
  symbol: string
  interval: string
  candles: Candle[]
  lastUpdated: number
  version: number
}
