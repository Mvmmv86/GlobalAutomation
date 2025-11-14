/**
 * HistoricalLoader - Carregador de dados históricos da Binance
 * Sistema profissional com cache, paginação e rate limiting
 */

import { Candle } from '../types'
import { Timeframe } from './TimeframeManager'

export interface HistoricalConfig {
  symbol: string
  testnet?: boolean
  apiKey?: string
  apiSecret?: string
  maxRetries?: number
  retryDelay?: number
  rateLimit?: number // requests per minute
  cacheEnabled?: boolean
  onProgress?: (loaded: number, total: number) => void
  onError?: (error: Error) => void
}

interface CacheEntry {
  symbol: string
  timeframe: Timeframe
  startTime: number
  endTime: number
  candles: Candle[]
  timestamp: number
}

export class HistoricalLoader {
  private config: HistoricalConfig
  private cache: Map<string, CacheEntry> = new Map()
  private requestQueue: Array<() => Promise<void>> = []
  private isProcessing = false
  private lastRequestTime = 0
  private requestCount = 0
  private requestResetTime = Date.now()

  // Binance API endpoints
  private readonly API_BASE_URL = 'https://api.binance.com'
  private readonly API_TESTNET_URL = 'https://testnet.binance.vision'
  private readonly API_FUTURES_URL = 'https://fapi.binance.com'
  private readonly API_FUTURES_TESTNET_URL = 'https://testnet.binancefuture.com'

  // Limites da API Binance
  private readonly MAX_KLINES_PER_REQUEST = 1000
  private readonly WEIGHT_PER_REQUEST = 1
  private readonly MAX_WEIGHT_PER_MINUTE = 1200

  // Mapeamento de timeframes para intervalo da Binance
  private readonly INTERVAL_MAP: Record<Timeframe, string> = {
    '1m': '1m',
    '3m': '3m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1h': '1h',
    '2h': '2h',
    '4h': '4h',
    '6h': '6h',
    '8h': '8h',
    '12h': '12h',
    '1d': '1d',
    '3d': '3d',
    '1w': '1w',
    '1M': '1M'
  }

  constructor(config: HistoricalConfig) {
    this.config = {
      maxRetries: 3,
      retryDelay: 1000,
      rateLimit: 100, // 100 requests per minute (conservative)
      cacheEnabled: true,
      ...config
    }

    console.log('📚 HistoricalLoader initialized for', config.symbol)
  }

  /**
   * Carrega dados históricos
   */
  async load(
    timeframe: Timeframe,
    startTime?: number,
    endTime?: number,
    limit?: number
  ): Promise<Candle[]> {
    const cacheKey = this.getCacheKey(this.config.symbol, timeframe, startTime, endTime)

    // Verificar cache
    if (this.config.cacheEnabled && this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey)!
      const age = Date.now() - cached.timestamp

      // Cache válido por 5 minutos
      if (age < 300000) {
        console.log(`📦 Using cached data for ${timeframe}`)
        return cached.candles
      }
    }

    // Calcular parâmetros
    const now = Date.now()
    const end = endTime || now
    const start = startTime || this.calculateStartTime(timeframe, end, limit || 1000)

    console.log(`📊 Loading ${timeframe} data from ${new Date(start).toISOString()} to ${new Date(end).toISOString()}`)

    // Fazer requisições em batches se necessário
    const candles = await this.fetchKlinesBatched(timeframe, start, end)

    // Salvar no cache
    if (this.config.cacheEnabled) {
      this.cache.set(cacheKey, {
        symbol: this.config.symbol,
        timeframe,
        startTime: start,
        endTime: end,
        candles,
        timestamp: Date.now()
      })
    }

