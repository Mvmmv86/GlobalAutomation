/**
 * SeparatePanelLayer - Renderiza indicadores em painéis separados
 * Suporta RSI, MACD, Stochastic, ATR, Volume, etc
 * Com auto-scale, grid e labels específicos
 */

import { Layer } from '../core/Layer'
import { ChartEngine } from '../Engine'
import { IndicatorEngine } from '../indicators/IndicatorEngine'
import { AnyIndicatorConfig, IndicatorResult, IndicatorType } from '../indicators/types'
import { PanelConfig } from '../PanelManager'

interface PanelBounds {
  min: number
  max: number
  range: number
}

interface GridLine {
  y: number
  value: number
  label: string
}

export class SeparatePanelLayer extends Layer {
  private indicatorEngine: IndicatorEngine
  private engine: ChartEngine | null = null
  private panelConfig: PanelConfig | null = null
  private indicators: AnyIndicatorConfig[] = []
  private cachedResults: Map<string, IndicatorResult> = new Map()
  private theme: any = null

  // Panel positioning
  private panelY: number = 0
  private panelHeight: number = 0

  constructor(name: string, zIndex: number, panelConfig: PanelConfig) {
    super(name, zIndex)
    this.indicatorEngine = new IndicatorEngine()
    this.panelConfig = panelConfig
  }

  /**
   * Inicializa com ChartEngine e tema
   */
  initialize(engine: ChartEngine, theme: any): void {
    this.engine = engine
    this.theme = theme
    this.markDirty()
  }

  /**
   * Define a posição Y do painel no canvas global
   */
  setPanelPosition(y: number, height: number): void {
    this.panelY = y
    this.panelHeight = height
    this.markDirty()
  }

  /**
   * Atualiza configuração do painel
   */
  setPanelConfig(config: PanelConfig): void {
    this.panelConfig = config
    this.markDirty()
  }

  /**
   * Adiciona indicador ao painel
   */
  addIndicator(config: AnyIndicatorConfig): void {
    const existingIndex = this.indicators.findIndex(i => i.id === config.id)

    if (existingIndex >= 0) {
      this.indicators[existingIndex] = config
    } else {
      this.indicators.push(config)
    }

    this.cachedResults.delete(config.id)
    this.markDirty()
  }

  /**
   * Remove indicador
   */
  removeIndicator(id: string): void {
    this.indicators = this.indicators.filter(i => i.id !== id)
    this.cachedResults.delete(id)
    this.markDirty()
  }

  /**
   * Obtém todos os indicadores
   */
  getIndicators(): AnyIndicatorConfig[] {
    return [...this.indicators]
  }

  /**
   * Calcula bounds (min/max) para os valores dos indicadores
   */
  private calculateBounds(results: IndicatorResult[]): PanelBounds {
    if (results.length === 0) {
      return { min: 0, max: 100, range: 100 }
    }

    let min = Infinity
    let max = -Infinity

    // Analisar todos os valores
    for (const result of results) {
      // Valores principais
      for (const value of result.values) {
        if (typeof value === 'number' && !isNaN(value)) {
          min = Math.min(min, value)
          max = Math.max(max, value)
        }
      }

      // Linhas adicionais (ex: MACD signal, histogram)
      if (result.additionalLines) {
        for (const lineValues of Object.values(result.additionalLines)) {
          for (const value of lineValues) {
            if (typeof value === 'number' && !isNaN(value)) {
              min = Math.min(min, value)
              max = Math.max(max, value)
            }
          }
        }
      }
    }

    // Fallback se não encontrou valores válidos
    if (!isFinite(min) || !isFinite(max)) {
      return { min: 0, max: 100, range: 100 }
    }

    // Adicionar padding (5% de cada lado)
    const range = max - min
    const padding = range * 0.05
    min -= padding
    max += padding

    return { min, max, range: max - min }
  }

  /**
   * Auto-scale específico por tipo de indicador
   */
  private getIndicatorBounds(type: IndicatorType, bounds: PanelBounds): PanelBounds {
    // Indicadores com faixa fixa
    switch (type) {
      case 'RSI':
      case 'STOCHRSI':
        return { min: 0, max: 100, range: 100 }

      case 'WILLR':
        return { min: -100, max: 0, range: 100 }

      case 'CCI':
        return { min: -200, max: 200, range: 400 }

      case 'STOCH':
        return { min: 0, max: 100, range: 100 }

      case 'MFI':
        return { min: 0, max: 100, range: 100 }

      default:
        // Usar bounds calculados
        return bounds
    }
  }

