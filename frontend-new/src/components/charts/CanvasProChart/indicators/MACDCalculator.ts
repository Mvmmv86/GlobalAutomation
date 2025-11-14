/**
 * MACD (Moving Average Convergence Divergence) Calculator
 * Indicador de tendência que mostra a relação entre duas médias móveis
 */

import { Candle } from '../types'

export interface MACDConfig {
  fastPeriod: number // Geralmente 12
  slowPeriod: number // Geralmente 26
  signalPeriod: number // Geralmente 9
}

export interface MACDResult {
  macd: number[]
  signal: number[]
  histogram: number[]
}

export class MACDCalculator {
  /**
   * Calcula EMA (Exponential Moving Average)
   * @param values Array de valores
   * @param period Período da EMA
   * @returns Array de valores EMA
   */
  private static calculateEMA(values: number[], period: number): number[] {
    const ema: number[] = []
    const multiplier = 2 / (period + 1)

    if (values.length < period) {
      return new Array(values.length).fill(NaN)
    }

    // Calcular SMA inicial
    let sum = 0
    for (let i = 0; i < period; i++) {
      sum += values[i]
    }
    ema[period - 1] = sum / period

    // Calcular EMA para os valores restantes
    for (let i = period; i < values.length; i++) {
      ema[i] = (values[i] - ema[i - 1]) * multiplier + ema[i - 1]
    }

    // Preencher valores iniciais com NaN
    for (let i = 0; i < period - 1; i++) {
      ema[i] = NaN
    }

    return ema
  }

  /**
   * Calcula o MACD para uma série de candles
   * @param candles Array de candles
   * @param config Configuração do MACD
   * @returns Objeto com linhas MACD, Signal e Histogram
   */
  static calculate(candles: Candle[], config: MACDConfig): MACDResult {
    const { fastPeriod, slowPeriod, signalPeriod } = config

    // Extrair preços de fechamento
    const closes = candles.map(c => c.close)

    // Calcular EMAs
    const emaFast = this.calculateEMA(closes, fastPeriod)
    const emaSlow = this.calculateEMA(closes, slowPeriod)

    // Calcular linha MACD
    const macd: number[] = []
    for (let i = 0; i < closes.length; i++) {
      if (!isNaN(emaFast[i]) && !isNaN(emaSlow[i])) {
        macd[i] = emaFast[i] - emaSlow[i]
      } else {
        macd[i] = NaN
      }
    }

    // Calcular linha de sinal (EMA do MACD)
    const validMacdValues = macd.filter(v => !isNaN(v))
    if (validMacdValues.length < signalPeriod) {
      // Não há dados suficientes para calcular signal
      return {
        macd,
        signal: new Array(macd.length).fill(NaN),
        histogram: new Array(macd.length).fill(NaN)
      }
    }

    // Criar array temporário sem NaN para calcular signal
    const tempMacd: number[] = []
    const indexMap: number[] = []
    for (let i = 0; i < macd.length; i++) {
      if (!isNaN(macd[i])) {
        tempMacd.push(macd[i])
        indexMap.push(i)
      }
    }

    // Calcular signal EMA
    const tempSignal = this.calculateEMA(tempMacd, signalPeriod)

    // Mapear signal de volta para o array original
    const signal: number[] = new Array(macd.length).fill(NaN)
    for (let i = 0; i < tempSignal.length; i++) {
      if (!isNaN(tempSignal[i])) {
        signal[indexMap[i]] = tempSignal[i]
      }
    }

    // Calcular histograma
    const histogram: number[] = []
    for (let i = 0; i < macd.length; i++) {
      if (!isNaN(macd[i]) && !isNaN(signal[i])) {
        histogram[i] = macd[i] - signal[i]
      } else {
        histogram[i] = NaN
      }
    }

    return { macd, signal, histogram }
  }

  /**
   * Identifica crossovers entre MACD e Signal
   * @param macd Array de valores MACD
   * @param signal Array de valores Signal
   * @returns Objeto com crossovers bullish e bearish
   */
  static findCrossovers(
    macd: number[],
    signal: number[]
  ): { bullish: number[]; bearish: number[] } {
    const bullish: number[] = []
    const bearish: number[] = []

    for (let i = 1; i < macd.length; i++) {
      if (isNaN(macd[i]) || isNaN(signal[i]) || isNaN(macd[i - 1]) || isNaN(signal[i - 1])) {
        continue
      }

      // Bullish crossover: MACD cruza signal de baixo para cima
      if (macd[i - 1] <= signal[i - 1] && macd[i] > signal[i]) {
        bullish.push(i)
      }

      // Bearish crossover: MACD cruza signal de cima para baixo
      if (macd[i - 1] >= signal[i - 1] && macd[i] < signal[i]) {
        bearish.push(i)
      }
    }

    return { bullish, bearish }
  }

