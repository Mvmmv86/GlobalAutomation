/**
 * Extended Calculator Functions - 50+ Technical Indicators
 * Implementações customizadas para indicadores avançados
 */

import { Candle } from '../types'
import { IndicatorResult } from './types'
import {
  ExtendedIndicatorType,
  AnyExtendedIndicatorConfig,
  ALMAConfig,
  DEMAConfig,
  TEMAConfig,
  HMAConfig,
  KAMAConfig,
  SMMAConfig,
  VWMAConfig,
  ZLEMAConfig,
  T3Config,
  VIDYAConfig,
  CMOConfig,
  DPOConfig,
  UOConfig,
  TSIConfig,
  PPOConfig,
  DCConfig,
  BBWConfig,
  BBPConfig,
  NATRConfig,
  RVIConfig,
  CHOPConfig,
  SuperTrendConfig,
  CMFConfig,
  EMVConfig,
  KVOConfig,
  NVIConfig,
  PVIConfig,
  PVTConfig,
  PIVOTConfig,
  ZIGZAGConfig,
  FRACTALConfig,
  AROONConfig,
  BOPConfig,
  VORTEXConfig,
  ELDER_RAYConfig,
  GATORConfig,
  MASS_INDEXConfig,
  SCHAFFConfig
} from './extendedTypes'

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Simple Moving Average
 */
function sma(values: number[], period: number): number[] {
  const result: number[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(NaN)
    } else {
      const sum = values.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
      result.push(sum / period)
    }
  }
  return result
}

/**
 * Exponential Moving Average
 */
function ema(values: number[], period: number): number[] {
  const result: number[] = []
  const multiplier = 2 / (period + 1)

  // Calculate initial SMA
  let sum = 0
  for (let i = 0; i < period; i++) {
    if (i < values.length) {
      sum += values[i]
    }
  }
  let prevEMA = sum / period

  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(NaN)
    } else if (i === period - 1) {
      result.push(prevEMA)
    } else {
      const currentEMA = (values[i] - prevEMA) * multiplier + prevEMA
      result.push(currentEMA)
      prevEMA = currentEMA
    }
  }

  return result
}

/**
 * Weighted Moving Average
 */
function wma(values: number[], period: number): number[] {
  const result: number[] = []
  const weightSum = (period * (period + 1)) / 2

  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(NaN)
    } else {
      let weightedSum = 0
      for (let j = 0; j < period; j++) {
        weightedSum += values[i - period + 1 + j] * (j + 1)
      }
      result.push(weightedSum / weightSum)
    }
  }

  return result
}

/**
 * True Range
 */
function trueRange(high: number, low: number, prevClose?: number): number {
  if (prevClose === undefined) {
    return high - low
  }
  return Math.max(
    high - low,
    Math.abs(high - prevClose),
    Math.abs(low - prevClose)
  )
}

/**
 * Standard Deviation
 */
function stdDev(values: number[], period: number): number[] {
  const result: number[] = []
  const means = sma(values, period)

  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(NaN)
    } else {
      const mean = means[i]
      const slice = values.slice(i - period + 1, i + 1)
      const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / period
      result.push(Math.sqrt(variance))
    }
  }

  return result
}

// ============================================
// TREND FOLLOWING INDICATORS
// ============================================

/**
 * Arnaud Legoux Moving Average (ALMA)
 */
export function calculateALMA(config: ALMAConfig, candles: Candle[]): IndicatorResult {
  const { period, offset, sigma } = config.params
  const closes = candles.map(c => c.close)
  const values: number[] = []

  const m = Math.floor(offset * (period - 1))
  const s = period / sigma

  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      values.push(NaN)
    } else {
      let weightSum = 0
      let sum = 0

      for (let j = 0; j < period; j++) {
        const weight = Math.exp(-Math.pow((j - m), 2) / (2 * Math.pow(s, 2)))
        weightSum += weight
        sum += closes[i - period + 1 + j] * weight
      }

      values.push(sum / weightSum)
    }
  }

  return {
    id: config.id,
    type: 'ALMA',
    values
  }
}

