/**
 * TimeframeManager - Gerenciador de timeframes com cache inteligente
 * Sistema profissional para múltiplos períodos temporais
 */

import { Candle } from '../types'
import { WebSocketManager } from './WebSocketManager'

export type Timeframe = '1m' | '3m' | '5m' | '15m' | '30m' | '1h' | '2h' | '4h' | '6h' | '8h' | '12h' | '1d' | '3d' | '1w' | '1M'

export interface TimeframeConfig {
  symbol: string
  activeTimeframe: Timeframe
  enabledTimeframes: Timeframe[]
  maxCandlesPerTimeframe: number
  cacheStrategy: 'memory' | 'indexeddb' | 'hybrid'
  onTimeframeChange?: (from: Timeframe, to: Timeframe) => void
  onDataUpdate?: (timeframe: Timeframe, candles: Candle[]) => void
  testnet?: boolean
}

interface TimeframeData {
  timeframe: Timeframe
  candles: Candle[]
  lastUpdate: number
  wsManager?: WebSocketManager
  isActive: boolean
  isLoading: boolean
  error?: string
}

interface AggregationRule {
  source: Timeframe
  target: Timeframe
  factor: number
}

export class TimeframeManager {
  private config: TimeframeConfig
  private timeframes: Map<Timeframe, TimeframeData> = new Map()
  private activeTimeframe: Timeframe
  private aggregationRules: AggregationRule[] = []
  private db?: IDBDatabase
  private memoryCache: Map<string, Candle[]> = new Map()

