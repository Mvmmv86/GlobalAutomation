/**
 * IndicatorRenderer - Renderiza indicadores técnicos no gráfico
 */

import { ChartEngine } from '../Engine'
import { IndicatorResult, AnyIndicatorConfig } from '../indicators/types'

export class IndicatorRenderer {
  private engine: ChartEngine

  constructor(engine: ChartEngine) {
    this.engine = engine
  }

  /**
   * Renderiza um indicador
   */
  render(
    ctx: CanvasRenderingContext2D,
    result: IndicatorResult,
    config: AnyIndicatorConfig
  ): void {
    if (!config.enabled || result.values.length === 0) {
      return
    }

    // Renderizar linha principal
    this.renderLine(ctx, result.values, config.color, config.lineWidth)

    // Renderizar linhas adicionais (se houver)
    if (result.additionalLines) {
      this.renderAdditionalLines(ctx, result, config)
    }
  }

  /**
   * Renderiza linha principal do indicador
   */
  private renderLine(
    ctx: CanvasRenderingContext2D,
    values: number[],
    color: string,
    lineWidth: number
  ): void {
    ctx.save()
    ctx.strokeStyle = color
    ctx.lineWidth = lineWidth
    ctx.beginPath()

    let started = false

    values.forEach((value, index) => {
      if (isNaN(value)) return

      const x = this.engine.indexToX(index)
      const y = this.engine.priceToY(value)

      if (!started) {
        ctx.moveTo(x, y)
        started = true
      } else {
        ctx.lineTo(x, y)
      }
    })

    ctx.stroke()
    ctx.restore()
  }

  /**
   * Renderiza linhas adicionais (BB, MACD, etc)
   */
  private renderAdditionalLines(
    ctx: CanvasRenderingContext2D,
    result: IndicatorResult,
    config: AnyIndicatorConfig
  ): void {
    if (!result.additionalLines) return

    // Cores específicas para cada tipo
    const lineColors = this.getAdditionalLineColors(result.type, config.color)

    Object.entries(result.additionalLines).forEach(([key, values]) => {
      const color = lineColors[key] || config.color
      const lineWidth = key === 'histogram' ? 1 : config.lineWidth

      if (key === 'histogram') {
        // Renderizar histograma (MACD)
        this.renderHistogram(ctx, values, color)
      } else if (key === 'overbought' || key === 'oversold') {
        // Renderizar linha horizontal (RSI)
        this.renderHorizontalLine(ctx, values[0], color, 1, true)
      } else {
        // Renderizar linha normal
        this.renderLine(ctx, values, color, lineWidth)
      }
    })
  }

  /**
   * Renderiza histograma (usado no MACD)
   */
  private renderHistogram(
    ctx: CanvasRenderingContext2D,
    values: number[],
    baseColor: string
  ): void {
    const zeroY = this.engine.priceToY(0)

    ctx.save()

    values.forEach((value, index) => {
      if (isNaN(value)) return

      const x = this.engine.indexToX(index)
      const y = this.engine.priceToY(value)
      const height = zeroY - y

      // Cor verde se positivo, vermelho se negativo
      ctx.fillStyle = value >= 0 ? '#4CAF50' : '#F44336'

      const barWidth = this.engine.getCandleWidth() * 0.6
      ctx.fillRect(x - barWidth / 2, Math.min(y, zeroY), barWidth, Math.abs(height))
    })

    ctx.restore()
  }

  /**
   * Renderiza linha horizontal (usado no RSI)
   */
  private renderHorizontalLine(
    ctx: CanvasRenderingContext2D,
    value: number,
    color: string,
    lineWidth: number,
    dashed: boolean = false
  ): void {
    const canvas = this.engine.getCanvas()
    const width = canvas.width / (window.devicePixelRatio || 1)
    const y = this.engine.priceToY(value)

    ctx.save()
    ctx.strokeStyle = color
    ctx.lineWidth = lineWidth

    if (dashed) {
      ctx.setLineDash([5, 5])
    }

    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()

    if (dashed) {
      ctx.setLineDash([])
    }

    ctx.restore()
  }

  /**
   * Retorna cores para linhas adicionais baseado no tipo
   */
  private getAdditionalLineColors(
    type: string,
    baseColor: string
  ): Record<string, string> {
    const colors: Record<string, Record<string, string>> = {
      // Bollinger Bands
      BB: {
        upper: '#00BCD4',
        lower: '#00BCD4',
        middle: baseColor
      },
      // Keltner Channels
      KC: {
        upper: '#8BC34A',
        lower: '#8BC34A',
        middle: baseColor
      },
      // MACD
      MACD: {
        signal: '#FF9800',
        histogram: baseColor
      },
      // Stochastic
      STOCH: {
        d: '#F44336'
      },
      // Stochastic RSI
      STOCHRSI: {
        d: '#FF5722'
      },
      // ADX
      ADX: {
        pdi: '#4CAF50',
        mdi: '#F44336'
      },
      // RSI
      RSI: {
        overbought: '#F44336',
        oversold: '#4CAF50'
      },
      // Ichimoku Cloud
      ICHIMOKU: {
        base: '#FF9800',
        spanA: '#4CAF50',
        spanB: '#F44336'
      },
      // KST
      KST: {
        signal: '#FF9800'
      }
    }

    return colors[type] || {}
  }

  /**
   * Renderiza múltiplos indicadores
   */
  renderMultiple(
    ctx: CanvasRenderingContext2D,
    results: IndicatorResult[],
    configs: AnyIndicatorConfig[]
  ): void {
    results.forEach(result => {
      const config = configs.find(c => c.id === result.id)
      if (config) {
        this.render(ctx, result, config)
      }
    })
  }
}
