/**
 * RSI (Relative Strength Index) Calculator
 * Indicador de momentum que mede a velocidade e mudança dos movimentos de preço
 * Varia de 0 a 100, com níveis de sobrecompra (>70) e sobrevenda (<30)
 */

import { Candle } from '../types'

export interface RSIConfig {
  period: number // Geralmente 14
  overbought?: number // Geralmente 70
  oversold?: number // Geralmente 30
}

export class RSICalculator {
  /**
   * Calcula o RSI para uma série de candles
   * @param candles Array de candles
   * @param config Configuração do RSI
   * @returns Array de valores RSI
   */
  static calculate(candles: Candle[], config: RSIConfig): number[] {
    const { period } = config
    const rsi: number[] = []

    if (candles.length < period + 1) {
      // Não há dados suficientes
      return new Array(candles.length).fill(NaN)
    }

    // Calcular mudanças de preço
    const changes: number[] = []
    for (let i = 1; i < candles.length; i++) {
      changes.push(candles[i].close - candles[i - 1].close)
    }

    // Calcular ganhos e perdas médias iniciais
    let avgGain = 0
    let avgLoss = 0

    for (let i = 0; i < period; i++) {
      if (changes[i] > 0) {
        avgGain += changes[i]
      } else {
        avgLoss += Math.abs(changes[i])
      }
    }

    avgGain /= period
    avgLoss /= period

    // Primeiro RSI
    if (avgLoss === 0) {
      rsi[period] = 100
    } else {
      const rs = avgGain / avgLoss
      rsi[period] = 100 - (100 / (1 + rs))
    }

    // Calcular RSI subsequentes usando Wilder's smoothing
    for (let i = period + 1; i < candles.length; i++) {
      const change = changes[i - 1]

      if (change > 0) {
        avgGain = (avgGain * (period - 1) + change) / period
        avgLoss = (avgLoss * (period - 1)) / period
      } else {
        avgGain = (avgGain * (period - 1)) / period
        avgLoss = (avgLoss * (period - 1) + Math.abs(change)) / period
      }

      if (avgLoss === 0) {
        rsi[i] = 100
      } else {
        const rs = avgGain / avgLoss
        rsi[i] = 100 - (100 / (1 + rs))
      }
    }

    // Preencher valores iniciais com NaN
    for (let i = 0; i < period; i++) {
      rsi[i] = NaN
    }

    return rsi
  }

  /**
   * Identifica divergências entre preço e RSI
   * @param candles Array de candles
   * @param rsi Array de valores RSI
   * @returns Objeto com divergências bullish e bearish
   */
  static findDivergences(
    candles: Candle[],
    rsi: number[]
  ): { bullish: number[]; bearish: number[] } {
    const bullish: number[] = []
    const bearish: number[] = []
    const lookback = 5 // Janela para detectar pivots

    for (let i = lookback; i < candles.length - lookback; i++) {
      // Verificar se é um pivot baixo no preço
      let isPriceLow = true
      for (let j = i - lookback; j <= i + lookback; j++) {
        if (j !== i && candles[j].low < candles[i].low) {
          isPriceLow = false
          break
        }
      }

      // Verificar se é um pivot baixo no RSI
      let isRSILow = true
      for (let j = i - lookback; j <= i + lookback; j++) {
        if (j !== i && !isNaN(rsi[j]) && rsi[j] < rsi[i]) {
          isRSILow = false
          break
        }
      }

      // Divergência bullish: preço faz low mais baixo, RSI faz low mais alto
      if (isPriceLow && isRSILow) {
        // Procurar pivot baixo anterior
        for (let k = i - lookback * 2; k > lookback; k--) {
          let isPrevPriceLow = true
          let isPrevRSILow = true

          for (let j = k - lookback; j <= k + lookback; j++) {
            if (j !== k && candles[j].low < candles[k].low) {
              isPrevPriceLow = false
            }
            if (j !== k && !isNaN(rsi[j]) && rsi[j] < rsi[k]) {
              isPrevRSILow = false
            }
          }

          if (isPrevPriceLow && isPrevRSILow) {
            // Verificar divergência
            if (candles[i].low < candles[k].low && rsi[i] > rsi[k]) {
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

      let isRSIHigh = true
      for (let j = i - lookback; j <= i + lookback; j++) {
        if (j !== i && !isNaN(rsi[j]) && rsi[j] > rsi[i]) {
          isRSIHigh = false
          break
        }
      }

      // Divergência bearish: preço faz high mais alto, RSI faz high mais baixo
      if (isPriceHigh && isRSIHigh) {
        // Procurar pivot alto anterior
        for (let k = i - lookback * 2; k > lookback; k--) {
          let isPrevPriceHigh = true
          let isPrevRSIHigh = true

          for (let j = k - lookback; j <= k + lookback; j++) {
            if (j !== k && candles[j].high > candles[k].high) {
              isPrevPriceHigh = false
            }
            if (j !== k && !isNaN(rsi[j]) && rsi[j] > rsi[k]) {
              isPrevRSIHigh = false
            }
          }

          if (isPrevPriceHigh && isPrevRSIHigh) {
            // Verificar divergência
            if (candles[i].high > candles[k].high && rsi[i] < rsi[k]) {
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
   * Calcula o StochRSI (Stochastic RSI)
   * @param rsi Array de valores RSI
   * @param period Período do Stochastic (geralmente 14)
   * @returns Objeto com valores K e D
   */
  static calculateStochRSI(
    rsi: number[],
    period: number = 14
  ): { k: number[]; d: number[] } {
    const k: number[] = []
    const d: number[] = []

    for (let i = 0; i < rsi.length; i++) {
      if (i < period - 1 || isNaN(rsi[i])) {
        k[i] = NaN
        d[i] = NaN
        continue
      }

      // Encontrar min e max no período
      let min = Infinity
      let max = -Infinity

      for (let j = i - period + 1; j <= i; j++) {
        if (!isNaN(rsi[j])) {
          min = Math.min(min, rsi[j])
          max = Math.max(max, rsi[j])
        }
      }

      // Calcular StochRSI
      if (max - min === 0) {
        k[i] = 50 // Valor neutro quando não há range
      } else {
        k[i] = ((rsi[i] - min) / (max - min)) * 100
      }
    }

    // Calcular linha D (média móvel de K, geralmente 3 períodos)
    const dPeriod = 3
    for (let i = 0; i < k.length; i++) {
      if (i < dPeriod - 1 || isNaN(k[i])) {
        d[i] = NaN
      } else {
        let sum = 0
        let count = 0
        for (let j = i - dPeriod + 1; j <= i; j++) {
          if (!isNaN(k[j])) {
            sum += k[j]
            count++
          }
        }
        d[i] = count > 0 ? sum / count : NaN
      }
    }

    return { k, d }
  }
}