/**
 * Double Exponential Moving Average (DEMA)
 */
export function calculateDEMA(config: DEMAConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const closes = candles.map(c => c.close)

  const ema1 = ema(closes, period)
  const ema2 = ema(ema1.filter(v => !isNaN(v)), period)

  const values: number[] = []
  let ema2Index = 0

  for (let i = 0; i < closes.length; i++) {
    if (isNaN(ema1[i]) || ema2Index >= ema2.length) {
      values.push(NaN)
    } else {
      values.push(2 * ema1[i] - ema2[ema2Index])
      if (!isNaN(ema1[i])) ema2Index++
    }
  }

  return {
    id: config.id,
    type: 'DEMA',
    values
  }
}

/**
 * Triple Exponential Moving Average (TEMA)
 */
export function calculateTEMA(config: TEMAConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const closes = candles.map(c => c.close)

  const ema1 = ema(closes, period)
  const ema2 = ema(ema1.filter(v => !isNaN(v)), period)
  const ema3 = ema(ema2.filter(v => !isNaN(v)), period)

  const values: number[] = []
  let ema2Index = 0
  let ema3Index = 0

  for (let i = 0; i < closes.length; i++) {
    if (isNaN(ema1[i]) || ema2Index >= ema2.length || ema3Index >= ema3.length) {
      values.push(NaN)
    } else {
      values.push(3 * ema1[i] - 3 * ema2[ema2Index] + ema3[ema3Index])
      if (!isNaN(ema1[i])) {
        ema2Index++
        if (!isNaN(ema2[ema2Index - 1])) ema3Index++
      }
    }
  }

  return {
    id: config.id,
    type: 'TEMA',
    values
  }
}

/**
 * Hull Moving Average (HMA)
 */
export function calculateHMA(config: HMAConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const closes = candles.map(c => c.close)

  const halfPeriod = Math.floor(period / 2)
  const sqrtPeriod = Math.floor(Math.sqrt(period))

  const wma1 = wma(closes, halfPeriod)
  const wma2 = wma(closes, period)

  const raw: number[] = []
  for (let i = 0; i < closes.length; i++) {
    if (isNaN(wma1[i]) || isNaN(wma2[i])) {
      raw.push(NaN)
    } else {
      raw.push(2 * wma1[i] - wma2[i])
    }
  }

  const values = wma(raw.filter(v => !isNaN(v)), sqrtPeriod)

  // Pad with NaN
  const padCount = closes.length - values.length
  const result = new Array(padCount).fill(NaN).concat(values)

  return {
    id: config.id,
    type: 'HMA',
    values: result
  }
}

/**
 * Kaufman Adaptive Moving Average (KAMA)
 */
export function calculateKAMA(config: KAMAConfig, candles: Candle[]): IndicatorResult {
  const { period, fastPeriod, slowPeriod } = config.params
  const closes = candles.map(c => c.close)
  const values: number[] = []

  const fastSC = 2 / (fastPeriod + 1)
  const slowSC = 2 / (slowPeriod + 1)

  for (let i = 0; i < closes.length; i++) {
    if (i < period) {
      values.push(NaN)
    } else if (i === period) {
      values.push(closes[i])
    } else {
      // Calculate Efficiency Ratio
      const change = Math.abs(closes[i] - closes[i - period])
      let volatility = 0
      for (let j = 1; j <= period; j++) {
        volatility += Math.abs(closes[i - j + 1] - closes[i - j])
      }
      const er = volatility !== 0 ? change / volatility : 0

      // Calculate Smoothing Constant
      const sc = Math.pow((er * (fastSC - slowSC) + slowSC), 2)

      // Calculate KAMA
      const kama = values[i - 1] + sc * (closes[i] - values[i - 1])
      values.push(kama)
    }
  }

  return {
    id: config.id,
    type: 'KAMA',
    values
  }
}

// ============================================
// MOMENTUM OSCILLATORS
// ============================================

