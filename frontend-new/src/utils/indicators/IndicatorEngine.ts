/**
 * IndicatorEngine - Shared Indicator Calculator
 * Calcula todos os 30+ indicadores usando technicalindicators library
 */

import {
  // Trend
  SMA,
  EMA,
  WMA,
  WEMA,
  TRIX,
  MACD,
  IchimokuCloud,

  // Momentum
  RSI,
  ROC,
  KST,
  PSAR,
  WilliamsR,
  StochasticRSI,

  // Volatility
  BollingerBands,
  ATR,
  KeltnerChannels,

  // Volume
  VWAP,
  OBV,
  ADL,
  ForceIndex,
  MFI,
  VolumeProfile,

  // Oscillators
  Stochastic,
  CCI,
  AwesomeOscillator,

  // Directional
  ADX
} from 'technicalindicators'

import {
  Candle,
  IndicatorResult,
  AnyIndicatorConfig,
  SMAConfig,
  EMAConfig,
  WMAConfig,
  WEMAConfig,
  TRIXConfig,
  MACDConfig,
  IchimokuConfig,
  RSIConfig,
  ROCConfig,
  KSTConfig,
  PSARConfig,
  WILLRConfig,
  STOCHRSIConfig,
  BBConfig,
  ATRConfig,
  KCConfig,
  NWEnvelopeConfig,
  TPOConfig,
  VWAPConfig,
  OBVConfig,
  ADLConfig,
  FIConfig,
  MFIConfig,
  VPConfig,
  STOCHConfig,
  CCIConfig,
  AOConfig,
  ADXConfig
} from './types'

import { calculateNadarayaWatsonEnvelope, NW_COLORS } from './nadarayaWatson'
import { calculateTPO, generateRenderData, TPOResult, TPORenderData, DEFAULT_TPO_CONFIG, TPOConfig as TPOCalcConfig } from './tpo'

export class IndicatorEngine {
  /**
   * Calcula indicador baseado na configuração
   */
  async calculate(config: AnyIndicatorConfig, candles: Candle[]): Promise<IndicatorResult | null> {
    if (!config.enabled || candles.length === 0) {
      return null
    }

    return this.calculateSync(config, candles)
  }

  /**
   * Calcula múltiplos indicadores em batch
   */
  async calculateMultiple(configs: AnyIndicatorConfig[], candles: Candle[]): Promise<IndicatorResult[]> {
    return configs
      .map(config => this.calculateSync(config, candles))
      .filter((result): result is IndicatorResult => result !== null)
  }

  /**
   * Calcula indicador de forma síncrona
   */
  calculateSync(config: AnyIndicatorConfig, candles: Candle[]): IndicatorResult | null {
    if (!config.enabled || candles.length === 0) {
      return null
    }

    try {
      switch (config.type) {
        // TREND INDICATORS
        case 'SMA':
          return this.calculateSMA(config as SMAConfig, candles)
        case 'EMA':
          return this.calculateEMA(config as EMAConfig, candles)
        case 'WMA':
          return this.calculateWMA(config as WMAConfig, candles)
        case 'WEMA':
          return this.calculateWEMA(config as WEMAConfig, candles)
        case 'TRIX':
          return this.calculateTRIX(config as TRIXConfig, candles)
        case 'MACD':
          return this.calculateMACD(config as MACDConfig, candles)
        case 'ICHIMOKU':
          return this.calculateIchimoku(config as IchimokuConfig, candles)

        // MOMENTUM INDICATORS
        case 'RSI':
          return this.calculateRSI(config as RSIConfig, candles)
        case 'ROC':
          return this.calculateROC(config as ROCConfig, candles)
        case 'KST':
          return this.calculateKST(config as KSTConfig, candles)
        case 'PSAR':
          return this.calculatePSAR(config as PSARConfig, candles)
        case 'WILLR':
          return this.calculateWILLR(config as WILLRConfig, candles)
        case 'STOCHRSI':
          return this.calculateSTOCHRSI(config as STOCHRSIConfig, candles)

        // VOLATILITY INDICATORS
        case 'BB':
          return this.calculateBB(config as BBConfig, candles)
        case 'ATR':
          return this.calculateATR(config as ATRConfig, candles)
        case 'KC':
          return this.calculateKC(config as KCConfig, candles)
        case 'NWENVELOPE':
          return this.calculateNWEnvelope(config as NWEnvelopeConfig, candles)

        // MARKET PROFILE
        case 'TPO':
          return this.calculateTPOIndicator(config as TPOConfig, candles)

        // VOLUME INDICATORS
        case 'VWAP':
          return this.calculateVWAP(config as VWAPConfig, candles)
        case 'OBV':
          return this.calculateOBV(config as OBVConfig, candles)
        case 'ADL':
          return this.calculateADL(config as ADLConfig, candles)
        case 'FI':
          return this.calculateFI(config as FIConfig, candles)
        case 'MFI':
          return this.calculateMFI(config as MFIConfig, candles)
        case 'VP':
          return this.calculateVP(config as VPConfig, candles)

        // OSCILLATORS
        case 'STOCH':
          return this.calculateSTOCH(config as STOCHConfig, candles)
        case 'CCI':
          return this.calculateCCI(config as CCIConfig, candles)
        case 'AO':
          return this.calculateAO(config as AOConfig, candles)

        // DIRECTIONAL
        case 'ADX':
          return this.calculateADX(config as ADXConfig, candles)

        default:
          console.warn(`Unknown indicator type: ${config.type}`)
          return null
      }
    } catch (error) {
      console.error(`Error calculating ${config.type}:`, error)
      return null
    }
  }

