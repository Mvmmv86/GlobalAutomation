/**
 * Extended Indicator Types - 50+ Technical Indicators
 * Sistema PROFISSIONAL com indicadores avançados
 */

import { BaseIndicatorConfig } from './types'

// ============================================
// EXTENDED INDICATOR TYPES (50+)
// ============================================

export type ExtendedIndicatorType =
  // Trend Following (15)
  | 'ALMA'      // Arnaud Legoux Moving Average
  | 'DEMA'      // Double Exponential Moving Average
  | 'TEMA'      // Triple Exponential Moving Average
  | 'HMA'       // Hull Moving Average
  | 'KAMA'      // Kaufman Adaptive Moving Average
  | 'SMMA'      // Smoothed Moving Average
  | 'VWMA'      // Volume Weighted Moving Average
  | 'ZLEMA'     // Zero Lag Exponential Moving Average
  | 'T3'        // Tillson T3
  | 'VIDYA'     // Variable Index Dynamic Average
  | 'FRAMA'     // Fractal Adaptive Moving Average
  | 'JMA'       // Jurik Moving Average
  | 'MAMA'      // MESA Adaptive Moving Average
  | 'SWMA'      // Sine Weighted Moving Average
  | 'LSMA'      // Least Squares Moving Average

  // Momentum Oscillators (15)
  | 'CMO'       // Chande Momentum Oscillator
  | 'DPO'       // Detrended Price Oscillator
  | 'KST'       // Know Sure Thing
  | 'TRIX'      // Triple Exponential
  | 'UO'        // Ultimate Oscillator
  | 'TSI'       // True Strength Index
  | 'PPO'       // Percentage Price Oscillator
  | 'PVO'       // Percentage Volume Oscillator
  | 'QStick'    // QStick Indicator
  | 'SMI'       // Stochastic Momentum Index
  | 'SRSI'      // Stochastic RSI
  | 'VHF'       // Vertical Horizontal Filter
  | 'WPR'       // Williams %R
  | 'FISH'      // Fisher Transform
  | 'CRSI'      // Connors RSI

  // Volatility Indicators (12)
  | 'DC'        // Donchian Channels
  | 'KC'        // Keltner Channels
  | 'BB'        // Bollinger Bands
  | 'BBW'       // Bollinger Band Width
  | 'BBP'       // Bollinger Band %B
  | 'NATR'      // Normalized ATR
  | 'RVI'       // Relative Volatility Index
  | 'CHOP'      // Choppiness Index
  | 'VIX'       // Volatility Index
  | 'HV'        // Historical Volatility
  | 'ChandelierExit' // Chandelier Exit
  | 'SuperTrend' // SuperTrend

  // Volume Indicators (12)
  | 'AD'        // Accumulation/Distribution
  | 'CMF'       // Chaikin Money Flow
  | 'EMV'       // Ease of Movement
  | 'FI'        // Force Index
  | 'KVO'       // Klinger Volume Oscillator
  | 'NVI'       // Negative Volume Index
  | 'PVI'       // Positive Volume Index
  | 'PVT'       // Price Volume Trend
  | 'VWAP'      // Volume Weighted Average Price
  | 'VPVR'      // Volume Profile Visible Range
  | 'VR'        // Volume Ratio
  | 'WAD'       // Williams Accumulation/Distribution

  // Market Structure (10)
  | 'PIVOT'     // Pivot Points
  | 'CAMARILLA' // Camarilla Pivot Points
  | 'FIBONACCI' // Fibonacci Retracements
  | 'GANN'      // Gann Levels
  | 'MURREY'    // Murrey Math Lines
  | 'SUPPORT'   // Support Levels
  | 'RESISTANCE'// Resistance Levels
  | 'ZIGZAG'    // ZigZag
  | 'FRACTAL'   // Fractal
  | 'MARKET_PROFILE' // Market Profile

  // Advanced Indicators (10)
  | 'VORTEX'    // Vortex Indicator
  | 'AROON'     // Aroon Oscillator
  | 'BOP'       // Balance of Power
  | 'CORAL'     // Coral Trend
  | 'ELDER_RAY' // Elder Ray Index
  | 'GATOR'     // Gator Oscillator
  | 'HT'        // Hilbert Transform
  | 'MASS_INDEX'// Mass Index
  | 'SCHAFF'    // Schaff Trend Cycle
  | 'VI'        // Vortex Indicator

