/**
 * CandleRendererMinimal - FASE 5
 *
 * Objetivo: Renderizar candles (velas) no gráfico
 *
 * O que faz:
 * - Desenha candles verdes (alta) e vermelhos (baixa)
 * - Renderiza corpo (open-close) e pavios (high-low)
 * - Usa mesmas margens do GridRenderer
 * - Performance otimizada (apenas candles visíveis)
 */

import type { ChartTheme } from '../theme'
import type { CandleData } from './DataManagerMinimal'

export interface CandleRenderConfig {
  width: number
  height: number
  candles: CandleData[]
  priceMin: number
  priceMax: number
  timeStart: number
  timeEnd: number
}

export class CandleRendererMinimal {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private theme: ChartTheme

  // Margens (mesmas do GridRenderer)
  private readonly MARGIN_LEFT = 80
  private readonly MARGIN_RIGHT = 20
  private readonly MARGIN_TOP = 20
  private readonly MARGIN_BOTTOM = 40

  // Largura mínima/máxima do candle
  private readonly MIN_CANDLE_WIDTH = 1
  private readonly MAX_CANDLE_WIDTH = 20

  constructor(canvas: HTMLCanvasElement, theme: ChartTheme) {
    this.canvas = canvas
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      throw new Error('Failed to get 2D context')
    }
    this.ctx = ctx
    this.theme = theme

    console.log('🕯️ [CandleRendererMinimal] Criado')
  }

  /**
   * Renderizar todos os candles
   */
  render(config: CandleRenderConfig): void {
    const { width, height, candles, priceMin, priceMax, timeStart, timeEnd } = config

    if (candles.length === 0) {
      console.warn('⚠️ [CandleRendererMinimal] Nenhum candle para renderizar')
      return
    }

    // Área de desenho (sem margens)
    const chartWidth = width - this.MARGIN_LEFT - this.MARGIN_RIGHT
    const chartHeight = height - this.MARGIN_TOP - this.MARGIN_BOTTOM

    const priceRange = priceMax - priceMin
    const timeRange = timeEnd - timeStart

    if (priceRange <= 0 || timeRange <= 0) {
      console.warn('⚠️ [CandleRendererMinimal] Range inválido:', { priceRange, timeRange })
      return
    }

    // Calcular largura do candle
    const candleWidth = this.calculateCandleWidth(chartWidth, candles.length)

    console.log(`🕯️ [CandleRendererMinimal] Renderizando ${candles.length} candles`, {
      chartWidth,
      chartHeight,
      candleWidth,
      priceRange,
      timeRange
    })

    // Renderizar cada candle
    candles.forEach((candle, index) => {
      this.renderCandle(candle, index, {
        chartWidth,
        chartHeight,
        candleWidth,
        candles,  // ✅ Passando array de candles para cálculo correto
        priceMin,
        priceMax,
        priceRange,
        timeStart,
        timeRange
      })
    })

    console.log('✅ [CandleRendererMinimal] Renderização completa')
  }

  /**
   * Renderizar um único candle
   */
  private renderCandle(
    candle: CandleData,
    index: number,
    params: {
      chartWidth: number
      chartHeight: number
      candleWidth: number
      candles: CandleData[]
      priceMin: number
      priceMax: number
      priceRange: number
      timeStart: number
      timeRange: number
    }
  ): void {
    const { chartWidth, chartHeight, candleWidth, candles, priceMin, priceMax, priceRange } = params

    // Converter preço para coordenada Y (invertido - preço alto = Y baixo)
    const priceToY = (price: number): number => {
      const ratio = (price - priceMin) / priceRange
      return this.MARGIN_TOP + chartHeight - (ratio * chartHeight)
    }

    // ✅ FIX: Distribuir candles uniformemente no espaço disponível
    // Cada candle ocupa um espaço fixo (candleWidth + gap)
    const totalCandles = candles.length
    const spacing = chartWidth / totalCandles
    const candleX = this.MARGIN_LEFT + (index * spacing)

    // Calcular coordenadas Y
    const highY = priceToY(candle.high)
    const lowY = priceToY(candle.low)
    const openY = priceToY(candle.open)
    const closeY = priceToY(candle.close)

    // Determinar cor (verde = alta, vermelho = baixa)
    const isGreen = candle.close >= candle.open
    const color = isGreen ? this.theme.candle.up : this.theme.candle.down

    // Desenhar pavio (high-low)
    const wickX = candleX + candleWidth / 2
    this.ctx.strokeStyle = color
    this.ctx.lineWidth = 1
    this.ctx.beginPath()
    this.ctx.moveTo(wickX, highY)
    this.ctx.lineTo(wickX, lowY)
    this.ctx.stroke()

    // Desenhar corpo (open-close)
    const bodyTop = Math.min(openY, closeY)
    const bodyHeight = Math.abs(closeY - openY)
    const minBodyHeight = 1 // Altura mínima para candles doji

    this.ctx.fillStyle = color
    this.ctx.fillRect(
      candleX,
      bodyTop,
      candleWidth,
      Math.max(minBodyHeight, bodyHeight)
    )
  }

  /**
   * Calcular largura ideal do candle baseado no espaço disponível
   */
  private calculateCandleWidth(chartWidth: number, candleCount: number): number {
    if (candleCount === 0) return this.MIN_CANDLE_WIDTH

    // Deixar 20% de espaço para gaps entre candles
    const availableWidth = chartWidth * 0.8
    const width = availableWidth / candleCount

    // Limitar entre min e max
    return Math.max(
      this.MIN_CANDLE_WIDTH,
      Math.min(this.MAX_CANDLE_WIDTH, width)
    )
  }

  /**
   * Limpar canvas
   */
  clear(): void {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
  }

  /**
   * Cleanup
   */
  destroy(): void {
    console.log('🧹 [CandleRendererMinimal] Destruindo')
    this.clear()
  }
}
