/**
 * WebSocketManager - Gerenciador de conexões WebSocket com Binance
 * Sistema profissional com reconnect automático, rate limiting e error handling
 */

import { Candle } from '../types'

export interface WebSocketConfig {
  symbol: string
  interval: string
  testnet?: boolean
  onCandle?: (candle: Candle) => void
  onTrade?: (trade: TradeData) => void
  onDepth?: (depth: DepthData) => void
  onTicker?: (ticker: TickerData) => void
  onError?: (error: Error) => void
  onConnect?: () => void
  onDisconnect?: (reason: string) => void
  maxReconnectAttempts?: number
  reconnectDelay?: number
}

export interface TradeData {
  symbol: string
  price: number
  quantity: number
  time: number
  isBuyerMaker: boolean
  tradeId: string
}

export interface DepthData {
  symbol: string
  bids: Array<[number, number]> // [price, quantity]
  asks: Array<[number, number]>
  lastUpdateId: number
  time: number
}

export interface TickerData {
  symbol: string
  priceChange: number
  priceChangePercent: number
  lastPrice: number
  bidPrice: number
  askPrice: number
  volume: number
  quoteVolume: number
  openPrice: number
  highPrice: number
  lowPrice: number
  prevClosePrice: number
  weightedAvgPrice: number
  openTime: number
  closeTime: number
}

interface StreamSubscription {
  stream: string
  ws: WebSocket | null
  reconnectAttempts: number
  reconnectTimer?: NodeJS.Timeout
  pingInterval?: NodeJS.Timeout
  isConnected: boolean
  lastPing?: number
  lastPong?: number
}

export class WebSocketManager {
  private config: WebSocketConfig
  private subscriptions: Map<string, StreamSubscription> = new Map()
  private isDestroyed = false
  private candleBuffer: Candle[] = []
  private bufferSize = 1000
  private lastCandle: Candle | null = null

  // URLs da Binance
  private readonly WS_BASE_URL = 'wss://stream.binance.com:9443/ws'
  private readonly WS_TESTNET_URL = 'wss://testnet.binance.vision/ws'
  private readonly WS_FUTURES_URL = 'wss://fstream.binance.com/ws'
  private readonly WS_FUTURES_TESTNET_URL = 'wss://stream.binancefuture.com/ws'

  constructor(config: WebSocketConfig) {
    this.config = {
      maxReconnectAttempts: 10,
      reconnectDelay: 3000,
      ...config
    }

    console.log('🌐 WebSocketManager initialized for', config.symbol)
  }

  /**
   * Conecta aos streams necessários
   */
  async connect(): Promise<void> {
    if (this.isDestroyed) {
      throw new Error('WebSocketManager has been destroyed')
    }

    // Stream de Kline (candles)
    this.subscribeToKline()

    // Stream de trades em tempo real
    if (this.config.onTrade) {
      this.subscribeToTrades()
    }

    // Stream de order book
    if (this.config.onDepth) {
      this.subscribeToDepth()
    }

    // Stream de ticker 24h
    if (this.config.onTicker) {
      this.subscribeToTicker()
    }
  }

  /**
   * Subscribe to Kline/Candle stream
   */
  private subscribeToKline(): void {
    const symbol = this.config.symbol.toLowerCase().replace('/', '')
    const interval = this.config.interval
    const streamName = `${symbol}@kline_${interval}`

    this.createWebSocketConnection(streamName, (data: any) => {
      const kline = data.k
      if (!kline) return

      const candle: Candle = {
        time: kline.t,
        open: parseFloat(kline.o),
        high: parseFloat(kline.h),
        low: parseFloat(kline.l),
        close: parseFloat(kline.c),
        volume: parseFloat(kline.v)
      }

      // Atualizar ou adicionar candle
      if (kline.x) {
        // Candle fechado
        this.addCandleToBuffer(candle)
        this.lastCandle = null
      } else {
        // Candle em formação
        this.lastCandle = candle
      }

      // Callback
      if (this.config.onCandle) {
        this.config.onCandle(candle)
      }
    })
  }

  /**
   * Subscribe to trades stream
   */
  private subscribeToTrades(): void {
    const symbol = this.config.symbol.toLowerCase().replace('/', '')
    const streamName = `${symbol}@trade`

    this.createWebSocketConnection(streamName, (data: any) => {
      const trade: TradeData = {
        symbol: data.s,
        price: parseFloat(data.p),
        quantity: parseFloat(data.q),
        time: data.T,
        isBuyerMaker: data.m,
        tradeId: data.t
      }

      if (this.config.onTrade) {
        this.config.onTrade(trade)
      }
    })
  }

