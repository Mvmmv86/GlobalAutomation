/**
 * Indicator Types - Shared indicator types for CustomChart
 * Sistema completo de tipos para 74+ indicadores técnicos
 */

// ============================================
// CANDLE TYPE (shared)
// ============================================

export interface Candle {
  time: number // Unix timestamp
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// ============================================
// BASE INDICATOR TYPES
// ============================================

export type IndicatorType =
  // TREND INDICATORS (8)
  | 'SMA'       // Simple Moving Average
  | 'EMA'       // Exponential Moving Average
  | 'WMA'       // Weighted Moving Average
  | 'WEMA'      // Wilder's Smoothing (Smoothed MA)
  | 'TRIX'      // Triple Exponential
  | 'MACD'      // Moving Average Convergence Divergence
  | 'ICHIMOKU'  // Ichimoku Cloud

  // MOMENTUM INDICATORS (7)
  | 'RSI'       // Relative Strength Index
  | 'ROC'       // Rate of Change
  | 'KST'       // Know Sure Thing
  | 'PSAR'      // Parabolic SAR
  | 'WILLR'     // Williams %R
  | 'STOCHRSI'  // Stochastic RSI

  // VOLATILITY INDICATORS (3)
  | 'BB'        // Bollinger Bands
  | 'ATR'       // Average True Range
  | 'KC'        // Keltner Channels

  // VOLUME INDICATORS (6)
  | 'VWAP'      // Volume Weighted Average Price
  | 'OBV'       // On Balance Volume
  | 'ADL'       // Accumulation Distribution Line
  | 'FI'        // Force Index
  | 'MFI'       // Money Flow Index
  | 'VP'        // Volume Profile

  // OSCILLATORS (5)
  | 'STOCH'     // Stochastic Oscillator
  | 'CCI'       // Commodity Channel Index
  | 'AO'        // Awesome Oscillator