  /**
   * Gera linhas de grid apropriadas para o tipo de indicador
   */
  private generateGridLines(type: IndicatorType, bounds: PanelBounds): GridLine[] {
    const lines: GridLine[] = []

    // Grid específico por tipo
    switch (type) {
      case 'RSI':
      case 'STOCHRSI':
      case 'MFI':
        lines.push(
          { y: 0, value: 70, label: '70' },
          { y: 0, value: 50, label: '50' },
          { y: 0, value: 30, label: '30' }
        )
        break

      case 'STOCH':
        lines.push(
          { y: 0, value: 80, label: '80' },
          { y: 0, value: 50, label: '50' },
          { y: 0, value: 20, label: '20' }
        )
        break

      case 'WILLR':
        lines.push(
          { y: 0, value: -20, label: '-20' },
          { y: 0, value: -50, label: '-50' },
          { y: 0, value: -80, label: '-80' }
        )
        break

      case 'CCI':
        lines.push(
          { y: 0, value: 100, label: '100' },
          { y: 0, value: 0, label: '0' },
          { y: 0, value: -100, label: '-100' }
        )
        break

      case 'MACD':
        lines.push({ y: 0, value: 0, label: '0' })
        break

      default:
        // Grid genérico: 5 linhas
        const step = bounds.range / 4
        for (let i = 0; i <= 4; i++) {
          const value = bounds.min + step * i
          lines.push({
            y: 0,
            value,
            label: value.toFixed(2)
          })
        }
    }

    // Calcular coordenadas Y no canvas
    return lines.map(line => ({
      ...line,
      y: this.valueToY(line.value, bounds)
    }))
  }

  /**
   * Converte valor do indicador para coordenada Y no painel
   */
  private valueToY(value: number, bounds: PanelBounds): number {
    if (bounds.range === 0) return this.panelY + this.panelHeight / 2

    const ratio = (value - bounds.min) / bounds.range
    // Inverter Y (canvas Y cresce para baixo)
    return this.panelY + this.panelHeight - ratio * this.panelHeight
  }

  /**
   * Renderiza background e grid do painel
   */
  private renderBackground(bounds: PanelBounds): void {
    if (!this.engine || !this.theme) return

    const ctx = this.ctx

    // Background
    ctx.fillStyle = this.theme.chart.background
    ctx.fillRect(0, this.panelY, this.canvas.width, this.panelHeight)

    // Border top
    ctx.strokeStyle = this.theme.grid.color
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, this.panelY)
    ctx.lineTo(this.canvas.width, this.panelY)
    ctx.stroke()

    // Grid lines
    const gridLines = this.generateGridLines(
      this.indicators[0]?.type || 'RSI',
      bounds
    )

    ctx.strokeStyle = this.theme.grid.color
    ctx.fillStyle = this.theme.text.primary
    ctx.font = '10px Arial'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'middle'

    for (const line of gridLines) {
      // Linha horizontal
      ctx.globalAlpha = 0.3
      ctx.beginPath()
      ctx.moveTo(0, line.y)
      ctx.lineTo(this.canvas.width - 50, line.y)
      ctx.stroke()

      // Label
      ctx.globalAlpha = 0.7
      ctx.fillText(line.label, this.canvas.width - 5, line.y)
    }