// ============================================
// EXTENDED CONFIGURATIONS
// ============================================

// Trend Following Configs
export interface ALMAConfig extends BaseIndicatorConfig {
  type: 'ALMA'
  params: {
    period: number
    offset: number
    sigma: number
  }
}

export interface DEMAConfig extends BaseIndicatorConfig {
  type: 'DEMA'
  params: {
    period: number
  }
}

export interface TEMAConfig extends BaseIndicatorConfig {
  type: 'TEMA'
  params: {
    period: number
  }
}

export interface HMAConfig extends BaseIndicatorConfig {
  type: 'HMA'
  params: {
    period: number
  }
}

export interface KAMAConfig extends BaseIndicatorConfig {
  type: 'KAMA'
  params: {
    period: number
    fastPeriod: number
    slowPeriod: number
  }
}

export interface SMMAConfig extends BaseIndicatorConfig {
  type: 'SMMA'
  params: {
    period: number
  }
}

export interface VWMAConfig extends BaseIndicatorConfig {
  type: 'VWMA'
  params: {
    period: number
  }
}

export interface ZLEMAConfig extends BaseIndicatorConfig {
  type: 'ZLEMA'
  params: {
    period: number
  }
}

export interface T3Config extends BaseIndicatorConfig {
  type: 'T3'
  params: {
    period: number
    volumeFactor: number
  }
}

export interface VIDYAConfig extends BaseIndicatorConfig {
  type: 'VIDYA'
  params: {
    period: number
    historyPeriod: number
  }
}

// Momentum Oscillators Configs
export interface CMOConfig extends BaseIndicatorConfig {
  type: 'CMO'
  params: {
    period: number
  }
}

export interface DPOConfig extends BaseIndicatorConfig {
  type: 'DPO'
  params: {
    period: number
  }
}

export interface UOConfig extends BaseIndicatorConfig {
  type: 'UO'
  params: {
    period1: number
    period2: number
    period3: number
  }
}

export interface TSIConfig extends BaseIndicatorConfig {
  type: 'TSI'
  params: {
    longPeriod: number
    shortPeriod: number
    signalPeriod: number
  }
}

export interface PPOConfig extends BaseIndicatorConfig {
  type: 'PPO'
  params: {
    fastPeriod: number
    slowPeriod: number
    signalPeriod: number
  }
}

// Volatility Indicators Configs
export interface DCConfig extends BaseIndicatorConfig {
  type: 'DC'
  params: {
    period: number
  }
}

export interface BBWConfig extends BaseIndicatorConfig {
  type: 'BBW'
  params: {
    period: number
    stdDev: number
  }
}

export interface BBPConfig extends BaseIndicatorConfig {
  type: 'BBP'
  params: {
    period: number
    stdDev: number
  }
}

export interface NATRConfig extends BaseIndicatorConfig {
  type: 'NATR'
  params: {
    period: number
  }
}

export interface RVIConfig extends BaseIndicatorConfig {
  type: 'RVI'
  params: {
    period: number
    smoothing: number
  }
}

export interface CHOPConfig extends BaseIndicatorConfig {
  type: 'CHOP'
  params: {
    period: number
  }
}

export interface SuperTrendConfig extends BaseIndicatorConfig {
  type: 'SuperTrend'
  params: {
    period: number
    multiplier: number
  }
}

// Volume Indicators Configs
export interface CMFConfig extends BaseIndicatorConfig {
  type: 'CMF'
  params: {
    period: number
  }
}

export interface EMVConfig extends BaseIndicatorConfig {
  type: 'EMV'
  params: {
    period: number
    divisor: number
  }
}

export interface KVOConfig extends BaseIndicatorConfig {
  type: 'KVO'
  params: {
    shortPeriod: number
    longPeriod: number
    signalPeriod: number
  }
}

export interface NVIConfig extends BaseIndicatorConfig {
  type: 'NVI'
  params: {
    startValue?: number
  }
}

export interface PVIConfig extends BaseIndicatorConfig {
  type: 'PVI'
  params: {
    startValue?: number
  }
}

export interface PVTConfig extends BaseIndicatorConfig {
  type: 'PVT'
  params: {}
}

// Market Structure Configs
export interface PIVOTConfig extends BaseIndicatorConfig {
  type: 'PIVOT'
  params: {
    type: 'classic' | 'fibonacci' | 'woodie' | 'camarilla' | 'demark'
  }
}