/**
 * Chande Momentum Oscillator (CMO)
 */
export function calculateCMO(config: CMOConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const closes = candles.map(c => c.close)
  const values: number[] = []

  for (let i = 0; i < closes.length; i++) {
    if (i < period) {
      values.push(NaN)
    } else {
      let upSum = 0
      let downSum = 0

      for (let j = 1; j <= period; j++) {
        const diff = closes[i - j + 1] - closes[i - j]
        if (diff > 0) {
          upSum += diff
        } else {
          downSum += Math.abs(diff)
        }
      }

      const cmo = (upSum + downSum) !== 0
        ? ((upSum - downSum) / (upSum + downSum)) * 100
        : 0
      values.push(cmo)
    }
  }

  return {
    id: config.id,
    type: 'CMO',
    values
  }
}

/**
 * Detrended Price Oscillator (DPO)
 */
export function calculateDPO(config: DPOConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const closes = candles.map(c => c.close)
  const smaValues = sma(closes, period)
  const values: number[] = []

  const shift = Math.floor(period / 2) + 1

  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      values.push(NaN)
    } else if (i - shift < 0 || isNaN(smaValues[i - shift])) {
      values.push(NaN)
    } else {
      values.push(closes[i - shift] - smaValues[i])
    }
  }

  return {
    id: config.id,
    type: 'DPO',
    values
  }
}

/**
 * Ultimate Oscillator (UO)
 */
export function calculateUO(config: UOConfig, candles: Candle[]): IndicatorResult {
  const { period1, period2, period3 } = config.params
  const values: number[] = []

  for (let i = 0; i < candles.length; i++) {
    if (i < Math.max(period1, period2, period3)) {
      values.push(NaN)
    } else {
      let bp1 = 0, bp2 = 0, bp3 = 0
      let tr1 = 0, tr2 = 0, tr3 = 0

      for (let j = 0; j < Math.max(period1, period2, period3); j++) {
        const idx = i - j
        const buyingPressure = candles[idx].close - Math.min(candles[idx].low, candles[idx - 1]?.close || candles[idx].low)
        const trueR = trueRange(candles[idx].high, candles[idx].low, candles[idx - 1]?.close)

        if (j < period1) {
          bp1 += buyingPressure
          tr1 += trueR
        }
        if (j < period2) {
          bp2 += buyingPressure
          tr2 += trueR
        }
        if (j < period3) {
          bp3 += buyingPressure
          tr3 += trueR
        }
      }

      const avg1 = bp1 / tr1
      const avg2 = bp2 / tr2
      const avg3 = bp3 / tr3

      const uo = ((avg1 * 4) + (avg2 * 2) + avg3) / 7 * 100
      values.push(uo)
    }
  }

  return {
    id: config.id,
    type: 'UO',
    values
  }
}

// ============================================
// VOLATILITY INDICATORS
// ============================================

/**
 * Donchian Channels (DC)
 */
export function calculateDC(config: DCConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const upper: number[] = []
  const lower: number[] = []
  const middle: number[] = []

  for (let i = 0; i < candles.length; i++) {
    if (i < period - 1) {
      upper.push(NaN)
      lower.push(NaN)
      middle.push(NaN)
    } else {
      const slice = candles.slice(i - period + 1, i + 1)
      const high = Math.max(...slice.map(c => c.high))
      const low = Math.min(...slice.map(c => c.low))
      const mid = (high + low) / 2

      upper.push(high)
      lower.push(low)
      middle.push(mid)
    }
  }

  return {
    id: config.id,
    type: 'DC',
    values: middle,
    additionalLines: {
      upper,
      lower
    }
  }
}

/**
 * Bollinger Band Width (BBW)
 */
