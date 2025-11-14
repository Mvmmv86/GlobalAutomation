/**
 * DataManager - Gerenciamento eficiente de grandes volumes de dados
 * Suporta 100k+ candles com performance otimizada
 */

import { Candle, DataBuffer } from './types'

export class DataManager {
  private buffer: DataBuffer
  private sortedCandles: Candle[]

  constructor(maxSize: number = 100000) {
    this.buffer = {
      candles: [],
      maxSize,
      startTime: 0,
      endTime: 0
    }
    this.sortedCandles = []
  }

  /**
   * Adiciona novos candles ao buffer
   */
  addCandles(candles: Candle[]): void {
    if (candles.length === 0) return

    // Merge com candles existentes
    const candleMap = new Map<number, Candle>()

    // Adicionar candles existentes
    this.buffer.candles.forEach(candle => {
      candleMap.set(candle.time, candle)
    })

    // Sobrescrever/adicionar novos candles
    candles.forEach(candle => {
      candleMap.set(candle.time, candle)
    })

    // Converter de volta para array e ordenar
    this.sortedCandles = Array.from(candleMap.values()).sort((a, b) => a.time - b.time)

    // Limitar ao tamanho máximo (manter os mais recentes)
    if (this.sortedCandles.length > this.buffer.maxSize) {
      this.sortedCandles = this.sortedCandles.slice(-this.buffer.maxSize)
    }

    this.buffer.candles = this.sortedCandles

    // Atualizar timestamps
    if (this.sortedCandles.length > 0) {
      this.buffer.startTime = this.sortedCandles[0].time
      this.buffer.endTime = this.sortedCandles[this.sortedCandles.length - 1].time
    }
  }

  /**
   * Atualiza o último candle (para dados em tempo real)
   */
  updateLastCandle(candle: Partial<Candle>): void {
    if (this.sortedCandles.length === 0) return

    const lastCandle = this.sortedCandles[this.sortedCandles.length - 1]

    // Atualizar apenas se for o mesmo timestamp
    if (candle.time === lastCandle.time) {
      Object.assign(lastCandle, candle)
    } else if (candle.time && candle.time > lastCandle.time) {
      // Novo candle
      this.addCandles([candle as Candle])
    }
  }

  /**
   * Retorna candles visíveis no range especificado
   * Usa busca binária para performance
   */
  getVisibleCandles(startIndex: number, endIndex: number): Candle[] {
    const start = Math.max(0, Math.floor(startIndex))
    const end = Math.min(this.sortedCandles.length, Math.ceil(endIndex))

    return this.sortedCandles.slice(start, end)
  }

  /**
   * Retorna candle por índice
   */
  getCandleAt(index: number): Candle | null {
    if (index < 0 || index >= this.sortedCandles.length) return null
    return this.sortedCandles[index]
  }

  /**
   * Encontra índice do candle mais próximo ao timestamp
   */
  findIndexByTime(time: number): number {
    if (this.sortedCandles.length === 0) return -1

    // Busca binária
    let left = 0
    let right = this.sortedCandles.length - 1

    while (left <= right) {
      const mid = Math.floor((left + right) / 2)
      const candleTime = this.sortedCandles[mid].time

      if (candleTime === time) {
        return mid
      } else if (candleTime < time) {
        left = mid + 1
      } else {
        right = mid - 1
      }
    }

    // Retornar o mais próximo
    return left < this.sortedCandles.length ? left : this.sortedCandles.length - 1
  }

  /**
   * Retorna o range de preços para os candles visíveis
   */
  getPriceRange(startIndex: number, endIndex: number): { min: number; max: number } {
    const visibleCandles = this.getVisibleCandles(startIndex, endIndex)

    if (visibleCandles.length === 0) {
      return { min: 0, max: 100 }
    }

    let min = Infinity
    let max = -Infinity

    visibleCandles.forEach(candle => {
      if (candle.low < min) min = candle.low
      if (candle.high > max) max = candle.high
    })

    // Adicionar margem de 2%
    const margin = (max - min) * 0.02
    return {
      min: min - margin,
      max: max + margin
    }
  }

  /**
   * Retorna estatísticas dos dados
   */
  getStats(): {
    totalCandles: number
    startTime: number
    endTime: number
    memoryUsage: number
  } {
    const bytesPerCandle = 48 // Aproximação (6 números * 8 bytes)
    const memoryUsage = this.sortedCandles.length * bytesPerCandle

    return {
      totalCandles: this.sortedCandles.length,
      startTime: this.buffer.startTime,
      endTime: this.buffer.endTime,
      memoryUsage
    }
  }

  /**
   * Limpa todos os dados
   */
  clear(): void {
    this.sortedCandles = []
    this.buffer.candles = []
    this.buffer.startTime = 0
    this.buffer.endTime = 0
  }

  /**
   * Retorna todos os candles (use com cuidado)
   */
  getAllCandles(): Candle[] {
    return this.sortedCandles
  }

  /**
   * Retorna o número total de candles
   */
  get length(): number {
    return this.sortedCandles.length
  }

  /**
   * Verifica se tem dados
   */
  get hasData(): boolean {
    return this.sortedCandles.length > 0
  }

  /**
   * Retorna o último candle
   */
  get lastCandle(): Candle | null {
    if (this.sortedCandles.length === 0) return null
    return this.sortedCandles[this.sortedCandles.length - 1]
  }

  /**
   * Retorna o primeiro candle
   */
  get firstCandle(): Candle | null {
    if (this.sortedCandles.length === 0) return null
    return this.sortedCandles[0]
  }

  /**
   * Método auxiliar para obter candles (usado pelo ChartEngine)
   */
  getCandles(): Candle[] {
    return this.sortedCandles
  }
}