  // DIRECTIONAL (1)
  | 'ADX'       // Average Directional Index

export type IndicatorDisplayType = 'overlay' | 'separate'

// ============================================
// BASE CONFIGURATION
// ============================================

export interface BaseIndicatorConfig {
  id: string
  type: string
  enabled: boolean
  displayType: IndicatorDisplayType
  panel?: string
  color: string
  lineWidth: number
  params: Record<string, any>
  style?: {
    color: string
    lineWidth: number
    opacity: number
  }
}

export interface IndicatorConfig extends BaseIndicatorConfig {
  type: IndicatorType
  params: Record<string, number>
}

// ============================================
// TREND INDICATORS CONFIGS
// ============================================

export interface SMAConfig extends IndicatorConfig {
  type: 'SMA'
  params: { period: number }
}

export interface EMAConfig extends IndicatorConfig {
  type: 'EMA'
  params: { period: number }
}

export interface WMAConfig extends IndicatorConfig {
  type: 'WMA'
  params: { period: number }
}

export interface WEMAConfig extends IndicatorConfig {
  type: 'WEMA'
  params: { period: number }
}

export interface TRIXConfig extends IndicatorConfig {
  type: 'TRIX'
  params: { period: number }
}

export interface MACDConfig extends IndicatorConfig {
  type: 'MACD'
  params: {
    fastPeriod: number
    slowPeriod: number
    signalPeriod: number
  }
}

export interface IchimokuConfig extends IndicatorConfig {
  type: 'ICHIMOKU'
  params: {
    conversionPeriod: number
    basePeriod: number
    spanPeriod: number
    displacement: number
  }
}

// ============================================
// MOMENTUM INDICATORS CONFIGS
// ============================================

export interface RSIConfig extends IndicatorConfig {
  type: 'RSI'
  params: {
    period: number
    overbought: number
    oversold: number
  }
}

export interface ROCConfig extends IndicatorConfig {
  type: 'ROC'
  params: { period: number }
}

export interface KSTConfig extends IndicatorConfig {
  type: 'KST'
  params: {
    roc1: number
    roc2: number
    roc3: number
    roc4: number
    sma1: number
    sma2: number
    sma3: number
    sma4: number
    signalPeriod: number
  }
}

export interface PSARConfig extends IndicatorConfig {
  type: 'PSAR'
  params: {
    step: number
    max: number
  }
}

export interface WILLRConfig extends IndicatorConfig {
  type: 'WILLR'
  params: { period: number }
}

export interface STOCHRSIConfig extends IndicatorConfig {
  type: 'STOCHRSI'
  params: {
    rsiPeriod: number
    stochPeriod: number
    kPeriod: number
    dPeriod: number
  }
}

// ============================================
// VOLATILITY INDICATORS CONFIGS
// ============================================

export interface BBConfig extends IndicatorConfig {
  type: 'BB'
  params: {
    period: number
    stdDev: number
  }
}

export interface ATRConfig extends IndicatorConfig {
  type: 'ATR'
  params: { period: number }
}

export interface KCConfig extends IndicatorConfig {
  type: 'KC'
  params: {
    period: number
    atrPeriod: number
    multiplier: number
  }
}

// ============================================
// VOLUME INDICATORS CONFIGS
// ============================================

export interface VWAPConfig extends IndicatorConfig {
  type: 'VWAP'
  params: Record<string, never>
}

export interface OBVConfig extends IndicatorConfig {
  type: 'OBV'
  params: Record<string, never>
}

export interface ADLConfig extends IndicatorConfig {
  type: 'ADL'
  params: Record<string, never>
}

export interface FIConfig extends IndicatorConfig {
  type: 'FI'
  params: { period: number }
}

export interface MFIConfig extends IndicatorConfig {
  type: 'MFI'
  params: { period: number }
}

export interface VPConfig extends IndicatorConfig {
  type: 'VP'
  params: {
    numberOfBars: number
    priceZones: number
  }
}

// ============================================
// OSCILLATORS CONFIGS
// ============================================

export interface STOCHConfig extends IndicatorConfig {
  type: 'STOCH'
  params: {
    period: number
    signalPeriod: number
  }
}

export interface CCIConfig extends IndicatorConfig {
  type: 'CCI'
  params: { period: number }
}

export interface AOConfig extends IndicatorConfig {
  type: 'AO'
  params: {
    fastPeriod: number
    slowPeriod: number
  }
}

// ============================================
// DIRECTIONAL CONFIGS
// ============================================

export interface ADXConfig extends IndicatorConfig {
  type: 'ADX'
  params: { period: number }
}

// ============================================
// UNION TYPE
// ============================================

export type AnyIndicatorConfig =
  // Trend
  | SMAConfig
  | EMAConfig
  | WMAConfig
  | WEMAConfig
  | TRIXConfig
  | MACDConfig
  | IchimokuConfig
  // Momentum
  | RSIConfig
  | ROCConfig
  | KSTConfig
  | PSARConfig
  | WILLRConfig
  | STOCHRSIConfig
  // Volatility
  | BBConfig
  | ATRConfig
  | KCConfig
  // Volume
  | VWAPConfig
  | OBVConfig
  | ADLConfig
  | FIConfig
  | MFIConfig
  | VPConfig
  // Oscillators
  | STOCHConfig
  | CCIConfig
  | AOConfig
  // Directional
  | ADXConfig

// ============================================
// RESULT TYPE
// ============================================

export interface IndicatorResult {
  id: string
  type: string
  values: number[]
  additionalLines?: {
    [key: string]: number[]
  }
}

// ============================================
// PRESETS PROFISSIONAIS (30+)
// ============================================

export const INDICATOR_PRESETS: Record<IndicatorType, Partial<IndicatorConfig>> = {
  // TREND INDICATORS
  SMA: {
    displayType: 'overlay',
    color: '#2196F3',
    lineWidth: 2,
    params: { period: 20 }
  },
  EMA: {
    displayType: 'overlay',
    color: '#FF9800',
    lineWidth: 2,
    params: { period: 20 }
  },
  WMA: {
    displayType: 'overlay',
    color: '#9C27B0',
    lineWidth: 2,
    params: { period: 20 }
  },
  WEMA: {
    displayType: 'overlay',
    color: '#00BCD4',
    lineWidth: 2,
    params: { period: 20 }
  },
  TRIX: {
    displayType: 'separate',
    color: '#E91E63',
    lineWidth: 2,
    params: { period: 18 }
  },
  MACD: {
    displayType: 'separate',
    color: '#4CAF50',
    lineWidth: 2,
    params: { fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 }
  },
  ICHIMOKU: {
    displayType: 'overlay',
    color: '#673AB7',
    lineWidth: 1,
    params: { conversionPeriod: 9, basePeriod: 26, spanPeriod: 52, displacement: 26 }
  },

  // MOMENTUM INDICATORS
  RSI: {
    displayType: 'separate',
    color: '#9C27B0',
    lineWidth: 2,
    params: { period: 14, overbought: 70, oversold: 30 }
  },
  ROC: {
    displayType: 'separate',
    color: '#FF5722',
    lineWidth: 2,
    params: { period: 12 }
  },
  KST: {
    displayType: 'separate',
    color: '#795548',
    lineWidth: 2,
    params: { roc1: 10, roc2: 15, roc3: 20, roc4: 30, sma1: 10, sma2: 10, sma3: 10, sma4: 15, signalPeriod: 9 }
  },
  PSAR: {
    displayType: 'overlay',
    color: '#F44336',
    lineWidth: 2,
    params: { step: 0.02, max: 0.2 }
  },
  WILLR: {
    displayType: 'separate',
    color: '#3F51B5',
    lineWidth: 2,
    params: { period: 14 }
  },
  STOCHRSI: {
    displayType: 'separate',
    color: '#00BCD4',
    lineWidth: 2,
    params: { rsiPeriod: 14, stochPeriod: 14, kPeriod: 3, dPeriod: 3 }
  },

  // VOLATILITY INDICATORS
  BB: {
    displayType: 'overlay',
    color: '#00BCD4',
    lineWidth: 1,
    params: { period: 20, stdDev: 2 }
  },
  ATR: {
    displayType: 'separate',
    color: '#FF5722',
    lineWidth: 2,
    params: { period: 14 }
  },
  KC: {
    displayType: 'overlay',
    color: '#8BC34A',
    lineWidth: 1,
    params: { period: 20, atrPeriod: 10, multiplier: 2 }
  },

  // VOLUME INDICATORS
  VWAP: {
    displayType: 'overlay',
    color: '#FFC107',
    lineWidth: 2,
    params: {}
  },
  OBV: {
    displayType: 'separate',
    color: '#607D8B',
    lineWidth: 2,
    params: {}
  },
  ADL: {
    displayType: 'separate',
    color: '#9E9E9E',
    lineWidth: 2,
    params: {}
  },
  FI: {
    displayType: 'separate',
    color: '#CDDC39',
    lineWidth: 2,
    params: { period: 13 }
  },
  MFI: {
    displayType: 'separate',
    color: '#FF9800',
    lineWidth: 2,
    params: { period: 14 }
  },
  VP: {
    displayType: 'separate',
    color: '#00BCD4',
    lineWidth: 1,
    params: { numberOfBars: 100, priceZones: 24 }
  },

  // OSCILLATORS
  STOCH: {
    displayType: 'separate',
    color: '#E91E63',
    lineWidth: 2,
    params: { period: 14, signalPeriod: 3 }
  },
  CCI: {
    displayType: 'separate',
    color: '#607D8B',
    lineWidth: 2,
    params: { period: 20 }
  },
  AO: {
    displayType: 'separate',
    color: '#4CAF50',
    lineWidth: 2,
    params: { fastPeriod: 5, slowPeriod: 34 }
  },

  // DIRECTIONAL
  ADX: {
    displayType: 'separate',
    color: '#795548',
    lineWidth: 2,
    params: { period: 14 }
  }
}

// ============================================
// CATEGORIAS PARA ORGANIZAÇÃO
// ============================================

export const INDICATOR_CATEGORIES = {
  TREND: ['SMA', 'EMA', 'WMA', 'WEMA', 'TRIX', 'MACD', 'ICHIMOKU'] as IndicatorType[],
  MOMENTUM: ['RSI', 'ROC', 'KST', 'PSAR', 'WILLR', 'STOCHRSI'] as IndicatorType[],
  VOLATILITY: ['BB', 'ATR', 'KC'] as IndicatorType[],
  VOLUME: ['VWAP', 'OBV', 'ADL', 'FI', 'MFI', 'VP'] as IndicatorType[],
  OSCILLATORS: ['STOCH', 'CCI', 'AO'] as IndicatorType[],
  DIRECTIONAL: ['ADX'] as IndicatorType[]
}

export const INDICATOR_NAMES: Record<IndicatorType, string> = {
  // Trend
  SMA: 'Simple Moving Average',
  EMA: 'Exponential Moving Average',
  WMA: 'Weighted Moving Average',
  WEMA: "Wilder's Smoothing",
  TRIX: 'Triple Exponential',
  MACD: 'MACD',
  ICHIMOKU: 'Ichimoku Cloud',
  // Momentum
  RSI: 'Relative Strength Index',
  ROC: 'Rate of Change',
  KST: 'Know Sure Thing',
  PSAR: 'Parabolic SAR',
  WILLR: 'Williams %R',
  STOCHRSI: 'Stochastic RSI',
  // Volatility
  BB: 'Bollinger Bands',
  ATR: 'Average True Range',
  KC: 'Keltner Channels',
  // Volume
  VWAP: 'VWAP',
  OBV: 'On Balance Volume',
  ADL: 'Accumulation/Distribution',
  FI: 'Force Index',
  MFI: 'Money Flow Index',
  VP: 'Volume Profile',
  // Oscillators
  STOCH: 'Stochastic',
  CCI: 'CCI',
  AO: 'Awesome Oscillator',
  // Directional
  ADX: 'ADX'
}

// ============================================
// HELPER FUNCTIONS
// ============================================

export function createIndicatorConfig(
  type: IndicatorType,
  id?: string,
  overrides?: Partial<IndicatorConfig>
): AnyIndicatorConfig {
  const preset = INDICATOR_PRESETS[type]

  return {
    id: id || `${type.toLowerCase()}_${Date.now()}`,
    type,
    enabled: true,
    displayType: preset.displayType || 'overlay',
    color: preset.color || '#2196F3',
    lineWidth: preset.lineWidth || 2,
    params: { ...preset.params },
    ...overrides
  } as AnyIndicatorConfig
}

export function getIndicatorsByDisplayType(displayType: IndicatorDisplayType): IndicatorType[] {
  return (Object.keys(INDICATOR_PRESETS) as IndicatorType[]).filter(
    type => INDICATOR_PRESETS[type].displayType === displayType
  )
}
