/**
 * DataManagerMinimal - FASE 3
 *
 * Objetivo: Armazenar e gerenciar candles da API
 *
 * O que faz:
 * - Recebe candles do hook useCandles
 * - Armazena em array simples
 * - Logs para debug
 * - NÃO renderiza ainda (isso vem na FASE 5)
 */

export interface CandleData {
  time: number        // Timestamp em ms
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export class DataManagerMinimal {
  private candles: CandleData[] = []
  private symbol: string
  private interval: string

  constructor(symbol: string, interval: string) {
    this.symbol = symbol
    this.interval = interval

    console.log(`📊 [DataManagerMinimal] Criado para ${symbol} ${interval}`)
  }

  /**
   * Atualizar candles vindos da API
   */
  updateCandles(newCandles: any[]): void {
    if (!newCandles || newCandles.length === 0) {
      console.warn('⚠️ [DataManagerMinimal] Nenhum candle recebido')
      return
    }

    // Converter formato da API para formato interno
    this.candles = newCandles.map(c => ({
      time: c.timestamp || c.time || 0,
      open: parseFloat(c.open) || 0,
      high: parseFloat(c.high) || 0,
      low: parseFloat(c.low) || 0,
      close: parseFloat(c.close) || 0,
      volume: parseFloat(c.volume) || 0
    }))

    // Ordenar por tempo (mais antigo primeiro)
    this.candles.sort((a, b) => a.time - b.time)

    console.log(`✅ [DataManagerMinimal] ${this.candles.length} candles armazenados para ${this.symbol} ${this.interval}`)
    console.log(`📈 [DataManagerMinimal] Primeiro candle:`, {
      time: new Date(this.candles[0].time).toISOString(),
      open: this.candles[0].open,
      high: this.candles[0].high,
      low: this.candles[0].low,
      close: this.candles[0].close,
      volume: this.candles[0].volume
    })
    console.log(`📈 [DataManagerMinimal] Último candle:`, {
      time: new Date(this.candles[this.candles.length - 1].time).toISOString(),
      open: this.candles[this.candles.length - 1].open,
      high: this.candles[this.candles.length - 1].high,
      low: this.candles[this.candles.length - 1].low,
      close: this.candles[this.candles.length - 1].close,
      volume: this.candles[this.candles.length - 1].volume
    })

    // Calcular faixa de preços
    const prices = this.candles.flatMap(c => [c.high, c.low])
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)

    console.log(`💰 [DataManagerMinimal] Faixa de preços: ${minPrice.toFixed(2)} - ${maxPrice.toFixed(2)}`)
  }

  /**
   * Obter todos os candles
   */
  getCandles(): CandleData[] {
    return this.candles
  }

  /**
   * Obter quantidade de candles
   */
  getCandleCount(): number {
    return this.candles.length
  }

  /**
   * Obter faixa de preços (min/max)
   */
  getPriceRange(): { min: number; max: number } {
    if (this.candles.length === 0) {
      return { min: 0, max: 0 }
    }

    const prices = this.candles.flatMap(c => [c.high, c.low])
    return {
      min: Math.min(...prices),
      max: Math.max(...prices)
    }
  }

  /**
   * Obter faixa de tempo (primeiro/último)
   */
  getTimeRange(): { start: number; end: number } {
    if (this.candles.length === 0) {
      return { start: 0, end: 0 }
    }

    return {
      start: this.candles[0].time,
      end: this.candles[this.candles.length - 1].time
    }
  }

  /**
   * Cleanup
   */
  destroy(): void {
    console.log(`🧹 [DataManagerMinimal] Destruindo (${this.candles.length} candles)`)
    this.candles = []
  }
}