  // Timeframe em millisegundos
  private readonly TIMEFRAME_MS: Record<Timeframe, number> = {
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

  // Limite de candles por timeframe para otimização
  private readonly DEFAULT_LIMITS: Record<Timeframe, number> = {
    '1m': 1440,   // 24 horas
    '3m': 1000,   // ~2 dias
    '5m': 1000,   // ~3.5 dias
    '15m': 1000,  // ~10 dias
    '30m': 1000,  // ~20 dias
    '1h': 1000,   // ~41 dias
    '2h': 1000,   // ~83 dias
    '4h': 1000,   // ~166 dias
    '6h': 1000,   // ~250 dias
    '8h': 1000,   // ~333 dias
    '12h': 1000,  // ~500 dias
    '1d': 1000,   // ~3 anos
    '3d': 1000,   // ~8 anos
    '1w': 520,    // 10 anos
    '1M': 120     // 10 anos
  }

  constructor(config: TimeframeConfig) {
    this.config = {
      maxCandlesPerTimeframe: 1000,
      cacheStrategy: 'hybrid',
      enabledTimeframes: ['1m', '5m', '15m', '1h', '4h', '1d'],
      ...config
    }

    this.activeTimeframe = config.activeTimeframe
    this.setupAggregationRules()
    this.initializeTimeframes()

    if (this.config.cacheStrategy !== 'memory') {
      this.initializeIndexedDB()
    }

    console.log('📊 TimeframeManager initialized', {
      symbol: config.symbol,
      activeTimeframe: config.activeTimeframe,
      enabledTimeframes: config.enabledTimeframes
    })
  }

  /**
   * Configura regras de agregação entre timeframes
   */
  private setupAggregationRules(): void {
    // Regras para agregar candles de timeframes menores em maiores
    this.aggregationRules = [
      { source: '1m', target: '3m', factor: 3 },
      { source: '1m', target: '5m', factor: 5 },
      { source: '1m', target: '15m', factor: 15 },
      { source: '1m', target: '30m', factor: 30 },
      { source: '1m', target: '1h', factor: 60 },
      { source: '5m', target: '15m', factor: 3 },
      { source: '5m', target: '30m', factor: 6 },
      { source: '5m', target: '1h', factor: 12 },
      { source: '15m', target: '30m', factor: 2 },
      { source: '15m', target: '1h', factor: 4 },
      { source: '15m', target: '4h', factor: 16 },
      { source: '30m', target: '1h', factor: 2 },
      { source: '30m', target: '2h', factor: 4 },
      { source: '1h', target: '2h', factor: 2 },
      { source: '1h', target: '4h', factor: 4 },
      { source: '1h', target: '6h', factor: 6 },
      { source: '1h', target: '12h', factor: 12 },
      { source: '1h', target: '1d', factor: 24 },
      { source: '4h', target: '8h', factor: 2 },
      { source: '4h', target: '12h', factor: 3 },
      { source: '4h', target: '1d', factor: 6 },
      { source: '1d', target: '3d', factor: 3 },
      { source: '1d', target: '1w', factor: 7 }
    ]
  }

  /**
   * Inicializa estrutura de dados para cada timeframe
   */
  private initializeTimeframes(): void {
    this.config.enabledTimeframes.forEach(tf => {
      this.timeframes.set(tf, {
        timeframe: tf,
        candles: [],
        lastUpdate: 0,
        isActive: tf === this.activeTimeframe,
        isLoading: false
      })
    })
  }

  /**
   * Inicializa IndexedDB para cache persistente
   */
  private async initializeIndexedDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('CandleCache', 1)

      request.onerror = () => {
        console.error('Failed to open IndexedDB')
        reject(request.error)
      }

      request.onsuccess = () => {
        this.db = request.result
        console.log('✅ IndexedDB initialized')
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // Store para cada timeframe
        this.config.enabledTimeframes.forEach(tf => {
          if (!db.objectStoreNames.contains(tf)) {
            const store = db.createObjectStore(tf, { keyPath: 'time' })
            store.createIndex('time', 'time', { unique: true })
          }
        })
      }
    })
  }

  /**
   * Conecta ao WebSocket para o timeframe ativo
   */
  async connectActiveTimeframe(): Promise<void> {
    const tfData = this.timeframes.get(this.activeTimeframe)
    if (!tfData) return

    // Se já tem WebSocket, não precisa reconectar
    if (tfData.wsManager?.isConnected()) {
      console.log(`Already connected to ${this.activeTimeframe}`)
      return
    }

    tfData.isLoading = true

    // Criar WebSocket manager
    tfData.wsManager = new WebSocketManager({
      symbol: this.config.symbol,
      interval: this.activeTimeframe,
      testnet: this.config.testnet,
      onCandle: (candle) => this.handleNewCandle(this.activeTimeframe, candle),
      onError: (error) => this.handleWebSocketError(this.activeTimeframe, error),
      onConnect: () => this.handleWebSocketConnect(this.activeTimeframe),
      onDisconnect: (reason) => this.handleWebSocketDisconnect(this.activeTimeframe, reason)
    })

    try {
      await tfData.wsManager.connect()
      tfData.isLoading = false
    } catch (error) {
      tfData.isLoading = false
      tfData.error = error instanceof Error ? error.message : 'Connection failed'
      throw error
    }
  }

  /**
   * Muda o timeframe ativo
   */
  async switchTimeframe(newTimeframe: Timeframe): Promise<void> {
    if (!this.config.enabledTimeframes.includes(newTimeframe)) {
      throw new Error(`Timeframe ${newTimeframe} is not enabled`)
    }

    if (newTimeframe === this.activeTimeframe) {
      console.log(`Already on timeframe ${newTimeframe}`)
      return
    }

    console.log(`🔄 Switching from ${this.activeTimeframe} to ${newTimeframe}`)

    const oldTimeframe = this.activeTimeframe
    const oldData = this.timeframes.get(oldTimeframe)
    const newData = this.timeframes.get(newTimeframe)

    if (!oldData || !newData) return

    // Desconectar timeframe anterior
    if (oldData.wsManager) {
      oldData.wsManager.disconnect()
      oldData.wsManager = undefined
    }
    oldData.isActive = false

    // Ativar novo timeframe
    this.activeTimeframe = newTimeframe
    newData.isActive = true

    // Callback
    if (this.config.onTimeframeChange) {
      this.config.onTimeframeChange(oldTimeframe, newTimeframe)
    }

    // Conectar ao novo timeframe
    await this.connectActiveTimeframe()

    // Retornar dados cached se existirem
    if (newData.candles.length > 0 && this.config.onDataUpdate) {
      this.config.onDataUpdate(newTimeframe, newData.candles)
    }
  }

  /**
   * Handle novo candle do WebSocket
   */
  private handleNewCandle(timeframe: Timeframe, candle: Candle): void {
    const tfData = this.timeframes.get(timeframe)
    if (!tfData) return

    // Encontrar ou adicionar candle
    const existingIndex = tfData.candles.findIndex(c => c.time === candle.time)

    if (existingIndex >= 0) {
      // Atualizar candle existente
      tfData.candles[existingIndex] = candle
    } else {
      // Adicionar novo candle
      tfData.candles.push(candle)

      // Manter limite de candles
      const limit = this.config.maxCandlesPerTimeframe || this.DEFAULT_LIMITS[timeframe]
      if (tfData.candles.length > limit) {
        tfData.candles = tfData.candles.slice(-limit)
      }
    }

    tfData.lastUpdate = Date.now()

    // Salvar no cache
    this.saveToCache(timeframe, tfData.candles)

    // Propagar para timeframes maiores se possível
    this.propagateToHigherTimeframes(timeframe, candle)

    // Callback
    if (tfData.isActive && this.config.onDataUpdate) {
      this.config.onDataUpdate(timeframe, tfData.candles)
    }
  }

  /**
   * Propaga dados para timeframes maiores através de agregação
   */
  private propagateToHigherTimeframes(sourceTimeframe: Timeframe, candle: Candle): void {
    const rules = this.aggregationRules.filter(r => r.source === sourceTimeframe)

    rules.forEach(rule => {
      const targetData = this.timeframes.get(rule.target)
      if (!targetData || targetData.wsManager) return // Não propagar se já tem WebSocket

      // Verificar se temos candles suficientes para agregar
      const sourceData = this.timeframes.get(sourceTimeframe)
      if (!sourceData || sourceData.candles.length < rule.factor) return

      // Agregar últimos N candles
      const lastCandles = sourceData.candles.slice(-rule.factor)
      const aggregated = this.aggregateCandles(lastCandles, rule.target)

      if (aggregated) {
        this.handleNewCandle(rule.target, aggregated)
      }
    })
  }

  /**
   * Agrega múltiplos candles em um único candle de timeframe maior
   */
  private aggregateCandles(candles: Candle[], targetTimeframe: Timeframe): Candle | null {
    if (candles.length === 0) return null

    const targetMs = this.TIMEFRAME_MS[targetTimeframe]
    const firstTime = candles[0].time
    const alignedTime = Math.floor(firstTime / targetMs) * targetMs

    // Verificar se todos os candles pertencem ao mesmo período
    const belongsToSamePeriod = candles.every(c => {
      const periodStart = Math.floor(c.time / targetMs) * targetMs
      return periodStart === alignedTime
    })

    if (!belongsToSamePeriod) return null

    return {
      time: alignedTime,
      open: candles[0].open,
      high: Math.max(...candles.map(c => c.high)),
      low: Math.min(...candles.map(c => c.low)),
      close: candles[candles.length - 1].close,
      volume: candles.reduce((sum, c) => sum + c.volume, 0)
    }
  }

  /**
   * Carrega dados históricos para um timeframe
   */
  async loadHistoricalData(timeframe: Timeframe, limit: number = 1000): Promise<Candle[]> {
    const tfData = this.timeframes.get(timeframe)
    if (!tfData) {
      throw new Error(`Timeframe ${timeframe} not initialized`)
    }

    tfData.isLoading = true

    try {
      // Primeiro tentar carregar do cache
      const cached = await this.loadFromCache(timeframe)
      if (cached && cached.length > 0) {
        tfData.candles = cached
        tfData.lastUpdate = Date.now()
        tfData.isLoading = false

        console.log(`📦 Loaded ${cached.length} candles from cache for ${timeframe}`)

        if (this.config.onDataUpdate) {
          this.config.onDataUpdate(timeframe, cached)
        }

        return cached
      }

      // Se não tem cache, precisará buscar do backend
      // (será implementado com o HistoricalLoader)
      tfData.isLoading = false
      return []

    } catch (error) {
      tfData.isLoading = false
      tfData.error = error instanceof Error ? error.message : 'Failed to load data'
      throw error
    }
  }

  /**
   * Salva candles no cache
   */
  private async saveToCache(timeframe: Timeframe, candles: Candle[]): Promise<void> {
    const cacheKey = `${this.config.symbol}_${timeframe}`

    // Memory cache
    if (this.config.cacheStrategy === 'memory' || this.config.cacheStrategy === 'hybrid') {
      this.memoryCache.set(cacheKey, candles)
    }

    // IndexedDB cache
    if (this.db && (this.config.cacheStrategy === 'indexeddb' || this.config.cacheStrategy === 'hybrid')) {
      try {
        const transaction = this.db.transaction([timeframe], 'readwrite')
        const store = transaction.objectStore(timeframe)

        // Clear old data
        await new Promise((resolve, reject) => {
          const clearReq = store.clear()
          clearReq.onsuccess = () => resolve(undefined)
          clearReq.onerror = () => reject(clearReq.error)
        })

        // Add new data
        for (const candle of candles) {
          store.add(candle)
        }

        await new Promise((resolve, reject) => {
          transaction.oncomplete = () => resolve(undefined)
          transaction.onerror = () => reject(transaction.error)
        })

      } catch (error) {
        console.error(`Failed to save to IndexedDB for ${timeframe}:`, error)
      }
    }
  }

  /**
   * Carrega candles do cache
   */
  private async loadFromCache(timeframe: Timeframe): Promise<Candle[] | null> {
    const cacheKey = `${this.config.symbol}_${timeframe}`

    // Try memory cache first
    if (this.memoryCache.has(cacheKey)) {
      return this.memoryCache.get(cacheKey) || null
    }

    // Try IndexedDB
    if (this.db && (this.config.cacheStrategy === 'indexeddb' || this.config.cacheStrategy === 'hybrid')) {
      try {
        const transaction = this.db.transaction([timeframe], 'readonly')
        const store = transaction.objectStore(timeframe)

        const candles = await new Promise<Candle[]>((resolve, reject) => {
          const request = store.getAll()
          request.onsuccess = () => resolve(request.result)
          request.onerror = () => reject(request.error)
        })

        if (candles.length > 0) {
          // Update memory cache
          this.memoryCache.set(cacheKey, candles)
          return candles
        }
      } catch (error) {
        console.error(`Failed to load from IndexedDB for ${timeframe}:`, error)
      }
    }

    return null
  }

  /**
   * WebSocket event handlers
   */
  private handleWebSocketConnect(timeframe: Timeframe): void {
    console.log(`✅ WebSocket connected for ${timeframe}`)
    const tfData = this.timeframes.get(timeframe)
    if (tfData) {
      tfData.error = undefined
    }
  }

  private handleWebSocketDisconnect(timeframe: Timeframe, reason: string): void {
    console.log(`🔌 WebSocket disconnected for ${timeframe}: ${reason}`)
  }

  private handleWebSocketError(timeframe: Timeframe, error: Error): void {
    console.error(`❌ WebSocket error for ${timeframe}:`, error)
    const tfData = this.timeframes.get(timeframe)
    if (tfData) {
      tfData.error = error.message
    }
  }

  /**
   * Obtém dados do timeframe ativo
   */
  getActiveData(): Candle[] {
    const tfData = this.timeframes.get(this.activeTimeframe)
    return tfData?.candles || []
  }

  /**
   * Obtém dados de qualquer timeframe
   */
  getData(timeframe: Timeframe): Candle[] {
    const tfData = this.timeframes.get(timeframe)
    return tfData?.candles || []
  }

  /**
   * Obtém status de todos os timeframes
   */
  getStatus(): Record<Timeframe, {
    candleCount: number
    lastUpdate: number
    isActive: boolean
    isLoading: boolean
    isConnected: boolean
    error?: string
  }> {
    const status: any = {}

    this.timeframes.forEach((data, tf) => {
      status[tf] = {
        candleCount: data.candles.length,
        lastUpdate: data.lastUpdate,
        isActive: data.isActive,
        isLoading: data.isLoading,
        isConnected: data.wsManager?.isConnected() || false,
        error: data.error
      }
    })

    return status
  }

  /**
   * Limpa cache de um ou todos os timeframes
   */
  async clearCache(timeframe?: Timeframe): Promise<void> {
    if (timeframe) {
      // Clear specific timeframe
      const cacheKey = `${this.config.symbol}_${timeframe}`
      this.memoryCache.delete(cacheKey)

      if (this.db) {
        const transaction = this.db.transaction([timeframe], 'readwrite')
        const store = transaction.objectStore(timeframe)
        await new Promise((resolve, reject) => {
          const req = store.clear()
          req.onsuccess = () => resolve(undefined)
          req.onerror = () => reject(req.error)
        })
      }

      const tfData = this.timeframes.get(timeframe)
      if (tfData) {
        tfData.candles = []
        tfData.lastUpdate = 0
      }
    } else {
      // Clear all
      this.memoryCache.clear()

      for (const tf of this.config.enabledTimeframes) {
        await this.clearCache(tf)
      }
    }

    console.log(`🗑️ Cache cleared for ${timeframe || 'all timeframes'}`)
  }

  /**
   * Desconecta todos os WebSockets e limpa recursos
   */
  destroy(): void {
    this.timeframes.forEach(tfData => {
      if (tfData.wsManager) {
        tfData.wsManager.destroy()
      }
    })

    this.timeframes.clear()
    this.memoryCache.clear()

    if (this.db) {
      this.db.close()
    }

    console.log('🗑️ TimeframeManager destroyed')
  }

  /**
   * Obtém timeframe ativo
   */
  getActiveTimeframe(): Timeframe {
    return this.activeTimeframe
  }

  /**
   * Obtém lista de timeframes habilitados
   */
  getEnabledTimeframes(): Timeframe[] {
    return this.config.enabledTimeframes
  }

  /**
   * Verifica se um timeframe está habilitado
   */
  isTimeframeEnabled(timeframe: Timeframe): boolean {
    return this.config.enabledTimeframes.includes(timeframe)
  }

  /**
   * Adiciona um novo timeframe
   */
  enableTimeframe(timeframe: Timeframe): void {
    if (!this.config.enabledTimeframes.includes(timeframe)) {
      this.config.enabledTimeframes.push(timeframe)

      this.timeframes.set(timeframe, {
        timeframe,
        candles: [],
        lastUpdate: 0,
        isActive: false,
        isLoading: false
      })

      console.log(`✅ Enabled timeframe ${timeframe}`)
    }
  }

  /**
   * Remove um timeframe
   */
  disableTimeframe(timeframe: Timeframe): void {
    if (timeframe === this.activeTimeframe) {
      throw new Error('Cannot disable active timeframe')
    }

    const index = this.config.enabledTimeframes.indexOf(timeframe)
    if (index >= 0) {
      this.config.enabledTimeframes.splice(index, 1)

      const tfData = this.timeframes.get(timeframe)
      if (tfData?.wsManager) {
        tfData.wsManager.destroy()
      }

      this.timeframes.delete(timeframe)
      this.clearCache(timeframe)

      console.log(`❌ Disabled timeframe ${timeframe}`)
    }
  }
}