export interface ZIGZAGConfig extends BaseIndicatorConfig {
  type: 'ZIGZAG'
  params: {
    deviation: number
  }
}

export interface FRACTALConfig extends BaseIndicatorConfig {
  type: 'FRACTAL'
  params: {
    period: number
  }
}

// Advanced Indicators Configs
export interface AROONConfig extends BaseIndicatorConfig {
  type: 'AROON'
  params: {
    period: number
  }
}

export interface BOPConfig extends BaseIndicatorConfig {
  type: 'BOP'
  params: {}
}

export interface VORTEXConfig extends BaseIndicatorConfig {
  type: 'VORTEX'
  params: {
    period: number
  }
}

export interface ELDER_RAYConfig extends BaseIndicatorConfig {
  type: 'ELDER_RAY'
  params: {
    period: number
  }
}

export interface GATORConfig extends BaseIndicatorConfig {
  type: 'GATOR'
  params: {
    jawPeriod: number
    teethPeriod: number
    lipsPeriod: number
    jawOffset: number
    teethOffset: number
    lipsOffset: number
  }
}

export interface MASS_INDEXConfig extends BaseIndicatorConfig {
  type: 'MASS_INDEX'
  params: {
    emaPeriod: number
    sumPeriod: number
  }
}

export interface SCHAFFConfig extends BaseIndicatorConfig {
  type: 'SCHAFF'
  params: {
    fastPeriod: number
    slowPeriod: number
    signalPeriod: number
  }
}

// ============================================
// UNION TYPE FOR ALL EXTENDED CONFIGS
// ============================================

export type AnyExtendedIndicatorConfig =
  // Trend Following
  | ALMAConfig
  | DEMAConfig
  | TEMAConfig
  | HMAConfig
  | KAMAConfig
  | SMMAConfig
  | VWMAConfig
  | ZLEMAConfig
  | T3Config
  | VIDYAConfig
  // Momentum
  | CMOConfig
  | DPOConfig
  | UOConfig
  | TSIConfig
  | PPOConfig
  // Volatility
  | DCConfig
  | BBWConfig
  | BBPConfig
  | NATRConfig
  | RVIConfig
  | CHOPConfig
  | SuperTrendConfig
  // Volume
  | CMFConfig
  | EMVConfig
  | KVOConfig
  | NVIConfig
  | PVIConfig
  | PVTConfig
  // Market Structure
  | PIVOTConfig
  | ZIGZAGConfig
  | FRACTALConfig
  // Advanced
  | AROONConfig
  | BOPConfig
  | VORTEXConfig
  | ELDER_RAYConfig
  | GATORConfig
  | MASS_INDEXConfig
  | SCHAFFConfig

// ============================================
// INDICATOR METADATA
// ============================================

export interface IndicatorMetadata {
  name: string
  category: 'trend' | 'momentum' | 'volatility' | 'volume' | 'structure' | 'advanced'
  description: string
  displayType: 'overlay' | 'separate'
  defaultPanel?: string
  parameters: Array<{
    name: string
    type: 'number' | 'string' | 'boolean'
    default: any
    min?: number
    max?: number
    step?: number
    options?: string[]
  }>
}

