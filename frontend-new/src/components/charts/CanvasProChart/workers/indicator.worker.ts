/**
 * Indicator Worker - Calcula indicadores técnicos em thread separada
 * Usa a biblioteca technicalindicators para cálculos pesados
 */

import * as TI from 'technicalindicators'
import { Candle } from '../types'
import { AnyIndicatorConfig } from '../indicators/types'

// Tipos de mensagens
interface CalculateIndicatorMessage {
  type: 'CALCULATE'
  id: string
  timestamp: number
  indicator: AnyIndicatorConfig
  candles: Candle[]
}

interface CalculateBatchMessage {
  type: 'CALCULATE_BATCH'
  id: string
  timestamp: number
  indicators: AnyIndicatorConfig[]
  candles: Candle[]
}

interface ClearCacheMessage {
  type: 'CLEAR_CACHE'
  id: string
  timestamp: number
}

type WorkerMessage = CalculateIndicatorMessage | CalculateBatchMessage | ClearCacheMessage

// Tipos de respostas
interface IndicatorResult {
  id: string
  type: string
  values: number[]
  additionalLines?: Record<string, number[]>
}

interface CalculateResponse {
  type: 'CALCULATE_COMPLETE'
  id: string
  timestamp: number
  result: IndicatorResult
  calculationTime: number
}

interface BatchCalculateResponse {
  type: 'BATCH_COMPLETE'
  id: string
  timestamp: number
  results: IndicatorResult[]
  calculationTime: number
}

interface ErrorResponse {
  type: 'ERROR'
  id: string
  timestamp: number
  error: string
  stack?: string
}

type WorkerResponse = CalculateResponse | BatchCalculateResponse | ErrorResponse

// Cache de resultados
const cache = new Map<string, IndicatorResult>()

/**
 * Gera chave de cache baseada no indicador e dados
 */
function getCacheKey(indicator: AnyIndicatorConfig, candlesLength: number): string {
  return `${indicator.id}_${indicator.type}_${JSON.stringify(indicator.params)}_${candlesLength}`
}

/**
 * Calcula um único indicador
 */