export function calculateBBW(config: BBWConfig, candles: Candle[]): IndicatorResult {
  const { period, stdDev: mult } = config.params
  const closes = candles.map(c => c.close)
  const smaValues = sma(closes, period)
  const stdDevValues = stdDev(closes, period)
  const values: number[] = []

  for (let i = 0; i < closes.length; i++) {
    if (isNaN(smaValues[i]) || isNaN(stdDevValues[i])) {
      values.push(NaN)
    } else {
      const upper = smaValues[i] + (stdDevValues[i] * mult)
      const lower = smaValues[i] - (stdDevValues[i] * mult)
      const width = ((upper - lower) / smaValues[i]) * 100
      values.push(width)
    }
  }

  return {
    id: config.id,
    type: 'BBW',
    values
  }
}

/**
 * SuperTrend Indicator
 */
export function calculateSuperTrend(config: SuperTrendConfig, candles: Candle[]): IndicatorResult {
  const { period, multiplier } = config.params
  const values: number[] = []
  const trend: number[] = []

  // Calculate ATR
  const atrValues: number[] = []
  for (let i = 0; i < candles.length; i++) {
    if (i === 0) {
      atrValues.push(candles[i].high - candles[i].low)
    } else {
      const tr = trueRange(candles[i].high, candles[i].low, candles[i - 1].close)
      if (i < period) {
        atrValues.push(tr)
      } else {
        const atr = (atrValues[i - 1] * (period - 1) + tr) / period
        atrValues.push(atr)
      }
    }
  }

  // Calculate SuperTrend
  let prevTrend = 1
  for (let i = 0; i < candles.length; i++) {
    if (i < period - 1) {
      values.push(NaN)
      trend.push(NaN)
    } else {
      const hl2 = (candles[i].high + candles[i].low) / 2
      const atr = atrValues[i]

      const upperBand = hl2 + (multiplier * atr)
      const lowerBand = hl2 - (multiplier * atr)

      if (candles[i].close <= upperBand && prevTrend === 1) {
        values.push(upperBand)
        trend.push(1)
        prevTrend = 1
      } else if (candles[i].close >= lowerBand && prevTrend === -1) {
        values.push(lowerBand)
        trend.push(-1)
        prevTrend = -1
      } else if (candles[i].close > upperBand) {
        values.push(lowerBand)
        trend.push(-1)
        prevTrend = -1
      } else {
        values.push(upperBand)
        trend.push(1)
        prevTrend = 1
      }
    }
  }

  return {
    id: config.id,
    type: 'SuperTrend',
    values,
    additionalLines: {
      trend
    }
  }
}

// ============================================
// VOLUME INDICATORS
// ============================================

/**
 * Chaikin Money Flow (CMF)
 */
export function calculateCMF(config: CMFConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const values: number[] = []

  for (let i = 0; i < candles.length; i++) {
    if (i < period - 1) {
      values.push(NaN)
    } else {
      let mfvSum = 0
      let volumeSum = 0

      for (let j = 0; j < period; j++) {
        const idx = i - j
        const high = candles[idx].high
        const low = candles[idx].low
        const close = candles[idx].close
        const volume = candles[idx].volume

        const mfm = high - low !== 0
          ? ((close - low) - (high - close)) / (high - low)
          : 0
        const mfv = mfm * volume

        mfvSum += mfv
        volumeSum += volume
      }

      const cmf = volumeSum !== 0 ? mfvSum / volumeSum : 0
      values.push(cmf)
    }
  }

  return {
    id: config.id,
    type: 'CMF',
    values
  }
}

// ============================================
// MARKET STRUCTURE
// ============================================

/**
 * Pivot Points
 */