    ctx.globalAlpha = 1
  }

  /**
   * Renderiza título do painel
   */
  private renderTitle(): void {
    if (!this.panelConfig || !this.theme) return

    const ctx = this.ctx
    const title = this.panelConfig.title || this.indicators.map(i => i.type).join(', ')

    ctx.fillStyle = this.theme.text.primary
    ctx.font = 'bold 12px Arial'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.fillText(title, 10, this.panelY + 5)
  }

  /**
   * Renderiza os indicadores
   */
  private renderIndicators(results: IndicatorResult[], bounds: PanelBounds): void {
    if (!this.engine) return

    const ctx = this.ctx
    const visibleRange = this.engine.getVisibleRange()

    for (let i = 0; i < results.length; i++) {
      const result = results[i]
      const config = this.indicators[i]

      if (!config || !config.enabled) continue

      // Renderizar linha principal
      this.renderLine(result.values, config.color, config.lineWidth, bounds, visibleRange)

      // Renderizar linhas adicionais (ex: MACD signal, histogram)
      if (result.additionalLines) {
        let additionalColorIndex = 0
        const additionalColors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#A8E6CF']

        for (const [key, values] of Object.entries(result.additionalLines)) {
          const color = additionalColors[additionalColorIndex % additionalColors.length]

          if (key === 'histogram') {
            // Renderizar como barras (ex: MACD histogram)
            this.renderHistogram(values, color, bounds, visibleRange)
          } else {
            // Renderizar como linha
            this.renderLine(values, color, 1.5, bounds, visibleRange)
          }

          additionalColorIndex++
        }
      }
    }
  }

  /**
   * Renderiza uma linha
   */
  private renderLine(
    values: number[],
    color: string,
    lineWidth: number,
    bounds: PanelBounds,
    visibleRange: { start: number; end: number }
  ): void {
    if (!this.engine) return

    const ctx = this.ctx
    const candleWidth = this.engine.getCandleWidth()

    ctx.strokeStyle = color
    ctx.lineWidth = lineWidth
    ctx.beginPath()

    let started = false

    for (let i = visibleRange.start; i <= visibleRange.end && i < values.length; i++) {
      const value = values[i]

      if (typeof value !== 'number' || isNaN(value)) continue

      const x = this.engine.indexToX(i) + candleWidth / 2
      const y = this.valueToY(value, bounds)

      if (!started) {
        ctx.moveTo(x, y)
        started = true
      } else {
        ctx.lineTo(x, y)
      }
    }

    ctx.stroke()
  }

  /**
   * Renderiza histogram (ex: MACD)
   */
  private renderHistogram(
    values: number[],
    color: string,
    bounds: PanelBounds,
    visibleRange: { start: number; end: number }
  ): void {
    if (!this.engine) return

    const ctx = this.ctx
    const candleWidth = this.engine.getCandleWidth()
    const zeroY = this.valueToY(0, bounds)

    for (let i = visibleRange.start; i <= visibleRange.end && i < values.length; i++) {
      const value = values[i]

      if (typeof value !== 'number' || isNaN(value)) continue

      const x = this.engine.indexToX(i)
      const y = this.valueToY(value, bounds)
      const height = Math.abs(y - zeroY)

      // Cor verde/vermelho baseado no sinal
      ctx.fillStyle = value >= 0 ? '#26a69a' : '#ef5350'
      ctx.globalAlpha = 0.6

      if (value >= 0) {
        ctx.fillRect(x, y, candleWidth - 1, height)
      } else {
        ctx.fillRect(x, zeroY, candleWidth - 1, height)
      }
    }

    ctx.globalAlpha = 1
  }

  /**
   * Renderiza o painel completo
   */
  render(): void {
    if (!this.isDirty || !this.engine || !this.panelConfig) {
      return
    }

    // Obter candles
    const candles = this.engine.getCandles()
    if (candles.length === 0) {
      this.clearDirtyRect()
      return
    }

    // Filtrar indicadores habilitados deste painel
    const enabledIndicators = this.indicators.filter(i => i.enabled)

    if (enabledIndicators.length === 0) {
      this.clearDirtyRect()
      return
    }

    // Calcular indicadores
    const results: IndicatorResult[] = []

    for (const indicator of enabledIndicators) {
      let result = this.cachedResults.get(indicator.id)

      if (!result) {
        result = this.indicatorEngine.calculate(indicator, candles)
        if (result) {
          this.cachedResults.set(indicator.id, result)
        }
      }

      if (result) {
        results.push(result)
      }
    }

    if (results.length === 0) {
      this.clearDirtyRect()
      return
    }

    // Calcular bounds
    const calculatedBounds = this.calculateBounds(results)
    const bounds = this.getIndicatorBounds(enabledIndicators[0].type, calculatedBounds)

    // Renderizar
    this.renderBackground(bounds)
    this.renderTitle()
    this.renderIndicators(results, bounds)

    this.clearDirtyRect()
  }

  /**
   * Invalida cache
   */
  invalidateCache(): void {
    this.cachedResults.clear()
    this.markDirty()
  }

  /**
   * Resize
   */
  resize(width: number, height: number): void {
    super.resize(width, height)
    this.invalidateCache()
  }

  /**
   * Destroy
   */
  destroy(): void {
    this.indicators = []
    this.cachedResults.clear()
  }
}