  /**
   * Subscribe to order book depth stream
   */
  private subscribeToDepth(): void {
    const symbol = this.config.symbol.toLowerCase().replace('/', '')
    const streamName = `${symbol}@depth20@100ms`

    this.createWebSocketConnection(streamName, (data: any) => {
      const depth: DepthData = {
        symbol: this.config.symbol,
        bids: data.bids.map((b: string[]) => [parseFloat(b[0]), parseFloat(b[1])]),
        asks: data.asks.map((a: string[]) => [parseFloat(a[0]), parseFloat(a[1])]),
        lastUpdateId: data.lastUpdateId,
        time: Date.now()
      }

      if (this.config.onDepth) {
        this.config.onDepth(depth)
      }
    })
  }

  /**
   * Subscribe to 24hr ticker stream
   */
  private subscribeToTicker(): void {
    const symbol = this.config.symbol.toLowerCase().replace('/', '')
    const streamName = `${symbol}@ticker`

    this.createWebSocketConnection(streamName, (data: any) => {
      const ticker: TickerData = {
        symbol: data.s,
        priceChange: parseFloat(data.p),
        priceChangePercent: parseFloat(data.P),
        lastPrice: parseFloat(data.c),
        bidPrice: parseFloat(data.b),
        askPrice: parseFloat(data.B),
        volume: parseFloat(data.v),
        quoteVolume: parseFloat(data.q),
        openPrice: parseFloat(data.o),
        highPrice: parseFloat(data.h),
        lowPrice: parseFloat(data.l),
        prevClosePrice: parseFloat(data.x),
        weightedAvgPrice: parseFloat(data.w),
        openTime: data.O,
        closeTime: data.C
      }

      if (this.config.onTicker) {
        this.config.onTicker(ticker)
      }
    })
  }

  /**
   * Cria conexão WebSocket com auto-reconnect
   */
  private createWebSocketConnection(streamName: string, handler: (data: any) => void): void {
    if (this.subscriptions.has(streamName)) {
      console.warn(`Already subscribed to ${streamName}`)
      return
    }

    const baseUrl = this.getWebSocketUrl()
    const url = `${baseUrl}/${streamName}`

    const subscription: StreamSubscription = {
      stream: streamName,
      ws: null,
      reconnectAttempts: 0,
      isConnected: false
    }

    this.subscriptions.set(streamName, subscription)

    const connect = () => {
      if (this.isDestroyed) return

      console.log(`🔌 Connecting to ${streamName}...`)

      const ws = new WebSocket(url)
      subscription.ws = ws

      ws.onopen = () => {
        console.log(`✅ Connected to ${streamName}`)
        subscription.isConnected = true
        subscription.reconnectAttempts = 0

        if (this.config.onConnect && this.subscriptions.size === 1) {
          this.config.onConnect()
        }

        // Setup ping/pong
        this.setupPingPong(subscription)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handler(data)
        } catch (error) {
          console.error(`Error parsing WebSocket data from ${streamName}:`, error)
        }
      }

      ws.onerror = (error) => {
        console.error(`❌ WebSocket error on ${streamName}:`, error)
        if (this.config.onError) {
          this.config.onError(new Error(`WebSocket error on ${streamName}`))
        }
      }

      ws.onclose = (event) => {
        console.log(`🔌 Disconnected from ${streamName}`, {
          code: event.code,
          reason: event.reason
        })

        subscription.isConnected = false
        this.clearPingPong(subscription)

        // Auto-reconnect logic
        if (!this.isDestroyed && subscription.reconnectAttempts < (this.config.maxReconnectAttempts || 10)) {
          subscription.reconnectAttempts++
          const delay = this.getReconnectDelay(subscription.reconnectAttempts)

          console.log(`🔄 Reconnecting to ${streamName} in ${delay}ms (attempt ${subscription.reconnectAttempts})`)

          subscription.reconnectTimer = setTimeout(() => {
            if (!this.isDestroyed) {
              connect()
            }
          }, delay)
        } else if (!this.isDestroyed) {
          console.error(`❌ Max reconnection attempts reached for ${streamName}`)
          if (this.config.onDisconnect) {
            this.config.onDisconnect(`Max reconnection attempts reached for ${streamName}`)
          }
        }
      }
    }