export function calculatePIVOT(config: PIVOTConfig, candles: Candle[]): IndicatorResult {
  const { type } = config.params
  const values: number[] = []
  const r1: number[] = []
  const r2: number[] = []
  const r3: number[] = []
  const s1: number[] = []
  const s2: number[] = []
  const s3: number[] = []

  for (let i = 0; i < candles.length; i++) {
    if (i === 0) {
      values.push(NaN)
      r1.push(NaN)
      r2.push(NaN)
      r3.push(NaN)
      s1.push(NaN)
      s2.push(NaN)
      s3.push(NaN)
    } else {
      const prev = candles[i - 1]
      const pivot = (prev.high + prev.low + prev.close) / 3

      if (type === 'classic') {
        values.push(pivot)
        r1.push(2 * pivot - prev.low)
        s1.push(2 * pivot - prev.high)
        r2.push(pivot + (prev.high - prev.low))
        s2.push(pivot - (prev.high - prev.low))
        r3.push(prev.high + 2 * (pivot - prev.low))
        s3.push(prev.low - 2 * (prev.high - pivot))
      } else if (type === 'fibonacci') {
        const range = prev.high - prev.low
        values.push(pivot)
        r1.push(pivot + 0.382 * range)
        s1.push(pivot - 0.382 * range)
        r2.push(pivot + 0.618 * range)
        s2.push(pivot - 0.618 * range)
        r3.push(pivot + range)
        s3.push(pivot - range)
      } else {
        // Default classic
        values.push(pivot)
        r1.push(2 * pivot - prev.low)
        s1.push(2 * pivot - prev.high)
        r2.push(pivot + (prev.high - prev.low))
        s2.push(pivot - (prev.high - prev.low))
        r3.push(prev.high + 2 * (pivot - prev.low))
        s3.push(prev.low - 2 * (prev.high - pivot))
      }
    }
  }

  return {
    id: config.id,
    type: 'PIVOT',
    values,
    additionalLines: {
      r1,
      r2,
      r3,
      s1,
      s2,
      s3
    }
  }
}

/**
 * ZigZag Indicator
 */
export function calculateZIGZAG(config: ZIGZAGConfig, candles: Candle[]): IndicatorResult {
  const { deviation } = config.params
  const values: number[] = new Array(candles.length).fill(NaN)

  if (candles.length < 2) {
    return { id: config.id, type: 'ZIGZAG', values }
  }

  let lastPivotIndex = 0
  let lastPivotValue = candles[0].close
  let lastPivotType: 'high' | 'low' = 'low'

  values[0] = lastPivotValue

  for (let i = 1; i < candles.length; i++) {
    const price = candles[i].close
    const percentChange = ((price - lastPivotValue) / lastPivotValue) * 100

    if (lastPivotType === 'low') {
      if (percentChange >= deviation) {
        // New high pivot
        values[i] = price
        lastPivotIndex = i
        lastPivotValue = price
        lastPivotType = 'high'
      } else if (price < lastPivotValue) {
        // Update low pivot
        values[lastPivotIndex] = NaN
        values[i] = price
        lastPivotIndex = i
        lastPivotValue = price
      }
    } else {
      if (percentChange <= -deviation) {
        // New low pivot
        values[i] = price
        lastPivotIndex = i
        lastPivotValue = price
        lastPivotType = 'low'
      } else if (price > lastPivotValue) {
        // Update high pivot
        values[lastPivotIndex] = NaN
        values[i] = price
        lastPivotIndex = i
        lastPivotValue = price
      }
    }
  }

  return {
    id: config.id,
    type: 'ZIGZAG',
    values
  }
}

// ============================================
// ADVANCED INDICATORS
// ============================================

/**
 * Aroon Oscillator
 */
export function calculateAROON(config: AROONConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const aroonUp: number[] = []
  const aroonDown: number[] = []
  const oscillator: number[] = []

  for (let i = 0; i < candles.length; i++) {
    if (i < period) {
      aroonUp.push(NaN)
      aroonDown.push(NaN)
      oscillator.push(NaN)
    } else {
      const slice = candles.slice(i - period, i + 1)

      let highestIdx = 0
      let lowestIdx = 0
      let highest = slice[0].high
      let lowest = slice[0].low

      for (let j = 1; j < slice.length; j++) {
        if (slice[j].high > highest) {
          highest = slice[j].high
          highestIdx = j
        }
        if (slice[j].low < lowest) {
          lowest = slice[j].low
          lowestIdx = j
        }
      }

      const up = ((period - (period - highestIdx)) / period) * 100
      const down = ((period - (period - lowestIdx)) / period) * 100

      aroonUp.push(up)
      aroonDown.push(down)
      oscillator.push(up - down)
    }
  }

  return {
    id: config.id,
    type: 'AROON',
    values: oscillator,
    additionalLines: {
      up: aroonUp,
      down: aroonDown
    }
  }
}

