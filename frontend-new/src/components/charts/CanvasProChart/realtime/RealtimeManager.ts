/**
 * RealtimeManager - Gerenciador central de dados real-time
 * Integra WebSocket, Timeframes e Historical Loader
 */

import { Candle } from '../types'
import { WebSocketManager, WebSocketConfig, TradeData, DepthData, TickerData } from './WebSocketManager'
import { TimeframeManager, Timeframe, TimeframeConfig } from './TimeframeManager'
import { HistoricalLoader, HistoricalConfig } from './HistoricalLoader'

export interface RealtimeConfig {
  symbol: string
  initialTimeframe: Timeframe
  enabledTimeframes?: Timeframe[]
  testnet?: boolean
  apiKey?: string
  apiSecret?: string

  // Configurações de dados
  historicalCandles?: number      // Quantos candles históricos carregar
  cacheStrategy?: 'memory' | 'indexeddb' | 'hybrid'
  autoReconnect?: boolean
  reconnectDelay?: number

  // Callbacks
  onDataReady?: (candles: Candle[]) => void
  onDataUpdate?: (candles: Candle[]) => void
  onTimeframeChange?: (from: Timeframe, to: Timeframe) => void
  onTradeUpdate?: (trade: TradeData) => void
  onDepthUpdate?: (depth: DepthData) => void
  onTickerUpdate?: (ticker: TickerData) => void
  onError?: (error: Error) => void
  onStatusChange?: (status: RealtimeStatus) => void
}

export interface RealtimeStatus {
  isConnected: boolean
  isLoading: boolean
  activeTimeframe: Timeframe
  candleCount: number
  lastUpdate: number
  error?: string
  websocketStatus: 'disconnected' | 'connecting' | 'connected' | 'error'
  historicalStatus: 'idle' | 'loading' | 'loaded' | 'error'
}

export class RealtimeManager {
  private config: RealtimeConfig
  private wsManager?: WebSocketManager
  private tfManager: TimeframeManager
  private histLoader: HistoricalLoader
  private status: RealtimeStatus
  private isInitialized = false
  private dataBuffer: Map<Timeframe, Candle[]> = new Map()
  private mergeTimer?: NodeJS.Timeout

  constructor(config: RealtimeConfig) {
    this.config = {
      historicalCandles: 1000,
      cacheStrategy: 'hybrid',
      autoReconnect: true,
      reconnectDelay: 3000,
      enabledTimeframes: ['1m', '5m', '15m', '1h', '4h', '1d'],
      ...config
    }

    // Estado inicial
    this.status = {
      isConnected: false,
      isLoading: false,
      activeTimeframe: config.initialTimeframe,
      candleCount: 0,
      lastUpdate: 0,
      websocketStatus: 'disconnected',
      historicalStatus: 'idle'
    }

    // Inicializar TimeframeManager
    this.tfManager = new TimeframeManager({
      symbol: config.symbol,
      activeTimeframe: config.initialTimeframe,
      enabledTimeframes: this.config.enabledTimeframes || ['1m', '5m', '15m', '1h', '4h', '1d'],
      cacheStrategy: this.config.cacheStrategy,
      testnet: config.testnet,
      onTimeframeChange: (from, to) => this.handleTimeframeChange(from, to),
      onDataUpdate: (tf, candles) => this.handleDataUpdate(tf, candles)
    })

    // Inicializar HistoricalLoader
    this.histLoader = new HistoricalLoader({
      symbol: config.symbol,
      testnet: config.testnet,
      apiKey: config.apiKey,
      apiSecret: config.apiSecret,
      onProgress: (loaded, total) => this.handleLoadProgress(loaded, total),
      onError: (error) => this.handleError(error)
    })

    console.log('🚀 RealtimeManager initialized', {
      symbol: config.symbol,
      timeframe: config.initialTimeframe,
      testnet: config.testnet
    })
  }

