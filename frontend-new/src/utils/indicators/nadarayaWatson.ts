/**
 * Nadaraya-Watson Envelope Indicator
 *
 * Implementation based on LuxAlgo's TradingView indicator
 * https://www.tradingview.com/script/Iko0E2kL-Nadaraya-Watson-Envelope-LuxAlgo/
 *
 * Uses Gaussian Kernel Regression to create smooth price envelopes
 * with Mean Absolute Error (MAE) for band calculation.
 */

import { Candle } from './types'

// ============================================
// TYPES
// ============================================

export interface NWEnvelopeParams {
  windowSize: number      // Number of candles (default: 250)
  bandwidth: number       // Gaussian kernel width (default: 8)
  multiplier: number      // MAE multiplier for bands (default: 3)
  source: 'close' | 'hlc3' | 'ohlc4' | 'hl2'
  repaint: boolean        // If true, uses full data (repainting). If false, endpoint method
}

export interface NWEnvelopePoint {
  time: number
  smoothLine: number
  upperBand: number
  lowerBand: number
}

export interface NWSignal {
  time: number
  type: 'buy' | 'sell'
  price: number
}

export interface NWEnvelopeResult {
  points: NWEnvelopePoint[]
  signals: NWSignal[]
  mae: number
}

// ============================================
// DEFAULT PARAMS
// ============================================

export const NW_DEFAULT_PARAMS: NWEnvelopeParams = {
  windowSize: 250,
  bandwidth: 8,
  multiplier: 3,
  source: 'close',
  repaint: true  // Default to repaint mode (like LuxAlgo default)
}

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Gaussian Kernel Function (identical to LuxAlgo)
 * gauss(x, h) => exp(-(x²)/(h²×2))
 */
function gaussianKernel(x: number, h: number): number {
  return Math.exp(-(x * x) / (2 * h * h))
}

/**
 * Extract source price from candle
 */
function getSourcePrice(candle: Candle, source: string): number {
  switch (source) {
    case 'hlc3':
      return (candle.high + candle.low + candle.close) / 3
    case 'ohlc4':
      return (candle.open + candle.high + candle.low + candle.close) / 4
    case 'hl2':
      return (candle.high + candle.low) / 2
    default:
      return candle.close
  }
}

// ============================================
// MAIN CALCULATION FUNCTION
// ============================================

/**
 * Calculate Nadaraya-Watson Envelope
 *
 * Combines LuxAlgo's TradingView logic with performance optimizations.
 *
 * Two modes available:
 * - Repaint Mode: Uses all data points, more accurate visually but repaints
 * - Non-Repaint Mode (Endpoint): Uses only past data, no repainting
 */