/**
 * Balance of Power (BOP)
 */
export function calculateBOP(config: BOPConfig, candles: Candle[]): IndicatorResult {
  const values: number[] = []

  for (let i = 0; i < candles.length; i++) {
    const high = candles[i].high
    const low = candles[i].low
    const open = candles[i].open
    const close = candles[i].close

    const bop = high - low !== 0
      ? (close - open) / (high - low)
      : 0

    values.push(bop)
  }

  return {
    id: config.id,
    type: 'BOP',
    values
  }
}

/**
 * Vortex Indicator
 */
export function calculateVORTEX(config: VORTEXConfig, candles: Candle[]): IndicatorResult {
  const { period } = config.params
  const viPlus: number[] = []
  const viMinus: number[] = []

  for (let i = 0; i < candles.length; i++) {
    if (i < period) {
      viPlus.push(NaN)
      viMinus.push(NaN)
    } else {
      let vmPlusSum = 0
      let vmMinusSum = 0
      let trSum = 0

      for (let j = 0; j < period; j++) {
        const idx = i - j
        if (idx > 0) {
          vmPlusSum += Math.abs(candles[idx].high - candles[idx - 1].low)
          vmMinusSum += Math.abs(candles[idx].low - candles[idx - 1].high)
          trSum += trueRange(candles[idx].high, candles[idx].low, candles[idx - 1].close)
        }
      }

      viPlus.push(trSum !== 0 ? vmPlusSum / trSum : 0)
      viMinus.push(trSum !== 0 ? vmMinusSum / trSum : 0)
    }
  }

  return {
    id: config.id,
    type: 'VORTEX',
    values: viPlus,
    additionalLines: {
      minus: viMinus
    }
  }
}

// ============================================
// MAIN EXTENDED CALCULATOR
// ============================================

export function calculateExtendedIndicator(
  config: AnyExtendedIndicatorConfig,
  candles: Candle[]
): IndicatorResult | null {
  try {
    switch (config.type) {
      // Trend Following
      case 'ALMA':
        return calculateALMA(config as ALMAConfig, candles)
      case 'DEMA':
        return calculateDEMA(config as DEMAConfig, candles)
      case 'TEMA':
        return calculateTEMA(config as TEMAConfig, candles)
      case 'HMA':
        return calculateHMA(config as HMAConfig, candles)
      case 'KAMA':
        return calculateKAMA(config as KAMAConfig, candles)

      // Momentum
      case 'CMO':
        return calculateCMO(config as CMOConfig, candles)
      case 'DPO':
        return calculateDPO(config as DPOConfig, candles)
      case 'UO':
        return calculateUO(config as UOConfig, candles)

      // Volatility
      case 'DC':
        return calculateDC(config as DCConfig, candles)
      case 'BBW':
        return calculateBBW(config as BBWConfig, candles)
      case 'SuperTrend':
        return calculateSuperTrend(config as SuperTrendConfig, candles)

      // Volume
      case 'CMF':
        return calculateCMF(config as CMFConfig, candles)

      // Market Structure
      case 'PIVOT':
        return calculatePIVOT(config as PIVOTConfig, candles)
      case 'ZIGZAG':
        return calculateZIGZAG(config as ZIGZAGConfig, candles)

      // Advanced
      case 'AROON':
        return calculateAROON(config as AROONConfig, candles)
      case 'BOP':
        return calculateBOP(config as BOPConfig, candles)
      case 'VORTEX':
        return calculateVORTEX(config as VORTEXConfig, candles)

      default:
        console.warn(`Extended indicator type ${config.type} not implemented yet`)
        return null
    }
  } catch (error) {
    console.error(`Error calculating extended indicator ${config.type}:`, error)
    return null
  }
}