export const INDICATOR_METADATA: Record<ExtendedIndicatorType, IndicatorMetadata> = {
  // Trend Following
  ALMA: {
    name: 'Arnaud Legoux MA',
    category: 'trend',
    description: 'Adaptive moving average with Gaussian distribution',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 9, min: 2, max: 200 },
      { name: 'offset', type: 'number', default: 0.85, min: 0, max: 1, step: 0.01 },
      { name: 'sigma', type: 'number', default: 6, min: 1, max: 50 }
    ]
  },
  DEMA: {
    name: 'Double Exponential MA',
    category: 'trend',
    description: 'Double smoothed exponential moving average',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  TEMA: {
    name: 'Triple Exponential MA',
    category: 'trend',
    description: 'Triple smoothed exponential moving average',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  HMA: {
    name: 'Hull MA',
    category: 'trend',
    description: 'Weighted moving average with reduced lag',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  KAMA: {
    name: 'Kaufman Adaptive MA',
    category: 'trend',
    description: 'Adaptive moving average based on volatility',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 10, min: 2, max: 200 },
      { name: 'fastPeriod', type: 'number', default: 2, min: 2, max: 50 },
      { name: 'slowPeriod', type: 'number', default: 30, min: 10, max: 200 }
    ]
  },
  SMMA: {
    name: 'Smoothed MA',
    category: 'trend',
    description: 'Smoothed moving average',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  VWMA: {
    name: 'Volume Weighted MA',
    category: 'trend',
    description: 'Moving average weighted by volume',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  ZLEMA: {
    name: 'Zero Lag EMA',
    category: 'trend',
    description: 'Exponential moving average with reduced lag',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  T3: {
    name: 'Tillson T3',
    category: 'trend',
    description: 'Smoothed moving average with minimal lag',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 8, min: 2, max: 200 },
      { name: 'volumeFactor', type: 'number', default: 0.7, min: 0, max: 1, step: 0.1 }
    ]
  },
  VIDYA: {
    name: 'Variable Index Dynamic Average',
    category: 'trend',
    description: 'Variable moving average based on volatility',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 },
      { name: 'historyPeriod', type: 'number', default: 30, min: 10, max: 200 }
    ]
  },
  FRAMA: {
    name: 'Fractal Adaptive MA',
    category: 'trend',
    description: 'Adaptive moving average using fractal dimension',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 4, max: 200 }
    ]
  },
  JMA: {
    name: 'Jurik MA',
    category: 'trend',
    description: 'Smooth and responsive moving average',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 },
      { name: 'phase', type: 'number', default: 0, min: -100, max: 100 }
    ]
  },
  MAMA: {
    name: 'MESA Adaptive MA',
    category: 'trend',
    description: 'Adaptive moving average using MESA algorithm',
    displayType: 'overlay',
    parameters: [
      { name: 'fastLimit', type: 'number', default: 0.5, min: 0.01, max: 0.99, step: 0.01 },
      { name: 'slowLimit', type: 'number', default: 0.05, min: 0.01, max: 0.99, step: 0.01 }
    ]
  },
  SWMA: {
    name: 'Sine Weighted MA',
    category: 'trend',
    description: 'Moving average weighted by sine function',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  LSMA: {
    name: 'Least Squares MA',
    category: 'trend',
    description: 'Linear regression moving average',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },

  // Momentum Oscillators
  CMO: {
    name: 'Chande Momentum Oscillator',
    category: 'momentum',
    description: 'Momentum oscillator measuring overbought/oversold',
    displayType: 'separate',
    defaultPanel: 'cmo',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  DPO: {
    name: 'Detrended Price Oscillator',
    category: 'momentum',
    description: 'Removes trend to identify cycles',
    displayType: 'separate',
    defaultPanel: 'dpo',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  KST: {
    name: 'Know Sure Thing',
    category: 'momentum',
    description: 'Multiple rate-of-change oscillator',
    displayType: 'separate',
    defaultPanel: 'kst',
    parameters: [
      { name: 'roc1', type: 'number', default: 10, min: 1, max: 100 },
      { name: 'roc2', type: 'number', default: 15, min: 1, max: 100 },
      { name: 'roc3', type: 'number', default: 20, min: 1, max: 100 },
      { name: 'roc4', type: 'number', default: 30, min: 1, max: 100 }
    ]
  },
  TRIX: {
    name: 'Triple Exponential',
    category: 'momentum',
    description: 'Triple smoothed momentum oscillator',
    displayType: 'separate',
    defaultPanel: 'trix',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  UO: {
    name: 'Ultimate Oscillator',
    category: 'momentum',
    description: 'Multi-timeframe momentum oscillator',
    displayType: 'separate',
    defaultPanel: 'uo',
    parameters: [
      { name: 'period1', type: 'number', default: 7, min: 1, max: 50 },
      { name: 'period2', type: 'number', default: 14, min: 1, max: 100 },
      { name: 'period3', type: 'number', default: 28, min: 1, max: 200 }
    ]
  },
  TSI: {
    name: 'True Strength Index',
    category: 'momentum',
    description: 'Double-smoothed momentum oscillator',
    displayType: 'separate',
    defaultPanel: 'tsi',
    parameters: [
      { name: 'longPeriod', type: 'number', default: 25, min: 2, max: 200 },
      { name: 'shortPeriod', type: 'number', default: 13, min: 2, max: 200 },
      { name: 'signalPeriod', type: 'number', default: 13, min: 2, max: 200 }
    ]
  },
  PPO: {
    name: 'Percentage Price Oscillator',
    category: 'momentum',
    description: 'MACD as percentage',
    displayType: 'separate',
    defaultPanel: 'ppo',
    parameters: [
      { name: 'fastPeriod', type: 'number', default: 12, min: 2, max: 200 },
      { name: 'slowPeriod', type: 'number', default: 26, min: 2, max: 200 },
      { name: 'signalPeriod', type: 'number', default: 9, min: 2, max: 200 }
    ]
  },
  PVO: {
    name: 'Percentage Volume Oscillator',
    category: 'momentum',
    description: 'Volume-based momentum oscillator',
    displayType: 'separate',
    defaultPanel: 'pvo',
    parameters: [
      { name: 'fastPeriod', type: 'number', default: 12, min: 2, max: 200 },
      { name: 'slowPeriod', type: 'number', default: 26, min: 2, max: 200 },
      { name: 'signalPeriod', type: 'number', default: 9, min: 2, max: 200 }
    ]
  },
  QStick: {
    name: 'QStick',
    category: 'momentum',
    description: 'Moving average of open-close difference',
    displayType: 'separate',
    defaultPanel: 'qstick',
    parameters: [
      { name: 'period', type: 'number', default: 8, min: 2, max: 200 }
    ]
  },
  SMI: {
    name: 'Stochastic Momentum Index',
    category: 'momentum',
    description: 'Enhanced stochastic oscillator',
    displayType: 'separate',
    defaultPanel: 'smi',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 },
      { name: 'smoothK', type: 'number', default: 3, min: 1, max: 50 },
      { name: 'smoothD', type: 'number', default: 3, min: 1, max: 50 }
    ]
  },
  SRSI: {
    name: 'Stochastic RSI',
    category: 'momentum',
    description: 'RSI with stochastic calculation',
    displayType: 'separate',
    defaultPanel: 'srsi',
    parameters: [
      { name: 'rsiPeriod', type: 'number', default: 14, min: 2, max: 200 },
      { name: 'stochPeriod', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  VHF: {
    name: 'Vertical Horizontal Filter',
    category: 'momentum',
    description: 'Identifies trending vs ranging markets',
    displayType: 'separate',
    defaultPanel: 'vhf',
    parameters: [
      { name: 'period', type: 'number', default: 28, min: 2, max: 200 }
    ]
  },
  WPR: {
    name: 'Williams %R',
    category: 'momentum',
    description: 'Momentum oscillator measuring overbought/oversold',
    displayType: 'separate',
    defaultPanel: 'wpr',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  FISH: {
    name: 'Fisher Transform',
    category: 'momentum',
    description: 'Normalizes price to Gaussian distribution',
    displayType: 'separate',
    defaultPanel: 'fisher',
    parameters: [
      { name: 'period', type: 'number', default: 10, min: 2, max: 200 }
    ]
  },
  CRSI: {
    name: 'Connors RSI',
    category: 'momentum',
    description: 'Composite RSI indicator',
    displayType: 'separate',
    defaultPanel: 'crsi',
    parameters: [
      { name: 'rsiPeriod', type: 'number', default: 3, min: 2, max: 200 },
      { name: 'streakPeriod', type: 'number', default: 2, min: 2, max: 200 },
      { name: 'rocPeriod', type: 'number', default: 100, min: 2, max: 200 }
    ]
  },

  // Volatility Indicators
  DC: {
    name: 'Donchian Channels',
    category: 'volatility',
    description: 'Highest high and lowest low channels',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 }
    ]
  },
  KC: {
    name: 'Keltner Channels',
    category: 'volatility',
    description: 'ATR-based volatility channels',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 },
      { name: 'multiplier', type: 'number', default: 2, min: 0.5, max: 5, step: 0.5 }
    ]
  },
  BB: {
    name: 'Bollinger Bands',
    category: 'volatility',
    description: 'Standard deviation-based bands',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 },
      { name: 'stdDev', type: 'number', default: 2, min: 0.5, max: 5, step: 0.5 }
    ]
  },
  BBW: {
    name: 'Bollinger Band Width',
    category: 'volatility',
    description: 'Measures Bollinger Band expansion/contraction',
    displayType: 'separate',
    defaultPanel: 'bbw',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 },
      { name: 'stdDev', type: 'number', default: 2, min: 0.5, max: 5, step: 0.5 }
    ]
  },
  BBP: {
    name: 'Bollinger Band %B',
    category: 'volatility',
    description: 'Position within Bollinger Bands',
    displayType: 'separate',
    defaultPanel: 'bbp',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 },
      { name: 'stdDev', type: 'number', default: 2, min: 0.5, max: 5, step: 0.5 }
    ]
  },
  NATR: {
    name: 'Normalized ATR',
    category: 'volatility',
    description: 'ATR as percentage of price',
    displayType: 'separate',
    defaultPanel: 'natr',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  RVI: {
    name: 'Relative Volatility Index',
    category: 'volatility',
    description: 'RSI applied to standard deviation',
    displayType: 'separate',
    defaultPanel: 'rvi',
    parameters: [
      { name: 'period', type: 'number', default: 10, min: 2, max: 200 },
      { name: 'smoothing', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  CHOP: {
    name: 'Choppiness Index',
    category: 'volatility',
    description: 'Measures market choppiness vs trending',
    displayType: 'separate',
    defaultPanel: 'chop',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  VIX: {
    name: 'Volatility Index',
    category: 'volatility',
    description: 'Market fear gauge',
    displayType: 'separate',
    defaultPanel: 'vix',
    parameters: [
      { name: 'period', type: 'number', default: 30, min: 10, max: 200 }
    ]
  },
  HV: {
    name: 'Historical Volatility',
    category: 'volatility',
    description: 'Statistical measure of price dispersion',
    displayType: 'separate',
    defaultPanel: 'hv',
    parameters: [
      { name: 'period', type: 'number', default: 20, min: 2, max: 200 },
      { name: 'annualized', type: 'boolean', default: true }
    ]
  },
  ChandelierExit: {
    name: 'Chandelier Exit',
    category: 'volatility',
    description: 'Volatility-based trailing stop',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 22, min: 2, max: 200 },
      { name: 'multiplier', type: 'number', default: 3, min: 0.5, max: 10, step: 0.5 }
    ]
  },
  SuperTrend: {
    name: 'SuperTrend',
    category: 'volatility',
    description: 'ATR-based trend following indicator',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 10, min: 2, max: 200 },
      { name: 'multiplier', type: 'number', default: 3, min: 0.5, max: 10, step: 0.5 }
    ]
  },

  // Volume Indicators
  AD: {
    name: 'Accumulation/Distribution',
    category: 'volume',
    description: 'Volume-based accumulation/distribution',
    displayType: 'separate',
    defaultPanel: 'ad',
    parameters: []
  },
  CMF: {
    name: 'Chaikin Money Flow',
    category: 'volume',
    description: 'Money flow volume indicator',
    displayType: 'separate',
    defaultPanel: 'cmf',
    parameters: [
      { name: 'period', type: 'number', default: 21, min: 2, max: 200 }
    ]
  },
  EMV: {
    name: 'Ease of Movement',
    category: 'volume',
    description: 'Price change vs volume relationship',
    displayType: 'separate',
    defaultPanel: 'emv',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 },
      { name: 'divisor', type: 'number', default: 10000, min: 100, max: 1000000 }
    ]
  },
  FI: {
    name: 'Force Index',
    category: 'volume',
    description: 'Price and volume momentum',
    displayType: 'separate',
    defaultPanel: 'fi',
    parameters: [
      { name: 'period', type: 'number', default: 13, min: 2, max: 200 }
    ]
  },
  KVO: {
    name: 'Klinger Volume Oscillator',
    category: 'volume',
    description: 'Volume-based trend indicator',
    displayType: 'separate',
    defaultPanel: 'kvo',
    parameters: [
      { name: 'shortPeriod', type: 'number', default: 34, min: 2, max: 200 },
      { name: 'longPeriod', type: 'number', default: 55, min: 2, max: 200 },
      { name: 'signalPeriod', type: 'number', default: 13, min: 2, max: 200 }
    ]
  },
  NVI: {
    name: 'Negative Volume Index',
    category: 'volume',
    description: 'Price changes on low volume days',
    displayType: 'separate',
    defaultPanel: 'nvi',
    parameters: [
      { name: 'startValue', type: 'number', default: 1000, min: 1, max: 10000 }
    ]
  },
  PVI: {
    name: 'Positive Volume Index',
    category: 'volume',
    description: 'Price changes on high volume days',
    displayType: 'separate',
    defaultPanel: 'pvi',
    parameters: [
      { name: 'startValue', type: 'number', default: 1000, min: 1, max: 10000 }
    ]
  },
  PVT: {
    name: 'Price Volume Trend',
    category: 'volume',
    description: 'Cumulative volume adjusted for price changes',
    displayType: 'separate',
    defaultPanel: 'pvt',
    parameters: []
  },
  VWAP: {
    name: 'Volume Weighted Average Price',
    category: 'volume',
    description: 'Average price weighted by volume',
    displayType: 'overlay',
    parameters: []
  },
  VPVR: {
    name: 'Volume Profile Visible Range',
    category: 'volume',
    description: 'Volume distribution by price level',
    displayType: 'overlay',
    parameters: [
      { name: 'rowSize', type: 'number', default: 24, min: 10, max: 100 },
      { name: 'valueArea', type: 'number', default: 70, min: 10, max: 90 }
    ]
  },
  VR: {
    name: 'Volume Ratio',
    category: 'volume',
    description: 'Up volume vs down volume ratio',
    displayType: 'separate',
    defaultPanel: 'vr',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  WAD: {
    name: 'Williams A/D',
    category: 'volume',
    description: 'Williams Accumulation/Distribution',
    displayType: 'separate',
    defaultPanel: 'wad',
    parameters: []
  },

  // Market Structure
  PIVOT: {
    name: 'Pivot Points',
    category: 'structure',
    description: 'Support/resistance levels',
    displayType: 'overlay',
    parameters: [
      {
        name: 'type',
        type: 'string',
        default: 'classic',
        options: ['classic', 'fibonacci', 'woodie', 'camarilla', 'demark']
      }
    ]
  },
  CAMARILLA: {
    name: 'Camarilla Pivot Points',
    category: 'structure',
    description: 'Advanced pivot point system',
    displayType: 'overlay',
    parameters: []
  },
  FIBONACCI: {
    name: 'Fibonacci Retracements',
    category: 'structure',
    description: 'Fibonacci support/resistance levels',
    displayType: 'overlay',
    parameters: [
      { name: 'lookback', type: 'number', default: 50, min: 10, max: 500 }
    ]
  },
  GANN: {
    name: 'Gann Levels',
    category: 'structure',
    description: 'Gann price and time levels',
    displayType: 'overlay',
    parameters: [
      { name: 'levels', type: 'number', default: 9, min: 1, max: 20 }
    ]
  },
  MURREY: {
    name: 'Murrey Math Lines',
    category: 'structure',
    description: 'Mathematical support/resistance levels',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 64, min: 8, max: 256 }
    ]
  },
  SUPPORT: {
    name: 'Support Levels',
    category: 'structure',
    description: 'Dynamic support levels',
    displayType: 'overlay',
    parameters: [
      { name: 'lookback', type: 'number', default: 100, min: 10, max: 500 },
      { name: 'strength', type: 'number', default: 3, min: 1, max: 10 }
    ]
  },
  RESISTANCE: {
    name: 'Resistance Levels',
    category: 'structure',
    description: 'Dynamic resistance levels',
    displayType: 'overlay',
    parameters: [
      { name: 'lookback', type: 'number', default: 100, min: 10, max: 500 },
      { name: 'strength', type: 'number', default: 3, min: 1, max: 10 }
    ]
  },
  ZIGZAG: {
    name: 'ZigZag',
    category: 'structure',
    description: 'Filters out minor price movements',
    displayType: 'overlay',
    parameters: [
      { name: 'deviation', type: 'number', default: 5, min: 0.1, max: 50, step: 0.1 }
    ]
  },
  FRACTAL: {
    name: 'Fractal',
    category: 'structure',
    description: 'Williams fractals for reversal points',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 5, min: 3, max: 21 }
    ]
  },
  MARKET_PROFILE: {
    name: 'Market Profile',
    category: 'structure',
    description: 'Time-price opportunity distribution',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'string', default: 'day', options: ['day', 'week', 'month'] },
      { name: 'valueArea', type: 'number', default: 70, min: 10, max: 90 }
    ]
  },

  // Advanced Indicators
  VORTEX: {
    name: 'Vortex Indicator',
    category: 'advanced',
    description: 'Trend direction and strength',
    displayType: 'separate',
    defaultPanel: 'vortex',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  },
  AROON: {
    name: 'Aroon Oscillator',
    category: 'advanced',
    description: 'Trend strength and direction',
    displayType: 'separate',
    defaultPanel: 'aroon',
    parameters: [
      { name: 'period', type: 'number', default: 25, min: 2, max: 200 }
    ]
  },
  BOP: {
    name: 'Balance of Power',
    category: 'advanced',
    description: 'Buying vs selling pressure',
    displayType: 'separate',
    defaultPanel: 'bop',
    parameters: []
  },
  CORAL: {
    name: 'Coral Trend',
    category: 'advanced',
    description: 'Adaptive trend indicator',
    displayType: 'overlay',
    parameters: [
      { name: 'period', type: 'number', default: 21, min: 2, max: 200 },
      { name: 'deviation', type: 'number', default: 0.4, min: 0.1, max: 1, step: 0.1 }
    ]
  },
  ELDER_RAY: {
    name: 'Elder Ray Index',
    category: 'advanced',
    description: 'Bull and bear power',
    displayType: 'separate',
    defaultPanel: 'elder',
    parameters: [
      { name: 'period', type: 'number', default: 13, min: 2, max: 200 }
    ]
  },
  GATOR: {
    name: 'Gator Oscillator',
    category: 'advanced',
    description: 'Alligator indicator histogram',
    displayType: 'separate',
    defaultPanel: 'gator',
    parameters: [
      { name: 'jawPeriod', type: 'number', default: 13, min: 2, max: 200 },
      { name: 'teethPeriod', type: 'number', default: 8, min: 2, max: 200 },
      { name: 'lipsPeriod', type: 'number', default: 5, min: 2, max: 200 },
      { name: 'jawOffset', type: 'number', default: 8, min: 0, max: 50 },
      { name: 'teethOffset', type: 'number', default: 5, min: 0, max: 50 },
      { name: 'lipsOffset', type: 'number', default: 3, min: 0, max: 50 }
    ]
  },
  HT: {
    name: 'Hilbert Transform',
    category: 'advanced',
    description: 'Cycle and phase analysis',
    displayType: 'separate',
    defaultPanel: 'ht',
    parameters: []
  },
  MASS_INDEX: {
    name: 'Mass Index',
    category: 'advanced',
    description: 'Volatility-based reversal indicator',
    displayType: 'separate',
    defaultPanel: 'mass',
    parameters: [
      { name: 'emaPeriod', type: 'number', default: 9, min: 2, max: 200 },
      { name: 'sumPeriod', type: 'number', default: 25, min: 2, max: 200 }
    ]
  },
  SCHAFF: {
    name: 'Schaff Trend Cycle',
    category: 'advanced',
    description: 'Improved MACD with cycle component',
    displayType: 'separate',
    defaultPanel: 'schaff',
    parameters: [
      { name: 'fastPeriod', type: 'number', default: 23, min: 2, max: 200 },
      { name: 'slowPeriod', type: 'number', default: 50, min: 2, max: 200 },
      { name: 'signalPeriod', type: 'number', default: 10, min: 2, max: 200 }
    ]
  },
  VI: {
    name: 'Vortex Indicator',
    category: 'advanced',
    description: 'Positive and negative trend movement',
    displayType: 'separate',
    defaultPanel: 'vi',
    parameters: [
      { name: 'period', type: 'number', default: 14, min: 2, max: 200 }
    ]
  }
}

// Helper function to get all indicator types
export function getAllIndicatorTypes(): ExtendedIndicatorType[] {
  return Object.keys(INDICATOR_METADATA) as ExtendedIndicatorType[]
}

// Helper function to get indicators by category
export function getIndicatorsByCategory(category: IndicatorMetadata['category']): ExtendedIndicatorType[] {
  return Object.entries(INDICATOR_METADATA)
    .filter(([_, meta]) => meta.category === category)
    .map(([type]) => type as ExtendedIndicatorType)
}

// Helper function to create default config
export function createDefaultIndicatorConfig(
  type: ExtendedIndicatorType,
  id?: string
): AnyExtendedIndicatorConfig | null {
  const metadata = INDICATOR_METADATA[type]
  if (!metadata) return null

  const params: any = {}
  metadata.parameters.forEach(param => {
    params[param.name] = param.default
  })

  return {
    id: id || `${type.toLowerCase()}_${Date.now()}`,
    type,
    enabled: true,
    displayType: metadata.displayType,
    panel: metadata.defaultPanel || 'main',
    params,
    style: {
      color: '#3498db',
      lineWidth: 2,
      opacity: 1
    }
  } as AnyExtendedIndicatorConfig
}