    connect()
  }

  /**
   * Setup ping/pong para manter conexão viva
   */
  private setupPingPong(subscription: StreamSubscription): void {
    subscription.pingInterval = setInterval(() => {
      if (subscription.ws?.readyState === WebSocket.OPEN) {
        subscription.ws.send(JSON.stringify({ ping: Date.now() }))
        subscription.lastPing = Date.now()
      }
    }, 30000) // Ping a cada 30 segundos
  }

  /**
   * Limpa ping/pong
   */
  private clearPingPong(subscription: StreamSubscription): void {
    if (subscription.pingInterval) {
      clearInterval(subscription.pingInterval)
      subscription.pingInterval = undefined
    }
  }

  /**
   * Calcula delay de reconexão com backoff exponencial
   */
  private getReconnectDelay(attempt: number): number {
    const baseDelay = this.config.reconnectDelay || 3000
    return Math.min(baseDelay * Math.pow(1.5, attempt - 1), 60000) // Max 60 segundos
  }

  /**
   * Retorna URL apropriada do WebSocket
   */
  private getWebSocketUrl(): string {
    // TODO: Detectar se é futures ou spot baseado no símbolo
    return this.config.testnet ? this.WS_TESTNET_URL : this.WS_BASE_URL
  }

  /**
   * Adiciona candle ao buffer
   */
  private addCandleToBuffer(candle: Candle): void {
    this.candleBuffer.push(candle)

    // Manter tamanho máximo do buffer
    if (this.candleBuffer.length > this.bufferSize) {
      this.candleBuffer.shift()
    }
  }

  /**
   * Obtém candles do buffer
   */
  getBufferedCandles(): Candle[] {
    const candles = [...this.candleBuffer]

    // Adicionar último candle em formação se existir
    if (this.lastCandle) {
      candles.push(this.lastCandle)
    }

    return candles
  }

  /**
   * Obtém último candle (fechado ou em formação)
   */
  getLastCandle(): Candle | null {
    return this.lastCandle || this.candleBuffer[this.candleBuffer.length - 1] || null
  }

  /**
   * Define candles históricos no buffer
   */
  setHistoricalCandles(candles: Candle[]): void {
    this.candleBuffer = candles.slice(-this.bufferSize)
  }

  /**
   * Verifica se está conectado
   */
  isConnected(): boolean {
    return Array.from(this.subscriptions.values()).some(s => s.isConnected)
  }

  /**
   * Obtém status de todas as conexões
   */
  getConnectionStatus(): Record<string, boolean> {
    const status: Record<string, boolean> = {}
    this.subscriptions.forEach((sub, stream) => {
      status[stream] = sub.isConnected
    })
    return status
  }

  /**
   * Desconecta de todos os streams
   */
  disconnect(): void {
    console.log('🔌 Disconnecting all WebSocket streams...')

    this.subscriptions.forEach((subscription, stream) => {
      // Limpar timers
      if (subscription.reconnectTimer) {
        clearTimeout(subscription.reconnectTimer)
      }
      this.clearPingPong(subscription)

      // Fechar WebSocket
      if (subscription.ws) {
        subscription.ws.close(1000, 'Manual disconnect')
        subscription.ws = null
      }

      console.log(`✅ Disconnected from ${stream}`)
    })

    this.subscriptions.clear()

    if (this.config.onDisconnect) {
      this.config.onDisconnect('Manual disconnect')
    }
  }

  /**
   * Destrói o manager
   */
  destroy(): void {
    this.isDestroyed = true
    this.disconnect()
    this.candleBuffer = []
    this.lastCandle = null
    console.log('🗑️ WebSocketManager destroyed')
  }

  /**
   * Reconecta a todos os streams
   */
  async reconnect(): Promise<void> {
    console.log('🔄 Reconnecting all streams...')

    // Salvar streams atuais
    const streams = Array.from(this.subscriptions.keys())

    // Desconectar
    this.disconnect()

    // Aguardar um pouco
    await new Promise(resolve => setTimeout(resolve, 1000))

    // Reconectar
    this.isDestroyed = false
    await this.connect()

    console.log('✅ Reconnection complete')
  }

  /**
   * Muda símbolo mantendo conexão
   */
  async changeSymbol(symbol: string): Promise<void> {
    console.log(`🔄 Changing symbol from ${this.config.symbol} to ${symbol}`)

    this.config.symbol = symbol
    await this.reconnect()
  }

  /**
   * Muda intervalo mantendo conexão
   */
  async changeInterval(interval: string): Promise<void> {
    console.log(`🔄 Changing interval from ${this.config.interval} to ${interval}`)

    this.config.interval = interval
    this.candleBuffer = [] // Limpar buffer ao mudar intervalo
    this.lastCandle = null

    await this.reconnect()
  }
}