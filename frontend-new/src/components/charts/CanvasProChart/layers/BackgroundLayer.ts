/**
 * BackgroundLayer - Layer estática para background e grid
 * Raramente é redesenhada (apenas quando tema ou viewport mudam significativamente)
 */

import { Layer } from '../core/Layer'
import { ChartTheme } from '../types'
import { ChartEngine } from '../Engine'

export class BackgroundLayer extends Layer {
  private theme: ChartTheme | null = null
  private engine: ChartEngine | null = null

  constructor(name: string, zIndex: number) {
    super(name, zIndex)
  }

  /**
   * Inicializa o layer com engine e theme
   */
  initialize(engine: ChartEngine, theme: ChartTheme): void {
    this.engine = engine
    this.theme = theme
    this.markDirty()
  }

  /**
   * Define o tema
   */
  setTheme(theme: ChartTheme): void {
    this.theme = theme
    this.markDirty()
  }

  /**
   * Define o engine
   */
  setEngine(engine: ChartEngine): void {
    this.engine = engine
    this.markDirty()
  }

  /**
   * Renderiza background e grid
   */
  render(): void {
    if (!this.theme || !this.engine) {
      console.warn('⚠️ [BackgroundLayer] Missing theme or engine')
      return
    }

    const width = this.canvas.width / (window.devicePixelRatio || 1)
    const height = this.canvas.height / (window.devicePixelRatio || 1)

    this.clear()

    // Desenhar background
    this.drawBackground(width, height)

    // Desenhar grid
    this.drawGrid(width, height)
  }

  /**
   * Desenha o background
   */
  private drawBackground(width: number, height: number): void {
    if (!this.theme) return

    this.ctx.fillStyle = this.theme.background
    this.ctx.fillRect(0, 0, width, height)
  }

  /**
   * Desenha a grade (horizontal e vertical)
   */
  private drawGrid(width: number, height: number): void {
    if (!this.theme || !this.engine) return

    this.ctx.strokeStyle = this.theme.grid.color
    this.ctx.lineWidth = this.theme.grid.lineWidth

    // Linhas horizontais (preço)
    const priceRange = this.engine.getPriceRange()
    const priceStep = this.calculatePriceStep(priceRange.max - priceRange.min)
    const startPrice = Math.floor(priceRange.min / priceStep) * priceStep

    for (let price = startPrice; price <= priceRange.max; price += priceStep) {
      const y = this.engine.priceToY(price)

      this.ctx.beginPath()
      this.ctx.moveTo(0, y)
      this.ctx.lineTo(width, y)
      this.ctx.stroke()

      // Label do preço
      this.ctx.fillStyle = this.theme.text.secondary
      this.ctx.font = `${this.theme.text.fontSize}px ${this.theme.text.fontFamily}`
      this.ctx.textAlign = 'right'
      this.ctx.fillText(price.toFixed(2), width - 5, y - 3)
    }

    // Linhas verticais (tempo)
    const visibleCandles = this.engine.getVisibleCandleCount()
    const timeStep = Math.max(10, Math.floor(visibleCandles / 10))
    const viewport = this.engine.getViewport()

    for (let i = Math.floor(viewport.startIndex); i <= viewport.endIndex; i += timeStep) {
      const x = this.engine.indexToX(i)

      if (x < 0 || x > width) continue

      this.ctx.beginPath()
      this.ctx.moveTo(x, 0)
      this.ctx.lineTo(x, height)
      this.ctx.stroke()
    }
  }

  /**
   * Calcula o step ideal para as linhas de preço
   */
  private calculatePriceStep(range: number): number {
    const steps = [0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000, 5000, 10000]
    const targetSteps = 10
    const idealStep = range / targetSteps

    return steps.reduce((prev, curr) => {
      return Math.abs(curr - idealStep) < Math.abs(prev - idealStep) ? curr : prev
    })
  }
}