  /**
   * Inicializa e conecta todos os componentes
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      console.log('Already initialized')
      return
    }

    console.log('🔄 Initializing RealtimeManager...')
    this.updateStatus({ isLoading: true, historicalStatus: 'loading' })

    try {
      // 1. Carregar dados históricos primeiro
      await this.loadHistoricalData()

      // 2. Conectar WebSocket para timeframe ativo
      await this.connectWebSocket()

      // 3. Marcar como inicializado
      this.isInitialized = true
      this.updateStatus({
        isLoading: false,
        isConnected: true,
        websocketStatus: 'connected',
        historicalStatus: 'loaded'
      })

      console.log('✅ RealtimeManager initialized successfully')

    } catch (error) {
      console.error('❌ Failed to initialize RealtimeManager:', error)
      this.updateStatus({
        isLoading: false,
        isConnected: false,
        websocketStatus: 'error',
        historicalStatus: 'error',
        error: error instanceof Error ? error.message : 'Initialization failed'
      })

      throw error
    }
  }

  /**
   * Carrega dados históricos
   */
  private async loadHistoricalData(): Promise<void> {
    console.log(`📚 Loading historical data for ${this.config.initialTimeframe}...`)

    const candles = await this.histLoader.loadRecent(
      this.config.initialTimeframe,
      this.config.historicalCandles || 1000
    )

    if (candles.length > 0) {
      // Armazenar no TimeframeManager
      this.tfManager.setHistoricalCandles(candles)

      // Armazenar no buffer local
      this.dataBuffer.set(this.config.initialTimeframe, candles)

      console.log(`✅ Loaded ${candles.length} historical candles`)

      // Callback para notificar que dados estão prontos
      if (this.config.onDataReady) {
        this.config.onDataReady(candles)
      }

      this.updateStatus({
        candleCount: candles.length,
        lastUpdate: Date.now()
      })
    }
  }

  /**
   * Conecta WebSocket
   */
  private async connectWebSocket(): Promise<void> {
    console.log('🔌 Connecting WebSocket...')

    this.wsManager = new WebSocketManager({
      symbol: this.config.symbol,
      interval: this.config.initialTimeframe,
      testnet: this.config.testnet,
      onCandle: (candle) => this.handleNewCandle(candle),
      onTrade: this.config.onTradeUpdate,
      onDepth: this.config.onDepthUpdate,
      onTicker: this.config.onTickerUpdate,
      onError: (error) => this.handleWebSocketError(error),
      onConnect: () => this.handleWebSocketConnect(),
      onDisconnect: (reason) => this.handleWebSocketDisconnect(reason)
    })

    await this.wsManager.connect()
  }

  /**
   * Handle novo candle do WebSocket
   */
  private handleNewCandle(candle: Candle): void {
    const timeframe = this.status.activeTimeframe
    let buffer = this.dataBuffer.get(timeframe) || []

    // Encontrar ou adicionar candle
    const existingIndex = buffer.findIndex(c => c.time === candle.time)

    if (existingIndex >= 0) {
      // Atualizar candle existente
      buffer[existingIndex] = candle
    } else {
      // Adicionar novo candle
      buffer.push(candle)

      // Manter limite
      const limit = this.config.historicalCandles || 1000
      if (buffer.length > limit) {
        buffer = buffer.slice(-limit)
      }
    }

    // Atualizar buffer
    this.dataBuffer.set(timeframe, buffer)

    // Debounce para evitar muitas atualizações
    if (this.mergeTimer) {
      clearTimeout(this.mergeTimer)
    }

    this.mergeTimer = setTimeout(() => {
      // Notificar atualização
      if (this.config.onDataUpdate) {
        this.config.onDataUpdate(buffer)
      }

      this.updateStatus({
        candleCount: buffer.length,
        lastUpdate: Date.now()
      })
    }, 100)
  }

  /**
   * Muda timeframe
   */
  async switchTimeframe(newTimeframe: Timeframe): Promise<void> {
    if (newTimeframe === this.status.activeTimeframe) {
      console.log(`Already on timeframe ${newTimeframe}`)
      return
    }

    console.log(`🔄 Switching to ${newTimeframe}...`)
    this.updateStatus({ isLoading: true })

    try {
      // Desconectar WebSocket atual
      if (this.wsManager) {
        this.wsManager.disconnect()
      }

      // Verificar se já temos dados cached
      let candles = this.dataBuffer.get(newTimeframe)

      if (!candles || candles.length === 0) {
        // Carregar dados históricos para novo timeframe
        candles = await this.histLoader.loadRecent(
          newTimeframe,
          this.config.historicalCandles || 1000
        )

        if (candles.length > 0) {
          this.dataBuffer.set(newTimeframe, candles)
        }
      }

      // Criar novo WebSocket para novo timeframe
      this.wsManager = new WebSocketManager({
        symbol: this.config.symbol,
        interval: newTimeframe,
        testnet: this.config.testnet,
        onCandle: (candle) => this.handleNewCandle(candle),
        onTrade: this.config.onTradeUpdate,
        onDepth: this.config.onDepthUpdate,
        onTicker: this.config.onTickerUpdate,
        onError: (error) => this.handleWebSocketError(error),
        onConnect: () => this.handleWebSocketConnect(),
        onDisconnect: (reason) => this.handleWebSocketDisconnect(reason)
      })

      await this.wsManager.connect()

      // Atualizar estado
      const oldTimeframe = this.status.activeTimeframe
      this.updateStatus({
        activeTimeframe: newTimeframe,
        candleCount: candles?.length || 0,
        isLoading: false
      })

      // Callbacks
      if (this.config.onTimeframeChange) {
        this.config.onTimeframeChange(oldTimeframe, newTimeframe)
      }

      if (candles && candles.length > 0 && this.config.onDataReady) {
        this.config.onDataReady(candles)
      }

      console.log(`✅ Switched to ${newTimeframe}`)

    } catch (error) {
      console.error(`❌ Failed to switch to ${newTimeframe}:`, error)
      this.updateStatus({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to switch timeframe'
      })
      throw error
    }
  }