  // ============================================
  // TREND INDICATORS
  // ============================================

  private calculateSMA(config: SMAConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const values = SMA.calculate({
      period: config.params.period,
      values: closes
    })

    return {
      id: config.id,
      type: 'SMA',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateEMA(config: EMAConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const values = EMA.calculate({
      period: config.params.period,
      values: closes
    })

    return {
      id: config.id,
      type: 'EMA',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateWMA(config: WMAConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const values = WMA.calculate({
      period: config.params.period,
      values: closes
    })

    return {
      id: config.id,
      type: 'WMA',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateWEMA(config: WEMAConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const values = WEMA.calculate({
      period: config.params.period,
      values: closes
    })

    return {
      id: config.id,
      type: 'WEMA',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateTRIX(config: TRIXConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const values = TRIX.calculate({
      period: config.params.period,
      values: closes
    })

    return {
      id: config.id,
      type: 'TRIX',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateMACD(config: MACDConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const result = MACD.calculate({
      fastPeriod: config.params.fastPeriod,
      slowPeriod: config.params.slowPeriod,
      signalPeriod: config.params.signalPeriod,
      values: closes,
      SimpleMAOscillator: false,
      SimpleMASignal: false
    })

    const macdLine = result.map(r => r?.MACD || NaN)
    const signalLine = result.map(r => r?.signal || NaN)
    const histogram = result.map(r => r?.histogram || NaN)

    return {
      id: config.id,
      type: 'MACD',
      values: this.padArray(macdLine, candles.length),
      additionalLines: {
        signal: this.padArray(signalLine, candles.length),
        histogram: this.padArray(histogram, candles.length)
      }
    }
  }

  private calculateIchimoku(config: IchimokuConfig, candles: Candle[]): IndicatorResult {
    const result = IchimokuCloud.calculate({
      conversionPeriod: config.params.conversionPeriod,
      basePeriod: config.params.basePeriod,
      spanPeriod: config.params.spanPeriod,
      displacement: config.params.displacement,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low)
    })

    const conversion = result.map(r => r?.conversion || NaN)
    const base = result.map(r => r?.base || NaN)
    const spanA = result.map(r => r?.spanA || NaN)
    const spanB = result.map(r => r?.spanB || NaN)

    return {
      id: config.id,
      type: 'ICHIMOKU',
      values: this.padArray(conversion, candles.length),
      additionalLines: {
        base: this.padArray(base, candles.length),
        spanA: this.padArray(spanA, candles.length),
        spanB: this.padArray(spanB, candles.length)
      }
    }
  }

  // ============================================
  // MOMENTUM INDICATORS
  // ============================================

  private calculateRSI(config: RSIConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const values = RSI.calculate({
      period: config.params.period,
      values: closes
    })

    return {
      id: config.id,
      type: 'RSI',
      values: this.padArray(values, candles.length),
      additionalLines: {
        overbought: new Array(candles.length).fill(config.params.overbought),
        oversold: new Array(candles.length).fill(config.params.oversold)
      }
    }
  }

  private calculateROC(config: ROCConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const values = ROC.calculate({
      period: config.params.period,
      values: closes
    })

    return {
      id: config.id,
      type: 'ROC',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateKST(config: KSTConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const result = KST.calculate({
      ROCPer1: config.params.roc1,
      ROCPer2: config.params.roc2,
      ROCPer3: config.params.roc3,
      ROCPer4: config.params.roc4,
      SMAROCPer1: config.params.sma1,
      SMAROCPer2: config.params.sma2,
      SMAROCPer3: config.params.sma3,
      SMAROCPer4: config.params.sma4,
      signalPeriod: config.params.signalPeriod,
      values: closes
    })

    const kst = result.map(r => r?.kst || NaN)
    const signal = result.map(r => r?.signal || NaN)

    return {
      id: config.id,
      type: 'KST',
      values: this.padArray(kst, candles.length),
      additionalLines: {
        signal: this.padArray(signal, candles.length)
      }
    }
  }

  private calculatePSAR(config: PSARConfig, candles: Candle[]): IndicatorResult {
    const values = PSAR.calculate({
      step: config.params.step,
      max: config.params.max,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low)
    })

    return {
      id: config.id,
      type: 'PSAR',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateWILLR(config: WILLRConfig, candles: Candle[]): IndicatorResult {
    const values = WilliamsR.calculate({
      period: config.params.period,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close)
    })

    return {
      id: config.id,
      type: 'WILLR',
      values: this.padArray(values, candles.length)
    }
  }

  private calculateSTOCHRSI(config: STOCHRSIConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const result = StochasticRSI.calculate({
      rsiPeriod: config.params.rsiPeriod,
      stochasticPeriod: config.params.stochPeriod,
      kPeriod: config.params.kPeriod,
      dPeriod: config.params.dPeriod,
      values: closes
    })

    const k = result.map(r => r?.k || NaN)
    const d = result.map(r => r?.d || NaN)

    return {
      id: config.id,
      type: 'STOCHRSI',
      values: this.padArray(k, candles.length),
      additionalLines: {
        d: this.padArray(d, candles.length)
      }
    }
  }

  // ============================================
  // VOLATILITY INDICATORS
  // ============================================

  private calculateBB(config: BBConfig, candles: Candle[]): IndicatorResult {
    const closes = candles.map(c => c.close)
    const result = BollingerBands.calculate({
      period: config.params.period,
      stdDev: config.params.stdDev,
      values: closes
    })

    const middle = result.map(r => r?.middle || NaN)
    const upper = result.map(r => r?.upper || NaN)
    const lower = result.map(r => r?.lower || NaN)

    return {
      id: config.id,
      type: 'BB',
      values: this.padArray(middle, candles.length),
      additionalLines: {
        upper: this.padArray(upper, candles.length),
        lower: this.padArray(lower, candles.length)
      }
    }
  }

  private calculateATR(config: ATRConfig, candles: Candle[]): IndicatorResult {
    const result = ATR.calculate({
      period: config.params.period,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close)
    })

    return {
      id: config.id,
      type: 'ATR',
      values: this.padArray(result, candles.length)
    }
  }

  private calculateKC(config: KCConfig, candles: Candle[]): IndicatorResult {
    const result = KeltnerChannels.calculate({
      period: config.params.period,
      atrPeriod: config.params.atrPeriod,
      multiplier: config.params.multiplier,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close)
    })

    const middle = result.map(r => r?.middle || NaN)
    const upper = result.map(r => r?.upper || NaN)
    const lower = result.map(r => r?.lower || NaN)

    return {
      id: config.id,
      type: 'KC',
      values: this.padArray(middle, candles.length),
      additionalLines: {
        upper: this.padArray(upper, candles.length),
        lower: this.padArray(lower, candles.length)
      }
    }
  }

  /**
   * TPO (Time Price Opportunity) / Market Profile
   * Réplica exata do Pine Script "TPO (Replica)" by Criptooasis
   * Returns POC, VAH, VAL levels AND full TPO data for canvas rendering with letters
   */
  private calculateTPOIndicator(config: TPOConfig, candles: Candle[]): IndicatorResult {
    // 🔍 DEBUG: Log dos params recebidos
    console.log('🔧 IndicatorEngine.calculateTPOIndicator - config.params:', config.params)

    // Convert candles to lightweight-charts format with proper Time type
    const lwCandles = candles.map(c => ({
      time: c.time as any, // Cast to Time type
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close
    }))

    // Build TPO config from params
    const tpoConfig: Partial<TPOCalcConfig> = {
      // NOVO: Configurações de sessão 24h
      use24hSession: config.params.use24hSession ?? DEFAULT_TPO_CONFIG.use24hSession,
      sessionStartHour: config.params.sessionStartHour ?? DEFAULT_TPO_CONFIG.sessionStartHour,
      sessionBars: config.params.sessionBars ?? DEFAULT_TPO_CONFIG.sessionBars,
      autoTickSize: config.params.autoTickSize ?? DEFAULT_TPO_CONFIG.autoTickSize,
      tickBarsBack: config.params.tickBarsBack ?? DEFAULT_TPO_CONFIG.tickBarsBack,
      targetSessionHeight: config.params.targetSessionHeight ?? DEFAULT_TPO_CONFIG.targetSessionHeight,
      manualTickSize: config.params.manualTickSize ?? DEFAULT_TPO_CONFIG.manualTickSize,
      valueAreaPercent: config.params.valueAreaPercent ?? DEFAULT_TPO_CONFIG.valueAreaPercent,
      showTPOLetters: config.params.showTPOLetters ?? DEFAULT_TPO_CONFIG.showTPOLetters,
      showPOCLine: config.params.showPOCLine ?? DEFAULT_TPO_CONFIG.showPOCLine,
      showValueAreaLines: config.params.showValueAreaLines ?? DEFAULT_TPO_CONFIG.showValueAreaLines,
      showValueAreaBoxes: config.params.showValueAreaBoxes ?? DEFAULT_TPO_CONFIG.showValueAreaBoxes,
      showInfoBox: config.params.showInfoBox ?? DEFAULT_TPO_CONFIG.showInfoBox,
    }

    // 🔍 DEBUG: Log do config final que vai pro cálculo
    console.log('🔧 IndicatorEngine - tpoConfig FINAL:', tpoConfig)

    const result = calculateTPO(lwCandles as any, tpoConfig)

    // Extract POC values for each candle (for line display)
    const pocValues = new Array(candles.length).fill(NaN)
    const vahValues = new Array(candles.length).fill(NaN)
    const valValues = new Array(candles.length).fill(NaN)

    // Map profile values to candle indices
    for (const profile of result.profiles) {
      for (let i = profile.startBarIndex; i <= profile.endBarIndex; i++) {
        pocValues[i] = profile.poc
        vahValues[i] = profile.vah
        valValues[i] = profile.val
      }
    }

    // Generate render data for canvas - includes candles for positioning
    const renderDataList: TPORenderData[] = []
    for (const profile of result.profiles) {
      const profileCandles = lwCandles.slice(profile.startBarIndex, profile.endBarIndex + 1)
      const renderData = generateRenderData(profile, profileCandles as any, result.config)
      renderDataList.push(renderData)
    }

    return {
      id: config.id,
      type: 'TPO',
      values: pocValues,
      additionalLines: {
        vah: vahValues,
        val: valValues
      },
      // Store full TPO result for canvas rendering
      tpoData: result,
      // Store pre-generated render data for each profile
      tpoRenderData: renderDataList,
      // Store candles for positioning letters
      tpoCandles: lwCandles
    } as IndicatorResult & { tpoData: TPOResult; tpoRenderData: TPORenderData[]; tpoCandles: any[] }
  }

  /**
   * Nadaraya-Watson Envelope (LuxAlgo)
   * Uses Gaussian kernel regression to create smooth price envelopes
   * Includes buy/sell signals based on price crossing the envelope bands
   */
  private calculateNWEnvelope(config: NWEnvelopeConfig, candles: Candle[]): IndicatorResult {
    const result = calculateNadarayaWatsonEnvelope(candles, {
      windowSize: config.params.windowSize,
      bandwidth: config.params.bandwidth,
      multiplier: config.params.multiplier,
      source: config.params.source,
      repaint: config.params.repaint
    })

    // Extract values for the smooth line
    const smoothLine = result.points.map(p => p.smoothLine)
    const upperBand = result.points.map(p => p.upperBand)
    const lowerBand = result.points.map(p => p.lowerBand)

    return {
      id: config.id,
      type: 'NWENVELOPE',
      values: this.padArray(smoothLine, candles.length),
      additionalLines: {
        upper: this.padArray(upperBand, candles.length),
        lower: this.padArray(lowerBand, candles.length)
      },
      // Include buy/sell signals from the NW calculation
      signals: result.signals.map(s => ({
        time: s.time,
        type: s.type,
        price: s.price
      }))
    }
  }

  // ============================================
  // VOLUME INDICATORS
  // ============================================

  private calculateVWAP(config: VWAPConfig, candles: Candle[]): IndicatorResult {
    const result = VWAP.calculate({
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close),
      volume: candles.map(c => c.volume)
    })

    return {
      id: config.id,
      type: 'VWAP',
      values: this.padArray(result, candles.length)
    }
  }

  private calculateOBV(config: OBVConfig, candles: Candle[]): IndicatorResult {
    const result = OBV.calculate({
      close: candles.map(c => c.close),
      volume: candles.map(c => c.volume)
    })

    return {
      id: config.id,
      type: 'OBV',
      values: this.padArray(result, candles.length)
    }
  }

  private calculateADL(config: ADLConfig, candles: Candle[]): IndicatorResult {
    const result = ADL.calculate({
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close),
      volume: candles.map(c => c.volume)
    })

    return {
      id: config.id,
      type: 'ADL',
      values: this.padArray(result, candles.length)
    }
  }

  private calculateFI(config: FIConfig, candles: Candle[]): IndicatorResult {
    const result = ForceIndex.calculate({
      close: candles.map(c => c.close),
      volume: candles.map(c => c.volume),
      period: config.params.period
    })

    return {
      id: config.id,
      type: 'FI',
      values: this.padArray(result, candles.length)
    }
  }

  private calculateMFI(config: MFIConfig, candles: Candle[]): IndicatorResult {
    const result = MFI.calculate({
      period: config.params.period,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close),
      volume: candles.map(c => c.volume)
    })

    return {
      id: config.id,
      type: 'MFI',
      values: this.padArray(result, candles.length)
    }
  }

  private calculateVP(config: VPConfig, candles: Candle[]): IndicatorResult {
    const result = VolumeProfile.calculate({
      close: candles.map(c => c.close),
      volume: candles.map(c => c.volume),
      noOfBars: config.params.numberOfBars,
      priceZone: config.params.priceZones
    })

    const values = result.map(r => r?.volumeAverage || NaN)

    return {
      id: config.id,
      type: 'VP',
      values: this.padArray(values, candles.length)
    }
  }

  // ============================================
  // OSCILLATORS
  // ============================================

  private calculateSTOCH(config: STOCHConfig, candles: Candle[]): IndicatorResult {
    const result = Stochastic.calculate({
      period: config.params.period,
      signalPeriod: config.params.signalPeriod,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close)
    })

    const k = result.map(r => r?.k || NaN)
    const d = result.map(r => r?.d || NaN)

    return {
      id: config.id,
      type: 'STOCH',
      values: this.padArray(k, candles.length),
      additionalLines: {
        d: this.padArray(d, candles.length)
      }
    }
  }

  private calculateCCI(config: CCIConfig, candles: Candle[]): IndicatorResult {
    const result = CCI.calculate({
      period: config.params.period,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close)
    })

    return {
      id: config.id,
      type: 'CCI',
      values: this.padArray(result, candles.length)
    }
  }

  private calculateAO(config: AOConfig, candles: Candle[]): IndicatorResult {
    const result = AwesomeOscillator.calculate({
      fastPeriod: config.params.fastPeriod,
      slowPeriod: config.params.slowPeriod,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low)
    })

    return {
      id: config.id,
      type: 'AO',
      values: this.padArray(result, candles.length)
    }
  }

  // ============================================
  // DIRECTIONAL
  // ============================================

  private calculateADX(config: ADXConfig, candles: Candle[]): IndicatorResult {
    const result = ADX.calculate({
      period: config.params.period,
      high: candles.map(c => c.high),
      low: candles.map(c => c.low),
      close: candles.map(c => c.close)
    })

    const adx = result.map((r: any) => r?.adx || NaN)
    const pdi = result.map((r: any) => r?.pdi || NaN)
    const mdi = result.map((r: any) => r?.mdi || NaN)

    return {
      id: config.id,
      type: 'ADX',
      values: this.padArray(adx, candles.length),
      additionalLines: {
        pdi: this.padArray(pdi, candles.length),
        mdi: this.padArray(mdi, candles.length)
      }
    }
  }

  // ============================================
  // HELPER METHODS
  // ============================================

  private padArray(values: number[], targetLength: number): number[] {
    const padding = targetLength - values.length
    if (padding <= 0) return values

    return [...new Array(padding).fill(NaN), ...values]
  }
}

// Singleton instance
export const indicatorEngine = new IndicatorEngine()