function calculateIndicator(indicator: AnyIndicatorConfig, candles: Candle[]): IndicatorResult {
  const cacheKey = getCacheKey(indicator, candles.length)

  // Verificar cache
  if (cache.has(cacheKey)) {
    console.log(`📊 Cache hit for ${indicator.type}`)
    return cache.get(cacheKey)!
  }

  console.log(`📊 Calculating ${indicator.type}...`)

  const result: IndicatorResult = {
    id: indicator.id,
    type: indicator.type,
    values: [],
    additionalLines: {}
  }

  // Extrair dados necessários
  const closes = candles.map(c => c.close)
  const highs = candles.map(c => c.high)
  const lows = candles.map(c => c.low)
  const opens = candles.map(c => c.open)
  const volumes = candles.map(c => c.volume)

  try {
    switch (indicator.type) {
      // Moving Averages
      case 'SMA': {
        const params = indicator.params as { period: number }
        const sma = TI.SMA.calculate({
          period: params.period,
          values: closes
        })
        result.values = padArray(sma, candles.length, params.period - 1)
        break
      }

      case 'EMA': {
        const params = indicator.params as { period: number }
        const ema = TI.EMA.calculate({
          period: params.period,
          values: closes
        })
        result.values = padArray(ema, candles.length, params.period - 1)
        break
      }

      case 'WMA': {
        const params = indicator.params as { period: number }
        const wma = TI.WMA.calculate({
          period: params.period,
          values: closes
        })
        result.values = padArray(wma, candles.length, params.period - 1)
        break
      }

      // Oscillators
      case 'RSI': {
        const params = indicator.params as { period: number }
        const rsi = TI.RSI.calculate({
          period: params.period,
          values: closes
        })
        result.values = padArray(rsi, candles.length, params.period)

        // Adicionar níveis de sobrecompra/sobrevenda
        result.additionalLines = {
          overbought: new Array(candles.length).fill(70),
          oversold: new Array(candles.length).fill(30)
        }
        break
      }

      case 'MACD': {
        const params = indicator.params as {
          fastPeriod: number
          slowPeriod: number
          signalPeriod: number
        }

        const macdResult = TI.MACD.calculate({
          values: closes,
          fastPeriod: params.fastPeriod,
          slowPeriod: params.slowPeriod,
          signalPeriod: params.signalPeriod,
          SimpleMAOscillator: false,
          SimpleMASignal: false
        })

        const startIndex = params.slowPeriod + params.signalPeriod - 2
        const macdValues: number[] = new Array(candles.length).fill(NaN)
        const signalValues: number[] = new Array(candles.length).fill(NaN)
        const histogramValues: number[] = new Array(candles.length).fill(NaN)

        macdResult.forEach((item, i) => {
          const index = startIndex + i
          if (index < candles.length) {
            macdValues[index] = item.MACD || NaN
            signalValues[index] = item.signal || NaN
            histogramValues[index] = item.histogram || NaN
          }
        })

        result.values = macdValues
        result.additionalLines = {
          signal: signalValues,
          histogram: histogramValues
        }
        break
      }

      case 'STOCH': {
        const params = indicator.params as {
          period: number
          signalPeriod: number
        }

        const stoch = TI.Stochastic.calculate({
          high: highs,
          low: lows,
          close: closes,
          period: params.period,
          signalPeriod: params.signalPeriod
        })

        const kValues: number[] = new Array(candles.length).fill(NaN)
        const dValues: number[] = new Array(candles.length).fill(NaN)

        stoch.forEach((item, i) => {
          const index = params.period - 1 + i
          if (index < candles.length) {
            kValues[index] = item.k
            dValues[index] = item.d
          }
        })

        result.values = kValues
        result.additionalLines = { d: dValues }
        break
      }

      // Volatility Indicators
      case 'BB': {
        const params = indicator.params as {
          period: number
          stdDev: number
        }

        const bb = TI.BollingerBands.calculate({
          period: params.period,
          values: closes,
          stdDev: params.stdDev
        })

        const upperValues: number[] = new Array(candles.length).fill(NaN)
        const middleValues: number[] = new Array(candles.length).fill(NaN)
        const lowerValues: number[] = new Array(candles.length).fill(NaN)

        bb.forEach((item, i) => {
          const index = params.period - 1 + i
          if (index < candles.length) {
            upperValues[index] = item.upper
            middleValues[index] = item.middle
            lowerValues[index] = item.lower
          }
        })

        result.values = middleValues
        result.additionalLines = {
          upper: upperValues,
          lower: lowerValues
        }
        break
      }

      case 'ATR': {
        const params = indicator.params as { period: number }
        const atr = TI.ATR.calculate({
          high: highs,
          low: lows,
          close: closes,
          period: params.period
        })
        result.values = padArray(atr, candles.length, params.period)
        break
      }

      // Volume Indicators
      case 'OBV': {
        const obv = TI.OBV.calculate({
          close: closes,
          volume: volumes
        })
        result.values = padArray(obv, candles.length, 0)
        break
      }

      case 'VWAP': {
        const vwap = TI.VWAP.calculate({
          high: highs,
          low: lows,
          close: closes,
          volume: volumes
        })
        result.values = vwap
        break
      }

      // Trend Indicators
      case 'ADX': {
        const params = indicator.params as { period: number }
        const adx = TI.ADX.calculate({
          high: highs,
          low: lows,
          close: closes,
          period: params.period
        })

        const adxValues: number[] = new Array(candles.length).fill(NaN)
        const pdiValues: number[] = new Array(candles.length).fill(NaN)
        const mdiValues: number[] = new Array(candles.length).fill(NaN)

        adx.forEach((item, i) => {
          const index = params.period * 2 - 1 + i
          if (index < candles.length) {
            adxValues[index] = item.adx
            pdiValues[index] = item.pdi
            mdiValues[index] = item.mdi
          }
        })

        result.values = adxValues
        result.additionalLines = {
          pdi: pdiValues,
          mdi: mdiValues
        }
        break
      }

      case 'CCI': {
        const params = indicator.params as { period: number }
        const cci = TI.CCI.calculate({
          high: highs,
          low: lows,
          close: closes,
          period: params.period
        })
        result.values = padArray(cci, candles.length, params.period - 1)
        break
      }

      case 'MFI': {
        const params = indicator.params as { period: number }
        const mfi = TI.MFI.calculate({
          high: highs,
          low: lows,
          close: closes,
          volume: volumes,
          period: params.period
        })
        result.values = padArray(mfi, candles.length, params.period)
        break
      }

      case 'WILLR': {
        const params = indicator.params as { period: number }
        const willr = TI.WilliamsR.calculate({
          high: highs,
          low: lows,
          close: closes,
          period: params.period
        })
        result.values = padArray(willr, candles.length, params.period - 1)
        break
      }

      default:
        console.warn(`Unknown indicator type: ${indicator.type}`)
        result.values = new Array(candles.length).fill(NaN)
    }

    // Salvar no cache
    cache.set(cacheKey, result)

    return result
  } catch (error) {
    console.error(`Error calculating ${indicator.type}:`, error)
    result.values = new Array(candles.length).fill(NaN)
    return result
  }
}