  /**
   * Carrega mais dados históricos
   */
  async loadMoreHistory(count: number = 1000): Promise<void> {
    const timeframe = this.status.activeTimeframe
    const currentBuffer = this.dataBuffer.get(timeframe) || []

    if (currentBuffer.length === 0) {
      // Carregar dados iniciais
      await this.loadHistoricalData()
      return
    }

    // Encontrar tempo mais antigo
    const oldestTime = Math.min(...currentBuffer.map(c => c.time))
    const startTime = oldestTime - (this.getTimeframeMs(timeframe) * count)

    console.log(`📚 Loading ${count} more candles before ${new Date(oldestTime).toISOString()}`)

    const olderCandles = await this.histLoader.load(
      timeframe,
      startTime,
      oldestTime - 1
    )

    if (olderCandles.length > 0) {
      // Mesclar com dados existentes
      const merged = [...olderCandles, ...currentBuffer]

      // Manter limite total
      const limit = (this.config.historicalCandles || 1000) * 2 // Permitir 2x o limite ao carregar mais
      const trimmed = merged.slice(-limit)

      this.dataBuffer.set(timeframe, trimmed)

      // Notificar atualização
      if (this.config.onDataUpdate) {
        this.config.onDataUpdate(trimmed)
      }

      this.updateStatus({
        candleCount: trimmed.length,
        lastUpdate: Date.now()
      })

      console.log(`✅ Loaded ${olderCandles.length} older candles, total: ${trimmed.length}`)
    }
  }

  /**
   * Preenche gaps nos dados
   */
  async fillDataGaps(): Promise<void> {
    const timeframe = this.status.activeTimeframe
    const currentBuffer = this.dataBuffer.get(timeframe) || []

    if (currentBuffer.length < 2) {
      return
    }

    console.log('🔍 Checking for data gaps...')

    const filled = await this.histLoader.fillGaps(timeframe, currentBuffer)

    if (filled.length > currentBuffer.length) {
      const newCandles = filled.length - currentBuffer.length
      console.log(`✅ Filled ${newCandles} gap candles`)

      this.dataBuffer.set(timeframe, filled)

      if (this.config.onDataUpdate) {
        this.config.onDataUpdate(filled)
      }

      this.updateStatus({
        candleCount: filled.length,
        lastUpdate: Date.now()
      })
    } else {
      console.log('✅ No gaps found')
    }
  }

  /**
   * WebSocket event handlers
   */
  private handleWebSocketConnect(): void {
    console.log('✅ WebSocket connected')
    this.updateStatus({
      isConnected: true,
      websocketStatus: 'connected',
      error: undefined
    })
  }

  private handleWebSocketDisconnect(reason: string): void {
    console.log(`🔌 WebSocket disconnected: ${reason}`)
    this.updateStatus({
      isConnected: false,
      websocketStatus: 'disconnected'
    })

    // Auto-reconnect se configurado
    if (this.config.autoReconnect && this.isInitialized) {
      setTimeout(() => {
        if (!this.wsManager?.isConnected()) {
          console.log('🔄 Auto-reconnecting...')
          this.connectWebSocket().catch(error => {
            console.error('Auto-reconnect failed:', error)
          })
        }
      }, this.config.reconnectDelay || 3000)
    }
  }

  private handleWebSocketError(error: Error): void {
    console.error('❌ WebSocket error:', error)
    this.updateStatus({
      websocketStatus: 'error',
      error: error.message
    })

    if (this.config.onError) {
      this.config.onError(error)
    }
  }

  /**
   * Outros event handlers
   */
  private handleTimeframeChange(from: Timeframe, to: Timeframe): void {
    console.log(`📊 Timeframe changed from ${from} to ${to}`)
    // Já tratado no switchTimeframe
  }