    return candles
  }

  /**
   * Carrega dados em lotes para períodos grandes
   */
  private async fetchKlinesBatched(
    timeframe: Timeframe,
    startTime: number,
    endTime: number
  ): Promise<Candle[]> {
    const allCandles: Candle[] = []
    const batchSize = this.MAX_KLINES_PER_REQUEST
    const interval = this.getTimeframeMs(timeframe)

    // Calcular número de candles necessários
    const totalCandles = Math.ceil((endTime - startTime) / interval)
    const batches = Math.ceil(totalCandles / batchSize)

    console.log(`📊 Need ${totalCandles} candles, will fetch in ${batches} batch(es)`)

    let currentStart = startTime

    for (let i = 0; i < batches; i++) {
      const batchEnd = Math.min(
        currentStart + (batchSize * interval),
        endTime
      )

      try {
        const candles = await this.fetchKlines(timeframe, currentStart, batchEnd, batchSize)
        allCandles.push(...candles)

        // Progress callback
        if (this.config.onProgress) {
          this.config.onProgress(allCandles.length, totalCandles)
        }

        currentStart = batchEnd

        // Se chegou ao fim, parar
        if (currentStart >= endTime) break

      } catch (error) {
        console.error(`Failed to fetch batch ${i + 1}/${batches}:`, error)

        if (this.config.onError) {
          this.config.onError(error instanceof Error ? error : new Error('Fetch failed'))
        }

        // Continuar com os dados que conseguimos
        break
      }
    }

    // Ordenar por tempo e remover duplicatas
    const uniqueCandles = this.deduplicateCandles(allCandles)

    console.log(`✅ Loaded ${uniqueCandles.length} unique candles`)
    return uniqueCandles
  }

  /**
   * Faz uma requisição de klines para a API da Binance
   */
  private async fetchKlines(
    timeframe: Timeframe,
    startTime: number,
    endTime: number,
    limit: number
  ): Promise<Candle[]> {
    // Rate limiting
    await this.waitForRateLimit()

    const baseUrl = this.getApiUrl()
    const symbol = this.config.symbol.toUpperCase().replace('/', '')
    const interval = this.INTERVAL_MAP[timeframe]

    const params = new URLSearchParams({
      symbol,
      interval,
      startTime: startTime.toString(),
      endTime: endTime.toString(),
      limit: Math.min(limit, this.MAX_KLINES_PER_REQUEST).toString()
    })

    const url = `${baseUrl}/api/v3/klines?${params}`

    let retries = 0
    const maxRetries = this.config.maxRetries || 3

    while (retries < maxRetries) {
      try {
        const response = await fetch(url, {
          method: 'GET',
          headers: this.getHeaders()
        })

        if (!response.ok) {
          const error = await response.text()
          throw new Error(`API Error: ${response.status} - ${error}`)
        }

        const data = await response.json()

        // Converter para formato Candle
        const candles: Candle[] = data.map((kline: any[]) => ({
          time: kline[0],
          open: parseFloat(kline[1]),
          high: parseFloat(kline[2]),
          low: parseFloat(kline[3]),
          close: parseFloat(kline[4]),
          volume: parseFloat(kline[5])
        }))

        // Atualizar contadores de rate limit
        this.requestCount++
        this.lastRequestTime = Date.now()

        return candles

      } catch (error) {
        retries++
        console.error(`Attempt ${retries}/${maxRetries} failed:`, error)

        if (retries < maxRetries) {
          const delay = this.config.retryDelay || 1000
          await new Promise(resolve => setTimeout(resolve, delay * retries))
        } else {
          throw error
        }
      }
    }

    return []
  }

  /**
   * Carrega dados mais recentes (útil para preencher gaps)
   */
  async loadRecent(timeframe: Timeframe, limit: number = 100): Promise<Candle[]> {
    const now = Date.now()
    const interval = this.getTimeframeMs(timeframe)
    const startTime = now - (interval * limit)

    return this.load(timeframe, startTime, now, limit)
  }

  /**
   * Carrega dados de um período específico
   */
  async loadRange(
    timeframe: Timeframe,
    startDate: Date | string | number,
    endDate: Date | string | number
  ): Promise<Candle[]> {
    const start = typeof startDate === 'number' ? startDate : new Date(startDate).getTime()
    const end = typeof endDate === 'number' ? endDate : new Date(endDate).getTime()

    return this.load(timeframe, start, end)
  }

  /**
   * Preenche gaps nos dados existentes
   */
  async fillGaps(timeframe: Timeframe, existingCandles: Candle[]): Promise<Candle[]> {
    if (existingCandles.length < 2) {
      return existingCandles
    }

    // Ordenar candles
    const sorted = [...existingCandles].sort((a, b) => a.time - b.time)
    const interval = this.getTimeframeMs(timeframe)
    const gaps: Array<{ start: number; end: number }> = []

    // Encontrar gaps
    for (let i = 1; i < sorted.length; i++) {
      const expectedTime = sorted[i - 1].time + interval
      const actualTime = sorted[i].time

      if (actualTime - expectedTime > interval) {
        gaps.push({
          start: expectedTime,
          end: actualTime - interval
        })
      }
    }

    if (gaps.length === 0) {
      console.log('✅ No gaps found')
      return sorted
    }

    console.log(`📊 Found ${gaps.length} gap(s) to fill`)

    // Preencher cada gap
    const newCandles: Candle[] = []

    for (const gap of gaps) {
      try {
        const gapCandles = await this.load(timeframe, gap.start, gap.end)
        newCandles.push(...gapCandles)
      } catch (error) {
        console.error(`Failed to fill gap from ${new Date(gap.start)} to ${new Date(gap.end)}:`, error)
      }
    }

    // Mesclar e deduplica
    const merged = [...sorted, ...newCandles]
    return this.deduplicateCandles(merged)
  }

  /**
   * Aguarda rate limit
   */
  private async waitForRateLimit(): Promise<void> {
    // Reset contador se passou 1 minuto
    const now = Date.now()
    if (now - this.requestResetTime > 60000) {
      this.requestCount = 0
      this.requestResetTime = now
    }

    // Se excedeu limite, aguardar
    if (this.requestCount >= (this.config.rateLimit || 100)) {
      const waitTime = 60000 - (now - this.requestResetTime)
      if (waitTime > 0) {
        console.log(`⏳ Rate limit reached, waiting ${Math.ceil(waitTime / 1000)}s`)
        await new Promise(resolve => setTimeout(resolve, waitTime))
        this.requestCount = 0
        this.requestResetTime = Date.now()
      }
    }

    // Aguardar entre requests para não sobrecarregar
    const timeSinceLastRequest = now - this.lastRequestTime
    if (timeSinceLastRequest < 100) {
      await new Promise(resolve => setTimeout(resolve, 100 - timeSinceLastRequest))
    }
  }

  /**
   * Calcula tempo inicial baseado no limite
   */
  private calculateStartTime(timeframe: Timeframe, endTime: number, limit: number): number {
    const interval = this.getTimeframeMs(timeframe)
    return endTime - (interval * limit)
  }

  /**
   * Obtém duração do timeframe em millisegundos
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
   * Remove candles duplicados
   */
  private deduplicateCandles(candles: Candle[]): Candle[] {
    const seen = new Set<number>()
    const unique: Candle[] = []

    for (const candle of candles) {
      if (!seen.has(candle.time)) {
        seen.add(candle.time)
        unique.push(candle)
      }
    }

    return unique.sort((a, b) => a.time - b.time)
  }

  /**
   * Gera chave de cache
   */
  private getCacheKey(symbol: string, timeframe: Timeframe, start?: number, end?: number): string {
    return `${symbol}_${timeframe}_${start || 'auto'}_${end || 'auto'}`
  }

  /**
   * Obtém URL da API apropriada
   */
  private getApiUrl(): string {
    // TODO: Detectar se é futures ou spot baseado no símbolo
    return this.config.testnet ? this.API_TESTNET_URL : this.API_BASE_URL
  }

  /**
   * Obtém headers para requisição
   */
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json'
    }

    // Se tiver API key, adicionar
    if (this.config.apiKey) {
      headers['X-MBX-APIKEY'] = this.config.apiKey
    }

    return headers
  }

  /**
   * Limpa cache
   */
  clearCache(): void {
    this.cache.clear()
    console.log('🗑️ Cache cleared')
  }

  /**
   * Obtém estatísticas do loader
   */
  getStats(): {
    cacheSize: number
    requestCount: number
    lastRequestTime: number
    rateLimitRemaining: number
  } {
    const now = Date.now()
    const elapsed = now - this.requestResetTime
    const remaining = elapsed > 60000 ?
      this.config.rateLimit || 100 :
      Math.max(0, (this.config.rateLimit || 100) - this.requestCount)

    return {
      cacheSize: this.cache.size,
      requestCount: this.requestCount,
      lastRequestTime: this.lastRequestTime,
      rateLimitRemaining: remaining
    }
  }

  /**
   * Valida dados carregados
   */
  validateCandles(candles: Candle[]): {
    valid: boolean
    issues: string[]
  } {
    const issues: string[] = []

    if (candles.length === 0) {
      return { valid: true, issues: [] }
    }

    // Verificar ordem temporal
    for (let i = 1; i < candles.length; i++) {
      if (candles[i].time <= candles[i - 1].time) {
        issues.push(`Candle at index ${i} is out of order`)
      }
    }

    // Verificar valores OHLC
    for (let i = 0; i < candles.length; i++) {
      const c = candles[i]

      if (c.high < c.low) {
        issues.push(`Candle at index ${i}: high < low`)
      }

      if (c.open > c.high || c.open < c.low) {
        issues.push(`Candle at index ${i}: open outside high/low range`)
      }

      if (c.close > c.high || c.close < c.low) {
        issues.push(`Candle at index ${i}: close outside high/low range`)
      }

      if (c.volume < 0) {
        issues.push(`Candle at index ${i}: negative volume`)
      }
    }

    return {
      valid: issues.length === 0,
      issues
    }
  }
}