/**
 * Preenche array com NaN no início
 */
function padArray(values: number[], targetLength: number, padStart: number): number[] {
  const result = new Array(targetLength).fill(NaN)
  values.forEach((value, i) => {
    result[padStart + i] = value
  })
  return result
}

/**
 * Processa mensagem de cálculo único
 */
function handleCalculate(msg: CalculateIndicatorMessage): void {
  const startTime = performance.now()

  try {
    const result = calculateIndicator(msg.indicator, msg.candles)
    const calculationTime = performance.now() - startTime

    const response: CalculateResponse = {
      type: 'CALCULATE_COMPLETE',
      id: msg.id,
      timestamp: Date.now(),
      result,
      calculationTime
    }

    self.postMessage(response)
    console.log(`✅ ${msg.indicator.type} calculated in ${calculationTime.toFixed(2)}ms`)
  } catch (error) {
    const errorResponse: ErrorResponse = {
      type: 'ERROR',
      id: msg.id,
      timestamp: Date.now(),
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    }
    self.postMessage(errorResponse)
  }
}

/**
 * Processa mensagem de cálculo em lote
 */
function handleBatchCalculate(msg: CalculateBatchMessage): void {
  const startTime = performance.now()

  try {
    const results: IndicatorResult[] = []

    for (const indicator of msg.indicators) {
      if (indicator.enabled) {
        results.push(calculateIndicator(indicator, msg.candles))
      }
    }

    const calculationTime = performance.now() - startTime

    const response: BatchCalculateResponse = {
      type: 'BATCH_COMPLETE',
      id: msg.id,
      timestamp: Date.now(),
      results,
      calculationTime
    }

    self.postMessage(response)
    console.log(`✅ Batch (${msg.indicators.length} indicators) calculated in ${calculationTime.toFixed(2)}ms`)
  } catch (error) {
    const errorResponse: ErrorResponse = {
      type: 'ERROR',
      id: msg.id,
      timestamp: Date.now(),
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    }
    self.postMessage(errorResponse)
  }
}

/**
 * Limpa o cache
 */
function handleClearCache(): void {
  const previousSize = cache.size
  cache.clear()
  console.log(`🧹 Cache cleared (${previousSize} entries removed)`)
}

/**
 * Message handler principal
 */
self.addEventListener('message', (event: MessageEvent<WorkerMessage>) => {
  const msg = event.data

  switch (msg.type) {
    case 'CALCULATE':
      handleCalculate(msg as CalculateIndicatorMessage)
      break

    case 'CALCULATE_BATCH':
      handleBatchCalculate(msg as CalculateBatchMessage)
      break

    case 'CLEAR_CACHE':
      handleClearCache()
      break

    default:
      console.warn('Unknown message type:', (msg as any).type)
  }
})

console.log('📊 Indicator Worker loaded')

// Exportar tipos para uso externo
export type {
  CalculateIndicatorMessage,
  CalculateBatchMessage,
  ClearCacheMessage,
  CalculateResponse,
  BatchCalculateResponse,
  ErrorResponse,
  IndicatorResult
}