  private handleDataUpdate(timeframe: Timeframe, candles: Candle[]): void {
    if (timeframe === this.status.activeTimeframe) {
      // Atualizar buffer local
      this.dataBuffer.set(timeframe, candles)

      // Notificar
      if (this.config.onDataUpdate) {
        this.config.onDataUpdate(candles)
      }
    }
  }

  private handleLoadProgress(loaded: number, total: number): void {
    console.log(`Loading: ${loaded}/${total} (${Math.round(loaded / total * 100)}%)`)
  }

  private handleError(error: Error): void {
    console.error('Error:', error)
    this.updateStatus({ error: error.message })

    if (this.config.onError) {
      this.config.onError(error)
    }
  }

  /**
   * Atualiza status
   */
  private updateStatus(partial: Partial<RealtimeStatus>): void {
    this.status = { ...this.status, ...partial }

    if (this.config.onStatusChange) {
      this.config.onStatusChange(this.status)
    }
  }

  /**
   * Helpers
   */
  private getTimeframeMs(timeframe: Timeframe): number {
    const msMap: Record<Timeframe, number> = {
      '1m': 60000,
      '3m': 180000,
      '5m': 300000,
      '15m': 900000,
      '30m': 1800000,
      '1h': 3600000,
      '2h': 7200000,
      '4h': 14400000,
      '6h': 21600000,
      '8h': 28800000,
      '12h': 43200000,
      '1d': 86400000,
      '3d': 259200000,
      '1w': 604800000,
      '1M': 2592000000
    }
    return msMap[timeframe]
  }

  /**
   * Public API
   */

  /**
   * Obtém dados atuais
   */
  getCurrentData(): Candle[] {
    return this.dataBuffer.get(this.status.activeTimeframe) || []
  }

  /**
   * Obtém status atual
   */
  getStatus(): RealtimeStatus {
    return { ...this.status }
  }

  /**
   * Verifica se está conectado
   */
  isConnected(): boolean {
    return this.status.isConnected && (this.wsManager?.isConnected() || false)
  }

  /**
   * Reconecta manualmente
   */
  async reconnect(): Promise<void> {
    console.log('🔄 Manual reconnect...')

    if (this.wsManager) {
      this.wsManager.disconnect()
    }

    await this.connectWebSocket()
  }

  /**
   * Muda símbolo
   */
  async changeSymbol(newSymbol: string): Promise<void> {
    console.log(`🔄 Changing symbol from ${this.config.symbol} to ${newSymbol}`)

    // Desconectar tudo
    this.destroy()

    // Atualizar configuração
    this.config.symbol = newSymbol

    // Reinicializar
    this.isInitialized = false
    this.dataBuffer.clear()

    // Re-criar componentes
    this.tfManager = new TimeframeManager({
      symbol: newSymbol,
      activeTimeframe: this.config.initialTimeframe,
      enabledTimeframes: this.config.enabledTimeframes || ['1m', '5m', '15m', '1h', '4h', '1d'],
      cacheStrategy: this.config.cacheStrategy,
      testnet: this.config.testnet,
      onTimeframeChange: (from, to) => this.handleTimeframeChange(from, to),
      onDataUpdate: (tf, candles) => this.handleDataUpdate(tf, candles)
    })

    this.histLoader = new HistoricalLoader({
      symbol: newSymbol,
      testnet: this.config.testnet,
      apiKey: this.config.apiKey,
      apiSecret: this.config.apiSecret,
      onProgress: (loaded, total) => this.handleLoadProgress(loaded, total),
      onError: (error) => this.handleError(error)
    })

    // Reinicializar
    await this.initialize()
  }

  /**
   * Limpa todos os dados
   */
  clearData(): void {
    this.dataBuffer.clear()
    this.tfManager.clearCache()
    this.histLoader.clearCache()

    this.updateStatus({
      candleCount: 0,
      lastUpdate: 0
    })

    console.log('🗑️ All data cleared')
  }

  /**
   * Destrói o manager
   */
  destroy(): void {
    console.log('🗑️ Destroying RealtimeManager...')

    if (this.mergeTimer) {
      clearTimeout(this.mergeTimer)
    }

    if (this.wsManager) {
      this.wsManager.destroy()
    }

    this.tfManager.destroy()
    this.dataBuffer.clear()

    this.isInitialized = false
    this.updateStatus({
      isConnected: false,
      websocketStatus: 'disconnected',
      historicalStatus: 'idle'
    })

    console.log('🗑️ RealtimeManager destroyed')
  }
}