  /**
   * Identifica divergências entre preço e MACD
   * @param candles Array de candles
   * @param macd Array de valores MACD
   * @returns Objeto com divergências bullish e bearish
   */
  static findDivergences(
    candles: Candle[],
    macd: number[]
  ): { bullish: number[]; bearish: number[] } {
    const bullish: number[] = []
    const bearish: number[] = []
    const lookback = 5 // Janela para detectar pivots

    for (let i = lookback; i < candles.length - lookback; i++) {
      if (isNaN(macd[i])) continue

      // Verificar se é um pivot baixo no preço
      let isPriceLow = true
      for (let j = i - lookback; j <= i + lookback; j++) {
        if (j !== i && candles[j].low < candles[i].low) {
          isPriceLow = false
          break
        }
      }

      // Verificar se é um pivot baixo no MACD
      let isMACDLow = true
      for (let j = i - lookback; j <= i + lookback; j++) {
        if (j !== i && !isNaN(macd[j]) && macd[j] < macd[i]) {
          isMACDLow = false
          break
        }
      }

      // Divergência bullish: preço faz low mais baixo, MACD faz low mais alto
      if (isPriceLow && isMACDLow) {
        // Procurar pivot baixo anterior
        for (let k = i - lookback * 2; k > lookback; k--) {
          if (isNaN(macd[k])) continue

          let isPrevPriceLow = true
          let isPrevMACDLow = true

          for (let j = k - lookback; j <= k + lookback; j++) {
            if (j !== k && candles[j].low < candles[k].low) {
              isPrevPriceLow = false
            }
            if (j !== k && !isNaN(macd[j]) && macd[j] < macd[k]) {
              isPrevMACDLow = false
            }
          }

          if (isPrevPriceLow && isPrevMACDLow) {
            // Verificar divergência
            if (candles[i].low < candles[k].low && macd[i] > macd[k]) {
              bullish.push(i)
            }
            break
          }
        }
      }

      // Verificar pivot alto (para divergência bearish)
      let isPriceHigh = true
      for (let j = i - lookback; j <= i + lookback; j++) {
        if (j !== i && candles[j].high > candles[i].high) {
          isPriceHigh = false
          break
        }
      }

      let isMACDHigh = true
      for (let j = i - lookback; j <= i + lookback; j++) {
        if (j !== i && !isNaN(macd[j]) && macd[j] > macd[i]) {
          isMACDHigh = false
          break
        }
      }

      // Divergência bearish: preço faz high mais alto, MACD faz high mais baixo
      if (isPriceHigh && isMACDHigh) {
        // Procurar pivot alto anterior
        for (let k = i - lookback * 2; k > lookback; k--) {
          if (isNaN(macd[k])) continue

          let isPrevPriceHigh = true
          let isPrevMACDHigh = true

          for (let j = k - lookback; j <= k + lookback; j++) {
            if (j !== k && candles[j].high > candles[k].high) {
              isPrevPriceHigh = false
            }
            if (j !== k && !isNaN(macd[j]) && macd[j] > macd[k]) {
              isPrevMACDHigh = false
            }
          }

          if (isPrevPriceHigh && isPrevMACDHigh) {
            // Verificar divergência
            if (candles[i].high > candles[k].high && macd[i] < macd[k]) {
              bearish.push(i)
            }
            break
          }
        }
      }
    }

    return { bullish, bearish }
  }

  /**
   * Calcula a força do momentum baseado no histogram
   * @param histogram Array de valores do histogram
   * @returns Força normalizada entre -1 e 1
   */
  static calculateMomentumStrength(histogram: number[]): number {
    const validValues = histogram.filter(v => !isNaN(v))
    if (validValues.length === 0) return 0

    // Pegar últimos 10 valores
    const recent = validValues.slice(-10)
    if (recent.length === 0) return 0

    // Calcular média
    const avg = recent.reduce((a, b) => a + b, 0) / recent.length

    // Normalizar baseado no desvio padrão
    const variance = recent.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / recent.length
    const stdDev = Math.sqrt(variance)

    if (stdDev === 0) return 0

    // Normalizar entre -1 e 1
    const normalized = Math.max(-1, Math.min(1, avg / (stdDev * 2)))

    return normalized
  }
}