export function calculateNadarayaWatsonEnvelope(
  candles: Candle[],
  params: Partial<NWEnvelopeParams> = {}
): NWEnvelopeResult {
  // Merge with defaults
  const {
    windowSize = NW_DEFAULT_PARAMS.windowSize,
    bandwidth = NW_DEFAULT_PARAMS.bandwidth,
    multiplier = NW_DEFAULT_PARAMS.multiplier,
    source = NW_DEFAULT_PARAMS.source,
    repaint = NW_DEFAULT_PARAMS.repaint
  } = params

  const h = bandwidth
  const n = Math.min(candles.length, windowSize)

  // Not enough data
  if (n < 2) {
    return { points: [], signals: [], mae: 0 }
  }

  // Extract source prices and times from most recent candles
  const relevantCandles = candles.slice(-n)
  const src = relevantCandles.map(c => getSourcePrice(c, source))
  const times = relevantCandles.map(c => c.time)

  const points: NWEnvelopePoint[] = []
  const signals: NWSignal[] = []

  if (repaint) {
    // ═══════════════════════════════════════════════════════
    // REPAINT MODE (like LuxAlgo's barstate.islast)
    // More accurate visually, but recalculates on historical bars
    // ═══════════════════════════════════════════════════════

    const smoothLine: number[] = []
    let sae = 0 // Sum of Absolute Errors

    // Step 1: Calculate smoothed line for each point
    // Using double loop like LuxAlgo's Pine Script
    for (let i = 0; i < n; i++) {
      let sum = 0
      let sumW = 0

      for (let j = 0; j < n; j++) {
        // Gaussian weight based on distance between points
        const w = gaussianKernel(i - j, h)
        sum += src[j] * w
        sumW += w
      }

      const y = sum / sumW
      smoothLine.push(y)
      sae += Math.abs(src[i] - y)
    }

    // Step 2: Calculate MAE (Mean Absolute Error) × multiplier
    // Identical to LuxAlgo: sae := sae / math.min(499, n-1) * mult
    const mae = (sae / Math.max(n - 1, 1)) * multiplier

    // Step 3: Build points with bands
    for (let i = 0; i < n; i++) {
      points.push({
        time: times[i],
        smoothLine: smoothLine[i],
        upperBand: smoothLine[i] + mae,
        lowerBand: smoothLine[i] - mae
      })

      // Detect signals (LuxAlgo style)
      // Signal is generated when candle CLOSES above/below the band (not just touches)
      // - Candle CLOSES ABOVE upper band = SELL signal (overbought, expect reversal down)
      // - Candle CLOSES BELOW lower band = BUY signal (oversold, expect reversal up)

      const currClose = src[i]

      // Use current candle's band values
      const upper = smoothLine[i] + mae
      const lower = smoothLine[i] - mae

      // SELL signal: candle CLOSES ABOVE upper band (overbought)
      if (currClose > upper) {
        signals.push({
          time: times[i],
          type: 'sell',
          price: currClose
        })
      }

      // BUY signal: candle CLOSES BELOW lower band (oversold)
      if (currClose < lower) {
        signals.push({
          time: times[i],
          type: 'buy',
          price: currClose
        })
      }
    }

    console.log(`🔍 NW Repaint Mode: Generated ${signals.length} signals from ${n} candles`)
    if (signals.length > 0) {
      console.log('📍 Signals:', signals.slice(0, 5), '...')
    }
    return { points, signals, mae }

  } else {
    // ═══════════════════════════════════════════════════════
    // NON-REPAINT MODE / ENDPOINT (like LuxAlgo's non-repaint option)
    // More reliable for real trading, uses only past data
    // ═══════════════════════════════════════════════════════

    // Pre-calculate coefficients (LuxAlgo optimization)
    // This avoids recalculating weights for each point
    const coefs: number[] = []
    let den = 0

    for (let i = 0; i < n; i++) {
      const w = gaussianKernel(i, h)
      coefs.push(w)
      den += w
    }

    // Calculate smoothed line for each point
    // Using endpoint method (only looks backward)
    const smoothLine: number[] = []

    for (let i = 0; i < n; i++) {
      let out = 0
      let localDen = 0

      // Only use data up to current index (non-repaint)
      const lookback = Math.min(i + 1, n)
      for (let j = 0; j < lookback; j++) {
        const w = coefs[j]
        const idx = i - j
        if (idx >= 0) {
          out += src[idx] * w
          localDen += w
        }
      }

      smoothLine.push(localDen > 0 ? out / localDen : src[i])
    }

    // Calculate MAE using SMA-style (like LuxAlgo's ta.sma)
    // mae = ta.sma(math.abs(src - out), 499) * mult
    const maeWindow = Math.min(n, 100) // Smaller window for performance

    for (let i = 0; i < n; i++) {
      // Calculate local MAE for this point
      let maeSum = 0
      let maeCount = 0

      const start = Math.max(0, i - maeWindow + 1)
      for (let k = start; k <= i; k++) {
        maeSum += Math.abs(src[k] - smoothLine[k])
        maeCount++
      }

      const localMae = maeCount > 0 ? (maeSum / maeCount) * multiplier : 0

      points.push({
        time: times[i],
        smoothLine: smoothLine[i],
        upperBand: smoothLine[i] + localMae,
        lowerBand: smoothLine[i] - localMae
      })

      // Detect signals (LuxAlgo style)
      // Signal is generated when candle CLOSES above/below the band
      const currClose = src[i]
      const upper = points[i].upperBand
      const lower = points[i].lowerBand

      // SELL signal: candle CLOSES ABOVE upper band (overbought)
      if (currClose > upper) {
        signals.push({
          time: times[i],
          type: 'sell',
          price: currClose
        })
      }

      // BUY signal: candle CLOSES BELOW lower band (oversold)
      if (currClose < lower) {
        signals.push({
          time: times[i],
          type: 'buy',
          price: currClose
        })
      }
    }

    const finalMae = points.length > 0
      ? points[points.length - 1].upperBand - points[points.length - 1].smoothLine
      : 0

    console.log(`🔍 NW Non-Repaint Mode: Generated ${signals.length} signals from ${n} candles`)
    if (signals.length > 0) {
      console.log('📍 Signals:', signals.slice(0, 5), '...')
    }
    return { points, signals, mae: finalMae }
  }
}

// ============================================
// INDICATOR CONFIG (for IndicatorEngine integration)
// ============================================

export interface NWEnvelopeConfig {
  id: string
  type: 'NWENVELOPE'
  enabled: boolean
  displayType: 'overlay'
  color: string
  lineWidth: number
  params: {
    windowSize: number
    bandwidth: number
    multiplier: number
    source: 'close' | 'hlc3' | 'ohlc4' | 'hl2'
    repaint: boolean
  }
}

export const NW_ENVELOPE_PRESET: Partial<NWEnvelopeConfig> = {
  displayType: 'overlay',
  color: '#2962FF',  // Blue for smooth line
  lineWidth: 2,
  params: {
    windowSize: 250,
    bandwidth: 8,
    multiplier: 3,
    source: 'close',
    repaint: true
  }
}

// ============================================
// COLORS (LuxAlgo style)
// ============================================

export const NW_COLORS = {
  smoothLine: '#2962FF',              // Blue
  upperBand: 'rgba(239, 83, 80, 0.8)', // Red (dnCss)
  lowerBand: 'rgba(38, 166, 154, 0.8)', // Teal (upCss)
  buySignal: '#26A69A',                // Teal
  sellSignal: '#EF5350',               // Red
  fillArea: 'rgba(41, 98, 255, 0.05)'  // Light blue fill
}
